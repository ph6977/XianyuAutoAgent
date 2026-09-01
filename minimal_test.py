#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
最简化用户获取测试
"""

import time

def minimal_test():
    print("最简化用户获取测试")
    
    try:
        from crawler_components.tools.batch_user_crawler import BatchUserCrawler
        print("✅ 导入成功")
        
        # 创建爬虫实例
        crawler = BatchUserCrawler(headless=False)
        print("✅ 创建实例成功")
        
        # 初始化浏览器
        if crawler.init_browser():
            print("✅ 浏览器初始化成功")
        else:
            print("❌ 浏览器初始化失败")
            return False
        
        # 登录并导航
        success = crawler.login_and_navigate()
        if success:
            print("✅ 成功进入页面")
        else:
            print("❌ 页面导航失败")
            return False
        
        print("等待页面加载...")
        time.sleep(8)
        
        # 直接调用更新后的获取用户方法
        print("开始获取用户...")
        users = crawler._get_chat_list_users(max_users=10)
        print(f"获取到 {len(users)} 个用户: {users}")
        
        if users:
            print("✅ 成功获取到用户昵称！")
            return True
        else:
            print("❌ 未获取到用户昵称")
            return False
            
    except Exception as e:
        print(f"❌ 出错: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        try:
            if 'crawler' in locals():
                print("关闭浏览器...")
                crawler.page.quit()
        except:
            pass

if __name__ == "__main__":
    minimal_test()
    input("按回车退出...")