#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
对话上下文管理器 - 管理聊天历史和商品信息
"""

import json
import os
import time
from typing import List, Dict, Optional
from loguru import logger


class ChatContextManager:
    """聊天上下文管理器"""

    def __init__(self, db_path: str = "chat_history.json"):
        self.db_path = db_path
        self._ensure_db_exists()
        # 添加会话实体映射，用于追踪对话中的重要实体
        self.session_entities = {}

    def _ensure_db_exists(self):
        """确保数据库文件存在"""
        if not os.path.exists(self.db_path):
            with open(self.db_path, 'w', encoding='utf-8') as f:
                json.dump({
                    "chats": {},
                    "items": {},
                    "metadata": {
                        "created_at": time.time(),
                        "last_updated": time.time()
                    }
                }, f, ensure_ascii=False, indent=2)

    def _get_session_key(self, user_id: str, chat_id: str = None) -> str:
        """获取会话键值，优先使用chat_id，否则使用user_id"""
        return chat_id if chat_id else user_id

    def store_multiple_locations(self, user_id: str, chat_id: str, locations: List[str], ttl: int = 3600):
        """存储多个位置到会话上下文中"""
        session_key = self._get_session_key(user_id, chat_id)
        
        if session_key not in self.session_entities:
            self.session_entities[session_key] = {}
        
        if 'locations' not in self.session_entities[session_key]:
            self.session_entities[session_key]['locations'] = []
        
        # 添加新的位置，记录时间戳
        current_time = time.time()
        for location in locations:
            self.session_entities[session_key]['locations'].append({
                'location': location,
                'timestamp': current_time
            })
        
        # 设置过期时间
        self.session_entities[session_key]['expire_time'] = current_time + ttl

    def get_location_list(self, user_id: str, chat_id: str) -> List[str]:
        """获取会话中的所有位置"""
        session_key = self._get_session_key(user_id, chat_id)
        
        if session_key not in self.session_entities:
            return []
        
        if 'locations' not in self.session_entities[session_key]:
            return []
        
        # 返回所有位置，按时间戳排序
        locations = [loc['location'] for loc in self.session_entities[session_key]['locations']]
        return locations

    def get_latest_location(self, user_id: str, chat_id: str) -> Optional[str]:
        """获取最新提及的位置"""
        locations = self.get_location_list(user_id, chat_id)
        if locations:
            # 返回列表中的最后一个位置（最新提及的）
            return locations[-1]
        return None

    def detect_location_ambiguity(self, user_id: str, chat_id: str) -> bool:
        """检测是否存在位置歧义"""
        locations = self.get_location_list(user_id, chat_id)
        return len(locations) > 1