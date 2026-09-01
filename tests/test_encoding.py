#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""测试编码修复"""

print("=" * 60)
print("编码测试")
print("=" * 60)
print("系统初始化成功")
print("=" * 60)

from xianyu_bot_components.core.context_manager import ChatContextManager
from xianyu_bot_components.关键问题回复.intent_analyzer import IntentAnalyzer

try:
    context_manager = ChatContextManager()
    intent_analyzer = IntentAnalyzer(context_manager=context_manager)
    print("所有组件初始化成功")
except Exception as e:
    print(f"初始化失败: {e}")

print("=" * 60)