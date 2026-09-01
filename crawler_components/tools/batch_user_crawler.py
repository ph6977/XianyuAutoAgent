#!/usr/bin/env python3
"""
批量用户聊天数据爬取工具 - 基于浏览器自动化一次性爬取多个用户的聊天记录
"""

import os
import json
import csv
import time
import re
from datetime import datetime
from typing import List, Dict, Optional
from loguru import logger

from DrissionPage import ChromiumPage, ChromiumOptions


class BatchUserCrawler:
    """基于浏览器自动化的批量用户聊天数据爬取器"""

    def __init__(self, headless: bool = False):
        """
        初始化爬取器

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
                # 设置初始URL和cookies
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
        max_wait = 60  # 增加等待时间
        start_time = time.time()

        while time.time() - start_time < max_wait:
            # 基于闲鱼实际页面结构的选择器
            chat_list_selectors = [
                # 实际调试发现的class名称
                '.rc-virtual-list-holder',       # 实际滚动容器（调试发现）
                '.conversation-list--jDBLEMex',  # 聊天列表
                '.conversation-item--JReyg97P',  # 聊天项目
                '.chat-container--gftCko_u',     # 聊天容器
                '.chat-main--xvquhxw1',          # 聊天主区域
                '.im-main--kaKv06s8',            # IM主区域
                '.conv-list-scroll--Bn4G27Nb',   # 聊天列表滚动区域
                '.rc-virtual-list',              # 虚拟列表
                '.user-order-container--gPgL3Azx', # 用户订单容器
                # 闲鱼可能使用的选择器
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
                'div[role="list"]',  # 通用列表选择器
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

            time.sleep(2)  # 增加等待间隔

        logger.warning("聊天页面加载超时，继续执行...")
        return True  # 即使超时也继续执行，可能页面结构不同

    def crawl_multiple_users_by_nickname(self, user_nicknames: List[str], max_messages: int = 100,
                                       delay_between_users: float = 3.0, max_retries: int = 2) -> Dict[str, Optional[Dict]]:
        """
        基于昵称批量爬取多个用户的聊天记录 - 增强版本（带重试机制）

        Args:
            user_nicknames: 用户昵称列表
            max_messages: 每个用户的最大消息数量
            delay_between_users: 用户之间的延迟（秒）
            max_retries: 最大重试次数

        Returns:
            Dict: 用户昵称到聊天数据的映射
        """
        results = {}

        if not self.is_logged_in:
            logger.error("请先登录并导航到聊天页面")
            return results

        logger.info(f"开始批量爬取 {len(user_nicknames)} 个用户的聊天记录...")

        for i, nickname in enumerate(user_nicknames, 1):
            success = False
            retry_count = 0

            while retry_count <= max_retries and not success:
                try:
                    logger.info(f"正在爬取第 {i}/{len(user_nicknames)} 个用户: {nickname} (重试 {retry_count}/{max_retries})")

                    # 查找并点击用户（带重试）
                    if not self._find_and_click_user_with_retry(nickname, max_retries=2):
                        logger.warning(f"未找到用户: {nickname}")
                        results[nickname] = None
                        break

                    # 等待聊天页面加载
                    time.sleep(3)

                    # 获取聊天记录（带重试）
                    chat_data = self._get_chat_history_with_retry(max_messages, max_retries=1)
                    results[nickname] = chat_data

                    if chat_data:
                        logger.info(f"✅ 成功获取用户 {nickname} 的 {len(chat_data['messages'])} 条消息")
                        success = True
                    else:
                        logger.warning(f"⚠️  未能获取用户 {nickname} 的聊天记录")
                        if retry_count < max_retries:
                            logger.info(f"将在 {delay_between_users} 秒后重试...")
                            time.sleep(delay_between_users)
                        else:
                            results[nickname] = None
                            break

                except Exception as e:
                    logger.error(f"爬取用户 {nickname} 时出错: {e}")
                    if retry_count < max_retries:
                        logger.info(f"将在 {delay_between_users} 秒后重试...")
                        time.sleep(delay_between_users)
                    else:
                        results[nickname] = None
                        break

                retry_count += 1

            # 添加延迟，避免请求过于频繁
            if i < len(user_nicknames):
                logger.info(f"等待 {delay_between_users} 秒后继续下一个用户...")
                time.sleep(delay_between_users)

        successful_count = sum(1 for v in results.values() if v)
        logger.info(f"批量爬取完成，成功获取 {successful_count}/{len(user_nicknames)} 个用户的记录")

        # 生成详细报告
        self._generate_crawl_report(results)

        return results

    def _find_and_click_user_with_retry(self, nickname: str, max_retries: int = 2) -> bool:
        """带重试的用户查找和点击"""
        for attempt in range(max_retries + 1):
            try:
                if self._find_and_click_user(nickname):
                    return True
                elif attempt < max_retries:
                    logger.info(f"第{attempt + 1}次查找用户失败，将在1秒后重试...")
                    time.sleep(1)
            except Exception as e:
                logger.warning(f"查找用户 {nickname} 时出错 (尝试 {attempt + 1}): {e}")
                if attempt < max_retries:
                    time.sleep(2)

        return False

    def _get_chat_history_with_retry(self, max_messages: int = 100, max_retries: int = 1) -> Optional[Dict]:
        """带重试的聊天记录获取"""
        for attempt in range(max_retries + 1):
            try:
                chat_data = self._get_chat_history(max_messages)
                if chat_data and chat_data.get('messages'):
                    return chat_data
                elif attempt < max_retries:
                    logger.info(f"第{attempt + 1}次获取聊天记录失败，将在2秒后重试...")
                    time.sleep(2)
            except Exception as e:
                logger.warning(f"获取聊天记录时出错 (尝试 {attempt + 1}): {e}")
                if attempt < max_retries:
                    time.sleep(3)

        return None

    def _generate_crawl_report(self, results: Dict[str, Optional[Dict]]):
        """生成爬取报告"""
        successful_users = [nickname for nickname, data in results.items() if data]
        failed_users = [nickname for nickname, data in results.items() if not data]

        total_messages = sum(len(data['messages']) for data in results.values() if data)

        logger.info(f"\n=== 爬取报告 ===")
        logger.info(f"总用户数: {len(results)}")
        logger.info(f"成功用户: {len(successful_users)}")
        logger.info(f"失败用户: {len(failed_users)}")
        logger.info(f"总消息数: {total_messages}")

        if successful_users:
            logger.info(f"成功用户列表: {successful_users}")

        if failed_users:
            logger.info(f"失败用户列表: {failed_users}")

    def crawl_chat_list_users(self, max_users: int = 10, max_messages: int = 100,
                            delay_between_users: float = 3.0) -> Dict[str, Optional[Dict]]:
        """
        自动爬取聊天列表中的用户聊天记录

        Args:
            max_users: 最大爬取用户数量
            max_messages: 每个用户的最大消息数量
            delay_between_users: 用户之间的延迟（秒）

        Returns:
            Dict: 用户昵称到聊天数据的映射
        """
        results = {}

        if not self.is_logged_in:
            logger.error("请先登录并导航到聊天页面")
            return results

        logger.info(f"开始自动爬取聊天列表中的前 {max_users} 个用户...")

        # 获取聊天列表中的用户
        user_nicknames = self._get_chat_list_users(max_users)

        if not user_nicknames:
            # 如果通过正常方法未找到用户，尝试从最近的临时文件中加载
            import glob
            import json
            import os
            
            # 查找最近的临时用户文件
            temp_files = glob.glob("temp_users_*.json")
            if temp_files:
                # 按修改时间排序，获取最新的文件
                temp_files.sort(key=os.path.getmtime, reverse=True)
                latest_temp_file = temp_files[0]
                
                logger.info(f"从临时文件中加载用户昵称: {latest_temp_file}")
                try:
                    with open(latest_temp_file, 'r', encoding='utf-8') as f:
                        user_nicknames = json.load(f)
                    # 限制用户数量
                    user_nicknames = user_nicknames[:max_users]
                    logger.info(f"从临时文件中加载了 {len(user_nicknames)} 个用户")
                except Exception as e:
                    logger.error(f"从临时文件加载用户昵称失败: {e}")
                    return results
            else:
                logger.warning("未在聊天列表中找到任何用户，且没有可用的临时文件")
                return results

        # 刷新页面以确保用户列表回到顶部
        logger.info("刷新页面以确保用户列表回到顶部...")
        self.page.refresh()
        time.sleep(5)  # 等待页面刷新完成
        
        # 等待聊天列表重新加载
        success = self._wait_for_chat_page_loaded()
        if not success:
            logger.warning("页面刷新后未能重新加载聊天列表")
            return {}

        logger.info(f"开始爬取 {len(user_nicknames)} 个用户的消息: {user_nicknames}")

        for i, nickname in enumerate(user_nicknames, 1):
            try:
                logger.info(f"正在爬取第 {i}/{len(user_nicknames)} 个用户: {nickname}")

                # 点击用户进入聊天页面
                if not self._click_user_in_chat_list(nickname):
                    logger.warning(f"无法点击用户: {nickname}")
                    results[nickname] = None
                    continue

                # 等待聊天页面加载
                time.sleep(2)

                # 获取聊天记录
                chat_data = self._get_chat_history(max_messages)
                results[nickname] = chat_data

                if chat_data:
                    logger.info(f"成功获取用户 {nickname} 的 {len(chat_data['messages'])} 条消息")
                else:
                    logger.warning(f"未能获取用户 {nickname} 的聊天记录")

                # 添加延迟，避免请求过于频繁
                if i < len(user_nicknames):
                    logger.info(f"等待 {delay_between_users} 秒后继续...")
                    time.sleep(delay_between_users)

            except Exception as e:
                logger.error(f"爬取用户 {nickname} 时出错: {e}")
                results[nickname] = None

        logger.info(f"自动爬取完成，成功获取 {sum(1 for v in results.values() if v)}/{len(user_nicknames)} 个用户的记录")
        return results

    def _get_chat_list_users(self, max_users: int = 10) -> List[str]:
        """
        获取聊天列表中的用户昵称

        Args:
            max_users: 最大用户数量

        Returns:
            List[str]: 用户昵称列表
        """
        try:
            logger.info(f"正在获取聊天列表中的前 {max_users} 个用户...")

            # 使用JavaScript在页面中查找具有特定样式的用户昵称元素
            # 根据页面实际结构，用户昵称通常在具有特定CSS样式的div元素中
            user_nicknames = []
            
            # 等待页面完全稳定
            time.sleep(5)

            # 使用JavaScript直接查找具有特定样式的用户昵称元素
            js_code = """
            var userElements = [];
            
            // 首先在聊天列表容器中查找用户昵称元素
            var virtualList = document.querySelector('.rc-virtual-list-holder');
            if (virtualList) {
                // 在每个会话项中查找用户昵称元素
                // 用户昵称元素通常具有这样的样式：overflow: hidden; text-overflow: ellipsis; white-space: nowrap; max-width: 176px;
                var items = virtualList.querySelectorAll('.conversation-item--JReyg97P');
                for (var i = 0; i < items.length; i++) {
                    var item = items[i];
                    
                    // 在每个会话项中查找用户昵称元素 - 精确查找具有特定样式的div
                    var nameElements = item.querySelectorAll('div');
                    for (var j = 0; j < nameElements.length; j++) {
                        var nameElement = nameElements[j];
                        var style = window.getComputedStyle(nameElement);
                        
                        // 检查元素是否具有用户昵称的典型样式
                        if (style.overflow === 'hidden' && 
                            style.textOverflow === 'ellipsis' && 
                            style.whiteSpace === 'nowrap' && 
                            style.maxWidth && 
                            (style.maxWidth.includes('176px') || style.maxWidth.includes('180px'))) {
                            
                            var text = nameElement.textContent.trim();
                            
                            // 确保文本不是空的，且长度合理
                            if (text && text.length > 1 && text.length < 30 && !userElements.includes(text)) {
                                // 检查是否包含明显的非昵称词汇
                                var excludePattern = /(券|发货|收货|价格|最优|品质|保证|物超所值|等待|记得|确认|系统|官方|客服|通知|消息)/i;
                                
                                // 检查是否包含用户昵称的特征（中文、英文字母、数字、下划线、特殊符号）
                                var nicknamePattern = /[a-zA-Z0-9_\u4e00-\u9fa5]/;
                                
                                if (nicknamePattern.test(text) && !excludePattern.test(text)) {
                                    userElements.push(text);
                                }
                            }
                        }
                    }
                }
            }
            
            // 如果上面的方法没有找到足够的用户，再尝试更宽松的查找方法
            if (userElements.length < 5) {
                // 查找具有特定CSS样式的div元素，这些通常是用户昵称
                var allDivs = document.querySelectorAll('div');
                for (var i = 0; i < allDivs.length; i++) {
                    var element = allDivs[i];
                    var style = window.getComputedStyle(element);
                    
                    // 检查元素是否具有用户昵称的典型样式
                    if (style.overflow === 'hidden' && 
                        style.textOverflow === 'ellipsis' && 
                        style.whiteSpace === 'nowrap') {
                        
                        var text = element.textContent.trim();
                        
                        // 确保文本不是空的，且长度合理
                        if (text && text.length > 1 && text.length < 30 && !userElements.includes(text)) {
                            // 检查是否包含明显的非昵称词汇
                            var excludePattern = /(券|发货|收货|价格|最优|品质|保证|物超所值|等待|记得|确认|系统|官方|客服|通知|消息)/i;
                            
                            // 检查是否包含用户昵称的特征（中文、英文字母、数字、下划线、特殊符号）
                            var nicknamePattern = /[a-zA-Z0-9_\u4e00-\u9fa5]/;
                            
                            if (nicknamePattern.test(text) && !excludePattern.test(text)) {
                                userElements.push(text);
                            }
                        }
                    }
                }
            }
            
            return userElements;
            """
            
            # 执行JavaScript查找用户昵称
            found_users = self.page.run_js(js_code)
            if found_users:
                user_nicknames = [user for user in found_users if user not in user_nicknames]
                logger.info(f"通过JavaScript找到 {len(user_nicknames)} 个用户: {user_nicknames[:max_users]}")
            
            # 如果JavaScript方式没有找到用户，尝试滚动加载更多
            if len(user_nicknames) < max_users:
                logger.info(f"当前找到 {len(user_nicknames)} 个用户，尝试滚动加载更多...")
                
                max_scroll_attempts = 10
                scroll_height = 400
                
                for attempt in range(max_scroll_attempts):
                    if len(user_nicknames) >= max_users:
                        break
                        
                    logger.info(f"第 {attempt + 1} 次滚动查找用户...")
                    
                    # 滚动到当前聊天列表底部
                    try:
                        # 使用JavaScript滚动
                        scroll_result = self.page.run_js("""
                            var scrollContainer = document.querySelector('.rc-virtual-list-holder') || 
                                                 document.querySelector('.conv-list-scroll--Bn4G27Nb') ||
                                                 document.querySelector('.im-main--kaKv06s8');
                            
                            if (scrollContainer) {
                                scrollContainer.scrollBy(0, arguments[0]);
                                return true;
                            }
                            return false;
                        """, scroll_height)
                        
                        if not scroll_result:
                            # 如果特定容器滚动失败，尝试页面滚动
                            self.page.scroll.down(scroll_height)
                            
                    except Exception as scroll_error:
                        logger.warning(f"滚动失败: {scroll_error}")
                    
                    # 等待新内容加载
                    time.sleep(4)
                    
                    # 再次执行JavaScript查找
                    found_users = self.page.run_js(js_code)
                    if found_users:
                        for user in found_users:
                            if user not in user_nicknames and len(user_nicknames) < max_users:
                                user_nicknames.append(user)
                                logger.info(f"滚动后找到用户: '{user}'")
                    
                    if len(user_nicknames) >= max_users:
                        break

            # 限制用户数量
            user_nicknames = user_nicknames[:max_users]

            logger.info(f"从聊天列表中找到 {len(user_nicknames)} 个用户: {user_nicknames}")
            
            # 将用户昵称保存到临时文件
            if user_nicknames:
                import json
                import os
                from datetime import datetime
                
                # 创建临时文件保存用户昵称
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                temp_file_path = os.path.join(os.getcwd(), f"temp_users_{timestamp}.json")
                
                with open(temp_file_path, 'w', encoding='utf-8') as f:
                    json.dump(user_nicknames, f, ensure_ascii=False, indent=2)
                
                logger.info(f"用户昵称已保存到临时文件: {temp_file_path}")
            
            return user_nicknames

        except Exception as e:
            logger.error(f"获取聊天列表用户时出错: {e}")
            import traceback
            traceback.print_exc()
            return []

            def _click_user_in_chat_list(self, nickname: str) -> bool:




                """

                在聊天列表中点击指定用户

        

                Args:

                    nickname: 用户昵称

        

                Returns:

                    bool: 是否成功点击用户

                """

                try:

                    logger.info(f"正在点击用户: {nickname}")

        

                    # 基于闲鱼实际页面结构的选择器 - 优化版本

                    chat_list_selectors = [

                        '.rc-virtual-list-holder',       # 实际滚动容器（调试发现）

                        '.conversation-list--jDBLEMex',  # 聊天列表

                        '.conversation-item--JReyg97P',  # 聊天项目（用户按钮容器）

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

                        return False

        

                    # 基于用户提供的HTML结构查找具有特定样式的用户昵称元素

                    # 查找具有特定CSS样式的div元素，这些通常是用户昵称

                    js_code = f"""

                    var targetElement = null;

                    var virtualList = document.querySelector('.rc-virtual-list-holder');

                    if (virtualList) {{

                        // 在每个会话项中查找用户昵称元素 - 精确查找具有特定样式的div

                        var items = virtualList.querySelectorAll('.conversation-item--JReyg97P');

                        for (var i = 0; i < items.length; i++) {{

                            var item = items[i];

                            

                            // 在每个会话项中查找用户昵称元素 - 精确查找具有特定样式的div

                            var nameElements = item.querySelectorAll('div');

                            for (var j = 0; j < nameElements.length; j++) {{

                                var nameElement = nameElements[j];

                                var text = nameElement.textContent.trim();

                                if (text === '{nickname}') {{

                                    targetElement = nameElement;

                                    break;

                                }}

                            }}

                            if (targetElement) break;

                        }}

                    }}

                    

                    return targetElement;

                    """

        

                    # 首先尝试直接查找用户

                    found_element = self.page.run_js(js_code)

                    if found_element:

                        try:

                            # 尝试直接点击找到的元素

                            self.page.run_js("arguments[0].click();", found_element)

                            time.sleep(2)

                            logger.info(f"成功点击用户: {nickname}")

                            return True

                        except Exception as click_error:

                            logger.warning(f"直接点击用户失败: {click_error}")

        

                    # 如果直接查找失败，尝试滚动查找

                    max_scroll_attempts = 20  # 增加滚动次数以确保找到用户

                    scroll_height = 400

                    no_new_elements_count = 0

                    previous_element_count = 0

        

                    for attempt in range(max_scroll_attempts):

                        logger.info(f"第 {attempt + 1} 次滚动查找用户 {nickname}...")

        

                        # 尝试使用JavaScript滚动

                        scroll_result = self.page.run_js("""

                            var scrollContainer = document.querySelector('.rc-virtual-list-holder') || 

                                                 document.querySelector('.conv-list-scroll--Bn4G27Nb') ||

                                                 document.querySelector('.im-main--kaKv06s8');

        

                            if (scrollContainer) {

                                scrollContainer.scrollBy(0, arguments[0]);

                                return true;

                            }

                            return false;

                        """, scroll_height)

        

                        if not scroll_result:

                            # 如果特定容器滚动失败，尝试页面滚动

                            self.page.scroll.down(scroll_height)

        

                        # 等待新内容加载

                        time.sleep(3)

        

                        # 再次尝试查找用户

                        found_element = self.page.run_js(js_code)

                        if found_element:

                            try:

                                # 尝试点击找到的元素

                                self.page.run_js("arguments[0].click();", found_element)

                                time.sleep(2)

                                logger.info(f"成功点击用户: {nickname}")

                                return True

                            except Exception as click_error:

                                logger.warning(f"滚动后点击用户失败: {click_error}")

        

                        # 检查是否滚动到底部（没有找到新元素）

                        current_elements = self.page.run_js("""

                            var count = 0;

                            var virtualList = document.querySelector('.rc-virtual-list-holder');

                            if (virtualList) {

                                var items = virtualList.querySelectorAll('.conversation-item--JReyg97P');

                                count = items.length;

                            }

                            return count;

                        """)

        

                        if current_elements == previous_element_count:

                            no_new_elements_count += 1

                            if no_new_elements_count >= 3:  # 连续3次没有新元素则认为已滚动到底

                                logger.info("已滚动到底部，未找到指定用户")

                                break

                        else:

                            no_new_elements_count = 0  # 重置计数器

        

                        previous_element_count = current_elements

        

                    logger.warning(f"在聊天列表中未找到可点击的用户: {nickname}")

                    return False

        

                except Exception as e:

                    logger.error(f"点击用户 {nickname} 时出错: {e}")

                    return False

    def _find_and_click_user(self, nickname: str) -> bool:
        """
        在聊天列表中查找并点击用户

        Args:
            nickname: 用户昵称

        Returns:
            bool: 是否成功找到并点击用户
        """
        try:
            logger.info(f"正在查找用户: {nickname}")

            # 基于闲鱼实际页面结构的选择器
            chat_list_selectors = [
                # 实际调试发现的class名称
                '.rc-virtual-list-holder',       # 实际滚动容器（调试发现）
                '.conversation-list--jDBLEMex',  # 聊天列表
                '.conversation-item--JReyg97P',  # 聊天项目
                '.chat-container--gftCko_u',     # 聊天容器
                '.chat-main--xvquhxw1',          # 聊天主区域
                '.im-main--kaKv06s8',            # IM主区域
                '.conv-list-scroll--Bn4G27Nb',   # 聊天列表滚动区域
                '.rc-virtual-list',              # 虚拟列表
                '.user-order-container--gPgL3Azx', # 用户订单容器
                # 闲鱼可能使用的选择器
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
                logger.warning("未找到聊天列表，尝试在整个页面中查找")
                # 如果在特定容器中找不到，尝试在整个页面中查找
                chat_list = self.page

            # 滚动查找用户
            max_scroll_attempts = 15
            scroll_height = 500
            last_scroll_position = 0

            for attempt in range(max_scroll_attempts):
                # 查找包含用户昵称的元素 - 使用更灵活的搜索
                user_elements = []

                # 尝试多种搜索方式
                search_patterns = [
                    f'text={nickname}',
                    f'text=.*{nickname}.*',
                    f'[title*="{nickname}"]',
                    f'[alt*="{nickname}"]'
                ]

                for pattern in search_patterns:
                    elements = chat_list.eles(pattern)
                    if elements:
                        user_elements.extend(elements)
                        logger.info(f"使用模式 '{pattern}' 找到 {len(elements)} 个匹配元素")

                if user_elements:
                    # 找到用户，点击进入聊天
                    logger.info(f"找到用户: {nickname}")
                    # 选择第一个可点击的元素
                    for element in user_elements:
                        try:
                            element.click()
                            time.sleep(2)
                            logger.info(f"成功点击用户: {nickname}")
                            return True
                        except Exception as click_error:
                            logger.warning(f"点击元素失败，尝试下一个: {click_error}")
                            continue

                # 如果没有找到，滚动聊天列表
                logger.info(f"未找到用户 {nickname}，尝试滚动聊天列表 (第{attempt + 1}次)")

                # 尝试多种滚动方式
                scroll_success = False

                try:
                    # 首先尝试使用DrissionPage的内置滚动方法
                    if chat_list != self.page:
                        # 如果chat_list是特定元素，尝试滚动该元素
                        try:
                            self.page.run_js("arguments[0].scrollBy(0, arguments[1])", chat_list, scroll_height)
                            scroll_success = True
                        except:
                            # 如果元素滚动失败，尝试页面滚动
                            self.page.scroll.down(scroll_height)
                            scroll_success = True
                    else:
                        # 如果是整个页面，使用页面滚动
                        self.page.scroll.down(scroll_height)
                        scroll_success = True
                except Exception as scroll_error:
                    logger.warning(f"滚动失败: {scroll_error}")
                    # 如果所有方法都失败，使用键盘滚动作为备用
                    try:
                        self.page.scroll.down(scroll_height)
                        scroll_success = True
                    except:
                        logger.error("所有滚动方法都失败")

                time.sleep(1.5)

                # 检查是否已经滚动到底部
                current_scroll = self.page.run_js("return arguments[0].scrollTop", chat_list) if chat_list != self.page else self.page.run_js("return window.pageYOffset")
                if current_scroll == last_scroll_position and attempt > 2:
                    logger.info("已滚动到底部，停止搜索")
                    break
                last_scroll_position = current_scroll

            logger.warning(f"在聊天列表中未找到用户: {nickname}")
            return False

        except Exception as e:
            logger.error(f"查找用户 {nickname} 时出错: {e}")
            return False

    def _get_chat_history(self, max_messages: int = 100) -> Optional[Dict]:
        """
        获取当前聊天页面的历史消息

        Args:
            max_messages: 最大消息数量

        Returns:
            Dict: 聊天数据
        """
        try:
            # 等待聊天消息区域加载
            logger.info("等待聊天消息区域加载...")
            time.sleep(3)

            # 尝试多种选择器来定位消息区域 - 基于实际闲鱼页面结构
            message_area_selectors = [
                '.message-list-reverse--P5t12NwJ',  # 实际消息列表容器
                '.scroll-container--WObNWx73',       # 滚动容器
                '.message-area',
                '.chat-area',
                '.message-list',
                '.chat-list',
                '.im-area',
                '.im-message',
                '[class*="message"]',
                '[class*="chat"]',
                '[class*="im"]',
                '.J_MessageList',
                '.J_ChatArea'
            ]

            message_area = None
            for selector in message_area_selectors:
                message_area = self.page.ele(selector, timeout=3)
                if message_area:
                    logger.info(f"找到消息区域: {selector}")
                    break

            if not message_area:
                logger.warning("未找到消息区域，尝试在整个页面中查找消息")
                message_area = self.page

            # 滚动到顶部加载历史消息
            logger.info("正在加载历史消息...")
            self._scroll_to_load_history()

            # 获取消息元素
            message_data = self._get_message_elements()

            if not message_data:
                logger.warning("未找到任何消息")
                return None

            # 处理消息数据
            messages = []
            for i, msg in enumerate(message_data[:max_messages]):
                try:
                    # 如果是字典格式（来自JavaScript），直接使用
                    if isinstance(msg, dict):
                        message_data = {
                            'role': msg.get('role', 'unknown'),
                            'content': msg.get('text', ''),
                            'timestamp': msg.get('timestamp', time.time()),
                            'time_text': '',
                            'element_class': '',
                            'element_id': '',
                            'parsed_at': datetime.now().isoformat()
                        }
                    else:
                        # 如果是元素对象，使用原有解析方法
                        message_data = self._parse_message_element(msg)

                    if message_data:
                        messages.append(message_data)
                except Exception as e:
                    logger.warning(f"解析第 {i+1} 条消息时出错: {e}")

            # 尝试获取当前聊天用户的昵称
            current_user_nickname = self._get_current_chat_user_nickname()

            # 构建聊天数据
            chat_data = {
                'user_nickname': current_user_nickname,
                'messages': messages,
                'message_count': len(messages),
                'crawl_time': datetime.now().isoformat(),
                'source': 'browser_automation'
            }

            logger.info(f"成功解析 {len(messages)} 条消息")
            return chat_data

        except Exception as e:
            logger.error(f"获取聊天记录时出错: {e}")
            return None

    def _scroll_to_load_history(self):
        """滚动消息区域以加载历史消息 - 优化版本（智能滚动和等待）"""
        try:
            logger.info("开始智能滚动加载历史消息...")

            # 检查滚动容器是否存在
            scroll_container_check = self.page.run_js("""
                var scrollContainer = document.querySelector('.scroll-container--WObNWx73');
                if (!scrollContainer) {
                    return { error: '未找到滚动容器' };
                }

                // 获取容器信息
                var computedStyle = window.getComputedStyle(scrollContainer);
                var containerRect = scrollContainer.getBoundingClientRect();

                return {
                    exists: true,
                    transform: computedStyle.transform,
                    width: containerRect.width,
                    height: containerRect.height,
                    top: containerRect.top,
                    left: containerRect.left
                };
            """)

            if 'error' in scroll_container_check:
                logger.warning(f"滚动容器检查失败: {scroll_container_check['error']}")
                return

            logger.info(f"滚动容器信息: {scroll_container_check}")

            # 智能滚动策略：根据消息加载情况动态调整
            max_scroll_attempts = 15
            base_scroll_distance = 300
            total_scrolled = 0
            consecutive_no_new_messages = 0

            for attempt in range(max_scroll_attempts):
                # 获取滚动前的消息数量
                messages_before = self._get_message_count()

                logger.info(f"第{attempt + 1}次向上滚动，累计滚动: {total_scrolled}px")

                # 计算当前滚动距离（逐步增加）
                current_distance = base_scroll_distance + (attempt * 100)
                total_scrolled += current_distance

                scroll_result = self.page.run_js(f"""
                    var scrollContainer = document.querySelector('.scroll-container--WObNWx73');
                    if (!scrollContainer) {{
                        return '未找到滚动容器';
                    }}

                    var beforeTransform = window.getComputedStyle(scrollContainer).transform;

                    // 聊天页面：使用正值向上滚动（加载历史消息）
                    scrollContainer.style.transform = 'translateY({total_scrolled}px)';

                    // 触发滚动事件
                    var scrollEvent = new Event('scroll', {{ bubbles: true }});
                    scrollContainer.dispatchEvent(scrollEvent);

                    // 强制重绘
                    scrollContainer.offsetHeight;

                    var afterTransform = window.getComputedStyle(scrollContainer).transform;

                    return {{
                        'before': beforeTransform,
                        'after': afterTransform,
                        'distance': {total_scrolled}
                    }};
                """)

                logger.info(f"滚动结果: {scroll_result}")

                # 智能等待：根据消息加载情况调整等待时间
                wait_time = self._calculate_wait_time(attempt, messages_before)
                logger.info(f"等待 {wait_time} 秒让消息加载...")
                time.sleep(wait_time)

                # 获取滚动后的消息数量
                messages_after = self._get_message_count()

                # 检查是否加载了新消息
                if messages_after > messages_before:
                    logger.info(f"✅ 成功加载新消息: {messages_before} -> {messages_after}")
                    consecutive_no_new_messages = 0
                else:
                    logger.info(f"⚠️  未加载新消息，当前总数: {messages_after}")
                    consecutive_no_new_messages += 1

                # 检查是否已滚动到顶部
                if consecutive_no_new_messages >= 3:
                    logger.info("连续3次滚动未加载新消息，可能已到顶部，停止滚动")
                    break

                # 检查transform是否接近初始状态
                if attempt >= 5:
                    top_check = self.page.run_js("""
                        var scrollContainer = document.querySelector('.scroll-container--WObNWx73');
                        if (!scrollContainer) {
                            return { error: '未找到滚动容器' };
                        }

                        var computedStyle = window.getComputedStyle(scrollContainer);
                        var transform = computedStyle.transform;

                        // 检查transform值是否接近初始状态
                        return {
                            transform: transform,
                            is_near_top: transform === 'none' || transform.includes('matrix(1, 0, 0, 1, 0, 0)') || transform.includes('matrix(1, 0, 0, 1, 0, 0)')
                        };
                    """)

                    if top_check.get('is_near_top', False):
                        logger.info("检测到可能已滚动到顶部，停止滚动")
                        break

            logger.info(f"滚动加载完成，累计滚动: {total_scrolled}px")

        except Exception as e:
            logger.warning(f"滚动加载历史消息时出错: {e}")

    def _get_message_count(self) -> int:
        """获取当前可见消息数量"""
        try:
            count_info = self.page.run_js("""
                var messageElements = document.querySelectorAll('[class*="message"], [class*="msg"], [class*="chat"], [class*="im"]');
                return {
                    total_count: messageElements.length,
                    visible_count: Array.from(messageElements).filter(el => {
                        var rect = el.getBoundingClientRect();
                        return rect.top >= 0 && rect.bottom <= window.innerHeight;
                    }).length
                };
            """)
            return count_info.get('total_count', 0)
        except Exception as e:
            logger.warning(f"获取消息数量失败: {e}")
            return 0

    def _calculate_wait_time(self, attempt: int, messages_before: int) -> float:
        """根据滚动次数和消息数量计算等待时间 - 加速版本"""
        # 基础等待时间（大幅减少）
        base_wait = 1.0

        # 根据滚动次数调整：轻微增加
        attempt_factor = min(attempt * 0.2, 1.0)  # 最大增加1秒

        # 根据消息数量调整：轻微增加
        message_factor = min(messages_before / 100, 0.5)  # 每100条消息增加最多0.5秒

        total_wait = base_wait + attempt_factor + message_factor

        # 限制最大等待时间
        return min(total_wait, 2.5)

    def _get_message_elements(self) -> List:
        """获取消息元素列表 - 优化版本"""
        try:
            # 首先尝试在消息容器中查找
            message_container_selectors = [
                '.message-list-reverse--P5t12NwJ',
                '.scroll-container--WObNWx73',
                '[class*="message-list"]',
                '[class*="chat-area"]',
                '[class*="im-area"]'
            ]

            # 在特定容器中查找消息 - 加速版本
            for container_selector in message_container_selectors:
                container = self.page.ele(container_selector, timeout=1)  # 减少超时时间
                if container:
                    logger.info(f"找到消息容器: {container_selector}")

                    # 在容器内查找消息元素 - 优化版本
                    message_selectors = [
                        'span[style*="color: rgb(31, 31, 31)"]',  # 基于您提供的消息样式
                        'span[style*="font-size: 14px"]',
                        '[class*="message"]',
                        '[class*="msg"]',
                        '[class*="chat"]',
                        '[class*="im"]',
                        '.J_Message',
                        '.J_ChatMessage',
                        'div[role="listitem"]',  # 通用列表项选择器
                        'li[class*="message"]'
                    ]

                    for selector in message_selectors:
                        elements = container.eles(selector)
                        if elements:
                            logger.info(f"在容器中找到 {len(elements)} 个消息元素 (选择器: {selector})")

                            # 过滤有效的消息元素
                            valid_elements = []
                            for element in elements:
                                text = element.text.strip()
                                if text and len(text) > 1 and len(text) < 1000:
                                    # 排除系统消息和通知
                                    if not any(keyword in text.lower() for keyword in ['系统', '通知', '客服', '机器人']):
                                        valid_elements.append(element)

                            if valid_elements:
                                logger.info(f"过滤后得到 {len(valid_elements)} 个有效消息元素")
                                return valid_elements

            # 极速方法：直接使用JavaScript提取消息数据
            logger.info("使用极速JavaScript提取消息数据...")

            # 直接提取消息内容和类型，跳过元素查找
            messages_data = self.page.run_js("""
                // 极速消息提取 - 直接获取内容和判断类型
                var messages = [];

                // 查找所有可能包含消息的元素
                var selectors = [
                    'span[style*="color: rgb(31, 31, 31)"]',
                    'span[style*="font-size: 14px"]',
                    '[class*="message"]',
                    '[class*="msg"]',
                    '[class*="chat"]',
                    '[class*="im"]',
                    'div[role="listitem"]'
                ];

                for (var i = 0; i < selectors.length; i++) {
                    var elements = document.querySelectorAll(selectors[i]);
                    for (var j = 0; j < elements.length; j++) {
                        var element = elements[j];
                        var text = element.textContent.trim();

                        if (text && text.length > 1 && text.length < 1000) {
                            // 排除系统消息
                            if (!text.includes('系统') && !text.includes('通知') && !text.includes('客服')) {

                                // 判断消息类型
                                var role = 'unknown';
                                var className = element.className || '';

                                // 基于位置判断
                                var rect = element.getBoundingClientRect();
                                if (rect.left < window.innerWidth / 2) {
                                    role = 'buyer';  // 左侧通常是买家
                                } else {
                                    role = 'seller'; // 右侧通常是卖家
                                }

                                // 基于类名进一步判断
                                if (className.includes('buyer') || className.includes('left')) {
                                    role = 'buyer';
                                } else if (className.includes('seller') || className.includes('right')) {
                                    role = 'seller';
                                }

                                messages.push({
                                    'text': text,
                                    'role': role,
                                    'timestamp': Date.now() / 1000
                                });
                            }
                        }
                    }
                }

                // 返回前几个示例消息用于调试
                var sampleMessages = [];
                for (var k = 0; k < Math.min(messages.length, 5); k++) {
                    sampleMessages.push(messages[k].text.substring(0, 50));
                }

                return {
                    'messages': messages,
                    'sample_messages': sampleMessages,
                    'total_count': messages.length
                };
            """)

            if messages_data and messages_data.get('messages'):
                logger.info(f"通过极速JavaScript提取到 {messages_data['total_count']} 条消息")
                logger.info(f"示例消息: {messages_data['sample_messages']}")

                # 直接返回消息数据，跳过元素查找
                return messages_data['messages']

            logger.warning("未找到任何消息")
            return []

        except Exception as e:
            logger.error(f"获取消息元素时出错: {e}")
            return []

    def _get_current_chat_user_nickname(self) -> str:
        """获取当前聊天用户的昵称"""
        try:
            # 尝试多种选择器来获取当前聊天用户的昵称 - 基于实际闲鱼页面结构
            nickname_selectors = [
                '.chat-title',
                '.user-name',
                '.nickname',
                '.contact-name',
                '[class*="title"]',
                '[class*="name"]',
                '[class*="user"]',
                '.J_ChatTitle',
                '.J_UserName',
                # 闲鱼实际使用的选择器
                'div[style*="overflow: hidden; text-overflow: ellipsis; white-space: nowrap; max-width: 176px"]',
                'div[style*="overflow: hidden; text-overflow: ellipsis; white-space: nowrap; max-width: 102px"]'
            ]

            for selector in nickname_selectors:
                element = self.page.ele(selector, timeout=2)
                if element:
                    nickname = element.text.strip()
                    if nickname:
                        logger.info(f"找到当前聊天用户昵称: {nickname}")
                        return nickname

            logger.warning("未能获取当前聊天用户昵称")
            return "未知用户"

        except Exception as e:
            logger.warning(f"获取用户昵称时出错: {e}")
            return "未知用户"

    def _extract_nickname_from_text(self, text: str) -> Optional[str]:
        """
        从组合文本中提取用户昵称

        闲鱼聊天列表中的文本格式通常是：
        - "用户昵称[订单信息]时间"
        - "用户昵称 时间"
        - 纯用户昵称
        """
        try:
            if not text or len(text) < 2:
                return None

            # 排除明显不是用户昵称的文本
            if any(keyword in text for keyword in ['消息', '通知', '搜索', '联系人']):
                return None

            # 尝试按常见分隔符分割
            # 1. 按方括号分割（处理 "用户昵称[订单信息]时间" 格式）
            if '[' in text and ']' in text:
                parts = text.split('[')
                if len(parts) > 1:
                    nickname = parts[0].strip()
                    if nickname and len(nickname) > 1 and len(nickname) < 30:
                        return nickname

            # 2. 按时间关键词分割（处理 "用户昵称 1小时前" 格式）
            time_keywords = ['小时前', '分钟前', '天前', '刚刚', '昨天', '前天']
            for keyword in time_keywords:
                if keyword in text:
                    parts = text.split(keyword)
                    if len(parts) > 1:
                        nickname = parts[0].strip()
                        if nickname and len(nickname) > 1 and len(nickname) < 30:
                            return nickname

            # 3. 如果文本长度适中且不包含特殊字符，可能是纯昵称
            if len(text) < 20 and not any(char in text for char in ['[', ']', '(', ')', '小时', '分钟', '天']):
                return text

            # 4. 尝试按空格分割，取第一个部分
            parts = text.split()
            if parts:
                first_part = parts[0].strip()
                if first_part and len(first_part) > 1 and len(first_part) < 20:
                    return first_part

            return None

        except Exception as e:
            logger.warning(f"提取昵称时出错: {e}")
            return None

    def _parse_message_element(self, msg_element) -> Optional[Dict]:
        """解析单个消息元素 - 优化版本"""
        try:
            # 获取消息文本内容
            text_content = msg_element.text
            if not text_content:
                return None

            # 清理文本内容
            cleaned_content = text_content.strip()
            if len(cleaned_content) < 2:
                return None

            # 判断消息发送者（更智能的判断逻辑）
            role = self._determine_message_role(msg_element)

            # 尝试提取时间信息
            timestamp_info = self._extract_timestamp_info(msg_element)

            message_data = {
                'role': role,
                'content': cleaned_content,
                'timestamp': timestamp_info.get('timestamp', time.time()),
                'time_text': timestamp_info.get('time_text', ''),
                'element_class': msg_element.attr('class') or '',
                'element_id': msg_element.attr('id') or '',
                'parsed_at': datetime.now().isoformat()
            }

            return message_data

        except Exception as e:
            logger.warning(f"解析消息元素时出错: {e}")
            return None

    def _determine_message_role(self, msg_element) -> str:
        """判断消息发送者角色 - 增强版本"""
        try:
            element_class = msg_element.attr('class') or ''
            element_id = msg_element.attr('id') or ''
            element_style = msg_element.attr('style') or ''

            # 基于class名称判断
            class_lower = element_class.lower()

            # 自己发送的消息特征
            self_keywords = ['self', 'me', 'sender', 'mine', 'my', 'right', 'send', 'outgoing', 'sent']
            if any(keyword in class_lower for keyword in self_keywords):
                return 'assistant'

            # 对方发送的消息特征
            other_keywords = ['other', 'user', 'friend', 'contact', 'left', 'receive', 'incoming', 'received']
            if any(keyword in class_lower for keyword in other_keywords):
                return 'user'

            # 基于位置判断（在页面右侧通常是自己的消息）
            try:
                rect = msg_element.rect
                if rect:
                    # 如果元素在页面右侧，可能是自己的消息
                    if rect['x'] > 400:  # 假设页面宽度800px，右侧400px以上
                        return 'assistant'
                    else:
                        return 'user'
            except:
                pass

            # 基于父元素判断
            try:
                parent = msg_element.parent
                if parent:
                    parent_class = parent.attr('class') or ''
                    parent_class_lower = parent_class.lower()

                    if any(keyword in parent_class_lower for keyword in self_keywords):
                        return 'assistant'
                    if any(keyword in parent_class_lower for keyword in other_keywords):
                        return 'user'
            except:
                pass

            # 默认认为是对方的消息
            return 'user'

        except Exception as e:
            logger.warning(f"判断消息角色时出错: {e}")
            return 'user'

    def _extract_timestamp_info(self, msg_element) -> Dict:
        """提取消息时间信息"""
        try:
            # 尝试从元素属性中获取时间
            time_attr = msg_element.attr('data-time') or msg_element.attr('time') or ''
            if time_attr:
                try:
                    timestamp = float(time_attr)
                    return {'timestamp': timestamp, 'time_text': ''}
                except:
                    pass

            # 尝试从文本中提取时间
            text = msg_element.text
            time_patterns = [
                r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})',  # 2023-01-01 12:00:00
                r'(\d{2}:\d{2}:\d{2})',  # 12:00:00
                r'(\d{2}:\d{2})',  # 12:00
                r'(\d+小时前)',
                r'(\d+分钟前)',
                r'(\d+天前)',
                r'(刚刚)',
                r'(昨天)',
                r'(前天)'
            ]

            for pattern in time_patterns:
                match = re.search(pattern, text)
                if match:
                    time_text = match.group(1)
                    return {'timestamp': time.time(), 'time_text': time_text}

            return {'timestamp': time.time(), 'time_text': ''}

        except Exception as e:
            logger.warning(f"提取时间信息时出错: {e}")
            return {'timestamp': time.time(), 'time_text': ''}

    def save_batch_results(self, results: Dict[str, Optional[Dict]], output_dir: str = "batch_user_chats") -> List[str]:
        """
        保存批量爬取结果

        Args:
            results: 爬取结果
            output_dir: 输出目录

        Returns:
            List[str]: 保存的文件路径列表
        """
        saved_files = []

        # 创建输出目录
        os.makedirs(output_dir, exist_ok=True)

        # 生成时间戳
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # 保存汇总报告
        summary_file = self._save_summary_report(results, output_dir, timestamp)
        if summary_file:
            saved_files.append(summary_file)

        # 保存每个用户的聊天记录
        for nickname, chat_data in results.items():
            if chat_data:
                # JSON格式
                json_file = self._save_chat_to_file(chat_data, nickname, output_dir)
                if json_file:
                    saved_files.append(json_file)

                # CSV格式
                csv_file = self._export_chat_to_csv(chat_data, nickname, output_dir)
                if csv_file:
                    saved_files.append(csv_file)

                # Markdown格式
                md_file = self._save_chat_to_markdown(chat_data, nickname, output_dir)
                if md_file:
                    saved_files.append(md_file)

        return saved_files

    def _save_summary_report(self, results: Dict[str, Optional[Dict]], output_dir: str, timestamp: str) -> Optional[str]:
        """保存批量爬取汇总报告"""
        try:
            summary_file = os.path.join(output_dir, f"batch_summary_{timestamp}.json")

            summary_data = {
                'batch_info': {
                    'total_users': len(results),
                    'successful_users': sum(1 for v in results.values() if v),
                    'failed_users': sum(1 for v in results.values() if v is None),
                    'crawl_time': datetime.now().isoformat(),
                    'timestamp': timestamp
                },
                'user_results': {}
            }

            for nickname, chat_data in results.items():
                if chat_data:
                    summary_data['user_results'][nickname] = {
                        'user_nickname': nickname,
                        'message_count': len(chat_data.get('messages', [])),
                        'status': 'success',
                        'crawl_time': chat_data.get('crawl_time', '')
                    }
                else:
                    summary_data['user_results'][nickname] = {
                        'status': 'failed',
                        'error': '未能获取聊天记录'
                    }

            with open(summary_file, 'w', encoding='utf-8') as f:
                json.dump(summary_data, f, ensure_ascii=False, indent=2)

            logger.info(f"汇总报告已保存到: {summary_file}")
            return summary_file

        except Exception as e:
            logger.error(f"保存汇总报告失败: {e}")
            return None

    def _save_chat_to_file(self, chat_data: Dict, nickname: str, output_dir: str = "user_chats") -> Optional[str]:
        """保存聊天记录到JSON文件"""
        try:
            # 创建输出目录
            os.makedirs(output_dir, exist_ok=True)

            # 生成文件名
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"user_chat_{nickname}_{timestamp}.json"
            filepath = os.path.join(output_dir, filename)

            # 保存为JSON文件
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(chat_data, f, ensure_ascii=False, indent=2)

            logger.info(f"聊天记录已保存到: {filepath}")
            return filepath

        except Exception as e:
            logger.error(f"保存聊天记录失败: {e}")
            return None

    def _export_chat_to_csv(self, chat_data: Dict, nickname: str, output_dir: str = "user_chats") -> Optional[str]:
        """导出聊天记录到CSV文件"""
        try:
            import csv

            # 创建输出目录
            os.makedirs(output_dir, exist_ok=True)

            # 生成文件名
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"user_chat_{nickname}_{timestamp}.csv"
            filepath = os.path.join(output_dir, filename)

            with open(filepath, 'w', newline='', encoding='utf-8-sig') as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow([
                    '用户昵称', '消息角色', '消息内容', '时间戳', '消息来源'
                ])

                for message in chat_data['messages']:
                    writer.writerow([
                        nickname,
                        message['role'],
                        message['content'],
                        datetime.fromtimestamp(message['timestamp']).strftime('%Y-%m-%d %H:%M:%S'),
                        chat_data.get('source', 'browser_automation')
                    ])

            logger.info(f"CSV文件已导出到: {filepath}")
            return filepath

        except Exception as e:
            logger.error(f"导出CSV失败: {e}")
            return None

    def export_batch_to_csv(self, results: Dict[str, Optional[Dict]], output_dir: str = "batch_user_chats") -> Optional[str]:
        """导出批量结果到单个CSV文件"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            csv_file = os.path.join(output_dir, f"batch_all_users_{timestamp}.csv")

            with open(csv_file, 'w', newline='', encoding='utf-8-sig') as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow([
                    '用户昵称', '消息角色', '消息内容', '时间戳', '消息来源', '状态'
                ])

                for nickname, chat_data in results.items():
                    if chat_data:
                        for message in chat_data['messages']:
                            writer.writerow([
                                nickname,
                                message['role'],
                                message['content'],
                                datetime.fromtimestamp(message['timestamp']).strftime('%Y-%m-%d %H:%M:%S'),
                                chat_data.get('source', 'browser_automation'),
                                'success'
                            ])
                    else:
                        # 对于失败的用户，添加一条记录
                        writer.writerow([
                            nickname,
                            '',
                            '未能获取聊天记录',
                            datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                            'browser_automation',
                            'failed'
                        ])

            logger.info(f"批量CSV文件已导出到: {csv_file}")
            return csv_file

        except Exception as e:
            logger.error(f"导出批量CSV失败: {e}")
            return None

    def _save_chat_to_markdown(self, chat_data: Dict, nickname: str, output_dir: str = "user_chats") -> Optional[str]:
        """保存聊天记录到Markdown文件"""
        try:
            # 创建输出目录
            os.makedirs(output_dir, exist_ok=True)

            # 生成文件名
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"user_chat_{nickname}_{timestamp}.md"
            filepath = os.path.join(output_dir, filename)

            with open(filepath, 'w', encoding='utf-8') as f:
                # 写入Markdown头部
                f.write(f"# 闲鱼聊天记录 - {nickname}\n\n")
                f.write(f"**爬取时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  \n")
                f.write(f"**总消息数**: {len(chat_data['messages'])}  \n")
                f.write(f"**用户昵称**: {nickname}  \n\n")

                # 写入消息列表
                f.write("## 聊天记录\n\n")

                for i, message in enumerate(chat_data['messages'], 1):
                    role = message.get('role', 'unknown')
                    content = message.get('content', '').strip()
                    timestamp = datetime.fromtimestamp(message.get('timestamp', time.time())).strftime('%Y-%m-%d %H:%M:%S')

                    # 根据消息角色设置不同的格式
                    if role == 'buyer':
                        f.write(f"### 👤 买家消息 #{i}\n")
                        f.write(f"**时间**: {timestamp}  \n")
                        f.write(f"**内容**: {content}  \n\n")
                    elif role == 'seller':
                        f.write(f"### 🏪 卖家消息 #{i}\n")
                        f.write(f"**时间**: {timestamp}  \n")
                        f.write(f"**内容**: {content}  \n\n")
                    else:
                        f.write(f"### ❓ 未知消息 #{i}\n")
                        f.write(f"**时间**: {timestamp}  \n")
                        f.write(f"**内容**: {content}  \n\n")

                # 添加统计信息
                f.write("## 统计信息\n\n")
                buyer_count = sum(1 for msg in chat_data['messages'] if msg.get('role') == 'buyer')
                seller_count = sum(1 for msg in chat_data['messages'] if msg.get('role') == 'seller')
                unknown_count = sum(1 for msg in chat_data['messages'] if msg.get('role') not in ['buyer', 'seller'])

                f.write(f"- **买家消息**: {buyer_count} 条  \n")
                f.write(f"- **卖家消息**: {seller_count} 条  \n")
                f.write(f"- **未知消息**: {unknown_count} 条  \n")
                f.write(f"- **消息总数**: {len(chat_data['messages'])} 条  \n\n")

            logger.info(f"Markdown聊天记录已保存到: {filepath}")
            return filepath

        except Exception as e:
            logger.error(f"保存Markdown聊天记录失败: {e}")
            return None


