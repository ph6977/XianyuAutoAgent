#!/usr/bin/env python3
"""
闲鱼自动客服机器人 - 重构版本
智能闲鱼客服机器人系统，实现7×24小时自动化值守

本模块是整个系统的核心入口，负责：
1. WebSocket长连接管理 - 与闲鱼服务器保持实时通信
2. 消息接收和处理 - 解密并解析闲鱼消息
3. 心跳维持机制 - 定期发送心跳包保持连接
4. 自动重连逻辑 - 网络断开时自动重连
5. 人工/自动模式切换 - 支持卖家随时接管对话
6. 消息去重和防回声 - 避免重复处理和无限循环

核心架构：
- WebSocket长连接 → 消息解密 → 意图分析 → 多专家Agent路由 → 生成回复 → 发送回复

技术特点：
- 使用asyncio异步架构，支持高并发消息处理
- 多级消息去重机制（SHA256 + TTL过期）
- 指数退避重连策略，防止服务器压力
- 支持飞书知识库实时查询设备库存
"""

import asyncio
import base64
import json
import os
import sys
import time
from loguru import logger
from dotenv import load_dotenv
import websockets

import sys
import os
# 添加项目根目录到Python路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# 导入核心模块
from src.core.xianyu_client import XianyuClient  # 闲鱼客户端，负责WebSocket连接和API调用
from src.core.context_manager import ChatContextManager  # 对话上下文管理器，维护多轮对话状态
from src.agents.xianyu_agent import XianyuReplyBot  # 多专家Agent系统，负责意图分析和回复生成
from src.utils.xianyu_utils import (
    generate_mid, generate_uuid, trans_cookies,
    generate_device_id, decrypt
)
from src.utils.sensitive_keywords import SensitiveKeywordDetector  # 敏感词检测器，用于安全过滤


