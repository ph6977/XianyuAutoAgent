#!/usr/bin/env python3
"""
优化版批量用户聊天数据爬取工具
基于实际测试结果重构，提高逻辑性、稳定性和健壮性
"""

import os
import json
import csv
import time
import re
from datetime import datetime
from typing import List, Dict, Optional, Tuple
from loguru import logger

from DrissionPage import ChromiumPage, ChromiumOptions


class OptimizedBatchUserCrawler:
    """基于浏览器自动化的优化版批量用户聊天数据爬取器"""

    def __init__(self, headless: bool = False):
        """
        初始化爬取器

        Args:
            headless: 是否使用无头模式
        """
        self.headless = headless
        self.page = None
        self.is_logged_in = False
        self.current_user_nickname = None

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
        """等待聊天页面加载完成 - 简化版本"""
        max_wait = 30
        start_time = time.time()

        while time.time() - start_time < max_wait:
            # 直接检查关键元素是否存在
            if self.page.ele('.rc-virtual-list-holder', timeout=2):
                logger.info("聊天页面加载完成")
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

    def crawl_multiple_users_by_nickname(self, user_nicknames: List[str], max_messages: int = 100,
                                       delay_between_users: float = 3.0, max_retries: int = 2) -> Dict[str, Optional[Dict]]:
        """
        基于昵称批量爬取多个用户的聊天记录 - 优化版本

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

        # 过滤系统消息
        system_keywords = ['通知', '系统', '客服', '官方', '消息', '公告', '提醒', '提示']
        filtered_users = []
        system_users = []

        for nickname in user_nicknames:
            is_system = any(keyword in nickname for keyword in system_keywords)
            if is_system:
                system_users.append(nickname)
                logger.info(f"跳过系统消息: {nickname}")
                results[nickname] = None  # 标记为跳过
            else:
                filtered_users.append(nickname)

        if system_users:
            logger.info(f"已过滤 {len(system_users)} 个系统消息: {system_users}")

        logger.info(f"开始批量爬取 {len(filtered_users)} 个真实用户的聊天记录...")

        for i, nickname in enumerate(filtered_users, 1):
            success = False
            retry_count = 0

            while retry_count <= max_retries and not success:
                try:
                    logger.info(f"正在爬取第 {i}/{len(user_nicknames)} 个用户: {nickname} (重试 {retry_count}/{max_retries})")

                    # 查找并点击用户
                    if not self._find_and_click_user(nickname):
                        logger.warning(f"未找到用户: {nickname}")
                        results[nickname] = None
                        break

                    # 等待聊天页面加载
                    time.sleep(2)

                    # 获取聊天记录
                    chat_data = self._get_chat_history_optimized(max_messages)
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

    def _find_and_click_user(self, nickname: str) -> bool:
        """
        在聊天列表中查找并点击用户 - 改进版本

        Args:
            nickname: 用户昵称

        Returns:
            bool: 是否成功找到并点击用户
        """
        try:
            logger.info(f"正在查找用户: {nickname}")

            # 先尝试使用JavaScript精确查找
            user_found = self.page.run_js(f"""
                function findUserByNickname(nickname) {{
                    // 查找所有可能的用户昵称元素
                    var selectors = [
                        'div[style*="max-width: 176px"][style*="font-weight: 500"][style*="color: rgb(51, 51, 51)"]',
                        'div[style*="overflow: hidden"][style*="text-overflow: ellipsis"][style*="white-space: nowrap"][style*="max-width: 176px"]',
                        'div[style*="overflow: hidden"][style*="text-overflow: ellipsis"][style*="white-space: nowrap"][style*="max-width: 102px"]'
                    ];

                    for (var i = 0; i < selectors.length; i++) {{
                        var elements = document.querySelectorAll(selectors[i]);
                        for (var j = 0; j < elements.length; j++) {{
                            var element = elements[j];
                            var text = element.textContent.trim();
                            if (text === nickname) {{
                                // 找到用户，点击并返回成功
                                element.click();
                                return true;
                            }}
                        }}
                    }}
                    return false;
                }}
                return findUserByNickname(arguments[0]);
            """, nickname)

            if user_found:
                time.sleep(2)
                logger.info(f"✅ 成功找到并点击用户: {nickname}")
                return True

            # 如果JavaScript方法失败，使用传统方法
            max_scroll_attempts = 8
            scroll_height = 300

            for attempt in range(max_scroll_attempts):
                # 首先尝试查找用户（不滚动）
                user_elements = self.page.eles(f'text={nickname}')

                if user_elements:
                    # 找到用户，点击进入聊天
                    logger.info(f"找到用户: {nickname}")
                    for element in user_elements:
                        try:
                            element.click()
                            time.sleep(2)
                            logger.info(f"✅ 成功点击用户: {nickname}")
                            return True
                        except Exception as click_error:
                            logger.warning(f"点击元素失败，尝试下一个: {click_error}")
                            continue

                # 如果这是第一次查找且没找到，先不滚动，可能是用户就在当前可见区域
                if attempt == 0:
                    logger.info(f"首次查找未找到用户 {nickname}，等待页面稳定...")
                    time.sleep(1)
                    continue

                # 如果还是没找到，再尝试滚动
                logger.info(f"未找到用户 {nickname}，尝试滚动聊天列表 (第{attempt}次)")

                # 使用JavaScript滚动，更可靠
                scroll_result = self.page.run_js(f"""
                    var scrollContainer = document.querySelector('.rc-virtual-list-holder') ||
                                         document.querySelector('.conv-list-scroll--Bn4G27Nb') ||
                                         document.querySelector('.rc-virtual-list');
                    if (scrollContainer) {{
                        scrollContainer.scrollTop += {scroll_height};
                        return {{'method': 'container_scroll', 'distance': {scroll_height}}};
                    }} else {{
                        window.scrollBy(0, {scroll_height});
                        return {{'method': 'window_scroll', 'distance': {scroll_height}}};
                    }}
                """)

                logger.debug(f"滚动结果: {scroll_result}")
                time.sleep(2)  # 增加等待时间，确保滚动后页面稳定

            logger.warning(f"❌ 在聊天列表中未找到用户: {nickname}")
            return False

        except Exception as e:
            logger.error(f"查找用户 {nickname} 时出错: {e}")
            return False

    def _get_chat_history_optimized(self, max_messages: int = 100) -> Optional[Dict]:
        """
        获取当前聊天页面的历史消息 - 优化版本

        Args:
            max_messages: 最大消息数量

        Returns:
            Dict: 聊天数据
        """
        try:
            # 等待聊天消息区域加载
            logger.info("等待聊天消息区域加载...")
            time.sleep(2)

            # 直接使用JavaScript提取消息数据，跳过复杂的元素查找
            logger.info("使用优化JavaScript提取消息数据...")

            # 滚动加载历史消息
            self._scroll_to_load_history_optimized()

            # 提取消息数据
            messages_data = self._extract_messages_with_js()

            if not messages_data:
                logger.warning("未找到任何消息")
                return None

            # 获取当前聊天用户的昵称
            current_user_nickname = self._get_current_chat_user_nickname_optimized()

            # 构建聊天数据
            chat_data = {
                'user_nickname': current_user_nickname,
                'messages': messages_data[:max_messages],
                'message_count': len(messages_data[:max_messages]),
                'crawl_time': datetime.now().isoformat(),
                'source': 'browser_automation'
            }

            logger.info(f"成功解析 {len(messages_data[:max_messages])} 条消息")
            return chat_data

        except Exception as e:
            logger.error(f"获取聊天记录时出错: {e}")
            return None

    def _scroll_to_load_history_optimized(self):
        """滚动消息区域以加载历史消息 - 优化版本"""
        try:
            logger.info("开始智能滚动加载历史消息...")

            # 简化滚动策略
            max_scroll_attempts = 5
            scroll_distance = 500
            consecutive_no_new_messages = 0

            for attempt in range(max_scroll_attempts):
                # 获取滚动前的消息数量
                messages_before = self._get_message_count_optimized()

                logger.info(f"第{attempt + 1}次向上滚动...")

                # 使用多种滚动方法 - 只滚动消息区域，不滚动用户列表
                scroll_result = self.page.run_js(f"""
                    // 尝试多种消息区域的滚动容器（排除用户列表容器）
                    var messageScrollContainers = [
                        '.scroll-container--WObNWx73',
                        '.message-scroll-container',
                        '.chat-scroll-container',
                        '.message-list',
                        '.chat-messages',
                        '[class*="message"][class*="scroll"]',
                        '[class*="chat"][class*="scroll"]'
                    ];

                    var scrollContainer = null;
                    for (var i = 0; i < messageScrollContainers.length; i++) {{
                        var container = document.querySelector(messageScrollContainers[i]);
                        if (container && container.scrollHeight > container.clientHeight) {{
                            scrollContainer = container;
                            break;
                        }}
                    }}

                    // 如果没找到特定消息容器，尝试通用容器但排除用户列表
                    if (!scrollContainer) {{
                        var allScrollContainers = document.querySelectorAll('[class*="scroll"]');
                        for (var j = 0; j < allScrollContainers.length; j++) {{
                            var container = allScrollContainers[j];
                            // 排除用户列表相关的容器
                            var containerClass = container.className || '';
                            if (container.scrollHeight > container.clientHeight &&
                                !containerClass.includes('conv-list') &&
                                !containerClass.includes('user-list') &&
                                !containerClass.includes('contact-list')) {{
                                scrollContainer = container;
                                break;
                            }}
                        }}
                    }}

                    if (!scrollContainer) {{
                        // 如果没有找到特定容器，尝试使用页面滚动
                        window.scrollBy(0, -{scroll_distance});
                        return {{'method': 'window_scroll', 'distance': -{scroll_distance}}};
                    }}

                    // 使用容器滚动
                    var currentScrollTop = scrollContainer.scrollTop;
                    scrollContainer.scrollTop = currentScrollTop + {scroll_distance};

                    return {{
                        'method': 'container_scroll',
                        'currentY': currentScrollTop,
                        'newY': scrollContainer.scrollTop,
                        'container': scrollContainer.className
                    }};
                """)

                logger.info(f"滚动结果: {scroll_result}")

                # 等待消息加载
                wait_time = 1.5
                logger.info(f"等待 {wait_time} 秒让消息加载...")
                time.sleep(wait_time)

                # 获取滚动后的消息数量
                messages_after = self._get_message_count_optimized()

                # 检查是否加载了新消息
                if messages_after > messages_before:
                    logger.info(f"✅ 成功加载新消息: {messages_before} -> {messages_after}")
                    consecutive_no_new_messages = 0
                else:
                    logger.info(f"⚠️  未加载新消息，当前总数: {messages_after}")
                    consecutive_no_new_messages += 1

                # 检查是否已滚动到顶部
                if consecutive_no_new_messages >= 2:
                    logger.info("连续2次滚动未加载新消息，可能已到顶部，停止滚动")
                    break

            logger.info("滚动加载完成")

        except Exception as e:
            logger.warning(f"滚动加载历史消息时出错: {e}")

    def _get_message_count_optimized(self) -> int:
        """获取当前可见消息数量 - 优化版本"""
        try:
            count_info = self.page.run_js("""
                // 基于实际闲鱼消息样式查找
                var messageElements = document.querySelectorAll('span[style*="color: rgb(31, 31, 31)"][style*="font-size: 14px"]');
                return messageElements.length;
            """)
            return count_info
        except Exception as e:
            logger.warning(f"获取消息数量失败: {e}")
            return 0

    def _extract_messages_with_js(self) -> List[Dict]:
        """使用JavaScript提取消息数据 - 优化版本"""
        try:
            messages_data = self.page.run_js("""
                // 极速消息提取 - 基于实际闲鱼页面结构
                var messages = [];

                // 查找所有可能包含消息的元素
                var selectors = [
                    'span[style*="color: rgb(31, 31, 31)"][style*="font-size: 14px"]',
                    'span[style*="font-size: 14px"]',
                    '[class*="message"]',
                    '[class*="msg"]'
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
                                var rect = element.getBoundingClientRect();

                                // 基于位置判断：左侧是买家，右侧是卖家
                                if (rect.left < window.innerWidth / 2) {
                                    role = 'buyer';
                                } else {
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

                return messages;
            """)

            if messages_data:
                # 转换为标准格式
                formatted_messages = []
                for msg in messages_data:
                    formatted_messages.append({
                        'role': msg.get('role', 'unknown'),
                        'content': msg.get('text', ''),
                        'timestamp': msg.get('timestamp', time.time()),
                        'time_text': '',
                        'element_class': '',
                        'element_id': '',
                        'parsed_at': datetime.now().isoformat()
                    })

                logger.info(f"通过优化JavaScript提取到 {len(formatted_messages)} 条消息")
                return formatted_messages

            return []

        except Exception as e:
            logger.error(f"提取消息数据时出错: {e}")
            return []

    def _get_current_chat_user_nickname_optimized(self) -> str:
        """获取当前聊天用户的昵称 - 改进版本"""
        try:
            # 方法1：直接使用点击的用户昵称（最可靠的方法）
            # 因为在_find_and_click_user中我们已经成功找到了用户
            # 这里我们可以直接返回用户昵称，避免复杂的DOM查找

            # 方法2：从页面标题获取
            title = self.page.title
            if title and '闲鱼' in title:
                import re
                match = re.search(r'(.+?)的闲鱼', title)
                if match and match.group(1):
                    nickname = match.group(1)
                    # 过滤系统文本
                    system_keywords = ['搜索', '联系人', '消息', '通知', '系统', '恭喜', '获得', '优惠', '省钱', '拍下', '付款', '待付款']
                    if not any(keyword in nickname for keyword in system_keywords):
                        logger.info(f"从页面标题找到当前聊天用户昵称: {nickname}")
                        return nickname

            # 方法3：使用JavaScript查找当前活跃的聊天项
            nickname = self.page.run_js("""
                // 查找当前活跃的聊天项
                var activeSelectors = [
                    '[class*="active"][class*="conversation"]',
                    '[class*="selected"][class*="chat"]',
                    '.conversation-item--active',
                    '.chat-item--selected'
                ];

                for (var i = 0; i < activeSelectors.length; i++) {
                    var activeElements = document.querySelectorAll(activeSelectors[i]);
                    for (var j = 0; j < activeElements.length; j++) {
                        // 在活跃元素中查找用户昵称
                        var userElements = activeElements[j].querySelectorAll('div[style*="max-width: 176px"][style*="font-weight: 500"][style*="color: rgb(51, 51, 51)"]');
                        for (var k = 0; k < userElements.length; k++) {
                            var text = userElements[k].textContent.trim();
                            if (text && text.length >= 2 && text.length <= 20) {
                                // 过滤系统文本
                                var systemKeywords = ['搜索', '联系人', '消息', '通知', '系统', '恭喜', '获得', '优惠', '省钱', '拍下', '付款', '待付款'];
                                var isSystemText = systemKeywords.some(function(keyword) {
                                    return text.includes(keyword);
                                });
                                if (!isSystemText) {
                                    return text;
                                }
                            }
                        }
                    }
                }
                return '';
            """)

            if nickname:
                logger.info(f"从活跃聊天项找到当前聊天用户昵称: {nickname}")
                return nickname

            # 方法4：如果以上方法都失败，返回一个默认值
            logger.warning("未能准确获取当前聊天用户昵称，使用默认值")
            return "当前用户"

        except Exception as e:
            logger.warning(f"获取用户昵称时出错: {e}")
            return "当前用户"

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

    def crawl_chat_list_users(self, max_users: int = 10, max_messages: int = 100,
                            delay_between_users: float = 3.0) -> Dict[str, Optional[Dict]]:
        """
        自动爬取聊天列表中的用户聊天记录 - 优化版本

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
            logger.warning("未在聊天列表中找到任何用户")
            return results

        logger.info(f"在聊天列表中找到 {len(user_nicknames)} 个用户")

        # 过滤系统消息
        system_keywords = ['通知', '系统', '客服', '官方', '消息', '公告', '提醒', '提示']
        filtered_users = []
        system_users = []

        for nickname in user_nicknames:
            is_system = any(keyword in nickname for keyword in system_keywords)
            if is_system:
                system_users.append(nickname)
                logger.info(f"跳过系统消息: {nickname}")
                results[nickname] = None  # 标记为跳过
            else:
                filtered_users.append(nickname)

        if system_users:
            logger.info(f"已过滤 {len(system_users)} 个系统消息: {system_users}")

        logger.info(f"开始批量爬取 {len(filtered_users)} 个真实用户的聊天记录...")

        for i, nickname in enumerate(filtered_users, 1):
            try:
                logger.info(f"正在爬取第 {i}/{len(filtered_users)} 个用户: {nickname}")

                # 点击用户进入聊天页面
                if not self._find_and_click_user(nickname):
                    logger.warning(f"无法点击用户: {nickname}")
                    results[nickname] = None
                    continue

                # 等待聊天页面加载
                time.sleep(2)

                # 获取聊天记录
                chat_data = self._get_chat_history_optimized(max_messages)
                results[nickname] = chat_data

                if chat_data:
                    logger.info(f"✅ 成功获取用户 {nickname} 的 {len(chat_data['messages'])} 条消息")
                else:
                    logger.warning(f"⚠️  未能获取用户 {nickname} 的聊天记录")

                # 添加延迟，避免请求过于频繁
                if i < len(filtered_users):
                    logger.info(f"等待 {delay_between_users} 秒后继续...")
                    time.sleep(delay_between_users)

            except Exception as e:
                logger.error(f"爬取用户 {nickname} 时出错: {e}")
                results[nickname] = None

        successful_count = sum(1 for v in results.values() if v)
        logger.info(f"自动爬取完成，成功获取 {successful_count}/{len(user_nicknames)} 个用户的记录")
        return results

    def _get_chat_list_users(self, max_users: int = 10) -> List[str]:
        """
        获取聊天列表中的用户昵称 - 简化优化版本

        Args:
            max_users: 最大用户数量

        Returns:
            List[str]: 用户昵称列表
        """
        try:
            logger.info(f"正在获取聊天列表中的前 {max_users} 个用户...")

            user_nicknames = []
            max_scroll_attempts = 10
            scroll_height = 300
            last_scroll_position = 0

            # 用户昵称选择器 - 基于实际闲鱼页面结构
            nickname_selectors = [
                'div[style*="max-width: 176px"][style*="font-weight: 500"][style*="color: rgb(51, 51, 51)"]',
                'div[style*="overflow: hidden"][style*="text-overflow: ellipsis"][style*="white-space: nowrap"][style*="max-width: 176px"]',
                'div[style*="overflow: hidden"][style*="text-overflow: ellipsis"][style*="white-space: nowrap"][style*="max-width: 102px"]'
            ]

            # 系统消息关键词
            system_keywords = ['通知', '系统', '客服', '官方', '消息', '公告', '提醒', '提示']

            for attempt in range(max_scroll_attempts):
                logger.info(f"第 {attempt + 1} 次查找用户...")

                # 在当前视图中查找用户昵称
                for selector in nickname_selectors:
                    elements = self.page.eles(selector)
                    for element in elements:
                        text = element.text.strip()
                        if text and len(text) > 1 and len(text) < 30:
                            # 过滤系统消息
                            is_system = any(keyword in text for keyword in system_keywords)
                            if not is_system and text not in user_nicknames:
                                user_nicknames.append(text)
                                logger.info(f"找到用户: {text}")

                        # 如果找到足够用户，停止查找
                        if len(user_nicknames) >= max_users:
                            break

                    if len(user_nicknames) >= max_users:
                        break

                # 如果已经找到足够用户，停止滚动
                if len(user_nicknames) >= max_users:
                    logger.info(f"已找到 {len(user_nicknames)} 个用户，停止滚动")
                    break

                # 滚动加载更多用户
                logger.info(f"滚动加载更多用户 (第{attempt + 1}次)...")
                scroll_result = self.page.run_js(f"""
                    var scrollContainer = document.querySelector('.rc-virtual-list-holder') ||
                                         document.querySelector('.conv-list-scroll--Bn4G27Nb') ||
                                         document.querySelector('.rc-virtual-list') ||
                                         document.querySelector('[class*="scroll"]');

                    if (scrollContainer) {{
                        var currentScrollTop = scrollContainer.scrollTop;
                        scrollContainer.scrollTop = currentScrollTop + {scroll_height};
                        return {{
                            'method': 'container_scroll',
                            'currentY': currentScrollTop,
                            'newY': scrollContainer.scrollTop,
                            'container': scrollContainer.className || ''
                        }};
                    }} else {{
                        window.scrollBy(0, {scroll_height});
                        return {{
                            'method': 'window_scroll',
                            'distance': {scroll_height}
                        }};
                    }}
                """)

                logger.debug(f"滚动结果: {scroll_result}")

                # 检查是否滚动到底部
                if 'currentY' in scroll_result and 'newY' in scroll_result:
                    if scroll_result['currentY'] == scroll_result['newY'] and attempt > 2:
                        logger.info("已滚动到底部，停止搜索")
                        break

                # 等待滚动后页面稳定
                time.sleep(2)

            # 限制用户数量
            user_nicknames = user_nicknames[:max_users]
            logger.info(f"从聊天列表中找到 {len(user_nicknames)} 个用户")
            return user_nicknames

        except Exception as e:
            logger.error(f"获取聊天列表用户时出错: {e}")
            return self._get_chat_list_users_fallback(max_users)

    def _get_chat_list_users_fallback(self, max_users: int = 10) -> List[str]:
        """获取聊天列表用户的后备方法"""
        try:
            logger.info("使用后备方法获取聊天列表用户...")

            # 基于文本查找用户昵称
            user_nicknames = []

            # 查找所有可能的用户昵称元素
            nickname_selectors = [
                'div[style*="max-width: 176px"][style*="font-weight: 500"][style*="color: rgb(51, 51, 51)"]',
                'div[style*="overflow: hidden"][style*="text-overflow: ellipsis"][style*="white-space: nowrap"][style*="max-width: 176px"]',
                'div[style*="overflow: hidden"][style*="text-overflow: ellipsis"][style*="white-space: nowrap"][style*="max-width: 102px"]'
            ]

            for selector in nickname_selectors:
                elements = self.page.eles(selector)
                for element in elements:
                    text = element.text.strip()
                    if text and len(text) > 1 and len(text) < 30:
                        # 过滤系统消息
                        system_keywords = ['通知', '系统', '客服', '官方', '消息', '公告', '提醒', '提示']
                        is_system = any(keyword in text for keyword in system_keywords)
                        if not is_system and text not in user_nicknames:
                            user_nicknames.append(text)
                            logger.info(f"找到用户: {text}")

                    if len(user_nicknames) >= max_users:
                        break

                if len(user_nicknames) >= max_users:
                    break

            logger.info(f"后备方法找到 {len(user_nicknames)} 个用户")
            return user_nicknames[:max_users]

        except Exception as e:
            logger.error(f"后备方法获取用户失败: {e}")
            return []

    def close_browser(self):
        """关闭浏览器"""
        if self.page:
            self.page.quit()
            logger.info("浏览器已关闭")


def main():
    """命令行入口函数"""
    import argparse

    parser = argparse.ArgumentParser(description='优化版批量用户聊天数据爬取工具')
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
        batch_crawler = OptimizedBatchUserCrawler(headless=args.headless)

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

        # 保存结果
        saved_files = batch_crawler.save_batch_results(results, args.output_dir)

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
        if 'batch_crawler' in locals():
            batch_crawler.close_browser()


if __name__ == '__main__':
    main()