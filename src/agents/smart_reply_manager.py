#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
关键问题回复系统 - 智能回复管理器
集成意图分析器和现有Agent，实现精准回复
"""

import os
import sys
from typing import Dict, List, Optional
from loguru import logger

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from .intent_analyzer import IntentAnalyzer
from src.agents.rental_consultant_agent import RentalConsultantAgent
from src.utils.sensitive_keywords import SensitiveKeywordDetector


class SmartReplyManager:
    """智能回复管理器"""
    
    def __init__(self, config_path: str = None, context_manager=None):
        """初始化智能回复管理器"""
        # 初始化意图分析器，传递上下文管理器
        self.context_manager = context_manager
        self.intent_analyzer = IntentAnalyzer(config_path, context_manager)
        
        # 初始化敏感词检测器
        self.sensitive_detector = SensitiveKeywordDetector()
        
        # 初始化Agent
        self.agents = self._init_agents()
        
        logger.info("智能回复管理器初始化完成")
    
    def _init_agents(self) -> Dict[str, object]:
        """初始化所有Agent"""
        agents = {}
        
        try:
            # 初始化智能租赁顾问Agent（使用默认参数）
            from openai import OpenAI
            client = OpenAI(
                api_key=os.getenv("API_KEY"),
                base_url=os.getenv("MODEL_BASE_URL", "https://api.deepseek.com")
            )
            
            # 创建简单的系统提示词
            rental_prompt = "你是一个专业的租赁顾问，为用户提供手机、相机租赁咨询服务。"
            shipping_prompt = "你是一个专业的快递时间查询顾问，为用户提供物流配送时间查询服务。"
            
            # 简单的安全过滤器
            def simple_safety_filter(text):
                return text  # 简单实现，实际应用中需要更复杂的过滤
            
            # 创建飞书读取器（如果需要）
            feishu_reader = None
            try:
                from src.knowledge.feishu_sheet_reader import FeishuSheetReader
                # 从环境变量获取配置
                app_id = os.getenv("FEISHU_APP_ID")
                app_secret = os.getenv("FEISHU_APP_SECRET")
                spreadsheet_token = os.getenv("FEISHU_SPREADSHEET_TOKEN")
                sheet_id = os.getenv("FEISHU_SHEET_ID")
                
                if app_id and app_secret and spreadsheet_token and sheet_id:
                    feishu_reader = FeishuSheetReader(app_id, app_secret, spreadsheet_token, sheet_id)
                    logger.info("飞书读取器初始化成功")
                else:
                    logger.warning("飞书API配置不完整，将使用基本功能")
            except Exception as e:
                logger.warning(f"飞书读取器初始化失败: {e}，将使用基本功能")
            
            # 初始化智能租赁顾问Agent
            agents['智能租赁顾问Agent'] = RentalConsultantAgent(
                client=client,
                system_prompt=rental_prompt,
                safety_filter=simple_safety_filter,
                feishu_reader=feishu_reader,
                context_manager=self.context_manager  # 传递上下文管理器
            )
            logger.info("智能租赁顾问Agent初始化成功")
            
            # 快递时间查询Agent暂时不可用
            logger.info("快递时间查询Agent将在后续版本中实现")
            
        except Exception as e:
            logger.error(f"Agent初始化失败: {e}")
        
        return agents
    
    def process_message(self, user_message: str, user_id: str = None, 
                       item_id: str = None, context: str = None, chat_id: str = None) -> List[str]:
        """
        处理用户消息
        
        Args:
            user_message: 用户消息
            user_id: 用户ID
            item_id: 商品ID
            context: 上下文信息
            chat_id: 聊天ID
            
        Returns:
            List[str]: 回复消息列表（空列表表示静默不回复）
        """
        try:
            # 0. 首先检测是否包含敏感词
            is_sensitive, detected_keywords = self.sensitive_detector.is_sensitive_message(user_message)
            if is_sensitive:
                logger.info(f"检测到敏感词，跳过AI回复，转人工处理: {detected_keywords}")
                # 返回空列表，表示不自动回复，让系统转人工
                return []
            
            # 1. 意图分析（传递上下文、用户ID和聊天ID）
            matched_agents, reason = self.intent_analyzer.analyze_intent(user_message, context, user_id, chat_id)
            
            # 2. 如果没有匹配的Agent，返回空列表（静默）
            if not matched_agents:
                logger.info(f"用户问题不相关，静默处理: {user_message}")
                return []
            
            # 3. 调用匹配的Agent生成回复
            replies = []
            
            for agent_name in matched_agents:
                if agent_name in self.agents:
                    agent = self.agents[agent_name]
                    
                    try:
                        # 调用Agent生成回复
                        if agent_name == '智能租赁顾问Agent':
                            reply = self._call_rental_agent(agent, user_message, item_id, context, user_id, chat_id)
                        elif agent_name == '快递时间查询Agent':
                            reply = self._call_shipping_agent(agent, user_message, context)
                        else:
                            logger.warning(f"未知的Agent类型: {agent_name}")
                            continue
                        
                        if reply:
                            replies.append(reply)
                            logger.info(f"{agent_name} 生成回复: {reply}")
                    
                    except Exception as e:
                        logger.error(f"调用 {agent_name} 失败: {e}")
            
            return replies
            
        except Exception as e:
            logger.error(f"处理消息时出错: {e}")
            return []
    
    def _call_rental_agent(self, agent, user_message: str, item_id: str = None, 
                          context: str = None, user_id: str = None, chat_id: str = None) -> Optional[str]:
        """调用租赁顾问Agent"""
        try:
            # 构建简洁的商品描述，不包含敏感技术信息
            item_description = ""
            if item_id:
                item_description = f"商品ID: {item_id}"
            # 不再将上下文信息传递给Agent，避免信息泄露
            
            # 调用Agent的generate方法，传递用户ID和聊天ID
            reply = agent.generate(user_message, item_description, context or "", user_id, chat_id)
            return reply
            
        except Exception as e:
            logger.error(f"调用租赁顾问Agent失败: {e}")
            return None
    
    def _call_shipping_agent(self, agent, user_message: str, 
                           context: str = None) -> Optional[str]:
        """调用快递时间查询Agent"""
        try:
            # 构建商品描述
            item_description = context or ""
            
            # 调用Agent的generate方法
            reply = agent.generate(user_message, item_description, context or "")
            return reply
            
        except Exception as e:
            logger.error(f"调用快递时间查询Agent失败: {e}")
            return None
    
    def reload_config(self):
        """重新加载配置"""
        self.intent_analyzer.reload_config()
        logger.info("智能回复管理器配置已重新加载")
    
    def get_agent_status(self) -> Dict[str, bool]:
        """获取Agent状态"""
        status = {}
        for agent_name, agent in self.agents.items():
            try:
                # 简单的健康检查
                status[agent_name] = agent is not None
            except Exception:
                status[agent_name] = False
        return status


# 测试代码
if __name__ == "__main__":
    manager = SmartReplyManager()
    
    # 测试消息
    test_messages = [
        ("我想租一个相机", "user123", "camera_001", "用户询问相机租赁"),
        ("我的快递什么时候到", "user456", None, "用户询问快递时间"),
        ("今天天气怎么样", "user789", None, "无关问题"),
        ("你们有手机出租吗", "user101", "phone_002", "用户询问手机租赁"),
        ("物流信息怎么查", "user202", None, "用户询问物流查询")
    ]
    
    for message, user_id, item_id, context in test_messages:
        replies = manager.process_message(message, user_id, item_id, context)
        print(f"问题: {message}")
        print(f"回复数量: {len(replies)}")
        for i, reply in enumerate(replies, 1):
            print(f"回复{i}: {reply}")
        print("-" * 50)