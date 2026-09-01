#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
飞书设备库存交互式查询机器人
用户可以输入问题询问产品情况，程序会调用大模型并读取飞书中的信息来回复
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


class InteractiveFeishuBot:
    """交互式飞书设备查询机器人"""
    
    def __init__(self):
        """初始化机器人"""
        # 初始化飞书读取器
        app_id = os.getenv("FEISHU_APP_ID")
        app_secret = os.getenv("FEISHU_APP_SECRET")
        spreadsheet_token = os.getenv("FEISHU_SPREADSHEET_TOKEN")
        sheet_id = os.getenv("FEISHU_SHEET_ID")
        
        if not all([app_id, app_secret, spreadsheet_token, sheet_id]):
            raise ValueError("飞书API配置不完整，请检查.env文件中的配置")
        
        self.feishu_reader = FeishuSheetReader(app_id, app_secret, spreadsheet_token, sheet_id)
        
        # 初始化大模型客户端
        api_key = os.getenv("API_KEY")
        base_url = os.getenv("MODEL_BASE_URL")
        model_name = os.getenv("MODEL_NAME")
        
        if not all([api_key, base_url, model_name]):
            raise ValueError("大模型API配置不完整，请检查.env文件中的配置")
        
        self.client = OpenAI(
            api_key=api_key,
            base_url=base_url
        )
        self.model_name = model_name
        
        # 系统提示词
        self.system_prompt = """你是一个专业的设备租赁顾问，能够根据飞书多维表格中的设备库存信息回答用户的问题。
        
        表格结构说明：
        - 第一行为月份标识（如"10月"、"11月"）
        - 第二行为列名（"机型"、"所在地"、1-31日期数字等）
        - 第三行开始为设备数据行
        
        设备状态说明：
        - 空白/None/空字符串：设备在仓库中，可出租
        - 数字1：设备在物流中（寄出），不可租赁
        - 数字2：设备在客户手中，产生租赁，不可租赁
        - 数字3：设备在物流中（寄回），不可租赁
        
        请根据用户的问题，结合飞书表格中的设备库存数据，提供准确、专业的回答。
        如果用户询问特定日期的设备可用性，请查询对应日期的设备状态。
        如果用户询问特定位置的设备，请根据"所在地"字段回答。
        """
        
        logger.info("交互式飞书设备查询机器人初始化完成")
    
    def get_feishu_data_summary(self) -> str:
        """获取飞书表格数据摘要"""
        try:
            data = self.feishu_reader._get_sheet_data()
            if not data:
                return "无法获取飞书表格数据"
            
            device_data = data.get('device_data', [])
            column_names = data.get('column_names', [])
            
            summary = "设备库存摘要：\n"
            summary += f"总设备数量：{len(device_data)}\n"
            
            if device_data:
                summary += "设备列表：\n"
                for i, row in enumerate(device_data[:10]):  # 显示前10个设备
                    if len(row) >= 2:
                        device_name = row[0] if len(row) > 0 else "未知"
                        location = row[1] if len(row) > 1 else "未知位置"
                        summary += f"- {device_name} (位置：{location})\n"
                
                if len(device_data) > 10:
                    summary += f"... 还有 {len(device_data) - 10} 个设备未显示\n"
            
            if column_names:
                summary += f"日期范围：{column_names[2] if len(column_names) > 2 else '未知'} 到 {column_names[-1] if len(column_names) > 0 else '未知'}\n"
            
            return summary
            
        except Exception as e:
            logger.error(f"获取飞书数据摘要失败: {e}")
            return f"获取飞书数据失败: {e}"
    
    def query_devices_by_user_question(self, question: str) -> str:
        """根据用户问题查询设备信息"""
        try:
            # 分析用户问题，提取关键信息
            locations = ["北京", "上海", "广州", "深圳", "杭州", "佛山", "东莞", "成都", "武汉", "西安"]
            location_found = None
            for loc in locations:
                if loc in question:
                    location_found = loc
                    break
            
            # 检查是否包含日期相关关键词
            date_keywords = ["月", "日", "号", "今天", "明天", "后天", "这周", "下周"]
            date_found = None
            for keyword in date_keywords:
                if keyword in question:
                    # 这里可以进一步解析具体日期，为简化我们使用当前日期
                    date_found = datetime.now().strftime('%Y-%m-%d')
                    break
            
            # 获取设备数据
            result = self.feishu_reader._get_sheet_data()
            if not result:
                return "无法获取设备数据"
            
            device_data = result.get('device_data', [])
            available_devices = []
            
            # 如果有位置要求，筛选对应位置的设备
            if location_found:
                for row in device_data:
                    if len(row) > 1 and location_found in str(row[1]):
                        # 检查设备在指定日期的可用性
                        if date_found:
                            device_name = row[0] if len(row) > 0 else "未知设备"
                            status = self.feishu_reader.find_device_status_by_date(device_name, date_found)
                            if self.feishu_reader._is_device_available(status):
                                available_devices.append({
                                    'name': device_name,
                                    'location': row[1],
                                    'status': status
                                })
                        else:
                            # 如果没有指定日期，检查当前日期的可用性
                            current_date = datetime.now().strftime('%Y-%m-%d')
                            device_name = row[0] if len(row) > 0 else "未知设备"
                            status = self.feishu_reader.find_device_status_by_date(device_name, current_date)
                            if self.feishu_reader._is_device_available(status):
                                available_devices.append({
                                    'name': device_name,
                                    'location': row[1],
                                    'status': status
                                })
            else:
                # 如果没有位置要求，检查所有设备
                for row in device_data:
                    device_name = row[0] if len(row) > 0 else "未知设备"
                    location = row[1] if len(row) > 1 else "未知位置"
                    
                    if date_found:
                        status = self.feishu_reader.find_device_status_by_date(device_name, date_found)
                    else:
                        current_date = datetime.now().strftime('%Y-%m-%d')
                        status = self.feishu_reader.find_device_status_by_date(device_name, current_date)
                    
                    if self.feishu_reader._is_device_available(status):
                        available_devices.append({
                            'name': device_name,
                            'location': location,
                            'status': status
                        })
            
            # 生成结果摘要
            if available_devices:
                result_summary = f"根据您的查询 '{question}'，找到以下可用设备：\n"
                for device in available_devices[:10]:  # 最多显示10个
                    result_summary += f"- {device['name']} (位置：{device['location']})\n"
                
                if len(available_devices) > 10:
                    result_summary += f"... 还有 {len(available_devices) - 10} 个设备\n"
            else:
                result_summary = f"根据您的查询 '{question}'，没有找到符合条件的可用设备。"
            
            return result_summary
            
        except Exception as e:
            logger.error(f"查询设备失败: {e}")
            return f"查询设备时出现错误：{e}"
    
    def chat_with_ai(self, user_question: str) -> str:
        """与AI进行对话"""
        try:
            # 获取飞书数据摘要
            feishu_data = self.get_feishu_data_summary()
            
            # 根据用户问题查询具体设备信息
            device_query_result = self.query_devices_by_user_question(user_question)
            
            # 构建AI提示词
            messages = [
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": f"""飞书表格设备库存信息：
{feishu_data}

根据用户问题查询到的具体设备信息：
{device_query_result}

用户问题：{user_question}

请结合以上信息，用专业、友好的语气回答用户的问题。如果用户询问设备可用性，请明确告知哪些设备可用、位置在哪里。如果用户询问价格或其他信息，请告知暂时无法提供，需要进一步咨询。"""}
            ]
            
            # 调用大模型
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                temperature=0.7,
                max_tokens=500
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            logger.error(f"AI对话失败: {e}")
            return f"抱歉，AI对话时出现错误：{e}"
    
    def run_interactive_session(self):
        """运行交互式会话"""
        print("=" * 60)
        print("🤖 飞书设备库存交互式查询机器人")
        print("=" * 60)
        print("您可以输入关于设备的问题，例如：")
        print("- 佛山有哪些设备？")
        print("- 10月15日北京有设备可用吗？")
        print("- 查询可用的设备")
        print("- 今天有什么设备可以租用？")
        print("- 输入 'quit' 或 'exit' 退出程序")
        print("=" * 60)
        
        while True:
            try:
                user_input = input("\n您: ").strip()
                
                if not user_input:
                    print("请输入您的问题。")
                    continue
                
                if user_input.lower() in ['quit', 'exit', '退出', 'q']:
                    print("👋 感谢使用飞书设备查询机器人，再见！")
                    break
                
                print("\n机器人正在思考...")
                
                # 获取AI回复
                ai_response = self.chat_with_ai(user_input)
                print(f"🤖 机器人: {ai_response}")
                
            except KeyboardInterrupt:
                print("\n\n👋 程序被用户中断，再见！")
                break
            except Exception as e:
                print(f"\n❌ 程序出现错误: {e}")
                logger.error(f"交互式会话错误: {e}")


def main():
    """主函数"""
    print("🚀 启动飞书设备库存交互式查询机器人...")
    
    try:
        bot = InteractiveFeishuBot()
        bot.run_interactive_session()
    except Exception as e:
        print(f"❌ 机器人初始化失败: {e}")
        logger.error(f"机器人初始化失败: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
