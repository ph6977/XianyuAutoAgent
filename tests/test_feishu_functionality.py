#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
飞书表格功能测试脚本
用于测试飞书表格读取器的各项功能
"""

import os
import sys
from datetime import datetime, timedelta

# 加载 .env 文件
from dotenv import load_dotenv
load_dotenv()

from feishu_knowledge_base.feishu_sheet_reader import FeishuSheetReader

def test_feishu_config():
    """检查飞书配置"""
    print("=" * 60)
    print("飞书API配置检查")
    print("=" * 60)
    
    # 从环境变量获取配置
    app_id = os.getenv("FEISHU_APP_ID")
    app_secret = os.getenv("FEISHU_APP_SECRET")
    spreadsheet_token = os.getenv("FEISHU_SPREADSHEET_TOKEN")
    sheet_id = os.getenv("FEISHU_SHEET_ID")
    
    print(f"FEISHU_APP_ID: {'已配置' if app_id else '未配置'}")
    print(f"FEISHU_APP_SECRET: {'已配置' if app_secret else '未配置'}")
    print(f"FEISHU_SPREADSHEET_TOKEN: {'已配置' if spreadsheet_token else '未配置'}")
    print(f"FEISHU_SHEET_ID: {'已配置' if sheet_id else '未配置'}")
    
    if not all([app_id, app_secret, spreadsheet_token, sheet_id]):
        print("\n⚠️  飞书API配置不完整！请设置以下环境变量：")
        print("  FEISHU_APP_ID=your_app_id")
        print("  FEISHU_APP_SECRET=your_app_secret")
        print("  FEISHU_SPREADSHEET_TOKEN=your_spreadsheet_token")
        print("  FEISHU_SHEET_ID=your_sheet_id")
        print("\n💡 提示：您可以在项目根目录创建 .env 文件来配置环境变量")
        return False
    
    return True

def test_access_token():
    """测试获取访问令牌"""
    print("\n" + "=" * 60)
    print("飞书访问令牌获取测试")
    print("=" * 60)
    
    app_id = os.getenv("FEISHU_APP_ID")
    app_secret = os.getenv("FEISHU_APP_SECRET")
    spreadsheet_token = os.getenv("FEISHU_SPREADSHEET_TOKEN")
    sheet_id = os.getenv("FEISHU_SHEET_ID")
    
    try:
        reader = FeishuSheetReader(app_id, app_secret, spreadsheet_token, sheet_id)
        token = reader._get_access_token()
        print(f"✅ 访问令牌获取成功: {token[:20]}...")
        return reader
    except Exception as e:
        print(f"❌ 访问令牌获取失败: {e}")
        return None

def test_sheet_data():
    """测试获取表格数据"""
    print("\n" + "=" * 60)
    print("飞书表格数据获取测试")
    print("=" * 60)
    
    reader = test_access_token()
    if not reader:
        return None
    
    try:
        data = reader._get_sheet_data()
        print(f"✅ 表格数据获取成功")
        print(f"   月份标识行长度: {len(data.get('month_headers', []))}")
        print(f"   列名行长度: {len(data.get('column_names', []))}")
        print(f"   设备数据行数: {len(data.get('device_data', []))}")
        
        # 显示前几行数据
        if data.get('column_names'):
            print(f"   列名: {data['column_names'][:5]}...")  # 只显示前5个
        
        return reader, data
    except Exception as e:
        print(f"❌ 表格数据获取失败: {e}")
        return None

def test_device_status_query(reader, data):
    """测试设备状态查询"""
    print("\n" + "=" * 60)
    print("设备状态查询测试")
    print("=" * 60)
    
    if not reader:
        print("❌ 飞书读取器未初始化")
        return
    
    # 示例设备名，需要根据实际情况调整
    sample_device_names = ["iPhone 13", "iPhone 14", "小米12", "华为P50", "设备名称"]
    
    # 获取实际的设备名称
    if data and 'device_data' in data and 'column_names' in data:
        device_name_col_index = None
        device_name_candidates = {'设备名称', '产品名称', '商品名称', '机型', '设备', '产品', '名称'}
        
        for i, col_name in enumerate(data['column_names']):
            col_text = str(col_name).strip()
            if col_text in device_name_candidates:
                device_name_col_index = i
                break
        
        if device_name_col_index is None:
            device_name_col_index = 0  # 默认第一列
        
        # 获取前几个设备名称
        actual_device_names = []
        for row in data['device_data'][:5]:  # 只取前5行
            if device_name_col_index < len(row) and row[device_name_col_index]:
                actual_device_names.append(str(row[device_name_col_index]).strip())
        
        if actual_device_names:
            sample_device_names = actual_device_names
    
    # 测试日期
    today = datetime.now().strftime('%Y-%m-%d')
    test_date = today
    
    print(f"测试日期: {test_date}")
    print("设备状态查询结果:")
    
    for device_name in sample_device_names[:3]:  # 只测试前3个设备
        try:
            status = reader.find_device_status_by_date(device_name, test_date)
            status_text = "可租用" if reader._is_device_available(status) else "不可租用"
            print(f"  - {device_name}: {status} ({status_text})")
        except Exception as e:
            print(f"  - {device_name}: 查询失败 - {e}")

def test_available_devices_query(reader):
    """测试可用设备查询"""
    print("\n" + "=" * 60)
    print("可用设备查询测试")
    print("=" * 60)
    
    if not reader:
        print("❌ 飞书读取器未初始化")
        return
    
    test_date = datetime.now().strftime('%Y-%m-%d')
    
    try:
        available_devices = reader.find_available_devices_by_date(test_date)
        print(f"日期 {test_date} 可用设备数量: {len(available_devices)}")
        
        for i, device in enumerate(available_devices[:5]):  # 只显示前5个
            print(f"  {i+1}. {device['name']} - 位置: {device['location']} - 状态: {device['status']}")
        
        if len(available_devices) > 5:
            print(f"  ... 还有 {len(available_devices) - 5} 个设备")
            
    except Exception as e:
        print(f"❌ 可用设备查询失败: {e}")

def test_date_range_query(reader):
    """测试日期范围查询"""
    print("\n" + "=" * 60)
    print("日期范围查询测试")
    print("=" * 60)
    
    if not reader:
        print("❌ 飞书读取器未初始化")
        return
    
    # 创建一个3天的日期范围
    start_date = datetime.now().strftime('%Y-%m-%d')
    end_date = (datetime.now() + timedelta(days=2)).strftime('%Y-%m-%d')
    
    try:
        # 尝试查询第一个设备的状态范围
        available_devices = reader.find_available_devices_by_date(start_date)
        if available_devices:
            device_name = available_devices[0]['name']
            status_list = reader.find_device_status_by_date_range(device_name, start_date, end_date)
            print(f"设备 {device_name} 在 {start_date} 到 {end_date} 的状态:")
            for date, status in status_list:
                status_text = "可租用" if reader._is_device_available(status) else "不可租用"
                print(f"  - {date}: {status} ({status_text})")
        else:
            print("当前日期没有可用设备，无法测试日期范围查询")
            
    except Exception as e:
        print(f"❌ 日期范围查询失败: {e}")

def test_location_query(reader):
    """测试按位置查询设备"""
    print("\n" + "=" * 60)
    print("按位置查询设备测试")
    print("=" * 60)
    
    if not reader:
        print("❌ 飞书读取器未初始化")
        return
    
    try:
        # 获取一些设备数据以确定可能的位置
        sheet_data = reader._get_sheet_data()
        if sheet_data and 'device_data' in sheet_data:
            # 尝试获取位置信息
            location_col_index = None
            for i, col_name in enumerate(sheet_data['column_names']):
                if col_name == '所在地':
                    location_col_index = i
                    break
            
            if location_col_index:
                # 获取第一个设备的位置
                first_device = sheet_data['device_data'][0] if sheet_data['device_data'] else None
                if first_device and location_col_index < len(first_device):
                    location = str(first_device[location_col_index])
                    if location and location != 'None':
                        print(f"尝试查询位置: {location}")
                        devices_by_location = reader.find_devices_by_location(location)
                        print(f"位置 {location} 的设备数量: {len(devices_by_location)}")
                        for i, device in enumerate(devices_by_location[:3]):
                            print(f"  - {device['name']} ({device['location']})")
                    else:
                        print("无法获取有效位置信息")
                else:
                    print("无法获取设备位置信息")
            else:
                print("表格中未找到'所在地'列")
        else:
            print("无法获取表格数据")
            
    except Exception as e:
        print(f"❌ 按位置查询设备失败: {e}")

def run_all_tests():
    """运行所有测试"""
    print("🚀 开始飞书表格功能测试")
    
    # 检查配置
    if not test_feishu_config():
        return
    
    # 获取表格数据用于后续测试
    result = test_sheet_data()
    if result:
        reader, data = result
    else:
        reader = test_access_token()
        data = None
    
    # 执行各项功能测试
    test_device_status_query(reader, data)
    test_available_devices_query(reader)
    test_date_range_query(reader)
    test_location_query(reader)
    
    print("\n" + "=" * 60)
    print("测试完成！")
    print("=" * 60)
    print("💡 如果测试失败，请检查：")
    print("   1. 飞书API配置是否正确")
    print("   2. 飞书应用是否有访问表格的权限")
    print("   3. 表格ID和工作表ID是否正确")
    print("   4. 网络连接是否正常")

if __name__ == "__main__":
    run_all_tests()