class XianyuBot:
    """
    闲鱼机器人主类
    
    这是整个系统的核心控制器，负责：
    1. 管理WebSocket连接生命周期
    2. 接收和处理闲鱼消息
    3. 调用多专家Agent系统生成回复
    4. 管理心跳和自动重连
    5. 处理人工/自动模式切换
    
    使用方法：
        bot = XianyuBot(cookies_str)
        await bot.main_loop()  # 启动主循环
    """

    def __init__(self, cookies_str):
        """
        初始化闲鱼机器人
        
        参数：
            cookies_str: 闲鱼登录Cookies字符串，用于身份验证
        """
        # 初始化核心组件
        self.client = XianyuClient(cookies_str)  # 闲鱼客户端，封装API调用
        self.context_manager = ChatContextManager()  # 上下文管理器，存储对话历史
        self.bot = XianyuReplyBot()  # 多专家Agent系统，生成智能回复
        
        # 初始化额外的组件（智能回复管理器）
        self._init_additional_components()

        # 配置参数（从环境变量读取，支持自定义配置）
        # 心跳配置：定期发送心跳包保持WebSocket连接
        self.heartbeat_interval = int(os.getenv("HEARTBEAT_INTERVAL", "30"))  # 心跳发送间隔（秒）
        self.heartbeat_timeout = int(os.getenv("HEARTBEAT_TIMEOUT", "10"))  # 心跳响应超时时间（秒）
        
        # 重连配置：网络断开时的自动重连策略
        self.max_reconnect_attempts = int(os.getenv("MAX_RECONNECT_ATTEMPTS", "10"))  # 最大重连次数
        self.reconnect_base_delay = int(os.getenv("RECONNECT_BASE_DELAY", "5"))  # 重连基础延迟（秒）
        self.reconnect_max_delay = int(os.getenv("RECONNECT_MAX_DELAY", "60"))  # 重连最大延迟（秒）
        
        # Token配置：闲鱼API访问令牌管理
        self.token_refresh_interval = int(os.getenv("TOKEN_REFRESH_INTERVAL", "3600"))  # Token刷新间隔（秒）
        self.message_expire_time = int(os.getenv("MESSAGE_EXPIRE_TIME", "300000"))  # 消息过期时间（毫秒）

        # 状态变量
        self.last_heartbeat_time = 0  # 上次心跳发送时间
        self.last_heartbeat_response = 0  # 上次心跳响应时间
        self.current_token = None  # 当前闲鱼API访问令牌
        self.last_token_refresh_time = 0  # 上次Token刷新时间
        self.reconnect_attempts = 0  # 当前重连尝试次数
        self.connection_restart_flag = False  # 连接重启标志
        self.ws = None  # WebSocket连接对象
        self.heartbeat_task = None  # 心跳任务
        self.token_refresh_task = None  # Token刷新任务

        # 消息去重机制配置
        # 防止重复处理同一条消息，避免无限循环
        self.processed_messages = set()  # 已处理消息的标识集合
        self.max_processed_messages = 1000  # 最大保存的消息数量
        self.message_ttl = 300  # 消息存活时间（秒），超过后自动清理
        self.message_timestamps = {}  # 消息时间戳记录，用于TTL清理
        self.sent_messages = set()  # 机器人已发送消息的标识集合
        self.sent_messages_ttl = 60  # 已发送消息存活时间（秒）
        self.sent_messages_timestamps = {}  # 已发送消息时间戳记录

        # 人工接管相关配置
        # 支持卖家随时切换到人工模式，处理复杂问题
        self.manual_mode_conversations = set()  # 处于人工接管模式的会话ID集合
        self.manual_mode_timeout = int(os.getenv("MANUAL_MODE_TIMEOUT", "3600"))  # 人工接管超时时间（秒），默认1小时
        self.manual_mode_timestamps = {}  # 记录进入人工模式的时间，用于自动恢复
        self.toggle_keywords = os.getenv("TOGGLE_KEYWORDS", "闲鱼").split(",")  # 人工接管切换关键词列表

    def _init_additional_components(self):
        """
        初始化额外的组件
        
        主要初始化智能回复管理器，它负责：
        1. 敏感词检测 - 识别并过滤敏感内容
        2. 意图分析 - 判断用户消息的意图
        3. Agent路由 - 将消息分发给对应的专家Agent
        
        这是一个双层决策系统：
        - 第一层：关键词快速匹配（零成本）
        - 第二层：LLM语义分析（高成本但准确）
        """
        # 确保智能回复管理器已初始化
        try:
            # 尝试导入并初始化智能回复管理器
            __import__('importlib.util')  # 确保importlib.util模块被导入
            importlib_util_module = sys.modules['importlib.util']  # 从sys.modules获取模块引用
            sys_module = __import__('sys')
            os_module = __import__('os')
            
            # 添加关键问题回复目录到Python路径
            smart_reply_path = os_module.path.join(os_module.path.dirname(__file__), "关键问题回复")
            if smart_reply_path not in sys_module.path:
                sys_module.path.insert(0, smart_reply_path)
            
            # 使用动态导入处理相对导入问题
            smart_reply_manager_path = os_module.path.join(smart_reply_path, "smart_reply_manager.py")
            spec = importlib_util_module.spec_from_file_location("smart_reply_manager", smart_reply_manager_path)
            smart_reply_manager_module = importlib_util_module.module_from_spec(spec)
            # 手动添加到sys.modules，使相对导入可以工作
            sys_module.modules["smart_reply_manager"] = smart_reply_manager_module
            spec.loader.exec_module(smart_reply_manager_module)
            
            SmartReplyManager = smart_reply_manager_module.SmartReplyManager
            
            if not hasattr(self.bot, 'smart_reply_manager') or self.bot.smart_reply_manager is None:
                self.bot.smart_reply_manager = SmartReplyManager()
                logger.info("智能回复管理器已初始化")
        except ImportError:
            logger.warning("无法导入智能回复管理器，可能未安装相关组件")
        except Exception as e:
            logger.error(f"初始化智能回复管理器失败: {e}")

    async def send_message(self, ws, chat_id, to_id, text):
        """
        发送消息到闲鱼
        
        这是消息发送的核心函数，负责：
        1. 构造消息数据结构（符合闲鱼协议格式）
        2. Base64编码消息内容
        3. 生成消息唯一标识（用于去重）
        4. 通过WebSocket发送消息
        
        参数：
            ws: WebSocket连接对象
            chat_id: 聊天会话ID
            to_id: 接收者用户ID
            text: 消息文本内容
        """
        # 构造消息数据结构
        # 闲鱼消息格式要求：contentType=1表示文本消息，text字段包含消息内容
        message_data = {
            "contentType": 1,
            "text": {"text": text}
        }
        # Base64编码消息内容（闲鱼协议要求）
        text_base64 = base64.b64encode(json.dumps(message_data).encode('utf-8')).decode('utf-8')

        # 构造完整的WebSocket消息
        # 包含消息路由、内容、接收者等信息
        msg = {
            "lwp": "/r/MessageSend/sendByReceiverScope",  # 消息发送API路径
            "headers": {"mid": generate_mid()},  # 消息ID，用于追踪
            "body": [
                {
                    "uuid": generate_uuid(),  # 消息UUID
                    "cid": f"{chat_id}@goofish",  # 聊天ID，@goofish是闲鱼标识
                    "conversationType": 1,  # 会话类型：1=单聊
                    "content": {
                        "contentType": 101,  # 内容类型：101=自定义消息
                        "custom": {
                            "type": 1,
                            "data": text_base64  # Base64编码的消息内容
                        }
                    },
                    "redPointPolicy": 0,  # 红点策略：0=不显示红点
                    "extension": {"extJson": "{}"},  # 扩展信息
                    "ctx": {
                        "appVersion": "1.0",  # 应用版本
                        "platform": "web"  # 平台：web端
                    },
                    "mtags": {},  # 消息标签
                    "msgReadStatusSetting": 1  # 已读状态设置
                },
                {
                    "actualReceivers": [
                        f"{to_id}@goofish",  # 接收者ID
                        f"{self.client.myid}@goofish"  # 发送者ID（自己）
                    ]
                }
            ]
        }

        # 在发送前记录消息ID，防止回声循环
        current_time = int(time.time() * 1000)
        sent_message_id = self._generate_message_id(chat_id, self.client.myid, text, current_time)
        self._record_sent_message(sent_message_id)

        await ws.send(json.dumps(msg))

    def _generate_message_id(self, chat_id, send_user_id, send_message, create_time):
        """
        生成消息唯一标识
        
        使用SHA256算法生成消息的唯一标识，用于消息去重。
        标识包含：聊天ID + 发送者ID + 消息内容 + 创建时间
        
        为什么需要消息ID？
        1. 防止重复处理同一条消息
        2. 检测机器人自己发送的消息（防回声）
        3. 消息去重机制的基础
        
        参数：
            chat_id: 聊天会话ID
            send_user_id: 发送者用户ID
            send_message: 消息内容
            create_time: 消息创建时间
            
        返回：
            str: 消息的SHA256哈希值（64位十六进制字符串）
        """
        import hashlib
        # 使用更精确的消息内容，包括时间戳和用户ID
        # 标准化消息内容，去除可能的空格和换行符差异
        normalized_message = send_message.strip().replace('\n', ' ').replace('\r', '')
        message_content = f"{chat_id}_{send_user_id}_{normalized_message}_{create_time}"
        return hashlib.sha256(message_content.encode('utf-8')).hexdigest()

    def _is_duplicate_message(self, message_id):
        """
        检查是否为重复消息
        
        消息去重机制的核心逻辑：
        1. 清理过期消息（TTL机制）
        2. 限制消息集合大小（防止内存溢出）
        3. 检查消息是否已处理
        4. 记录新消息
        
        为什么需要去重？
        - 网络抖动可能导致消息重复发送
        - 服务器可能重试推送同一条消息
        - 避免重复处理造成资源浪费
        
        参数：
            message_id: 消息唯一标识
            
        返回：
            bool: True表示重复消息，False表示新消息
        """
        current_time = time.time()

        # 清理过期消息（TTL机制）
        # 超过message_ttl秒的消息自动清理，防止内存无限增长
        expired_messages = []
        for msg_id, timestamp in self.message_timestamps.items():
            if current_time - timestamp > self.message_ttl:
                expired_messages.append(msg_id)

        for msg_id in expired_messages:
            if msg_id in self.processed_messages:
                self.processed_messages.remove(msg_id)
            if msg_id in self.message_timestamps:
                del self.message_timestamps[msg_id]

        # 限制消息集合大小
        # 当消息数量超过max_processed_messages时，删除最旧的消息
        if len(self.processed_messages) > self.max_processed_messages:
            # 删除最旧的消息（按时间戳排序）
            oldest_messages = sorted(self.message_timestamps.items(), key=lambda x: x[1])[:100]
            for msg_id, _ in oldest_messages:
                if msg_id in self.processed_messages:
                    self.processed_messages.remove(msg_id)
                if msg_id in self.message_timestamps:
                    del self.message_timestamps[msg_id]

        # 检查是否已处理
        if message_id in self.processed_messages:
            return True  # 重复消息

        # 记录新消息
        self.processed_messages.add(message_id)
        self.message_timestamps[message_id] = current_time
        return False  # 新消息

    def _record_sent_message(self, message_id):
        """
        记录机器人已发送的消息
        
        用于防回声机制：检测机器人自己发送的消息，避免无限循环
        
        参数：
            message_id: 消息唯一标识
        """
        current_time = time.time()

        # 清理过期的已发送消息
        expired_messages = []
        for msg_id, timestamp in self.sent_messages_timestamps.items():
            if current_time - timestamp > self.sent_messages_ttl:
                expired_messages.append(msg_id)

        for msg_id in expired_messages:
            if msg_id in self.sent_messages:
                self.sent_messages.remove(msg_id)
            if msg_id in self.sent_messages_timestamps:
                del self.sent_messages_timestamps[msg_id]

        # 记录新发送的消息
        self.sent_messages.add(message_id)
        self.sent_messages_timestamps[message_id] = current_time

    def _is_sent_by_bot(self, chat_id, send_user_id, send_message, create_time):
        """
        检查消息是否是机器人自己发送的
        
        防回声机制的核心：避免机器人处理自己发送的消息，导致无限循环
        
        检测方法：
        1. 精确匹配用户ID（最可靠）
        2. 检查消息ID是否在已发送列表中
        3. 检查内容相似性（备用方法）
        
        参数：
            chat_id: 聊天会话ID
            send_user_id: 发送者用户ID
            send_message: 消息内容
            create_time: 消息创建时间
            
        返回：
            bool: True表示是机器人消息，False表示是用户消息
        """
        # 方法1：检查用户ID（精确匹配）
        if send_user_id == self.client.myid:
            logger.debug(f"通过用户ID检测到机器人消息: {send_user_id}")
            return True

        # 方法1.1：检查用户ID（去除可能的@goofish后缀）
        clean_send_user_id = send_user_id.replace('@goofish', '')
        clean_myid = self.client.myid.replace('@goofish', '')
        if clean_send_user_id == clean_myid:
            logger.debug(f"通过清理后的用户ID检测到机器人消息: {clean_send_user_id}")
            return True

        # 方法2：检查消息内容是否在已发送消息列表中
        message_id = self._generate_message_id(chat_id, send_user_id, send_message, create_time)
        if message_id in self.sent_messages:
            logger.debug(f"通过消息ID检测到机器人消息: {message_id}")
            return True

        # 方法3：检查内容相似性（防止时间戳差异导致ID不匹配）
        normalized_message = send_message.strip().replace('\n', ' ').replace('\r', '')
        # 这里需要存储已发送消息的内容，而不仅仅是ID
        # 暂时禁用此方法，因为我们需要存储消息内容
        # 目前仅依赖方法1和方法2

        logger.debug(f"未检测到机器人消息: 用户ID={send_user_id}, 清理后={clean_send_user_id}, 机器人ID={self.client.myid}, 清理后={clean_myid}, 内容={normalized_message}")
        return False

    async def initialize_connection(self, ws):
        """
        初始化WebSocket连接
        
        WebSocket连接建立后的初始化流程：
        1. 获取/刷新访问令牌（Token）
        2. 注册连接（告诉服务器我要开始接收消息）
        3. 同步消息状态（获取未读消息）
        
        参数：
            ws: WebSocket连接对象
        """
        # 检查Token是否需要刷新
        if not self.current_token or (time.time() - self.last_token_refresh_time) >= self.token_refresh_interval:
            logger.info("获取初始token...")
            token_result = self.client.refresh_token()
            logger.debug(f"refresh_token返回结果类型: {type(token_result)}")
            logger.debug(f"refresh_token返回结果值: {token_result}")
            if token_result is None:
                logger.error("无法获取有效token，初始化失败")
                raise Exception("Token获取失败")
            # 更新当前token
            self.current_token = token_result
            self.last_token_refresh_time = time.time()
            logger.info(f"成功设置当前token: {self.current_token[:20]}...")

        logger.debug(f"当前token: {self.current_token}")
        if self.current_token is None:
            logger.error("无法获取有效token，初始化失败")
            raise Exception("Token获取失败")

        # 注册连接（/reg API）
        # 向服务器注册当前WebSocket连接，开始接收消息推送
        register_msg = {
            "lwp": "/reg",  # 注册API路径
            "headers": {
                "cache-header": "app-key token ua wv",
                "app-key": "444e9908a51d1cb236a27862abc769c9",  # 闲鱼Web端App Key
                "token": self.current_token,  # 访问令牌
                "ua": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36 DingTalk(2.1.5) OS(Windows/10) Browser(Chrome/133.0.0.0) DingWeb/2.1.5 IMPaaS DingWeb/2.1.5",
                "dt": "j",  # 设备类型
                "wv": "im:3,au:3,sy:6",  # 协议版本
                "sync": "0,0;0;0;0;",  # 同步配置
                "did": self.client.device_id,  # 设备ID
                "mid": generate_mid()  # 消息ID
            }
        }
        await ws.send(json.dumps(register_msg))
        await asyncio.sleep(1)  # 等待服务器处理注册

        # 同步消息状态（/r/SyncStatus/ackDiff API）
        # 获取服务器上的未读消息，确保不遗漏任何消息
        sync_msg = {
            "lwp": "/r/SyncStatus/ackDiff",
            "headers": {"mid": "5701741704675979 0"},
            "body": [
                {
                    "pipeline": "sync", "tooLong2Tag": "PNM,1", "channel": "sync",
                    "topic": "sync", "highPts": 0, "pts": int(time.time() * 1000) * 1000,
                    "seq": 0, "timestamp": int(time.time() * 1000)
                }
            ]
        }
        await ws.send(json.dumps(sync_msg))
        logger.info('连接注册完成')

    async def handle_incoming_message(self, message_data, websocket):
        """
        处理接收到的消息
        
        这是消息处理的主入口，流程：
        1. 发送ACK响应（告诉服务器已收到）
        2. 检查是否为同步包消息（只处理同步包）
        3. 解密消息内容（闲鱼消息是加密的）
        4. 处理订单状态消息
        5. 处理聊天消息
        
        参数：
            message_data: 原始消息数据（JSON格式）
            websocket: WebSocket连接对象
        """
        try:
            # 发送ACK响应（告诉服务器消息已收到）
            await self._send_ack_response(message_data, websocket)

            # 如果不是同步包消息，直接返回
            # 只处理同步包消息（包含聊天内容）
            if not self._is_sync_package(message_data):
                return

            # 解密并处理消息
            # 闲鱼消息是加密的，需要先解密
            sync_data = message_data["body"]["syncPushPackage"]["data"][0]
            if "data" not in sync_data:
                return

            try:
                data = sync_data["data"]
                try:
                    # 尝试直接解码（可能是Base64编码）
                    data = base64.b64decode(data).decode("utf-8")
                    data = json.loads(data)
                    return
                except Exception:
                    # 需要解密（使用闲鱼的加密算法）
                    decrypted_data = decrypt(data)
                    message = json.loads(decrypted_data)
            except Exception as e:
                logger.error(f"消息解密失败: {e}")
                return

            # 处理订单状态消息（发货、收货、退款等）
            await self._handle_order_status(message)

            # 处理聊天消息（用户发送的文本消息）
            await self._handle_chat_message(message, websocket)

        except Exception as e:
            logger.error(f"处理消息时发生错误: {str(e)}")

    async def _send_ack_response(self, message_data, websocket):
        """发送ACK响应"""
        try:
            ack = {
                "code": 200,
                "headers": {
                    "mid": message_data["headers"].get("mid", generate_mid()),
                    "sid": message_data["headers"].get("sid", ''),
                }
            }

            # 复制其他可能的header字段
            for key in ["app-key", "ua", "dt"]:
                if key in message_data["headers"]:
                    ack["headers"][key] = message_data["headers"][key]

            await websocket.send(json.dumps(ack))
        except Exception:
            pass

    def _is_sync_package(self, message_data):
        """判断是否为同步包消息"""
        try:
            return (
                isinstance(message_data, dict)
                and "body" in message_data
                and "syncPushPackage" in message_data["body"]
                and "data" in message_data["body"]["syncPushPackage"]
                and len(message_data["body"]["syncPushPackage"]["data"]) > 0
            )
        except Exception:
            return False

    async def _handle_order_status(self, message):
        """处理订单状态消息"""
        try:
            if '3' in message and 'redReminder' in message['3']:
                status = message['3']['redReminder']
                user_id = message['1'].split('@')[0]
                user_url = f'https://www.goofish.com/personal?userId={user_id}'

                if status == '等待买家付款':
                    logger.info(f'等待买家 {user_url} 付款')
                elif status == '交易关闭':
                    logger.info(f'买家 {user_url} 交易关闭')
                elif status == '等待卖家发货':
                    logger.info(f'交易成功 {user_url} 等待卖家发货')
        except Exception:
            pass

    async def _handle_chat_message(self, message, websocket):
        """处理聊天消息"""
        try:
            # 检查是否为用户聊天消息
            if not self._is_chat_message(message):
                return

            # 检查是否为用户正在输入状态
            if self._is_typing_status(message):
                logger.debug("用户正在输入")
                return

            # 提取消息信息
            create_time = int(message["1"]["5"])
            send_user_name = message["1"]["10"]["reminderTitle"]
            send_user_id = message["1"]["10"]["senderUserId"]
            send_message = message["1"]["10"]["reminderContent"]

            # 时效性验证
            if (time.time() * 1000 - create_time) > self.message_expire_time:
                logger.debug("过期消息丢弃")
                return

            # 获取商品ID和会话ID
            url_info = message["1"]["10"]["reminderUrl"]
            item_id = url_info.split("itemId=")[1].split("&")[0] if "itemId=" in url_info else None
            chat_id = message["1"]["2"].split('@')[0]

            if not item_id:
                logger.warning("无法获取商品ID")
                return

            # 检查切换关键词 - 卖家切换人工/自动模式
            if send_user_id == self.client.myid:
                logger.debug("检测到卖家消息，检查是否为控制命令")
                
                # 检查切换命令
                if self._check_toggle_keywords(send_message):
                    mode = self._toggle_manual_mode(chat_id)
                    if mode == "manual":
                        logger.info(f"🔴 已接管会话 {chat_id} (商品: {item_id})")
                    else:
                        logger.info(f"🟢 已恢复会话 {chat_id} 的自动回复 (商品: {item_id})")
                    return
                
                # 记录卖家人工回复
                self.context_manager.add_message_by_chat(chat_id, self.client.myid, item_id, "assistant", send_message)
                logger.info(f"卖家人工回复 (会话: {chat_id}, 商品: {item_id}): {send_message}")
                return

            # 生成消息唯一标识并检查重复
            message_id = self._generate_message_id(chat_id, send_user_id, send_message, create_time)
            logger.debug(f"生成消息ID: {message_id}")
            if self._is_duplicate_message(message_id):
                logger.debug(f"重复消息已忽略: {message_id}")
                return
            else:
                logger.debug(f"新消息，继续处理")

            logger.info(f"用户: {send_user_name} (ID: {send_user_id}), 商品: {item_id}, 会话: {chat_id}, 消息: {send_message}")

            # 检查是否为机器人自己发送的消息，避免无限循环
            logger.debug(f"消息发送者ID: {send_user_id}, 机器人ID: {self.client.myid}")

            # 增强的机器人消息检测
            is_bot_message = self._is_sent_by_bot(chat_id, send_user_id, send_message, create_time)
            logger.debug(f"机器人消息检测结果: {is_bot_message}")
            logger.debug(f"发送者ID: {send_user_id}, 机器人ID: {self.client.myid}")
            logger.debug(f"已发送消息数量: {len(self.sent_messages)}")

            if is_bot_message:
                logger.info(f"忽略机器人自己发送的消息: {send_message}")
                return
            else:
                logger.debug("这是用户发送的消息，继续处理")

            # 检测是否为议价相关消息并提取价格信息
            is_bargain_related = self._is_bargain_message(send_message)
            if is_bargain_related:
                price_info = self._extract_price_info(send_message)
                if price_info:
                    # 如果检测到价格信息，记录议价事件
                    original_price = self._get_original_price(item_id)  # 获取原始价格
                    if original_price and price_info.get('price'):
                        self.context_manager.add_bargain_event(
                            chat_id=chat_id,
                            original_price=original_price,
                            counter_price=price_info['price'],
                            message_content=send_message
                        )
            
            # 添加用户消息到上下文
            message_type = "price_negotiation" if is_bargain_related else "text"
            self.context_manager.add_message_by_chat(chat_id, send_user_id, item_id, "user", send_message, message_type)

            # 如果当前会话处于人工接管模式，不进行自动回复
            if self._is_manual_mode(chat_id):
                logger.info(f"🔴 会话 {chat_id} 处于人工接管模式，跳过自动回复")
                return

            # 获取完整的对话上下文
            context = self.context_manager.get_context_by_chat(chat_id)
            context_text = self._format_context_for_agent(context)

            # 检测是否包含敏感词，如果是则自动进入人工模式
            detector = SensitiveKeywordDetector()
            detected_keywords = detector.detect_sensitive_keywords(send_message)
            
            if detected_keywords:
                logger.info(f"检测到敏感词，自动进入人工模式: {detected_keywords}")
                self._enter_manual_mode(chat_id)  # 进入人工模式
                # 不进行AI回复，等待人工处理
                return
            
            # 优先尝试使用智能回复系统
            if hasattr(self.bot, 'smart_reply_manager') and self.bot.smart_reply_manager:
                try:
                    smart_replies = self.bot.smart_reply_manager.process_message(
                        user_message=send_message,
                        user_id=send_user_id,
                        item_id=item_id,
                        context=context_text
                    )
                    if smart_replies:
                        for reply in smart_replies:
                            self.context_manager.add_message_by_chat(chat_id, self.client.myid, item_id, "assistant", reply)
                            logger.info(f"智能回复系统回复: {reply}")
                            await self.send_message(websocket, chat_id, send_user_id, reply)
                        return
                except Exception as smart_err:
                    logger.error(f"智能回复系统处理失败: {smart_err}")

            # 生成回复
            item_info = self.context_manager.get_item_info(item_id)
            if not item_info:
                logger.info(f"从API获取商品信息: {item_id}")
                api_result = self.client.xianyu.get_item_info(item_id)
                if 'data' in api_result and 'itemDO' in api_result['data']:
                    item_info = api_result['data']['itemDO']
                    self.context_manager.save_item_info(item_id, item_info)
                else:
                    logger.warning(f"获取商品信息失败: {api_result}")
                    return

            # 构建商品描述，处理可能的字段缺失
            try:
                item_description = f"{item_info['desc']};当前商品售卖价格为:{str(item_info['soldPrice'])}"
            except KeyError as e:
                logger.warning(f"商品信息字段缺失: {e}, 使用默认描述")
                item_description = "商品信息获取中..."

            # 获取完整的对话上下文
            context = self.context_manager.get_context_by_chat(chat_id)

            # 生成回复
            bot_reply = self.bot.generate_reply(
                send_message,
                item_description,
                context=context
            )

            # 检查是否为价格意图，如果是则增加议价次数
            if self.bot.last_intent == "price":
                self.context_manager.increment_bargain_count_by_chat(chat_id)
                bargain_count = self.context_manager.get_bargain_count_by_chat(chat_id)
                logger.info(f"用户 {send_user_name} 对商品 {item_id} 的议价次数: {bargain_count}")

            # 添加机器人回复到上下文
            self.context_manager.add_message_by_chat(chat_id, self.client.myid, item_id, "assistant", bot_reply)

            logger.info(f"机器人回复: {bot_reply}")
            await self.send_message(websocket, chat_id, send_user_id, bot_reply)

        except Exception as e:
            logger.error(f"处理聊天消息时发生错误: {str(e)}")
            import traceback
            logger.error(f"错误详情: {traceback.format_exc()}")

    def _format_context_for_agent(self, context):
        """格式化上下文，提供给智能回复体系使用"""
        if not context:
            return ""
        formatted = []
        for message in context:
            role = message.get("role", "")
            if role == "assistant":
                role_label = "助手"
            elif role == "user":
                role_label = "用户"
            else:
                role_label = role or "其他"
            content = message.get("content", "")
            formatted.append(f"{role_label}: {content}")
        return "\n".join(formatted)

    def _is_chat_message(self, message):
        """判断是否为用户聊天消息"""
        try:
            return (
                isinstance(message, dict)
                and "1" in message
                and isinstance(message["1"], dict)
                and "10" in message["1"]
                and isinstance(message["1"]["10"], dict)
                and "reminderContent" in message["1"]["10"]
            )
        except Exception:
            return False

    def _is_typing_status(self, message):
        """判断是否为用户正在输入状态消息"""
        try:
            return (
                isinstance(message, dict)
                and "1" in message
                and isinstance(message["1"], list)
                and len(message["1"]) > 0
                and isinstance(message["1"][0], dict)
                and "1" in message["1"][0]
                and isinstance(message["1"][0]["1"], str)
                and "@goofish" in message["1"][0]["1"]
            )
        except Exception:
            return False

    async def send_heartbeat(self, ws):
        """
        发送心跳包
        
        心跳机制用于：
        1. 告诉服务器"我还活着"
        2. 保持WebSocket连接不被服务器断开
        3. 检测连接是否仍然有效
        
        参数：
            ws: WebSocket连接对象
        """
        try:
            heartbeat_mid = generate_mid()  # 心跳消息ID
            heartbeat_msg = {
                "lwp": "/!",  # 心跳API路径（闲鱼协议）
                "headers": {"mid": heartbeat_mid}
            }
            await ws.send(json.dumps(heartbeat_msg))
            self.last_heartbeat_time = time.time()
            logger.debug("心跳包已发送")
            return heartbeat_mid
        except Exception as e:
            logger.error(f"发送心跳包失败: {e}")
            raise

    async def heartbeat_loop(self, ws):
        """
        心跳维护循环
        
        持续发送心跳包，检测连接状态：
        1. 每隔heartbeat_interval秒发送一次心跳
        2. 检测心跳响应是否超时
        3. 连续超时次数达到阈值时，认为连接断开
        
        为什么需要心跳？
        - 网络NAT设备会自动断开长时间无数据的连接
        - 服务器会主动断开不活跃的客户端
        - 及时发现连接断开，触发重连
        
        参数：
            ws: WebSocket连接对象
        """
        consecutive_timeouts = 0  # 连续超时次数
        max_consecutive_timeouts = 3  # 最大连续超时次数（超过后认为连接断开）

        while True:
            try:
                current_time = time.time()

                # 检查是否需要发送心跳
                if current_time - self.last_heartbeat_time >= self.heartbeat_interval:
                    await self.send_heartbeat(ws)

                # 检查上次心跳响应时间
                time_since_last_response = current_time - self.last_heartbeat_response
                if time_since_last_response > (self.heartbeat_interval + self.heartbeat_timeout):
                    consecutive_timeouts += 1
                    logger.warning(f"心跳响应超时({time_since_last_response:.1f}秒)，连续超时次数: {consecutive_timeouts}")

                    if consecutive_timeouts >= max_consecutive_timeouts:
                        logger.error(f"连续{consecutive_timeouts}次心跳超时，连接可能已断开")
                        break  # 跳出循环，触发重连
                else:
                    # 重置连续超时计数（收到响应说明连接正常）
                    consecutive_timeouts = 0

                await asyncio.sleep(1)  # 每秒检查一次
            except Exception as e:
                logger.error(f"心跳循环出错: {e}")
                break

    async def handle_heartbeat_response(self, message_data):
        """
        处理心跳响应
        
        服务器收到心跳包后会返回响应，更新最后心跳响应时间
        
        参数：
            message_data: 服务器响应数据
            
        返回：
            bool: True表示是心跳响应，False表示不是
        """
        try:
            # 验证响应格式（包含mid和code=200）
            if (
                isinstance(message_data, dict)
                and "headers" in message_data
                and "mid" in message_data["headers"]
                and "code" in message_data
                and message_data["code"] == 200
            ):
                self.last_heartbeat_response = time.time()
                logger.debug("收到心跳响应")
                return True
        except Exception as e:
            logger.error(f"处理心跳响应出错: {e}")
        return False

    async def token_refresh_loop(self):
        """
        Token刷新循环
        
        定期刷新访问令牌（Token），防止令牌过期导致API调用失败
        
        为什么需要Token？
        - 闲鱼API使用Token进行身份验证
        - Token有有效期（默认1小时）
        - 过期后需要刷新，否则无法发送消息
        """
        while True:
            try:
                current_time = time.time()

                # 检查是否需要刷新token
                if current_time - self.last_token_refresh_time >= self.token_refresh_interval:
                    logger.info("Token即将过期，准备刷新...")

                    new_token = self.client.refresh_token()
                    if new_token:
                        logger.info("Token刷新成功，准备重新建立连接...")
                        self.connection_restart_flag = True  # 设置重启标志
                        if self.ws:
                            await self.ws.close()  # 关闭当前连接，触发重连
                        break
                    else:
                        logger.error("Token刷新失败，将在5分钟后重试")
                        await asyncio.sleep(300)  # 等待5分钟后重试
                        continue

                await asyncio.sleep(60)  # 每分钟检查一次

            except Exception as e:
                logger.error(f"Token刷新循环出错: {e}")
                await asyncio.sleep(60)

    async def main_loop(self):
        """
        主事件循环
        
        这是整个系统的入口，负责：
        1. 建立WebSocket连接
        2. 启动心跳任务
        3. 启动Token刷新任务
        4. 接收和处理消息
        5. 处理连接断开和重连
        
        主循环流程：
        连接 → 注册 → 启动心跳 → 消息处理 → 断开 → 重连
        """
        while True:
            try:
                # 重置连接重启标志
                self.connection_restart_flag = False

                # WebSocket连接配置
                headers = {
                    "Cookie": self.client.cookies_str,
                    "Host": "wss-goofish.dingtalk.com",
                    "Connection": "Upgrade",
                    "Pragma": "no-cache",
                    "Cache-Control": "no-cache",
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36",
                    "Origin": "https://www.goofish.com",
                    "Accept-Encoding": "gzip, deflate, br, zstd",
                    "Accept-Language": "zh-CN,zh;q=0.9",
                }

                # 建立WebSocket连接
                async with websockets.connect(
                    self.client.base_url,
                    extra_headers=headers,
                    ping_interval=None,  # 禁用内置心跳（使用自定义心跳）
                    close_timeout=10,
                    open_timeout=30
                ) as websocket:
                    self.ws = websocket
                    # 初始化连接（注册、同步状态）
                    await self.initialize_connection(websocket)

                    # 初始化心跳时间
                    self.last_heartbeat_time = time.time()
                    self.last_heartbeat_response = time.time()

                    # 启动心跳任务（后台运行）
                    self.heartbeat_task = asyncio.create_task(self.heartbeat_loop(websocket))

                    # 启动token刷新任务（后台运行）
                    self.token_refresh_task = asyncio.create_task(self.token_refresh_loop())

                    # 主消息处理循环
                    async for message in websocket:
                        try:
                            # 检查是否需要重启连接（Token刷新触发）
                            if self.connection_restart_flag:
                                logger.info("检测到连接重启标志，准备重新建立连接...")
                                break

                            message_data = json.loads(message)

                            # 处理心跳响应（优先处理）
                            if await self.handle_heartbeat_response(message_data):
                                continue

                            # 处理其他消息（聊天、订单等）
                            await self.handle_incoming_message(message_data, websocket)

                        except json.JSONDecodeError:
                            logger.error("消息解析失败")
                        except Exception as e:
                            logger.error(f"处理消息时发生错误: {str(e)}")

            except websockets.exceptions.ConnectionClosed:
                logger.warning("WebSocket连接已关闭")

            except Exception as e:
                logger.error(f"连接发生错误: {e}")

            finally:
                # 清理异步任务
                await self._cleanup_tasks()

                # 处理重连逻辑（指数退避策略）
                await self._handle_reconnect()

    def _check_toggle_keywords(self, message):
        """
        检查消息是否包含切换关键词
        
        卖家可以通过发送特定关键词切换人工/自动模式
        
        参数：
            message: 消息内容
            
        返回：
            bool: True表示包含切换关键词
        """
        message_stripped = message.strip()
        return message_stripped in self.toggle_keywords

    def _is_manual_mode(self, chat_id):
        """
        检查特定会话是否处于人工接管模式
        
        参数：
            chat_id: 聊天会话ID
            
        返回：
            bool: True表示处于人工模式
        """
        if chat_id not in self.manual_mode_conversations:
            return False
        
        # 检查是否超时（超过manual_mode_timeout自动退出）
        current_time = time.time()
        if chat_id in self.manual_mode_timestamps:
            if current_time - self.manual_mode_timestamps[chat_id] > self.manual_mode_timeout:
                # 超时，自动退出人工模式
                self._exit_manual_mode(chat_id)
                return False
        
        return True

    def _enter_manual_mode(self, chat_id):
        """进入人工接管模式"""
        self.manual_mode_conversations.add(chat_id)
        self.manual_mode_timestamps[chat_id] = time.time()

    def _exit_manual_mode(self, chat_id):
        """退出人工接管模式"""
        self.manual_mode_conversations.discard(chat_id)
        if chat_id in self.manual_mode_timestamps:
            del self.manual_mode_timestamps[chat_id]

    def _toggle_manual_mode(self, chat_id):
        """
        切换人工接管模式
        
        参数：
            chat_id: 聊天会话ID
            
        返回：
            str: "manual"表示人工模式，"auto"表示自动模式
        """
        if self._is_manual_mode(chat_id):
            self._exit_manual_mode(chat_id)
            return "auto"
        else:
            self._enter_manual_mode(chat_id)
            return "manual"

    async def _cleanup_tasks(self):
        """清理异步任务"""
        if self.heartbeat_task:
            self.heartbeat_task.cancel()
            try:
                await self.heartbeat_task
            except asyncio.CancelledError:
                pass

        if self.token_refresh_task:
            self.token_refresh_task.cancel()
            try:
                await self.token_refresh_task
            except asyncio.CancelledError:
                pass

    async def _handle_reconnect(self):
        """
        处理重连逻辑
        
        使用指数退避策略：
        - 第1次重连：5秒
        - 第2次重连：10秒
        - 第3次重连：20秒
        - ...
        - 最大延迟：60秒
        
        添加随机抖动（0.8-1.2倍），防止多个客户端同时重连
        """
        if self.connection_restart_flag:
            # 主动重启（Token刷新），立即重连
            logger.info("主动重启连接，立即重连...")
            self.reconnect_attempts = 0
        else:
            # 被动重连（连接断开），使用指数退避策略
            self.reconnect_attempts += 1

            if self.reconnect_attempts > self.max_reconnect_attempts:
                logger.error(f"已达到最大重连次数({self.max_reconnect_attempts})，程序将退出")
                sys.exit(1)  # 退出程序

            # 计算退避延迟（指数增长）
            delay = min(
                self.reconnect_base_delay * (2 ** (self.reconnect_attempts - 1)),
                self.reconnect_max_delay
            )

            # 添加随机抖动（防止惊群效应）
            import random
            jitter = random.uniform(0.8, 1.2)
            final_delay = delay * jitter

            logger.info(f"第{self.reconnect_attempts}次重连，等待{final_delay:.1f}秒后重连...")
            await asyncio.sleep(final_delay)

    def _is_bargain_message(self, content: str) -> bool:
        """
        判断消息是否与议价相关
        
        使用关键词匹配快速识别议价消息
        
        参数：
            content: 消息内容
            
        返回：
            bool: True表示是议价消息
        """
        bargain_keywords = [
            "便宜", "优惠", "还价", "砍价", "打折", "降价", "价格", "多少钱", "贵", "便宜点",
            "多少", "价位", "底价", "让利", "成交价", "原价", "折扣", "促销", "特价", 
            "1块", "一块", "少点", "给个价", "能少", "价格能", "可以便宜", "能便宜",
            "降", "减", "便宜些", "再便宜", "太贵", "贵了", "砍砍价", "还还价"
        ]
        return any(keyword in content for keyword in bargain_keywords)

    def _extract_price_info(self, content: str) -> dict:
        """
        从消息中提取价格信息
        
        使用正则表达式匹配多种价格格式：
        - "100元"
        - "￥100"
        - "100块"
        - 纯数字
        
        参数：
            content: 消息内容
            
        返回：
            dict: 包含价格信息的字典，None表示未找到
        """
        import re
        
        # 尝试匹配数字价格（包括带"元"、"￥"、"¥"的情况）
        price_patterns = [
            r'(\d+\.?\d*)\s*元',  # 匹配 "数字 元"
            r'[￥¥]\s*(\d+\.?\d*)',  # 匹配 "￥数字" 或 "¥数字"
            r'(\d+\.?\d*)\s*块',  # 匹配 "数字 块"
            r'(\d+\.?\d*)\s*[一二三四五六七八九十百千万亿]',  # 匹配数字后跟中文数字单位
            r'(\d+\.?\d*)\s*(?:[^\w\s]|$)',  # 匹配纯数字（后面是非字母数字字符或结尾）
        ]
        
        for pattern in price_patterns:
            matches = re.findall(pattern, content)
            if matches:
                for match in matches:
                    try:
                        price = float(match)
                        if 0.1 <= price <= 999999:  # 合理的价格范围
                            return {
                                "price": price,
                                "source": match
                            }
                    except ValueError:
                        continue
        
        return None

    def _get_original_price(self, item_id: str) -> float:
        """
        获取商品原始价格
        
        优先从缓存获取，缓存未命中则调用API获取
        
        参数：
            item_id: 商品ID
            
        返回：
            float: 商品原始价格，None表示获取失败
        """
        try:
            # 尝试从商品信息缓存中获取价格
            item_info = self.context_manager.get_item_info(item_id)
            if item_info and 'price' in item_info:
                return float(item_info['price'])
                
            # 如果缓存中没有，尝试通过API获取
            item_detail = self.client.xianyu.get_item_info(item_id)
            if item_detail and 'data' in item_detail:
                item_data = item_detail['data'].get('result', {}).get('item', {})
                if 'price' in item_data:
                    original_price = float(item_data['price'])
                    # 保存到缓存（避免重复请求）
                    if not item_info:
                        self.context_manager.save_item_info(item_id, item_data)
                    return original_price
        except Exception as e:
            logger.error(f"获取商品价格失败 {item_id}: {e}")
        
        return None


