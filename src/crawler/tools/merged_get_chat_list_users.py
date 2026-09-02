#!/usr/bin/env python3
"""
合并版获取消息列表中的用户名工具
结合了精确用户识别和正确滚动功能
"""

import os
import json
import time
import csv
from datetime import datetime
from typing import List, Dict, Optional
from loguru import logger

from DrissionPage import ChromiumPage, ChromiumOptions


class MergedChatListUserExtractor:
    """合并版聊天列表用户提取器"""

    def __init__(self, headless: bool = False):
        """
        初始化提取器

        Args:
            headless: 是否使用无头模式
        """
        self.headless = headless
        self.page = None
        self.is_logged_in = False

    def init_browser(self):
        """初始化浏览器"""
        try:
            options = ChromiumOptions()
            if self.headless:
                options.headless()

            # 设置用户代理
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

    def _load_cookies_from_env(self) -> Optional[str]:
        """从.env文件加载cookies"""
        try:
            env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
            if os.path.exists(env_path):
                with open(env_path, 'r', encoding='utf-8') as f:
                    for line in f:
                        if line.startswith('COOKIES_STR='):
                            return line[len('COOKIES_STR='):].strip()
        except Exception as e:
            logger.warning(f"加载cookies失败: {e}")
        return None

    def login_and_navigate(self):
        """登录并导航到聊天页面"""
        try:
            # 导航到闲鱼聊天页面
            logger.info("正在打开闲鱼聊天页面...")
            self.page.get("https://www.goofish.com/im?spm=a21ybx.account.sidebar.2.6a3035ca2iyGly")

            # 等待页面加载
            self.page.wait.load_start()
            time.sleep(3)

            # 检查是否已登录
            current_url = self.page.url
            logger.info(f"当前页面URL: {current_url}")

            if "login" in current_url or "signin" in current_url:
                logger.info("检测到需要登录，请手动完成登录操作...")
                print("请手动完成闲鱼登录操作，登录完成后按回车键继续...")
                input()
                logger.info("登录完成，继续执行...")

            # 等待聊天页面完全加载
            self._wait_for_chat_page_loaded()
            self.is_logged_in = True
            logger.info("成功进入闲鱼聊天页面")
            return True

        except Exception as e:
            logger.error(f"登录和导航失败: {e}")
            return False

    def _wait_for_chat_page_loaded(self):
        """等待聊天页面加载完成"""
        max_wait = 60
        start_time = time.time()

        while time.time() - start_time < max_wait:
            # 基于闲鱼实际页面结构的选择器
            chat_list_selectors = [
                '.rc-virtual-list-holder',       # 实际滚动容器
                '.conversation-list--jDBLEMex',  # 聊天列表
                '.conversation-item--JReyg97P',  # 聊天项目
                '.chat-container--gftCko_u',     # 聊天容器
                '.chat-main--xvquhxw1',          # 聊天主区域
                '.im-main--kaKv06s8',            # IM主区域
                '.conv-list-scroll--Bn4G27Nb',   # 聊天列表滚动区域
                '.rc-virtual-list',              # 虚拟列表
                '.user-order-container--gPgL3Azx', # 用户订单容器
                '.J_List',
                '.J_ChatList',
                '.chat-list',
                '.message-list',
                '.conversation-list',
                '.list',
                '.im-list',
                '[class*="chat"]',
                '[class*="message"]',
                '[class*="conversation"]',
                '[class*="list"]',
                '[class*="im"]',
                'div[role="list"]',
                'ul[class*="list"]',
                'div[class*="list"]'
            ]

            for selector in chat_list_selectors:
                try:
                    element = self.page.ele(selector, timeout=3)
                    if element:
                        logger.info(f"找到聊天列表元素: {selector}")
                        # 检查元素是否包含用户列表
                        if element.eles('text=.*'):
                            logger.info("聊天页面加载完成")
                            return True
                except Exception as e:
                    logger.debug(f"选择器 {selector} 查找失败: {e}")
                    continue

            # 检查是否有任何用户相关的元素
            user_elements = self.page.eles('[class*="user"]')
            if user_elements:
                logger.info("找到用户相关元素，聊天页面可能已加载")
                return True

            # 检查是否有任何包含文本的元素（可能是用户昵称）
            text_elements = self.page.eles('text=.+')
            if len(text_elements) > 5:  # 如果有多个文本元素，可能页面已加载
                logger.info("找到多个文本元素，聊天页面可能已加载")
                return True

            # 检查页面标题或URL是否表明已在聊天页面
            current_url = self.page.url
            current_title = self.page.title
            if "im" in current_url or "chat" in current_url or "闲鱼" in current_title:
                logger.info("URL或标题表明已在聊天页面，继续执行")
                return True

            time.sleep(2)

        logger.warning("聊天页面加载超时，继续执行...")
        return True

    def extract_user_nicknames(self, max_users: int = 20) -> List[str]:
        """
        提取聊天列表中的用户昵称 - 结合精确识别和正确滚动

        Args:
            max_users: 最大用户数量，设置为0表示查找所有用户

        Returns:
            List[str]: 用户昵称列表
        """
        if not self.is_logged_in:
            logger.error("请先登录并导航到聊天页面")
            return []

        logger.info(f"开始提取聊天列表中的前 {max_users} 个用户昵称...")

        try:
            # 基于闲鱼实际页面结构的选择器
            chat_list_selectors = [
                '.rc-virtual-list-holder',
                '.conversation-list--jDBLEMex',
                '.conversation-item--JReyg97P',
                '.chat-container--gftCko_u',
                '.chat-main--xvquhxw1',
                '.im-main--kaKv06s8',
                '.conv-list-scroll--Bn4G27Nb',
                '.rc-virtual-list',
                '.user-order-container--gPgL3Azx',
                '.J_List',
                '.J_ChatList',
                '.chat-list',
                '.message-list',
                '.conversation-list',
                '.list',
                '.im-list',
                '[class*="chat"]',
                '[class*="message"]',
                '[class*="conversation"]',
                '[class*="list"]',
                '[class*="im"]'
            ]

            chat_list = None
            for selector in chat_list_selectors:
                chat_list = self.page.ele(selector, timeout=3)
                if chat_list:
                    logger.info(f"找到聊天列表: {selector}")
                    break

            if not chat_list:
                logger.warning("未找到聊天列表")
                return []

            user_nicknames = []
            max_scroll_attempts = 20
            scroll_height = 300
            last_scroll_position = 0

            for attempt in range(max_scroll_attempts):
                logger.info(f"第 {attempt + 1} 次滚动查找用户...")

                # 使用JavaScript基于精确的HTML元素结构获取用户昵称 - 纯HTML元素方法
                chat_users = self.page.run_js("""
                    function getDirectUsers() {
                        const users = [];

                        // 基于精确的HTML结构查找真正的用户昵称
                        // 完全基于HTML元素样式特征，不依赖文本内容过滤

                        // 方法1：查找具有精确样式的用户昵称元素
                        // 这是真正的用户昵称元素的精确特征
                        const exactUserDivs = document.querySelectorAll('div[style*="max-width: 176px"][style*="font-weight: 500"][style*="color: rgb(51, 51, 51)"]');

                        // 方法2：查找父元素具有特定结构的用户昵称
                        const parentUserDivs = document.querySelectorAll('div[style*="font-weight: 500; font-size: 14px; color: rgb(51, 51, 51); line-height: 1.28571; display: flex; align-items: center; width: 180px; cursor: pointer;"] > div[style*="overflow: hidden"][style*="text-overflow: ellipsis"][style*="white-space: nowrap"][style*="max-width"]');

                        // 方法3：查找具有用户昵称典型样式的元素
                        const userStyleDivs = document.querySelectorAll('div[style*="overflow: hidden"][style*="text-overflow: ellipsis"][style*="white-space: nowrap"][style*="max-width: 176px"]');

                        // 合并所有找到的元素
                        const allElements = [...exactUserDivs, ...parentUserDivs, ...userStyleDivs];

                        // 调试：显示找到的所有元素
                        console.log('找到的元素数量:', allElements.length);
                        for (let i = 0; i < allElements.length; i++) {
                            const div = allElements[i];
                            const text = div.textContent.trim();
                            const style = div.getAttribute('style');
                            console.log(`元素 ${i}: "${text}" (样式: ${style})`);
                        }

                        // 基于HTML元素特征获取用户昵称，并过滤系统消息
                        for (const div of allElements) {
                            const text = div.textContent.trim();

                            // 检查基本的文本有效性
                            if (text && text.length >= 1 && text.length <= 30) {
                                // 过滤系统消息
                                const systemKeywords = ['通知', '系统', '客服', '官方', '消息', '公告', '提醒', '提示'];
                                const isSystemMessage = systemKeywords.some(keyword => text.includes(keyword));

                                if (!isSystemMessage && !users.includes(text)) {
                                    users.push(text);
                                }
                            }
                        }

                        return users.slice(0, arguments[0]);
                    }

                    return getDirectUsers(arguments[0]);
                """, max_users)

                if chat_users:
                    for nickname in chat_users:
                        if nickname and nickname not in user_nicknames:
                            user_nicknames.append(nickname)
                            logger.info(f"找到用户: {nickname}")

                # 如果已经找到足够的用户，停止滚动
                if len(user_nicknames) >= max_users:
                    logger.info(f"已找到 {len(user_nicknames)} 个用户，停止滚动")
                    break

                # 滚动聊天列表 - 使用正确的滚动方法
                try:
                    if chat_list != self.page:
                        try:
                            self.page.run_js("arguments[0].scrollBy(0, arguments[1])", chat_list, scroll_height)
                        except:
                            self.page.scroll.down(scroll_height)
                    else:
                        self.page.scroll.down(scroll_height)
                except Exception as scroll_error:
                    logger.warning(f"滚动失败: {scroll_error}")

                time.sleep(1.5)

                # 检查是否已经滚动到底部
                current_scroll = self.page.run_js("return arguments[0].scrollTop", chat_list) if chat_list != self.page else self.page.run_js("return window.pageYOffset")
                if current_scroll == last_scroll_position and attempt > 2:
                    logger.info("已滚动到底部，停止搜索")
                    break
                last_scroll_position = current_scroll

            # 过滤掉当前用户自己的账号
            user_nicknames = self._filter_own_account(user_nicknames)

            # 限制用户数量
            user_nicknames = user_nicknames[:max_users]

            logger.info(f"从聊天列表中找到 {len(user_nicknames)} 个用户")
            return user_nicknames

        except Exception as e:
            logger.error(f"提取用户昵称时出错: {e}")
            return []

    def _filter_own_account(self, user_nicknames: List[str]) -> List[str]:
        """过滤掉当前用户自己的账号"""
        try:
            # 使用多种方法获取当前登录用户的昵称
            current_user = self.page.run_js("""
                function getCurrentUser() {
                    // 方法1：查找页面顶部或侧边栏的用户信息
                    const headerUserElements = document.querySelectorAll('[class*="account"], [class*="user"], [class*="nick"], [class*="name"]');
                    for (const element of headerUserElements) {
                        const text = element.textContent.trim();
                        if (text && text.length > 1 && text.length < 30) {
                            // 检查元素位置 - 通常在页面顶部或侧边栏
                            const rect = element.getBoundingClientRect();
                            if (rect.top < 100 || rect.left < 100) {
                                return text;
                            }
                        }
                    }

                    // 方法2：查找页面标题或meta信息中的用户信息
                    const title = document.title;
                    if (title && title.includes('闲鱼')) {
                        // 尝试从标题中提取用户名
                        const match = title.match(/(.+?)的闲鱼/);
                        if (match && match[1]) {
                            return match[1];
                        }
                    }

                    // 方法3：查找用户头像旁边的文本
                    const avatarElements = document.querySelectorAll('[class*="avatar"], [class*="head"], img[src*="avatar"], img[src*="head"], img[alt*="头像"]');
                    for (const avatar of avatarElements) {
                        // 查找头像旁边的文本元素
                        const parent = avatar.parentElement;
                        if (parent) {
                            const siblings = Array.from(parent.children).filter(child => child !== avatar);
                            for (const sibling of siblings) {
                                const text = sibling.textContent.trim();
                                if (text && text.length > 1 && text.length < 30) {
                                    return text;
                                }
                            }
                        }
                    }

                    return null;
                }
                return getCurrentUser();
            """)

            if current_user and current_user in user_nicknames:
                logger.info(f"过滤掉当前用户账号: {current_user}")
                user_nicknames = [nickname for nickname in user_nicknames if nickname != current_user]

            # 额外过滤：排除与当前用户昵称相似的账号
            if current_user:
                filtered_nicknames = []
                for nickname in user_nicknames:
                    # 排除完全相同的昵称
                    if nickname == current_user:
                        continue
                    # 排除可能相关的昵称变体
                    if current_user in nickname or nickname in current_user:
                        logger.info(f"过滤掉可能相关的账号: {nickname}")
                        continue
                    filtered_nicknames.append(nickname)
                user_nicknames = filtered_nicknames

            return user_nicknames
        except Exception as e:
            logger.warning(f"获取当前用户信息失败: {e}")
            return user_nicknames

    def save_user_list(self, user_nicknames: List[str], output_file: str = "merged_chat_list_users.txt") -> bool:
        """
        保存用户列表到文件

        Args:
            user_nicknames: 用户昵称列表
            output_file: 输出文件路径

        Returns:
            bool: 是否保存成功
        """
        try:
            # 确保输出目录存在
            output_dir = os.path.dirname(output_file)
            if output_dir and not os.path.exists(output_dir):
                os.makedirs(output_dir, exist_ok=True)

            # 保存为文本文件
            with open(output_file, 'w', encoding='utf-8') as f:
                for nickname in user_nicknames:
                    f.write(f"{nickname}\n")

            logger.info(f"用户列表已保存到: {output_file}")

            # 同时保存为JSON格式
            json_file = output_file.replace('.txt', '.json')
            user_data = {
                'extract_time': datetime.now().isoformat(),
                'total_users': len(user_nicknames),
                'users': user_nicknames
            }
            with open(json_file, 'w', encoding='utf-8') as f:
                json.dump(user_data, f, ensure_ascii=False, indent=2)

            logger.info(f"用户数据JSON已保存到: {json_file}")
            return True

        except Exception as e:
            logger.error(f"保存用户列表失败: {e}")
            return False

    def close_browser(self):
        """关闭浏览器"""
        if self.page:
            self.page.quit()
            logger.info("浏览器已关闭")


