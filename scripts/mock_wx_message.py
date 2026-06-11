#!/usr/bin/env python3
"""模拟发送微信消息到系统监听接口"""

import requests
import json

# 消息体
body = {
    'id': None,
    'wechatid': 'wxid_3hio95ow9yh122',
    'friendid': 'yoin007',
    'msgsvrid': '1141955020534006954',
    'issend': 'false',
    'contenttype': 1,
    'content': '待完善记录：11\n学生1：杨善青\n学生2：刘洪义\n任课教师：冯秀珍\n时间：2026-06-11 14:40\n事件类型：为班集体贡献',
    'ext': '',
    'type': 0,
    'createTime': 1779191745000,
    'owner': None,
    'userContent': None
}

# 系统监听接口地址（根据实际部署调整）
url = "http://localhost:14600/"

def send_mock_message(msg_body=None):
    """发送模拟消息"""
    if msg_body is None:
        msg_body = body

    headers = {"Content-Type": "application/json"}

    try:
        response = requests.post(url, json=msg_body, headers=headers, timeout=10)
        print(f"状态码: {response.status_code}")
        print(f"响应: {response.text}")
        return response
    except requests.exceptions.RequestException as e:
        print(f"请求失败: {e}")
        return None

if __name__ == "__main__":
    # 直接发送
    send_mock_message()

    # 可交互修改内容
    print("\n如需修改消息内容，编辑 body 字典后重新运行")