def setup_logging():
    """配置日志系统"""
    log_level = os.getenv("LOG_LEVEL", "INFO").upper()
    logger.remove()
    logger.add(
        sys.stderr,
        level=log_level,
        format="<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>"
    )
    logger.info(f"日志级别设置为: {log_level}")


def test_cookies_validity(cookies_str):
    """测试cookies是否有效"""
    try:
        from src.utils.xianyu_utils import trans_cookies, generate_device_id
        from src.utils.xianyu_apis import XianyuApis

        # 创建临时实例测试cookies
        temp_xianyu = XianyuApis()
        temp_cookies = trans_cookies(cookies_str)
        temp_xianyu.session.cookies.update(temp_cookies)

        # 尝试获取token，设置超时避免无限等待
        device_id = generate_device_id(temp_cookies.get('unb', 'unknown'))

        # 使用monkey patch临时修改get_token方法，限制重试次数
        original_get_token = temp_xianyu.get_token

        def patched_get_token(device_id, retry_count=0):
            # 限制最大重试次数为1
            if retry_count >= 1:
                logger.warning("Cookies验证: 达到最大重试次数，返回失败")
                return {"error": "验证失败"}
            return original_get_token(device_id, retry_count)

        # 应用补丁
        temp_xianyu.get_token = patched_get_token

        try:
            token_result = temp_xianyu.get_token(device_id)
        finally:
            # 恢复原始方法
            temp_xianyu.get_token = original_get_token

        # 检查是否成功获取token
        if 'data' in token_result and 'accessToken' in token_result['data']:
            logger.debug("Cookies验证成功")
            return False  # cookies有效，不需要刷新
        else:
            logger.warning(f"Cookies验证失败，需要刷新。API返回: {token_result}")
            return True   # cookies无效，需要刷新

    except SystemExit:
        # 捕获get_token中的sys.exit(1)
        logger.warning("Cookies验证失败（SystemExit），需要刷新")
        return True
    except Exception as e:
        logger.warning(f"Cookies验证异常: {str(e)}，需要刷新")
        return True