def main():
    """命令行入口函数"""
    import argparse

    parser = argparse.ArgumentParser(description='合并版获取消息列表中的用户名工具')
    parser.add_argument('--max-users', type=int, default=0, help='最大用户数量（0表示交互式输入，默认：0）')
    parser.add_argument('--output-file', default='merged_chat_list_users.txt', help='输出文件路径（默认：merged_chat_list_users.txt）')
    parser.add_argument('--headless', action='store_true', help='使用无头模式')

    args = parser.parse_args()

    # 交互式输入用户数量
    if args.max_users == 0:
        try:
            user_input = input("请输入要获取的用户数量（默认10个）: ").strip()
            if user_input:
                args.max_users = int(user_input)
            else:
                args.max_users = 10
        except ValueError:
            print("输入无效，使用默认值10个用户")
            args.max_users = 10

    try:
        # 创建用户提取器
        extractor = MergedChatListUserExtractor(headless=args.headless)

        # 初始化浏览器
        print("正在初始化浏览器...")
        if not extractor.init_browser():
            print("浏览器初始化失败")
            return

        # 登录并导航到聊天页面
        print("正在登录并导航到闲鱼聊天页面...")
        if not extractor.login_and_navigate():
            print("登录和导航失败")
            return

        # 提取用户昵称
        print(f"正在提取聊天列表中的前 {args.max_users} 个用户昵称...")
        user_nicknames = extractor.extract_user_nicknames(max_users=args.max_users)

        if user_nicknames:
            print(f"\n成功提取 {len(user_nicknames)} 个用户昵称:")
            for i, nickname in enumerate(user_nicknames, 1):
                print(f"  {i}. {nickname}")

            # 保存用户列表
            print(f"\n正在保存用户列表到文件: {args.output_file}")
            if extractor.save_user_list(user_nicknames, args.output_file):
                print(f"用户列表保存成功！")
                print(f"   文本文件: {args.output_file}")
                print(f"   JSON文件: {args.output_file.replace('.txt', '.json')}")
            else:
                print("用户列表保存失败")
        else:
            print("未找到任何用户昵称")

    except Exception as e:
        print(f"程序执行失败: {e}")
    finally:
        # 关闭浏览器
        if 'extractor' in locals():
            extractor.close_browser()


if __name__ == '__main__':
    main()