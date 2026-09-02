#!/usr/bin/env python3
"""
分析闲鱼聊天界面HTML结构工具
用于获取准确的用户昵称元素结构
"""

import os
import time
from DrissionPage import ChromiumPage, ChromiumOptions
from loguru import logger

class ChatStructureAnalyzer:
    def __init__(self, headless=False):
        self.headless = headless
        self.page = None

    def init_browser(self):
        """初始化浏览器"""
        try:
            options = ChromiumOptions()
            if self.headless:
                options.headless()

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
            logger.info("正在打开闲鱼聊天页面...")
            self.page.get("https://www.goofish.com/im?spm=a21ybx.account.sidebar.2.6a3035ca2iyGly")
            self.page.wait.load_start()
            time.sleep(3)

            current_url = self.page.url
            logger.info(f"当前页面URL: {current_url}")

            if "login" in current_url or "signin" in current_url:
                logger.info("检测到需要登录，请手动完成登录操作...")
                print("请手动完成闲鱼登录操作，登录完成后按回车键继续...")
                input()
                logger.info("登录完成，继续执行...")

            # 等待聊天页面加载
            time.sleep(5)
            logger.info("成功进入闲鱼聊天页面")
            return True
        except Exception as e:
            logger.error(f"登录和导航失败: {e}")
            return False

    def analyze_chat_structure(self):
        """分析聊天界面结构"""
        try:
            logger.info("开始分析聊天界面结构...")

            # 1. 分析整个页面结构
            page_structure = self.page.run_js("""
                const structure = {
                    title: document.title,
                    url: window.location.href,
                    bodyClasses: document.body.className,
                    bodyId: document.body.id
                };

                // 查找所有可能的聊天列表容器
                const chatContainers = [];
                const selectors = [
                    '.rc-virtual-list-holder',
                    '.im-main--kaKv06s8',
                    '.conv-list-scroll--Bn4G27Nb',
                    '.rc-virtual-list',
                    '.user-order-container--gPgL3Azx',
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
                ];

                for (const selector of selectors) {
                    const elements = document.querySelectorAll(selector);
                    for (const element of elements) {
                        chatContainers.push({
                            selector: selector,
                            element: {
                                tagName: element.tagName,
                                className: element.className,
                                id: element.id,
                                textContent: element.textContent.trim().substring(0, 100),
                                childrenCount: element.children.length,
                                styles: element.getAttribute('style'),
                                outerHTML: element.outerHTML.substring(0, 500)
                            }
                        });
                    }
                }

                structure.chatContainers = chatContainers;

                // 查找所有可能的用户昵称元素
                const userElements = [];
                const userSelectors = [
                    'div[style*="overflow: hidden"][style*="text-overflow: ellipsis"][style*="white-space: nowrap"][style*="max-width"]',
                    'div[style*="max-width: 176px"]',
                    'div[style*="max-width: 102px"]',
                    '.user-name',
                    '.nickname',
                    '.username',
                    '[class*="name"]',
                    '[class*="user"]',
                    'span[class*="name"]',
                    'div[class*="name"]'
                ];

                for (const selector of userSelectors) {
                    const elements = document.querySelectorAll(selector);
                    for (const element of elements) {
                        const text = element.textContent.trim();
                        if (text && text.length > 1 && text.length < 30) {
                            userElements.push({
                                selector: selector,
                                text: text,
                                element: {
                                    tagName: element.tagName,
                                    className: element.className,
                                    id: element.id,
                                    styles: element.getAttribute('style'),
                                    parentHTML: element.parentElement ? element.parentElement.outerHTML.substring(0, 300) : '无父元素',
                                    outerHTML: element.outerHTML
                                }
                            });
                        }
                    }
                }

                structure.userElements = userElements;

                // 查找所有div元素（用于分析结构）
                const allDivs = document.querySelectorAll('div');
                const interestingDivs = [];

                for (const div of allDivs) {
                    const text = div.textContent.trim();
                    if (text && text.length > 1 && text.length < 30) {
                        const style = div.getAttribute('style') || '';
                        if (style.includes('overflow') || style.includes('ellipsis') || style.includes('nowrap')) {
                            interestingDivs.push({
                                text: text,
                                className: div.className,
                                styles: style,
                                outerHTML: div.outerHTML
                            });
                        }
                    }
                }

                structure.interestingDivs = interestingDivs;

                return structure;
            """)

            return page_structure

        except Exception as e:
            logger.error(f"分析聊天结构失败: {e}")
            return None

    def save_analysis_result(self, structure, output_file="chat_structure_analysis.json"):
        """保存分析结果"""
        try:
            import json
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(structure, f, ensure_ascii=False, indent=2)
            logger.info(f"分析结果已保存到: {output_file}")
            return True
        except Exception as e:
            logger.error(f"保存分析结果失败: {e}")
            return False

    def close_browser(self):
        """关闭浏览器"""
        if self.page:
            self.page.quit()
            logger.info("浏览器已关闭")

def main():
    """主函数"""
    print("=== 闲鱼聊天界面结构分析工具 ===")
    print("此工具将帮助您获取准确的HTML结构信息")
    print("=" * 50)

    analyzer = ChatStructureAnalyzer(headless=False)

    try:
        # 初始化浏览器
        if not analyzer.init_browser():
            print("浏览器初始化失败")
            return

        # 登录并导航
        print("正在登录并导航到闲鱼聊天页面...")
        if not analyzer.login_and_navigate():
            print("登录和导航失败")
            return

        # 分析结构
        print("正在分析聊天界面结构...")
        structure = analyzer.analyze_chat_structure()

        if structure:
            # 显示关键信息
            print("\n=== 分析结果摘要 ===")
            print(f"页面标题: {structure.get('title', 'N/A')}")
            print(f"页面URL: {structure.get('url', 'N/A')}")

            chat_containers = structure.get('chatContainers', [])
            print(f"找到 {len(chat_containers)} 个可能的聊天列表容器")

            user_elements = structure.get('userElements', [])
            print(f"找到 {len(user_elements)} 个可能的用户昵称元素")

            # 显示找到的用户昵称
            if user_elements:
                print("\n=== 找到的用户昵称 ===")
                for i, user in enumerate(user_elements, 1):
                    print(f"{i}. {user['text']} (选择器: {user['selector']})")

            # 保存详细结果
            analyzer.save_analysis_result(structure)

            print(f"\n详细分析结果已保存到: chat_structure_analysis.json")
            print("请查看该文件获取完整的HTML结构信息")

    except Exception as e:
        print(f"分析过程中出错: {e}")
    finally:
        analyzer.close_browser()

if __name__ == '__main__':
    main()