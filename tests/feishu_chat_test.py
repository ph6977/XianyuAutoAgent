#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
飞书信息获取和回复功能 - 基于conversation_final.py的简化版本
"""

import sys
import os
import re
import time
from datetime import datetime
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from xianyu_bot_components.关键问题回复.intent_analyzer import IntentAnalyzer
from xianyu_bot_components.core.context_manager import ChatContextManager
from feishu_knowledge_base.feishu_sheet_reader import FeishuSheetReader
from xianyu_bot_components.utils.sensitive_keywords import SensitiveKeywordDetector
import openai

# 城市列表
CITIES = ["北京", "上海", "广州", "深圳", "杭州", "南京", "苏州", "成都", "重庆", "武汉", "西安", "长沙", "佛山", "东莞"]

class FeishuChat:
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
            print("✅ 飞书API连接成功")
        else:
            self.feishu_reader = None
            print("❌ 飞书API配置不完整")
        
        self.sensitive_manager = SensitiveKeywordDetector()
        self.user_id = "user"
        self.chat_id = "chat"
        
        # 初始化AI客户端
        self.api_key = os.getenv("DEEPSEEK_API_KEY")
        if self.api_key:
            self.client = openai.OpenAI(
                api_key=self.api_key,
                base_url="https://api.deepseek.com"
            )
            print("✅ AI服务连接成功")
        else:
            self.client = None
            print("❌ AI服务未配置")
        
        # 对话历史
        self.conversation_history = []
        
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
        
        # 检查是否是询问可用日期的问题
        if not dates and ('哪几号' in text or '哪天' in text or '什么时候' in text or '几号' in text):
            # 提取月份
            month_pattern = r'(\d{1,2})月'
            month_match = re.search(month_pattern, text)
            if month_match:
                return {"query_type": "available_dates", "month": month_match.group(1)}
        
        return dates
    
    def get_feishu_data(self):
        """获取飞书数据"""
        if not self.feishu_reader:
            return None
        
        try:
            return self.feishu_reader._get_sheet_data()
        except Exception as e:
            print(f"❌ 获取飞书数据失败: {e}")
            return None
    
    def query_devices(self, location=None, date=None, month=None):
        """查询设备信息"""
        data = self.get_feishu_data()
        if not data:
            return "❌ 无法获取设备数据"
        
        devices = data.get('device_data', [])
        column_names = data.get('column_names', [])
        month_headers = data.get('month_headers', [])
        
        # 处理月份查询（如"10月怎么样"）
        if month and ('怎么样' in sys.argv[-1] or '如何' in sys.argv[-1] or '情况' in sys.argv[-1]):
            available_dates = []
            
            # 找到月份在month_headers中的位置
            month_col_index = None
            for i, header in enumerate(month_headers):
                if header and month in str(header):
                    month_col_index = i
                    break
            
            if month_col_index is not None:
                # 获取该月份的所有日期
                for i, col in enumerate(column_names):
                    if i < 2:  # 跳过设备名称和位置列
                        continue
                    date_str = f"{month}月{col}日"
                    
                    # 检查该日期有哪些设备可用
                    available_devices = []
                    for device in devices:
                        if len(device) > i:
                            status = device[i]
                            if status is None or status == '':
                                device_name = device[0]
                                device_loc = device[1]
                                if not location or device_loc == location:
                                    available_devices.append(device_name)
                    
                    if available_devices:
                        available_dates.append(f"{date_str}（{len(available_devices)}台设备）")
            
            if available_dates:
                result = f"📍 {location or ''}{month}月可用情况：\n"
                result += "\n".join(available_dates[:10])
                if len(available_dates) > 10:
                    result += f"\n...还有 {len(available_dates) - 10} 个可用日期"
                return result
            else:
                return f"❌ {month}月没有可用设备"
        
        # 处理具体日期查询
        filtered_devices = []
        for device in devices:
            if len(device) < 2:
                continue
            
            device_name = device[0]
            device_location = device[1]
            
            # 位置过滤
            if location and device_location != location:
                continue
            
            # 日期过滤
            if date:
                date_index = None
                for i, col in enumerate(column_names):
                    # 构造日期匹配模式
                    day_match = re.search(r'(\d+)', date)
                    if day_match and str(col) == day_match.group(1):
                        date_index = i
                        break
                
                if date_index is not None and date_index < len(device):
                    status = device[date_index]
                    if status is not None and status != '':
                        continue
            
            filtered_devices.append({
                'name': device_name,
                'location': device_location
            })
        
        if not filtered_devices:
            if location and date:
                return f"❌ {date}在{location}没有可用设备"
            elif location:
                return f"❌ {location}没有可用设备"
            elif date:
                return f"❌ {date}没有可用设备"
            else:
                return "❌ 没有找到匹配的设备"
        
        # 格式化结果
        result = f"✅ 找到 {len(filtered_devices)} 台设备：\n"
        for device in filtered_devices[:5]:
            result += f"  • {device['name']} ({device['location']})\n"
        
        if len(filtered_devices) > 5:
            result += f"  ...还有 {len(filtered_devices) - 5} 台设备\n"
        
        return result
    
    def ai_reply(self, user_input):
        """AI回复"""
        if not self.client:
            return "❌ AI服务未配置"
        
        # 获取上下文
        latest_location = self.context_manager.get_latest_location(self.user_id, self.chat_id)
        
        system_prompt = f"""你是一个友好的设备租赁助手。当前上下文：
