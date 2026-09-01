#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
手动测试框架 - 基于conversation_final.py扩展
支持批量测试、详细记录和结果分析
"""

import sys
import os
import re
import time
import json
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

class TestFramework:
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
        
        # 初始化AI客户端
        self.api_key = os.getenv("DEEPSEEK_API_KEY")
        if self.api_key:
            self.client = openai.OpenAI(
                api_key=self.api_key,
                base_url="https://api.deepseek.com"
            )
        else:
            print("警告: 未找到DEEPSEEK_API_KEY，AI对话功能将不可用")
            self.client = None
        
        # 对话历史
        self.conversation_history = []
        
        # 测试结果记录
        self.test_results = []
        
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
    
    def process_query(self, user_input):
        """处理用户查询"""
        start_time = time.time()
        
        # 检查敏感词
        is_sensitive, _ = self.sensitive_manager.is_sensitive_message(user_input)
        if is_sensitive:
            response = "抱歉，您的问题涉及敏感内容，我无法回答。请换个方式提问。"
            return {
                "response": response,
                "processing_time": time.time() - start_time,
                "intent": "sensitive_content",
                "locations": [],
                "dates": []
            }
        
        # 使用意图分析器判断用户意图
        intent_result = self.intent_analyzer.analyze_intent(user_input, self.user_id, self.chat_id)
        response, agent_name = intent_result
        # 根据agent_name判断意图
        if agent_name == "智能租赁顾问Agent" or "租赁" in response:
            intent = "device_query"
        elif agent_name == "快递时间查询Agent" or "快递" in response:
            intent = "delivery_query"
        else:
            intent = "general_chat"
        
        # 检查是否包含位置或日期关键词，如果有也当作设备查询
        if any(keyword in user_input for keyword in CITIES) or '月' in user_input or '日' in user_input or '号' in user_input or '有货' in user_input or '有哪些' in user_input:
            intent = "device_query"
        
        # 提取位置和日期
        locations = self.extract_locations(user_input)
        dates = self.extract_dates(user_input)
        
        # 处理日期
        date = None
        query_available_dates = False
        query_month = None
        
        # 首先检查是否有具体日期
        if dates:
            if isinstance(dates, dict) and dates.get("query_type") == "available_dates":
                query_available_dates = True
                query_month = dates.get("month")
            else:
                date = dates[0]
        else:
            # 没有具体日期，检查是否只提到了月份
            month_match = re.search(r'(\d{1,2})月', user_input)
            if month_match:
                query_month = month_match.group(1)
        
        # 检查是否是简化的日期查询（如"2号"、"5号"等）
        simplified_date = None
        if not date and not query_available_dates:
            # 匹配"X号"格式
            day_match = re.search(r'(\d{1,2})号', user_input)
            if day_match:
                # 获取之前提到的月份
                latest_location = self.context_manager.get_latest_location(self.user_id, self.chat_id)
                # 从对话历史中查找月份
                mentioned_month = None
                for msg in reversed(self.conversation_history[-10:]):
                    if msg['role'] == 'user':
                        month_match = re.search(r'(\d{1,2})月', msg['content'])
                        if month_match:
                            mentioned_month = month_match.group(1)
                            break
                
                if mentioned_month:
                    simplified_date = f"{mentioned_month}月{day_match.group(1)}日"
                    date = simplified_date
        
        # 如果是一般对话，使用AI回复
        if intent == "general_chat":
            # 仍然提取位置信息以更新上下文
            if locations:
                self.context_manager.store_multiple_locations(self.user_id, self.chat_id, locations)
            
            response = self.ai_chat(user_input)
            return {
                "response": response,
                "processing_time": time.time() - start_time,
                "intent": intent,
                "locations": locations,
                "dates": dates
            }
        
        # 处理位置
        location = None
        if locations:
            # 存储所有位置到上下文
            self.context_manager.store_multiple_locations(self.user_id, self.chat_id, locations)
            location = locations[0]  # 简化测试，直接选择第一个
        elif not locations and not dates and not simplified_date:
            # 如果没有位置也没有日期，尝试从上下文获取位置
            location = self.context_manager.get_latest_location(self.user_id, self.chat_id)
        
        # 如果有位置但没有具体日期，先列出该位置的设备
        if location and not date and not simplified_date:
            if not self.feishu_reader:
                response = "飞书API未配置，无法查询设备信息"
            else:
                try:
                    # 获取设备数据
                    data = self.feishu_reader._get_sheet_data()
                    devices = data.get('device_data', [])
                    
                    # 筛选该位置的设备
                    location_devices = []
                    for device in devices:
                        if len(device) >= 2 and device[1] == location:
                            location_devices.append(device[0])
                    
                    if location_devices:
                        response = f"{location}有以下设备：\n"
                        for i, device_name in enumerate(location_devices, 1):
                            response += f"{i}. {device_name}\n"
                        
                        response += f"\n请告诉我您想查询哪个具体日期的可用性，例如：'{location}10月18日有货吗？'"
                    else:
                        response = f"抱歉，{location}暂时没有可用的设备"
                        
                except Exception as e:
                    response = f"查询设备信息时出错: {str(e)}"
            
            return {
                "response": response,
                "processing_time": time.time() - start_time,
                "intent": intent,
                "locations": locations,
                "dates": dates
            }
        
        # 查询飞书
        if date or location or query_available_dates:
            if not self.feishu_reader:
                response = "飞书API未配置，无法查询设备信息"
            else:
                try:
                    # 获取设备数据
                    data = self.feishu_reader._get_sheet_data()
                    devices = data.get('device_data', [])
                    
                    # 处理查询可用日期的特殊情况
                    if query_available_dates:
                        # 查询指定月份的可用日期和设备
                        available_dates = []
                        available_devices_by_date = {}
                        column_names = data.get('column_names', [])
                        
                        # 找到指定月份的所有日期列
                        month_dates = []
                        date_indices = []
                        for i, col in enumerate(column_names):
                            if query_month and query_month in str(col):
                                month_dates.append(str(col))
                                date_indices.append(i)
                        
                        # 检查每个日期有哪些设备可用
                        for date_str, date_idx in zip(month_dates, date_indices):
                            available_devices = []
                            for device in devices:
                                if len(device) > date_idx:
                                    status = device[date_idx]
                                    if status is None or status == '':
                                        available_devices.append(device[0])  # 设备名称
                            
                            if available_devices:
                                available_dates.append(date_str)
                                available_devices_by_date[date_str] = available_devices
                        
                        if available_dates:
                            # 处理日期格式，提取具体的日
                            days_info = []
                            for date_str in available_dates:
                                # 提取数字（日）
                                day_match = re.search(r'(\d+)', date_str)
                                if day_match:
                                    day = day_match.group(1)
                                    devices = available_devices_by_date[date_str]
                                    days_info.append(f"{query_month}月{day}日（{len(devices)}台设备）")
                            
                            response = f"{location}在{query_month}月可用的日期和设备情况：\n"
                            response += "\n".join(days_info[:5])  # 最多显示5个日期
                            
                            # 如果有位置，也列出该位置的所有设备
                            if location:
                                location_devices = []
                                for device in devices:
                                    if len(device) >= 2 and device[1] == location:
                                        location_devices.append(device[0])
                                
                                if location_devices:
                                    response += f"\n\n{location}共有设备：{', '.join(location_devices)}"
                        else:
                            response = f"{location}在{query_month}月没有可用的日期"
                    else:
                        # 正常的设备查询
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
                                response = f"{date}在{location}没有可用的设备"
                            elif location:
                                response = f"{location}没有可用的设备"
                            elif date:
                                response = f"{date}没有可用的设备"
                            else:
                                response = "没有找到匹配的设备"
                        else:
                            # 格式化结果
                            response = f"找到 {len(filtered_devices)} 台设备:\n"
                            for device in filtered_devices[:5]:  # 最多显示5台
                                device_name = device.get('name', '未知设备')
                                device_location = device.get('location', '未知位置')
                                response += f"- {device_name} ({device_location})\n"
                            
                            if len(filtered_devices) > 5:
                                response += f"...还有 {len(filtered_devices) - 5} 台设备\n"
                
                except Exception as e:
                    response = f"查询设备信息时出错: {str(e)}"
        else:
            # 没有明确的查询信息，使用AI进行对话
            response = self.ai_chat(user_input)
        
        return {
            "response": response,
            "processing_time": time.time() - start_time,
            "intent": intent,
            "locations": locations,
            "dates": dates
        }
    
    def ai_chat(self, user_input):
        """使用AI进行自然对话"""
        if not self.api_key:
            return "抱歉，AI对话功能未配置，无法进行对话。"
        
        # 获取上下文信息
        latest_location = self.context_manager.get_latest_location(self.user_id, self.chat_id)
        all_entities = self.context_manager.get_all_entities(self.user_id, self.chat_id)
        # 确保entities是字典格式
        if not isinstance(all_entities, dict):
            all_entities = {}
        
        # 构建系统提示
        system_prompt = """你是一个智能租赁顾问助手，专门帮助用户查询设备租赁信息。你的特点是：

