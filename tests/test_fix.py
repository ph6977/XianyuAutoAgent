#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试修复后的查询逻辑
"""

import os
import sys
from pathlib import Path

# 添加项目路径
sys.path.append(str(Path(__file__).parent))

from dotenv import load_dotenv
load_dotenv()

from xianyu_bot_components.agents.rental_consultant_agent import RentalConsultantAgent
from xianyu_bot_components.core.context_manager import ChatContextManager
from openai import OpenAI

def test_city_query():
    """测试城市查询"""
    print("="*50)
    print("测试城市查询修复")
    print("="*50)
    
    # 初始化
    client = OpenAI(
        api_key=os.getenv("API_KEY") or os.getenv("DEEPSEEK_API_KEY"),
        base_url=os.getenv("MODEL_BASE_URL", "https://api.deepseek.com")
    )
    system_prompt = "你是一个设备租赁顾问"
    agent = RentalConsultantAgent(client, system_prompt)
    context_manager = ChatContextManager()
    
    # 模拟用户ID和聊天ID
    user_id = "test_user_001"
    chat_id = "test_chat_001"
    
    # 1. 先存储一个设备到上下文（模拟之前的对话）
    print("\n1. 存储上下文：胖卡4-010在东莞")
    context_manager.store_entity(user_id, chat_id, "device_type", "胖卡4-010")
    context_manager.store_entity(user_id, chat_id, "location", "东莞")
    
    # 2. 查询佛山的设备（用户没有明确提及设备型号）
    print("\n2. 查询佛山的设备")
    user_message = "佛山10月有吗"
    item_description = "设备租赁"
    context = "用户之前询问过东莞的胖卡4-010"
    
    # 分析意图
    intent_result = agent._analyze_user_intent(user_message, item_description, context, user_id, chat_id)
    print(f"意图分析结果: {intent_result}")
    
    # 处理查询
    reply = agent._handle_comprehensive_availability(intent_result, item_description, context, user_message)
    print(f"\n机器人回复: {reply}")
    
    # 3. 检查是否正确查询了佛山的所有设备，而不是被限制为胖卡4-010
    if "佛山" in reply and ("胖卡4-010" not in reply or "暂时没有可出租的设备" in reply):
        print("\n✅ 测试通过：正确查询了佛山的设备，没有被上下文中的设备限制")
    else:
        print("\n❌ 测试失败：仍然被上下文中的设备限制")

if __name__ == "__main__":
    test_city_query()