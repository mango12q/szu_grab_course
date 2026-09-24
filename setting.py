# -*- coding: utf-8 -*-
# 程序设置
#
# 私有信息（学号 / Cookie / token / electiveBatchCode / 要抢的课程）有两种填法：
#
#   方法一（推荐）：复制同目录下的 config.example.json 为 config.json，在里面填。
#                   config.json 已被 .gitignore 忽略，push 时不会把你的学号和 Cookie 传到 GitHub。
#
#   方法二：直接改下面「需要你自己填的部分」的默认值。这种方式自己本地用没问题，
#           但如果你把改动 commit 上去，你的学号和 Cookie 就会公开在仓库里，
#           任何人都能拿去冒充你登录选课系统（直到你重新登录使 Cookie 失效）。

import json
import os

_CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")


# ==================== 需要你自己填的部分（默认值） ====================

# 学号
user_id = ""

# 每次重新登录后都会改变
cookie = ""

electiveBatchCode = ""

# 每次重新登录后都会改变
token = ""

# 你要抢的课程，格式：[{'id': '202320242150294000101', 'type': 'FANKC', 'name': '信息检索(潘微科)'}]
# 课程类别：本班课程 TJKC / 方案内课程 FANKC / 方案外课程 FAWKC / 校公选课 XGXK
#           慕课 MOOC / 辅修课程 FXKC / 体育课程 TYKC
# 注意 id 里带的是学年学期码（20232024…），过了一个学期就会失效，需要重新获取。
courses = []

# 间隔时间，单位是 ms（最好不要低于 400ms，不然可能会被系统判定为异常请求）
delay = 400

# 抢课轮数，每一轮会把 courses 从上到下遍历一遍
count = 150000000

# ====================================================================


# 如果存在 config.json，就用它覆盖上面的默认值
if os.path.exists(_CONFIG_FILE):
    with open(_CONFIG_FILE, "r", encoding="utf-8") as _f:
        _config = json.load(_f)

    user_id = str(_config.get("user_id") or user_id)
    cookie = str(_config.get("cookie") or cookie)
    electiveBatchCode = str(_config.get("electiveBatchCode") or electiveBatchCode)
    token = str(_config.get("token") or token)
    if _config.get("courses"):
        courses = _config["courses"]
    if _config.get("delay"):
        delay = int(_config["delay"])
    if _config.get("count"):
        count = int(_config["count"])


########## 不要修改下面的配置！！！！！！  ############
########## 不要修改下面的配置！！！！！！  ############
########## 不要修改下面的配置！！！！！！  ############

url = "http://bkxk.szu.edu.cn/"

headers = {
    "Cookie": cookie.strip(),
    "token": token.strip(),
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/74.0.3729.157 Safari/537.36",
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "Accept-Encoding": "gzip, deflate",
    "Accept-Language": "en-US,en;q=0.9,zh-CN;q=0.8,zh;q=0.7",
    "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
    "Host": "bkxk.szu.edu.cn",
    "Pragma": "no-cache"
}


# 启动时的自检提醒（不影响运行，只是提示你哪里还没填）
_missing = [name for name in ("user_id", "cookie", "token", "electiveBatchCode") if not globals()[name]]
if _missing:
    print("[配置提醒] 还没填写：" + "、".join(_missing) + "（改 config.json 或 setting.py）")
if not courses:
    print("[配置提醒] courses 是空的，main.py 不会提交任何选课请求")
