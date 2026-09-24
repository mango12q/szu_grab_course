# -*- coding: utf-8 -*-
# 程序入口

import random
import sys
import time

import choose_course
import setting

# 正常轮询间隔（秒），来自 setting.delay（毫秒）
BASE_DELAY = setting.delay / 1000.0

# 连续请求失败时的退避上限（秒）：失败越多等得越久，避免把服务器打挂、也避免被风控
MAX_BACKOFF = 30.0


def sleep_with_jitter(seconds):
    """睡一小段，并加 ±15% 的随机抖动，避免固定节奏被识别成脚本"""
    time.sleep(seconds * (0.85 + random.random() * 0.3))


def looks_like_login_page(text):
    """接口正常应该返回 JSON；如果返回的是登录页 HTML，说明 Cookie / token 已经失效"""
    head = text.lstrip()[:200].lower()
    return head.startswith("<!doctype") or head.startswith("<html")


def choose_once(course):
    """提交一次选课请求，返回 (状态, 文案)

    状态取值：
      success  抢到了
      full     课容量满，继续重试
      expired  会话失效，需要重新抓 Cookie
      retry    其它返回，原样打印后继续重试
    """
    response = choose_course.start_choose(course['id'], course['type'])

    if "添加选课志愿成功" in response:
        return "success", "抢课成功"
    if "该课程超过课容量" in response:
        return "full", "该课程超过课容量"
    if looks_like_login_page(response):
        return "expired", "服务器返回的是登录页，Cookie / token 很可能已经失效"
    return "retry", response


def main():
    if not setting.courses:
        print("courses 是空的，没有需要抢的课程，请先填写 config.json 或 setting.py")
        return 1

    if not (setting.user_id and setting.cookie and setting.token):
        print("user_id / cookie / token 还没填好，请先填写 config.json 或 setting.py")
        return 1

    pending = list(setting.courses)   # 还没抢到的课程
    got = []                          # 已经抢到的课程
    backoff = BASE_DELAY
    error_streak = 0
    expired = False

    try:
        for _ in range(setting.count):
            if not pending:
                break

            for course in list(pending):
                try:
                    status, message = choose_once(course)
                except KeyboardInterrupt:
                    raise
                except Exception as exc:
                    # 网络 / 解析类错误：退避之后再重试，不能在出错时毫无间隔地狂发请求
                    error_streak += 1
                    print("%s: 请求出错 %s: %s（%.1f 秒后重试）"
                          % (course['name'], type(exc).__name__, exc, backoff))
                    if error_streak == 5:
                        print("连续 5 次请求都出错，请检查网络，以及 config.json 里的"
                              "课程 id / type 是否填写正确")
                    sleep_with_jitter(backoff)
                    backoff = min(backoff * 2, MAX_BACKOFF)
                    continue

                backoff = BASE_DELAY      # 请求恢复正常，退避重置
                error_streak = 0

                if status == "success":
                    print(course['name'] + ": 抢课成功")
                    got.append(course)
                    pending.remove(course)          # 抢到的课不再重复提交
                elif status == "full":
                    print(course['name'] + ": 该课程超过课容量")
                elif status == "expired":
                    print(course['name'] + ": " + message)
                    expired = True
                    break
                else:
                    print(course['name'] + ": " + message)

                sleep_with_jitter(BASE_DELAY)

            if expired:
                break

    except KeyboardInterrupt:
        print()
        print("通过键盘中断退出程序")

    print("抢课结束")
    print("======================")
    if got:
        print("已抢到 %d 门课程：" % len(got))
        for course in got:
            print("    " + course['name'])
    if expired:
        print("检测到登录状态已失效，已提前停止。")
        print("请重新登录选课系统，把新的 Cookie、token 填回 config.json 后再跑一次。")
    elif pending:
        print("还有 %d 门课程没有抢到：" % len(pending))
        for course in pending:
            print("    " + course['name'])

    print("======================")
    print("您现在选课的结果如下")
    try:
        choose_course.query_result()
    except KeyboardInterrupt:
        pass
    except Exception as exc:
        # 这一步失败不影响前面已经抢到的课程，不要让整个程序崩掉
        print("查询选课结果失败：%s: %s" % (type(exc).__name__, exc))
        print("（常见原因是 Cookie / token 已经失效，或者不在选课时间内）")

    return 2 if expired else 0


if __name__ == "__main__":
    sys.exit(main())
