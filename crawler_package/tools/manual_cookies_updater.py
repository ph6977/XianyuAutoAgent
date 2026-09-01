#!/usr/bin/env python3
"""
手动Cookies更新工具 - 用于启动菜单集成
"""

import os
import sys
import asyncio
from cookie_refresher import manual_update_cookies_main


def main():
    """命令行入口函数"""
    if len(sys.argv) < 2:
        print("用法: python manual_cookies_updater.py \"cookies_string\"")
        print("示例: python manual_cookies_updater.py \"cookie1=value1; cookie2=value2\"")
        sys.exit(1)

    cookies_str = sys.argv[1]

    # 运行异步主函数
    success = asyncio.run(manual_update_cookies_main(cookies_str))

    if success:
        print("✅ Cookies手动更新成功")
        sys.exit(0)
    else:
        print("❌ Cookies手动更新失败")
        sys.exit(1)


if __name__ == '__main__':
    main()