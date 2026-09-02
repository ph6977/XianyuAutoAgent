"""
闲鱼智能体系统 - 多专家Agent架构
"""

import re
import os
import sys
from typing import List, Dict
from loguru import logger
from openai import OpenAI

# 添加关键问题回复目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '关键问题回复'))


class XianyuReplyBot:
    """闲鱼回复机器人"""

    def __init__(self):
        # 确保环境变量已加载
        from dotenv import load_dotenv
        load_dotenv()
        
        # 初始化OpenAI客户端
        self.client = OpenAI(
            api_key=os.getenv("API_KEY") or os.getenv("DEEPSEEK_API_KEY"),
            base_url=os.getenv("MODEL_BASE_URL", "https://api.deepseek.com"),
        )
        self._init_system_prompts()
        self._init_agents()
        self._init_rental_agent()
        
        # 初始化智能回复管理器
        self._init_smart_reply_manager()
        
        self.router = IntentRouter(self.agents['classify'])
        self.last_intent = None

    def _init_agents(self):
        """初始化各领域Agent"""
        self.agents = {
            'classify': ClassifyAgent(self.client, self.classify_prompt, self._safe_filter),
            'price': PriceAgent(self.client, self.price_prompt, self._safe_filter),
            'tech': TechAgent(self.client, self.tech_prompt, self._safe_filter),
            'default': DefaultAgent(self.client, self.default_prompt, self._safe_filter),
        }

    def _init_rental_agent(self):
        """初始化租赁顾问Agent"""
        try:
            from .rental_consultant_agent import RentalConsultantAgent
            
            # 租赁顾问系统提示词
            rental_system_prompt = """你是一个专业的设备租赁顾问，为用户提供手机、相机等设备租赁咨询服务。
            请根据用户的需求，推荐合适的设备，并提供租赁价格、租期、押金、使用注意事项等信息。
            回复要专业、友好、准确，以可爱少女的口吻与客户交流。"""
            
            # 尝试初始化飞书读取器
            feishu_reader = None
            try:
                from src.knowledge.feishu_sheet_reader import FeishuSheetReader
                app_id = os.getenv("FEISHU_APP_ID")
                app_secret = os.getenv("FEISHU_APP_SECRET")
                spreadsheet_token = os.getenv("FEISHU_SPREADSHEET_TOKEN")
                sheet_id = os.getenv("FEISHU_SHEET_ID")
                
                if all([app_id, app_secret, spreadsheet_token, sheet_id]):
                    feishu_reader = FeishuSheetReader(app_id, app_secret, spreadsheet_token, sheet_id)
                    logger.info("飞书读取器初始化成功，租赁顾问将支持设备状态查询")
                else:
                    logger.warning("飞书配置不完整，租赁顾问将不支持设备状态查询功能")
            except Exception as e:
                logger.warning(f"飞书读取器初始化失败: {e}")

            self.rental_agent = RentalConsultantAgent(
                client=self.client,
                system_prompt=rental_system_prompt,
                feishu_reader=feishu_reader
            )
            logger.info("租赁顾问Agent初始化成功")
        except Exception as e:
            logger.warning(f"租赁顾问Agent初始化失败: {e}")
            self.rental_agent = None

    def _init_smart_reply_manager(self):
        """初始化智能回复管理器"""
        try:
            from src.agents.smart_reply_manager import SmartReplyManager
            
            self.smart_reply_manager = SmartReplyManager()
            logger.info("智能回复管理器初始化成功")
        except Exception as e:
            logger.warning(f"智能回复管理器初始化失败: {e}")
            self.smart_reply_manager = None

    def _init_system_prompts(self):
        """初始化各Agent专用提示词"""
        script_dir = os.path.dirname(os.path.abspath(__file__))
        prompt_dir = os.path.join(script_dir, "..", "..", "prompts")  # 回到项目根目录

        try:
            # 加载分类提示词
            with open(os.path.join(prompt_dir, "classify_prompt.txt"), "r", encoding="utf-8") as f:
                self.classify_prompt = f.read()

            # 加载价格提示词
            with open(os.path.join(prompt_dir, "price_prompt.txt"), "r", encoding="utf-8") as f:
                self.price_prompt = f.read()

            # 加载技术提示词
            with open(os.path.join(prompt_dir, "tech_prompt.txt"), "r", encoding="utf-8") as f:
                self.tech_prompt = f.read()

            # 加载默认提示词
            with open(os.path.join(prompt_dir, "default_prompt.txt"), "r", encoding="utf-8") as f:
                self.default_prompt = f.read()

            logger.info("成功加载所有提示词")
        except Exception as e:
            logger.error(f"加载提示词时出错: {e}")
            raise

    def _safe_filter(self, text: str) -> str:
        """安全过滤模块"""
        blocked_phrases = ["微信", "QQ", "支付宝", "银行卡", "线下"]
        return "[安全提醒]请通过平台沟通" if any(p in text for p in blocked_phrases) else text

    def format_history(self, context: List[Dict]) -> str:
        """格式化对话历史"""
        user_assistant_msgs = [msg for msg in context if msg['role'] in ['user', 'assistant']]
        return "\n".join([f"{msg['role']}: {msg['content']}" for msg in user_assistant_msgs])

    def generate_reply(self, user_msg: str, item_desc: str, context: List[Dict]) -> str:
        """生成回复主流程"""
        try:
            formatted_context = self.format_history(context)

            # 首先尝试使用智能回复管理器
            if self.smart_reply_manager:
                try:
                    # 尝试从上下文中获取item_id
                    item_id = None
                    if context and len(context) > 0:
                        # 查找包含item_id的上下文消息
                        for msg in reversed(context):
                            if 'item_id' in msg:
                                item_id = msg['item_id']
                                break
                            elif 'content' in msg and 'itemId=' in msg['content']:
                                # 从内容中提取item_id
                                import re
                                match = re.search(r'itemId=(\d+)', msg['content'])
                                if match:
                                    item_id = match.group(1)
                                    break

                    # 使用智能回复管理器处理消息
                    smart_replies = self.smart_reply_manager.process_message(
                        user_message=user_msg,
                        user_id=None,  # 从上下文中获取用户ID
                        item_id=item_id,
                        context=formatted_context
                    )

                    # 如果智能回复管理器返回了回复，则使用它
                    if smart_replies and len(smart_replies) > 0:
                        # 返回第一个回复
                        return smart_replies[0]
                    # 如果智能回复管理器返回空列表，表示静默不回复
                    # 在这种情况下，继续使用原有逻辑

                except Exception as e:
                    logger.error(f"智能回复管理器处理失败: {e}")
                    # 如果智能回复管理器失败，继续使用原有逻辑

            # 检查是否为租赁意图（优先处理）
            if self._is_rental_intent(user_msg) and self.rental_agent:
                try:
                    logger.info('检测到租赁意图，使用租赁顾问Agent')
                    self.last_intent = 'rental'
                    return self.rental_agent.generate(
                        user_message=user_msg,
                        item_description=item_desc,
                        context=formatted_context
                    )
                except Exception as rental_error:
                    logger.error(f"租赁顾问Agent处理失败: {rental_error}")
                    # 继续使用默认路由

            # 1. 路由决策
            detected_intent = self.router.detect(user_msg, item_desc, formatted_context)

            # 2. 获取对应Agent
            internal_intents = {'classify'}

            if detected_intent in self.agents and detected_intent not in internal_intents:
                agent = self.agents[detected_intent]
                logger.info(f'意图识别完成: {detected_intent}')
                self.last_intent = detected_intent
            else:
                agent = self.agents['default']
                logger.info(f'意图识别完成: default')
                self.last_intent = 'default'

            # 3. 获取议价次数
            bargain_count = self._extract_bargain_count(context)
            logger.info(f'议价次数: {bargain_count}')

            # 4. 生成回复
            return agent.generate(
                user_msg=user_msg,
                item_desc=item_desc,
                context=formatted_context,
                bargain_count=bargain_count
            )
        except Exception as e:
            logger.error(f"生成回复时出错: {e}")
            import traceback
            logger.error(f"错误详情: {traceback.format_exc()}")
            return "抱歉，我遇到了一些问题，请稍后再试哦～"

    def _is_rental_intent(self, message: str) -> bool:
        """检测租赁意图"""
        message_lower = message.lower()
        rental_keywords = [
            '租', '租赁', '租用', '租一天', '租一周', '租期', '租金', '押金', 
            '租借', '短期租', '长期租', '租赁时间', '租多久', '租费', '出租'
        ]
        return any(keyword in message_lower for keyword in rental_keywords)

    def _extract_bargain_count(self, context: List[Dict]) -> int:
        """从上下文中提取议价次数信息"""
        for msg in context:
            if msg['role'] == 'system' and '议价次数' in msg['content']:
                try:
                    match = re.search(r'议价次数[:：]\s*(\d+)', msg['content'])
                    if match:
                        return int(match.group(1))
                except Exception:
                    pass
        return 0

    def reload_prompts(self):
        """重新加载所有提示词"""
        logger.info("正在重新加载提示词...")
        self._init_system_prompts()
        self._init_agents()
        logger.info("提示词重新加载完成")


