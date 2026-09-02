#!/usr/bin/env python3
"""
独立聊天记录查询工具
可以独立运行，无需启动闲鱼机器人主程序
"""

import os
import sys
import json
import pandas as pd
from datetime import datetime
from loguru import logger


class ChatQueryTool:
    """聊天记录查询工具"""

    def __init__(self):
        self.chat_history_file = "chat_history.json"
        self.output_dir = "output"

        # 确保输出目录存在
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)

    def load_chat_history(self):
        """加载聊天记录数据"""
        if not os.path.exists(self.chat_history_file):
            logger.warning(f"聊天记录文件不存在: {self.chat_history_file}")
            return {}

        try:
            with open(self.chat_history_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            logger.info(f"成功加载聊天记录，共 {len(data.get('chats', {}))} 个会话")
            return data
        except Exception as e:
            logger.error(f"加载聊天记录失败: {e}")
            return {}

    def list_all_chats(self):
        """列出所有会话"""
        data = self.load_chat_history()
        chats = data.get('chats', {})

        if not chats:
            print("没有找到任何会话记录")
            return []

        print(f"\n共找到 {len(chats)} 个会话:")
        print("-" * 100)

        chat_list = []
        for i, (chat_id, chat_data) in enumerate(chats.items(), 1):
            user_id = chat_data.get('user_id', '未知')
            item_id = chat_data.get('item_id', '未知')
            messages = chat_data.get('messages', [])
            bargain_count = chat_data.get('bargain_count', 0)

            # 获取最后消息时间
            last_message_time = None
            if messages:
                last_message = messages[-1]
                timestamp = last_message.get('timestamp')
                if timestamp:
                    last_message_time = datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')

            print(f"{i}. 会话ID: {chat_id}")
            print(f"   用户ID: {user_id}")
            print(f"   商品ID: {item_id}")
            print(f"   消息数: {len(messages)}")
            print(f"   议价次数: {bargain_count}")
            print(f"   最后消息: {last_message_time or 'N/A'}")
            print("-" * 100)

            chat_list.append({
                'chat_id': chat_id,
                'user_id': user_id,
                'item_id': item_id,
                'message_count': len(messages),
                'bargain_count': bargain_count,
                'last_message_time': last_message_time
            })

        return chat_list

    def show_chat_statistics(self):
        """显示统计信息"""
        data = self.load_chat_history()
        chats = data.get('chats', {})

        if not chats:
            print("没有找到任何会话记录")
            return

        total_messages = 0
        total_bargain_count = 0
        latest_chat_time = None

        for chat_data in chats.values():
            messages = chat_data.get('messages', [])
            total_messages += len(messages)
            total_bargain_count += chat_data.get('bargain_count', 0)

            # 查找最新消息时间
            if messages:
                last_message = messages[-1]
                timestamp = last_message.get('timestamp')
                if timestamp:
                    message_time = datetime.fromtimestamp(timestamp)
                    if latest_chat_time is None or message_time > latest_chat_time:
                        latest_chat_time = message_time

        avg_messages = total_messages / len(chats) if chats else 0
        latest_time_str = latest_chat_time.strftime('%Y-%m-%d %H:%M:%S') if latest_chat_time else 'N/A'

        print(f"\n聊天记录统计信息:")
        print(f"   总会话数: {len(chats)}")
        print(f"   总消息数: {total_messages}")
        print(f"   总议价次数: {total_bargain_count}")
        print(f"   平均每会话消息数: {avg_messages:.2f}")
        print(f"   最新会话时间: {latest_time_str}")

    def search_chat_by_keyword(self, keyword):
        """根据关键词搜索聊天记录"""
        data = self.load_chat_history()
        chats = data.get('chats', {})

        if not chats:
            print(f"📭 没有找到包含关键词 '{keyword}' 的聊天记录")
            return []

        results = []
        for chat_id, chat_data in chats.items():
            messages = chat_data.get('messages', [])
            for message in messages:
                content = message.get('content', '')
                if keyword.lower() in content.lower():
                    results.append({
                        'chat_id': chat_id,
                        'user_id': chat_data.get('user_id', '未知'),
                        'item_id': chat_data.get('item_id', '未知'),
                        'role': message.get('role', '未知'),
                        'content': content,
                        'timestamp': message.get('timestamp')
                    })

        if not results:
            print(f"没有找到包含关键词 '{keyword}' 的聊天记录")
            return []

        print(f"\n找到 {len(results)} 条包含关键词 '{keyword}' 的消息:")
        print("-" * 120)

        for i, result in enumerate(results, 1):
            time_str = datetime.fromtimestamp(result['timestamp']).strftime('%Y-%m-%d %H:%M:%S') if result['timestamp'] else 'N/A'
            print(f"{i}. 会话ID: {result['chat_id']}")
            print(f"   用户ID: {result['user_id']}")
            print(f"   商品ID: {result['item_id']}")
            print(f"   角色: {result['role']}")
            print(f"   时间: {time_str}")
            print(f"   内容: {result['content']}")
            print("-" * 120)

        return results

    def view_chat_detail(self, chat_id):
        """查看特定会话的详细内容"""
        data = self.load_chat_history()
        chats = data.get('chats', {})

        if chat_id not in chats:
            print(f"未找到会话ID为 '{chat_id}' 的聊天记录")
            return None

        chat_data = chats[chat_id]
        messages = chat_data.get('messages', [])

        if not messages:
            print(f"会话 '{chat_id}' 中没有消息记录")
            return None

        print(f"\n会话 {chat_id} 的详细内容:")
        print(f"用户ID: {chat_data.get('user_id', '未知')}")
        print(f"商品ID: {chat_data.get('item_id', '未知')}")
        print(f"议价次数: {chat_data.get('bargain_count', 0)}")
        print("-" * 80)

        for i, message in enumerate(messages, 1):
            role = message.get('role', '未知')
            content = message.get('content', '')
            timestamp = message.get('timestamp')
            time_str = datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S') if timestamp else 'N/A'

            role_display = "用户" if role == "user" else "机器人"
            print(f"{i}. {role_display} - {time_str}")
            print(f"   {content}")
            print("-" * 80)

        return chat_data

    def export_all_chats_to_csv(self):
        """导出所有聊天记录到CSV"""
        data = self.load_chat_history()
        chats = data.get('chats', {})

        if not chats:
            print("没有聊天记录可导出")
            return None

        # 准备数据
        records = []
        for chat_id, chat_data in chats.items():
            messages = chat_data.get('messages', [])
            for message in messages:
                timestamp = message.get('timestamp')
                time_str = datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S') if timestamp else ''

                records.append({
                    'chat_id': chat_id,
                    'user_id': chat_data.get('user_id', ''),
                    'item_id': chat_data.get('item_id', ''),
                    'role': message.get('role', ''),
                    'content': message.get('content', ''),
                    'timestamp': time_str,
                    'bargain_count': chat_data.get('bargain_count', 0)
                })

        # 导出到CSV
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"{self.output_dir}/chat_query_export_{timestamp}.csv"

        df = pd.DataFrame(records)
        df.to_csv(filename, index=False, encoding='utf-8-sig')

        print(f"成功导出 {len(records)} 条聊天记录到: {filename}")
        return filename

    def show_help(self):
        """显示帮助信息"""
        print("""
独立聊天记录查询工具

使用方法:
  python tools/chat_query.py list              # 列出所有会话
  python tools/chat_query.py stats             # 显示统计信息
  python tools/chat_query.py search <关键词>    # 搜索聊天记录
  python tools/chat_query.py view <会话ID>      # 查看会话详情
  python tools/chat_query.py export            # 导出所有聊天记录到CSV
  python tools/chat_query.py help              # 显示此帮助信息

说明:
- 此工具可以独立运行，无需启动闲鱼机器人主程序
- 数据来源: chat_history.json
- 导出文件保存在 output/ 目录下
""")


def main():
    """主函数"""
    # 配置日志
    logger.remove()
    logger.add(sys.stderr, level="INFO")

    query_tool = ChatQueryTool()

    if len(sys.argv) < 2:
        query_tool.show_help()
        return

    command = sys.argv[1]

    if command == "list":
        query_tool.list_all_chats()

    elif command == "stats":
        query_tool.show_chat_statistics()

    elif command == "search":
        if len(sys.argv) < 3:
            print("请指定搜索关键词，例如: python tools/chat_query.py search 价格")
            return
        keyword = sys.argv[2]
        query_tool.search_chat_by_keyword(keyword)

    elif command == "view":
        if len(sys.argv) < 3:
            print("请指定会话ID，例如: python tools/chat_query.py view 123456789")
            return
        chat_id = sys.argv[2]
        query_tool.view_chat_detail(chat_id)

    elif command == "export":
        query_tool.export_all_chats_to_csv()

    elif command in ["help", "--help", "-h"]:
        query_tool.show_help()

    else:
        print(f"未知命令: {command}")
        query_tool.show_help()


if __name__ == '__main__':
    main()