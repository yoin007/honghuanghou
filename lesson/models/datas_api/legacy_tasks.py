# -*- coding: utf-8 -*-
"""Legacy Tasks API - 任务管理接口。

Batch32: 从 datas_api_legacy.py 拆分任务管理逻辑。
"""

import json
import sqlite3
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from models.datas_api.auth import User, get_current_user
from models.datas_api.legacy_common import check_legacy_api_permission
from utils.db_config import TASK_DB


router = APIRouter()

TASK_DB_PATH = TASK_DB


class TaskCreate(BaseModel):
    func: str
    type: str = "function"
    trigger_type: str
    trigger_args: str
    args: str = None
    kwargs: str = None
    one_off: bool = True
    description: str = None


class TaskUpdate(BaseModel):
    func: Optional[str] = None
    type: Optional[str] = None
    trigger_type: Optional[str] = None
    trigger_args: Optional[str] = None
    args: Optional[str] = None
    kwargs: Optional[str] = None
    one_off: Optional[bool] = None
    description: Optional[str] = None
    consumed: Optional[bool] = None


def get_tasks_connection():
    """获取任务数据库连接管理器。"""
    from models.datas_api.repositories.sqlite_base import SQLiteConnectionManager

    return SQLiteConnectionManager(TASK_DB_PATH, row_factory=sqlite3.Row)


@router.get("/tasks/funcs", dependencies=[Depends(check_legacy_api_permission)])
async def get_available_funcs(current_user: User = Depends(get_current_user)):
    """获取可用的任务函数列表"""
    from models.task import Task
    task_obj = Task()
    funcs = task_obj.get_available_funcs()
    return {"funcs": funcs}


@router.get("/tasks", dependencies=[Depends(check_legacy_api_permission)])
async def get_tasks(
    page: int = 1,
    page_size: int = 10,
    search: str = None,
    consumed: str = None,  # 状态筛选: "all" 或 None=全部, "pending"=待执行, "done"=已执行
    current_user: User = Depends(get_current_user)
):
    """获取任务列表"""
    try:
        with get_tasks_connection() as conn:
            cursor = conn.cursor()

            # 构建基础查询条件
            where_conditions = []
            params = []

            # 搜索条件
            if search:
                where_conditions.append("(func LIKE ? OR description LIKE ?)")
                params.extend([f"%{search}%", f"%{search}%"])

            # 状态筛选
            if consumed == "pending":
                where_conditions.append("consumed = 0")
            elif consumed == "done":
                where_conditions.append("consumed = 1")

            # 构建 WHERE 子句
            where_clause = ""
            count_params = []
            if where_conditions:
                where_clause = " WHERE " + " AND ".join(where_conditions)
                count_params = params.copy()

            # 获取总数
            cursor.execute(f"SELECT COUNT(*) FROM tasks{where_clause}", tuple(count_params))
            total = cursor.fetchone()[0]

            # 获取数据
            sql = f"SELECT * FROM tasks{where_clause} ORDER BY id DESC LIMIT ? OFFSET ?"
            params.extend([page_size, (page - 1) * page_size])

            cursor.execute(sql, tuple(params))
            rows = cursor.fetchall()

        tasks = []
        for row in rows:
            task = dict(row)
            if task.get('trigger_args'):
                try:
                    task['trigger_args'] = json.dumps(json.loads(task['trigger_args']), ensure_ascii=False, indent=2)
                except:
                    pass
            if task.get('args'):
                try:
                    task['args'] = json.dumps(json.loads(task['args']), ensure_ascii=False, indent=2)
                except:
                    pass
            if task.get('kwargs'):
                try:
                    task['kwargs'] = json.dumps(json.loads(task['kwargs']), ensure_ascii=False, indent=2)
                except:
                    pass
            tasks.append(task)

        return {
            "total": total,
            "page": page,
            "page_size": page_size,
            "data": tasks
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取任务列表失败: {str(e)}")


@router.post("/tasks", dependencies=[Depends(check_legacy_api_permission)])
async def create_task(task: TaskCreate, current_user: User = Depends(get_current_user)):
    """创建任务"""
    try:
        with get_tasks_connection() as conn:
            cursor = conn.cursor()

            cursor.execute(
                """INSERT INTO tasks (func, type, trigger_type, trigger_args, args, kwargs, one_off, description, consumed)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    task.func,
                    task.type,
                    task.trigger_type,
                    task.trigger_args,
                    task.args,
                    task.kwargs,
                    task.one_off,
                    task.description,
                    False
                )
            )
            task_id = cursor.lastrowid

        return {"status": "success", "message": "任务创建成功", "id": task_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"创建任务失败: {str(e)}")


@router.put("/tasks/{task_id}", dependencies=[Depends(check_legacy_api_permission)])
async def update_task(task_id: int, task: TaskUpdate, current_user: User = Depends(get_current_user)):
    """更新任务"""
    try:
        with get_tasks_connection() as conn:
            cursor = conn.cursor()

            cursor.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
            if not cursor.fetchone():
                raise HTTPException(status_code=404, detail="任务不存在")

            update_fields = []
            update_values = []

            if task.func is not None:
                update_fields.append("func = ?")
                update_values.append(task.func)
            if task.type is not None:
                update_fields.append("type = ?")
                update_values.append(task.type)
            if task.trigger_type is not None:
                update_fields.append("trigger_type = ?")
                update_values.append(task.trigger_type)
            if task.trigger_args is not None:
                update_fields.append("trigger_args = ?")
                update_values.append(task.trigger_args)
            if task.args is not None:
                update_fields.append("args = ?")
                update_values.append(task.args)
            if task.kwargs is not None:
                update_fields.append("kwargs = ?")
                update_values.append(task.kwargs)
            if task.one_off is not None:
                update_fields.append("one_off = ?")
                update_values.append(task.one_off)
            if task.description is not None:
                update_fields.append("description = ?")
                update_values.append(task.description)
            if task.consumed is not None:
                update_fields.append("consumed = ?")
                update_values.append(task.consumed)

            if not update_fields:
                raise HTTPException(status_code=400, detail="没有提供更新数据")

            update_values.append(task_id)
            sql = f"UPDATE tasks SET {', '.join(update_fields)} WHERE id = ?"
            cursor.execute(sql, tuple(update_values))

        return {"status": "success", "message": "任务更新成功"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"更新任务失败: {str(e)}")


@router.delete("/tasks/{task_id}", dependencies=[Depends(check_legacy_api_permission)])
async def delete_task(task_id: int, current_user: User = Depends(get_current_user)):
    """删除任务"""
    try:
        with get_tasks_connection() as conn:
            cursor = conn.cursor()

            cursor.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
            if not cursor.fetchone():
                raise HTTPException(status_code=404, detail="任务不存在")

            cursor.execute("DELETE FROM tasks WHERE id = ?", (task_id,))

        return {"status": "success", "message": "任务删除成功"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"删除任务失败: {str(e)}")
