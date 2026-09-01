#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简单测试 - 验证项目结构是否正确
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

from loguru import logger


def test_imports():
    """测试所有模块是否可以正常导入"""
    logger.info("测试模块导入...")
    
    try:
        # 测试核心模块
        from src.core.xianyu_bot import XianyuBot
        from src.core.xianyu_client import XianyuClient
        from src.core.context_manager import ChatContextManager
        logger.success("核心模块导入成功")
        
        # 测试智能模块
        from src.intelligence.intent_analyzer import IntentAnalyzer
        from src.intelligence.smart_reply_manager import SmartReplyManager
        logger.success("智能模块导入成功")
        
        # 测试代理模块
        from src.agents.xianyu_agent import XianyuReplyBot
        from src.agents.rental_consultant import RentalConsultantAgent
        logger.success("代理模块导入成功")
        
        # 测试工具模块
        from src.utils.xianyu_apis import XianyuApis
        from src.utils.xianyu_utils import generate_device_id
        from src.utils.sensitive_keywords import SensitiveKeywordDetector
        logger.success("工具模块导入成功")
        
        logger.success("所有模块导入成功！")
        return True
        
    except Exception as e:
        logger.error(f"模块导入失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_config():
    """测试配置文件"""
    logger.info("测试配置文件...")
    
    # 检查环境变量
    api_key = os.getenv("API_KEY")
    cookies_str = os.getenv("COOKIES_STR")
    
    if api_key:
        logger.success(f"API_KEY已加载: {api_key[:10]}...")
    else:
        logger.warning("API_KEY未找到")
    
    if cookies_str:
        logger.success(f"COOKIES_STR已加载: 长度={len(cookies_str)}")
    else:
        logger.warning("COOKIES_STR未找到")
    
    # 检查配置文件
    config_files = [
        "config/.env",
        "config/agent_config.md",
        "config/product_mapping.json",
        "config/requirements.txt"
    ]
    
    for file_path in config_files:
        full_path = project_root / file_path
        if full_path.exists():
            logger.success(f"配置文件存在: {file_path}")
        else:
            logger.warning(f"配置文件缺失: {file_path}")


def main():
    """主函数"""
    logger.info("=" * 50)
    logger.info("开始简单测试")
    logger.info("=" * 50)
    
    # 测试导入
    imports_ok = test_imports()
    print("\n" + "=" * 50 + "\n")
    
    # 测试配置
    test_config()
    print("\n" + "=" * 50 + "\n")
    
    if imports_ok:
        logger.success("项目结构测试通过！")
    else:
        logger.error("项目结构测试失败！")


if __name__ == "__main__":
    main()