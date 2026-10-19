# -*- coding: utf-8 -*-
"""公告 class_id 锚定回归测试。

背景：历史公告按 class_code 存储，但前端实际传入 class_name（lesson.py class_template
把 class_name 塞进 class_code 字段），调度任务传入数字 class_code，两套键互相查不到；
升年级改名后旧 class_name 也失效。修复后公告以 class_id 为主锚点，class_code 仅作
历史数据兼容匹配。
"""

import os
import shutil
import tempfile

import pytest


@pytest.fixture()
def homework_db():
    """在临时目录创建 Homework 实例（含 announcements 表）"""
    tmp_dir = tempfile.mkdtemp()
    db_path = os.path.join(tmp_dir, "homework.db")
    from models.lesson.homework import Homework

    hw = Homework()
    hw.__enter__(db_path=db_path)
    hw.__create_table__()
    yield hw
    hw.__exit__(None, None, None)
    shutil.rmtree(tmp_dir, ignore_errors=True)


class TestAnnouncementClassIdAnchor:
    """公告以 class_id 为主锚点"""

    def test_add_with_class_id(self, homework_db):
        homework_db.add_announcement("202501", "调度公告", "系统", "内容", None, class_id=7)
        anns = homework_db.get_announcement("202501", class_id=7)
        assert len(anns) == 1
        assert anns[0]["title"] == "调度公告"

    def test_class_id_unifies_mixed_class_code_keys(self, homework_db):
        """同一班级以 class_code（调度）和 class_name（教师）两种键写入的公告，
        都能通过 class_id 查到——无论查询时班级叫什么名字。"""
        homework_db.add_announcement("202501", "调度公告", "系统", "内容", None, class_id=7)
        homework_db.add_announcement("高一1班", "教师公告", "王老师", "内容", None, class_id=7)

        # 升年级后班级改名为「高二1班」，class_id 不变
        anns = homework_db.get_announcement("高二1班", class_id=7)
        titles = {a["title"] for a in anns}
        assert titles == {"调度公告", "教师公告"}

    def test_class_id_fallback_matches_legacy_rows(self, homework_db):
        """未回填 class_id 的历史行（旧 class_code 写法）仍能被查到"""
        homework_db.add_announcement("202501", "历史公告", "系统", "内容", None)
        anns = homework_db.get_announcement("202501", class_id=7)
        assert len(anns) == 1
        assert anns[0]["title"] == "历史公告"

    def test_get_without_class_id_keeps_legacy_behavior(self, homework_db):
        """不传 class_id 时保持原有按 class_code 精确匹配的行为"""
        homework_db.add_announcement("202401", "旧公告", "老师", "内容", None)
        anns = homework_db.get_announcement("202401")
        assert len(anns) == 1
        # class_id 不同的行不会误入
        homework_db.add_announcement("高一1班", "别班公告", "老师", "内容", None, class_id=9)
        anns = homework_db.get_announcement("202401")
        assert len(anns) == 1

    def test_class_id_column_created(self, homework_db):
        """新库建表后 announcements 含 class_id 列"""
        cols = [r[1] for r in homework_db.cursor.execute(
            "PRAGMA table_info(announcements)"
        ).fetchall()]
        assert "class_id" in cols


class TestResolveClass:
    """班级标识解析：class_name 与 class_code 均可定位班级"""

    @pytest.fixture()
    def fake_moral(self, monkeypatch):
        from models.datas_api.moral import base as moral_base

        rows = {
            "202501": {"class_id": 7, "class_code": "202501", "class_name": "高二1班"},
            "高二1班": {"class_id": 7, "class_code": "202501", "class_name": "高二1班"},
        }

        class FakeDB:
            def query_one(self, sql, params):
                return rows.get(str(params[0]))

        class FakeCtx:
            def __enter__(self):
                return FakeDB()

            def __exit__(self, *args):
                return False

        monkeypatch.setattr(moral_base, "get_moral_db", lambda: FakeCtx())
        from models.datas_api import legacy_homework

        return legacy_homework

    def test_resolve_by_class_name(self, fake_moral):
        row = fake_moral._resolve_class("高二1班")
        assert row["class_id"] == 7

    def test_resolve_by_class_code(self, fake_moral):
        row = fake_moral._resolve_class("202501")
        assert row["class_id"] == 7

    def test_resolve_unknown_returns_none(self, fake_moral):
        assert fake_moral._resolve_class("不存在班") is None

    def test_resolve_none_identifier(self, fake_moral):
        assert fake_moral._resolve_class(None) is None
