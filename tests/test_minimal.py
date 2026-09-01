#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
最小化测试 - 验证核心功能
"""

import sys
import os
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 加载环境变量
from dotenv import load_dotenv
load_dotenv(os.path.join(project_root, '.env'))

from loguru import logger


def test_basic_setup():
    """测试基础设置"""
    logger.info("测试基础设置...")
    
    # 检查环境变量
    api_key = os.getenv("API_KEY")
    if api_key:
        logger.success("API_KEY已加载")
    else:
        logger.error("API_KEY未找到")
        return False
    
    cookies_str = os.getenv("COOKIES_STR")
    if cookies_str:
        logger.success("COOKIES_STR已加载")
    else:
        logger.error("COOKIES_STR未找到")
        return False
    
    return True


def test_llm_connection():
    """测试LLM连接"""
    logger.info("测试LLM连接...")
    
    try:
        from openai import OpenAI
        
        client = OpenAI(
            api_key=os.getenv("API_KEY"),
            base_url=os.getenv("MODEL_BASE_URL", "https://api.deepseek.com")
        )
        
        # 发送一个简单的测试请求
        response = client.chat.completions.create(
            model=os.getenv("MODEL_NAME", "deepseek-chat"),
            messages=[
                {"role": "user", "content": "你好"}
            ],
            max_tokens=50
        )
        
        reply = response.choices[0].message.content
        logger.success(f"LLM响应: {reply}")
        return True
        
    except Exception as e:
        logger.error(f"LLM连接失败: {e}")
        return False


def test_intent_analyzer():
    """测试意图分析器"""
    logger.info("测试意图分析器...")
    
    try:
        from src.intelligence.intent_analyzer import IntentAnalyzer
        
        analyzer = IntentAnalyzer()
        
        # 测试一个问题
        question = "南京有吗"
        agents, reason = analyzer.analyze_intent(question)
        
        logger.info(f"问题: {question}")
        logger.info(f"匹配的Agent: {agents}")
        logger.info(f"原因: {reason}")
        
        return True
        
    except Exception as e:
        logger.error(f"意图分析器测试失败: {e}")
        return False


def main():
    """主函数"""
    logger.info("=" * 50)
    logger.info("开始最小化测试")
    logger.info("=" * 50)
    
    all_passed = True
    
    # 测试基础设置
    if not test_basic_setup():
        all_passed = False
    print("\n" + "-" * 50 + "\n")
    
    # 测试LLM连接
    if not test_llm_connection():
        all_passed = False
    print("\n" + "-" * 50 + "\n")
    
    # 测试意图分析器
    if not test_intent_analyzer():
        all_passed = False
    print("\n" + "=" * 50 + "\n")
    
    if all_passed:
        logger.success("所有测试通过！")
    else:
        logger.error("部分测试失败！")


if __name__ == "__main__":
    main()