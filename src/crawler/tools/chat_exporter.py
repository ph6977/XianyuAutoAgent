"""
聊天记录导出工具 - 导出聊天记录到CSV文件
"""

import csv
import os
import time
from datetime import datetime
from typing import List, Dict, Optional
from loguru import logger

from core.context_manager import ChatContextManager


class ChatHistoryExporter:
    """聊天记录导出器"""

    def __init__(self, db_path: str = "chat_history.json"):
        self.context_manager = ChatContextManager(db_path)

    def export_all_chats_to_csv(self, output_dir: str = "exports") -> Optional[str]:
        """导出所有聊天记录到CSV文件"""
        try:
            data = self.context_manager._load_db()
            chats_dict = data["chats"]
            if not chats_dict:
                logger.warning("没有找到聊天记录")
                return None

            # 创建输出目录
            os.makedirs(output_dir, exist_ok=True)

            # 生成文件名
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"xianyu_chats_{timestamp}.csv"
            filepath = os.path.join(output_dir, filename)

            with open(filepath, 'w', newline='', encoding='utf-8-sig') as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow([
                    '会话ID', '商品ID', '用户ID', '消息角色', '消息内容',
                    '时间戳', '议价次数', '创建时间', '最后更新时间'
                ])

                for chat_id, chat in chats_dict.items():
                    for message in chat['messages']:
                        # 处理可能缺失的字段
                        created_at = chat.get('created_at', data.get('metadata', {}).get('created_at', message['timestamp']))
                        last_updated = chat.get('last_updated', message['timestamp'])

                        writer.writerow([
                            chat_id,
                            chat['item_id'],
                            chat['user_id'],
                            message['role'],
                            message['content'],
                            datetime.fromtimestamp(message['timestamp']).strftime('%Y-%m-%d %H:%M:%S'),
                            chat['bargain_count'],
                            datetime.fromtimestamp(created_at).strftime('%Y-%m-%d %H:%M:%S'),
                            datetime.fromtimestamp(last_updated).strftime('%Y-%m-%d %H:%M:%S')
                        ])

            logger.info(f"成功导出 {len(chats_dict)} 个会话到 {filepath}")
            return filepath

        except Exception as e:
            logger.error(f"导出聊天记录失败: {e}")
            return None

    def export_chat_by_id_to_csv(self, chat_id: str, output_dir: str = "exports") -> Optional[str]:
        """导出特定会话的聊天记录到CSV文件"""
        try:
            chats = self.context_manager.get_all_chats()
            target_chat = None

            for chat in chats:
                if chat['chat_id'] == chat_id:
                    target_chat = chat
                    break

            if not target_chat:
                logger.warning(f"未找到会话ID为 {chat_id} 的聊天记录")
                return None

            # 创建输出目录
            os.makedirs(output_dir, exist_ok=True)

            # 生成文件名
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"xianyu_chat_{chat_id}_{timestamp}.csv"
            filepath = os.path.join(output_dir, filename)

            with open(filepath, 'w', newline='', encoding='utf-8-sig') as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow([
                    '会话ID', '商品ID', '用户ID', '消息角色', '消息内容',
                    '时间戳', '议价次数', '创建时间', '最后更新时间'
                ])

                for message in target_chat['messages']:
                    writer.writerow([
                        target_chat['chat_id'],
                        target_chat['item_id'],
                        target_chat['user_id'],
                        message['role'],
                        message['content'],
                        datetime.fromtimestamp(message['timestamp']).strftime('%Y-%m-%d %H:%M:%S'),
                        target_chat['bargain_count'],
                        datetime.fromtimestamp(target_chat['created_at']).strftime('%Y-%m-%d %H:%M:%S'),
                        datetime.fromtimestamp(target_chat['last_updated']).strftime('%Y-%m-%d %H:%M:%S')
                    ])

            logger.info(f"成功导出会话 {chat_id} 到 {filepath}")
            return filepath

        except Exception as e:
            logger.error(f"导出会话失败: {e}")
            return None

    def export_chat_summary_to_csv(self, output_dir: str = "exports") -> Optional[str]:
        """导出会话摘要到CSV文件"""
        try:
            chats = self.context_manager.get_all_chats()
            if not chats:
                logger.warning("没有找到聊天记录")
                return None

            # 创建输出目录
            os.makedirs(output_dir, exist_ok=True)

            # 生成文件名
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"xianyu_summary_{timestamp}.csv"
            filepath = os.path.join(output_dir, filename)

            with open(filepath, 'w', newline='', encoding='utf-8-sig') as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow([
                    '会话ID', '商品ID', '用户ID', '消息数量', '议价次数',
                    '创建时间', '最后更新时间', '最后消息时间'
                ])

                for chat in chats:
                    last_message_time = None
                    if chat['messages']:
                        last_message_time = max(msg['timestamp'] for msg in chat['messages'])

                    writer.writerow([
                        chat['chat_id'],
                        chat['item_id'],
                        chat['user_id'],
                        len(chat['messages']),
                        chat['bargain_count'],
                        datetime.fromtimestamp(chat['created_at']).strftime('%Y-%m-%d %H:%M:%S'),
                        datetime.fromtimestamp(chat['last_updated']).strftime('%Y-%m-%d %H:%M:%S'),
                        datetime.fromtimestamp(last_message_time).strftime('%Y-%m-%d %H:%M:%S') if last_message_time else 'N/A'
                    ])

            logger.info(f"成功导出会话摘要到 {filepath}")
            return filepath

        except Exception as e:
            logger.error(f"导出会话摘要失败: {e}")
            return None

    def list_all_chats(self) -> List[Dict]:
        """列出所有会话"""
        data = self.context_manager._load_db()
        chats_dict = data["chats"]
        result = []

        for chat_id, chat in chats_dict.items():
            chat_info = {
                'chat_id': chat_id,
                'item_id': chat['item_id'],
                'user_id': chat['user_id'],
                'message_count': len(chat['messages']),
                'bargain_count': chat['bargain_count'],
                'last_message_time': None
            }

            if chat['messages']:
                last_message_time = max(msg['timestamp'] for msg in chat['messages'])
                chat_info['last_message_time'] = datetime.fromtimestamp(last_message_time).strftime('%Y-%m-%d %H:%M:%S')

            result.append(chat_info)

        return result

    def get_chat_statistics(self) -> Dict:
        """获取聊天统计信息"""
        return self.context_manager.get_chat_statistics()