def main():
    """命令行入口函数"""
    import argparse

    parser = argparse.ArgumentParser(description='批量用户聊天数据爬取工具')
    parser.add_argument('--nickname-file', help='包含用户昵称列表的文件路径（每行一个用户昵称）')
    parser.add_argument('--max-users', type=int, default=10, help='自动爬取的最大用户数量（默认：10）')
    parser.add_argument('--output-dir', default='batch_user_chats', help='输出目录')
    parser.add_argument('--max-messages', type=int, default=100, help='每个用户的最大消息数量')
    parser.add_argument('--delay', type=float, default=1.5, help='用户之间的延迟（秒）')
    parser.add_argument('--headless', action='store_true', help='使用无头模式')

    args = parser.parse_args()

    # 检查参数
    if not args.nickname_file and args.max_users <= 0:
        print("错误: 必须提供昵称文件或设置最大用户数量")
        return

    try:
        # 创建批量爬取器
        batch_crawler = BatchUserCrawler(headless=args.headless)

        # 初始化浏览器
        if not batch_crawler.init_browser():
            print("浏览器初始化失败")
            return

        # 登录并导航到聊天页面
        print("正在登录并导航到闲鱼聊天页面...")
        if not batch_crawler.login_and_navigate():
            print("登录和导航失败")
            return

        results = {}

        if args.nickname_file:
            # 使用昵称文件模式
            try:
                with open(args.nickname_file, 'r', encoding='utf-8') as f:
                    user_nicknames = [line.strip() for line in f if line.strip() and not line.startswith('#')]

                if not user_nicknames:
                    print("错误: 用户昵称列表文件为空")
                    return

                print(f"读取到 {len(user_nicknames)} 个用户昵称")

                # 批量爬取
                print(f"开始批量爬取 {len(user_nicknames)} 个用户的聊天记录...")
                results = batch_crawler.crawl_multiple_users_by_nickname(
                    user_nicknames,
                    max_messages=args.max_messages,
                    delay_between_users=args.delay
                )

            except Exception as e:
                print(f"读取用户昵称文件失败: {e}")
                return
        else:
            # 自动爬取聊天列表用户模式
            print(f"开始自动爬取聊天列表中的前 {args.max_users} 个用户...")
            results = batch_crawler.crawl_chat_list_users(
                max_users=args.max_users,
                max_messages=args.max_messages,
                delay_between_users=args.delay
            )

        # 保存结果
        saved_files = batch_crawler.save_batch_results(results, args.output_dir)

        # 导出批量CSV
        csv_file = batch_crawler.export_batch_to_csv(results, args.output_dir)
        if csv_file:
            saved_files.append(csv_file)

        if saved_files:
            print(f"\n批量爬取完成！共保存 {len(saved_files)} 个文件:")
            for file in saved_files:
                print(f"  - {file}")

            # 显示统计信息
            successful = sum(1 for v in results.values() if v)
            print(f"\n统计信息:")
            print(f"  总用户数: {len(results)}")
            print(f"  成功获取: {successful}")
            print(f"  失败用户: {len(results) - successful}")
        else:
            print("文件保存失败")

    except Exception as e:
        print(f"批量爬取失败: {e}")
    finally:
        # 关闭浏览器
        if batch_crawler.page:
            batch_crawler.page.quit()
            print("浏览器已关闭")


if __name__ == '__main__':
    main()