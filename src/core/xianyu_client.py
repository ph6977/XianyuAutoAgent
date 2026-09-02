"""
闲鱼客户端 - 处理API调用和连接管理
"""

import time
import os
import sys
from loguru import logger
from dotenv import load_dotenv

import sys
import os
# 添加项目根目录到Python路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.utils.xianyu_utils import trans_cookies, generate_device_id
from src.utils.xianyu_apis import XianyuApis


class XianyuClient:
    """闲鱼客户端类"""

    def __init__(self, cookies_str):
        self.base_url = 'wss://wss-goofish.dingtalk.com/'
        self.cookies_str = cookies_str
        self.cookies = trans_cookies(cookies_str)
        self.xianyu = XianyuApis()
        self.xianyu.session.cookies.update(self.cookies)

        # 检查cookies是否有效
        if not self.cookies or 'unb' not in self.cookies:
            logger.warning("无效的cookies，请先运行 'python refresh_cookies.py' 获取cookies")
            self.myid = "unknown"
        else:
            self.myid = self.cookies['unb']

        logger.info(f"初始化卖家ID: {self.myid}")
        logger.info(f"Cookies中的unb字段: {self.cookies.get('unb', 'NOT_FOUND')}")
        self.device_id = generate_device_id(self.myid)

        # Token状态
        self.current_token = None
        self.last_token_refresh_time = 0

    def refresh_token(self):
        """刷新token"""
        try:
            logger.info("开始刷新token...")

            # 获取新token
            token_result = self.xianyu.get_token(self.device_id)
            logger.debug(f"get_token返回结果: {token_result}")

            # 检查API响应结构
            if isinstance(token_result, dict) and 'data' in token_result:
                if 'accessToken' in token_result['data']:
                    new_token = token_result['data']['accessToken']
                    self.current_token = new_token
                    self.last_token_refresh_time = time.time()
                    logger.info("Token刷新成功")
                    return new_token
                else:
                    logger.error(f"Token响应中缺少accessToken字段: {token_result}")
                    return None
            else:
                logger.error(f"Token API返回格式异常: {token_result}")
                return None

        except SystemExit:
            # 捕获get_token中的sys.exit(1)
            logger.error("Token获取失败，Cookie已失效，需要重新登录")
            return None
        except Exception as e:
            logger.error(f"Token刷新异常: {str(e)}")
            return None