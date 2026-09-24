# -*- coding: utf-8 -*-
# 选课相关逻辑

import json

import setting
import util

headers = setting.headers
session = util.get_session()


class SessionExpiredError(Exception):
    """服务器返回的是登录页，说明 Cookie / token 已经失效"""


# 查询已选课程列表（「我的课程」用的就是这个接口）
# 返回 dataList 列表；登录失效抛 SessionExpiredError，返回内容不是预期的 JSON 抛 ValueError
def query_selected():
    response = session.post(
        url=util.get_url("xsxkapp/sys/xsxkapp/elective/courseResult.do?timestamp={}&studentCode={}").format(
            util.get_timestamp(), setting.user_id),
        headers=headers)

    if util.looks_like_login_page(response.text):
        raise SessionExpiredError("返回的是登录页，Cookie / token 很可能已经失效")

    try:
        json_data = json.loads(response.text)
    except ValueError:
        raise ValueError("返回内容不是 JSON：%s" % (response.text or "")[:200])

    if not isinstance(json_data, dict) or 'dataList' not in json_data:
        raise ValueError("返回里没有 dataList 字段：%s" % (response.text or "")[:200])

    data_list = json_data['dataList']
    return data_list if isinstance(data_list, list) else []


# 查询选课结果（已经选中的课程）并打印
def query_result():
    index = 1
    for obj in query_selected():
        print(index, end=" ")
        index = index + 1

        print("course_name is :", obj.get('courseName'))
        print("teacher is :", obj.get('teacherName'))
        print("place and time is ", obj.get('teachingPlace'))
        print("---------------------------------")


# 选课
def start_choose(class_id, teaching_class_type):
    form_data = {
        'addParam': (r'''{"data":{"operationType":"1","studentCode":%s,"electiveBatchCode":%s,"teachingClassId":%s,"isMajor":"1","campus":"01","teachingClassType":%s,"chooseVolunteer":"1"}}''' % (
            setting.user_id, setting.electiveBatchCode, class_id, teaching_class_type))
    }

    response = session.post(
        url=util.get_url("xsxkapp/sys/xsxkapp/elective/volunteer.do"),
        data=form_data,
        headers=headers)

    return response.text
