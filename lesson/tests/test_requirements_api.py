# -*- coding: utf-8 -*-
"""需求中心 API：提交校验、可见范围（老师只看自己）、状态流转留痕。"""

import os
import sqlite3
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from fastapi import HTTPException

from models.datas_api import requirements_api
from models.datas_api.auth import User
from tests.test_invigilation_todo_sync import MiniMoralDB


@pytest.fixture
def req_env(monkeypatch):
    """独立内存 moral.db，patch 连接函数（带上下文管理器，与生产 MoralDatabase 接口一致）。"""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    db = MiniMoralDB(conn)
    for sql in requirements_api.TABLE_SQL:
        db.execute(sql)

    from contextlib import contextmanager

    @contextmanager
    def fake_moral_db():
        yield db

    monkeypatch.setattr(requirements_api, "get_moral_db", fake_moral_db)

    def _submit(title="希望监考通知能按学科筛选", submitter="T_甲", **kwargs):
        payload = {
            "title": title,
            "problem": "每次都要逐个复制粘贴通知，容易漏发。",
            "expectation": "点一次按钮只通知对应学科的老师。",
            **kwargs,
        }
        return requirements_api.submit_requirement(
            requirements_api.RequirementCreate(**payload),
            user=User(username=submitter, role="teacher"),
        )

    yield db, _submit
    conn.close()


def test_submit_creates_pending_with_log(req_env):
    db, submit = req_env
    res = submit()

    assert res["success"] is True
    assert res["data"]["requirement_no"].startswith("REQ-")
    row = db.query_one("SELECT * FROM requirement WHERE id = ?", (res["data"]["id"],))
    assert row["status"] == "pending"
    assert row["submitter_name"] == "T_甲"
    logs = db.query_all("SELECT * FROM requirement_log")
    assert len(logs) == 1 and logs[0]["action"] == "submit"


def test_submit_rejects_too_short_fields(req_env):
    _, submit = req_env
    with pytest.raises(Exception):
        submit(title="x")            # 标题太短
    with pytest.raises(Exception):
        submit(problem="短")          # 问题描述太短
    with pytest.raises(Exception):
        submit(expectation="短")      # 期望太短


def test_teacher_sees_only_own(req_env):
    db, submit = req_env
    r1 = submit()
    # 第二位老师提交
    res2 = submit(title="另一个需求", submitter="T_乙")

    mine_a = requirements_api.list_requirements("mine", user=User(username="T_甲", role="teacher"))
    assert [r["id"] for r in mine_a["data"]] == [r1["data"]["id"]]

    # 老师看全部 → 拒绝
    with pytest.raises(HTTPException) as exc:
        requirements_api.list_requirements("all", user=User(username="T_甲", role="teacher"))
    assert exc.value.status_code == 403

    # 教务/管理员看全部
    all_rows = requirements_api.list_requirements("all", user=User(username="jw", role="jiaowu"))
    assert len(all_rows["data"]) == 2
    all_rows_admin = requirements_api.list_requirements("all", user=User(username="ad", role="admin"))
    assert len(all_rows_admin["data"]) == 2


def test_detail_visibility(req_env):
    db, submit = req_env
    r = submit()
    rid = r["data"]["id"]

    # 提交人可看
    detail = requirements_api.get_requirement_detail(rid, user=User(username="T_甲", role="teacher"))
    assert detail["data"]["title"].startswith("希望监考")
    # 他人不可看
    with pytest.raises(HTTPException) as exc:
        requirements_api.get_requirement_detail(rid, user=User(username="T_乙", role="teacher"))
    assert exc.value.status_code == 403
    # 教务可看
    detail_jw = requirements_api.get_requirement_detail(rid, user=User(username="jw", role="jiaowu"))
    assert detail_jw["data"]["id"] == rid
    # 不存在
    with pytest.raises(HTTPException):
        requirements_api.get_requirement_detail(999, user=User(username="jw", role="jiaowu"))


def test_status_update_flow_with_log(req_env):
    db, submit = req_env
    rid = submit()["data"]["id"]

    # 老师不能推进状态
    with pytest.raises(HTTPException) as exc:
        requirements_api.update_requirement_status(
            rid, requirements_api.StatusUpdate(status="designing"),
            user=User(username="T_甲", role="teacher"))
    assert exc.value.status_code == 403

    # 教务推进：待澄清 → 待审核 → 已上线
    for status, note in (("designing", None), ("reviewing", "设计稿已给教务确认"), ("done", "已上线")):
        requirements_api.update_requirement_status(
            rid, requirements_api.StatusUpdate(status=status, note=note),
            user=User(username="jw", role="jiaowu"))

    row = db.query_one("SELECT status FROM requirement WHERE id = ?", (rid,))
    assert row["status"] == "done"
    logs = db.query_all("SELECT * FROM requirement_log WHERE requirement_id = ? ORDER BY id", (rid,))
    assert [l["action"] for l in logs] == ["submit", "status", "status", "status"]
    # note 为空时自动生成默认说明
    assert "设计中" in logs[1]["note"]

    # 非法状态拒绝
    with pytest.raises(HTTPException) as exc:
        requirements_api.update_requirement_status(
            rid, requirements_api.StatusUpdate(status="bad_status"),
            user=User(username="jw", role="jiaowu"))
    assert exc.value.status_code == 400


def test_comment_permissions(req_env):
    db, submit = req_env
    rid = submit()["data"]["id"]

    # 提交人可补充说明
    requirements_api.add_requirement_comment(
        rid, requirements_api.CommentCreate(note="补充：主要是期中考试的时候"),
        user=User(username="T_甲", role="teacher"))
    # 他人不可
    with pytest.raises(HTTPException) as exc:
        requirements_api.add_requirement_comment(
            rid, requirements_api.CommentCreate(note="路过"),
            user=User(username="T_乙", role="teacher"))
    assert exc.value.status_code == 403
    # 教务可留言
    requirements_api.add_requirement_comment(
        rid, requirements_api.CommentCreate(note="已和教务确认场景"),
        user=User(username="jw", role="jiaowu"))

    logs = db.query_all("SELECT * FROM requirement_log WHERE requirement_id = ? AND action = 'comment'", (rid,))
    assert len(logs) == 2
