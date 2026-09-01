#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试修复后的用户昵称提取功能
"""

import time
from crawler_components.tools.batch_user_crawler import BatchUserCrawler

def test_nickname_extraction():
    """测试用户昵称提取功能"""
    crawler = BatchUserCrawler(headless=False)  # 使用有头模式以便观察

    try:
        print("初始化浏览器...")
        if not crawler.init_browser():
            print("浏览器初始化失败")
            return False

        print("登录并导航到闲鱼聊天页面...")
        if not crawler.login_and_navigate():
            print("登录和导航失败")
            return False

        print("开始测试用户昵称提取...")
        user_nicknames = crawler._get_chat_list_users(max_users=10)

        print(f"成功提取到 {len(user_nicknames)} 个用户昵称:")
        for i, nickname in enumerate(user_nicknames, 1):
            print(f"  {i}. {nickname}")

        if user_nicknames:
            print("✅ 用户昵称提取功能修复成功！")
            return True
        else:
            print("❌ 仍未能提取到任何用户昵称")
            return False

    except Exception as e:
        print(f"测试过程中出现错误: {e}")
        import traceback
        traceback.print_exc()
        return False

    finally:
        # 不关闭浏览器，以便观察结果
        print("\n浏览器保持打开状态，您可以手动检查页面...")

if __name__ == "__main__":
    test_nickname_extraction()