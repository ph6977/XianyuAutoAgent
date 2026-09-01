#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""测试飞书数据格式"""

import os
import sys
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from feishu_knowledge_base.feishu_sheet_reader import FeishuSheetReader

# 初始化飞书读取器
app_id = os.getenv("FEISHU_APP_ID")
app_secret = os.getenv("FEISHU_APP_SECRET")
spreadsheet_token = os.getenv("FEISHU_SPREADSHEET_TOKEN")
sheet_id = os.getenv("FEISHU_SHEET_ID")

feishu_reader = FeishuSheetReader(app_id, app_secret, spreadsheet_token, sheet_id)
data = feishu_reader._get_sheet_data()

print("数据类型:", type(data))
print("数据键:", data.keys() if isinstance(data, dict) else "不是字典")

if isinstance(data, dict):
    device_data = data.get('device_data', [])
    print("device_data类型:", type(device_data))
    print("device_data长度:", len(device_data))
    if device_data:
        print("第一行数据:", device_data[0])
        print("第一行数据类型:", type(device_data[0]))