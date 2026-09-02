#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
智能租赁顾问Agent
为用户提供手机、相机等设备租赁咨询服务
"""

import os
import re
import json
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional, Any
from loguru import logger

# 安全过滤器
def default_safety_filter(text: str) -> str:
    """默认安全过滤器"""
    return text

class RentalConsultantAgent:
    """智能租赁顾问Agent"""
    
    def __init__(self, client, system_prompt: str, safety_filter=None, feishu_reader=None, context_manager=None):
        """初始化租赁顾问Agent"""
        self.client = client
        self.system_prompt = system_prompt
        self.safety_filter = safety_filter or default_safety_filter
        self.feishu_reader = feishu_reader
        self.context_manager = context_manager  # 添加上下文管理器
        self.product_mapping = self._load_product_mapping()
        self.use_xianyu_api_knowledge = os.getenv("USE_XIANYU_API_KNOWLEDGE", "true").strip().lower() == "true"

        # 如果没有提供飞书读取器，尝试从环境变量创建
        if self.feishu_reader is None:
            try:
                from src.knowledge.feishu_sheet_reader import FeishuSheetReader
                app_id = os.getenv("FEISHU_APP_ID")
                app_secret = os.getenv("FEISHU_APP_SECRET")
                spreadsheet_token = os.getenv("FEISHU_SPREADSHEET_TOKEN")
                sheet_id = os.getenv("FEISHU_SHEET_ID")
                
                if all([app_id, app_secret, spreadsheet_token, sheet_id]):
                    self.feishu_reader = FeishuSheetReader(app_id, app_secret, spreadsheet_token, sheet_id)
                    logger.info("成功初始化飞书读取器")
                else:
                    logger.warning("飞书配置不完整，部分功能可能受限")
            except Exception as e:
                logger.warning(f"飞书读取器初始化失败: {e}")

    def _load_product_mapping(self) -> Dict[str, List[str]]:
        """加载商品ID到设备名称的映射"""
        mapping_path = os.getenv("PRODUCT_MAPPING_FILE", "product_mapping.json")
        try:
            with open(mapping_path, "r", encoding="utf-8") as f:
                mapping_data = json.load(f)
            logger.info(f"成功加载商品映射文件: {mapping_path}")
            return mapping_data
        except FileNotFoundError:
            logger.warning(f"未找到商品映射文件: {mapping_path}")
        except json.JSONDecodeError as e:
            logger.error(f"商品映射文件解析失败: {e}")
        except Exception as e:
            logger.error(f"商品映射文件加载异常: {e}")
        return {}

    def _resolve_target_devices(
        self,
        target_devices: List[str],
        item_description: str = "",
        user_message: str = "",
        allow_product_mapping: bool = True
    ) -> List[str]:
        """根据商品ID映射实际设备名称"""
        resolved_devices: List[str] = []
        seen: set[str] = set()
        candidates: List[str] = []

        if target_devices:
            if isinstance(target_devices, (list, tuple, set)):
                for entry in target_devices:
                    if entry is None:
                        continue
                    if isinstance(entry, (list, tuple, set)):
                        candidates.extend(str(item) for item in entry if item)
                    else:
                        candidates.append(str(entry))
            else:
                candidates.append(str(target_devices))

        def append_product_ids_from(text: str):
            if not text:
                return
            matches = re.findall(r'商品ID[:：]?\s*(\d{6,})', text)
            for pid in matches:
                candidates.append(pid)

        if allow_product_mapping:
            append_product_ids_from(item_description or "")
            append_product_ids_from(user_message or "")

        for raw in candidates:
            if not raw:
                continue
            raw_text = raw.strip()
            if not raw_text:
                continue

            product_id = None
            if "商品ID" in raw_text:
                match = re.search(r'(\d{6,})', raw_text)
                if match:
                    product_id = match.group(1)
            elif raw_text.isdigit():
                product_id = raw_text

            if product_id:
                if not allow_product_mapping:
                    logger.debug(f"跳过商品ID {product_id} 的映射（已禁用闲鱼商品知识库）")
                    continue
                mapped_devices = self.product_mapping.get(product_id)
                if mapped_devices:
                    for device_name in mapped_devices:
                        normalized = str(device_name).strip()
                        if normalized and normalized not in seen:
                            resolved_devices.append(normalized)
                            seen.add(normalized)
                else:
                    logger.warning(f"商品ID {product_id} 未在映射表中配置，跳过此商品ID的映射")
                    # 不再保留原始ID，这样可以避免查询不存在的ID
                    # 如果商品ID无法映射，就不将其加入目标设备列表
                    continue
                continue

            if raw_text not in seen:
                resolved_devices.append(raw_text)
                seen.add(raw_text)

        return resolved_devices

    def generate(self, user_message: str, item_description: str = "", context: str = "", user_id: str = None, chat_id: str = None) -> str:
        """
        生成回复
        
        Args:
            user_message: 用户消息
            item_description: 商品描述
            context: 上下文信息
            user_id: 用户ID
            chat_id: 聊天ID
            
        Returns:
            回复内容
        """
        try:
            # 1. 分析用户意图
            intent_analysis = self._analyze_user_intent(user_message, item_description, context, user_id, chat_id)
            logger.info(f"意图分析结果: {intent_analysis}")
            
            # 2. 根据意图类型处理
            intent_type = intent_analysis.get('intent_type', 'general_inquiry')
            
            if intent_type == 'availability_check':
                if intent_analysis.get('query_strategy') == 'comprehensive':
                    return self._handle_comprehensive_availability(intent_analysis, item_description, context, user_message)
                elif intent_analysis.get('query_strategy') == 'time_first':
                    return self._handle_time_first_availability(intent_analysis, item_description, context, user_message)
                elif intent_analysis.get('query_strategy') == 'location_first':
                    return self._handle_location_first_availability(intent_analysis, item_description, context)
            elif intent_type == 'location_inquiry':
                return self._handle_location_inquiry(intent_analysis, item_description, context)
            elif intent_type == 'date_inquiry':
                return self._handle_date_inquiry(intent_analysis, item_description, context)
            else:
                return self._handle_general_inquiry(intent_analysis, user_message, item_description, context)
                
        except Exception as e:
            logger.error(f"生成回复时出错: {e}")
            return "抱歉，我遇到了一些问题，请稍后再试哦～"
    
    def _analyze_user_intent(self, user_message: str, item_description: str, context: str, user_id: str = None, chat_id: str = None) -> Dict:
        """
        分析用户意图
        
        Args:
            user_message: 用户消息
            item_description: 商品描述
            context: 上下文信息
            user_id: 用户ID
            chat_id: 聊天ID
            
        Returns:
            意图分析结果
        """
        today_str = datetime.now().strftime('%Y-%m-%d')
        
        # 从上下文管理器获取实体信息
        context_entities = {}
        if self.context_manager and user_id:
            context_entities = self.context_manager.get_all_entities(user_id, chat_id or user_id)
            logger.debug(f"从上下文管理器获取实体: {context_entities}")
        
        # 构建上下文信息字符串
        context_info = ""
        if context_entities:
            context_items = []
            for entity_type, entity_value in context_entities.items():
                # 跳过内部使用的键
                if entity_type in ["entities", "locations"]:
                    continue
                # 确保值是字符串类型
                if entity_value is None:
                    continue
                entity_value_str = str(entity_value)
                
                if entity_type == "location":
                    context_items.append(f"用户位置: {entity_value_str}")
                elif entity_type == "device_type":
                    context_items.append(f"设备类型: {entity_value_str}")
                elif entity_type == "time_reference":
                    context_items.append(f"时间参考: {entity_value_str}")
                elif entity_type == "latest_location":
                    context_items.append(f"最新位置: {entity_value_str}")
                else:
                    context_items.append(f"{entity_type}: {entity_value_str}")
            
            if context_items:
                context_info = "会话上下文: " + ", ".join(context_items) + "\n"
        
        prompt = f"""
{context_info}
你是一个专业的租赁顾问AI助手，请分析用户消息的意图并提取关键信息。

