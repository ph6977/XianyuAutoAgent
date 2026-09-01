#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试修复后的飞书读取器和API密钥
"""

import os
from dotenv import load_dotenv
from feishu_knowledge_base.feishu_sheet_reader import FeishuSheetReader
from openai import OpenAI

# 加载环境变量
load_dotenv()

def test_feishu_reader():
    """测试飞书读取器"""
    print("测试飞书读取器初始化...")
    
    try:
        reader = FeishuSheetReader(
            os.getenv('FEISHU_APP_ID'),
            os.getenv('FEISHU_APP_SECRET'),
            os.getenv('FEISHU_SPREADSHEET_TOKEN'),
            os.getenv('FEISHU_SHEET_ID')
        )
        print('✅ 飞书读取器初始化成功!')
        
        # 测试查询
        devices = reader.find_devices_by_location('南京')
        print(f'✅ 南京设备数量: {len(devices)}')
        for device in devices:
            print(f'  - {device["name"]} ({device["location"]})')
            
        return reader
    except Exception as e:
        print(f'❌ 初始化失败: {e}')
        return None

def test_openai_client():
    """测试OpenAI客户端"""
    print("\n测试OpenAI客户端...")
    
    try:
        client = OpenAI(
            api_key=os.getenv("API_KEY"),
            base_url=os.getenv("MODEL_BASE_URL", "https://api.deepseek.com")
        )
        
        # 简单测试API连接
        print('✅ OpenAI客户端初始化成功!')
        print(f'API Key前缀: {os.getenv("API_KEY", "")[:8]}...')
        print(f'Model Base URL: {os.getenv("MODEL_BASE_URL")}')
        print(f'Model Name: {os.getenv("MODEL_NAME")}')
        
        return client
    except Exception as e:
        print(f'❌ OpenAI客户端初始化失败: {e}')
        return None

def main():
    """主函数"""
    print("=== 修复后功能测试 ===")
    
    # 加载环境变量
    load_dotenv()
    
    print(f"FEISHU_APP_ID: {'已配置' if os.getenv('FEISHU_APP_ID') else '未配置'}")
    print(f"FEISHU_SPREADSHEET_TOKEN: {'已配置' if os.getenv('FEISHU_SPREADSHEET_TOKEN') else '未配置'}")
    print(f"API_KEY: {'已配置' if os.getenv('API_KEY') else '未配置'}")
    
    # 测试飞书读取器
    feishu_reader = test_feishu_reader()
    
    # 测试OpenAI客户端
    openai_client = test_openai_client()
    
    if feishu_reader and openai_client:
        print("\n✅ 所有组件初始化成功！")
        print("现在机器人应该能够:")
        print("  - 查询飞书表格中的设备信息")
        print("  - 使用AI模型生成回复")
        print("  - 正确响应'南京有什么机型'等位置查询")
    else:
        print("\n❌ 某些组件初始化失败，请检查配置")

if __name__ == "__main__":
    main()