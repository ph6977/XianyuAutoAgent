#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简单测试月份查询
"""

import os
import sys
from pathlib import Path

# 添加项目路径
sys.path.append(str(Path(__file__).parent))

from dotenv import load_dotenv
load_dotenv()

from openai import OpenAI
from xianyu_bot_components.agents.rental_consultant_agent import RentalConsultantAgent

# 初始化
client = OpenAI(
    api_key=os.getenv("API_KEY") or os.getenv("DEEPSEEK_API_KEY"),
    base_url=os.getenv("MODEL_BASE_URL", "https://api.deepseek.com")
)
system_prompt = "你是一个设备租赁顾问"
agent = RentalConsultantAgent(client, system_prompt)

# 模拟查询
user_message = "佛山10月有吗"
item_description = "设备租赁"
context = ""
user_id = "test_user"
chat_id = "test_chat"

print(f"测试消息: {user_message}")

# 分析意图
intent_result = agent._analyze_user_intent(user_message, item_description, context, user_id, chat_id)
rental_dates = intent_result.get('extracted_info', {}).get('rental_dates', '')
target_city = intent_result.get('extracted_info', {}).get('target_city', '')

print(f"\n解析结果:")
print(f"  城市: {target_city}")
print(f"  日期: {rental_dates}")

# 处理查询
reply = agent._handle_comprehensive_availability(intent_result, item_description, context, user_message)

# 显示回复
print("\n" + "="*50)
print("机器人回复:")
print("="*50)
print(reply)