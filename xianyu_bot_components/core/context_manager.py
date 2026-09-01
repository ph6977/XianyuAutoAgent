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
        
        # 确保entities键存在
        if "entities" not in self.session_entities[session_key]:
            self.session_entities[session_key]["entities"] = {}
        
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
        
        try:
            if session_key in self.session_entities:
                session_data = self.session_entities[session_key]
                
                # 处理旧的实体存储格式
                if "entities" in session_data and isinstance(session_data["entities"], dict):
                    for entity_type, entity_data in session_data["entities"].items():
                        if isinstance(entity_data, dict) and "expires_at" in entity_data and "value" in entity_data:
                            if time.time() <= entity_data["expires_at"]:
                                entities[entity_type] = entity_data["value"]
                
                # 处理位置列表
                if "locations" in session_data:
                    locations = self.get_location_list(user_id, chat_id)
                    if locations:
                        entities["locations"] = ", ".join(locations)
                        entities["latest_location"] = locations[-1] if locations else None
            
            return entities
        except Exception as e:
            logger.error(f"获取实体时出错: {e}")
            return {}

    def clear_expired_entities(self):
        """清理过期的实体"""
        current_time = time.time()
        sessions_to_remove = []
        
        for session_key, session_data in self.session_entities.items():
            # 检查是否有entities键
            if "entities" not in session_data:
                continue
                
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

    def _load_db(self) -> Dict:
        """加载数据库"""
        try:
            with open(self.db_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"加载数据库失败: {e}")
            return {"chats": {}, "items": {}, "metadata": {"created_at": time.time(), "last_updated": time.time()}}

    def _save_db(self, data: Dict):
        """保存数据库"""
        try:
            data["metadata"]["last_updated"] = time.time()
            with open(self.db_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"保存数据库失败: {e}")

    def add_message_by_chat(self, chat_id: str, user_id: str, item_id: str, role: str, content: str, message_type: str = "text"):
        """添加消息到聊天记录"""
        data = self._load_db()

        if chat_id not in data["chats"]:
            data["chats"][chat_id] = {
                "chat_id": chat_id,
                "item_id": item_id,
                "user_id": user_id,
                "messages": [],
                "bargain_count": 0,
                "original_price": None,  # 标价
                "final_price": None,    # 成交价
                "discount_amount": None, # 折扣金额
                "discount_percentage": None, # 折扣百分比
                "shipping_info": None,  # 邮费信息
                "is_free_shipping": False, # 是否包邮
                "deal_status": "pending", # 交易状态: pending, completed, cancelled
                "bargain_history": [],  # 议价过程
                "first_message_content": content if role == "user" else None, # 首次消息内容
                "response_time_avg": None, # 平均响应时间
                "total_session_time": None, # 会话总时长
                "return_status": None,  # 退货状态
                "product_condition": None, # 商品成色
                "posting_time": None,  # 发布时间
                "negotiation_pattern": None, # 议价模式
                "seller_response_pattern": None, # 卖家回应模式
                "created_at": time.time(),
                "last_updated": time.time()
            }

        message = {
            "role": role,
            "content": content,
            "timestamp": time.time(),
            "message_type": message_type, # 消息类型: text, price_negotiation, order_status等
            "is_bargain_related": self._is_bargain_message(content) # 是否与议价相关
        }

        data["chats"][chat_id]["messages"].append(message)
        data["chats"][chat_id]["last_updated"] = time.time()

        # 自动提取并存储实体
        try:
            self._extract_and_store_entities(user_id, chat_id, content)
        except Exception as e:
            logger.error(f"提取并存储实体时出错: {e}")
            import traceback
            logger.error(f"错误详情: {traceback.format_exc()}")

        self._save_db(data)
    
    def _extract_and_store_entities(self, user_id: str, chat_id: str, content: str):
        """从消息中提取实体并存储到会话上下文"""
        # 清理过期实体
        self.clear_expired_entities()
        
        # 提取地点实体 - 支持多位置
        location_keywords = ["北京", "上海", "广州", "深圳", "杭州", "南京", "东莞", "佛山", "重庆", "成都", 
                           "武汉", "西安", "苏州", "长沙", "青岛", "大连", "厦门", "宁波", "无锡", "合肥"]
        found_locations = []
        for location in location_keywords:
            if location in content:
                found_locations.append(location)
        
        # 存储所有找到的位置
        if found_locations:
            self.store_multiple_locations(user_id, chat_id, found_locations)
        
        # 提取设备类型相关关键词
        device_keywords = ["胖卡", "相机", "手机", "镜头", "设备", "器材", "单反", "微单", "镜头", "无人机", 
                          "拍摄", "拍摄设备", "摄像", "摄像设备", "拍照"]
        for device in device_keywords:
            if device in content:
                self.store_entity(user_id, chat_id, "device_type", device)
                break  # 设备类型仍然只存储一个
        
        # 提取时间相关关键词（这里可以进一步扩展为具体的日期解析）
        time_keywords = ["今天", "明天", "后天", "本周", "下周", "本月", "下月", "1月", "2月", "3月", 
                        "4月", "5月", "6月", "7月", "8月", "9月", "10月", "11月", "12月"]
        for time_kw in time_keywords:
            if time_kw in content:
                self.store_entity(user_id, chat_id, "time_reference", time_kw)
                break  # 如果找到一个时间引用，就不需要再查找其他

    def _is_bargain_message(self, content: str) -> bool:
        """判断消息是否与议价相关"""
        bargain_keywords = [
            "便宜", "优惠", "还价", "砍价", "打折", "降价", "价格", "多少钱", "贵", "便宜点",
            "多少", "价位", "底价", "让利", "成交价", "原价", "折扣", "促销", "特价", 
            "1块", "一块", "少点", "给个价", "能少", "价格能", "可以便宜", "能便宜"
        ]
        return any(keyword in content for keyword in bargain_keywords)

    def get_context_by_chat(self, chat_id: str) -> List[Dict]:
        """获取聊天上下文"""
        data = self._load_db()

        if chat_id not in data["chats"]:
            return []

        return data["chats"][chat_id]["messages"]

    def get_item_info(self, item_id: str) -> Dict:
        """获取商品信息"""
        data = self._load_db()
        
        if item_id not in data["items"]:
            # 如果商品不存在，创建基本信息
            data["items"][item_id] = {
                "item_id": item_id,
                "title": "",
                "price": None,
                "description": "",
                "images": [],
                "category": "",
                "status": "active",
                "created_at": time.time(),
                "last_updated": time.time()
            }
            self._save_db(data)
        
        return data["items"][item_id]