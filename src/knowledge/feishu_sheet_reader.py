#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
飞书表格读取器

本模块实现了与飞书电子表格的集成，用于：
1. 获取设备库存状态
2. 查询设备租赁情况
3. 检查设备可用性

工作流程：
调用飞书API → 获取表格数据 → 解析设备状态 → 返回可用设备列表

技术特点：
- OAuth2认证（自动获取访问令牌）
- 表格数据解析（支持合并单元格）
- 设备状态判断（空白/数字表示不同状态）
- 缓存机制（减少API调用）
"""

import os
import json
import requests
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from loguru import logger

class FeishuSheetReader:
    """
    飞书表格读取器
    
    负责与飞书电子表格交互，获取设备库存和租赁信息
    """
    
    def __init__(self, app_id: str, app_secret: str, spreadsheet_token: str, sheet_id: str):
        """
        初始化飞书表格读取器
        
        参数：
            app_id: 飞书应用ID
            app_secret: 飞书应用密钥
            spreadsheet_token: 电子表格token
            sheet_id: 工作表ID
        """
        self.app_id = app_id
        self.app_secret = app_secret
        self.spreadsheet_token = spreadsheet_token
        self.sheet_id = sheet_id
        self.access_token = None  # 访问令牌（缓存）
        self.session = requests.Session()
        
        # 设置请求头
        self.session.headers.update({
            'Content-Type': 'application/json; charset=utf-8'
        })
    
    def _get_access_token(self) -> str:
        """
        获取飞书访问令牌
        
        使用OAuth2认证获取访问令牌
        令牌有效期：2小时
        
        返回：
            str: 访问令牌
        """
        if self.access_token:
            return self.access_token
        
        try:
            url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
            
            data = {
                "app_id": self.app_id,
                "app_secret": self.app_secret
            }
            
            response = self.session.post(url, json=data, timeout=10)
            response.raise_for_status()
            
            result = response.json()
            if result.get('code') != 0:
                raise Exception(f"获取访问令牌失败: {result.get('msg')}")
            
            # 解析访问令牌（兼容不同响应格式）
            if 'tenant_access_token' in result:
                self.access_token = result['tenant_access_token']
            elif 'data' in result and 'access_token' in result['data']:
                self.access_token = result['data']['access_token']
            else:
                raise Exception(f"无法找到访问令牌，响应结构: {result}")
            
            return self.access_token
            
        except Exception as e:
            logger.error(f"获取飞书访问令牌失败: {e}")
            raise
    
    def _get_sheet_data(self) -> Dict:
        """
        获取表格数据，返回结构化数据
        
        表格结构说明：
        - 第一行：月份标识（如"10月"、"11月"）
        - 第二行：列名（"机型"、"所在地"、1-31日期数字）
        - 第三行及以后：设备数据行
        
        设备状态说明：
        - 空白/None：设备可租用（白色格子）
        - 数字1：设备在物流中（寄出）
        - 数字2：设备在客户手中（租赁中）
        - 数字3：设备在物流中（寄回）
        
        返回：
            Dict: 结构化表格数据
        """
        try:
            access_token = self._get_access_token()
            
            # 使用Sheets API获取电子表格数据
            url = f"https://open.feishu.cn/open-apis/sheets/v2/spreadsheets/{self.spreadsheet_token}/values/{self.sheet_id}"
            
            headers = {
                'Authorization': f'Bearer {access_token}',
                'Content-Type': 'application/json; charset=utf-8'
            }
            
            response = self.session.get(url, headers=headers, timeout=15)
            response.raise_for_status()
            
            result = response.json()
            if result.get('code') != 0:
                raise Exception(f"获取表格数据失败: {result.get('msg')}")
            
            # 解析表格数据
            values = result.get('data', {}).get('valueRange', {}).get('values', [])
            
            if not values or len(values) < 3:
                logger.warning("获取到的表格数据结构不完整")
                return {}
            
            month_headers = values[0]  # 月份标识行
            column_names = values[1]   # 列名行
            device_data = values[2:]   # 设备数据行
            
            # 构建结构化数据
            structured_data = {
                'month_headers': month_headers,
                'column_names': column_names,
                'device_data': device_data
            }
            
            logger.info(f"成功获取 {len(device_data)} 行设备数据")
            return structured_data
            
        except Exception as e:
            logger.error(f"获取表格数据失败: {e}")
            raise
    
    def _is_device_available(self, status_value) -> bool:
        """
        判断设备是否可租用
        
        根据飞书表格实际结构：
        - 空白/None/空字符串：设备可租用（白色格子）
        - 数字1：设备在物流中（寄出），不可租赁
        - 数字2：设备在客户手中（租赁中），不可租赁
        - 数字3：设备在物流中（寄回），不可租赁
        
        参数：
            status_value: 表格中的状态值
            
        返回：
            bool: True表示可租用，False表示不可租用
        """
        # 空白/None/空字符串都表示可租用
        if status_value is None or status_value == '' or status_value == 'None':
            return True
        
        # 数字表示设备正在使用中
        try:
            status_num = int(str(status_value).strip())
            # 任何数字状态都表示设备不可用
            return False
        except ValueError:
            # 非数字字符串，可能是其他状态标记
            # 根据文档，只有空白状态是可租用的
            return False
    
    
    
    def _find_device_row_new(self, device_name: str, sheet_data: Dict) -> Optional[List]:
        """
        精确匹配设备行（新格式）
        
        Args:
            device_name: 设备名称
            sheet_data: 结构化表格数据
            
        Returns:
            匹配的设备行数据，如果未找到返回None
        """
        device_data = sheet_data.get('device_data', [])
        column_names = sheet_data.get('column_names', [])
        
        device_name_col_index = None
        device_name_candidates = {'设备名称', '产品名称', '商品名称', '机型', '设备', '产品', '名称'}
        for i, col_name in enumerate(column_names):
            col_text = str(col_name).strip()
            if col_text in device_name_candidates:
                device_name_col_index = i
                break

        if device_name_col_index is None:
            device_name_col_index = 0

        for row in device_data:
            if device_name_col_index < len(row):
                cell_value = row[device_name_col_index]
                if cell_value and str(cell_value).strip() == device_name.strip():
                    return row

        return None
    
    def _find_date_column_index(self, sheet_data: Dict, month: int, day: int) -> Optional[int]:
        """
        根据月份和日期找到对应的列索引
        
        Args:
            sheet_data: 结构化表格数据
            month: 月份（1-12）
            day: 日期（1-31）
            
        Returns:
            列索引，如果未找到返回None
        """
        column_names = sheet_data.get('column_names', [])
        
        # 根据实际表格结构：
        # C1: 10月（合并单元格）
        # C2-AG2: 1-31（日期数字）
        # AH1: 11月（合并单元格）
        # AH2-BK2: 1-30（日期数字）
        
        # 找到月份标识的位置
        month_header_row = sheet_data.get('month_headers', [])
        date_row = sheet_data.get('column_names', [])
        
        logger.debug(f"查找月份 {month} 日期 {day}")
        logger.debug(f"月份头行内容: {month_header_row}")
        logger.debug(f"日期行内容: {date_row}")
        
        # 查找目标月份
        month_col_index = None
        for i, header in enumerate(month_header_row):
            if header and str(header).strip():  # 确保值不是None或空字符串
                header_str = str(header).strip()
                logger.debug(f"检查月份列 {i}: '{header_str}' 是否包含 '{month}月'")
                if f"{month}月" in header_str or f"{month}月" == header_str:
                    month_col_index = i
                    logger.debug(f"找到月份 {month} 在列索引 {i}")
                    break
        
        if month_col_index is None:
            # 如果没有找到月份标识，按照表格结构的逻辑：
            # 10月从C列开始（索引2），11月从AH列开始（索引33）
            if month == 10:
                month_start_col = 2  # C列
                logger.info(f"使用默认10月开始列: {month_start_col}")
            elif month == 11:
                month_start_col = 33  # AH列
                logger.info(f"使用默认11月开始列: {month_start_col}")
            else:
                # 对于其他月份，尝试查找
                logger.warning(f"未找到月份 {month} 的月份标识，尝试直接查找日期")
                # 直接在列名中查找目标日期
                for i, col_name in enumerate(date_row):
                    if col_name == day:
                        # 检查该列是否在合理的日期范围内
                        if 2 <= i <= 35:  # 10月日期范围
                            logger.info(f"找到日期 {day} 在10月范围列索引 {i}")
                            return i
                        elif 34 <= i <= 65:  # 11月日期范围
                            logger.info(f"找到日期 {day} 在11月范围列索引 {i}")
                            return i
                logger.warning(f"在所有可能范围内都未找到日期 {day}")
                return None
        else:
            month_start_col = month_col_index
        
        # 日期列从月份列的下一行开始（即month_start_col + 1）
        date_start_col = month_start_col + 1
        
        # 在日期行中查找目标日期
        logger.debug(f"在列范围 {date_start_col} 到 {min(date_start_col + 31, len(date_row))} 中查找日期 {day}")
        for i in range(date_start_col, min(date_start_col + 31, len(date_row))):
            if i < len(date_row) and date_row[i] == day:
                logger.info(f"找到日期 {day} 在列索引 {i}")
                return i
        
        logger.warning(f"未找到日期 {day} 在月份 {month} 的列")
        logger.debug(f"在范围 {date_start_col} 到 {min(date_start_col + 31, len(date_row))} 中未找到日期 {day}")
        return None
    
    
    
    def find_device_status_by_date(self, device_name: str, date: str) -> Optional[str]:
        """
        根据日期查找设备状态
        
        Args:
            device_name: 设备名称
            date: 日期字符串，格式如 "2025-11-05"
            
        Returns:
            设备状态值，如果未找到返回None
        """
        try:
            sheet_data = self._get_sheet_data()
            
            # 解析日期
            date_obj = datetime.strptime(date, '%Y-%m-%d')
            day = date_obj.day
            month = date_obj.month
            year = date_obj.year
            
            # 找到设备行
            device_row = self._find_device_row_new(device_name, sheet_data)
            if not device_row:
                logger.warning(f"未找到设备: {device_name}")
                return "DEVICE_NOT_FOUND"
            
            # 根据月份和日期找到对应的列索引
            column_index = self._find_date_column_index(sheet_data, month, day)
            if column_index is None:
                logger.warning(f"未找到日期 {date} 对应的列")
                return None
            
            # 获取状态值
            if column_index < len(device_row):
                date_value = device_row[column_index]
            else:
                date_value = None
            
            # 根据截图，白色格子（None/空）直接表示可租用，不需要继承
            # date_value 保持原样（None或空字符串）
            
            logger.info(f"设备 {device_name} 在 {date} 的状态: {date_value}")
            return date_value
            
        except Exception as e:
            logger.error(f"查找设备状态失败: {e}")
            return None
    
    def find_device_status_by_date_range(self, device_name: str, start_date: str, end_date: str) -> List[Tuple[str, str]]:
        """
        根据日期范围查找设备状态
        
        Args:
            device_name: 设备名称
            start_date: 开始日期
            end_date: 结束日期
            
        Returns:
            列表，每个元素为(日期, 状态)的元组
        """
        try:
            start_dt = datetime.strptime(start_date, '%Y-%m-%d')
            end_dt = datetime.strptime(end_date, '%Y-%m-%d')
            
            status_list = []
            current_dt = start_dt
            while current_dt <= end_dt:
                current_date = current_dt.strftime('%Y-%m-%d')
                status = self.find_device_status_by_date(device_name, current_date)
                status_list.append((current_date, status))
                current_dt += timedelta(days=1)
            
            return status_list
            
        except Exception as e:
            logger.error(f"查找设备日期范围状态失败: {e}")
            return []
    
    def find_available_devices_by_date(self, date: str, target_devices: List[str] = None, 
                                     target_location: str = None) -> List[Dict]:
        """
        根据日期查找可用设备
        
        Args:
            date: 日期字符串
            target_devices: 目标设备列表，如果为None则查询所有设备
            target_location: 目标位置，如果指定则只返回该位置的设备
            
        Returns:
            可用设备列表
        """
        try:
            sheet_data = self._get_sheet_data()
            available_devices = []
            
            device_data = sheet_data.get('device_data', [])
            column_names = sheet_data.get('column_names', [])
            
            # 找到设备名称和位置列的索引
            device_name_col_index = None
            location_col_index = None
            for i, col_name in enumerate(column_names):
                if col_name == '机型':
                    device_name_col_index = i
                elif col_name == '所在地':
                    location_col_index = i
            
            if device_name_col_index is None:
                logger.warning("未找到设备名称列")
                return []
            
            logger.debug(f"查找日期 {date} 的设备，目标设备列表: {target_devices}")
            
            for row in device_data:
                # 获取设备名称
                if device_name_col_index >= len(row) or not row[device_name_col_index]:
                    continue
                
                device_name = str(row[device_name_col_index]).strip()
                logger.debug(f"检查设备: {device_name}")
                
                # 如果指定了目标设备，检查是否匹配（精确匹配）
                if target_devices:
                    device_match = False
                    for target_device in target_devices:
                        logger.debug(f"  比较目标设备: '{target_device.strip()}' vs '{device_name}'")
                        if device_name == target_device.strip():
                            device_match = True
                            logger.debug(f"  找到匹配设备: {device_name}")
                            break
                    if not device_match:
                        logger.debug(f"  设备 {device_name} 不在目标列表中，跳过")
                        continue
                
                # 获取设备位置
                location = '未知'
                if (location_col_index is not None and 
                    location_col_index < len(row) and 
                    row[location_col_index]):
                    location = str(row[location_col_index]).strip()
                
                # 检查位置是否匹配
                if target_location and target_location not in location:
                    logger.debug(f"  设备 {device_name} 位置 {location} 不匹配目标位置 {target_location}，跳过")
                    continue
                
                # 检查设备在指定日期的状态
                logger.debug(f"  查询设备 {device_name} 在日期 {date} 的状态")
                status = self.find_device_status_by_date(device_name, date)
                logger.debug(f"  设备 {device_name} 在 {date} 的状态: {status}")
                
                # 根据状态判断是否可用
                is_available = self._is_device_available(status)
                logger.debug(f"  设备 {device_name} 在 {date} 可用: {is_available}")
                
                if is_available:
                    device_info = {
                        'name': device_name,
                        'location': location,
                        'status': status
                    }
                    available_devices.append(device_info)
                    logger.debug(f"  添加可用设备: {device_info}")
            
            logger.info(f"日期 {date} 找到 {len(available_devices)} 个可用设备")
            logger.debug(f"可用设备列表: {[d['name'] for d in available_devices]}")
            return available_devices
            
        except Exception as e:
            logger.error(f"查找可用设备失败: {e}")
            return []
    
    def find_available_devices_by_date_range(self, start_date: str, end_date: str, 
                                           target_devices: List[str] = None, 
                                           target_location: str = None) -> List[Dict]:
        """
        根据日期范围查找可用设备
        
        Args:
            start_date: 开始日期
            end_date: 结束日期
            target_devices: 目标设备列表
            target_location: 目标位置
            
        Returns:
            可用设备列表
        """
        try:
            start_dt = datetime.strptime(start_date, '%Y-%m-%d')
            end_dt = datetime.strptime(end_date, '%Y-%m-%d')
            
            # 获取所有日期的可用设备交集
            all_available_devices = None
            
            current_dt = start_dt
            while current_dt <= end_dt:
                current_date = current_dt.strftime('%Y-%m-%d')
                daily_available = self.find_available_devices_by_date(
                    current_date, target_devices, target_location
                )
                
                if all_available_devices is None:
                    all_available_devices = daily_available
                else:
                    # 取交集：只保留每天都可用的设备
                    available_names = {d['name'] for d in daily_available}
                    all_available_devices = [
                        d for d in all_available_devices 
                        if d['name'] in available_names
                    ]
                
                current_dt += timedelta(days=1)
            
            logger.info(f"日期范围 {start_date} 到 {end_date} 找到 {len(all_available_devices or [])} 个连续可用设备")
            return all_available_devices or []
            
        except Exception as e:
            logger.error(f"查找日期范围可用设备失败: {e}")
            return []
    
    def query_device_info(self, device_name: str) -> List[Dict]:
        """
        查询设备信息（包括价格等）
        
        Args:
            device_name: 设备名称或关键词
            
        Returns:
            设备信息列表
        """
        try:
            sheet_data = self._get_sheet_data()
            matching_devices = []
            
            # 获取设备数据行
            device_data = sheet_data.get('device_data', [])
            column_names = sheet_data.get('column_names', [])
            
            # 找到设备名称列的索引
            device_name_col_index = None
            device_name_candidates = {'设备名称', '产品名称', '设备', 'product_name', 'name', '设备名', '机型'}
            for i, col_name in enumerate(column_names):
                if str(col_name) in device_name_candidates:
                    device_name_col_index = i
                    break
            
            # 如果没有找到设备名称列，使用默认索引
            if device_name_col_index is None:
                device_name_col_index = 0  # 默认第一列为设备名
            
            # 遍历设备数据行
            for row in device_data:
                # 获取设备名称
                current_device_name = None
                if device_name_col_index < len(row) and row[device_name_col_index]:
                    current_device_name = str(row[device_name_col_index])
                
                # 检查设备名称是否匹配（包含关键词）
                if current_device_name and device_name.lower() in current_device_name.lower():
                    # 构建设备信息字典
                    device_info = {
                        '设备名称': current_device_name
                    }
                    
                    # 添加所有列的信息
                    for i, col_name in enumerate(column_names):
                        if i < len(row) and row[i] is not None:
                            device_info[str(col_name)] = str(row[i])
                    
                    matching_devices.append(device_info)
            
            logger.info(f"查询 '{device_name}' 找到 {len(matching_devices)} 个设备")
            return matching_devices
            
        except Exception as e:
            logger.error(f"查询设备信息失败: {e}")
            return []

    def find_devices_by_location(self, location: str) -> List[Dict]:
        """
        根据位置查找设备
        
        Args:
            location: 位置信息
            
        Returns:
            设备列表
        """
        try:
            sheet_data = self._get_sheet_data()
            matching_devices = []
            
            # 获取设备数据行
            device_data = sheet_data.get('device_data', [])
            column_names = sheet_data.get('column_names', [])
            
            # 找到位置列的索引
            location_col_index = None
            location_candidates = {'位置', '城市', '所在城市', 'city', 'location', '所在位置', '所在地'}
            for i, col_name in enumerate(column_names):
                if str(col_name) in location_candidates:
                    location_col_index = i
                    break
            
            # 找到设备名称列的索引
            device_name_col_index = None
            device_name_candidates = {'设备名称', '产品名称', '设备', 'product_name', 'name', '设备名', '机型'}
            for i, col_name in enumerate(column_names):
                if str(col_name) in device_name_candidates:
                    device_name_col_index = i
                    break
            
            # 如果没有找到关键列，使用默认索引
            if device_name_col_index is None:
                device_name_col_index = 0  # 默认第一列为设备名
            if location_col_index is None:
                location_col_index = 1    # 默认第二列为位置
            
            # 遍历设备数据行
            for row in device_data:
                # 获取位置信息
                device_location = None
                if location_col_index < len(row) and row[location_col_index]:
                    device_location = str(row[location_col_index])
                
                # 检查位置是否匹配
                if device_location and location in device_location:
                    # 获取设备名称
                    device_name = None
                    if device_name_col_index < len(row) and row[device_name_col_index]:
                        device_name = str(row[device_name_col_index])
                    
                    if device_name:
                        matching_devices.append({
                            'name': device_name,
                            'location': device_location
                        })
            
            logger.info(f"位置 {location} 找到 {len(matching_devices)} 个设备")
            return matching_devices
            
        except Exception as e:
            logger.error(f"按位置查找设备失败: {e}")
            return []

# 测试代码
if __name__ == "__main__":
    import os
    from datetime import datetime
    
    # 从环境变量获取配置
    app_id = os.getenv("FEISHU_APP_ID")
    app_secret = os.getenv("FEISHU_APP_SECRET")
    spreadsheet_token = os.getenv("FEISHU_SPREADSHEET_TOKEN")
    sheet_id = os.getenv("FEISHU_SHEET_ID")
    
    if all([app_id, app_secret, spreadsheet_token, sheet_id]):
        reader = FeishuSheetReader(app_id, app_secret, spreadsheet_token, sheet_id)
        
        # 测试设备状态判断
        test_cases = [None, '', '0', '被预定', '1', '2', '3']
        print("设备状态判断测试:")
        for case in test_cases:
            is_available = reader._is_device_available(case)
            print(f"  状态值: {case} -> 可租用: {is_available}")
        
        # 测试日期查询
        today = datetime.now().strftime('%Y-%m-%d')
        print(f"\n测试查询日期: {today}")
        
        try:
            available = reader.find_available_devices_by_date(today)
            print(f"找到 {len(available)} 个可用设备")
            for device in available[:3]:  # 只显示前3个
                print(f"  - {device['name']} ({device['location']})")
        except Exception as e:
            print(f"查询失败: {e}")
    else:
        print("缺少飞书API配置，跳过测试")