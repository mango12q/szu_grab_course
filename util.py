# -*- coding: utf-8 -*-
# 程序工具

import time
import requests
from requests.adapters import HTTPAdapter

import setting

# 单次请求的超时时间（秒）。requests 默认不超时，一旦服务器不响应，
# 程序会一直卡在那里，连 Ctrl+C 都不一定好使。下载课程列表嫌慢可以调大这个值。
TIMEOUT = 10


class TimeoutHTTPAdapter(HTTPAdapter):
    """给所有请求加上默认超时，避免某一个请求把整个程序挂死"""

    def send(self, request, **kwargs):
        timeout = kwargs.get("timeout")
        if not isinstance(timeout, (int, float, tuple)):
            kwargs["timeout"] = TIMEOUT
        return super().send(request, **kwargs)


session = requests.session()
session.mount("http://", TimeoutHTTPAdapter())
session.mount("https://", TimeoutHTTPAdapter())

current_milli_time = lambda: int(round(time.time() * 1000))


# 返回当前时间戳
def get_timestamp():
    return str(current_milli_time())
    
# Python 的模块就是天然的单例模式，因为模块在第一次导入时，会生成 .pyc 文件，当第二次导入时，就会直接加载 .pyc 文件，而不会再次执行模块代码。
# 返回session
def get_session():
    return session

# 获取完整路径
def get_url(relavie_path):
    return "{}{}".format(setting.url,relavie_path)


# 接口正常应该返回 JSON；如果返回的是登录页 HTML，说明 Cookie / token 已经失效
def looks_like_login_page(text):
    head = (text or "").lstrip()[:200].lower()
    return head.startswith("<!doctype") or head.startswith("<html")
