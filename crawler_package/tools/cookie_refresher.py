"""
Cookie刷新工具 - 自动获取和更新闲鱼登录cookies
"""

import asyncio
import os
import sys
from loguru import logger
from playwright.async_api import async_playwright


class CookieRefresher:
    """Cookie刷新器"""

    def __init__(self):
        self.browser = None
        self.context = None
        self.page = None

    async def check_environment(self):
        """检查环境是否满足要求"""
        try:
            import playwright
            return True
        except ImportError:
            logger.error("未安装Playwright，请运行: pip install playwright && playwright install chromium")
            return False

    async def get_cookies_after_login(self, keep_browser_open=False, auto_mode=False):
        """获取登录后的cookies"""
        try:
            async with async_playwright() as p:
                # 启动浏览器
                self.browser = await p.chromium.launch(
                    headless=False,
                    args=[
                        '--disable-blink-features=AutomationControlled',
                        '--disable-features=VizDisplayCompositor',
                        '--disable-background-timer-throttling',
                        '--disable-backgrounding-occluded-windows',
                        '--disable-renderer-backgrounding'
                    ]
                )

                # 创建上下文
                self.context = await self.browser.new_context(
                    viewport={'width': 1200, 'height': 800},
                    user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36'
                )

                # 创建页面
                self.page = await self.context.new_page()

                # 导航到闲鱼聊天页面
                logger.info("正在打开闲鱼聊天页面...")
                await self.page.goto("https://www.goofish.com/im?spm=a21ybx.account.sidebar.2.6a3035ca2iyGly")

                # 等待页面加载
                await self.page.wait_for_timeout(3000)

                # 显示当前页面URL
                current_url = self.page.url
                logger.info(f"当前页面URL: {current_url}")

                # 等待用户完成登录操作
                logger.info("请手动完成闲鱼登录操作...")
                print("登录完成后，请在终端中按回车键继续...")

                # 使用异步方式等待用户输入
                import asyncio

                async def wait_for_enter():
                    """等待用户按回车键"""
                    loop = asyncio.get_event_loop()

                    # 在单独的线程中运行input()，避免阻塞事件循环
                    def get_input():
                        try:
                            input()  # 等待用户按回车
                            return True
                        except EOFError:
                            return False

                    try:
                        result = await loop.run_in_executor(None, get_input)
                        if result:
                            logger.info("用户确认完成登录，继续获取cookies...")
                        return result
                    except Exception as e:
                        logger.error(f"等待用户输入时出错: {e}")
                        return False

                # 等待用户输入，设置超时
                try:
                    await asyncio.wait_for(wait_for_enter(), timeout=300)  # 5分钟超时
                except asyncio.TimeoutError:
                    logger.warning("等待超时，继续获取cookies...")

                # 等待页面稳定
                await self.page.wait_for_timeout(2000)

                # 获取cookies
                cookies = await self.context.cookies()
                logger.info(f"成功获取 {len(cookies)} 个cookies")

                # 调试：显示所有cookies名称
                cookie_names = [cookie['name'] for cookie in cookies]
                logger.debug(f"获取的cookies名称: {cookie_names}")

                # 格式化cookies字符串
                cookies_str = '; '.join([f"{cookie['name']}={cookie['value']}" for cookie in cookies])

                # 更新.env文件
                await self._update_env_file(cookies_str)

                if not keep_browser_open:
                    await self._cleanup()

                return cookies_str

        except Exception as e:
            logger.error(f"获取cookies失败: {e}")
            await self._cleanup()
            return None

    async def _update_env_file(self, cookies_str):
        """更新.env文件"""
        try:
            script_dir = os.path.dirname(os.path.abspath(__file__))
            env_path = os.path.join(script_dir, "..", ".env")

            if not os.path.exists(env_path):
                logger.warning(f".env文件不存在: {env_path}")
                return False

            # 读取现有内容
            with open(env_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()

            # 更新COOKIES_STR
            updated = False
            new_lines = []
            for line in lines:
                if line.startswith('COOKIES_STR='):
                    new_lines.append(f'COOKIES_STR={cookies_str}\n')
                    updated = True
                else:
                    new_lines.append(line)

            # 如果没找到COOKIES_STR，则添加
            if not updated:
                new_lines.append(f'COOKIES_STR={cookies_str}\n')

            # 写回文件
            with open(env_path, 'w', encoding='utf-8') as f:
                f.writelines(new_lines)

            logger.info("已成功更新.env文件中的COOKIES_STR")
            return True

        except Exception as e:
            logger.error(f"更新.env文件失败: {e}")
            return False

    async def update_cookies_manual(self, cookies_str):
        """手动更新cookies"""
        try:
            logger.info("正在手动更新cookies...")

            # 验证cookies格式
            if not cookies_str or len(cookies_str.strip()) == 0:
                logger.error("cookies字符串不能为空")
                return False

            # 更新.env文件
            success = await self._update_env_file(cookies_str)

            if success:
                logger.info("手动更新cookies成功")
                return True
            else:
                logger.error("手动更新cookies失败")
                return False

        except Exception as e:
            logger.error(f"手动更新cookies失败: {e}")
            return False

    async def _cleanup(self):
        """清理资源"""
        try:
            if self.page:
                await self.page.close()
            if self.context:
                await self.context.close()
            if self.browser:
                await self.browser.close()
        except Exception as e:
            logger.warning(f"清理资源时出错: {e}")


async def refresh_cookies_main(keep_open=False, auto_mode=False):
    """刷新cookies主函数"""
    refresher = CookieRefresher()

    # 检查环境
    if not await refresher.check_environment():
        return False

    # 获取cookies
    cookies = await refresher.get_cookies_after_login(
        keep_browser_open=keep_open,
        auto_mode=auto_mode
    )

    return cookies is not None


async def manual_update_cookies_main(cookies_str):
    """手动更新cookies主函数"""
    refresher = CookieRefresher()
    success = await refresher.update_cookies_manual(cookies_str)
    return success


def main():
    """命令行入口函数"""
    import argparse

    parser = argparse.ArgumentParser(description='闲鱼Cookie刷新工具')
    parser.add_argument('--keep-open', action='store_true', help='保持浏览器打开')
    parser.add_argument('--auto-mode', action='store_true', help='自动模式（不等待用户输入）')

    args = parser.parse_args()

    # 运行异步主函数
    success = asyncio.run(refresh_cookies_main(
        keep_open=args.keep_open,
        auto_mode=args.auto_mode
    ))

    if success:
        logger.info("Cookie刷新完成")
        sys.exit(0)
    else:
        logger.error("Cookie刷新失败")
        sys.exit(1)


if __name__ == '__main__':
    main()