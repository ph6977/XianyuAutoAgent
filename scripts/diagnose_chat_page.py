#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
诊断聊天页面 - 分析为什么无法找到消息元素
"""

import os
import sys
import time
import logging
from DrissionPage import ChromiumPage, ChromiumOptions

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(name)s:%(funcName)s:%(lineno)d - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

class ChatPageDiagnoser:
    def __init__(self):
        self.page = None

    def init_browser(self):
        """初始化浏览器"""
        try:
            options = ChromiumOptions()
            options.set_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36')

            # 加载现有cookies
            cookies_str = self._load_cookies_from_env()
            if cookies_str:
                logger.info("检测到现有cookies，将尝试使用")
                options.set_argument(f'--initial-url=https://www.goofish.com/im?spm=a21ybx.account.sidebar.2.6a3035ca2iyGly')

            self.page = ChromiumPage(options)
            logger.info("浏览器初始化完成")
            return True

        except Exception as e:
            logger.error(f"浏览器初始化失败: {e}")
            return False

    def _load_cookies_from_env(self):
        """从.env文件加载cookies"""
        try:
            env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
            if os.path.exists(env_path):
                with open(env_path, 'r', encoding='utf-8') as f:
                    for line in f:
                        if line.startswith('COOKIES_STR='):
                            return line[len('COOKIES_STR='):].strip()
        except Exception as e:
            logger.warning(f"加载cookies失败: {e}")
        return None

    def login_and_navigate(self):
        """登录并导航到闲鱼聊天页面"""
        try:
            logger.info("正在打开闲鱼聊天页面...")
            self.page.get("https://www.goofish.com/im?spm=a21ybx.account.sidebar.2.6a3035ca2iyGly")
            time.sleep(10)

            logger.info(f"当前页面URL: {self.page.url}")
            logger.info("成功进入闲鱼聊天页面")
            return True
        except Exception as e:
            logger.error(f"导航到聊天页面失败: {e}")
            return False

    def click_first_user(self):
        """点击第一个用户"""
        try:
            logger.info("尝试点击用户列表中的第一个用户...")
            time.sleep(5)

            # 点击第一个用户
            click_result = self.page.run_js("""
                var userList = document.querySelector('.rc-virtual-list-holder');
                if (!userList) {
                    return '未找到用户列表';
                }

                var userElements = userList.querySelectorAll('[class*="user"], [class*="contact"], [class*="conversation"]');
                if (userElements.length > 0) {
                    userElements[0].click();
                    return '点击成功';
                }
                return '未找到用户元素';
            """)

            logger.info(f"点击用户结果: {click_result}")
            time.sleep(5)
            return True

        except Exception as e:
            logger.error(f"点击用户失败: {e}")
            return False

    def diagnose_chat_page(self):
        """诊断聊天页面结构"""
        try:
            logger.info("=== 开始诊断聊天页面 ===")

            # 等待聊天页面加载
            time.sleep(5)

            # 1. 检查页面基本信息
            print("\n" + "="*50)
            print("页面基本信息")
            print("="*50)
            print(f"当前URL: {self.page.url}")
            print(f"页面标题: {self.page.title}")
            print(f"页面HTML长度: {len(self.page.html)}")

            # 2. 检查聊天区域
            print("\n" + "="*50)
            print("聊天区域检查")
            print("="*50)

            chat_containers = [
                '.message-list-reverse--P5t12NwJ',
                '.scroll-container--WObNWx73',
                '.chat-container',
                '.message-area',
                '.chat-area',
                '.im-area'
            ]

            for selector in chat_containers:
                element = self.page.ele(selector, timeout=2)
                if element:
                    print(f"[OK] 找到聊天容器: {selector}")
                    print(f"   元素HTML: {element.html[:200]}...")
                else:
                    print(f"[FAIL] 未找到聊天容器: {selector}")

            # 3. 检查消息元素
            print("\n" + "="*50)
            print("消息元素检查")
            print("="*50)

            message_selectors = [
                '[class*="message"]',
                '[class*="msg"]',
                '[class*="chat"]',
                '[class*="im"]',
                '.J_Message',
                '.J_ChatMessage'
            ]

            for selector in message_selectors:
                elements = self.page.eles(selector)
                if elements:
                    print(f"[OK] 找到消息元素 (选择器: {selector}): {len(elements)} 个")
                    for i, element in enumerate(elements[:3]):  # 只显示前3个
                        print(f"   消息 {i+1}: {element.text[:100]}")
                else:
                    print(f"[FAIL] 未找到消息元素: {selector}")

            # 4. 检查文本内容
            print("\n" + "="*50)
            print("页面文本内容检查")
            print("="*50)

            all_text_elements = self.page.eles('text=.+')
            print(f"找到 {len(all_text_elements)} 个文本元素")

            # 显示前10个文本元素
            for i, element in enumerate(all_text_elements[:10]):
                text = element.text.strip()
                if text and len(text) > 1:
                    print(f"   {i+1}. {text[:100]}")

            # 5. 检查滚动容器状态
            print("\n" + "="*50)
            print("滚动容器状态")
            print("="*50)

            scroll_info = self.page.run_js("""
                var scrollContainer = document.querySelector('.scroll-container--WObNWx73');
                if (!scrollContainer) {
                    return { error: '未找到滚动容器' };
                }

                var computedStyle = window.getComputedStyle(scrollContainer);

                // 查找所有子元素
                var children = scrollContainer.children;
                var childInfo = [];
                for (var i = 0; i < children.length; i++) {
                    childInfo.push({
                        'tag': children[i].tagName,
                        'class': children[i].className,
                        'text': children[i].textContent.substring(0, 50)
                    });
                }

                return {
                    'transform': computedStyle.transform,
                    'children': childInfo,
                    'childCount': children.length
                };
            """)

            print(f"滚动容器状态: {scroll_info}")

            # 6. 检查页面结构
            print("\n" + "="*50)
            print("页面结构分析")
            print("="*50)

            structure_info = self.page.run_js("""
                // 查找所有包含消息相关class的元素
                var messageElements = document.querySelectorAll('[class*="message"], [class*="msg"], [class*="chat"], [class*="im"]');
                var structure = [];

                for (var i = 0; i < messageElements.length; i++) {
                    var element = messageElements[i];
                    var rect = element.getBoundingClientRect();

                    if (rect.width > 0 && rect.height > 0) {  // 只显示可见元素
                        structure.push({
                            'class': element.className,
                            'tag': element.tagName,
                            'text': element.textContent.substring(0, 100),
                            'visible': rect.top >= 0 && rect.bottom <= window.innerHeight
                        });
                    }
                }

                return {
                    'totalElements': messageElements.length,
                    'visibleElements': structure.filter(e => e.visible).length,
                    'structure': structure.slice(0, 10)  // 只显示前10个
                };
            """)

            print(f"页面结构分析: {structure_info}")

            return True

        except Exception as e:
            logger.error(f"诊断聊天页面失败: {e}")
            return False

def main():
    """主函数"""
    diagnoser = ChatPageDiagnoser()

    try:
        # 初始化浏览器
        if not diagnoser.init_browser():
            return

        # 登录并导航到聊天页面
        if not diagnoser.login_and_navigate():
            return

        # 点击第一个用户
        if not diagnoser.click_first_user():
            return

        # 诊断聊天页面
        if diagnoser.diagnose_chat_page():
            logger.info("✅ 诊断完成！")
        else:
            logger.error("❌ 诊断失败")

        # 不关闭浏览器，让用户继续观察
        logger.info("诊断完成，浏览器保持打开状态...")
        print("\n诊断完成，浏览器保持打开状态，您可以继续观察页面...")

    except Exception as e:
        logger.error(f"诊断过程中出错: {e}")

if __name__ == "__main__":
    main()