用户消息: {user_message}
商品信息: {item_description}
上下文: {context}
当前参考日期: {today_str}

请以JSON格式返回分析结果，格式如下：
{{
    "intent_type": "意图类型(general_inquiry/availability_check/location_inquiry/date_inquiry)",
    "query_strategy": "查询策略(comprehensive/time_first/location_first)",
    "context_analysis": "上下文分析",
    "extracted_info": {{
        "target_devices": ["目标设备列表"],
        "rental_dates": "租赁日期或日期范围",
        "target_city": "目标城市",
        "other_info": "其他信息"
    }},
    "specific_instruction": "具体指令"

要求：
1. 准确识别意图类型
2. 提取关键信息
3. 策略选择：
   - comprehensive: 综合查询（同时包含设备/日期/位置）
   - time_first: 时间优先查询（先问时间再问设备）
   - location_first: 位置优先查询（先问位置再问设备）
4. 从上下文信息中补充缺失的信息：
   - 如果用户消息中没有明确提及城市，但上下文中有位置信息，则使用上下文中的位置
   - 重要：只有当用户明确询问某个设备时，才使用上下文中的设备型号信息。如果用户只是询问某个城市或日期的设备情况，不要限制为特定设备型号
5. 设备型号识别规则：
   - 只有当用户消息中明确提及具体设备型号时，才将其列入target_devices
   - 如果用户只是泛泛询问"有什么设备"、"有哪些机器"等，target_devices应为空列表[]
   - 设备型号必须是精确的型号名称，例如：['胖卡4-002', '胖卡4-010']，而不是泛化的描述如['相机', '胖卡系列设备']等
6. 所有与时间相关的表述必须转换为绝对日期或日期范围，并使用YYYY-MM-DD格式。例如："本月25号"需转换成"2025-11-25"；"本月25号到28号"需转换成["2025-11-25","2025-11-28"]；"月底""下个月""下周"等相对时间必须结合当前参考日期计算出具体日期
7. 严格按照JSON格式返回
"""
        
        try:
            response = self.client.chat.completions.create(
                model=os.getenv("MODEL_NAME", "deepseek-chat"),
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                max_tokens=1000
            )
            
            # 解析响应
            content = response.choices[0].message.content.strip()
            
            # 处理可能的 markdown 格式
            if content.startswith('```json'):
                json_start = content.find('{')
                json_end = content.rfind('}') + 1
                if json_start >= 0 and json_end > json_start:
                    content = content[json_start:json_end]
            
            result = json.loads(content)
            
            # 如果用户消息中没有明确提及城市，但上下文中有位置信息，则补充
            extracted_info = result.get('extracted_info', {})
            if not extracted_info.get('target_city'):
                # 优先使用latest_location，确保获取最新提及的位置
                latest_location = context_entities.get('latest_location')
                if latest_location:
                    logger.info(f"从上下文补充最新位置信息: {latest_location}")
                    extracted_info['target_city'] = latest_location
                    result['extracted_info'] = extracted_info
                elif context_entities.get('location'):
                    logger.info(f"从上下文补充位置信息: {context_entities['location']}")
                    extracted_info['target_city'] = context_entities['location']
                    result['extracted_info'] = extracted_info
            
            # 如果用户消息中没有明确提及设备类型，但上下文中有设备类型信息，则补充
            if not extracted_info.get('target_devices') and context_entities.get('device_type'):
                device_type = context_entities['device_type']
                logger.info(f"从上下文补充设备类型信息: {device_type}")
                
                # 避免添加泛化的设备类型描述，只添加具体的设备型号
                # 检查设备类型是否为具体的型号格式（如包含数字、连字符等标识具体型号的字符）
                import re
                if re.search(r'[\d-]', device_type) or device_type in ['胖卡4-001', '胖卡4-002', '胖卡4-003', '胖卡4-004', '胖卡4-005', '胖卡4-006', '胖卡4-007', '胖卡4-008', '胖卡4-009', '胖卡4-010']:
                    # 这是一个具体的设备型号，可以添加
                    if not extracted_info.get('target_devices'):
                        extracted_info['target_devices'] = []
                    extracted_info['target_devices'].append(device_type)
                    result['extracted_info'] = extracted_info
                else:
                    logger.info(f"设备类型 '{device_type}' 为泛化描述，跳过添加到目标设备列表")
            
            return result
            
        except Exception as e:
            logger.error(f"意图分析失败: {e}")
            # 返回默认意图
            return {
                "intent_type": "general_inquiry",
                "query_strategy": "comprehensive",
                "context_analysis": "默认处理",
                "extracted_info": {},
                "specific_instruction": "提供一般性租赁咨询服务"
            }

    def _handle_comprehensive_availability(self, intent_analysis: Dict, item_description: str, context: str, user_message: str = "") -> str:
        """处理综合可用性查询 - 优化版：先确定城市，再查询时间"""
        try:
            extracted_info = intent_analysis.get('extracted_info', {})
            
            # 1. 首先确定城市
            customer_location = extracted_info.get('target_city', '')
            if not customer_location:
                # 如果没有城市信息，询问用户
                return "请问您想查询哪个城市的设备呢？😊"
            
            logger.info(f"查询城市: {customer_location}")
            
            # 2. 处理日期信息
            raw_rental_dates = extracted_info.get('rental_dates', '')
            rental_dates = None
            
            # 如果有日期信息，解析日期
            if raw_rental_dates:
                if isinstance(raw_rental_dates, (list, tuple)):
                    if len(raw_rental_dates) == 2:
                        rental_dates = (str(raw_rental_dates[0]).strip(), str(raw_rental_dates[1]).strip())
                    elif len(raw_rental_dates) == 1:
                        rental_dates = str(raw_rental_dates[0]).strip()
                    else:
                        rental_dates = self._parse_rental_dates(' '.join(map(str, raw_rental_dates)))
                else:
                    rental_dates = self._parse_rental_dates(raw_rental_dates or '')
            
            # 3. 如果没有具体日期，询问用户
            if not rental_dates:
                return f"好的，我了解您想查询{customer_location}的设备。请问您想查询哪个日期的可用情况呢？比如今天、明天或者具体的日期～"
            
            logger.info(f"查询日期: {rental_dates}")
            
            # 检查是否是月份查询（如"10月"被解析为"2025-10-01"）
            if isinstance(rental_dates, str) and rental_dates.endswith('-01'):
                logger.info(f"检测到月份查询: {rental_dates}，将查询整个月份的可用性")
                # 尝试获取该月份的所有可用日期
                try:
                    year, month = rental_dates.split('-')[:2]
                    month_start = f"{year}-{month}-01"
                    # 获取该月最后一天
                    import calendar
                    last_day = calendar.monthrange(int(year), int(month))[1]
                    month_end = f"{year}-{month}-{last_day:02d}"
                    logger.info(f"查询月份范围: {month_start} 到 {month_end}")
                    
                    # 查询整个月份的可用性
                    available_devices_by_date = {}
                    days_with_devices = 0
                    for day in range(1, last_day + 1):
                        date_str = f"{year}-{month}-{day:02d}"
                        devices = self.feishu_reader.find_available_devices_by_date(
                            date_str, None, customer_location
                        )
                        if devices:
                            available_devices_by_date[date_str] = devices
                            days_with_devices += 1
                    
                    logger.info(f"月份查询完成: {days_with_devices} 天有设备可用")
                    
                    if available_devices_by_date:
                        # 生成月份汇总回复
                        reply = f"{customer_location}在{year}年{month}月有以下日期有设备可租哦😊\n\n"
                        for date, devices in sorted(available_devices_by_date.items()):
                            device_names = [d['name'] for d in devices]
                            reply += f"📅 {date}: {', '.join(device_names)}\n"
                        reply += f"\n总共{len(available_devices_by_date)}天有设备可租，需要了解某个日期的详细信息吗？💫"
                        return self.safety_filter(reply)
                    else:
                        # 如果整个月都没有设备，再查询具体某一天
                        pass
                except Exception as e:
                    logger.error(f"查询月份可用性失败: {e}")
                    # 出错时继续使用原有逻辑
            
            # 4. 解析目标设备
            raw_target_devices = extracted_info.get('target_devices', [])
            final_target_devices = None  # 默认查询所有设备
            
            # 只有当用户明确提及具体设备型号时，才设置过滤
            # 如果只是从上下文继承的设备信息，不应该限制查询
            user_message_lower = user_message.lower()
            if raw_target_devices:
                refined_target_devices = []
                for device in raw_target_devices:
                    device_str = str(device)
                    # 检查用户消息中是否明确提到了这个设备
                    if device_str.lower() in user_message_lower:
                        # 跳过泛化描述
                        if not any(keyword in device_str for keyword in ['系列', '所有', '全部', '通用']):
                            refined_target_devices.append(device_str)
                
                if refined_target_devices:
                    final_target_devices = self._resolve_target_devices(
                        refined_target_devices,
                        item_description=item_description if self.use_xianyu_api_knowledge else "",
                        user_message=user_message,
                        allow_product_mapping=self.use_xianyu_api_knowledge
                    )
            
            # 5. 查询设备可用性
            if self.feishu_reader is None:
                return "抱歉，暂时无法查询设备状态，请稍后再试哦～"
            
            available_devices = []
            
            # 根据日期类型查询
            if isinstance(rental_dates, tuple) and len(rental_dates) == 2:
                # 日期范围查询
                start_date, end_date = rental_dates
                available_devices = self.feishu_reader.find_available_devices_by_date_range(
                    start_date, end_date, final_target_devices, customer_location
                )
            else:
                # 单日期查询
                query_date = rental_dates if isinstance(rental_dates, str) else str(rental_dates)
                available_devices = self.feishu_reader.find_available_devices_by_date(
                    query_date, final_target_devices, customer_location
                )
            
            # 6. 生成回复
            if available_devices:
                device_names = [device['name'] for device in available_devices]
                locations = list(set(device['location'] for device in available_devices))
                
                reply = f"{customer_location}在{rental_dates}有这些设备可以出租哦😊\n"
                reply += f"设备：{', '.join(device_names)}\n"
                reply += f"设备位置：{', '.join(locations)}\n"
                reply += "需要我帮您了解更多详情吗？💫"
            else:
                reply = f"抱歉，{customer_location}在{rental_dates}暂时没有可出租的设备呢，您可以试试其他日期哦～"
            
            return self.safety_filter(reply)
            
        except Exception as e:
            logger.error(f"处理综合可用性查询失败: {e}")
            return "抱歉，查询设备状态时遇到了一些问题，请稍后再试哦～"

    def _handle_time_first_availability(self, intent_analysis: Dict, item_description: str, context: str, user_message: str = "") -> str:
        """处理时间优先的可用性查询"""
        try:
            extracted_info = intent_analysis.get('extracted_info', {})

            raw_rental_dates = extracted_info.get('rental_dates', '')
            if isinstance(raw_rental_dates, (list, tuple)):
                if len(raw_rental_dates) == 2:
                    rental_dates = (str(raw_rental_dates[0]).strip(), str(raw_rental_dates[1]).strip())
                elif len(raw_rental_dates) == 1:
                    rental_dates = str(raw_rental_dates[0]).strip()
                else:
                    rental_dates = self._parse_rental_dates(' '.join(map(str, raw_rental_dates)))
            else:
                rental_dates = self._parse_rental_dates(raw_rental_dates or '')

            logger.info(f"时间优先策略解析日期: {rental_dates}")

            target_devices = self._resolve_target_devices(
                extracted_info.get('target_devices', []),
                item_description=item_description if self.use_xianyu_api_knowledge else "",
                user_message=user_message,
                allow_product_mapping=self.use_xianyu_api_knowledge
            )

            customer_location = extracted_info.get('target_city', '')
            
            logger.info(f"时间优先查询 - 使用位置: {customer_location}")

            if self.feishu_reader is None:
                return "抱歉，暂时无法查询设备状态，请稍后再试哦～"

            availability_result = self._query_availability_by_time_strategy(
                rental_dates=rental_dates,
                target_devices=target_devices,
                customer_location=customer_location
            )

            reply = self._format_time_strategy_reply(
                availability_result,
                customer_location
            )

            return self.safety_filter(reply)

        except Exception as exc:
            logger.error(f"处理时间优先查询失败: {exc}")
            return "抱歉，查询设备状态时出了点小问题，我们稍后再试试好吗？"

    def _query_availability_by_time_strategy(
        self,
        rental_dates: Any,
        target_devices: List[str],
        customer_location: str
    ) -> Dict[str, Any]:
        """按照时间窗口查询可用设备"""
        start_date: Optional[str] = None
        end_date: Optional[str] = None
        single_date: Optional[str] = None

        if isinstance(rental_dates, (list, tuple)) and len(rental_dates) == 2:
            start_date, end_date = rental_dates
        elif isinstance(rental_dates, str):
            range_pair = self._split_date_range_string(rental_dates)
            if range_pair:
                start_date, end_date = range_pair
            else:
                single_date = rental_dates.strip()
        elif rental_dates:
            single_date = str(rental_dates)

        if not single_date and not start_date:
            single_date = datetime.now().strftime('%Y-%m-%d')

        filter_devices = target_devices if target_devices else None
        available_devices: List[Dict[str, Any]] = []

        if self.feishu_reader is None:
            logger.warning("飞书读取器未初始化，无法查询设备可用性")
            return {
                "devices": [],
                "start_date": start_date,
                "end_date": end_date,
                "single_date": single_date
            }

        logger.info(f"查询设备可用性 - 位置参数: {customer_location}")
        
        if start_date and end_date:
            available_devices = self.feishu_reader.find_available_devices_by_date_range(
                start_date,
                end_date,
                filter_devices,
                customer_location or None
            )
        else:
            query_date = single_date or start_date or end_date or datetime.now().strftime('%Y-%m-%d')
            available_devices = self.feishu_reader.find_available_devices_by_date(
                query_date,
                filter_devices,
                customer_location or None
            )
            single_date = query_date

        logger.info(
            f"时间优先查询结果: start={start_date}, end={end_date}, "
            f"single={single_date}, devices={len(available_devices)}"
        )

        return {
            "devices": available_devices,
            "start_date": start_date,
            "end_date": end_date,
            "single_date": single_date
        }

    def _format_time_strategy_reply(self, availability_result: Dict[str, Any], customer_location: str) -> str:
        """根据时间策略查询结果生成自然语言回复"""
        devices = availability_result.get("devices") or []
        date_label = self._describe_date_window(
            availability_result.get("start_date"),
            availability_result.get("end_date"),
            availability_result.get("single_date")
        )

        if devices:
            total_count = len(devices)
            preview_names = [device['name'] for device in devices[:5]]
            device_names = "、".join(preview_names)
            if total_count > 5:
                device_names += f" 等{total_count}台"

            location_candidates = {device.get('location') or "仓库" for device in devices}
            location_text = "、".join(sorted(location_candidates))

            reply = f"{date_label} 这段时间有这些设备可以出租哦😊\n"
            reply += f"可用设备：{device_names}\n"
            reply += f"所在城市：{location_text}\n"
            reply += "需要我帮您预留或者推荐更合适的配置吗？"
            return reply

        location_hint = f"（{customer_location}）" if customer_location else ""
        return (
            f"抱歉，{date_label}{location_hint}暂时没有空闲的设备。"
            "要不要换个日期，或者告诉我具体的设备/城市，我再帮您继续查？"
        )

    def _describe_date_window(self, start_date: Optional[str], end_date: Optional[str], single_date: Optional[str]) -> str:
        """将日期窗口转换成更友好的文本"""
        if start_date and end_date:
            if start_date == end_date:
                return self._format_date_label(start_date)
            return f"{self._format_date_label(start_date)} - {self._format_date_label(end_date)}"

        if single_date:
            return self._format_date_label(single_date)

        return "这段时间"

    def _split_date_range_string(self, date_str: str) -> Optional[Tuple[str, str]]:
        """从字符串中提取日期范围"""
        if not date_str:
            return None

        normalized = date_str.strip()
        separators = ['至', '到', '~', '－', '—', '–']
        for sep in separators:
            if sep in normalized:
                parts = [p.strip() for p in normalized.split(sep) if p.strip()]
                if len(parts) == 2:
                    return parts[0], parts[1]

        match = re.match(r'^\s*(\d{4}-\d{1,2}-\d{1,2})\D+(\d{4}-\d{1,2}-\d{1,2})\s*$', normalized)
        if match:
            return match.group(1), match.group(2)

        return None

    def _handle_location_first_availability(self, intent_analysis: Dict, item_description: str, context: str) -> str:
        """处理位置优先的可用性查询"""
        try:
            extracted_info = intent_analysis.get('extracted_info', {})
            
            # 解析客户位置
            customer_location = extracted_info.get('target_city', '')
            
            # 如果没有飞书读取器，返回提示
            if self.feishu_reader is None:
                return "抱歉，暂时无法查询设备状态，请稍后再试哦～"
            
            # 查询该位置的设备
            available_devices = self.feishu_reader.find_devices_by_location(customer_location)
            
            # 生成回复
            if available_devices:
                device_names = [d['name'] for d in available_devices]
                reply = f"在{customer_location}有这些设备可以出租哦😊\n"
                reply += f"设备：{', '.join(device_names)}\n"
                reply += "您想了解哪个设备的详细信息呢？💫"
            else:
                reply = f"抱歉，{customer_location}暂时没有可出租的设备呢，您可以试试其他城市哦～"
            
            return self.safety_filter(reply)
            
        except Exception as e:
            logger.error(f"处理位置优先查询失败: {e}")
            return "抱歉，查询设备状态时遇到了一些问题，请稍后再试哦～"
    
    def _handle_location_inquiry(self, intent_analysis: Dict, item_description: str, context: str) -> str:
        """处理位置询问"""
        try:
            extracted_info = intent_analysis.get('extracted_info', {})
            customer_location = extracted_info.get('target_city', '')
            
            if customer_location:
                # 如果已经提供了位置信息，先询问用户想要查询的日期
                # 不要直接查询今天的设备，因为用户可能想了解其他日期的可用性
                reply = f"好的，我来帮您查询{customer_location}的设备情况😊\n"
                reply += "请问您想了解哪个日期的设备可用性呢？比如今天、明天，或者具体的日期（如10月25日）？"
                return self.safety_filter(reply)
            else:
                # 询问用户位置
                return "请问您在哪个城市呢？这样我可以为您推荐附近的设备哦～😊"
                
        except Exception as e:
            logger.error(f"处理位置询问失败: {e}")
            return "请问您在哪个城市呢？这样我可以为您推荐附近的设备哦～😊"
    
    def _handle_date_inquiry(self, intent_analysis: Dict, item_description: str, context: str) -> str:
        """处理日期询问"""
        try:
            extracted_info = intent_analysis.get('extracted_info', {})
            rental_dates = extracted_info.get('rental_dates', None)
            target_devices = self._resolve_target_devices(
                extracted_info.get('target_devices', []),
                item_description=item_description if self.use_xianyu_api_knowledge else "",
                user_message="",  # 这里不需要用户消息，因为我们已经在意图分析中提取了信息
                allow_product_mapping=self.use_xianyu_api_knowledge
            )
            target_city = extracted_info.get('target_city', '')

            # 如果意图分析中已经提取了日期信息，则调用时间优先策略
            if rental_dates:
                # 调用时间优先策略处理已提取的日期
                availability_result = self._query_availability_by_time_strategy(
                    rental_dates=rental_dates,
                    target_devices=target_devices,
                    customer_location=target_city
                )
                
                reply = self._format_time_strategy_reply(
                    availability_result,
                    target_city
                )
                
                return self.safety_filter(reply)
            
            # 如果没有提取到日期，则询问用户日期
            return "请问您想租设备的具体日期是哪天呢？或者您想租几天？😊"
            
        except Exception as e:
            logger.error(f"处理日期询问失败: {e}")
            return "请问您想租设备的具体日期是哪天呢？或者您想租几天？😊"

    def _calculate_rental_price(self, device_model: str, rental_days: int) -> Dict:
        """
        根据设备型号和租赁天数计算价格
        
        Args:
            device_model: 设备型号
            rental_days: 租赁天数
            
        Returns:
            包含价格信息的字典
        """
        # 价格表（每日单价）
        price_table = {
            "胖卡4-002": {
                1: 250, 2: 150, 3: 120, 5: 100, 7: 90, 10: 70, 15: 60, 30: 45
            },
            "胖卡4-006": {
                1: 250, 2: 150, 3: 120, 5: 100, 7: 90, 10: 70, 15: None, 30: 45
            },
            # 可以添加更多设备型号
        }
        
        # 获取设备价格表
        device_prices = price_table.get(device_model, {})
        
        # 根据租赁天数查找对应单价
        daily_price = None
        applicable_days = None
        
        # 找到最接近的租期档位
        for days in sorted(device_prices.keys(), reverse=True):
            if rental_days >= days and device_prices[days] is not None:
                daily_price = device_prices[days]
                applicable_days = days
                break
        
        # 如果没有找到合适的档位，使用默认价格
        if daily_price is None:
            daily_price = 150  # 默认单价
            applicable_days = rental_days
        
        # 计算总价
        total_price = daily_price * rental_days
        
        return {
            "device_model": device_model,
            "rental_days": rental_days,
            "daily_price": daily_price,
            "applicable_pricing_tier": f"{applicable_days}天档位",
            "total_price": total_price
        }
    
    def _handle_general_inquiry(self, intent_analysis: Dict, user_message: str, item_description: str, context: str) -> str:
        """处理一般性咨询"""
        try:
            extracted_info = intent_analysis.get('extracted_info', {})
            target_devices = extracted_info.get('target_devices', [])
            rental_dates = extracted_info.get('rental_dates', [])
            target_city = extracted_info.get('target_city', '')
            
            # 检查是否是价格查询
            price_keywords = ['多少钱', '价格', '费用', '收费', '要多少', '成本', '租金']
            if any(keyword in user_message for keyword in price_keywords):
                # 处理价格查询
                if target_devices and rental_dates:
                    device_model = target_devices[0] if target_devices else None
                    
                    # 计算租赁天数
                    rental_days = 1  # 默认1天
                    if isinstance(rental_dates, list) and len(rental_dates) >= 2:
                        try:
                            start_date = datetime.strptime(rental_dates[0], '%Y-%m-%d')
                            end_date = datetime.strptime(rental_dates[1], '%Y-%m-%d')
                            # 取机当天不算租金，只算使用天数
                            rental_days = (end_date - start_date).days
                            # 至少算1天
                            if rental_days < 1:
                                rental_days = 1
                        except:
                            rental_days = 3  # 默认3天
                    elif isinstance(rental_dates, str) and rental_dates:
                        rental_days = 3  # 默认3天
                    
                    # 计算价格
                    if device_model:
                        price_info = self._calculate_rental_price(device_model, rental_days)
                        
                        # 生成回复
                        reply = f"好的呢～我来帮你查一下{device_model}在{target_city}租{rental_days}天的价格哦！✨\n\n"
                        reply += f"查询到啦！📱\n"
                        reply += f"**{device_model}** 在{target_city}租用 **{rental_days}天**的价格是：\n"
                        reply += f"**💰 总计 {price_info['total_price']}元**（{price_info['daily_price']}元/天，{price_info['applicable_pricing_tier']}）\n\n"
                        reply += "这个价格已经包含基础保险和服务费啦～😊\n"
                        reply += "需要我帮你直接下单预留，还是想再看看其他设备呀？💫"
                        
                        return self.safety_filter(reply)
            
            # 检查是否是询问计算方式
            calculation_keywords = ['怎么算的', '怎么计算', '如何计算', '怎么来的', '计算方式', '价格构成']
            if any(keyword in user_message for keyword in calculation_keywords):
                if target_devices and rental_dates:
                    device_model = target_devices[0] if target_devices else None
                    
                    # 计算租赁天数
                    rental_days = 3  # 默认3天
                    if isinstance(rental_dates, list) and len(rental_dates) >= 2:
                        try:
                            start_date = datetime.strptime(rental_dates[0], '%Y-%m-%d')
                            end_date = datetime.strptime(rental_dates[1], '%Y-%m-%d')
                            # 取机当天不算租金，只算使用天数
                            rental_days = (end_date - start_date).days
                            # 至少算1天
                            if rental_days < 1:
                                rental_days = 1
                        except:
                            rental_days = 3  # 默认3天
                    elif isinstance(rental_dates, str) and rental_dates:
                        rental_days = 3  # 默认3天
                    if isinstance(rental_dates, list) and len(rental_dates) >= 2:
                        try:
                            start_date = datetime.strptime(rental_dates[0], '%Y-%m-%d')
                            end_date = datetime.strptime(rental_dates[1], '%Y-%m-%d')
                            # 取机当天不算租金，只算使用天数
                            rental_days = (end_date - start_date).days
                            # 至少算1天
                            if rental_days < 1:
                                rental_days = 1
                        except:
                            rental_days = 3
                    
                    # 计算价格
                    if device_model:
                        logger.info(f"计算价格说明: 设备={device_model}, 天数={rental_days}, 日期范围={rental_dates}")
                        price_info = self._calculate_rental_price(device_model, rental_days)
                        logger.info(f"价格计算结果: {price_info}")
                        
                        # 生成详细的价格计算说明
                        reply = f"哎呀～你问得超仔细呢！✨\n"
                        reply += f"让我来给你拆解一下这个价格是怎么算出来的哦～💖\n\n"
                        reply += f"**📅 租期计算**\n"
                        if isinstance(rental_dates, list) and len(rental_dates) >= 2:
                            reply += f"{rental_dates[0]} 取机 → {rental_dates[1]} 还机\n"
                        reply += f"一共是 **{rental_days}天** 租期哦！（租期按自然日计算哒～）\n\n"
                        reply += f"**💰 价格构成**\n"
                        reply += f"{device_model}在{target_city}的 **{price_info['applicable_pricing_tier']}** 是 **{price_info['daily_price']}元/天**\n"
                        reply += f"所以：\n"
                        reply += f"{price_info['daily_price']}元/天 × {rental_days}天 = **{price_info['total_price']}元**（总价）\n\n"
                        reply += f"**📝 价目表参考**\n"
                        reply += f"胖卡4-002各档位单价：\n"
                        reply += f"• 1天：250元/天\n"
                        reply += f"• 2天：150元/天\n"
                        reply += f"• 3天：120元/天 ← 您选择的档位\n"
                        reply += f"• 5天：100元/天\n"
                        reply += f"• 7天：90元/天\n"
                        reply += f"• 10天：70元/天\n"
                        reply += f"• 15天：60元/天\n"
                        reply += f"• 30天：45元/天\n\n"
                        reply += f"**🧾 最终合计**\n"
                        reply += f"**{price_info['total_price']}元**（已包含基础保险和服务费）💫\n\n"
                        reply += f"这样是不是清楚多啦～\n"
                        reply += f"所有费用都在下单前透明展示，不会有隐藏扣款哦！😊\n"
                        reply += f"需要我再解释哪部分，或者帮你直接下单锁定吗？📦💖"
                        
                        return self.safety_filter(reply)
            
            # 非价格查询的一般性咨询
            prompt = f"""
你是一个专业的18岁少女风格的租赁顾问，请用可爱友好的语气回复用户的一般性咨询。

用户消息: {user_message}
商品信息: {item_description}
上下文: {context}
意图分析: {intent_analysis.get('context_analysis', '一般咨询')}

请用可爱的语气回复用户，保持专业但友好的风格。
"""
            
            response = self.client.chat.completions.create(
                model=os.getenv("MODEL_NAME", "deepseek-chat"),
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=500
            )
            
            reply = response.choices[0].message.content.strip()
            return self.safety_filter(reply)
            
        except Exception as e:
            logger.error(f"处理一般性咨询失败: {e}")
            return "您好呀～我是您的租赁小助手，有什么我可以帮您的吗？😊"
    
    def _format_date_label(self, date_str: str) -> str:
        try:
            dt = datetime.strptime(date_str, '%Y-%m-%d')
            return f"{dt.month}月{dt.day}日"
        except Exception:
            return date_str

    def _parse_rental_dates(self, date_str: str) -> Any:
        """
        解析租赁日期，支持多种日期格式
        
        Args:
            date_str: 日期字符串
            
        Returns:
            解析后的日期（字符串或元组）
        """
        if not date_str:
            return datetime.now().strftime('%Y-%m-%d')
        
        # 移除多余的空格
        date_str = date_str.strip()
        
        # 处理两个日期用空格分隔的情况 (如 "2025-10-01 2025-10-31")
        if ' ' in date_str and re.match(r'\d{4}-\d{1,2}-\d{1,2} \d{4}-\d{1,2}-\d{1,2}', date_str):
            parts = date_str.split()
            if len(parts) == 2:
                return (parts[0].strip(), parts[1].strip())
        
        # 当前日期
        today = datetime.now()
        
        # 处理相对日期格式
        if '后天' in date_str:
            target_date = today + timedelta(days=2)
            return target_date.strftime('%Y-%m-%d')
        elif '明天' in date_str:
            target_date = today + timedelta(days=1)
            return target_date.strftime('%Y-%m-%d')
        elif '今天' in date_str:
            return today.strftime('%Y-%m-%d')
        elif '大后天' in date_str:
            target_date = today + timedelta(days=3)
            return target_date.strftime('%Y-%m-%d')
        
        # 处理"下个月X号"格式
        match = re.search(r'下个月(\d+)号', date_str)
        if match:
            day = int(match.group(1))
            next_month = today.replace(day=1) + timedelta(days=32)
            next_month = next_month.replace(day=1)
            try:
                target_date = next_month.replace(day=day)
                return target_date.strftime('%Y-%m-%d')
            except ValueError:
                # 处理月末日期
                target_date = next_month.replace(day=1) + timedelta(days=31)
                return target_date.strftime('%Y-%m-%d')
        
        # 处理"X个月后"格式
        match = re.search(r'(\d+)个月后', date_str)
        if match:
            months = int(match.group(1))
            target_date = today + timedelta(days=30 * months)
            return target_date.strftime('%Y-%m-%d')
        
        # 处理"X天后"格式
        match = re.search(r'(\d+)天后', date_str)
        if match:
            days = int(match.group(1))
            target_date = today + timedelta(days=days)
            return target_date.strftime('%Y-%m-%d')
        
        # 处理"下周X"格式
        weekdays = {
            '一': 0, '二': 1, '三': 2, '四': 3, '五': 4, '六': 5, '日': 6,
            '1': 0, '2': 1, '3': 2, '4': 3, '5': 4, '6': 5, '天': 6
        }
        for weekday_cn, weekday_num in weekdays.items():
            if f'下周{weekday_cn}' in date_str:
                # 计算下周指定星期的日期
                today_weekday = today.weekday()
                days_ahead = weekday_num - today_weekday
                if days_ahead <= 0:
                    days_ahead += 7
                days_ahead += 7  # 下周
                target_date = today + timedelta(days=days_ahead)
                return target_date.strftime('%Y-%m-%d')
        
        # 处理连续日期格式"连续X天"
        match = re.search(r'连续(\d+)天', date_str)
        if match:
            days = int(match.group(1))
            start_date = today + timedelta(days=1)  # 从明天开始
            end_date = start_date + timedelta(days=days-1)
            return f"{start_date.strftime('%Y-%m-%d')}-{end_date.strftime('%Y-%m-%d')}"
        
        # 处理日期范围格式 - 优先匹配跨月格式
        cross_month_patterns = [
            r'(\d+)月(\d+)日到(\d+)月(\d+)日',
            r'(\d+)月(\d+)日-(\d+)月(\d+)日',
            r'(\d+)月(\d+)日至(\d+)月(\d+)日',
            r'(\d+)月(\d+)号到(\d+)月(\d+)号',
            r'(\d+)月(\d+)号-(\d+)月(\d+)号',
            r'(\d+)月(\d+)号至(\d+)月(\d+)号'
        ]
        
        for pattern in cross_month_patterns:
            match = re.search(pattern, date_str)
            if match:
                try:
                    month1, day1, month2, day2 = match.groups()
                    year = today.year
                    
                    # 处理跨年情况
                    if int(month1) > int(month2):
                        year2 = year + 1
                    else:
                        year2 = year
                    
                    start_date = datetime(year, int(month1), int(day1))
                    end_date = datetime(year2, int(month2), int(day2))
                    return (start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d'))
                except ValueError:
                    continue
        
        # 处理同月日期范围格式
        same_month_patterns = [
            r'(\d+)月(\d+)日到(\d+)日',
            r'(\d+)月(\d+)日-(\d+)日',
            r'(\d+)月(\d+)日至(\d+)日',
            r'(\d+)月(\d+)号到(\d+)号',
            r'(\d+)月(\d+)号-(\d+)号',
            r'(\d+)月(\d+)号至(\d+)号'
        ]
        
        for pattern in same_month_patterns:
            match = re.search(pattern, date_str)
            if match:
                try:
                    month, day1, day2 = match.groups()
                    year = today.year
                    
                    start_date = datetime(year, int(month), int(day1))
                    end_date = datetime(year, int(month), int(day2))
                    return (start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d'))
                except ValueError:
                    continue
        
        # 处理单日期格式
        single_date_patterns = [
            r'(\d+)月(\d+)日',
            r'(\d+)月(\d+)号',
            r'(\d+)-(\d+)',
            r'(\d+)/(\d+)'
        ]
        
        for pattern in single_date_patterns:
            match = re.search(pattern, date_str)
            if match:
                try:
                    if pattern == r'(\d+)月(\d+)日':
                        month, day = match.groups()
                        year = today.year
                        target_date = datetime(year, int(month), int(day))
                        return target_date.strftime('%Y-%m-%d')
                    else:
                        # 简单的月-日格式
                        month, day = match.groups()
                        year = today.year
                        target_date = datetime(year, int(month), int(day))
                        return target_date.strftime('%Y-%m-%d')
                except ValueError:
                    continue
        
        # 如果无法解析，返回原始字符串
        return date_str

    def _check_continuous_availability(self, start_date: str, end_date: str, target_devices: List[str]) -> List[Dict]:
        """
        检查连续日期的设备可用性
        
        Args:
            start_date: 开始日期
            end_date: 结束日期
            target_devices: 目标设备列表
            
        Returns:
            可用设备列表
        """
        if self.feishu_reader is None:
            return []

        # 尝试解析日期
        try:
            start_dt = datetime.strptime(start_date, '%Y-%m-%d')
            end_dt = datetime.strptime(end_date, '%Y-%m-%d')
        except ValueError:
            return []

        # 逐天检查设备可用性
        current_dt = start_dt
        all_available = True
        available_devices = []

        while current_dt <= end_dt and all_available:
            current_date = current_dt.strftime('%Y-%m-%d')

            if target_devices:
                # 检查特定设备
                daily_available_names = []
                for device_name in target_devices:
                    status = self.feishu_reader.find_device_status_by_date(device_name, current_date)
                    if self.feishu_reader._is_device_available(status):  # 设备可用
                        daily_available_names.append(device_name)
                    else:
                        # 一旦发现某天某设备不可用，整个设备都不符合要求
                        all_available = False
            else:
                # 检查所有设备
                daily_available = self.feishu_reader.find_available_devices_by_date(
                    current_date, 
                    target_devices=None,
                    target_location=None
                )
                if daily_available:
                    daily_available_names = [device['name'] for device in daily_available]
                else:
                    all_available = False

            if not all_available:
                break

            # 如果这是第一天，初始化可用设备列表
            if not available_devices:
                available_devices = daily_available_names
            else:
                # 取交集：只保留每天都可用的设备
                available_devices = [name for name in available_devices if name in daily_available_names]

            current_dt += timedelta(days=1)

        # 转换为标准格式
        if target_devices:
            result = []
            for device_name in available_devices:
                # 获取设备位置信息
                status = self.feishu_reader.find_device_status_by_date(device_name, start_date)
                # 这里简化处理，实际需要从表格中获取位置信息
                result.append({
                    'name': device_name,
                    'location': 'Unknown',  # 实际应用中需要获取具体位置
                    'status': status
                })
            return result
        else:
            # 如果没有指定设备，返回所有设备的通用格式
            result = []
            for device_name in available_devices:
                result.append({
                    'name': device_name,
                    'location': 'Unknown',
                    'status': 'available'
                })
            return result