"""datas_api_legacy task routes sqlite_base 回归测试。"""

import sqlite3

import pytest
from fastapi import HTTPException

from models.datas_api import legacy_tasks as tasks_module
from models.datas_api.repositories.sqlite_base import SQLiteConnectionManager


def _init_tasks_db(db_path):
    conn = sqlite3.connect(db_path)
    conn.execute(
        """
        CREATE TABLE tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            func TEXT,
            type TEXT,
            trigger_type TEXT,
            trigger_args TEXT,
            args TEXT,
            kwargs TEXT,
            one_off INTEGER,
            description TEXT,
            consumed INTEGER DEFAULT 0
        )
        """
    )
    conn.commit()
    conn.close()


def test_get_tasks_connection_uses_sqlite_connection_manager(monkeypatch, tmp_path):
    db_path = str(tmp_path / "task.db")
    monkeypatch.setattr(tasks_module, "TASK_DB_PATH", db_path)

    manager = tasks_module.get_tasks_connection()

    assert isinstance(manager, SQLiteConnectionManager)
    assert manager.db_path == db_path
    assert manager.row_factory is sqlite3.Row


def test_legacy_task_routes_keep_legacy_permission_dependency():
    task_paths = {
        "/tasks/funcs",
        "/tasks",
        "/tasks/{task_id}",
    }

    for route in tasks_module.router.routes:
        if getattr(route, "path", "") not in task_paths:
            continue
        dependency_calls = {dep.call for dep in route.dependant.dependencies}
        assert tasks_module.check_legacy_api_permission in dependency_calls


@pytest.mark.asyncio
async def test_legacy_task_routes_crud_with_sqlite_base(monkeypatch, tmp_path):
    db_path = str(tmp_path / "task.db")
    _init_tasks_db(db_path)
    monkeypatch.setattr(tasks_module, "TASK_DB_PATH", db_path)

    created = await tasks_module.create_task(
        tasks_module.TaskCreate(
            func="send_notice",
            type="function",
            trigger_type="date",
            trigger_args='{"run_at": "2026-05-06"}',
            args='["hello"]',
            kwargs='{"room": "test"}',
            one_off=True,
            description="测试任务",
        )
    )

    assert created["status"] == "success"
    task_id = created["id"]

    listed = await tasks_module.get_tasks(page=1, page_size=10)
    assert listed["total"] == 1
    assert listed["data"][0]["id"] == task_id
    assert listed["data"][0]["trigger_args"].startswith("{")

    updated = await tasks_module.update_task(
        task_id,
        tasks_module.TaskUpdate(description="已更新", consumed=True),
    )
    assert updated == {"status": "success", "message": "任务更新成功"}

    done = await tasks_module.get_tasks(consumed="done")
    assert done["total"] == 1
    assert done["data"][0]["description"] == "已更新"

    deleted = await tasks_module.delete_task(task_id)
    assert deleted == {"status": "success", "message": "任务删除成功"}

    listed = await tasks_module.get_tasks()
    assert listed["total"] == 0


@pytest.mark.asyncio
async def test_legacy_task_routes_keep_error_contract(monkeypatch, tmp_path):
    db_path = str(tmp_path / "task.db")
    _init_tasks_db(db_path)
    monkeypatch.setattr(tasks_module, "TASK_DB_PATH", db_path)

    with pytest.raises(HTTPException) as exc_info:
        await tasks_module.update_task(999, tasks_module.TaskUpdate(description="missing"))

    assert exc_info.value.status_code == 404
