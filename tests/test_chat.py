#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
聊天测试 - 验证智能回复功能
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

from src.agents.xianyu_agent import XianyuReplyBot
from src.intelligence.intent_analyzer import IntentAnalyzer
from loguru import logger


def test_intent_analyzer():
    """测试意图分析器"""
    logger.info("测试意图分析器...")
    
    analyzer = IntentAnalyzer()
    
    test_questions = [
        "南京有吗",
        "10月怎么样",
        "RTK设备多少钱",
        "怎么租",
        "你好",
        "东莞的设备什么时候有空"
    ]
    
    for question in test_questions:
        try:
            result = analyzer.analyze_intent(question)
            logger.info(f"问题: {question}")
            logger.info(f"意图: {result.get('intent', 'unknown')}")
            logger.info(f"实体: {result.get('entities', {})}")
            logger.info("-" * 40)
        except Exception as e:
            logger.error(f"分析失败: {question} - {e}")
    
    logger.success("意图分析器测试完成")


def test_reply_bot():
    """测试回复机器人"""
    logger.info("测试回复机器人...")
    
    try:
        bot = XianyuReplyBot()
        
        test_messages = [
            "南京有吗",
            "10月怎么样",
            "RTK设备多少钱",
            "你好"
        ]
        
        for message in test_messages:
            try:
                # 模拟用户消息
                reply = bot.process_message(message, user_id="test_user", chat_id="test_chat")
                logger.info(f"用户: {message}")
                logger.info(f"机器人: {reply}")
                logger.info("-" * 40)
            except Exception as e:
                logger.error(f"回复失败: {message} - {e}")
        
        logger.success("回复机器人测试完成")
        
    except Exception as e:
        logger.error(f"初始化回复机器人失败: {e}")


def main():
    """主函数"""
    logger.info("=" * 50)
    logger.info("开始聊天功能测试")
    logger.info("=" * 50)
    
    # 测试意图分析
    test_intent_analyzer()
    print("\n" + "=" * 50 + "\n")
    
    # 测试回复机器人
    test_reply_bot()
    print("\n" + "=" * 50 + "\n")
    
    logger.success("聊天功能测试完成！")


if __name__ == "__main__":
    main()