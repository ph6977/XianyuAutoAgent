#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试修复后的飞书位置查询功能
"""

import os
from dotenv import load_dotenv
from feishu_knowledge_base.feishu_sheet_reader import FeishuSheetReader

# 加载环境变量
load_dotenv()

def test_location_query():
    """测试位置查询功能"""
    print("测试修复后的飞书位置查询功能...")
    
    # 初始化飞书读取器
    reader = FeishuSheetReader(
        os.getenv('FEISHU_APP_ID'),
        os.getenv('FEISHU_APP_SECRET'), 
        os.getenv('FEISHU_SPREADSHEET_TOKEN'),
        os.getenv('FEISHU_SHEET_ID')
    )
    
    # 测试查询南京设备
    print('\n测试查询南京设备...')
    devices_in_nanjing = reader.find_devices_by_location('南京')
    print(f'南京设备数量: {len(devices_in_nanjing)}')
    for device in devices_in_nanjing:
        print(f'  - {device["name"]} ({device["location"]})')

    # 测试查询佛山设备
    print('\n测试查询佛山设备...')
    devices_in_foshan = reader.find_devices_by_location('佛山') 
    print(f'佛山设备数量: {len(devices_in_foshan)}')
    for device in devices_in_foshan:
        print(f'  - {device["name"]} ({device["location"]})')
    
    # 测试查询东莞设备
    print('\n测试查询东莞设备...')
    devices_in_dongguan = reader.find_devices_by_location('东莞') 
    print(f'东莞设备数量: {len(devices_in_dongguan)}')
    for device in devices_in_dongguan:
        print(f'  - {device["name"]} ({device["location"]})')

if __name__ == "__main__":
    test_location_query()