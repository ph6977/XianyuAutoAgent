"""
增强版聊天记录爬虫 - 为分析优化
专门收集砍价次数、成交情况、价格变化、物流讨论等关键指标
"""

import os
import json
import csv
import time
import re
from datetime import datetime
from typing import List, Dict, Optional
from loguru import logger
import pandas as pd

from DrissionPage import ChromiumPage, ChromiumOptions


class EnhancedChatCrawler:
    """为分析优化的增强版聊天记录爬虫"""

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
        
        # 用于分析的特殊字段
        self.conversation_context = {
            'bargain_attempts': 0,      # 砍价次数
            'price_mentions': [],       # 价格提及
            'deal_keywords_found': [],  # 成交关键词
            'shipping_keywords_found': [], # 物流关键词
            'negotiation_phases': [],   # 议价阶段
            'transaction_status': 'pending'  # 交易状态
        }

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
            
        except Exception as e:
            logger.error(f"浏览器初始化失败: {e}")
            raise

    def _load_cookies_from_env(self) -> Optional[str]:
        """从环境变量加载cookies"""
        try:
            cookies_str = os.getenv("COOKIES_STR")
            if cookies_str:
                # 验证cookies是否包含关键字段
                if 'unb' in cookies_str and len(cookies_str) > 50:
                    return cookies_str
                else:
                    logger.warning("环境变量中的cookies格式不正确或缺少关键字段")
                    return None
            else:
                logger.warning("未找到COOKIES_STR环境变量")
                return None
        except Exception as e:
            logger.error(f"加载cookies失败: {e}")
            return None

    def navigate_to_chat(self, user_nickname: str) -> bool:
        """
        导航到指定用户的聊天页面

        Args:
            user_nickname: 用户昵称

        Returns:
            bool: 是否成功导航
        """
        try:
            logger.info(f"正在导航到用户 {user_nickname} 的聊天页面")
            
            # 首先确保在聊天主页面
            logger.info("正在导航到闲鱼聊天页面...")
            self.page.get("https://www.goofish.com/im?spm=a21ybx.account.sidebar.2.6a3035ca2iyGly")
            time.sleep(3)

            # 等待页面加载
            if not self._wait_for_chat_page_loaded():
                logger.warning("聊天页面加载超时")
                return False
            
            # 在聊天列表中查找并点击用户
            if not self._find_and_click_user_in_chat_list(user_nickname):
                logger.warning(f"未找到用户: {user_nickname} 在聊天列表中")
                # 如果在聊天列表中找不到，可能需要使用搜索功能
                return self._search_and_navigate_to_user(user_nickname)
            
            time.sleep(3)  # 等待聊天页面加载
            return True
                
        except Exception as e:
            logger.error(f"导航到聊天页面失败: {e}")
            return False

    def _wait_for_chat_page_loaded(self):
        """等待聊天页面加载完成"""
        max_wait = 30
        start_time = time.time()

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
            '[class*="chat"]',
            '[class*="conversation"]',
            '[class*="im"]'
        ]

        while time.time() - start_time < max_wait:
            for selector in chat_list_selectors:
                try:
                    element = self.page.ele(selector, timeout=2)
                    if element:
                        logger.info(f"找到聊天列表元素: {selector}")
                        return True
                except Exception:
                    continue

            # 检查是否有任何用户相关的元素
            user_elements = self.page.eles('[class*="user"]')
            if user_elements:
                logger.info("找到用户相关元素，聊天页面可能已加载")
                return True

            time.sleep(1)

        logger.warning("聊天页面加载超时")
        return False

    def _find_and_click_user_in_chat_list(self, user_nickname: str) -> bool:
        """
        在聊天列表中查找并点击用户

        Args:
            user_nickname: 用户昵称

        Returns:
            bool: 是否成功找到并点击用户
        """
        try:
            logger.info(f"在聊天列表中查找用户: {user_nickname}")

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

            # 滚动查找用户
            max_scroll_attempts = 15
            scroll_height = 500
            last_scroll_position = 0

            for attempt in range(max_scroll_attempts):
                # 使用JavaScript精确查找用户
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
                """, user_nickname)

                if user_found:
                    time.sleep(2)
                    logger.info(f"✅ 成功找到并点击用户: {user_nickname}")
                    return True

                # 如果JavaScript方法失败，使用传统方法
                # 首先尝试查找用户（不滚动）
                user_elements = self.page.eles(f'text={user_nickname}')

                if user_elements:
                    # 找到用户，点击进入聊天
                    logger.info(f"找到用户: {user_nickname}")
                    for element in user_elements:
                        try:
                            element.click()
                            time.sleep(2)
                            logger.info(f"✅ 成功点击用户: {user_nickname}")
                            return True
                        except Exception as click_error:
                            logger.warning(f"点击元素失败，尝试下一个: {click_error}")
                            continue

                # 如果还是没找到，再尝试滚动
                logger.info(f"未找到用户 {user_nickname}，尝试滚动聊天列表 (第{attempt + 1}次)")

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

                # 检查是否已经滚动到底部
                current_scroll = self.page.run_js("return arguments[0].scrollTop", chat_list) if chat_list != self.page else self.page.run_js("return window.pageYOffset")
                if current_scroll == last_scroll_position and attempt > 2:
                    logger.info("已滚动到底部，停止搜索")
                    break
                last_scroll_position = current_scroll

            logger.warning(f"❌ 在聊天列表中未找到用户: {user_nickname}")
            return False

        except Exception as e:
            logger.error(f"查找用户 {user_nickname} 时出错: {e}")
            return False

    def _search_and_navigate_to_user(self, user_nickname: str) -> bool:
        """
        使用搜索功能导航到用户

        Args:
            user_nickname: 用户昵称

        Returns:
            bool: 是否成功导航
        """
        try:
            logger.info(f"使用搜索功能查找用户: {user_nickname}")
            
            # 查找搜索框 - 通常在页面顶部
            search_selectors = [
                'input[placeholder*="搜索"]',
                'input[placeholder*="联系人"]',
                'input[placeholder*="朋友"]',
                'input[role="search"]',
                'input[type="text"]',
                'input'
            ]
            
            search_input = None
            for selector in search_selectors:
                try:
                    search_input = self.page.ele(selector, timeout=3)
                    if search_input and search_input.rect().y < 100:  # 通常在页面顶部
                        break
                except:
                    continue
            
            if not search_input:
                logger.error("未找到搜索输入框")
                return False
            
            # 清空并输入用户昵称
            search_input.clear()
            search_input.input(user_nickname)
            time.sleep(1)
            
            # 查找搜索结果
            # 使用JavaScript方法查找匹配的用户
            search_result_found = self.page.run_js(f"""
                function searchUser(nickname) {{
                    // 查找所有可能的搜索结果
                    var selectors = [
                        'div[style*="max-width: 176px"][style*="font-weight: 500"][style*="color: rgb(51, 51, 51)"]',
                        'div[style*="overflow: hidden"][style*="text-overflow: ellipsis"][style*="white-space: nowrap"]',
                        '[class*="search"] [class*="result"]',
                        '[class*="contact"] [class*="name"]'
                    ];

                    for (var i = 0; i < selectors.length; i++) {{
                        var elements = document.querySelectorAll(selectors[i]);
                        for (var j = 0; j < elements.length; j++) {{
                            var element = elements[j];
                            var text = element.textContent.trim();
                            if (text && text.includes(nickname)) {{
                                element.click();
                                return true;
                            }}
                        }}
                    }}
                    return false;
                }}
                return searchUser(arguments[0]);
            """, user_nickname)
            
            if search_result_found:
                time.sleep(2)
                logger.info(f"通过搜索成功找到并点击用户: {user_nickname}")
                return True
            
            # 如果JavaScript方法失败，尝试常规方法
            search_results = self.page.eles(f'text={user_nickname}')
            for result in search_results:
                try:
                    # 检查元素是否在搜索结果区域
                    if result.rect().y < 300:  # 搜索结果通常在页面上部
                        result.click()
                        time.sleep(2)
                        logger.info(f"通过搜索找到并点击用户: {user_nickname}")
                        return True
                except:
                    continue
            
            logger.warning(f"搜索用户 {user_nickname} 失败")
            return False
            
        except Exception as e:
            logger.error(f"搜索用户时出错: {e}")
            return False

    def extract_enhanced_message_data(self, message_element) -> Optional[Dict]:
        """
        提取增强的消息数据，包含分析所需的关键指标

        Args:
            message_element: 消息元素

        Returns:
            Dict: 包含增强数据的消息信息
        """
        try:
            # 使用JavaScript来提取消息数据，更可靠
            message_data = self.page.run_js("""
                function extractMessageData(element) {
                    if (!element) return null;
                    
                    // 获取消息内容
                    var content = '';
                    // 尝试多种方式获取内容
                    if (element.textContent) {
                        content = element.textContent.trim();
                    } else if (element.innerText) {
                        content = element.innerText.trim();
                    }
                    
                    // 检查是否是消息元素
                    var isMessage = false;
                    var role = 'unknown';
                    
                    // 检查元素的类名和样式来判断是否是消息
                    var className = element.className || '';
                    var style = element.getAttribute('style') || '';
                    
                    // 检查是否是消息内容元素 - 基于闲鱼的实际样式
                    if (style.includes('color: rgb(31, 31, 31)') && style.includes('font-size: 14px')) {
                        isMessage = true;
                    }
                    
                    // 检查父元素来判断消息角色
                    var parent = element.parentElement;
                    while (parent) {
                        var parentStyle = parent.getAttribute('style') || '';
                        // 基于位置判断角色：左侧是买家，右侧是卖家
                        if (parentStyle.includes('justify-content: flex-start')) {
                            role = 'buyer';
                            break;
                        } else if (parentStyle.includes('justify-content: flex-end')) {
                            role = 'seller';
                            break;
                        }
                        parent = parent.parentElement;
                    }
                    
                    // 如果没有通过样式判断出角色，尝试通过元素结构判断
                    if (role === 'unknown') {
                        // 检查元素是否在特定的消息容器中
                        var current = element;
                        while (current && current !== document) {
                            if (current.className && (current.className.includes('my-') || current.className.includes('sender'))) {
                                role = 'seller';
                                break;
                            }
                            current = current.parentElement;
                        }
                        
                        if (role === 'unknown') {
                            // 默认为买家消息
                            role = 'buyer';
                        }
                    }
                    
                    if (!isMessage && content.length < 2) {
                        return null; // 不是有效消息
                    }
                    
                    return {
                        content: content,
                        role: role
                    };
                }
                return extractMessageData(arguments[0]);
            """, message_element)
            
            if not message_data or not message_data['content']:
                return None
            
            # 构建完整的消息数据结构
            result = {
                'user_nickname': self.current_user_nickname,
                'message_role': message_data['role'],
                'message_content': message_data['content'],
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'message_source': 'enhanced_crawler',
                'bargain_related': False,      # 是否与砍价相关
                'price_mentioned': False,      # 是否提及价格
                'price_value': None,           # 价格值
                'deal_related': False,         # 是否与成交相关
                'shipping_related': False,     # 是否与物流相关
                'shipping_cost': None,         # 物流费用
                'negotiation_phase': 'initial' # 议价阶段
            }

            # 分析消息内容，提取关键指标
            content = result['message_content'].lower()
            
            # 1. 检测砍价相关
            bargain_keywords = [
                '便宜', '少点', '再便宜', '能少', '砍价', '优惠', '打折', '降点', 
                '价格', '多少钱', '贵', '贵了', '太贵', '能便宜', '给个优惠', '优惠价'
            ]
            for keyword in bargain_keywords:
                if keyword in content:
                    result['bargain_related'] = True
                    self.conversation_context['bargain_attempts'] += 1
                    break

            # 2. 检测价格提及
            price_pattern = r'(\d+(?:\.\d{1,2})?)元|(\d+(?:\.\d{1,2})?)块|(\d+(?:\.\d{1,2})?)[￥$]'
            price_matches = re.findall(price_pattern, content)
            if price_matches:
                result['price_mentioned'] = True
                for match in price_matches:
                    actual_price = next((m for m in match if m), None)
                    if actual_price:
                        try:
                            price_value = float(actual_price)
                            result['price_value'] = price_value
                            self.conversation_context['price_mentions'].append({
                                'value': price_value,
                                'content': content,
                                'timestamp': result['timestamp']
                            })
                            break
                        except ValueError:
                            continue

            # 3. 检测成交相关
            deal_keywords = [
                '付款', '已付', '支付', '转账', '拍下', '下单', '成交', '买了', '要了',
                '发货', '快递', '包邮', '已发', '马上发', '确认收货', '收到货', '签收'
            ]
            for keyword in deal_keywords:
                if keyword in content:
                    result['deal_related'] = True
                    self.conversation_context['deal_keywords_found'].append({
                        'keyword': keyword,
                        'content': content,
                        'timestamp': result['timestamp']
                    })
                    
                    # 更新交易状态
                    if any(w in content for w in ['付款', '已付', '支付', '转账']):
                        self.conversation_context['transaction_status'] = 'paid'
                    elif any(w in content for w in ['发货', '已发', '快递']):
                        self.conversation_context['transaction_status'] = 'shipped'
                    elif any(w in content for w in ['确认收货', '收到货', '签收']):
                        self.conversation_context['transaction_status'] = 'completed'
                    break

            # 4. 检测物流相关
            shipping_keywords = [
                '快递', '物流', '包邮', '运费', '邮费', '发', '发货', '到付', '顺丰', 
                '邮政', '圆通', '中通', '申通', '韵达', '配送', '到货', '签收'
            ]
            for keyword in shipping_keywords:
                if keyword in content:
                    result['shipping_related'] = True
                    self.conversation_context['shipping_keywords_found'].append({
                        'keyword': keyword,
                        'content': content,
                        'timestamp': result['timestamp']
                    })
                    
                    # 尝试提取物流费用
                    cost_pattern = r'运费(\d+(?:\.\d{1,2})?)|邮费(\d+(?:\.\d{1,2})?)|快递费(\d+(?:\.\d{1,2})?)'
                    cost_matches = re.findall(cost_pattern, content)
                    if cost_matches:
                        for match in cost_matches[0]:
                            if match and match.strip():
                                try:
                                    shipping_cost = float(match.strip())
                                    result['shipping_cost'] = shipping_cost
                                    break
                                except ValueError:
                                    continue
                    break

            # 5. 确定议价阶段
            if result['bargain_related'] and result['price_mentioned']:
                result['negotiation_phase'] = 'active_negotiation'
            elif result['deal_related']:
                result['negotiation_phase'] = 'deal_conclusion'
            elif result['shipping_related']:
                result['negotiation_phase'] = 'shipping_discussion'
            elif any(content.count(kw) > 0 for kw in bargain_keywords):
                result['negotiation_phase'] = 'bargain_initiation'
            
            return result

        except Exception as e:
            logger.error(f"提取增强消息数据失败: {e}")
            return None

    def crawl_user_chat_enhanced(self, user_nickname: str, max_messages: int = 100) -> List[Dict]:
        """
        爬取用户聊天记录（增强版）

        Args:
            user_nickname: 用户昵称
            max_messages: 最大消息数量

        Returns:
            List[Dict]: 增强的聊天记录列表
        """
        try:
            logger.info(f"开始爬取用户 {user_nickname} 的增强聊天记录，最多 {max_messages} 条")
            
            # 重置对话上下文
            self._reset_conversation_context()
            self.current_user_nickname = user_nickname
            
            # 导航到聊天页面
            if not self.navigate_to_chat(user_nickname):
                logger.error(f"无法导航到用户 {user_nickname} 的聊天页面")
                return []
            
            # 等待聊天页面完全加载
            time.sleep(3)
            
            # 使用JavaScript方法提取消息，更准确
            all_messages = []
            messages_scraped = 0
            previous_height = 0
            no_new_messages_count = 0
            max_no_new_messages = 3  # 如果连续几次滚动都没有新消息，则停止
            
            while messages_scraped < max_messages and no_new_messages_count < max_no_new_messages:
                # 使用JavaScript提取当前可见的消息
                js_messages = self.page.run_js("""
                    function extractChatMessages() {
                        var messages = [];
                        
                        // 基于闲鱼实际页面结构提取消息
                        // 查找所有可能包含消息的元素
                        var selectors = [
                            'span[style*="color: rgb(31, 31, 31)"][style*="font-size: 14px"]',
                            'div[style*="color: rgb(31, 31, 31)"][style*="font-size: 14px"]',
                            '[class*="message"] span',
                            '[class*="msg"] span',
                            'div[style*="max-width: 41vmin"]',  // 闲鱼消息气泡
                            'div[style*="max-width: 300px"]'     // 另一种消息气泡
                        ];
                        
                        for (var i = 0; i < selectors.length; i++) {
                            var elements = document.querySelectorAll(selectors[i]);
                            for (var j = 0; j < elements.length; j++) {
                                var element = elements[j];
                                var text = element.textContent.trim();
                                
                                if (text && text.length > 1) {  // 有效消息内容
                                    // 判断消息角色
                                    var role = 'unknown';
                                    var rect = element.getBoundingClientRect();
                                    
                                    // 基于位置判断：左侧是买家，右侧是卖家
                                    if (rect.left < window.innerWidth / 2.5) {
                                        role = 'buyer';
                                    } else {
                                        role = 'seller';
                                    }
                                    
                                    // 双重检查：查看元素的父容器
                                    var parent = element.parentElement;
                                    while (parent) {
                                        var parentStyle = parent.getAttribute('style') || '';
                                        if (parentStyle.includes('justify-content: flex-end')) {
                                            role = 'seller';
                                            break;
                                        } else if (parentStyle.includes('justify-content: flex-start')) {
                                            role = 'buyer';
                                            break;
                                        }
                                        parent = parent.parentElement;
                                    }
                                    
                                    messages.push({
                                        content: text,
                                        role: role,
                                        element: element
                                    });
                                }
                            }
                        }
                        
                        return messages;
                    }
                    return extractChatMessages();
                """)
                
                # 处理提取到的消息
                initial_message_count = len(all_messages)
                
                for js_msg in js_messages:
                    content = js_msg.get('content', '')
                    role = js_msg.get('role', 'unknown')
                    
                    # 检查是否已经存在相同的消息
                    is_duplicate = any(msg['message_content'] == content and msg['message_role'] == role for msg in all_messages)
                    
                    if content and not is_duplicate:
                        # 创建消息数据结构
                        message_data = {
                            'user_nickname': self.current_user_nickname,
                            'message_role': role,
                            'message_content': content,
                            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                            'message_source': 'enhanced_crawler',
                            'bargain_related': False,
                            'price_mentioned': False,
                            'price_value': None,
                            'deal_related': False,
                            'shipping_related': False,
                            'shipping_cost': None,
                            'negotiation_phase': 'initial'
                        }
                        
                        # 使用增强的数据提取方法
                        enhanced_data = self.extract_enhanced_message_data_from_content(content, role)
                        if enhanced_data:
                            all_messages.append(enhanced_data)
                            messages_scraped += 1
                            
                            if messages_scraped >= max_messages:
                                break
                
                # 检查是否有新消息
                if len(all_messages) > initial_message_count:
                    no_new_messages_count = 0  # 有新消息，重置计数
                else:
                    no_new_messages_count += 1  # 没有新消息，增加计数
                
                if messages_scraped >= max_messages:
                    break
                
                # 滚动加载更多消息
                current_scroll_height = self.page.run_js("return document.body.scrollHeight;")
                self.page.scroll.to_bottom()
                time.sleep(2)  # 等待加载
                
                # 检查页面高度是否变化
                new_scroll_height = self.page.run_js("return document.body.scrollHeight;")
                if new_scroll_height == current_scroll_height:
                    logger.info("已到达页面底部，没有更多消息")
                    break
            
            logger.info(f"成功爬取 {len(all_messages)} 条增强聊天记录")
            return all_messages
            
        except Exception as e:
            logger.error(f"爬取增强聊天记录失败: {e}")
            import traceback
            traceback.print_exc()
            return []

    def extract_enhanced_message_data_from_content(self, content, role):
        """
        从内容和角色直接创建增强的消息数据

        Args:
            content: 消息内容
            role: 消息角色

        Returns:
            Dict: 包含增强数据的消息信息
        """
        try:
            # 基本消息数据
            message_data = {
                'user_nickname': self.current_user_nickname,
                'message_role': role,
                'message_content': content,
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'message_source': 'enhanced_crawler',
                'bargain_related': False,      # 是否与砍价相关
                'price_mentioned': False,      # 是否提及价格
                'price_value': None,           # 价格值
                'deal_related': False,         # 是否与成交相关
                'shipping_related': False,     # 是否与物流相关
                'shipping_cost': None,         # 物流费用
                'negotiation_phase': 'initial' # 议价阶段
            }

            # 分析消息内容，提取关键指标
            content_lower = content.lower()
            
            # 1. 检测砍价相关
            bargain_keywords = [
                '便宜', '少点', '再便宜', '能少', '砍价', '优惠', '打折', '降点', 
                '价格', '多少钱', '贵', '贵了', '太贵', '能便宜', '给个优惠', '优惠价'
            ]
            for keyword in bargain_keywords:
                if keyword in content_lower:
                    message_data['bargain_related'] = True
                    self.conversation_context['bargain_attempts'] += 1
                    break

            # 2. 检测价格提及
            price_pattern = r'(\d+(?:\.\d{1,2})?)元|(\d+(?:\.\d{1,2})?)块|(\d+(?:\.\d{1,2})?)[￥$]'
            price_matches = re.findall(price_pattern, content_lower)
            if price_matches:
                message_data['price_mentioned'] = True
                for match in price_matches:
                    actual_price = next((m for m in match if m), None)
                    if actual_price:
                        try:
                            price_value = float(actual_price)
                            message_data['price_value'] = price_value
                            self.conversation_context['price_mentions'].append({
                                'value': price_value,
                                'content': content_lower,
                                'timestamp': message_data['timestamp']
                            })
                            break
                        except ValueError:
                            continue

            # 3. 检测成交相关
            deal_keywords = [
                '付款', '已付', '支付', '转账', '拍下', '下单', '成交', '买了', '要了',
                '发货', '快递', '包邮', '已发', '马上发', '确认收货', '收到货', '签收'
            ]
            for keyword in deal_keywords:
                if keyword in content_lower:
                    message_data['deal_related'] = True
                    self.conversation_context['deal_keywords_found'].append({
                        'keyword': keyword,
                        'content': content_lower,
                        'timestamp': message_data['timestamp']
                    })
                    
                    # 更新交易状态
                    if any(w in content_lower for w in ['付款', '已付', '支付', '转账']):
                        self.conversation_context['transaction_status'] = 'paid'
                    elif any(w in content_lower for w in ['发货', '已发', '快递']):
                        self.conversation_context['transaction_status'] = 'shipped'
                    elif any(w in content_lower for w in ['确认收货', '收到货', '签收']):
                        self.conversation_context['transaction_status'] = 'completed'
                    break

            # 4. 检测物流相关
            shipping_keywords = [
                '快递', '物流', '包邮', '运费', '邮费', '发', '发货', '到付', '顺丰', 
                '邮政', '圆通', '中通', '申通', '韵达', '配送', '到货', '签收'
            ]
            for keyword in shipping_keywords:
                if keyword in content_lower:
                    message_data['shipping_related'] = True
                    self.conversation_context['shipping_keywords_found'].append({
                        'keyword': keyword,
                        'content': content_lower,
                        'timestamp': message_data['timestamp']
                    })
                    
                    # 尝试提取物流费用
                    cost_pattern = r'运费(\d+(?:\.\d{1,2})?)|邮费(\d+(?:\.\d{1,2})?)|快递费(\d+(?:\.\d{1,2})?)'
                    cost_matches = re.findall(cost_pattern, content_lower)
                    if cost_matches:
                        for match in cost_matches[0]:
                            if match and match.strip():
                                try:
                                    shipping_cost = float(match.strip())
                                    message_data['shipping_cost'] = shipping_cost
                                    break
                                except ValueError:
                                    continue
                    break

            # 5. 确定议价阶段
            if message_data['bargain_related'] and message_data['price_mentioned']:
                message_data['negotiation_phase'] = 'active_negotiation'
            elif message_data['deal_related']:
                message_data['negotiation_phase'] = 'deal_conclusion'
            elif message_data['shipping_related']:
                message_data['negotiation_phase'] = 'shipping_discussion'
            elif any(content_lower.count(kw) > 0 for kw in bargain_keywords):
                message_data['negotiation_phase'] = 'bargain_initiation'
            
            return message_data

        except Exception as e:
            logger.error(f"从内容提取增强消息数据失败: {e}")
            return None

    def _reset_conversation_context(self):
        """重置对话上下文"""
        self.conversation_context = {
            'bargain_attempts': 0,
            'price_mentions': [],
            'deal_keywords_found': [],
            'shipping_keywords_found': [],
            'negotiation_phases': [],
            'transaction_status': 'pending'
        }

    def save_enhanced_chat_data(self, messages: List[Dict], output_path: str):
        """
        保存增强的聊天数据到CSV文件

        Args:
            messages: 消息列表
            output_path: 输出路径
        """
        if not messages:
            logger.warning("没有消息数据需要保存")
            return
        
        # 确保输出目录存在
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        # 定义CSV列名
        fieldnames = [
            'user_nickname', 'message_role', 'message_content', 'timestamp', 
            'message_source', 'bargain_related', 'price_mentioned', 'price_value',
            'deal_related', 'shipping_related', 'shipping_cost', 'negotiation_phase'
        ]
        
        with open(output_path, 'w', newline='', encoding='utf-8-sig') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            for message in messages:
                writer.writerow(message)
        
        logger.info(f"增强聊天数据已保存到: {output_path}")

    def generate_analysis_summary(self, messages: List[Dict], summary_path: str = None):
        """
        生成分析摘要

        Args:
            messages: 消息列表
            summary_path: 摘要保存路径
        """
        if not summary_path:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            summary_path = f"analysis_summaries/chat_analysis_summary_{timestamp}.json"
        
        # 计算各种指标
        bargain_count = sum(1 for msg in messages if msg.get('bargain_related', False))
        deal_count = sum(1 for msg in messages if msg.get('deal_related', False))
        price_mention_count = sum(1 for msg in messages if msg.get('price_mentioned', False))
        shipping_count = sum(1 for msg in messages if msg.get('shipping_related', False))
        
        # 价格统计
        prices = [msg['price_value'] for msg in messages if msg.get('price_value') is not None]
        price_stats = {
            'count': len(prices),
            'min': min(prices) if prices else None,
            'max': max(prices) if prices else None,
            'avg': sum(prices) / len(prices) if prices else None
        } if prices else {'count': 0, 'min': None, 'max': None, 'avg': None}
        
        # 生成摘要
        summary = {
            'summary_generated_at': datetime.now().isoformat(),
            'total_messages': len(messages),
            'bargain_related_messages': bargain_count,
            'deal_related_messages': deal_count,
            'price_mentioned_messages': price_mention_count,
            'shipping_related_messages': shipping_count,
            'price_statistics': price_stats,
            'transaction_status': self.conversation_context.get('transaction_status', 'unknown'),
            'bargain_attempts': self.conversation_context.get('bargain_attempts', 0),
            'user_nickname': self.current_user_nickname
        }
        
        # 确保目录存在
        os.makedirs(os.path.dirname(summary_path), exist_ok=True)
        
        with open(summary_path, 'w', encoding='utf-8') as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)
        
        logger.info(f"分析摘要已保存到: {summary_path}")
        return summary

    def crawl_and_analyze_user(self, user_nickname: str, max_messages: int = 100, 
                              output_dir: str = "enhanced_chats") -> str:
        """
        完整的爬取和分析流程

        Args:
            user_nickname: 用户昵称
            max_messages: 最大消息数
            output_dir: 输出目录

        Returns:
            str: 保存的文件路径
        """
        logger.info(f"开始对用户 {user_nickname} 进行完整的爬取和分析")
        
        try:
            # 初始化浏览器
            self.init_browser()
            
            # 爬取增强聊天记录
            messages = self.crawl_user_chat_enhanced(user_nickname, max_messages)
            
            if not messages:
                logger.warning(f"未能爬取到用户 {user_nickname} 的聊天记录")
                return ""
            
            # 生成时间戳
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            # 保存增强聊天数据
            chat_file = os.path.join(
                output_dir, 
                f"enhanced_user_chat_{user_nickname}_{timestamp}.csv"
            )
            self.save_enhanced_chat_data(messages, chat_file)
            
            # 生成分析摘要
            summary_file = os.path.join(
                output_dir,
                f"analysis_summary_{user_nickname}_{timestamp}.json"
            )
            self.generate_analysis_summary(messages, summary_file)
            
            logger.info(f"用户 {user_nickname} 的爬取和分析已完成")
            logger.info(f"聊天数据: {chat_file}")
            logger.info(f"分析摘要: {summary_file}")
            
            # 关闭浏览器
            if self.page:
                self.page.quit()
            
            return chat_file
            
        except Exception as e:
            logger.error(f"爬取和分析用户 {user_nickname} 失败: {e}")
            if self.page:
                self.page.quit()
            return ""


def main():
    """主函数 - 命令行接口"""
    import argparse
    import time
    
    parser = argparse.ArgumentParser(description='增强版闲鱼聊天记录爬虫')
    parser.add_argument('--nickname', type=str, help='用户昵称（单个用户）')
    parser.add_argument('--nickname-file', type=str, help='用户昵称文件路径（批量用户）')
    parser.add_argument('--max-messages', type=int, default=100, help='最大消息数量')
    parser.add_argument('--output-dir', type=str, default='enhanced_chats', help='输出目录')
    parser.add_argument('--headless', action='store_true', help='无头模式')
    parser.add_argument('--delay', type=float, default=1.0, help='用户间延迟（秒）')
    
    args = parser.parse_args()
    
    crawler = EnhancedChatCrawler(headless=args.headless)
    
    if args.nickname:
        # 单个用户爬取
        result_file = crawler.crawl_and_analyze_user(
            user_nickname=args.nickname,
            max_messages=args.max_messages,
            output_dir=args.output_dir
        )
        
        if result_file:
            print(f"✅ 单个用户爬取完成！数据已保存到: {result_file}")
        else:
            print("❌ 单个用户爬取失败！请检查日志获取详细信息")
    
    elif args.nickname_file:
        # 批量用户爬取
        print(f"开始批量爬取用户聊天记录...")
        print(f"用户列表文件: {args.nickname_file}")
        
        # 读取用户昵称列表
        try:
            with open(args.nickname_file, 'r', encoding='utf-8') as f:
                nicknames = [line.strip() for line in f if line.strip()]
            
            print(f"找到 {len(nicknames)} 个用户需要爬取")
            
            success_count = 0
            for i, nickname in enumerate(nicknames, 1):
                print(f"\n[{i}/{len(nicknames)}] 正在爬取用户: {nickname}")
                
                result_file = crawler.crawl_and_analyze_user(
                    user_nickname=nickname,
                    max_messages=args.max_messages,
                    output_dir=args.output_dir
                )
                
                if result_file:
                    print(f"✅ 用户 {nickname} 爬取完成")
                    success_count += 1
                else:
                    print(f"❌ 用户 {nickname} 爬取失败")
                
                # 用户间延迟
                if i < len(nicknames):
                    print(f"等待 {args.delay} 秒后继续...")
                    time.sleep(args.delay)
            
            print(f"\n批量爬取完成！成功: {success_count}/{len(nicknames)}")
            
        except FileNotFoundError:
            print(f"❌ 用户昵称文件不存在: {args.nickname_file}")
        except Exception as e:
            print(f"❌ 批量爬取出错: {e}")
    
    else:
        print("请指定用户昵称(--nickname)或用户昵称文件(--nickname-file)")


if __name__ == "__main__":
    main()