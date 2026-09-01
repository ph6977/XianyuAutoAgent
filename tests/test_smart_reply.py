#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试修复后的智能回复管理器
"""

import sys
import os

# 添加项目路径
sys.path.append('.')

from xianyu_bot_components.关键问题回复.smart_reply_manager import SmartReplyManager

def test_smart_reply_manager():
    """测试智能回复管理器"""
    print("测试修复后的智能回复管理器...")
    
    manager = SmartReplyManager()
    
    print('智能回复管理器Agent状态:')
    status = manager.get_agent_status()
    for agent_name, is_active in status.items():
        print(f'  {agent_name}: {is_active}')
    
    # 检查租赁顾问Agent是否有飞书读取器
    if '智能租赁顾问Agent' in manager.agents:
        agent = manager.agents['智能租赁顾问Agent']
        print(f'\n租赁顾问Agent飞书读取器状态: {agent.feishu_reader is not None}')
        
        # 测试位置查询
        print('\n测试位置查询功能...')
        if agent.feishu_reader:
            devices = agent.feishu_reader.find_devices_by_location('南京')
            print(f'南京设备数量: {len(devices)}')
            for device in devices:
                print(f'  - {device["name"]} ({device["location"]})')
        else:
            print('飞书读取器未初始化')
    
    # 测试处理消息
    print('\n测试消息处理...')
    replies = manager.process_message("南京有机型可以使用吗", "user123", "1002962108247", "测试上下文")
    print(f'回复数量: {len(replies)}')
    for i, reply in enumerate(replies, 1):
        print(f'回复{i}: {reply}')

if __name__ == "__main__":
    test_smart_reply_manager()