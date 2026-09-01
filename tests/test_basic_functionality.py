#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
基础功能测试
"""

import sys
import os
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 加载环境变量
from dotenv import load_dotenv
load_dotenv(os.path.join(project_root, 'config', '.env'))

from src.agents.rental_consultant import RentalConsultantAgent
from src.intelligence.intent_analyzer import IntentAnalyzer
from loguru import logger


def test_rental_consultant():
    """测试租赁顾问"""
    logger.info("测试租赁顾问功能...")
    
    # RentalConsultantAgent需要client参数，这里传入None
    consultant = RentalConsultantAgent(None, "")
    
    # 测试设备查询
    result = consultant.check_device_availability("南京", "2025-01-01")
    logger.info(f"南京设备查询结果: {result}")
    
    # 测试日期查询
    result = consultant.check_date_availability("南京", "RTK设备")
    logger.info(f"南京日期查询结果: {result}")
    
    # 测试综合查询
    result = consultant.comprehensive_availability_query("南京", "RTK设备", "2025-01-01")
    logger.info(f"南京综合查询结果: {result}")
    
    logger.success("租赁顾问测试完成")


def test_intent_analyzer():
    """测试意图分析器"""
    logger.info("测试意图分析器功能...")
    
    analyzer = IntentAnalyzer()
    
    # 测试各种意图
    test_cases = [
        ("南京有吗", "location"),
        ("10月怎么样", "date"),
        ("RTK设备多少钱", "price"),
        ("怎么租", "process"),
        ("你好", "greeting")
    ]
    
    for question, expected_intent in test_cases:
        result = analyzer.analyze_intent(question)
        logger.info(f"问题: {question}")
        logger.info(f"预期意图: {expected_intent}, 实际结果: {result}")
    
    logger.success("意图分析器测试完成")


def main():
    """主函数"""
    logger.info("=" * 50)
    logger.info("开始基础功能测试")
    logger.info("=" * 50)
    
    try:
        test_rental_consultant()
        print("\n" + "=" * 50 + "\n")
        test_intent_analyzer()
        logger.success("所有测试完成")
    except Exception as e:
        logger.error(f"测试失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()