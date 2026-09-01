# -*- coding: utf-8 -*-
"""
对话测试程序 - 最终版本，支持多位置选择和上下文管理
"""

import sys
import os
import re
import time
from datetime import datetime
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 添加项目根目录到Python路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from xianyu_bot_components.关键问题回复.intent_analyzer import IntentAnalyzer
from xianyu_bot_components.core.context_manager import ChatContextManager
from feishu_knowledge_base.feishu_sheet_reader import FeishuSheetReader
from xianyu_bot_components.utils.sensitive_keywords import SensitiveKeywordDetector
import openai

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
        price_sheet_id = os.getenv("FEISHU_PRICE_SHEET_ID")  # 价格表的sheet ID
        
        if all([app_id, app_secret, spreadsheet_token, sheet_id]):
            self.feishu_reader = FeishuSheetReader(app_id, app_secret, spreadsheet_token, sheet_id)
            # 初始化价格表读取器（如果有配置）
            if price_sheet_id:
                self.price_reader = FeishuSheetReader(app_id, app_secret, spreadsheet_token, price_sheet_id)
            else:
                self.price_reader = None
                print("警告: 未配置价格表ID，将无法查询价格信息")
        else:
            self.feishu_reader = None
            self.price_reader = None
            print("警告: 飞书API配置不完整，将无法查询设备信息")
        
        self.sensitive_manager = SensitiveKeywordDetector()
        self.user_id = "test_user"
        self.chat_id = "test_chat"
        
        # 初始化AI客户端
        self.api_key = os.getenv("DEEPSEEK_API_KEY")
        if self.api_key:
            self.client = openai.OpenAI(api_key=self.api_key, base_url="https://api.deepseek.com")
        else:
            self.client = None
            print("警告: DeepSeek API密钥未配置，将无法使用AI对话功能")
    
    def extract_locations(self, text):
        """提取文本中的城市名称"""
        locations = []
        for city in CITIES:
            if city in text:
                locations.append(city)
        return locations
    
    def extract_dates(self, text):
        """提取文本中的日期信息"""
        dates = []
        
        # 提取月份（如"10月"、"11月"）
        month_pattern = r'(\d{1,2})月'
        month_matches = re.findall(month_pattern, text)
        
        # 提取具体日期（如"10月18日"、"18号"）
        date_pattern = r'(\d{1,2})月(\d{1,2})日?'
        date_matches = re.findall(date_pattern, text)
        
        if date_matches:
            # 只返回第一个匹配的日期
            month, day = date_matches[0]
            dates.append(f"{month}月{day}日")
        elif month_matches and ('怎么样' in text or '如何' in text or '情况' in text):
            # 如果只提到月份且询问情况，返回特殊标记
            return {"query_type": "available_dates", "month": month_matches[0]}
        
        return dates
    
    def handle_multi_location(self, locations):
        """处理多个位置的情况"""
        if len(locations) == 1:
            return locations[0]
        
        print(f"\n检测到多个位置：{', '.join(locations)}")
        print("请选择要查询的位置：")
        for i, location in enumerate(locations, 1):
            print(f"{i}. {location}")
        
        while True:
            try:
                choice = input("请输入序号（按回车默认选择1）：").strip()
                if not choice:
                    choice = "1"
                choice = int(choice)
                if 1 <= choice <= len(locations):
                    selected = locations[choice - 1]
                    print(f"已选择：{selected}")
                    return selected
                else:
                    print("序号无效，请重新输入")
            except ValueError:
                print("请输入有效的数字序号")
    
    def ai_chat(self, user_input):
        """使用AI进行对话"""
        if not self.client:
            return "抱歉，AI功能未配置，无法进行对话。"
        
        try:
            # 获取对话上下文
            context_messages = self.context_manager.get_context_by_chat(self.chat_id)
            
            # 构建对话历史
            messages = [
                {"role": "system", "content": "你是一个闲鱼设备租赁助手，专门帮助用户查询设备可用性等信息。注意：如果用户询问价格，请明确告知价格信息需要从数据库中查询，不要提供任何示例价格或猜测价格。请用友好、专业的语气回复用户。"}
            ]
            
            # 添加上下文对话
            for msg in context_messages[-5:]:  # 只保留最近5条
                messages.append({"role": msg["role"], "content": msg["content"]})
            
            # 添加当前用户输入
            messages.append({"role": "user", "content": user_input})
            
            response = self.client.chat.completions.create(
                model="deepseek-chat",
                messages=messages,
                temperature=0.7
            )
            
            ai_response = response.choices[0].message.content.strip()
            
            # 保存对话到上下文
            self.context_manager.add_message_by_chat(self.chat_id, self.user_id, "test_item", "user", user_input)
            self.context_manager.add_message_by_chat(self.chat_id, self.user_id, "test_item", "assistant", ai_response)
            
            return ai_response
            
        except Exception as e:
            return f"AI对话出错：{str(e)}"
    
    def process_query(self, user_input):
        """处理用户查询"""
        start_time = time.time()
        
        # 检查敏感词
        is_sensitive, _ = self.sensitive_manager.is_sensitive_message(user_input)
        if is_sensitive:
            return "抱歉，您的问题涉及敏感内容，我无法回答。请换个方式提问。"
        
        # 先简单判断是否包含价格相关词汇
        price_keywords = ['多少钱', '价格', '费用', '租金', '收费', '成本', '报价', '租一天', '租一周', '租一月']
        is_price_related = any(keyword in user_input for keyword in price_keywords)
        
        # 使用意图分析器判断用户意图
        intent_result = self.intent_analyzer.analyze_intent(user_input, self.user_id, self.chat_id)
        # intent_result 是一个元组 (response, agent_name)
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
        
        # 如果是价格相关且有价格表读取器，进行价格查询
        if is_price_related and self.price_reader:
            try:
                # 构建意图分析提示
                intent_prompt = f"""请分析用户的意图。用户说："{user_input}"

请判断这是否是价格查询，并提取相关信息。

如果是价格查询，请返回JSON格式：
{{
    "is_price_query": true,
    "device_name": "设备名称",
    "rental_duration": "租用时长（如：1天、1周、1个月等，如果没有明确说明则为null）",
    "query_type": "价格查询"
}}

如果不是价格查询，返回：
{{
    "is_price_query": false,
    "intent": "其他意图描述"
}}

只返回JSON，不要其他内容。
"""
                
                response = self.client.chat.completions.create(
                    model="deepseek-chat",
                    messages=[
                        {"role": "system", "content": "你是一个意图分析助手，专门分析用户的查询意图。"},
                        {"role": "user", "content": intent_prompt}
                    ],
                    temperature=0.1
                )
                
                intent_result = response.choices[0].message.content.strip()
                print(f"\n[调试] AI意图分析结果: {intent_result}")
                
                # 尝试解析JSON
                try:
                    import json
                    intent_data = json.loads(intent_result)
                    print(f"[调试] 解析后的意图数据: {intent_data}")
                    
                    # 如果是价格查询且有价格表读取器
                    if intent_data.get("is_price_query") and self.price_reader:
                        print(f"[调试] 确认为价格查询，开始查询价格")
                        device_name = intent_data.get("device_name", user_input)
                        rental_duration = intent_data.get("rental_duration")
                        
                        try:
                            # 从价格表获取数据
                            price_data = self.price_reader._get_sheet_data()
                            price_devices = price_data.get('device_data', [])
                            price_columns = price_data.get('column_names', [])
                            
                            # 调试信息
                            print(f"\n[调试] 价格查询:")
                            print(f"  设备名称: {device_name}")
                            print(f"  租期: {rental_duration}")
                            print(f"  价格表列数: {len(price_columns)}")
                            print(f"  价格表行数: {len(price_devices)}")
                            