class IntentRouter:
    """意图路由决策器"""

    def __init__(self, classify_agent):
        self.rules = {
            'tech': {
                'keywords': ['参数', '规格', '型号', '连接', '对比'],
                'patterns': [r'和.+比']
            },
            'price': {
                'keywords': ['便宜', '价', '砍价', '少点'],
                'patterns': [r'\d+元', r'能少\d+']
            },
            'rental': {
                'keywords': ['租', '租赁', '租用', '租一天', '租一周', '租期', '租金', '押金', '租借', '短期租', '长期租', '租多久', '租费', '出租'],
                'patterns': []
            }
        }
        self.classify_agent = classify_agent

    def detect(self, user_msg: str, item_desc, context) -> str:
        """四级路由策略（租赁和技术优先）"""
        text_clean = re.sub(r'[^\w\u4e00-\u9fa5]', '', user_msg)

        # 1. 租赁类关键词优先检查
        if any(kw in text_clean for kw in self.rules['rental']['keywords']):
            return 'rental'

        # 2. 技术类关键词优先检查
        if any(kw in text_clean for kw in self.rules['tech']['keywords']):
            return 'tech'

        # 3. 技术类正则优先检查
        for pattern in self.rules['tech']['patterns']:
            if re.search(pattern, text_clean):
                return 'tech'

        # 4. 价格类检查
        for intent in ['price']:
            if any(kw in text_clean for kw in self.rules[intent]['keywords']):
                return intent

            for pattern in self.rules[intent]['patterns']:
                if re.search(pattern, text_clean):
                    return intent

        # 5. 大模型兜底
        return self.classify_agent.generate(
            user_msg=user_msg,
            item_desc=item_desc,
            context=context
        )


