#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""测试价格计算说明功能"""

import os
import sys
from datetime import datetime
from openai import OpenAI
from dotenv import load_dotenv

# 添加路径
sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'xianyu_bot_components'))

# 加载环境变量
load_dotenv()

from xianyu_bot_components.agents.rental_consultant_agent import RentalConsultantAgent

def test_price_explanation():
    """测试价格计算说明"""
    # 初始化OpenAI客户端
    client = OpenAI(
        api_key=os.getenv("API_KEY") or os.getenv("DEEPSEEK_API_KEY"),
        base_url=os.getenv("MODEL_BASE_URL", "https://api.deepseek.com")
    )
    
    # 系统提示词
    system_prompt = """你是一个专业的设备租赁顾问，为用户提供设备租赁咨询服务。"""
    
    # 创建租赁顾问
    agent = RentalConsultantAgent(client, system_prompt)
    
    # 模拟用户查询
    user_message = "具体是怎么算的"
    item_description = "胖卡4-002租赁"
    context = "用户之前查询了胖卡4-002在东莞11月12-15日的价格"
    
    # 构建意图分析结果
    intent_analysis = {
        'intent_type': 'general_inquiry',
        'query_strategy': 'comprehensive',
        'context_analysis': '用户询问价格计算方式',
        'extracted_info': {
            'target_devices': ['胖卡4-002'],
            'rental_dates': ['2025-11-12', '2025-11-15'],
            'target_city': '东莞',
            'other_info': '用户意图是询问价格的计算方式或明细'
        },
        'specific_instruction': '解释价格构成'
    }
    
    # 调用处理方法
    reply = agent._handle_general_inquiry(intent_analysis, user_message, item_description, context)
    
    print("=" * 60)
    print("价格计算说明测试")
    print("=" * 60)
    print("用户问题:", user_message)
    print("-" * 60)
    # 只检查关键信息
    if "120元/天" in reply and "360元" in reply:
        print("[OK] 测试通过：价格计算说明正确！")
        print("关键信息：120元/天 × 3天 = 360元")
    else:
        print("[ERROR] 测试失败：价格计算说明有误")
        # 查找价格信息
        import re
        prices = re.findall(r'\d+元/天', reply)
        totals = re.findall(r'总计 \d+元|合计 \d+元|\*\*\d+元\*\*', reply)
        print("找到的单价:", prices)
        print("找到的总价:", totals)
    print("=" * 60)

if __name__ == "__main__":
    test_price_explanation()