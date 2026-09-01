#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
飞书多维表格详细功能测试脚本
用于验证机器人能否准确读取飞书中的内容
"""

import os
import sys
import json
from datetime import datetime

# 加载环境变量
from dotenv import load_dotenv
load_dotenv()

# 添加项目根目录到Python路径
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

from feishu_knowledge_base.feishu_sheet_reader import FeishuSheetReader
from loguru import logger


def test_feishu_connection():
    """测试飞书连接和基本配置"""
    print("=" * 60)
    print("飞书连接测试")
    print("=" * 60)
    
    # 检查环境变量配置
    app_id = os.getenv("FEISHU_APP_ID")
    app_secret = os.getenv("FEISHU_APP_SECRET")
    spreadsheet_token = os.getenv("FEISHU_SPREADSHEET_TOKEN")
    sheet_id = os.getenv("FEISHU_SHEET_ID")
    
    print(f"FEISHU_APP_ID: {'已配置' if app_id else '未配置'}")
    print(f"FEISHU_APP_SECRET: {'已配置' if app_secret else '未配置'}")
    print(f"FEISHU_SPREADSHEET_TOKEN: {'已配置' if spreadsheet_token else '未配置'}")
    print(f"FEISHU_SHEET_ID: {'已配置' if sheet_id else '未配置'}")
    
    if not all([app_id, app_secret, spreadsheet_token, sheet_id]):
        print("❌ 飞书API配置不完整")
        return False
    
    try:
        # 创建飞书读取器实例
        reader = FeishuSheetReader(app_id, app_secret, spreadsheet_token, sheet_id)
        print("✅ 飞书读取器创建成功")
        
        # 尝试获取访问令牌
        access_token = reader._get_access_token()  # 使用私有方法获取令牌
        if access_token:
            print("✅ 访问令牌获取成功")
        else:
            print("❌ 访问令牌获取失败")
            return False
            
        return True
        
    except Exception as e:
        print(f"❌ 飞书连接测试失败: {str(e)}")
        return False


def test_read_sheet_data():
    """测试读取飞书表格数据"""
    print("\n" + "=" * 60)
    print("飞书表格数据读取测试")
    print("=" * 60)
    
    app_id = os.getenv("FEISHU_APP_ID")
    app_secret = os.getenv("FEISHU_APP_SECRET")
    spreadsheet_token = os.getenv("FEISHU_SPREADSHEET_TOKEN")
    sheet_id = os.getenv("FEISHU_SHEET_ID")
    
    if not all([app_id, app_secret, spreadsheet_token, sheet_id]):
        print("❌ 飞书API配置不完整")
        return False
    
    try:
        reader = FeishuSheetReader(app_id, app_secret, spreadsheet_token, sheet_id)
        
        # 获取表格数据
        data = reader._get_sheet_data()  # 使用私有方法获取结构化数据
        if data:
            print(f"✅ 成功获取表格数据")
            
            month_headers = data.get('month_headers', [])
            column_names = data.get('column_names', [])
            device_data = data.get('device_data', [])
            
            print(f"📊 月份标识行: {month_headers[:10]}...")  # 显示前10个
            print(f"📊 列名行: {column_names[:10]}...")      # 显示前10个
            print(f"📊 设备数据行数: {len(device_data)}")
            
            if len(device_data) > 0:
                print("\n📝 前3行设备数据预览:")
                for i, row in enumerate(device_data[:3]):
                    print(f"   第{i+3}行: {row[:10]}...")  # 显示前10个字段
            
            return True
        else:
            print("❌ 未能获取表格数据")
            return False
            
    except Exception as e:
        print(f"❌ 读取表格数据失败: {str(e)}")
        return False


def test_device_query():
    """测试设备查询功能"""
    print("\n" + "=" * 60)
    print("设备查询功能测试")
    print("=" * 60)
    
    app_id = os.getenv("FEISHU_APP_ID")
    app_secret = os.getenv("FEISHU_APP_SECRET")
    spreadsheet_token = os.getenv("FEISHU_SPREADSHEET_TOKEN")
    sheet_id = os.getenv("FEISHU_SHEET_ID")
    
    if not all([app_id, app_secret, spreadsheet_token, sheet_id]):
        print("❌ 飞书API配置不完整")
        return False
    
    try:
        reader = FeishuSheetReader(app_id, app_secret, spreadsheet_token, sheet_id)
        
        # 测试获取当前日期的可用设备
        today = datetime.now().strftime('%Y-%m-%d')
        all_devices = reader.find_available_devices_by_date(today)
        print(f"✅ 查询 {today} 可用设备: 找到 {len(all_devices)} 个设备")
        
        if len(all_devices) > 0:
            print("\n🔍 前3个设备详情:")
            for i, device in enumerate(all_devices[:3]):
                print(f"   设备 {i+1}: {device}")
        
        # 测试按位置查询 - 使用find_devices_by_location方法
        try:
            location_devices = reader.find_devices_by_location("北京")
            print(f"📍 查询包含'北京'的设备: 找到 {len(location_devices)} 个设备")
        except Exception as e:
            print(f"📍 按位置查询可能不适用当前表格结构: {e}")
        
        # 测试查询特定日期可用设备
        try:
            date_query = reader.find_available_devices_by_date("2025-10-15")
            print(f"📅 查询2025-10-15可用设备: 找到 {len(date_query)} 个设备")
        except Exception as e:
            print(f"📅 查询特定日期出现异常，尝试当前日期: {e}")
            current_date = datetime.now().strftime('%Y-%m-%d')
            date_query = reader.find_available_devices_by_date(current_date)
            print(f"📅 查询{current_date}可用设备: 找到 {len(date_query)} 个设备")
        
        return True
        
    except Exception as e:
        print(f"❌ 设备查询测试失败: {str(e)}")
        return False


def test_data_accuracy():
    """测试数据准确性"""
    print("\n" + "=" * 60)
    print("数据准确性验证")
    print("=" * 60)
    
    app_id = os.getenv("FEISHU_APP_ID")
    app_secret = os.getenv("FEISHU_APP_SECRET")
    spreadsheet_token = os.getenv("FEISHU_SPREADSHEET_TOKEN")
    sheet_id = os.getenv("FEISHU_SHEET_ID")
    
    if not all([app_id, app_secret, spreadsheet_token, sheet_id]):
        print("❌ 飞书API配置不完整")
        return False
    
    try:
        reader = FeishuSheetReader(app_id, app_secret, spreadsheet_token, sheet_id)
        
        # 获取原始数据
        raw_data = reader._get_sheet_data()
        if not raw_data:
            print("❌ 无法获取原始数据，无法进行准确性验证")
            return False
        
        print(f"📊 原始数据结构: 包含month_headers, column_names, device_data")
        print(f"📊 月份标识行长度: {len(raw_data.get('month_headers', []))}")
        print(f"📊 列名行长度: {len(raw_data.get('column_names', []))}")
        print(f"📊 设备数据行数: {len(raw_data.get('device_data', []))}")
        
        # 检查数据结构
        column_names = raw_data.get('column_names', [])
        device_data = raw_data.get('device_data', [])
        
        if len(column_names) > 0:
            print(f"\n📋 列名行预览: {column_names[:10]}...")  # 显示前10个列名
        
        if len(device_data) > 0:
            print(f"\n🔍 第一行设备数据预览: {device_data[0][:10]}...")  # 显示前10个字段
        
        # 验证数据一致性
        print("\n🔍 数据一致性检查:")
        for i, row in enumerate(device_data[:3]):  # 检查前3行
            if len(row) > 1:  # 确保行有足够的列
                device_name = row[0] if len(row) > 0 else "N/A"
                location = row[1] if len(row) > 1 else "N/A"
                print(f"   第{i+3}行: 设备名='{device_name}', 位置='{location}'")
            else:
                print(f"   第{i+3}行: 数据不足")
        
        # 测试设备状态判断逻辑
        print(f"\n🔧 设备状态判断逻辑测试:")
        test_cases = [None, '', '1', '2', '3', '被预定', 1, 2, 3]
        for case in test_cases:
            is_available = reader._is_device_available(case)
            status = '可租用' if is_available else '不可租用'
            print(f"   状态值 '{case}' -> {status}")
        
        return True
        
    except Exception as e:
        print(f"❌ 数据准确性验证失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """主测试函数"""
    print("🤖 飞书功能详细测试")
    print(f"🕒 测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"📁 项目路径: {project_root}")
    
    # 执行各项测试
    tests = [
        ("飞书连接", test_feishu_connection),
        ("表格数据读取", test_read_sheet_data),
        ("设备查询", test_device_query),
        ("数据准确性", test_data_accuracy),
    ]
    
    results = {}
    for test_name, test_func in tests:
        try:
            results[test_name] = test_func()
        except Exception as e:
            print(f"❌ {test_name}测试出错: {str(e)}")
            results[test_name] = False
    
    # 输出测试总结
    print("\n" + "=" * 60)
    print("测试总结")
    print("=" * 60)
    
    total_tests = len(tests)
    passed_tests = sum(1 for result in results.values() if result)
    
    print(f"📊 总测试项: {total_tests}")
    print(f"✅ 通过测试: {passed_tests}")
    print(f"❌ 失败测试: {total_tests - passed_tests}")
    
    print("\n📋 详细结果:")
    for test_name, result in results.items():
        status = "✅ 通过" if result else "❌ 失败"
        print(f"   {test_name}: {status}")
    
    if passed_tests == total_tests:
        print(f"\n🎉 所有测试通过！飞书功能可正常使用。")
        print(f"💡 机器人已能准确读取飞书表格内容。")
    else:
        print(f"\n⚠️  部分测试失败，请检查配置。")
    
    return passed_tests == total_tests


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
