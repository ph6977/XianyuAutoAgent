#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试OpenAI客户端连接
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI

# 设置输出编码
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.detach())

# 加载环境变量
load_dotenv()

def test_openai_client():
    """测试OpenAI客户端"""
    print("="*50)
    print("OpenAI客户端测试")
    print("="*50)
    
    # 获取配置
    api_key = os.getenv("API_KEY") or os.getenv("DEEPSEEK_API_KEY")
    base_url = os.getenv("MODEL_BASE_URL", "https://api.deepseek.com")
    model_name = os.getenv("MODEL_NAME", "deepseek-chat")
    
    print(f"API Key: {api_key[:10]}...{api_key[-10:] if api_key else 'None'}")
    print(f"Base URL: {base_url}")
    print(f"Model: {model_name}")
    print()
    
    # 初始化客户端
    client = OpenAI(
        api_key=api_key,
        base_url=base_url
    )
    
    try:
        # 测试聊天
        response = client.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "user", "content": "你好，请回复'客户端测试成功'"}
            ],
            temperature=0.1,
            max_tokens=50
        )
        
        reply = response.choices[0].message.content
        print(f"[OK] 客户端测试成功")
        print(f"回复: {reply}")
        return True
        
    except Exception as e:
        print(f"[ERROR] 客户端测试失败: {e}")
        return False

if __name__ == "__main__":
    test_openai_client()