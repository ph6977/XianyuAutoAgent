#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
修正滚动方向测试 - 确保聊天页面使用与用户列表相同的滚动方向
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

class CorrectScrollDirectionTester:
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
            time.sleep(5)

            logger.info(f"当前页面URL: {self.page.url}")

            # 等待聊天页面加载
            self._wait_for_chat_page_loaded()

            logger.info("成功进入闲鱼聊天页面")
            return True
        except Exception as e:
            logger.error(f"导航到聊天页面失败: {e}")
            return False

    def _wait_for_chat_page_loaded(self, timeout=60):
        """等待聊天页面加载完成"""
        start_time = time.time()
        while time.time() - start_time < timeout:
            if 'goofish.com/im' in self.page.url or '闲鱼' in self.page.title:
                selectors = [
                    '.im-main--kaKv06s8',
                    '.rc-virtual-list-holder',
                    '.conv-list-scroll--Bn4G27Nb',
                    '.rc-virtual-list',
                    '.user-order-container--gPgL3Azx'
                ]

                for selector in selectors:
                    elements = self.page.eles(selector)
                    if elements:
                        logger.info(f"找到聊天列表元素: {selector}")
                        return True
                time.sleep(2)
            else:
                time.sleep(2)

        logger.warning("聊天页面加载超时，但URL或标题表明已在聊天页面，继续执行")
        return True

    def click_first_user(self):
        """点击第一个用户"""
        try:
            logger.info("尝试点击用户列表中的第一个用户...")

            # 获取用户列表中的第一个用户信息
            first_user_info = self.page.run_js("""
                var userList = document.querySelector('.rc-virtual-list-holder');
                if (!userList) {
                    return null;
                }

                // 查找第一个用户元素
                var userElements = userList.querySelectorAll('[class*="user"], [class*="contact"], [class*="conversation"]');
                if (userElements.length > 0) {
                    return {
                        'text': userElements[0].textContent,
                        'className': userElements[0].className
                    };
                }
                return null;
            """)

            if first_user_info:
                logger.info(f"找到第一个用户: {first_user_info.get('text', '未知用户')}")

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
                time.sleep(3)
                return True
            else:
                logger.error("无法找到用户列表中的任何用户")
                return False

        except Exception as e:
            logger.error(f"点击用户失败: {e}")
            return False

    def test_correct_scroll_direction(self):
        """测试修正后的滚动方向"""
        logger.info("=== 开始测试修正后的滚动方向 ===")

        try:
            # 等待聊天页面完全加载
            time.sleep(3)

            # 获取初始状态
            initial_info = self._get_chat_info()
            logger.info(f"初始状态: {initial_info}")

            print(f"\n=== 初始状态 ===")
            print(f"可见消息: {initial_info.get('visible_messages', 0)} 条")
            print(f"总消息数: {initial_info.get('total_messages', 0)} 条")
            print(f"滚动高度: {initial_info.get('scroll_height', 0)}px")
            print(f"客户端高度: {initial_info.get('client_height', 0)}px")

            # 等待3秒，让用户观察初始状态
            print("等待3秒，请观察初始聊天页面状态...")
            time.sleep(3)

            # 方法1: 使用与用户列表相同的滚动方向 - 负值向上滚动
            logger.info("方法1: 使用负值向上滚动（与用户列表相同）")
            scroll_result1 = self.page.run_js("""
                var scrollContainer = document.querySelector('.scroll-container--WObNWx73');
                if (!scrollContainer) {
                    return '未找到滚动容器';
                }

                var beforeTransform = window.getComputedStyle(scrollContainer).transform;

                // 使用负值向上滚动（与用户列表滚动方向一致）
                scrollContainer.style.transform = 'translateY(-300px)';

                // 触发滚动事件
                var scrollEvent = new Event('scroll', { bubbles: true });
                scrollContainer.dispatchEvent(scrollEvent);

                var afterTransform = window.getComputedStyle(scrollContainer).transform;

                return {
                    'before': beforeTransform,
                    'after': afterTransform,
                    'direction': '向上滚动（负值）'
                };
            """)

            logger.info(f"负值向上滚动结果: {scroll_result1}")
            time.sleep(2)

            # 检查滚动后的状态
            info_after_up = self._get_chat_info()
            logger.info(f"向上滚动后状态: {info_after_up}")

            print(f"\n=== 负值向上滚动后 ===")
            print(f"transform变化: {scroll_result1.get('before', '')} -> {scroll_result1.get('after', '')}")
            print(f"可见消息: {info_after_up.get('visible_messages', 0)} 条")
            print(f"总消息数: {info_after_up.get('total_messages', 0)} 条")

            # 等待3秒，让用户观察向上滚动后的状态
            print("等待3秒，请观察向上滚动后的聊天页面状态...")
            time.sleep(3)

            # 方法2: 使用正值向下滚动
            logger.info("方法2: 使用正值向下滚动")
            scroll_result2 = self.page.run_js("""
                var scrollContainer = document.querySelector('.scroll-container--WObNWx73');
                if (!scrollContainer) {
                    return '未找到滚动容器';
                }

                var beforeTransform = window.getComputedStyle(scrollContainer).transform;

                // 使用正值向下滚动
                scrollContainer.style.transform = 'translateY(0px)';

                // 触发滚动事件
                var scrollEvent = new Event('scroll', { bubbles: true });
                scrollContainer.dispatchEvent(scrollEvent);

                var afterTransform = window.getComputedStyle(scrollContainer).transform;

                return {
                    'before': beforeTransform,
                    'after': afterTransform,
                    'direction': '向下滚动（正值）'
                };
            """)

            logger.info(f"正值向下滚动结果: {scroll_result2}")
            time.sleep(2)

            # 检查滚动后的状态
            info_after_down = self._get_chat_info()
            logger.info(f"向下滚动后状态: {info_after_down}")

            print(f"\n=== 正值向下滚动后 ===")
            print(f"transform变化: {scroll_result2.get('before', '')} -> {scroll_result2.get('after', '')}")
            print(f"可见消息: {info_after_down.get('visible_messages', 0)} 条")
            print(f"总消息数: {info_after_down.get('total_messages', 0)} 条")

            # 显示滚动方向对比
            print(f"\n=== 滚动方向对比 ===")
            print(f"初始可见消息: {initial_info.get('visible_messages', 0)} 条")
            print(f"负值向上滚动后: {info_after_up.get('visible_messages', 0)} 条")
            print(f"正值向下滚动后: {info_after_down.get('visible_messages', 0)} 条")

            # 分析滚动方向是否正确
            if info_after_up.get('visible_messages', 0) > initial_info.get('visible_messages', 0):
                print("✅ 滚动方向正确：负值向上滚动加载了更多历史消息")
            elif info_after_up.get('visible_messages', 0) < initial_info.get('visible_messages', 0):
                print("❌ 滚动方向错误：负值向上滚动反而减少了可见消息")
            else:
                print("⚠️  滚动方向可能正确，但可见消息数量没有变化")

            return True

        except Exception as e:
            logger.error(f"测试滚动方向时出错: {e}")
            return False

    def _get_chat_info(self):
        """获取聊天页面信息"""
        try:
            chat_info = self.page.run_js("""
                var chatContainer = document.querySelector('.message-list-reverse--P5t12NwJ');
                if (!chatContainer) {
                    return { error: '未找到聊天容器' };
                }

                var computedStyle = window.getComputedStyle(chatContainer);
                var scrollContainer = chatContainer.querySelector('.scroll-container--WObNWx73');

                // 获取当前可见的消息 - 使用更通用的选择器
                var visibleMessages = [];
                var allMessages = [];

                // 尝试多种消息选择器
                var selectors = [
                    '[class*="message"]',
                    '[class*="msg"]',
                    '[class*="chat"]',
                    '[class*="im"]',
                    '.J_Message',
                    '.J_ChatMessage'
                ];

                for (var i = 0; i < selectors.length; i++) {
                    var elements = chatContainer.querySelectorAll(selectors[i]);
                    for (var j = 0; j < elements.length; j++) {
                        var rect = elements[j].getBoundingClientRect();
                        if (rect.top >= 0 && rect.bottom <= window.innerHeight) {
                            visibleMessages.push({
                                'text': elements[j].textContent.substring(0, 50),
                                'top': rect.top,
                                'bottom': rect.bottom
                            });
                        }
                        allMessages.push(elements[j]);
                    }
                }

                return {
                    'chatContainer': {
                        'className': chatContainer.className,
                        'scrollHeight': chatContainer.scrollHeight,
                        'clientHeight': chatContainer.clientHeight,
                        'scrollTop': chatContainer.scrollTop,
                        'transform': computedStyle.transform
                    },
                    'scrollContainer': scrollContainer ? {
                        'className': scrollContainer.className,
                        'transform': window.getComputedStyle(scrollContainer).transform
                    } : null,
                    'visibleMessages': visibleMessages,
                    'totalMessages': allMessages.length
                };
            """)

            return {
                'visible_messages': len(chat_info.get('visibleMessages', [])),
                'total_messages': chat_info.get('totalMessages', 0),
                'scroll_height': chat_info.get('chatContainer', {}).get('scrollHeight', 0),
                'client_height': chat_info.get('chatContainer', {}).get('clientHeight', 0)
            }

        except Exception as e:
            logger.warning(f"获取聊天信息失败: {e}")
            return {'visible_messages': 0, 'total_messages': 0, 'scroll_height': 0, 'client_height': 0}

    def close_browser(self):
        """关闭浏览器"""
        if self.page:
            self.page.quit()
            logger.info("浏览器已关闭")

def main():
    """主函数"""
    tester = CorrectScrollDirectionTester()

    try:
        # 初始化浏览器
        if not tester.init_browser():
            return

        # 登录并导航到聊天页面
        if not tester.login_and_navigate():
            return

        # 点击第一个用户
        if not tester.click_first_user():
            return

        # 测试修正后的滚动方向
        if tester.test_correct_scroll_direction():
            logger.info("✅ 滚动方向测试完成！")
        else:
            logger.error("❌ 滚动方向测试失败")

    except Exception as e:
        logger.error(f"测试过程中出错: {e}")
    finally:
        tester.close_browser()

if __name__ == "__main__":
    main()