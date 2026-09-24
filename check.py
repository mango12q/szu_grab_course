# -*- coding: utf-8 -*-
# 只读自检：确认「配置填对了没 / 选课系统连得上吗 / Cookie 还有效吗 / 接口字段名对不对得上」
#
# 全程只读，不提交任何选课请求，可以放心跑：
#     python check.py
#
# 退出码：0 自检通过 / 1 配置没填好 / 2 登录态或接口有问题

import sys
import time

import requests

import choose_course
import main
import setting
import util


def report(ok, text):
    print(("  [OK]   " if ok else "  [FAIL] ") + text)


def run_check():
    print("=" * 64)
    print("szu_grab_course 只读自检（不会提交任何选课请求）")
    print("=" * 64)

    # ---------- 1. 配置 ----------
    print("\n[1/4] 配置")
    missing = [name for name in ("user_id", "cookie", "token", "electiveBatchCode")
               if not getattr(setting, name, "")]
    if missing:
        report(False, "还没填：" + "、".join(missing))
        print("         照着 README「四、配置」填 config.json，或直接改 setting.py")
        return 1
    report(True, "user_id / cookie / token / electiveBatchCode 都填了")
    if not setting.courses:
        print("  [WARN] courses 是空的：自检能过，但 main.py 不会抢任何课")

    # ---------- 2. 连通性 ----------
    print("\n[2/4] 选课系统连通性（只读 GET，不带你的凭证）")
    url = util.get_url("xsxkapp/sys/xsxkapp/*default/index.do")
    try:
        response = requests.get(url, timeout=util.TIMEOUT,
                                headers={"User-Agent": setting.headers["User-Agent"]})
        report(True, "%s 返回 HTTP %s，系统是活的" % (url, response.status_code))
    except Exception as exc:
        report(False, "连不上：%s: %s" % (type(exc).__name__, exc))
        print("         检查网络；也可能现在不是选课季，系统本身没对外开放")
        return 2

    # ---------- 3. 登录态 + 接口协议 ----------
    print("\n[3/4] 用你填的 Cookie / token 查一次「已选课程」（只读，不提交选课）")
    try:
        data_list = choose_course.query_selected()
    except choose_course.SessionExpiredError as exc:
        report(False, "登录态已失效：%s" % exc)
        print("         重新登录选课系统，把新的 Cookie 和 token 填回 config.json")
        return 2
    except Exception as exc:
        report(False, "接口返回不对：%s: %s" % (type(exc).__name__, exc))
        print("         如果提示「没有 dataList 字段」，说明学校接口结构变了，")
        print("         把这条报错发到 mango12q@163.com")
        return 2

    report(True, "Cookie / token 有效，接口能正常返回")
    report(True, "拿到已选课程 %d 条" % len(data_list))

    # ---------- 4. 字段名 ----------
    print("\n[4/4] 核对「教学班 ID」的字段名（两级确认靠它做精确匹配）")
    if not data_list:
        print("  [WARN] 你目前一门课都没选，拿不到字段名")
        print("         等有已选课程时再跑一次；或者看 logs/ 里的 enrolled_list 原文")
    else:
        print("  已选列表第一条的字段：")
        for key, value in data_list[0].items():
            print("      %-24s %s" % (key, str(value)[:56]))
        ids = main.extract_ids(data_list)
        if ids:
            report(True, "能提取到可用于比对的课程 ID，例如 %s" % sorted(ids)[0])
        else:
            report(False, "一个课程 ID 都提取不到，字段名和预期不同")
            print("         把上面这些字段名发到 mango12q@163.com，加上就能用")

    # ---------- 顺带提醒：courses 里的 id 是不是旧学年的 ----------
    if setting.courses:
        this_year = time.localtime().tm_year
        allowed = {str(this_year), str(this_year - 1)}
        for course in setting.courses:
            course_id = str(course.get('id', ''))
            if course_id[:4].isdigit() and course_id[:4] not in allowed:
                print("  [WARN] %s 的 id 以 %s 开头，看着是旧学年的课，可能已经失效"
                      % (course.get('name') or course_id, course_id[:4]))

    print("\n" + "=" * 64)
    print("自检通过：配置、连通性、登录态、接口协议都对得上，可以 python main.py 了")
    print("=" * 64)
    return 0


if __name__ == "__main__":
    sys.exit(run_check())
