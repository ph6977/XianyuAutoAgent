#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试月份查询优化
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

def test_month_query():
    """测试月份查询"""
    print("="*50)
    print("测试月份查询优化")
    print("="*50)
    
    # 初始化
    client = OpenAI(
        api_key=os.getenv("API_KEY") or os.getenv("DEEPSEEK_API_KEY"),
        base_url=os.getenv("MODEL_BASE_URL", "https://api.deepseek.com")
    )
    system_prompt = "你是一个设备租赁顾问"
    agent = RentalConsultantAgent(client, system_prompt)
    
    # 模拟用户消息
    user_message = "佛山10月有吗"
    item_description = "设备租赁"
    context = ""
    user_id = "test_user"
    chat_id = "test_chat"
    
    # 分析意图
    print("\n1. 分析用户意图...")
    intent_result = agent._analyze_user_intent(user_message, item_description, context, user_id, chat_id)
    print(f"   意图类型: {intent_result.get('intent_type')}")
    print(f"   提取信息: {intent_result.get('extracted_info')}")
    
    # 处理查询
    print("\n2. 处理查询...")
    reply = agent._handle_comprehensive_availability(intent_result, item_description, context, user_message)
    
    # 只显示回复的前500个字符
    print(f"\n机器人回复（前500字符）:\n{reply[:500]}")
    
    # 检查回复是否包含多个日期
    if "📅" in reply and reply.count("📅") > 1:
        print(f"\n✅ 测试通过：展示了{reply.count('📅')}个日期的设备信息")
    elif "总共" in reply and "天有设备可租" in reply:
        # 提取天数
        import re
        match = re.search(r'总共(\d+)天有设备可租', reply)
        if match:
            days = match.group(1)
            print(f"\n✅ 测试通过：展示了{days}天的汇总信息")
        else:
            print("\n✅ 测试通过：展示了月份汇总信息")
    else:
        print("\n⚠️ 可能还是只展示了一天")

if __name__ == "__main__":
    test_month_query()