# 查找匹配的设备
                            matched_device_rows = []
                            price_type_row = None
                            
                            # 首先查找价格类型行（包含"每日单价"）
                            print(f"  [调试] 查找价格类型行（包含'每日单价'）:")
                            for idx, row in enumerate(price_devices):
                                print(f"    行{idx+1}: {row}")
                                if len(row) > 1:
                                    print(f"      第二个元素: '{row[1]}' (类型: {type(row[1])})")
                                    if row[1] and '每日单价' in str(row[1]):
                                        price_type_row = row
                                        print(f"      ✓ 找到价格类型行!")
                                        break
                            
                            # 然后查找设备行
                            print(f"  [调试] 查找设备 '{device_name}':")
                            for idx, row in enumerate(price_devices):
                                device_name_in_table = str(row[0]) if len(row) > 0 else "空"
                                print(f"    行{idx+1}: '{device_name_in_table}'")
                                
                                # 查找设备行 - 使用精确匹配
                                if len(row) > 0 and device_name == device_name_in_table:
                                    matched_device_rows.append(row)
                                    print(f"    → 精确匹配成功!")
                            
                            # 如果没有精确匹配，尝试模糊匹配
                            if not matched_device_rows:
                                print(f"  [调试] 未找到精确匹配，尝试模糊匹配")
                                # 将"胖卡4002"转换为"胖卡4-002"
                                if '胖卡' in device_name:
                                    # 提取数字部分
                                    import re
                                    match = re.search(r'胖卡(\d+)', device_name)
                                    if match:
                                        number = match.group(1)
                                        print(f"  [调试] 提取数字: {number}")
                                        # 如果是4位数(如4002)，取最后3位(002)
                                        if len(number) == 4:
                                            number = number[-3:]
                                        # 确保是3位数
                                        if len(number) == 2:
                                            number = '0' + number
                                        elif len(number) == 1:
                                            number = '00' + number
                                        
                                        # 尝试不同的格式
                                        for fmt in [f"胖卡4-{number}"]:
                                            print(f"  [调试] 尝试格式: {fmt}")
                                            for row in price_devices:
                                                if len(row) > 0 and fmt == str(row[0]):
                                                    matched_device_rows.append(row)
                                                    print(f"  [调试] 找到匹配: {row[0]}")
                                                    break
                                            if matched_device_rows:
                                                break
                            
                            print(f"  [调试] 匹配的设备行数: {len(matched_device_rows)}")
                            print(f"  [调试] 价格类型行: {price_type_row}")
                            
                            if matched_device_rows:
                                print(f"  [调试] 开始生成价格响应")
                                response = f"根据价格表查询结果：\n"
                                for device_row in matched_device_rows[:5]:  # 最多显示5条
                                    name = device_row[0] if len(device_row) > 0 else 'N/A'
                                    
                                    # 如果有指定租用时长，查找对应的价格列
                                    if rental_duration:
                                        # 查找包含租用时长的列
                                        price_col_index = None
                                        for i, col in enumerate(price_columns):
                                            if rental_duration in str(col):
                                                price_col_index = i
                                                break
                                        
                                        if price_col_index and price_col_index < len(device_row):
                                            price = device_row[price_col_index]
                                            if price:
                                                response += f"- {name} ({rental_duration}): {price}元\n"
                                            else:
                                                response += f"- {name}: {rental_duration}暂无价格\n"
                                        else:
                                            response += f"- {name}: 未找到{rental_duration}的价格\n"
                                    else:
                                        # 显示所有价格信息
                                        price_info = []
                                        for i, col in enumerate(price_columns):
                                            if i >= 2 and i < len(device_row):  # 跳过前两列
                                                price = device_row[i]
                                                if price:
                                                    price_info.append(f"{col}: {price}元")
                                        
                                        if price_info:
                                            response += f"- {name}\n"
                                            for pi in price_info:
                                                response += f"  {pi}\n"
                                        else:
                                            response += f"- {name}: 暂无价格信息\n"
                                
                                return response
                            else:
                                return f"抱歉，价格表中没有找到 '{device_name}' 的价格信息。"
                        except Exception as e:
                            return f"查询价格时出错: {str(e)}"
                            
                except json.JSONDecodeError:
                    # JSON解析失败，继续使用原有逻辑
                    pass
                    
            except Exception as e:
                # 大模型调用失败，继续使用原有逻辑
                pass
        
        # 如果是价格相关但没有价格表，提示用户
        elif is_price_related and not self.price_reader:
            return "抱歉，价格表未配置，暂时无法查询价格信息。请联系管理员配置价格表。"
        
        # 设备查询相关意图
        # 提取位置和日期
        locations = self.extract_locations(user_input)
        dates = self.extract_dates(user_input)
        
        # 处理位置
        location = None
        location_from_context = False
        if locations:
            # 存储所有位置到上下文
            self.context_manager.store_multiple_locations(self.user_id, self.chat_id, locations)
            # 处理多位置选择
            location = self.handle_multi_location(locations)
        else:
            # 如果没有位置，尝试从上下文获取位置
            location = self.context_manager.get_latest_location(self.user_id, self.chat_id)
            if location:
                location_from_context = True
                print(f"\n(从上下文获取位置: {location})")
        
        # 处理日期
        date = None
        date_range = []  # 存储日期范围
        query_available_dates = False
        query_month = None
        
        # 检查是否包含月份但没有具体日期
        month_match = re.search(r'(\d{1,2})月', user_input)
        if month_match and not re.search(r'(\d{1,2})月(\d{1,2})', user_input):
            query_month = month_match.group(1)
            query_available_dates = True
            print(f"\n(查询{query_month}月可用日期)")
        elif dates:
            if isinstance(dates, dict) and dates.get("query_type") == "available_dates":
                query_available_dates = True
                query_month = dates.get("month")
                print(f"\n(查询{query_month}月可用日期)")
            else:
                # 检查是否是日期范围查询
                range_match = re.search(r'(\d{1,2})月(\d{1,2})(?:到|至|-|~)(\d{1,2})', user_input)
                if range_match:
                    start_day = int(range_match.group(2))
                    end_day = int(range_match.group(3))
                    month = range_match.group(1)
                    # 生成日期范围
                    for day in range(start_day, end_day + 1):
                        date_range.append(f"{month}月{day}日")
                    date = date_range[0]  # 使用第一个日期作为主要查询日期
                    print(f"\n(检测到日期范围: {date_range[0]} 到 {date_range[-1]})")
                else:
                    date = dates[0]
                    print(f"\n(检测到日期: {date})")
        
        # 如果有位置但没有具体日期
        if location and not date:
            # 如果用户询问"X月怎么样"，查询该月的可用日期
            if query_month and ('怎么样' in user_input or '如何' in user_input or '情况' in user_input):
                query_available_dates = True
                print(f"\n(查询{location}{query_month}月情况)")
        
        # 初始化response
        response = None
        
        # 检查是否是省略句（如"那...呢"、"其他呢"等）
        is_elliptical = any(pattern in user_input for pattern in ['那', '其他', '还有', '另外']) and '呢' in user_input
        
        # 获取最近的对话历史，用于理解省略句
        recent_context = []
        try:
            context_messages = self.context_manager.get_context_by_chat(self.chat_id)
            if context_messages:
                # 获取最近3条对话
                recent_context = context_messages[-3:]
        except:
            pass
        
        # 检查信息完整性，如果缺失关键信息则询问
        if not location and not date:
            # 既没有位置也没有日期
            if is_elliptical:
                # 省略句且没有上下文信息
                if recent_context:
                    # 有历史对话，尝试理解省略内容
                    last_msg = recent_context[-1].get('content', '') if recent_context else ''
                    if '重庆' in last_msg or '北京' in last_msg or '上海' in last_msg:
                        # 上一条对话提到了位置
                        return f"请问您想了解{last_msg[:10]}的什么信息？\n\n您可以这样问：\n- 其他日期有货吗？\n- 10月有哪些日期有货？\n- 价格是多少？"
                    else:
                        return "请问您想了解什么？是查询某个位置的设备，还是某个日期的可用情况？\n\n您可以这样问：\n- 北京有货吗？\n- 上海10月18日有货吗？\n- 10月有哪些日期有货？"
                else:
                    # 没有历史对话
                    return "请问您想了解什么？是查询某个位置的设备，还是某个日期的可用情况？\n\n您可以这样问：\n- 北京有货吗？\n- 上海10月18日有货吗？\n- 10月有哪些日期有货？"
            else:
                return "请问您想查询哪个位置的设备？比如：北京、上海、广州等。\n\n您可以这样问：\n- 北京有货吗？\n- 上海10月18日有货吗？"
        elif date and not location and not location_from_context:
            # 有日期但没有位置，且上下文中也没有位置
            if is_elliptical:
                # 省略句，需要更多信息
                if recent_context:
                    # 有历史对话，尝试理解省略内容
                    last_msg = recent_context[-1].get('content', '') if recent_context else ''
                    if '重庆' in last_msg:
                        # 上一条对话提到了重庆
                        return f"关于{date}重庆的情况，正在为您查询..."
                        # 这里可以继续执行查询逻辑，使用重庆作为位置
                        location = '重庆'
                    elif '北京' in last_msg:
                        location = '北京'
                        return f"关于{date}北京的情况，正在为您查询..."
                    elif '上海' in last_msg:
                        location = '上海'
                        return f"关于{date}上海的情况，正在为您查询..."
                    else:
                        return f"关于{date}的信息，您想了解哪个位置的情况？\n\n您可以这样问：\n- {date}北京有货吗？\n- {date}上海有货吗？"
                else:
                    # 没有历史对话
                    return f"关于{date}的信息，您想了解哪个位置的情况？\n\n您可以这样问：\n- {date}北京有货吗？\n- {date}上海有货吗？"
            else:
                # 检查是否是日期范围查询
                if '到' in user_input or '-' in user_input or '~' in user_input:
                    return f"请问您想查询{date}前后哪个位置的设备？比如：北京、上海、广州等。\n\n您可以这样问：\n- {date}北京有货吗？\n- {date}上海有货吗？"
                else:
                    return f"请问您想查询{date}哪个位置的设备？比如：北京、上海、广州等。\n\n您可以这样问：\n- {date}北京有货吗？\n- {date}上海有货吗？"
        elif location and not date:
            # 有位置但没有日期，可以列出该位置的设备
            pass  # 继续执行后续逻辑
        
        # 如果没有飞书读取器，返回默认响应
        if not self.feishu_reader:
            if location:
                response = f"抱歉，无法查询'{location}'的设备信息，飞书API未配置。"
            elif date:
                response = f"抱歉，无法查询'{date}'的设备信息，飞书API未配置。"
            else:
                response = "请提供更多查询信息，如位置或日期。"
        else:
            try:
                # 获取设备数据
                data = self.feishu_reader._get_sheet_data()
                devices = data.get('device_data', [])
                
                # 处理查询可用日期的特殊情况
                if query_available_dates or date:
                    column_names = data.get('column_names', [])
                    
                    # 如果是查询整个月份的可用日期
                    if query_available_dates:
                        # 查询指定月份的可用日期和设备
                        available_dates = []
                        available_devices_by_date = {}
                        month_headers = data.get('month_headers', [])
                        
                        # 找到指定月份的所有日期列
                        month_dates = []
                        date_indices = []
                        
                        # 首先找到月份在month_headers中的位置
                        month_col_index = None
                        for i, header in enumerate(month_headers):
                            if header and query_month in str(header):
                                month_col_index = i
                                break
                        
                        # 如果找到了月份，获取该月份下的所有日期列
                        if month_col_index is not None:
                            # 从列名中获取该月份的所有日期
                            for i, col in enumerate(column_names):
                                # 跳过设备名称和位置列
                                if i < 2:
                                    continue
                                # 构造日期字符串
                                date_str = f"{query_month}月{col}日"
                                month_dates.append(date_str)
                                date_indices.append(i)
                        
                        # 检查每个日期有哪些设备可用
                        seen_dates = set()  # 避免重复日期
                        for date_str, date_idx in zip(month_dates, date_indices):
                            # 提取日期的唯一标识（如10月10日）
                            date_key = re.search(r'(\d+)月(\d+)日', date_str)
                            if date_key:
                                date_unique = f"{date_key.group(1)}月{date_key.group(2)}日"
                                if date_unique in seen_dates:
                                    continue
                                seen_dates.add(date_unique)
                            
                            available_devices = []
                            for device in devices:
                                # 检查设备是否在指定位置
                                if location and len(device) >= 2 and device[1] != location:
                                    continue
                                
                                # 检查设备在指定日期是否可用
                                if date_idx < len(device) and self.feishu_reader._is_device_available(device[date_idx]):
                                                                device_name = device[0]
                                                                if device_name not in available_devices:
                                                                    available_devices.append(device_name)                            
                            if available_devices:
                                available_dates.append(date_unique)
                                available_devices_by_date[date_unique] = available_devices
                        
                        if available_dates:
                            response = f"{query_month}月可用日期及设备：\n"
                            for date in sorted(available_dates, key=lambda x: int(re.search(r'(\d+)日', x).group(1))):
                                devices_list = available_devices_by_date[date]
                                response += f"\n{date}: {len(devices_list)}台设备可用\n"
                                for device in devices_list[:3]:  # 最多显示3台
                                    response += f"  - {device}\n"
                                if len(devices_list) > 3:
                                    response += f"  ... 还有{len(devices_list)-3}台\n"
                        else:
                            response = f"抱歉，{query_month}月没有可用的设备"
                    
                    # 如果是查询具体日期
                    elif date or date_range:
                                            # 如果是日期范围查询
                                            if date_range:
                                                response = f"{date_range[0]}到{date_range[-1]}{location if location else '所有位置'}可用设备：\n"
                                                all_available_devices = {}
                                                
                                                for query_date in date_range:
                                                    date_col = None
                                                    # 提取日期数字
                                                    date_nums = re.findall(r'(\d+)日', query_date)
                                                    if date_nums:
                                                        date_num = date_nums[0]
                                                        # 查找对应的列
                                                        for i, col in enumerate(column_names):
                                                            if str(col) == date_num:
                                                                date_col = i
                                                                break
                                                    
                                                    if date_col is not None:
                                                        available_devices = []
                                                        for device in devices:
                                                            # 检查设备是否在指定位置
                                                            if location and len(device) >= 2 and device[1] != location:
                                                                continue
                                                            
                                                            # 检查设备在指定日期是否可用
                                                            if date_col < len(device) and self.feishu_reader._is_device_available(device[date_col]):
                                                                device_name = device[0]
                                                                if device_name not in available_devices:
                                                                    available_devices.append(device_name)
                                                        
                                                        if available_devices:
                                                            all_available_devices[query_date] = available_devices
                                                
                                                if all_available_devices:
                                                    # 按日期汇总可用设备
                                                    device_availability = {}
                                                    for date_str, devices_list in all_available_devices.items():
                                                        for device in devices_list:
                                                            if device not in device_availability:
                                                                device_availability[device] = []
                                                            device_availability[device].append(date_str)
                                                    
                                                    # 显示每个设备的可用日期
                                                    for device, available_dates in device_availability.items():
                                                        if len(available_dates) == len(date_range):
                                                            # 整个期间都可用
                                                            response += f"{device}: 全部日期可用\n"
                                                        else:
                                                            # 部分日期可用
                                                            response += f"{device}: {', '.join(available_dates)}\n"
                                                else:
                                                    response = f"抱歉，{date_range[0]}到{date_range[-1]}{location if location else '所有位置'}没有可用设备"
                                            else:
                                                # 单个日期查询
                                                # 查找日期列
                                                date_col = None
                                                
                                                # 尝试多种方式匹配日期
                                                for i, col in enumerate(column_names):
                                                    col_str = str(col)
                                                    # 直接匹配
                                                    if date in col_str:
                                                        date_col = i
                                                        print(f"\n调试: 直接匹配找到列 '{col_str}' (索引: {i})")
                                                        break
                                                    # 尝试匹配日期中的数字（如"18"匹配"10月18日"）
                                                    date_nums = re.findall(r'(\d+)日?', date)
                                                    if date_nums:
                                                        date_num = date_nums[0]
                                                        if date_num in col_str:
                                                            date_col = i
                                                            print(f"\n调试: 数字匹配找到列 '{col_str}' (索引: {i}), 日期数字: {date_num}")
                                                            break
                                                
                                                if date_col is not None:
                                                    available_devices = []
                                                    for device in devices:
                                                        # 检查设备是否在指定位置
                                                        if location and len(device) >= 2 and device[1] != location:
                                                            continue
                                                        
                                                        # 检查设备在指定日期是否可用
                                                        if date_col < len(device) and self.feishu_reader._is_device_available(device[date_col]):
                                                            device_name = device[0]
                                                            if device_name not in available_devices:
                                                                available_devices.append(device_name)
                                                    
                                                    if available_devices:
                                                        location_text = f"{location}" if location else "所有位置"
                                                        response = f"{date}{location_text}可用设备：\n"
                                                        for i, device in enumerate(available_devices, 1):
                                                            response += f"{i}. {device}\n"
                                                    else:
                                                        location_text = f"{location}" if location else "所有位置"
                                                        response = f"抱歉，{date}{location_text}没有可用设备"
                    else:
                            # 如果没有找到日期列，显示可用的日期列
                            available_dates = []
                            for i, col in enumerate(column_names[2:], start=2):  # 跳过前两列
                                if col:
                                    available_dates.append(str(col))
                            
                            if available_dates:
                                response = f"抱歉，无法找到{date}的档期信息。\n\n可查询的日期包括：\n"
                                for d in available_dates[:10]:  # 最多显示10个
                                    response += f"  - {d}\n"
                                if len(available_dates) > 10:
                                    response += f"  ... 还有{len(available_dates)-10}个日期\n"
                                response += f"\n请使用上述格式查询，例如：'重庆{available_dates[0]}有货吗？'"
                            else:
                                response = f"抱歉，无法找到{date}的档期信息，且系统中没有可用的日期数据"
                        
                elif location:
                    # 如果有位置但没有具体日期，列出该位置的设备
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
                        
                elif date:
                    # 如果有日期但没有位置，查询该日期所有位置的设备
                    date_col = None
                    column_names = data.get('column_names', [])
                    
                    # 尝试多种方式匹配日期
                    for i, col in enumerate(column_names):
                        col_str = str(col)
                        # 直接匹配
                        if date in col_str:
                            date_col = i
                            break
                        # 尝试匹配日期中的数字（如"18"匹配"10月18日"）
                        date_nums = re.findall(r'(\d+)日?', date)
                        if date_nums:
                            date_num = date_nums[0]
                            if date_num in col_str:
                                date_col = i
                                break
                    
                    if date_col is not None:
                        location_stats = {}
                        for device in devices:
                            if date_col < len(device) and self.feishu_reader._is_device_available(device[date_col]):
                                device_location = device[1] if len(device) > 1 else '未知'
                                if device_location not in location_stats:
                                    location_stats[device_location] = []
                                location_stats[device_location].append(device[0])
                        
                        if location_stats:
                            response = f"{date}设备可用情况：\n"
                            for loc, dev_list in location_stats.items():
                                response += f"\n{loc}: {len(dev_list)}台可用\n"
                                for device in dev_list[:3]:  # 最多显示3台
                                    response += f"  - {device}\n"
                                if len(dev_list) > 3:
                                    response += f"  ... 还有{len(dev_list)-3}台\n"
                        else:
                            response = f"抱歉，{date}所有位置都没有可用设备"
                    else:
                        # 如果没有找到日期列，显示可用的日期列
                        available_dates = []
                        for i, col in enumerate(column_names[2:], start=2):  # 跳过前两列
                            if col:
                                available_dates.append(str(col))
                        
                        if available_dates:
                            response = f"抱歉，无法找到{date}的档期信息。\n\n可查询的日期包括：\n"
                            for d in available_dates[:10]:  # 最多显示10个
                                response += f"  - {d}\n"
                            if len(available_dates) > 10:
                                response += f"  ... 还有{len(available_dates)-10}个日期\n"
                            response += f"\n请使用上述格式查询，例如：'重庆{available_dates[0]}有货吗？'"
                        else:
                            response = f"抱歉，无法找到{date}的档期信息，且系统中没有可用的日期数据"
                else:
                    response = "请提供位置或日期信息，例如：'重庆有货吗？'或'10月18日有货吗？'"
                    
            except Exception as e:
                response = f"查询设备信息时出错: {str(e)}"
        
        # 保存对话到上下文
        self.context_manager.add_message_by_chat(self.chat_id, self.user_id, "test_item", "user", user_input)
        self.context_manager.add_message_by_chat(self.chat_id, self.user_id, "test_item", "assistant", response)
        
        return response
    
    def run(self):
        """运行对话测试"""
        print("=" * 50)
        print("闲鱼设备租赁助手 - 测试程序")
        print("=" * 50)
        print("\n输入 'quit' 或 'exit' 退出程序")
        print("输入 'debug' 查看飞书表格调试信息")
        print("输入 'clear' 清空对话历史")
        print("=" * 50)
        
        while True:
            try:
                user_input = input("\n您: ").strip()
                
                if user_input.lower() in ['quit', 'exit', '退出']:
                    print("\n感谢使用，再见！")
                    break
                
                if user_input.lower() == 'clear':
                    # ChatContextManager 没有直接的 clear_context 方法，
                    # 我们可以通过删除聊天记录来清空
                    print("\n对话历史已清空（功能待实现）")
                    continue
                
                # 处理debug命令
                if user_input.lower() == 'debug' and self.feishu_reader:
                    print("\n" + "=" * 30)
                    print("飞书表格调试信息")
                    print("=" * 30)
                    
                    try:
                        # 获取所有表格
                        sheets = self.feishu_reader.list_sheets()
                        total_devices = 0
                        location_stats = {}
                        
                        print(f"文档中共有 {len(sheets)} 个表格：")
                        
                        for sheet in sheets:
                            sheet_id = sheet.get('sheet_id')
                            sheet_name = sheet.get('sheet_name', '未命名')
                            print(f"\n--- 表格: {sheet_name} (ID: {sheet_id}) ---")
                            
                            # 临时创建读取器获取这个sheet的数据
                            temp_reader = FeishuSheetReader(
                                self.feishu_reader.app_id,
                                self.feishu_reader.app_secret,
                                self.feishu_reader.spreadsheet_token,
                                sheet_id
                            )
                            
                            try:
                                sheet_data = temp_reader._get_sheet_data()
                                device_count = len(sheet_data.get('device_data', []))
                                total_devices += device_count
                                print(f"  设备数量: {device_count}")
                                
                                # 统计这个sheet的位置信息
                                for row in sheet_data.get('device_data', []):
                                    if len(row) > 1:
                                        location = str(row[1])
                                        location_stats[location] = location_stats.get(location, 0) + 1
                                
                                # 如果是当前sheet，显示详细信息
                                if sheet_id == self.feishu_reader.sheet_id:
                                    print(f"  列名: {sheet_data.get('column_names', [])}")
                                    
                            except Exception as e:
                                print(f"  读取失败: {e}")
                        
                        print(f"\n=== 总计 ===")
                        print(f"所有表格总设备数: {total_devices}")
                        print("\n各位置设备统计（所有表格）:")
                        for location, count in sorted(location_stats.items()):
                            print(f"  {location}: {count} 台")
                        
                        # 显示佛山的所有设备（从当前sheet）
                        print("\n当前表格中佛山的设备详情:")
                        foshan_devices = self.feishu_reader.find_devices_by_location("佛山")
                        for device in foshan_devices:
                            print(f"  - {device['name']}")
                            
                    except Exception as e:
                        print(f"调试失败: {e}")
                    print("=" * 30)
                    continue
                
                if not user_input:
                    continue
                
                # 处理查询
                response = self.process_query(user_input)
                print(f"\n助手: {response}")
                
            except KeyboardInterrupt:
                print("\n\n程序被用户中断")
                break
            except Exception as e:
                print(f"\n错误: {str(e)}")

if __name__ == "__main__":
    test = ConversationTest()
    test.run()