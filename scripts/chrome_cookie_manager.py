#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Chrome Cookie管理器 - 单实例持久化方案
"""

import os
import json
import asyncio
import sys
import threading
import time
from typing import Optional, List, Dict, Any, Tuple, Union, Callable
from loguru import logger
import weakref
import traceback
from contextlib import asynccontextmanager

import requests
import websockets

try:
    from playwright.async_api import async_playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    logger.warning("Playwright未安装，Chrome自动获取cookies功能不可用")

# 自定义异常类
class ChromeCookieManagerError(Exception):
    """Chrome Cookie管理器基础异常"""
    pass

class BrowserConnectionError(ChromeCookieManagerError):
    """浏览器连接异常"""
    pass

class PageValidationError(ChromeCookieManagerError):
    """页面验证异常"""
    pass

class LoginDetectionError(ChromeCookieManagerError):
    """登录检测异常"""
    pass

class CookieExtractionError(ChromeCookieManagerError):
    """Cookie提取异常"""
    pass

class ConfigurationError(ChromeCookieManagerError):
    """配置异常"""
    pass

class ChromeCookieManager:
    """Chrome Cookie管理器 - 单实例模式，线程安全"""
    
    # 类变量，确保全局只有一个管理器实例
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        """单例模式，确保只有一个管理器实例"""
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._initialized = False
            return cls._instance
    
    def __init__(self) -> None:
        if hasattr(self, '_initialized') and self._initialized:
            return
        
        # 配置化参数
        self.config: Dict[str, Any] = {
            # URL配置
            'xianyu_url': "https://www.goofish.com/im?spm=a21ybx.home.sidebar.2.4c053da6snhTXP",
            
            # 超时配置（毫秒）
            'timeout': 30000,
            
            # 页面配置
            'viewport_width': 1920,
            'viewport_height': 1080,
            
            # User-Agent配置
            'user_agent': "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36",
            
            # Chrome路径配置 - 优先使用系统Chrome
            'chrome_paths': [
                r"C:\Users\Administrator\AppData\Local\Google\Chrome\Bin\chrome.exe",
                r"C:\Users\{}\AppData\Local\Google\Chrome\Bin\chrome.exe".format(os.getenv('USERNAME', '')),
                r"C:\Program Files\Google\Chrome\Application\chrome.exe",
                r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
                r"C:\Users\{}\AppData\Local\Google\Chrome\Application\chrome.exe".format(os.getenv('USERNAME', '')),
            ],
            
            # 登录检测配置
            'login_check': {
                'max_wait_time': 60,  # 最大等待时间（秒）
                'initial_wait_time': 5,  # 初始等待时间（秒）
                'check_interval': 5,  # 检查间隔（秒）
            }
        }
            
        self.chrome_path: Optional[str] = self._find_chrome_path()
        self.xianyu_url: str = self.config['xianyu_url']
        self.timeout: int = self.config['timeout']
        
        # Chrome实例 - 单实例
        self._playwright = None
        self._browser = None
        self._context = None
        self._page = None
        self._is_ready = False
        self._last_activity_time = time.time()
        
        # 统一的异步锁 - 简化锁机制避免死锁
        self._lock = asyncio.Lock()
        
        # 持久化监控
        self._monitor_thread = None
        self._monitor_running = False
        self._monitor_health_check_interval = 60  # 健康检查间隔（秒）
        self._monitor_last_health_check = time.time()
        
        # 调试计数器
        self._browser_creation_count = 0
        self._page_creation_count = 0
        
        # 重置计数器标志
        self._counters_reset = False
        
        # 保持模式标志
        self._keep_alive_mode = False
        
        # 线程隔离的Playwright实例管理
        self._thread_playwrights = {}  # {thread_name: playwright_instance}
        self._max_thread_instances = 5  # 最大线程实例数
        self._last_cleanup_time = time.time()  # 上次清理时间
        self._cleanup_interval = 300  # 清理间隔（5分钟）
        
        self._initialized = True
    
    def _is_page_valid(self) -> bool:
        """检查页面对象是否有效 - 同步检查版本"""
        if not self._page:
            logger.debug("[DEBUG] 页面对象为None")
            return False
        
        try:
            # 检查页面是否已关闭
            if self._page.is_closed():
                logger.debug("[DEBUG] 页面对象已关闭")
                return False
            
            # 检查页面上下文是否存在
            if not hasattr(self._page, 'context') or not self._page.context:
                logger.debug("[DEBUG] 页面上下文不存在")
                return False
            
            # 检查浏览器连接状态
            if not hasattr(self._page.context, 'browser') or not self._page.context.browser:
                logger.debug("[DEBUG] 页面浏览器对象不存在")
                return False
            
            if hasattr(self._page.context.browser, 'is_connected') and not self._page.context.browser.is_connected():
                logger.debug("[DEBUG] 页面浏览器连接已断开")
                return False
            
            # 同步检查页面URL（不使用异步方法）
            if hasattr(self._page, 'url'):
                url = self._page.url
                if not url:
                    logger.debug("[DEBUG] 页面URL为空")
                    return False
                logger.debug(f"[DEBUG] 页面URL: {url}")
            
            return True
            
        except Exception as e:
            logger.debug(f"[DEBUG] 页面对象验证失败: {e}")
            return False
    
    
    
    async def _cleanup_resources(self, force: bool = False):
        """清理所有资源（只清理当前实例创建的资源）"""
        # 检查保持模式
        if getattr(self, '_keep_alive_mode', False):
            if not force:
                logger.debug("[DEBUG] 保持模式开启，跳过资源清理")
                return
            logger.debug("[DEBUG] 强制清理覆盖保持模式")
            self._keep_alive_mode = False
        
        logger.info("开始清理当前Chromium实例资源...")
        
        try:
            # 清理页面
            if self._page:
                try:
                    if hasattr(self._page, 'is_closed') and not self._page.is_closed():
                        await self._page.close()
                        logger.debug("页面已关闭")
                except Exception as e:
                    logger.debug(f"关闭页面时发生异常: {e}")
                finally:
                    self._page = None
                    logger.info("页面对象已清理")
            
            # 清理浏览器上下文
            if hasattr(self, '_context') and self._context:
                try:
                    await self._context.close()
                    logger.debug("浏览器上下文已关闭")
                except Exception as e:
                    logger.debug(f"关闭浏览器上下文时发生异常: {e}")
                finally:
                    self._context = None
                    logger.info("浏览器上下文已清理")
            
            # 清理浏览器（只关闭当前实例创建的浏览器）
            if self._browser:
                try:
                    if hasattr(self._browser, 'is_connected'):
                        is_connected = self._browser.is_connected()
                        if is_connected:
                            # 只关闭当前浏览器创建的上下文
                            try:
                                contexts = self._browser.contexts
                                for context in contexts:
                                    await context.close()
                                logger.debug(f"已关闭 {len(contexts)} 个浏览器上下文")
                            except Exception as ctx_error:
                                logger.debug(f"关闭浏览器上下文时发生异常: {ctx_error}")
                            
                            # 关闭浏览器
                            await self._browser.close()
                            logger.debug("当前Chromium浏览器实例已关闭")
                        else:
                            logger.debug("浏览器已经断开连接")
                    else:
                        logger.debug("浏览器对象不支持连接检查")
                except Exception as e:
                    logger.debug(f"关闭浏览器时发生异常: {e}")
                finally:
                    self._browser = None
                    logger.info("当前浏览器对象已清理")
            
            # 不清理Playwright实例，让它可以重用
            # 这样可以避免创建多个Playwright实例
            if self._playwright:
                logger.debug("保留Playwright实例以供重用")
            
            # 重置状态
            self._is_ready = False
            logger.info("✓ 当前Chromium实例资源清理完成")
            
        except Exception as e:
            logger.error(f"清理资源时发生异常: {e}")
            # 即使清理失败，也确保对象被设置为None
            self._page = None
            self._context = None
            self._browser = None
            self._is_ready = False
    
    async def _check_login_via_cookies(self) -> bool:
        """通过Cookie检查登录状态 - 改进版本"""
        try:
            if not self._is_page_valid():
                logger.warning("页面对象无效，无法检查Cookie")
                return False
                
            cookies = await self._page.context.cookies()
            if not cookies:
                logger.warning("无法获取Cookie")
                return False
            
            cookie_names = [cookie.get('name', '') for cookie in cookies]
            
            # 核心字段 - 必须有 unb
            core_fields = ['unb']
            # 辅助字段 - 提高检测准确性
            auxiliary_fields = ['t', '_tb_token_', 'tracknick', '_m_h5_tk']
            
            # 检查核心字段
            has_core = all(field in cookie_names for field in core_fields)
            
            # 检查辅助字段（至少要有2个）
            has_auxiliary = sum(1 for field in auxiliary_fields if field in cookie_names) >= 2
            
            # Cookie数量检查（登录后通常有20+个字段）
            sufficient_count = len(cookies) >= 20
            
            # 验证unb字段值的有效性
            unb_value = None
            for cookie in cookies:
                if cookie.get('name') == 'unb':
                    unb_value = cookie.get('value', '')
                    break
            
            valid_unb = unb_value and len(unb_value) >= 3 and unb_value.isdigit()
            
            # 综合判断
            if has_core and valid_unb and has_auxiliary:
                found_aux = [field for field in auxiliary_fields if field in cookie_names]
                logger.info(f"✓ 通过Cookie检测到已登录状态 (unb={unb_value} + 辅助字段:{found_aux})")
                return True
            elif has_core and valid_unb and sufficient_count:
                logger.info(f"✓ 通过Cookie检测到已登录状态 (unb={unb_value} + 数量:{len(cookies)})")
                return True
            else:
                found_aux = [field for field in auxiliary_fields if field in cookie_names]
                logger.warning(f"Cookie验证不完整 - unb:{has_core}, 有效:{valid_unb}, 辅助:{found_aux}, 数量:{len(cookies)}")
                return False
                
        except Exception as e:
            logger.warning(f"检查Cookie失败: {e}")
            return False
    
    
    
    async def _check_login_via_content(self) -> bool:
        """通过页面内容检查登录状态"""
        if not self._is_page_valid():
            return False
        
        try:
            content = await self._page.content()
            
            # 更新的登录关键词 - 基于现代闲鱼/淘宝页面
            login_keywords = [
                "我的闲鱼",
                "我的",
                "消息",
                "发布",
                "个人中心",
                "设置",
                "退出",
                "我的订单",
                "我的收藏",
                "淘宝",
                "支付宝",
                "已登录",
                "闲鱼"
            ]
            
            found_keywords = []
            for keyword in login_keywords:
                if keyword in content:
                    found_keywords.append(keyword)
            
            if found_keywords:
                logger.info(f"✓ 页面内容包含登录关键词: {found_keywords}")
                return True
            else:
                logger.warning("页面内容中未找到登录关键词")
                return False
                
        except Exception as e:
            logger.warning(f"内容检查失败: {e}")
            return False
    
    async def _wait_for_login_with_retry(self) -> bool:
        """带重试机制的等待登录 - 增强验证版本"""
        # 从配置获取参数
        login_config = self.config['login_check']
        max_wait_time = login_config['max_wait_time']  # 最大等待时间（秒）
        initial_wait_time = login_config['initial_wait_time']  # 初始等待时间（秒）
        check_interval = login_config['check_interval']  # 检查间隔（秒）
        
        logger.info(f"开始等待用户登录，最大等待时间: {max_wait_time}秒")
        
        # 增加初始等待时间，确保页面完全加载
        await asyncio.sleep(initial_wait_time)
        
        waited_time = initial_wait_time
        
        while waited_time < max_wait_time:
            try:
                # 检查页面状态
                if not self._is_page_valid():
                    logger.warning("页面对象无效，尝试重建...")
                    await self._cleanup_resources(force=True)
                    if not await self.ensure_chrome_ready():
                        logger.error("无法重建Chrome实例")
                        return False
                
                # 执行多重登录检测
                detection_results = await self._comprehensive_login_check()
                
                # 分析检测结果
                if self._validate_login_detection(detection_results):
                    logger.info(f"✓ 通过综合检测确认登录状态 (等待 {waited_time} 秒)")
                    return True
                
                # 更新等待时间
                waited_time += check_interval
                logger.info(f"等待用户登录中... ({waited_time}/{max_wait_time}秒)")
                logger.debug(f"检测结果: {detection_results}")
                
                # 等待下次检查
                await asyncio.sleep(check_interval)
                
            except Exception as e:
                logger.error(f"登录检测异常: {e}")
                waited_time += check_interval
                if waited_time < max_wait_time:
                    await asyncio.sleep(check_interval)
        
        # 超时后的最后尝试
        logger.warning("等待超时，进行最后尝试...")
        detection_results = await self._comprehensive_login_check()
        if self._validate_login_detection(detection_results):
            logger.info("✓ 最后尝试通过综合检测确认登录状态")
            return True
        
        logger.error(f"等待 {max_wait_time} 秒后仍未检测到有效登录状态")
        return False
    
    def _find_chrome_path(self):
        """查找Chrome浏览器路径 - 优先使用系统Chrome"""
        chrome_paths = [
            r"C:\Users\Administrator\AppData\Local\Google\Chrome\Bin\chrome.exe",
            r"C:\Users\%USERNAME%\AppData\Local\Google\Chrome\Bin\chrome.exe",
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
            r"C:\Users\%USERNAME%\AppData\Local\Google\Chrome\Application\chrome.exe"
        ]
        
        for path in chrome_paths:
            expanded_path = os.path.expandvars(path)
            if os.path.exists(expanded_path):
                logger.info(f"✅ 找到系统Chrome浏览器: {expanded_path}")
                return expanded_path
        
        logger.error("❌ 未找到系统Chrome！自动获取cookies可能会被限流")
        logger.error("建议安装Chrome浏览器或使用手动脚本获取cookies")
        return None
    
    def format_cookies_for_env(self, cookies: List[Dict[str, Any]]) -> str:
        """将Cookie列表格式化为环境变量字符串"""
        cookie_parts: List[str] = []
        for cookie in cookies:
            name: str = cookie.get('name', '')
            value: str = cookie.get('value', '')
            if name and value:
                cookie_parts.append(f"{name}={value}")
        return "; ".join(cookie_parts)
    
    def update_env_file(self, cookies_str: str) -> bool:
        """更新.env文件中的COOKIES_STR"""
        try:
            env_file_path: str = ".env"
            
            # 读取现有内容
            if os.path.exists(env_file_path):
                with open(env_file_path, 'r', encoding='utf-8') as f:
                    lines: List[str] = f.readlines()
            else:
                lines: List[str] = []
            
            # 更新或添加COOKIES_STR
            updated: bool = False
            for i, line in enumerate(lines):
                if line.startswith("COOKIES_STR="):
                    lines[i] = f"COOKIES_STR={cookies_str}\n"
                    updated = True
                    break
            
            if not updated:
                lines.append(f"COOKIES_STR={cookies_str}\n")
            
            # 写入文件
            with open(env_file_path, 'w', encoding='utf-8') as f:
                f.writelines(lines)
            
            logger.info("成功更新.env文件中的COOKIES_STR")
            return True
            
        except Exception as e:
            logger.error(f"更新.env文件时发生异常: {e}")
            return False
    
    

    def _is_browser_valid(self) -> bool:
        """检查浏览器对象是否有效"""
        try:
            browser = self._safe_get_browser()
            if not browser:
                logger.debug("[DEBUG] 浏览器对象为None")
                return False
            
            # 检查浏览器是否已关闭
            try:
                if hasattr(browser, 'is_connected') and not browser.is_connected():
                    logger.warning("[WARNING] 浏览器连接已断开")
                    return False
            except Exception as e:
                logger.debug(f"[DEBUG] 检查浏览器连接状态失败: {e}")
                return False
            
            # 尝试获取浏览器进程信息
            try:
                if hasattr(browser, '_process') and browser._process:
                    if not browser._process.is_running():
                        logger.warning("[WARNING] 浏览器进程已停止")
                        return False
            except Exception as e:
                logger.debug(f"[DEBUG] 检查浏览器进程状态失败: {e}")
                return False
            
            # 尝试获取浏览器上下文列表来验证连接
            try:
                contexts = browser.contexts
                logger.debug(f"[DEBUG] 浏览器上下文数量: {len(contexts)}")
                return True
            except Exception as e:
                logger.warning(f"[WARNING] 无法获取浏览器上下文: {e}")
                return False
                
        except Exception as e:
            logger.debug(f"[DEBUG] 浏览器对象验证失败: {e}")
            return False
    
    def _is_browser_truly_invalid(self) -> bool:
        """更严格的浏览器无效性检查，避免误判"""
        browser = self._safe_get_browser()
        if not browser:
            return True
        
        try:
            # 多重检查确保浏览器真的无效
            checks = [
                not browser.is_connected(),
                hasattr(browser, '_process') and browser._process and not browser._process.is_running()
            ]
            
            # 只有所有检查都通过才认为浏览器无效
            if all(checks):
                logger.warning("[WARNING] 浏览器确实已失效，需要重建")
                return True
            
            return False
        except Exception as e:
            logger.debug(f"[DEBUG] 浏览器状态检查异常: {e}")
            # 在检查异常时，保守处理，不认为浏览器无效
            return False
    
    

    async def ensure_chrome_ready(self):
        """确保Chromium实例已准备就绪并始终保持在前端运行 - 重构版本"""
        current_thread = threading.current_thread().name
        logger.debug(f"[DEBUG] 线程 {current_thread} 开始确保Chromium就绪")
        
        # 确保当前线程有异步上下文
        self._ensure_async_context()
        
        # 首先检查页面是否已经就绪
        if await self._check_page_ready():
            return True
        
        # 检查Playwright是否可用
        if not PLAYWRIGHT_AVAILABLE:
            logger.error("Playwright未安装，无法使用Chromium自动获取cookies功能")
            return False
        
        # 浏览器重建检测
        if await self._should_rebuild_browser():
            logger.info(f"[INFO] {current_thread} 检测到需要创建新的Chromium实例...")
            await self._create_new_browser_instance(current_thread)
        
        # 确保浏览器和页面都有效
        return await self._validate_and_prepare_page(current_thread)
    
    async def _check_page_ready(self) -> bool:
        """检查页面是否已经就绪"""
        page = self._safe_get_page()
        if page and not page.is_closed():
            try:
                # 检查页面连接状态
                if hasattr(page, '_context') and page._context:
                    # 将浏览器窗口带到前台
                    await page.bring_to_front()
                    # 最大化窗口确保在前端
                    await page.evaluate("window.moveTo(0, 0); window.resizeTo(screen.width, screen.height);")
                    logger.debug(f"[DEBUG] Chromium浏览器已置于前台并最大化")
                    self._is_ready = True
                    return True
                else:
                    logger.warning(f"[WARNING] 页面上下文无效，无法置于前台")
                    self._is_ready = False
                    return False
            except Exception as e:
                logger.warning(f"[WARNING] 将Chromium置于前台失败: {e}")
                self._is_ready = False
                return False
        else:
            logger.warning(f"[WARNING] 页面对象无效或已关闭")
            self._is_ready = False
            return False
    
    async def _should_rebuild_browser(self) -> bool:
        """检查是否需要重建浏览器"""
        browser = self._safe_get_browser()
        
        if not browser:
            logger.debug("[DEBUG] 浏览器对象不存在，需要创建")
            return True
        
        if not browser.is_connected():
            logger.debug("[DEBUG] 浏览器连接已断开，需要重建")
            return True
            
        return False
    
    async def _create_new_browser_instance(self, thread_name: str):
        """创建新的浏览器实例"""
        # 清理旧资源
        await self._cleanup_resources(force=True)
        await asyncio.sleep(1)  # 等待资源完全清理
        
        # 创建新的Playwright实例
        playwright = self._safe_get_playwright()
        if not playwright or not hasattr(playwright, 'stop'):
            logger.info(f"[INFO] {thread_name} 创建新的Playwright实例")
            playwright = await async_playwright().start()
            self._safe_set_playwright(playwright)
        
        # 在异步锁内进行所有浏览器操作
        async with self._async_lock():
            # 获取线程隔离的Playwright实例
            playwright = await self._get_thread_isolated_playwright()
            if not playwright:
                logger.error("[ERROR] 无法创建有效的Playwright实例")
                return False
            
            # 启动浏览器
            browser = await self._launch_chromium_browser(playwright, thread_name)
            if not browser:
                return False
            
            # 创建页面
            page = await self._create_browser_page(browser, thread_name)
            if not page:
                return False
            
            # 导航到闲鱼页面
            if not await self._navigate_to_xianyu_page(page, thread_name):
                return False
            
            logger.info(f"[INFO] ✓ {thread_name} 的Chromium实例已准备就绪并保持在前端最大化显示")
            self._is_ready = True
            self._last_activity_time = time.time()
            return True
    
    async def _launch_chromium_browser(self, playwright, thread_name: str):
        """启动Chromium浏览器"""
        # 定义启动选项
        launch_options = self._get_chrome_launch_options()
        
        chrome_info = self._get_chrome_info()
        logger.info(f"[INFO] {thread_name} {chrome_info}")
        self._browser_creation_count += 1
        logger.info(f"[DEBUG] 浏览器创建计数: {self._browser_creation_count}")
        
        # 验证Playwright对象有效性
        if not hasattr(playwright, 'chromium'):
            logger.error("[ERROR] Playwright对象缺少chromium属性")
            return None
        
        browser = await playwright.chromium.launch(**launch_options)
        
        # 立即验证浏览器对象
        if not browser:
            logger.error("[ERROR] 浏览器启动失败，返回None")
            return None
        
        # 立即验证浏览器是否真的启动成功
        if not browser.is_connected():
            logger.error("[ERROR] 浏览器启动后立即失效")
            return None
        
        self._safe_set_browser(browser)
        logger.info(f"[INFO] ✓ {thread_name} 的Chromium浏览器已启动并保持在前端")
        
        # 等待浏览器完全启动
        await asyncio.sleep(2)
        
        # 验证浏览器连接状态
        if not browser.is_connected():
            logger.error("[ERROR] 浏览器启动后立即失效")
            return None
        
        return browser
    
    def _get_chrome_launch_options(self) -> dict:
        """获取Chrome启动选项"""
        return {
            "headless": False,  # 确保不是无头模式，必须在前端显示
            "args": [
                "--no-first-run",
                "--no-default-browser-check",
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--disable-extensions",
                "--disable-plugins",
                "--disable-background-timer-throttling",
                "--disable-renderer-backgrounding",
                "--start-maximized",  # 启动时最大化
                "--disable-backgrounding-occluded-windows",  # 防止后台窗口被优化
                "--disable-features=TranslateUI",  # 禁用翻译UI
                "--disable-ipc-flooding-protection",  # 禁用IPC洪水保护
                "--disable-web-security",  # 禁用Web安全检查
                "--disable-features=VizDisplayCompositor",  # 禁用显示合成器
                "--always-on-top",  # 始终保持在顶层
                "--window-position=0,0",  # 窗口位置在左上角
                "--force-device-scale-factor=1",  # 强制设备缩放因子
                "--disable-infobars",  # 禁用信息栏
                "--disable-notifications",  # 禁用通知
                "--disable-popup-blocking",  # 禁用弹出窗口阻止
                "--ignore-certificate-errors",  # 忽略证书错误
                "--allow-running-insecure-content",  # 允许运行不安全内容
                "--disable-web-security",  # 禁用Web安全
                "--disable-features=IsolateOrigins,site-per-process"  # 禁用进程隔离
            ]
        }
    
    def _get_chrome_info(self) -> str:
        """获取Chrome启动信息"""
        if self.chrome_path:
            return f"启动系统Chrome: {self.chrome_path}"
        else:
            return "启动Playwright自带的Chromium - 保持前端显示"
    
    async def _create_browser_page(self, browser, thread_name: str):
        """创建新页面"""
        logger.info(f"[INFO] {thread_name} 创建新页面...")
        self._page_creation_count += 1
        logger.info(f"[DEBUG] 页面创建计数: {self._page_creation_count}")
        
        page = await browser.new_page()
        
        # 验证页面对象
        if not page:
            logger.error("[ERROR] 页面创建失败，返回None")
            return None
        
        self._safe_set_page(page)
        logger.info(f"[INFO] ✓ {thread_name} 的新页面创建成功")
        
        # 设置页面属性
        await page.set_extra_http_headers({
            "User-Agent": self.config['user_agent'],
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8"
        })
        await page.set_viewport_size({
            "width": self.config['viewport_width'], 
            "height": self.config['viewport_height']
        })
        
        # 确保页面在前端并最大化
        await page.bring_to_front()
        await page.evaluate("window.moveTo(0, 0); window.resizeTo(screen.width, screen.height);")
        
        return page
    
    async def _navigate_to_xianyu_page(self, page, thread_name: str) -> bool:
        """导航到闲鱼聊天页面"""
        logger.info(f"[INFO] {thread_name} 正在导航到闲鱼聊天页面: {self.xianyu_url}")
        logger.info(f"[DEBUG] 目标URL: {self.xianyu_url}")
        
        try:
            # 导航到聊天页面，等待网络空闲
            response = await page.goto(self.xianyu_url, wait_until="networkidle", timeout=self.timeout)
            logger.info(f"[DEBUG] 页面导航完成，状态码: {response.status if response else '未知'}")
            
            # 检查是否成功加载聊天页面
            if response and response.status in [200, 302]:
                logger.info(f"[INFO] {thread_name} 聊天页面加载成功")
                
                # 等待聊天页面元素加载完成
                try:
                    # 等闲鱼聊天页面可能的元素
                    selectors = [
                        '.conversation-list', 
                        '.chat-container', 
                        '.im-container',
                        '.session-list',
                        '[class*="conversation"]',
                        '[class*="chat"]',
                        '[class*="session"]',
                        '[class*="message"]',
                        '.idle-fish-im',
                        '.goofish-im',
                        '[data-testid*="chat"]',
                        '[data-testid*="conversation"]'
                    ]
                    
                    element_found = False
                    for selector in selectors:
                        try:
                            await page.wait_for_selector(selector, timeout=1000)
                            logger.info(f"[INFO] {thread_name} 检测到聊天界面元素: {selector}")
                            element_found = True
                            break
                        except:
                            continue
                    
                    if not element_found:
                        # 如果没有找到特定元素，检查是否在正确的域名
                        current_url = page.url
                        if 'goofish.com' in current_url or '2.taobao.com' in current_url:
                            logger.info(f"[INFO] {thread_name} 检测到闲鱼域名，页面可能已加载: {current_url}")
                            element_found = True
                        else:
                            logger.warning(f"[WARNING] {thread_name} 页面可能未成功加载到闲鱼，当前URL: {current_url}")
                            return False
                    
                    return True
                    
                except Exception as e:
                    logger.warning(f"[WARNING] {thread_name} 等待聊天界面元素失败: {e}")
                    current_url = page.url
                    logger.info(f"[INFO] {thread_name} 当前页面URL: {current_url}")
                    return True  # 页面已加载，只是元素可能不同
            
            else:
                logger.error(f"[ERROR] {thread_name} 页面加载失败，状态码: {response.status if response else '未知'}")
                current_url = page.url
                logger.error(f"[ERROR] {thread_name} 当前URL: {current_url}")
                return False
                
        except Exception as e:
            logger.error(f"[ERROR] {thread_name} 导航到聊天页面失败: {e}")
            if hasattr(e, 'message'):
                logger.error(f"[ERROR] {thread_name} 错误详情: {e.message}")
            return False
    
    async def _validate_and_prepare_page(self, thread_name: str) -> bool:
        """验证并准备页面"""
        # 检查页面是否存在
        page = self._safe_get_page()
        if not page:
            logger.error(f"[ERROR] {thread_name} 页面对象不存在")
            return False
        
        # 检查页面状态
        if page.is_closed():
            logger.error(f"[ERROR] {thread_name} 页面已关闭")
            return False
        
        # 检查页面连接
        if not self._is_page_valid():
            logger.error(f"[ERROR] {thread_name} 页面连接无效")
            return False
        
        # 确保页面在前端显示
        try:
            await page.bring_to_front()
            # 最大化窗口
            await page.evaluate("window.moveTo(0, 0); window.resizeTo(screen.width, screen.height);")
            logger.debug(f"[DEBUG] {thread_name} 页面已置于前端并最大化")
        except Exception as e:
            logger.warning(f"[WARNING] {thread_name} 将页面置于前端失败: {e}")
            # 即使失败也继续执行
        
        # 更新就绪状态
        self._is_ready = True
        self._last_activity_time = time.time()
        return True
    
    def _safe_get_playwright(self):
        """安全获取Playwright实例"""
        return getattr(self, '_playwright', None)
    
    def _safe_set_playwright(self, playwright):
        """安全设置Playwright实例"""
        self._playwright = playwright
    
    def _safe_get_browser(self):
        """安全获取浏览器实例"""
        return getattr(self, '_browser', None)
    
    def _safe_set_browser(self, browser):
        """安全设置浏览器实例"""
        self._browser = browser
    
    def _safe_get_context(self):
        """安全获取页面上下文实例"""
        if hasattr(self, '_context'):
            return self._context
        return None
    
    def _safe_set_context(self, context):
        """安全设置页面上下文实例"""
        self._context = context
    
    def _safe_get_page(self):
        """安全获取页面实例"""
        return getattr(self, '_page', None)
    
    def _safe_set_page(self, page):
        """安全设置页面实例"""
        self._page = page

    def _ensure_async_context(self):
        """确保当前线程有异步上下文"""
        try:
            asyncio.get_event_loop()
        except RuntimeError:
            # 如果当前线程没有事件循环，创建一个
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

    def _async_lock(self):
        """获取异步锁"""
        return getattr(self, '_lock', asyncio.Lock())

    async def _get_thread_isolated_playwright(self):
        """获取线程隔离的Playwright实例"""
        thread_name = threading.current_thread().name
        if thread_name not in self._thread_playwrights:
            # 清理旧实例以避免内存泄漏
            if len(self._thread_playwrights) >= self._max_thread_instances:
                oldest_thread = min(self._thread_playwrights.keys(), key=lambda x: x)
                try:
                    playwright_to_stop = self._thread_playwrights[oldest_thread]
                    if hasattr(playwright_to_stop, 'stop'):
                        await playwright_to_stop.stop()
                except Exception as e:
                    logger.warning(f"停止旧Playwright实例失败: {e}")
                del self._thread_playwrights[oldest_thread]
            
            # 创建新的Playwright实例
            playwright = await async_playwright().start()
            self._thread_playwrights[thread_name] = playwright
            logger.info(f"为线程 {thread_name} 创建了新的Playwright实例")
        return self._thread_playwrights[thread_name]

    async def _comprehensive_login_check(self) -> Dict[str, bool]:
        """执行综合登录检测"""
        results = {
            'cookies': await self._check_login_via_cookies(),
            'content': await self._check_login_via_content()
        }
        return results

    def _validate_login_detection(self, detection_results: Dict[str, bool]) -> bool:
        """验证登录检测结果"""
        # 至少一个检测方法成功
        return detection_results.get('cookies', False) or detection_results.get('content', False)

    async def get_cookies_from_debug_port(self, debug_port_url: str = "http://127.0.0.1:9222"):
        """从已打开的Chrome调试端口获取cookies"""
        try:
            # 获取浏览器标签页列表
            tabs_url = f"{debug_port_url}/json"
            response = requests.get(tabs_url, timeout=10)
            tabs = response.json()
            
            # 查找闲鱼相关的标签页
            xianyu_tabs = [tab for tab in tabs if 'goofish.com' in tab.get('url', '') or 'xianyu' in tab.get('url', '')]
            
            if not xianyu_tabs:
                logger.warning("未找到闲鱼相关的浏览器标签页")
                # 尝试所有标签页
                xianyu_tabs = tabs
            
            cookies = []
            for tab in xianyu_tabs:
                # 获取单个标签页的详细信息
                tab_url = tab['webSocketDebuggerUrl']
                # 使用Chromium的调试协议获取cookies
                # 由于直接通过调试协议获取cookies比较复杂，我们使用Playwright来处理
                if await self.ensure_chrome_ready():
                    page = self._safe_get_page()
                    if page:
                        # 获取当前页面的cookies
                        cookies = await page.context.cookies()
                        logger.info(f"从Chrome调试端口获取到 {len(cookies)} 个cookies")
                        return cookies
                        
        except Exception as e:
            logger.error(f"从Chrome调试端口获取cookies失败: {e}")
            return []
        return []

    async def get_cookies_keep_browser_open(self) -> List[Dict[str, Any]]:
        """获取cookies并保持浏览器持续打开，支持持续获取"""
        # 设置保持模式
        self._keep_alive_mode = True
        logger.info("Chrome Cookie管理器启动 - 保持模式开启，浏览器将持续保持打开")
        logger.info("请在浏览器中完成登录操作，系统将自动检测登录状态并获取cookies")
        logger.info("浏览器窗口将始终保持在前端最大化显示")
        logger.info("要停止获取，请中断程序运行 (Ctrl+C)")
        
        try:
            # 确保Chrome实例就绪
            if not await self.ensure_chrome_ready():
                logger.error("无法启动Chrome实例，获取cookies失败")
                return []
            
            # 等待登录
            logger.info("等待用户登录操作...")
            if not await self._wait_for_login_with_retry():
                logger.error("等待登录超时，获取cookies失败")
                return []
            
            # 登录成功后，获取cookies
            page = self._safe_get_page()
            if not page:
                logger.error("页面对象无效，无法获取cookies")
                return []
            
            cookies = await page.context.cookies()
            logger.info(f"成功获取 {len(cookies)} 个cookies")
            
            # 检查是否包含必要的登录字段
            cookie_names = [cookie['name'] for cookie in cookies]
            if 'unb' not in cookie_names:
                logger.warning("获取的cookies中缺少unb字段，可能未正确登录")
                return []
            else:
                logger.info("✓ cookies包含unb字段，登录状态有效")
                return cookies

        except KeyboardInterrupt:
            logger.info("用户中断操作，保持浏览器打开状态...")
            return []
        except Exception as e:
            logger.error(f"获取cookies时发生异常: {e}")
            logger.error(f"异常详情: {traceback.format_exc()}")
            return []

    async def get_cookies(self) -> List[Dict[str, Any]]:
        """获取cookies - 保持浏览器打开版本"""
        return await self.get_cookies_keep_browser_open()

    def stop_monitoring(self):
        """停止监控并清理资源"""
        if self._monitor_running:
            self._monitor_running = False
            if self._monitor_thread and self._monitor_thread.is_alive():
                self._monitor_thread.join(timeout=5)
            logger.info("Chrome Cookie管理器监控已停止")

    def __del__(self):
        """析构函数，确保资源清理"""
        try:
            # 尝试获取当前事件循环
            loop = None
            try:
                loop = asyncio.get_running_loop()
                # 如果在事件循环中，调度清理任务
                if loop.is_running():
                    # 不直接await，而是创建任务
                    pass
            except RuntimeError:
                # 没有运行中的事件循环，直接清理
                pass

            # 停止监控
            self.stop_monitoring()
        except Exception as e:
            logger.error(f"清理Chrome Cookie管理器资源时发生异常: {e}")


# 非异步辅助函数，用于简化使用
def get_chrome_cookies() -> Optional[str]:
    """便捷函数：获取Chrome cookies并返回字符串格式"""
    async def _get_cookies_async():
        manager = ChromeCookieManager()
        cookies = await manager.get_cookies_keep_browser_open()
        if cookies:
            return manager.format_cookies_for_env(cookies)
        return None

    # 获取或创建事件循环
    try:
        loop = asyncio.get_running_loop()
        logger.warning("当前已在事件循环中，无法同步运行Chrome Cookie获取")
        return None
    except RuntimeError:
        # 没有运行中的事件循环，可以安全创建
        loop = asyncio.new_event_loop()
        asyncio.set_loop(loop)
        try:
            cookies_str = loop.run_until_complete(_get_cookies_async())
            return cookies_str
        finally:
            # 不关闭浏览器，保持打开状态
            pass

if __name__ == "__main__":
    # 命令行使用示例
    import argparse

    parser = argparse.ArgumentParser(description='Chrome Cookie管理器')
    parser.add_argument('--action', choices=['get', 'test'], default='get', help='操作类型')
    parser.add_argument('--keep-open', action='store_true', help='保持浏览器打开')
    args = parser.parse_args()

    if args.action == 'get':
        async def main():
            manager = ChromeCookieManager()
            if args.keep_open:
                cookies = await manager.get_cookies_keep_browser_open()
            else:
                cookies = await manager.get_cookies()
            
            if cookies:
                cookies_str = manager.format_cookies_for_env(cookies)
                print(f"获取到的Cookies:")
                print(cookies_str)
                
                # 询问是否更新环境变量
                response = input("是否更新.env文件中的COOKIES_STR? (y/n): ")
                if response.lower() == 'y':
                    success = manager.update_env_file(cookies_str)
                    if success:
                        print("✓ .env文件已更新")
                    else:
                        print("✗ .env文件更新失败")
            else:
                print("未能获取到有效的cookies")
                print("请确保：")
                print("1. 已安装Chrome浏览器")
                print("2. Playwright已正确安装: pip install playwright")
                print("3. 已安装浏览器驱动: playwright install")
                print("4. 在浏览器中成功登录闲鱼账号")

        # 运行异步主函数
        try:
            asyncio.run(main())
        except KeyboardInterrupt:
            print("\n用户中断操作")
        except Exception as e:
            print(f"运行出错: {e}")
            import traceback
            traceback.print_exc()
    elif args.action == 'test':
        print("Chrome Cookie管理器测试")
        print(f"Playwright可用: {PLAYWRIGHT_AVAILABLE}")
        manager = ChromeCookieManager()
        print(f"Chrome路径: {manager.chrome_path}")
