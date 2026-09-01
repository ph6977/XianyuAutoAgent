#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""非交互式测试程序"""

import sys
import os
import re
from datetime import datetime
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from xianyu_bot_components.关键问题回复.intent_analyzer import IntentAnalyzer
from xianyu_bot_components.core.context_manager import ChatContextManager
from feishu_knowledge_base.feishu_sheet_reader import FeishuSheetReader
from xianyu_bot_components.utils.sensitive_keywords import SensitiveKeywordDetector

# 城市列表
CITIES = ["北京", "上海", "广州", "深圳", "杭州", "南京", "苏州", "成都", "重庆", "武汉", "西安", "长沙", "佛山", "东莞"]

class ConversationTest:
    def __init__(self):
        self.intent_analyzer = IntentAnalyzer()
        self.context_manager = ChatContextManager()
        # 初始化飞书读取器
        app_id = os.getenv("FEISHU_APP_ID")
        app_secret = os.getenv("FEISHU_APP_SECRET")
        spreadsheet_token = os.getenv("FEISHU_SPREADSHEET_TOKEN")
        sheet_id = os.getenv("FEISHU_SHEET_ID")
        
        if all([app_id, app_secret, spreadsheet_token, sheet_id]):
            self.feishu_reader = FeishuSheetReader(app_id, app_secret, spreadsheet_token, sheet_id)
        else:
            self.feishu_reader = None
            print("警告: 飞书API配置不完整，将无法查询设备信息")
        
        self.sensitive_manager = SensitiveKeywordDetector()
        self.user_id = "test_user"
        self.chat_id = "test_chat"
        
    def extract_locations(self, text):
        """从文本中提取城市"""
        found_locations = []
        for city in CITIES:
            if city in text:
                found_locations.append(city)
        return found_locations
    
    def extract_dates(self, text):
        """从文本中提取日期"""
        # 匹配"X月X日"、"X月X号"、"X月X"等格式
        date_pattern = r'(\d{1,2})月(\d{1,2})(?:日|号)?'
        matches = re.findall(date_pattern, text)
        
        dates = []
        for month, day in matches:
            dates.append(f"{month}月{day}日")
        
        return dates
    
    def process_query(self, user_input):
        """处理用户查询"""
        # 检查敏感词
        is_sensitive, _ = self.sensitive_manager.is_sensitive_message(user_input)
        if is_sensitive:
            return "抱歉，您的问题涉及敏感内容，我无法回答。请换个方式提问。"
        
        # 提取位置和日期
        locations = self.extract_locations(user_input)
        dates = self.extract_dates(user_input)
        
        # 处理位置
        location = None
        if locations:
            # 存储所有位置到上下文
            self.context_manager.store_multiple_locations(self.user_id, self.chat_id, locations)
            # 如果有多个位置，选择第一个
            location = locations[0]
            print(f"检测到位置: {', '.join(locations)}")
        elif not locations and not dates:
            # 如果没有位置也没有日期，尝试从上下文获取位置
            location = self.context_manager.get_latest_location(self.user_id, self.chat_id)
            if location:
                print(f"从上下文获取位置: {location}")
        
        # 处理日期
        date = dates[0] if dates else None
        if date:
            print(f"检测到日期: {date}")
        
        # 查询飞书
        if date or location:
            if not self.feishu_reader:
                return "飞书API未配置，无法查询设备信息"
            
            try:
                # 获取设备数据
                data = self.feishu_reader._get_sheet_data()
                devices = data.get('device_data', [])
                
                # 过滤设备
                filtered_devices = []
                for device in devices:
                    # 设备数据格式: [设备名称, 位置, 1月1日, 1月2日, ...]
                    if len(device) < 2:
                        continue
                    
                    device_name = device[0]
                    device_location = device[1]
                    
                    # 位置过滤
                    if location and device_location != location:
                        continue
                    
                    # 日期过滤 - 检查设备在该日期是否可用
                    if date:
                        # 获取列名映射
                        column_names = data.get('column_names', [])
                        # 查找日期对应的列索引
                        date_index = None
                        for i, col in enumerate(column_names):
                            if date in str(col):
                                date_index = i
                                break
                        
                        if date_index is not None and date_index < len(device):
                            status = device[date_index]
                            # None或空字符串表示可用
                            if status is not None and status != '':
                                continue
                    
                    filtered_devices.append({
                        'name': device_name,
                        'location': device_location,
                        'data': device
                    })
                
                if not filtered_devices:
                    if location and date:
                        return f"{date}在{location}没有可用的设备"
                    elif location:
                        return f"{location}没有可用的设备"
                    elif date:
                        return f"{date}没有可用的设备"
                
                # 格式化结果
                result = f"找到 {len(filtered_devices)} 台设备:\n"
                for device in filtered_devices[:5]:  # 最多显示5台
                    device_name = device.get('name', '未知设备')
                    device_location = device.get('location', '未知位置')
                    result += f"- {device_name} ({device_location})\n"
                
                if len(filtered_devices) > 5:
                    result += f"...还有 {len(filtered_devices) - 5} 台设备\n"
                
                return result
                
            except Exception as e:
                return f"查询设备信息时出错: {str(e)}"
        else:
            return "请指定要查询的位置或日期，例如：'北京有哪些机器？'或'10月18日有哪些机器？'"
    
    def run_tests(self):
        """运行测试用例"""
        print("对话测试程序 - 非交互式版本")
        print("=" * 40)
        
        test_cases = [
            "北京有哪些机器？",
            "10月18日有哪些机器？",
            "南京和佛山有什么设备？",
            "重庆有哪些机器？",
            "10月20日呢？",  # 测试上下文
            "上海和广州呢？",  # 测试多位置
            "今天天气怎么样？"  # 测试无关问题
        ]
        
        for i, query in enumerate(test_cases, 1):
            print(f"\n测试 {i}: {query}")
            print("-" * 30)
            response = self.process_query(query)
            print(f"回答: {response}")
            print()

if __name__ == "__main__":
    test = ConversationTest()
    test.run_tests()