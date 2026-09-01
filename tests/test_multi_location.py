#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""测试多位置功能"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from context_manager_clean import ChatContextManager

def test_multi_location():
    print("测试多位置功能")
    print("=" * 40)
    
    # 初始化上下文管理器
    context_manager = ChatContextManager()
    
    user_id = "test_user"
    chat_id = "test_chat"
    
    # 测试存储多个位置
    print("1. 测试存储多个位置")
    locations = ["南京", "佛山", "重庆"]
    context_manager.store_multiple_locations(user_id, chat_id, locations)
    print(f"存储位置: {locations}")
    
    # 测试获取位置列表
    print("\n2. 测试获取位置列表")
    stored_locations = context_manager.get_location_list(user_id, chat_id)
    print(f"获取位置列表: {stored_locations}")
    
    # 测试检测位置歧义
    print("\n3. 测试检测位置歧义")
    has_ambiguity = context_manager.detect_location_ambiguity(user_id, chat_id)
    print(f"检测到位置歧义: {has_ambiguity}")
    
    # 测试获取最新位置
    print("\n4. 测试获取最新位置")
    latest_location = context_manager.get_latest_location(user_id, chat_id)
    print(f"最新位置: {latest_location}")
    
    print("\n测试完成!")

if __name__ == "__main__":
    test_multi_location()