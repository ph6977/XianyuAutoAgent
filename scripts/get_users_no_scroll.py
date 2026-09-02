#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
获取当前页面用户昵称测试（无滚动功能）
"""

import time
import re
from loguru import logger

def get_current_page_users_no_scroll():
    """获取当前页面可见的用户昵称（不滚动）"""
    print("开始获取当前页面用户昵称（无滚动）...")
    
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
            return []
        
        # 登录并导航
        success = crawler.login_and_navigate()
        if success:
            print("✅ 成功进入页面")
        else:
            print("❌ 页面导航失败")
            return []
        
        print("等待页面加载...")
        time.sleep(8)  # 等待动态内容加载
        
        user_nicknames = []
        
        # 使用JavaScript直接从页面DOM获取所有可能包含用户信息的元素
        print("使用JavaScript获取页面上的用户昵称...")
        
        # JavaScript代码，专门查找可能的用户昵称元素
        js_code = """
        (function() {
            var results = [];
            
            // 查找所有可能是用户昵称的元素
            var allElements = document.querySelectorAll('*');
            
            for (var i = 0; i < allElements.length; i++) {
                var element = allElements[i];
                var text = element.textContent ? element.textContent.trim() : '';
                
                // 检查文本长度和内容
                if (text && text.length > 1 && text.length < 20) {
                    // 检查是否包含中文、英文或数字（用户昵称的特征）
                    if (/[{u4e00}-{u9fa5}a-zA-Z0-9]/.test(text)) {
                        // 检查元素是否可能包含用户昵称
                        var className = element.className || '';
                        var style = element.getAttribute('style') || '';
                        var id = element.id || '';
                        
                        // 用户昵称通常具有某些特征
                        var hasUserNicknameFeatures = 
                            // 包含特定关键词
                            /user|nick|name|contact|item|conversation/i.test(className + id) ||
                            // 具有特定样式（溢出省略）
                            /ellipsis|nowrap|overflow/.test(style) ||
                            // 在特定容器内
                            element.closest('.conversation-item--JReyg97P') !== null ||
                            element.closest('.rc-virtual-list-holder') !== null ||
                            element.closest('.im-main--kaKv06s8') !== null;
                        
                        // 过滤系统文本
                        var isSystem = [
                            '搜索', '联系人', '消息', '聊天', '最近', '全部', '暂无', 
                            '通知', '通', '知', '设置', '客服', '官方', '系统', 
                            '公告', '帮助', '历史', '记录', '统计', '时间', '日期',
                            '上午', '下午', '刚刚', '分钟前', '小时前', '显示',
                            '更多', '加载', '刷新', '设置', '退出', '登录', '闲鱼',
                            '个人', '资料', '详情', '返回', '发送', '输入', '复制',
                            '转发', '删除', '举报', '拉黑', '点赞', '赞', '收藏',
                            '语音', '图片', '表情', '红包', '转账', '名片', '位置'
                        ].some(function(keyword) {
                            return text.toLowerCase().includes(keyword.toLowerCase()) || 
                                   keyword.toLowerCase().includes(text.toLowerCase());
                        });
                        
                        if (!isSystem && (hasUserNicknameFeatures || text.length > 1)) {
                            results.push({
                                text: text,
                                className: className,
                                tagName: element.tagName,
                                style: style
                            });
                        }
                    }
                }
            }
            
            return results;
        })();
        """
        
        try:
            elements_data = crawler.page.run_js(js_code)
            print(f"通过JavaScript获取到 {len(elements_data)} 个潜在用户元素")
            
            for item in elements_data:
                if isinstance(item, dict) and 'text' in item:
                    text = item['text']
                    if text and len(text) > 1 and len(text) < 20 and text not in user_nicknames:
                        user_nicknames.append(text)
                        print(f"找到用户: '{text}' (标签: {item.get('tagName', 'N/A')})")
                        
            print(f"\n总共找到 {len(user_nicknames)} 个用户昵称:")
            for i, nickname in enumerate(user_nicknames, 1):
                print(f"  {i}. {nickname}")
                
        except Exception as js_error:
            print(f"JavaScript执行失败: {js_error}")
            print("尝试使用页面元素方法...")
            
            # 尝试获取所有div和span元素
            try:
                all_elements = crawler.page.eles('*', timeout=5)
                print(f"找到 {len(all_elements)} 个页面元素")
                
                for element in all_elements:
                    try:
                        text = element.text.strip()
                        if text and 1 < len(text) < 20:
                            # 过滤系统文本
                            system_keywords = [
                                '搜索', '联系人', '消息', '聊天', '最近', '全部', '暂无', 
                                '通知', '通', '知', '设置', '客服', '官方', '系统', 
                                '公告', '帮助', '历史', '记录', '统计', '时间', '日期',
                                '上午', '下午', '刚刚', '分钟前', '小时前', '显示',
                                '更多', '加载', '刷新', '设置', '退出', '登录', '闲鱼'
                            ]
                            
                            is_system = any(keyword in text.lower() for keyword in system_keywords)
                            
                            # 检查是否包含有效字符
                            has_valid_chars = bool(re.search(r'[{u4e00}-{u9fff}]|[a-zA-Z0-9]', text))
                            
                            if not is_system and has_valid_chars and text not in user_nicknames:
                                user_nicknames.append(text)
                                print(f"找到用户: {text}")
                                
                    except:
                        continue
                        
            except Exception as e:
                print(f"页面元素方法也失败: {e}")
        
        print(f"\n最终获取到 {len(user_nicknames)} 个用户昵称")
        return user_nicknames
        
    except Exception as e:
        print(f"❌ 出错: {e}")
        import traceback
        traceback.print_exc()
        return []
    finally:
        try:
            if 'crawler' in locals():
                print("关闭浏览器...")
                crawler.page.quit()
        except:
            pass

if __name__ == "__main__":
    print("当前页面用户昵称获取测试（无滚动）")
    print("=" * 50)
    users = get_current_page_users_no_scroll()
    print(f"\n测试完成，共找到 {len(users)} 个用户")
    input("按回车退出...")