1. 友好自然地与用户对话
2. 理解并记住对话中的上下文信息（如位置、日期等）
3. 当用户询问设备相关信息时，可以引导他们使用查询功能
4. 对话要简洁、专业、有帮助

当前对话上下文：
- 最新位置：{location}
- 其他实体信息：{entities}
- 对话历史：{history}

请根据用户的输入，提供自然、友好的回复。如果用户询问设备可用性、位置、日期等具体信息，请提醒他们可以使用查询功能。""".format(
            location=latest_location or "未提及",
            entities=all_entities or "无",
            history=self._get_recent_history()
        )
        
        # 准备消息
        messages = [
            {"role": "system", "content": system_prompt},
        ]
        
        # 添加最近的对话历史
        for msg in self.conversation_history[-6:]:  # 只保留最近6条对话
            messages.append(msg)
        
        # 添加当前用户输入
        messages.append({"role": "user", "content": user_input})
        
        try:
            # 调用AI API
            response = self.client.chat.completions.create(
                model="deepseek-chat",
                messages=messages,
                max_tokens=500,
                temperature=0.7
            )
            
            ai_response = response.choices[0].message.content
            
            # 更新对话历史
            self.conversation_history.append({"role": "user", "content": user_input})
            self.conversation_history.append({"role": "assistant", "content": ai_response})
            
            # 保持对话历史在合理长度
            if len(self.conversation_history) > 20:
                self.conversation_history = self.conversation_history[-20:]
            
            return ai_response
            
        except Exception as e:
            return f"AI对话出现问题: {str(e)}"
    
    def _get_recent_history(self):
        """获取最近的对话历史摘要"""
        if not self.conversation_history:
            return "无历史对话"
        
        recent = self.conversation_history[-4:]  # 最近4条
        summary = []
        for msg in recent:
            role = "用户" if msg["role"] == "user" else "助手"
            summary.append(f"{role}: {msg['content'][:50]}...")
        
        return "\n".join(summary)
    
    def run_single_test(self, test_input, test_name=None):
        """运行单个测试"""
        if not test_name:
            test_name = f"测试_{len(self.test_results) + 1}"
        
        print(f"\n{'='*50}")
        print(f"测试: {test_name}")
        print(f"输入: {test_input}")
        print(f"{'='*50}")
        
        # 记录开始时间
        start_time = time.time()
        
        # 处理查询
        result = self.process_query(test_input)
        
        # 记录结果
        test_result = {
            "test_name": test_name,
            "input": test_input,
            "response": result["response"],
            "processing_time": result["processing_time"],
            "intent": result["intent"],
            "locations": result["locations"],
            "dates": result["dates"],
            "timestamp": datetime.now().isoformat()
        }
        
        self.test_results.append(test_result)
        
        # 打印结果
        print(f"意图: {result['intent']}")
        print(f"识别的位置: {result['locations']}")
        print(f"识别的日期: {result['dates']}")
        print(f"处理时间: {result['processing_time']:.3f}秒")
        print(f"\n回复:\n{result['response']}")
        
        return test_result
    
    def run_batch_tests(self, test_cases):
        """批量运行测试"""
        print(f"\n开始批量测试，共{len(test_cases)}个测试用例")
        
        for i, test_case in enumerate(test_cases, 1):
            if isinstance(test_case, dict):
                self.run_single_test(test_case["input"], test_case.get("name"))
            else:
                self.run_single_test(test_case)
        
        # 生成测试报告
        self.generate_report()
    
    def generate_report(self):
        """生成测试报告"""
        report = {
            "summary": {
                "total_tests": len(self.test_results),
                "successful_tests": len([r for r in self.test_results if r.get("success", True)]),
                "failed_tests": len([r for r in self.test_results if not r.get("success", True)]),
                "average_processing_time": sum(r["processing_time"] for r in self.test_results) / len(self.test_results),
                "test_date": datetime.now().isoformat()
            },
            "details": self.test_results
        }
        
        # 保存报告
        report_file = f"test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        
        # 打印摘要
        print(f"\n{'='*50}")
        print("测试报告摘要")
        print(f"{'='*50}")
        print(f"总测试数: {report['summary']['total_tests']}")
        print(f"成功测试: {report['summary']['successful_tests']}")
        print(f"失败测试: {report['summary']['failed_tests']}")
        print(f"平均处理时间: {report['summary']['average_processing_time']:.3f}秒")
        print(f"报告已保存到: {report_file}")
        
        return report

# 测试用例定义
TEST_CASES = [
    # 基础功能测试
    {"name": "基础位置查询", "input": "北京有哪些机器？"},
    {"name": "基础日期查询", "input": "10月18日有哪些机器？"},
    {"name": "多位置查询", "input": "北京和上海有什么设备？"},
    
    # 上下文理解测试
    {"name": "上下文位置", "input": "重庆有哪些机器？"},
    {"name": "上下文日期", "input": "那20号呢？"},
    {"name": "简化日期", "input": "2号有吗"},
    
    # 模糊查询测试
    {"name": "月份查询", "input": "南京11月能租吗"},
    {"name": "有货查询", "input": "东莞有货吗"},
    
    # 边界条件测试
    {"name": "空输入", "input": ""},
    {"name": "只有空格", "input": "   "},
    {"name": "特殊字符", "input": "北京@#$%有货吗？"},
    
    # AI对话测试
    {"name": "打招呼", "input": "你好"},
    {"name": "无关问题", "input": "今天天气怎么样？"},
    {"name": "租设备意图", "input": "我想租个设备"},
]

if __name__ == "__main__":
    test_framework = TestFramework()
    
    print("="*60)
    print("手动测试框架")
    print("="*60)
    print("\n可用命令:")
    print("1. batch - 运行批量测试")
    print("2. interactive - 交互式测试")
    print("3. single <输入> - 运行单个测试")
    
    while True:
        command = input("\n请输入命令: ").strip()
        
        if command == "batch":
            test_framework.run_batch_tests(TEST_CASES)
        elif command == "interactive":
            while True:
                user_input = input("\n请输入测试内容（输入quit退出）: ").strip()
                if user_input.lower() == "quit":
                    break
                test_framework.run_single_test(user_input)
        elif command.startswith("single "):
            test_input = command[7:]
            test_framework.run_single_test(test_input)
        elif command == "quit":
            break
        else:
            print("无效命令")
