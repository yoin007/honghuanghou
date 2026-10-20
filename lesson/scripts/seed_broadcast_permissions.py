#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
IP 广播指令规则种子脚本

向 permission 表插入 4 条微信指令规则（models/broadcast 模块）：

    广播终端               查询全部终端（编号为播放用 UI 编号）
    广播 7 / 广播全部      引用语音消息触发终端播放（type=22），可加「强制」
    广播授权 老师名 token  （仅管理员）绑定
    广播解绑 老师名        （仅管理员）解绑

- 幂等：按 func 判重，重复执行不会重复插入
- 规则按 priority 升序匹配，「广播终端/授权/解绑」必须排在通用「广播」之前，
  否则会被 ^广播 规则抢先命中

使用方式（在 lesson 目录下，用运行后端的 Python）：
    python scripts/seed_broadcast_permissions.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.manage.member import Member

RULES = [
    dict(func="broadcast_terminals", func_name="广播终端查询", pattern=r"^广播终端",
         type="", priority=30, example="广播终端"),
    dict(func="broadcast_bind", func_name="广播授权", pattern=r"^广播授权",
         type="", priority=31, example="广播授权 张三 abc123"),
    dict(func="broadcast_unbind", func_name="广播解绑", pattern=r"^广播解绑",
         type="", priority=32, example="广播解绑 张三"),
    # 通用「广播」只匹配引用消息(type=22)，具体解析在函数内完成
    dict(func="broadcast_voice", func_name="语音广播", pattern=r"^广播",
         type="22", priority=33, example="引用语音消息后发送：广播 7"),
]


def main():
    with Member() as m:
        existing = {row[1] for row in m.permission_func_list()}

    inserted = 0
    for rule in RULES:
        if rule["func"] in existing:
            print(f"已存在，跳过: {rule['func']}")
            continue
        with Member() as m:
            m.insert_permission(
                func=rule["func"],
                func_name=rule["func_name"],
                white_list="all",
                pattern=rule["pattern"],
                type=rule["type"],
                priority=rule["priority"],
                example=rule["example"],
                module="broadcast",
                notes="IP广播集成 seed_broadcast_permissions.py",
            )
        inserted += 1
        print(f"已插入: {rule['func']} <- /{rule['pattern']}/")

    print(f"完成：新增 {inserted} 条，共 {len(RULES)} 条规则")


if __name__ == "__main__":
    main()
