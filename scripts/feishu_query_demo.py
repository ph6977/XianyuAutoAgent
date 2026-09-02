#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
飞书设备库存查询示例
演示如何查询飞书中的设备信息并使用AI进行回答
"""

import os
import sys
from datetime import datetime
from typing import Dict, List, Optional

# 加载环境变量
from dotenv import load_dotenv
load_dotenv()

# 添加项目根目录到Python路径
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

from feishu_knowledge_base.feishu_sheet_reader import FeishuSheetReader
from openai import OpenAI
from loguru import logger


def query_feishu_data():
    """查询飞书数据并展示功能"""
    print("🔍 正在连接飞书API并获取设备数据...")
    
    # 初始化飞书读取器
    app_id = os.getenv("FEISHU_APP_ID")
    app_secret = os.getenv("FEISHU_APP_SECRET")
    spreadsheet_token = os.getenv("FEISHU_SPREADSHEET_TOKEN")
    sheet_id = os.getenv("FEISHU_SHEET_ID")
    
    if not all([app_id, app_secret, spreadsheet_token, sheet_id]):
        print("❌ 飞书API配置不完整，请检查.env文件中的配置")
        return
    
    try:
        feishu_reader = FeishuSheetReader(app_id, app_secret, spreadsheet_token, sheet_id)
        
        # 获取表格数据
        data = feishu_reader._get_sheet_data()
        if not data:
            print("❌ 无法获取飞书表格数据")
            return
        
        print("✅ 成功连接飞书API并获取数据")
        print(f"📊 设备总数: {len(data.get('device_data', []))}")
        print(f"📅 月份标识: {data.get('month_headers', [])[:10]}...")  # 显示前10个
        print(f"📅 列名: {data.get('column_names', [])[:10]}...")       # 显示前10个
        
        # 显示设备列表
        device_data = data.get('device_data', [])
        print("\n📋 设备列表:")
        for i, row in enumerate(device_data[:5]):  # 显示前5个设备
            if len(row) >= 2:
                device_name = row[0] if len(row) > 0 else "未知设备"
                location = row[1] if len(row) > 1 else "未知位置"
                print(f"  {i+1}. {device_name} - 位置: {location}")
        
        if len(device_data) > 5:
            print(f"  ... 还有 {len(device_data) - 5} 个设备")
        
        # 示例查询：查询当前日期的可用设备
        print("\n🔍 查询当前日期可用设备...")
        current_date = datetime.now().strftime('%Y-%m-%d')
        available_devices = feishu_reader.find_available_devices_by_date(current_date)
        print(f"🗓️  {current_date} 可用设备数量: {len(available_devices)}")
        
        for device in available_devices[:3]:  # 显示前3个
            print(f"  - {device['name']} ({device['location']})")
        
        # 示例查询：查询特定位置的设备
        print("\n🔍 查询佛山地区设备...")
        foshan_devices = []
        for row in device_data:
            if len(row) > 1 and '佛山' in str(row[1]):
                device_name = row[0] if len(row) > 0 else "未知设备"
                current_status = feishu_reader.find_device_status_by_date(device_name, current_date)
                is_available = feishu_reader._is_device_available(current_status)
                foshan_devices.append({
                    'name': device_name,
                    'location': row[1],
                    'available': is_available,
                    'status': current_status
                })
        
        print(f"📍 佛山地区设备数量: {len(foshan_devices)}")
        for device in foshan_devices:
            status_text = "✅ 可用" if device['available'] else "❌ 不可用"
            print(f"  - {device['name']} - 状态: {status_text}")
    
    except Exception as e:
        print(f"❌ 查询飞书数据时出现错误: {e}")
        logger.error(f"查询飞书数据错误: {e}")


def ai_demo_response(user_question: str):
    """演示AI如何响应用户问题"""
    print(f"\n🤔 分析问题: {user_question}")
    
    # 初始化大模型客户端
    api_key = os.getenv("API_KEY")
    base_url = os.getenv("MODEL_BASE_URL")
    model_name = os.getenv("MODEL_NAME")
    
    if not all([api_key, base_url, model_name]):
        print("❌ 大模型API配置不完整")
        return
    
    try:
        client = OpenAI(api_key=api_key, base_url=base_url)
        
        # 查询飞书数据
        app_id = os.getenv("FEISHU_APP_ID")
        app_secret = os.getenv("FEISHU_APP_SECRET")
        spreadsheet_token = os.getenv("FEISHU_SPREADSHEET_TOKEN")
        sheet_id = os.getenv("FEISHU_SHEET_ID")
        
        feishu_reader = FeishuSheetReader(app_id, app_secret, spreadsheet_token, sheet_id)
        
        # 获取当前日期的可用设备
        current_date = datetime.now().strftime('%Y-%m-%d')
        available_devices = feishu_reader.find_available_devices_by_date(current_date)
        
        # 根据用户问题筛选设备
        relevant_devices = []
        if "佛山" in user_question or "foshan" in user_question.lower():
            relevant_devices = [d for d in available_devices if "佛山" in d['location']]
        elif "东莞" in user_question or "dongguan" in user_question.lower():
            relevant_devices = [d for d in available_devices if "东莞" in d['location']]
        else:
            relevant_devices = available_devices
        
        # 构建AI提示词
        system_prompt = """你是一个专业的设备租赁顾问，能够根据设备库存信息回答用户的问题。
        请用专业、友好的语气回答用户的问题。如果用户询问设备可用性，请明确告知哪些设备可用、位置在哪里。
        如果用户询问价格或其他信息，请告知暂时无法提供，需要进一步咨询。"""
        
        device_list_str = "\n".join([f"- {d['name']} ({d['location']})" for d in relevant_devices[:10]])
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"""当前可用设备列表：
{device_list_str}

用户问题：{user_question}

请根据以上设备信息，用专业、友好的语气回答用户的问题。"""}
        ]
        
        response = client.chat.completions.create(
            model=model_name,
            messages=messages,
            temperature=0.7,
            max_tokens=300
        )
        
        print(f"🤖 AI回复: {response.choices[0].message.content}")
        
    except Exception as e:
        print(f"❌ AI回复时出现错误: {e}")


def main():
    """主函数"""
    print("🚀 飞书设备库存查询演示")
    print("=" * 50)
    
    # 查询飞书数据
    query_feishu_data()
    
    # 演示AI响应
    print("\n" + "=" * 50)
    print("🤖 AI响应演示")
    print("=" * 50)
    
    demo_questions = [
        "佛山有哪些设备可以租用？",
        "今天有什么设备是可用的？",
        "东莞地区有设备吗？"
    ]
    
    for question in demo_questions:
        ai_demo_response(question)
        print("-" * 30)


if __name__ == "__main__":
    main()