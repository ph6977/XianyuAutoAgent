"""
闲鱼API封装 - 处理闲鱼平台的API调用
"""

import time
import os
import re
import sys
import requests
from loguru import logger
from src.utils.xianyu_utils import generate_sign


class XianyuApis:
    """闲鱼API类"""

    def __init__(self):
        self.url = 'https://h5api.m.goofish.com/h5/mtop.taobao.idlemessage.pc.login.token/1.0/'
        self.session = requests.Session()
        self.session.headers.update({
            'accept': 'application/json',
            'accept-language': 'zh-CN,zh;q=0.9',
            'cache-control': 'no-cache',
            'origin': 'https://www.goofish.com',
            'pragma': 'no-cache',
            'priority': 'u=1, i',
            'referer': 'https://www.goofish.com/',
            'sec-ch-ua': '"Not(A:Brand";v="99", "Google Chrome";v="133", "Chromium";v="133"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-site',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36',
        })

    def clear_duplicate_cookies(self):
        """清理重复的cookies"""
        new_jar = requests.cookies.RequestsCookieJar()
        added_cookies = set()

        cookie_list = list(self.session.cookies)
        cookie_list.reverse()

        for cookie in cookie_list:
            if cookie.name not in added_cookies:
                new_jar.set_cookie(cookie)
                added_cookies.add(cookie.name)

        self.session.cookies = new_jar
        self.update_env_cookies()

    def update_env_cookies(self):
        """更新.env文件中的COOKIES_STR"""
        try:
            cookie_str = '; '.join([f"{cookie.name}={cookie.value}" for cookie in self.session.cookies])

            # 获取当前文件所在目录
            script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # 向上两级目录到项目根目录
            env_path = os.path.join(script_dir, ".env")
            if not os.path.exists(env_path):
                logger.warning(f".env文件不存在: {env_path}，无法更新COOKIES_STR")
                return

            with open(env_path, 'r', encoding='utf-8') as f:
                env_content = f.read()

            if 'COOKIES_STR=' in env_content:
                new_env_content = re.sub(
                    r'COOKIES_STR=.*',
                    f'COOKIES_STR={cookie_str}',
                    env_content
                )

                with open(env_path, 'w', encoding='utf-8') as f:
                    f.write(new_env_content)

                logger.debug("已更新.env文件中的COOKIES_STR")
            else:
                logger.warning(".env文件中未找到COOKIES_STR配置项")
        except Exception as e:
            logger.warning(f"更新.env文件失败: {str(e)}")

    def hasLogin(self, retry_count=0):
        """调用hasLogin.do接口进行登录状态检查"""
        if retry_count >= 2:
            logger.error("Login检查失败，重试次数过多")
            return False

        try:
            url = 'https://passport.goofish.com/newlogin/hasLogin.do'
            params = {
                'appName': 'xianyu',
                'fromSite': '77'
            }
            data = {
                'hid': self.session.cookies.get('unb', ''),
                'ltl': 'true',
                'appName': 'xianyu',
                'appEntrance': 'web',
                '_csrf_token': self.session.cookies.get('XSRF-TOKEN', ''),
                'umidToken': '',
                'hsiz': self.session.cookies.get('cookie2', ''),
                'bizParams': 'taobaoBizLoginFrom=web',
                'mainPage': 'false',
                'isMobile': 'false',
                'lang': 'zh_CN',
                'returnUrl': '',
                'fromSite': '77',
                'isIframe': 'true',
                'documentReferer': 'https://www.goofish.com/',
                'defaultView': 'hasLogin',
                'umidTag': 'SERVER',
                'deviceId': self.session.cookies.get('cna', '')
            }

            response = self.session.post(url, params=params, data=data)
            res_json = response.json()

            # 检查API调用是否成功
            if res_json.get('content', {}).get('success'):
                logger.debug("hasLogin API调用成功")
                self.clear_duplicate_cookies()
                return True
            else:
                logger.warning(f"hasLogin API调用失败: {res_json}")
                time.sleep(0.5)
                return self.hasLogin(retry_count + 1)

        except Exception as e:
            logger.error(f"hasLogin请求异常: {str(e)}")
            time.sleep(0.5)
            return self.hasLogin(retry_count + 1)

    def get_token(self, device_id, retry_count=0):
        """获取token"""
        if retry_count >= 2:
            logger.error("获取token失败，Cookie已失效")
            logger.error("🔴 请手动登录闲鱼，然后更新.env文件中的COOKIES_STR")
            logger.error("🔴 或者运行 'python tools/cli.py refresh-cookies' 来刷新cookies")
            return None

        params = {
            'jsv': '2.7.2',
            'appKey': '34839810',
            't': str(int(time.time()) * 1000),
            'sign': '',
            'v': '1.0',
            'type': 'originaljson',
            'accountSite': 'xianyu',
            'dataType': 'json',
            'timeout': '20000',
            'api': 'mtop.taobao.idlemessage.pc.login.token',
            'sessionOption': 'AutoLoginOnly',
            'spm_cnt': 'a21ybx.im.0.0',
        }
        data_val = '{"appKey":"444e9908a51d1cb236a27862abc769c9","deviceId":"' + device_id + '"}'
        data = {
            'data': data_val,
        }

        token = self.session.cookies.get('_m_h5_tk', '').split('_')[0]
        sign = generate_sign(params['t'], token, data_val)
        params['sign'] = sign

        try:
            response = self.session.post(self.url, params=params, data=data)
            res_json = response.json()

            if isinstance(res_json, dict):
                ret_value = res_json.get('ret', [])
                if not any('SUCCESS::调用成功' in ret for ret in ret_value):
                    logger.warning(f"Token API调用失败，错误信息: {ret_value}")
                    if 'Set-Cookie' in response.headers:
                        logger.debug("检测到Set-Cookie，更新cookie")
                        self.clear_duplicate_cookies()
                    wait_time = 2 + retry_count * 2
                    logger.info(f"等待 {wait_time} 秒后重试...")
                    time.sleep(wait_time)
                    return self.get_token(device_id, retry_count + 1)
                else:
                    logger.info("Token获取成功")
                    return res_json
            else:
                logger.error(f"Token API返回格式异常: {res_json}")
                return self.get_token(device_id, retry_count + 1)

        except Exception as e:
            logger.error(f"Token API请求异常: {str(e)}")
            time.sleep(0.5)
            return self.get_token(device_id, retry_count + 1)

    def get_item_info(self, item_id, retry_count=0):
        """获取商品信息"""
        if retry_count >= 3:
            logger.error("获取商品信息失败，重试次数过多")
            return {"error": "获取商品信息失败，重试次数过多"}

        params = {
            'jsv': '2.7.2',
            'appKey': '34839810',
            't': str(int(time.time()) * 1000),
            'sign': '',
            'v': '1.0',
            'type': 'originaljson',
            'accountSite': 'xianyu',
            'dataType': 'json',
            'timeout': '20000',
            'api': 'mtop.taobao.idle.pc.detail',
            'sessionOption': 'AutoLoginOnly',
            'spm_cnt': 'a21ybx.im.0.0',
        }

        data_val = '{"itemId":"' + item_id + '"}'
        data = {
            'data': data_val,
        }

        token = self.session.cookies.get('_m_h5_tk', '').split('_')[0]
        sign = generate_sign(params['t'], token, data_val)
        params['sign'] = sign

        try:
            response = self.session.post(
                'https://h5api.m.goofish.com/h5/mtop.taobao.idle.pc.detail/1.0/',
                params=params,
                data=data
            )

            res_json = response.json()
            if isinstance(res_json, dict):
                ret_value = res_json.get('ret', [])
                if not any('SUCCESS::调用成功' in ret for ret in ret_value):
                    logger.warning(f"商品信息API调用失败，错误信息: {ret_value}")
                    if 'Set-Cookie' in response.headers:
                        logger.debug("检测到Set-Cookie，更新cookie")
                        self.clear_duplicate_cookies()
                    time.sleep(0.5)
                    return self.get_item_info(item_id, retry_count + 1)
                else:
                    logger.debug(f"商品信息获取成功: {item_id}")
                    return res_json
            else:
                logger.error(f"商品信息API返回格式异常: {res_json}")
                return self.get_item_info(item_id, retry_count + 1)

        except Exception as e:
            logger.error(f"商品信息API请求异常: {str(e)}")
            time.sleep(0.5)
            return self.get_item_info(item_id, retry_count + 1)

    def get_chat_list(self, access_token, retry_count=0):
        """获取聊天列表"""
        if retry_count >= 3:
            logger.error("获取聊天列表失败，重试次数过多")
            return None

        try:
            # 使用更标准的Xianyu API端点
            url = 'https://h5api.m.goofish.com/h5/mtop.taobao.idle.main.chat.list/1.0/'
            params = {
                'jsv': '2.7.2',
                'appKey': '34839810',
                't': str(int(time.time()) * 1000),
                'sign': '',
                'v': '1.0',
                'type': 'originaljson',
                'accountSite': 'xianyu',
                'dataType': 'json',
                'timeout': '20000',
                'api': 'mtop.taobao.idle.main.chat.list',
                'sessionOption': 'AutoLoginOnly',
                'spm_cnt': 'a21ybx.im.0.0',
            }

            data_val = '{"accessToken":"' + access_token + '","pageSize":100,"pageNum":1}'
            data = {
                'data': data_val,
            }

            token = self.session.cookies.get('_m_h5_tk', '').split('_')[0]
            sign = generate_sign(params['t'], token, data_val)
            params['sign'] = sign

            response = self.session.post(url, params=params, data=data)
            res_json = response.json()

            if isinstance(res_json, dict):
                ret_value = res_json.get('ret', [])
                if not any('SUCCESS::调用成功' in ret for ret in ret_value):
                    logger.warning(f"聊天列表API调用失败，错误信息: {ret_value}")
                    if 'Set-Cookie' in response.headers:
                        logger.debug("检测到Set-Cookie，更新cookie")
                        self.clear_duplicate_cookies()
                    time.sleep(0.5)
                    return self.get_chat_list(access_token, retry_count + 1)
                else:
                    logger.debug("聊天列表获取成功")
                    return res_json
            else:
                logger.error(f"聊天列表API返回格式异常: {res_json}")
                return self.get_chat_list(access_token, retry_count + 1)

        except Exception as e:
            logger.error(f"聊天列表API请求异常: {str(e)}")
            time.sleep(0.5)
            return self.get_chat_list(access_token, retry_count + 1)

    def get_chat_detail(self, access_token, chat_id, retry_count=0):
        """获取聊天详情"""
        if retry_count >= 3:
            logger.error("获取聊天详情失败，重试次数过多")
            return None

        try:
            # 使用更标准的Xianyu API端点
            url = 'https://h5api.m.goofish.com/h5/mtop.taobao.idle.main.chat.detail/1.0/'
            params = {
                'jsv': '2.7.2',
                'appKey': '34839810',
                't': str(int(time.time()) * 1000),
                'sign': '',
                'v': '1.0',
                'type': 'originaljson',
                'accountSite': 'xianyu',
                'dataType': 'json',
                'timeout': '20000',
                'api': 'mtop.taobao.idle.main.chat.detail',
                'sessionOption': 'AutoLoginOnly',
                'spm_cnt': 'a21ybx.im.0.0',
            }

            data_val = '{"accessToken":"' + access_token + '","chatId":"' + chat_id + '","pageSize":100,"pageNum":1}'
            data = {
                'data': data_val,
            }

            token = self.session.cookies.get('_m_h5_tk', '').split('_')[0]
            sign = generate_sign(params['t'], token, data_val)
            params['sign'] = sign

            response = self.session.post(url, params=params, data=data)
            res_json = response.json()

            if isinstance(res_json, dict):
                ret_value = res_json.get('ret', [])
                if not any('SUCCESS::调用成功' in ret for ret in ret_value):
                    logger.warning(f"聊天详情API调用失败，错误信息: {ret_value}")
                    if 'Set-Cookie' in response.headers:
                        logger.debug("检测到Set-Cookie，更新cookie")
                        self.clear_duplicate_cookies()
                    time.sleep(0.5)
                    return self.get_chat_detail(access_token, chat_id, retry_count + 1)
                else:
                    logger.debug(f"聊天详情获取成功: {chat_id}")
                    return res_json
            else:
                logger.error(f"聊天详情API返回格式异常: {res_json}")
                return self.get_chat_detail(access_token, chat_id, retry_count + 1)

        except Exception as e:
            logger.error(f"聊天详情API请求异常: {str(e)}")
            time.sleep(0.5)
            return self.get_chat_detail(access_token, chat_id, retry_count + 1)