def main():
    """
    主函数
    
    程序入口，负责：
    1. 加载环境变量（.env文件）
    2. 配置日志系统
    3. 验证Cookies有效性
    4. 必要时自动刷新Cookies
    5. 启动机器人主循环
    """
    # 加载环境变量
    import os
    from pathlib import Path
    # 获取项目根目录的.env文件路径
    env_path = Path(__file__).parent.parent / ".env"
    load_dotenv(dotenv_path=str(env_path))

    # 配置日志
    setup_logging()

    # 获取cookies
    cookies_str = os.getenv("COOKIES_STR", "")

    # 检查cookies是否有效
    from xianyu_bot_components.utils.xianyu_utils import trans_cookies
    cookies_dict = trans_cookies(cookies_str)

    logger.info(f"检查cookies有效性: cookies_dict={bool(cookies_dict)}, unb字段={'unb' in cookies_dict if cookies_dict else False}")

    # 智能cookies刷新策略
    if not cookies_dict or 'unb' not in cookies_dict or test_cookies_validity(cookies_str):
        # 如果没有有效cookies，强制刷新
        logger.warning("检测到无效cookies，开始刷新Cookies...")
        logger.info("首次使用需要获取闲鱼登录cookies，请按照以下步骤操作：")
        logger.info("1. 浏览器会自动打开闲鱼页面")
        logger.info("2. 请手动完成登录操作")
        logger.info("3. 登录完成后，在终端中按回车键继续")
        logger.info("4. 程序会自动获取并保存cookies")

        # 使用工具刷新cookies
        __import__('importlib.util')  # 确保importlib.util模块被导入
        importlib_util_module = sys.modules['importlib.util']  # 从sys.modules获取模块引用
        sys_module = __import__('sys')
        os_module = __import__('os')
        # 添加crawler_components.tools目录到Python路径
        current_dir = os_module.path.dirname(os_module.path.dirname(os_module.path.abspath(__file__)))  # xianyu_bot_components
        tools_path = os_module.path.join(current_dir, "crawler_components", "tools")
        if tools_path not in sys_module.path:
            sys_module.path.insert(0, tools_path)
        
        # 动态导入refresh_cookies_main
        cookie_refresher_path = os_module.path.join(tools_path, "cookie_refresher.py")
        spec = importlib_util_module.spec_from_file_location("cookie_refresher", cookie_refresher_path)
        cookie_refresher_module = importlib_util_module.module_from_spec(spec)
        # 手动添加到sys.modules，使模块可以被正确引用
        sys_module.modules["cookie_refresher"] = cookie_refresher_module
        spec.loader.exec_module(cookie_refresher_module)
        refresh_cookies_main = cookie_refresher_module.refresh_cookies_main

        success = asyncio.run(refresh_cookies_main(auto_mode=False))
        if success:
            logger.info("Cookies刷新完成，重新加载环境变量...")
            # 重新加载环境变量以获取更新后的COOKIES_STR
            from pathlib import Path
            env_path = Path(__file__).parent.parent / ".env"
            load_dotenv(dotenv_path=str(env_path), override=True)
            cookies_str = os.getenv("COOKIES_STR", "")

            # 重新检查cookies是否有效
            cookies_dict = trans_cookies(cookies_str)
            if not cookies_dict or 'unb' not in cookies_dict:
                logger.error("刷新后的cookies仍然无效，程序无法继续运行")
                logger.info("请手动运行 'python tools/cli.py refresh-cookies' 获取cookies后重试")
                sys.exit(1)

            # 再次验证cookies有效性
            if test_cookies_validity(cookies_str):
                logger.error("刷新后的cookies仍然无法通过API验证，程序无法继续运行")
                logger.info("请检查网络连接或尝试重新登录")
                sys.exit(1)

            logger.info("使用新cookies重新启动程序...")
        else:
            logger.error("Cookies刷新失败，程序无法继续运行")
            logger.info("请手动运行 'python tools/cli.py refresh-cookies' 获取cookies后重试")
            sys.exit(1)

    logger.info("使用现有Cookies启动程序...")

    # 创建机器人实例并启动主循环
    bot = XianyuBot(cookies_str)
    asyncio.run(bot.main_loop())


if __name__ == '__main__':
    main()