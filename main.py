# -*- coding: utf-8 -*-
# 程序入口

import json
import os
import random
import sys
import time

import choose_course
import setting
import util

# 正常轮询间隔（秒），来自 setting.delay（毫秒）
BASE_DELAY = setting.delay / 1000.0

# 连续请求失败时的退避上限（秒）：失败越多等得越久，避免把服务器打挂、也避免被风控
MAX_BACKOFF = 30.0

# 学校说「已受理」之后，还要回查「已选课程」列表来确认是不是真的选上了。
# 已选列表有同步延迟，所以查不到时会在这一轮里多查几次。
CONFIRM_ATTEMPTS = 3
CONFIRM_RETRY_SECONDS = 1.0

# 学校返回里代表「提交成功」和「已经选过」的关键词。
# 两者都只是「候选」——必须回查已选课程列表、按教学班 ID 精确匹配之后才算真的抢到。
SUCCESS_KEYWORDS = ("添加选课志愿成功",)
ALREADY_SELECTED_KEYWORDS = ("已经选过", "已选过", "已经选到", "已经存在选课结果中", "已经存在")

# 课容量满，属于可重试
FULL_KEYWORDS = ("该课程超过课容量", "超过课容量", "课容量已满", "课程容量已满",
                 "教学班容量已满", "人数已满", "容量已满")

# 已选课程列表里可能出现的教学班 ID 字段名（不确定学校用哪个，一个都不放过）
ID_KEYS = ("teachingClassId", "teachingClassID", "teachingClassid", "classId",
           "teachingClassCode", "electiveCourseId")

# 响应原文落盘目录（已在 .gitignore 里），方便事后校准判断规则
LOG_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")


def sleep_with_jitter(seconds):
    """睡一小段，并加 ±15% 的随机抖动，避免固定节奏被识别成脚本"""
    time.sleep(seconds * (0.85 + random.random() * 0.3))


class ResponseLog:
    """把见过的响应原文记下来，每种只记第一次，方便事后校准判断规则"""

    def __init__(self, path):
        self.path = path
        self.seen = {}
        self._fh = None

    def record(self, kind, text):
        text = "" if text is None else str(text)
        if text in self.seen:
            self.seen[text] += 1
            return
        self.seen[text] = 1
        try:
            if self._fh is None:
                os.makedirs(os.path.dirname(self.path), exist_ok=True)
                self._fh = open(self.path, "a", encoding="utf-8")
            self._fh.write("[%s] %s\n%s\n%s\n\n"
                           % (time.strftime("%Y-%m-%d %H:%M:%S"), kind, text[:2000], "-" * 60))
            self._fh.flush()
        except Exception:
            pass          # 记日志失败绝不能影响抢课

    def close(self):
        if self._fh is not None:
            try:
                self._fh.close()
            except Exception:
                pass
            self._fh = None


def classify(response):
    """判断学校这次返回属于哪一类，返回 (状态, 文案)"""
    if any(keyword in response for keyword in SUCCESS_KEYWORDS):
        return "success_candidate", "学校提示已受理"
    if any(keyword in response for keyword in ALREADY_SELECTED_KEYWORDS):
        return "success_candidate", "学校提示已经选过"
    if any(keyword in response for keyword in FULL_KEYWORDS):
        return "full", "该课程超过课容量"
    if util.looks_like_login_page(response):
        return "expired", "服务器返回的是登录页，Cookie / token 很可能已经失效"
    return "retry", response


def choose_once(course, log=None):
    """提交一次选课请求，返回 (状态, 文案)"""
    response = choose_course.start_choose(course['id'], course['type'])
    status, message = classify(response)
    if log is not None:
        log.record(status, response)
    return status, message


def extract_ids(data_list):
    """从已选课程列表里取出所有能用来精确比对的课程 ID"""
    ids = set()
    for item in data_list:
        if not isinstance(item, dict):
            continue
        for key in ID_KEYS:
            value = item.get(key)
            if value not in (None, ""):
                ids.add(str(value).strip())
        # 字段名猜不到时的兜底：课程 ID 是 20 位以上的纯数字串
        for value in item.values():
            if isinstance(value, str):
                value = value.strip()
                if value.isdigit() and len(value) >= 12:
                    ids.add(value)
    return ids


def confirm_enrolled(course, log=None):
    """回查「已选课程」列表，确认这门课是不是真的落库了

    返回：
      confirmed   已选列表里确实有这门课
      absent      列表有效，但这门课还没出现（可能只是同步延迟）
      unknown     列表里找不到任何能用于比对的课程 ID 字段，无法核实
      unavailable 回查接口一直失败
      expired     回查时发现登录已失效
    """
    course_id = str(course['id']).strip()
    last_error = None
    saw_list = False

    for attempt in range(CONFIRM_ATTEMPTS):
        if attempt:
            time.sleep(CONFIRM_RETRY_SECONDS)
        try:
            data_list = choose_course.query_selected()
        except choose_course.SessionExpiredError:
            return "expired"
        except Exception as exc:
            last_error = exc
            continue

        saw_list = True
        if log is not None:
            log.record("enrolled_list", json.dumps(data_list, ensure_ascii=False))

        ids = extract_ids(data_list)
        if course_id in ids:
            return "confirmed"
        if data_list and not ids:
            # 列表里有课，但一个能用于比对的 ID 都没有，说明字段名和预期不同
            return "unknown"
        # 列表有效但这门课暂时还没出现：可能是同步延迟，隔一会儿再查

    if not saw_list:
        print("    回查已选课程列表失败：%s: %s" % (type(last_error).__name__, last_error))
        return "unavailable"
    return "absent"


def main():
    if not setting.courses:
        print("courses 是空的，没有需要抢的课程，请先填写 config.json 或 setting.py")
        return 1

    if not (setting.user_id and setting.cookie and setting.token):
        print("user_id / cookie / token 还没填好，请先填写 config.json 或 setting.py")
        return 1

    log = ResponseLog(os.path.join(LOG_DIR, "responses-%s.log" % time.strftime("%Y%m%d")))

    pending = list(setting.courses)   # 还没确认抢到的课程
    got = []                          # 已经确认抢到的课程
    backoff = BASE_DELAY
    error_streak = 0
    expired = False

    try:
        for _ in range(setting.count):
            if not pending:
                break

            for course in list(pending):
                try:
                    status, message = choose_once(course, log)
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

                if status == "success_candidate":
                    print("%s: %s，正在回查「已选课程」确认…" % (course['name'], message))
                    result = confirm_enrolled(course, log)
                    if result == "confirmed":
                        print("%s: 已由学校已选课程列表确认选中 ✓" % course['name'])
                        got.append(course)
                        pending.remove(course)
                    elif result == "unknown":
                        print("%s: 已选课程列表里找不到可用于比对的课程 ID 字段，无法核实，"
                              "先按提交成功处理（响应原文已存进日志，可回来看）" % course['name'])
                        got.append(course)
                        pending.remove(course)
                    elif result == "expired":
                        print("%s: 回查时发现登录状态已失效" % course['name'])
                        expired = True
                        break
                    else:
                        print("%s: 学校已受理，但已选课程列表里还没有这门课，继续重试" % course['name'])
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
    finally:
        log.close()

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
    if log.seen:
        print("本次见过的响应原文已存到：%s" % log.path)

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