class BaseAgent:
    """Agent基类"""

    def __init__(self, client, system_prompt, safety_filter):
        self.client = client
        self.system_prompt = system_prompt
        self.safety_filter = safety_filter

    def generate(self, user_msg: str, item_desc: str, context: str, bargain_count: int = 0) -> str:
        """生成回复模板方法"""
        messages = self._build_messages(user_msg, item_desc, context)
        response = self._call_llm(messages)
        return self.safety_filter(response)

    def _build_messages(self, user_msg: str, item_desc: str, context: str) -> List[Dict]:
        """构建消息链"""
        return [
            {"role": "system", "content": f"【商品信息】{item_desc}\n【你与客户对话历史】{context}\n{self.system_prompt}"},
            {"role": "user", "content": user_msg}
        ]

    def _call_llm(self, messages: List[Dict], temperature: float = 0.4) -> str:
        """调用大模型"""
        try:
            response = self.client.chat.completions.create(
                model=os.getenv("MODEL_NAME", "qwen-max"),
                messages=messages,
                temperature=temperature,
                max_tokens=500,
                top_p=0.8
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"大模型调用失败: {str(e)}")
            # 智能回退系统 - 根据用户消息内容生成不同的回复
            return self._generate_fallback_response(messages[-1]['content'] if messages else "")

    def _generate_fallback_response(self, user_message: str) -> str:
        """生成智能回退回复"""
        import random

        # 关键词匹配生成不同回复
        user_message_lower = user_message.lower()

        # 价格相关
        if any(keyword in user_message_lower for keyword in ['价格', '价', '便宜', '贵', '多少钱', '砍价']):
            responses = [
                "您好！商品价格已经是最优惠的了，质量保证，现货速发。",
                "这款商品性价比很高，价格已经是最低了，包邮哦。",
                "价格很实惠了，正品保证，可以放心购买。"
            ]
        # 技术相关
        elif any(keyword in user_message_lower for keyword in ['参数', '规格', '型号', '配置', '功能']):
            responses = [
                "商品详情页面有完整的参数信息，您可以查看一下。",
                "这是全新正品，具体参数请参考商品描述页面。",
                "商品参数齐全，都是官方正品配置。"
            ]
        # 发货相关
        elif any(keyword in user_message_lower for keyword in ['发货', '快递', '物流', '多久', '时间']):
            responses = [
                "现货速发，一般24小时内发货，快递时效2-3天。",
                "今天下单今天发，快递时效2-3天左右。",
                "现货立即发货，快递时效2-3天，偏远地区稍长。"
            ]
        # 质量相关
        elif any(keyword in user_message_lower for keyword in ['质量', '正品', '真假', '保修', '售后']):
            responses = [
                "全新正品，质量保证，支持验货。",
                "都是官方正品，质量有保障，支持售后。",
                "正品保证，质量可靠，可以放心购买。"
            ]
        # 默认回复
        else:
            responses = [
                "您好！我是闲鱼客服助手，很高兴为您服务。",
                "有什么可以帮助您的吗？商品都是全新正品。",
                "您好！商品都是现货，有什么问题可以问我。"
            ]

        return random.choice(responses)


