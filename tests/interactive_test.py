#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
交互式功能测试：上下文功能、飞书信息获取功能、地区时间机器可用性查询
"""

import asyncio
import os
import sys
from datetime import datetime
from loguru import logger

# 添加项目路径
sys.path.append(os.path.join(os.path.dirname(__file__)))

from xianyu_bot_components.关键问题回复.intent_analyzer import IntentAnalyzer
from xianyu_bot_components.core.context_manager import ChatContextManager
from feishu_knowledge_base.feishu_sheet_reader import FeishuSheetReader


class InteractiveTester:
    """交互式测试器"""
    
    def __init__(self):
        """初始化测试器"""
        # 初始化上下文管理器
        self.context_manager = ChatContextManager()
        
        # 初始化意图分析器
        self.intent_analyzer = IntentAnalyzer(context_manager=self.context_manager)
        
        # 初始化飞书读取器，处理可能的配置缺失
        try:
            self.feishu_reader = FeishuSheetReader()
        except TypeError as e:
            # 如果缺少必要的配置参数，创建一个占位对象
            logger.warning(f"飞书读取器初始化失败，可能缺少配置: {e}")
            self.feishu_reader = None
        
        # 模拟用户ID和聊天ID
        self.user_id = "interactive_test_user"
        self.chat_id = "interactive_test_chat"
        
        # 设置日志
        logger.add("interactive_test.log", rotation="10 MB", level="INFO")
        
    def display_menu(self):
        """显示菜单"""
        print("\n" + "=" * 60)
        print("交互式功能测试菜单")
        print("=" * 60)
        print("1. 测试意图分析器 (语义分析)")
        print("2. 测试上下文管理功能")
        print("3. 测试飞书信息获取功能")
        print("4. 测试地区时间机器可用性查询")
        print("5. 模拟完整对话流程")
        print("6. 查看当前上下文实体")
        print("0. 退出")
        print("=" * 60)
    
    def test_intent_analysis(self):
        """测试意图分析器"""
        print("\n" + "-" * 50)
        print("测试意图分析器 (输入 'back' 返回菜单)")
        print("-" * 50)
        
        while True:
            question = input("\n请输入您的问题: ").strip()
            
            if question.lower() == 'back':
                break
                
            if not question:
                continue
                
            try:
                # 获取当前上下文
                context_entities = self.context_manager.get_all_entities(self.user_id, self.chat_id)
                context_str = f"上下文: {context_entities}" if context_entities else "无上下文"
                
                print(f"当前上下文: {context_str}")
                
                # 分析意图
                matched_agents, reason = self.intent_analyzer.analyze_intent(
                    question, 
                    context=context_str,
                    user_id=self.user_id,
                    chat_id=self.chat_id
                )
                
                print(f"问题: {question}")
                print(f"匹配Agent: {matched_agents}")
                print(f"分析原因: {reason}")
                
            except Exception as e:
                print(f"分析错误: {e}")
    
    def test_context_management(self):
        """测试上下文管理"""
        print("\n" + "-" * 50)
        print("测试上下文管理 (输入 'back' 返回菜单)")
        print("-" * 50)
        print("命令格式: <实体类型> <实体值>")
        print("例如: location 东莞, device 相机, date 2025-10-15")
        print("特殊命令: show (查看所有实体), clear (清除所有实体)")
        
        while True:
            cmd = input("\n请输入命令: ").strip()
            
            if cmd.lower() == 'back':
                break
            elif cmd.lower() == 'show':
                entities = self.context_manager.get_all_entities(self.user_id, self.chat_id)
                print(f"当前实体: {entities}")
            elif cmd.lower() == 'clear':
                # 通过存储空值来清除实体
                self.context_manager.user_contexts[self.user_id] = {}
                print("实体已清除")
            elif cmd:
                parts = cmd.split(' ', 1)
                if len(parts) >= 2:
                    entity_type, entity_value = parts[0], parts[1]
                    self.context_manager.store_entity(self.user_id, self.chat_id, entity_type, entity_value)
                    print(f"已存储实体: {entity_type} = {entity_value}")
                    
                    # 显示更新后的实体
                    entities = self.context_manager.get_all_entities(self.user_id, self.chat_id)
                    print(f"当前所有实体: {entities}")
                else:
                    print("格式错误，请使用: <实体类型> <实体值>")
    
    def test_feishu_functionality(self):
        """测试飞书功能"""
        print("\n" + "-" * 50)
        print("测试飞书信息获取功能")
        print("-" * 50)
        
        if self.feishu_reader is None:
            print("飞书读取器未初始化，可能缺少API配置")
            print("请确保在.env文件中配置了以下参数:")
            print("  - FEISHU_APP_ID")
            print("  - FEISHU_APP_SECRET")
            print("  - FEISHU_SPREADSHEET_TOKEN")
            print("  - FEISHU_SHEET_ID")
            print("\n跳过飞书功能测试")
            return
        
        try:
            print("正在获取飞书设备数据...")
            
            # 获取所有设备
            devices = self.feishu_reader.get_all_devices()
            print(f"总设备数量: {len(devices)}")
            
            if devices:
                print("\n前10个设备:")
                for i, device in enumerate(devices[:10], 1):
                    print(f"  {i}. {device}")
            
            # 演示按地点查询
            print("\n按地点查询示例:")
            locations = ["东莞", "南京", "上海", "北京"]  # 使用常见的地点进行测试
            for loc in locations:
                if self.feishu_reader:
                    loc_devices = self.feishu_reader.find_devices_by_location(loc)
                    print(f"  {loc}地区设备: {len(loc_devices)}个")
                    if loc_devices:
                        print(f"    例如: {loc_devices[:2]}")  # 显示前2个
                else:
                    print(f"  {loc}地区设备: 飞书API未配置")
            
            # 演示按日期查询
            print("\n按日期查询示例:")
            test_dates = ["2025-12-25", "2025-12-26", "2025-12-27"]
            for date in test_dates:
                if self.feishu_reader:
                    available = self.feishu_reader.find_available_devices_by_date(date)
                    print(f"  {date}可用设备: {len(available)}个")
                    if available:
                        print(f"    例如: {available[:2]}")  # 显示前2个
                else:
                    print(f"  {date}可用设备: 飞书API未配置")
            
            print("\n注意: 如果没有配置飞书API或没有数据，上述结果可能为空")
            
        except Exception as e:
            print(f"飞书功能测试错误: {e}")
            print("请检查飞书API配置是否正确")
    
    def test_location_time_queries(self):
        """测试地区时间查询"""
        print("\n" + "-" * 50)
        print("测试地区时间机器可用性查询")
        print("-" * 50)
        print("模拟用户询问不同地区和时间的设备可用性")
        
        # 预设查询场景
        scenarios = [
            ("东莞", "2025-10-15", "询问特定地区和时间的设备可用性"),
            ("南京", "2025-11-20", "询问另一个城市的设备情况"),
            ("上海", "2025-12-25", "询问节假日的设备情况")
        ]
        
        for location, date, description in scenarios:
            print(f"\n场景: {description}")
            print(f"地点: {location}, 日期: {date}")
            
            try:
                # 先存储上下文
                self.context_manager.store_entity(self.user_id, self.chat_id, "location", location)
                self.context_manager.store_entity(self.user_id, self.chat_id, "time_reference", date)
                
                # 模拟用户查询
                query = f"{location}{date.split('-')[2]}号有设备吗"
                print(f"用户查询: {query}")
                
                # 分析意图
                matched_agents, reason = self.intent_analyzer.analyze_intent(
                    query,
                    context=f"用户位置: {location}",
                    user_id=self.user_id,
                    chat_id=self.chat_id
                )
                
                print(f"匹配Agent: {matched_agents}")
                print(f"分析原因: {reason}")
                
                # 如果匹配到租赁顾问，尝试获取飞书数据
                if "智能租赁顾问Agent" in matched_agents:
                    print(f"  ✓ 正确识别为设备租赁查询")
                    if self.feishu_reader:
                        # 尝试获取该地区和日期的数据
                        loc_devices = self.feishu_reader.find_devices_by_location(location)
                        available_on_date = self.feishu_reader.find_available_devices_by_date(date)
                        print(f"  {location}地区设备: {len(loc_devices)}个")
                        print(f"  {date}可用设备: {len(available_on_date)}个")
                    else:
                        print(f"  {location}地区设备: 飞书API未配置")
                        print(f"  {date}可用设备: 飞书API未配置")
            except Exception as e:
                print(f"  错误: {e}")
    
    def simulate_conversation(self):
        """模拟完整对话流程"""
        print("\n" + "-" * 50)
        print("模拟完整对话流程")
        print("-" * 50)
        print("这将模拟一个用户询问设备租赁的完整对话")
        
        # 清空上下文
        self.context_manager.user_contexts[self.user_id] = {}
        
        # 对话流程
        conversation = [
            ("我想租个设备", "general"),
            ("东莞有货吗", "location_inquiry"),
            ("10月15号可以租吗", "date_inquiry"),
            ("有什么型号的", "device_inquiry"),
            ("那10月20号呢", "date_followup"),
            ("南京的设备怎么样", "location_followup"),
            ("今天天气怎样", "unrelated")
        ]
        
        for i, (message, msg_type) in enumerate(conversation, 1):
            print(f"\n{i}. 用户: {message}")
            
            # 根据消息类型更新上下文
            if "东莞" in message:
                self.context_manager.store_entity(self.user_id, self.chat_id, "location", "东莞")
            elif "南京" in message:
                self.context_manager.store_entity(self.user_id, self.chat_id, "location", "南京")
            
            if "10月15" in message:
                self.context_manager.store_entity(self.user_id, self.chat_id, "time_reference", "2025-10-15")
            elif "10月20" in message:
                self.context_manager.store_entity(self.user_id, self.chat_id, "time_reference", "2025-10-20")
            
            if "设备" in message or "型号" in message:
                self.context_manager.store_entity(self.user_id, self.chat_id, "device_type", "通用设备")
            
            # 分析意图
            try:
                current_context = self.context_manager.get_all_entities(self.user_id, self.chat_id)
                matched_agents, reason = self.intent_analyzer.analyze_intent(
                    message,
                    context=f"当前上下文: {current_context}",
                    user_id=self.user_id,
                    chat_id=self.chat_id
                )
                
                print(f"   类型: {msg_type}")
                print(f"   匹配Agent: {matched_agents}")
                print(f"   分析原因: {reason}")
                print(f"   当前上下文: {current_context}")
                
            except Exception as e:
                print(f"   错误: {e}")
    
    def show_current_context(self):
        """显示当前上下文"""
        print("\n" + "-" * 50)
        print("当前上下文实体")
        print("-" * 50)
        
        entities = self.context_manager.get_all_entities(self.user_id, self.chat_id)
        if entities:
            print("当前存储的实体:")
            for entity_type, entity_value in entities.items():
                print(f"  {entity_type}: {entity_value}")
        else:
            print("当前没有存储的实体")
    
    def run(self):
        """运行交互式测试"""
        print("欢迎使用交互式功能测试!")
        print(f"开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        while True:
            self.display_menu()
            
            try:
                choice = input("\n请选择功能 (0-6): ").strip()
                
                if choice == '1':
                    self.test_intent_analysis()
                elif choice == '2':
                    self.test_context_management()
                elif choice == '3':
                    self.test_feishu_functionality()
                elif choice == '4':
                    self.test_location_time_queries()
                elif choice == '5':
                    self.simulate_conversation()
                elif choice == '6':
                    self.show_current_context()
                elif choice == '0':
                    print("\n感谢使用交互式功能测试！")
                    break
                else:
                    print("\n无效选择，请输入 0-6 之间的数字")
                    
            except KeyboardInterrupt:
                print("\n\n程序被用户中断")
                break
            except Exception as e:
                print(f"\n发生错误: {e}")


def main():
    """主函数"""
    tester = InteractiveTester()
    tester.run()


if __name__ == "__main__":
    main()
