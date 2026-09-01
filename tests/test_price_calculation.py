#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""测试价格计算功能"""

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

def test_price_calculation():
    """测试价格计算"""
    # 初始化OpenAI客户端
    client = OpenAI(
        api_key=os.getenv("API_KEY") or os.getenv("DEEPSEEK_API_KEY"),
        base_url=os.getenv("MODEL_BASE_URL", "https://api.deepseek.com")
    )
    
    # 系统提示词
    system_prompt = """你是一个专业的设备租赁顾问，为用户提供设备租赁咨询服务。"""
    
    # 创建租赁顾问
    agent = RentalConsultantAgent(client, system_prompt)
    
    # 测试胖卡4-002租3天的价格
    device_model = "胖卡4-002"
    rental_days = 3
    
    price_info = agent._calculate_rental_price(device_model, rental_days)
    
    print("=" * 50)
    print("价格计算测试")
    print("=" * 50)
    print(f"设备型号: {price_info['device_model']}")
    print(f"租赁天数: {price_info['rental_days']}天")
    print(f"适用档位: {price_info['applicable_pricing_tier']}")
    print(f"每日单价: {price_info['daily_price']}元")
    print(f"总价: {price_info['total_price']}元")
    print("=" * 50)
    
    # 验证计算是否正确
    expected_price = 120 * 3  # 3天档位单价120元
    if price_info['total_price'] == expected_price:
        print("[OK] 测试通过：价格计算正确！")
    else:
        print(f"[ERROR] 测试失败：期望价格{expected_price}元，实际价格{price_info['total_price']}元")
    
    # 测试其他天数
    print("\n其他天数测试：")
    for days in [1, 2, 5, 7, 10, 15, 30]:
        price_info = agent._calculate_rental_price("胖卡4-002", days)
        print(f"{days}天: {price_info['daily_price']}元/天 × {days}天 = {price_info['total_price']}元")

if __name__ == "__main__":
    test_price_calculation()