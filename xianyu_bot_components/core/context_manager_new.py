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

    def store_entity(self, user_id: str, chat_id: str, entity_type: str, entity_value: str, ttl: int = 3600):
        """存储实体到会话上下文中"""
        session_key = self._get_session_key(user_id, chat_id)
        
        if session_key not in self.session_entities:
            self.session_entities[session_key] = {
                "entities": {},
                "created_at": time.time()
            }
        
        # 存储实体及其过期时间
        self.session_entities[session_key]["entities"][entity_type] = {
            "value": entity_value,
            "expires_at": time.time() + ttl
        }

    def get_entity(self, user_id: str, chat_id: str, entity_type: str) -> Optional[str]:
        """从会话上下文中获取实体"""
        session_key = self._get_session_key(user_id, chat_id)
        
        if session_key not in self.session_entities:
            return None
        
        # 检查过期时间
        entities = self.session_entities[session_key]["entities"]
        if entity_type in entities:
            entity = entities[entity_type]
            if time.time() <= entity["expires_at"]:
                return entity["value"]
            else:
                # 实体已过期，删除它
                del entities[entity_type]
                return None
        
        return None

    def get_all_entities(self, user_id: str, chat_id: str) -> Dict[str, str]:
        """获取会话中的所有实体"""
        session_key = self._get_session_key(user_id, chat_id)
        entities = {}
        
        if session_key in self.session_entities:
            session_data = self.session_entities[session_key]["entities"]
            # 过滤过期实体并返回值
            for entity_type, entity_data in session_data.items():
                if time.time() <= entity_data["expires_at"]:
                    entities[entity_type] = entity_data["value"]
                else:
                    # 删除过期实体
                    del session_data[entity_type]
        
        return entities

    def clear_expired_entities(self):
        """清理过期的实体"""
        current_time = time.time()
        sessions_to_remove = []
        
        for session_key, session_data in self.session_entities.items():
            entities_to_remove = []
            for entity_type, entity_data in session_data["entities"].items():
                if current_time > entity_data["expires_at"]:
                    entities_to_remove.append(entity_type)
            
            # 删除过期实体
            for entity_type in entities_to_remove:
                del session_data["entities"][entity_type]
            
            # 如果会话中没有实体了，考虑删除整个会话（可以设置一个最小存活时间）
            if not session_data["entities"]:
                if current_time - session_data.get("created_at", 0) > 7200:  # 2小时
                    sessions_to_remove.append(session_key)
        
        # 删除过期的会话
        for session_key in sessions_to_remove:
            if session_key in self.session_entities:
                del self.session_entities[session_key]

    # 新增多位置管理方法
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