class PriceAgent(BaseAgent):
    """议价处理Agent"""

    def generate(self, user_msg: str, item_desc: str, context: str, bargain_count: int = 0) -> str:
        """重写生成逻辑"""
        dynamic_temp = self._calc_temperature(bargain_count)
        messages = self._build_messages(user_msg, item_desc, context)
        messages[0]['content'] += f"\n▲当前议价轮次：{bargain_count}"

        try:
            response = self.client.chat.completions.create(
                model=os.getenv("MODEL_NAME", "qwen-max"),
                messages=messages,
                temperature=dynamic_temp,
                max_tokens=500,
                top_p=0.8
            )
            return self.safety_filter(response.choices[0].message.content)
        except Exception as e:
            logger.error(f"议价Agent大模型调用失败: {str(e)}")
            # 使用智能回退系统
            return self.safety_filter(self._generate_fallback_response(user_msg))

    def _calc_temperature(self, bargain_count: int) -> float:
        """动态温度策略"""
        return min(0.3 + bargain_count * 0.15, 0.9)


class TechAgent(BaseAgent):
    """技术咨询Agent"""

    def generate(self, user_msg: str, item_desc: str, context: str, bargain_count: int = 0) -> str:
        """重写生成逻辑"""
        messages = self._build_messages(user_msg, item_desc, context)

        try:
            response = self.client.chat.completions.create(
                model=os.getenv("MODEL_NAME", "qwen-max"),
                messages=messages,
                temperature=0.4,
                max_tokens=500,
                top_p=0.8,
                extra_body={
                    "enable_search": True,
                }
            )
            return self.safety_filter(response.choices[0].message.content)
        except Exception as e:
            logger.error(f"技术Agent大模型调用失败: {str(e)}")
            # 使用智能回退系统
            return self.safety_filter(self._generate_fallback_response(user_msg))


class ClassifyAgent(BaseAgent):
    """意图识别Agent"""

    def generate(self, **args) -> str:
        response = super().generate(**args)
        return response


class DefaultAgent(BaseAgent):
    """默认处理Agent"""

    def _call_llm(self, messages: List[Dict], *args) -> str:
        """限制默认回复长度"""
        response = super()._call_llm(messages, temperature=0.7)
        return response