- 最新位置：{latest_location or '未提及'}

请根据用户输入提供自然、友好的回复。如果用户询问设备信息，引导他们使用查询功能。"""
        
        messages = [
            {"role": "system", "content": system_prompt}
        ]
        
        # 添加最近对话历史
        for msg in self.conversation_history[-6:]:
            messages.append(msg)
        
        messages.append({"role": "user", "content": user_input})
        
        try:
            response = self.client.chat.completions.create(
                model="deepseek-chat",
                messages=messages,
                max_tokens=200,
                temperature=0.7
            )
            
            ai_response = response.choices[0].message.content
            
            # 更新对话历史
            self.conversation_history.append({"role": "user", "content": user_input})
            self.conversation_history.append({"role": "assistant", "content": ai_response})
            
            # 保持历史长度
            if len(self.conversation_history) > 20:
                self.conversation_history = self.conversation_history[-20:]
            
            return ai_response
            
        except Exception as e:
            return f"❌ AI回复失败: {str(e)}"
    
    def process_input(self, user_input):
        """处理用户输入"""
        # 检查敏感词
        is_sensitive, _ = self.sensitive_manager.is_sensitive_message(user_input)
        if is_sensitive:
            return "❌ 问题涉及敏感内容，请换个方式提问"
        
        # 提取位置和日期
        locations = self.extract_locations(user_input)
        dates = self.extract_dates(user_input)
        
        # 存储位置到上下文
        if locations:
            self.context_manager.store_multiple_locations(self.user_id, self.chat_id, locations)
        
        # 判断是否是设备查询
        is_device_query = (
            any(city in user_input for city in CITIES) or
            '月' in user_input or '日' in user_input or '号' in user_input or
            '有货' in user_input or '有哪些' in user_input or '能租吗' in user_input or
            '可以不' in user_input or '怎么样' in user_input
        )
        
        # 处理设备查询
        if is_device_query:
            location = locations[0] if locations else self.context_manager.get_latest_location(self.user_id, self.chat_id)
            
            # 处理日期
            date = None
            month = None
            
            if dates:
                if isinstance(dates, dict) and dates.get("query_type") == "available_dates":
                    month = dates.get("month")
                else:
                    date = dates[0]
            else:
                # 检查是否只提到月份
                month_match = re.search(r'(\d{1,2})月', user_input)
                if month_match:
                    month = month_match.group(1)
            
            # 如果有位置但没有具体日期，先列出设备
            if location and not date and not month:
                result = self.query_devices(location=location)
                if result.startswith("✅"):
                    result += f"\n💡 查询具体日期可用性，例如：'{location}10月18日'"
                return result
            
            # 查询具体信息
            return self.query_devices(location=location, date=date, month=month)
        
        # 其他情况使用AI回复
        return self.ai_reply(user_input)
    
    def run(self):
        """运行聊天程序"""
        print("\n" + "="*50)
        print("🤖 飞书设备查询助手")
        print("="*50)
        print("\n💡 使用提示：")
        print("  • 查询位置：'北京有哪些设备？'")
        print("  • 查询日期：'10月18日有货吗？'")
        print("  • 查询月份：'10月怎么样？'")
        print("  • 日常对话：'你好'、'今天天气如何？'")
        print("\n输入 'quit' 或 'exit' 退出\n")
        
        while True:
            try:
                user_input = input("👤 您：").strip()
                
                if user_input.lower() in ['quit', 'exit', '退出']:
                    print("\n👋 再见！")
                    break
                
                if not user_input:
                    continue
                
                # 处理输入
                response = self.process_input(user_input)
                print(f"\n🤖 助手：{response}\n")
                
            except KeyboardInterrupt:
                print("\n\n👋 程序已退出")
                break
            except Exception as e:
                print(f"\n❌ 错误：{str(e)}\n")

if __name__ == "__main__":
    chat = FeishuChat()
    chat.run()