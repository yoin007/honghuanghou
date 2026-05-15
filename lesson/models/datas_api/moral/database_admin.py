# -*- coding: utf-8 -*-
"""
数据库管理 API

提供数据库文件的查看、表管理、清空重置等功能
仅限管理员访问
"""

import os
import logging
import hashlib
from datetime import datetime
from typing import Optional, List, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from models.datas_api.auth import User
from models.datas_api.moral.api_permission import require_configured_api_permission
from models.datas_api.moral.base import log_operation, get_moral_db
from models.datas_api.repositories.sqlite_base import get_sqlite_connection

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin/database", tags=["数据库管理"])

API_DATABASE_LIST = "/api/moral/admin/database/list"
API_DATABASE_TABLES = "/api/moral/admin/database/tables/{db_name}"
API_DATABASE_PROTECTED = "/api/moral/admin/database/protected-tables"
API_DATABASE_TOKEN = "/api/moral/admin/database/generate-token/{db_name}/{table_name}"
API_DATABASE_CLEAR = "/api/moral/admin/database/clear/{db_name}/{table_name}"
API_DATABASE_INTEGRITY = "/api/moral/admin/database/check-integrity"

# 数据库目录（lesson/databases）
DATABASES_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), "databases")

# 受保护表（不可清空）
PROTECTED_TABLES = {
    "moral.db": [
        "teacher", "student", "school_year", "semester",
        "grade", "class", "role", "grade_level_config",
        "moral_config", "moral_operation_log",
        "api_permission_config", "api_permission_module",
        "teacher_todo_series", "teacher_todo_group",  # 待办定义和群组定义
        "punishment_period_config",  # 处分期限配置
    ],
    "member.db": ["permission"],
    "invigilation.db": ["exam_project"],
}

# 可清空表（业务数据）
CLEARABLE_TABLES = {
    "moral.db": [
        ("student_daily_record", "日常表现记录"),
        ("student_school_record", "校级事件记录"),
        ("grade_moral_task", "德育任务配置"),
        ("student_task_finish", "学生任务完成记录"),
        ("moment_record", "点滴记录"),
        ("punishment_record", "处分记录"),
        ("punishment_revoke_application", "处分撤销申请"),
        ("punishment_expire_reminder", "处分到期提醒"),
        ("collective_event", "集体事件"),
        ("collective_event_distribution", "集体事件分配"),
        ("student_profile", "学生画像"),
        ("student_profile_history", "画像历史"),
        ("ai_consultation", "AI诊疗会话"),
        ("ai_consultation_message", "诊疗消息"),
        ("birthday_reminder", "生日提醒"),
        ("birthday_reminder_config", "生日提醒配置"),
        ("warning_log", "预警日志"),
        ("task_carryover_log", "结转日志"),
        ("teacher_todo_assignee", "待办协作教师"),
        ("teacher_todo_occurrence", "待办实例"),
        ("teacher_todo_reminder_log", "待办提醒日志"),
        ("teacher_todo_group_member", "群组成员"),
        ("semester_evaluation_record", "学期末评价记录"),
        ("moral_evaluation", "德育评价"),
    ],
    "task.db": [("tasks", "任务记录")],
    "messages.db": [("messages", "微信消息")],
    "queues.db": [("queues", "发送队列")],
    "homework.db": [("homework", "作业记录")],
    "daily.db": [("daily", "每日记录")],
    "inout.db": [("inout", "进出记录")],
    "filegather.db": [("files", "文件收集记录")],
    "notes.db": [("notes", "笔记")],
    "invigilation.db": [("invigilation_slot", "监考安排"), ("invigilation_notification_log", "通知日志")],
}

# 所有数据库表的中文名映射（用于前端显示）
TABLE_DISPLAY_NAMES = {
    "moral.db": {
        "teacher": "教师信息",
        "student": "学生信息",
        "school_year": "学年设置",
        "semester": "学期设置",
        "grade": "年级设置",
        "class": "班级设置",
        "role": "角色配置",
        "grade_level_config": "年级等级配置",
        "moral_config": "德育系统配置",
        "moral_operation_log": "操作日志",
        "api_permission_config": "API权限配置",
        "api_permission_module": "API权限模块",
        "student_daily_record": "日常表现记录",
        "student_school_record": "校级事件记录",
        "grade_moral_task": "德育任务配置",
        "student_task_finish": "学生任务完成记录",
        "moment_record": "点滴记录",
        "punishment_record": "处分记录",
        "punishment_period_config": "处分期限配置",
        "punishment_revoke_application": "处分撤销申请",
        "punishment_expire_reminder": "处分到期提醒",
        "collective_event": "集体事件",
        "collective_event_distribution": "集体事件分配",
        "student_profile": "学生画像",
        "student_profile_history": "画像历史",
        "ai_consultation": "AI诊疗会话",
        "ai_consultation_message": "诊疗消息",
        "birthday_reminder": "生日提醒",
        "birthday_reminder_config": "生日提醒配置",
        "daily_event_type": "日常事件类型",
        "school_event_type": "校级事件类型",
        "warning_log": "预警日志",
        "task_carryover_log": "结转日志",
        "teacher_todo_series": "待办定义",
        "teacher_todo_assignee": "待办协作教师",
        "teacher_todo_occurrence": "待办实例",
        "teacher_todo_reminder_log": "待办提醒日志",
        "teacher_todo_group": "协作群组",
        "teacher_todo_group_member": "群组成员",
        "semester_evaluation_record": "学期末评价记录",
        "moral_evaluation": "德育评价",
    },
    "member.db": {
        "permission": "微信权限配置",
    },
    "invigilation.db": {
        "exam_project": "考试项目",
        "invigilation_slot": "监考安排",
        "invigilation_notification_log": "通知日志",
    },
    "task.db": {
        "tasks": "任务记录",
    },
    "messages.db": {
        "messages": "微信消息",
    },
    "queues.db": {
        "queues": "发送队列",
    },
    "homework.db": {
        "homework": "作业记录",
    },
    "daily.db": {
        "daily": "每日记录",
    },
    "inout.db": {
        "inout": "进出记录",
    },
    "filegather.db": {
        "files": "文件收集记录",
    },
    "notes.db": {
        "notes": "笔记",
    },
    "colleges.db": {
        "colleges": "院校信息",
    },
}


# ==================== Pydantic 模型 ====================

class ClearTableRequest(BaseModel):
    """清空表请求"""
    confirmation_token: str = Field(..., description="确认令牌")


# ==================== 工具函数 ====================

def _resolve_database_path(db_name: str) -> str:
    """解析数据库路径，并阻止路径穿越。"""
    normalized_name = os.path.basename(db_name or "")
    if normalized_name != db_name or not normalized_name.endswith(".db"):
        raise HTTPException(400, "数据库名称不合法")

    db_path = os.path.abspath(os.path.join(DATABASES_DIR, normalized_name))
    databases_root = os.path.abspath(DATABASES_DIR)
    if os.path.dirname(db_path) != databases_root:
        raise HTTPException(400, "数据库名称不合法")
    return db_path


def _ensure_clearable_table(db_name: str, table_name: str) -> None:
    """仅允许清空显式登记的业务表。"""
    allowed_tables = {name for name, _ in CLEARABLE_TABLES.get(db_name, [])}
    if table_name not in allowed_tables:
        raise HTTPException(400, f"表 {table_name} 不在可清空白名单中")


def is_admin_user(user: User) -> bool:
    """检查是否是管理员"""
    return user.role in ["admin", "jiaowu"]


def get_table_count(db_path: str) -> int:
    """获取数据库中的表数量"""
    conn = get_sqlite_connection(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table'")
        return cursor.fetchone()[0]
    finally:
        conn.close()


def generate_confirmation_token(db_name: str, table_name: str, username: str) -> str:
    """生成确认令牌"""
    timestamp = datetime.now().strftime("%Y%m%d%H")
    data = f"{db_name}:{table_name}:{username}:{timestamp}"
    return hashlib.md5(data.encode()).hexdigest()


# ==================== API 路由 ====================

@router.get("/list", summary="获取数据库列表")
async def list_databases(user: User = Depends(require_configured_api_permission(API_DATABASE_LIST, "GET", allow_missing=False))):
    """获取所有数据库文件列表"""
    if not is_admin_user(user):
        raise HTTPException(403, "只有管理员可以访问")

    databases = []

    for filename in os.listdir(DATABASES_DIR):
        if not filename.endswith(".db"):
            continue
        # 排除备份和副本文件
        if "backup" in filename or "副本" in filename or ".raw_pwd" in filename:
            continue

        db_path = os.path.join(DATABASES_DIR, filename)

        try:
            size = os.path.getsize(db_path)
            table_count = get_table_count(db_path)
            databases.append({
                "name": filename,
                "size": size,
                "table_count": table_count,
                "status": "ok"
            })
        except Exception as e:
            logger.warning(f"获取数据库 {filename} 信息失败: {e}")
            databases.append({
                "name": filename,
                "size": 0,
                "table_count": 0,
                "status": "error"
            })

    # 按大小排序
    databases.sort(key=lambda x: x["size"], reverse=True)

    return {"success": True, "data": databases}


@router.get("/tables/{db_name}", summary="获取数据库表列表")
async def get_database_tables(db_name: str, user: User = Depends(require_configured_api_permission(API_DATABASE_TABLES, "GET", allow_missing=False))):
    """获取指定数据库的所有表"""
    if not is_admin_user(user):
        raise HTTPException(403, "只有管理员可以访问")

    db_path = _resolve_database_path(db_name)

    if not os.path.exists(db_path):
        raise HTTPException(404, f"数据库 {db_name} 不存在")

    tables = []
    protected_list = PROTECTED_TABLES.get(db_name, [])
    clearable_list = {name for name, _ in CLEARABLE_TABLES.get(db_name, [])}
    display_map = TABLE_DISPLAY_NAMES.get(db_name, {})

    try:
        conn = get_sqlite_connection(db_path)
        cursor = conn.cursor()

        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        table_names = [row[0] for row in cursor.fetchall()]

        for table_name in table_names:
            # 获取记录数
            try:
                cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
                row_count = cursor.fetchone()[0]
            except:
                row_count = 0

            # 获取中文名
            display_name = display_map.get(table_name, None)

            # 判断是否受保护、是否允许由管理页清空
            protected = table_name in protected_list

            tables.append({
                "name": table_name,
                "display_name": display_name,
                "row_count": row_count,
                "protected": protected,
                "clearable": table_name in clearable_list and not protected
            })

        conn.close()

    except Exception as e:
        logger.error(f"获取表列表失败: {e}")
        raise HTTPException(500, f"获取表列表失败: {str(e)}")

    return {"success": True, "data": tables}


@router.get("/protected-tables", summary="获取受保护表列表")
async def get_protected_tables(user: User = Depends(require_configured_api_permission(API_DATABASE_PROTECTED, "GET", allow_missing=False))):
    """获取所有受保护的表列表"""
    if not is_admin_user(user):
        raise HTTPException(403, "只有管理员可以访问")

    return {"success": True, "data": PROTECTED_TABLES}


@router.get("/generate-token/{db_name}/{table_name}", summary="生成清空确认令牌")
async def generate_clear_token(db_name: str, table_name: str, user: User = Depends(require_configured_api_permission(API_DATABASE_TOKEN, "GET", allow_missing=False))):
    """生成清空操作的确认令牌"""
    if not is_admin_user(user):
        raise HTTPException(403, "只有管理员可以访问")

    # 检查是否受保护，并要求命中可清空白名单
    protected_list = PROTECTED_TABLES.get(db_name, [])
    if table_name in protected_list:
        raise HTTPException(400, f"表 {table_name} 受保护，不可清空")
    _ensure_clearable_table(db_name, table_name)

    token = generate_confirmation_token(db_name, table_name, user.username)

    return {"success": True, "data": {"token": token, "expires_in": 300}}


@router.post("/clear/{db_name}/{table_name}", summary="清空表数据")
async def clear_table(
    db_name: str,
    table_name: str,
    request: ClearTableRequest,
    req: Request,
    user: User = Depends(require_configured_api_permission(API_DATABASE_CLEAR, "POST", allow_missing=False))
):
    """清空指定表的数据"""
    if not is_admin_user(user):
        raise HTTPException(403, "只有管理员可以执行此操作")

    # 检查是否受保护
    protected_list = PROTECTED_TABLES.get(db_name, [])
    if table_name in protected_list:
        raise HTTPException(400, f"表 {table_name} 受保护，不可清空")
    _ensure_clearable_table(db_name, table_name)

    # 验证确认令牌
    expected_token = generate_confirmation_token(db_name, table_name, user.username)
    if request.confirmation_token != expected_token:
        raise HTTPException(400, "确认令牌无效，请重新确认")

    db_path = _resolve_database_path(db_name)

    if not os.path.exists(db_path):
        raise HTTPException(404, f"数据库 {db_name} 不存在")

    try:
        conn = get_sqlite_connection(db_path)
        cursor = conn.cursor()

        # 获取清空前记录数
        cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
        original_count = cursor.fetchone()[0]

        # 执行清空
        cursor.execute(f"DELETE FROM {table_name}")
        conn.commit()
        conn.close()

        # 记录操作日志
        with get_moral_db() as moral_db:
            log_operation(
                db=moral_db,
                operator=user.username,
                operator_role=user.role,
                operation='CLEAR_TABLE',
                table_name=f"{db_name}.{table_name}",
                record_id=0,
                old_data={"row_count": original_count},
                new_data={"row_count": 0},
                ip_address=req.client.host if req.client else None
            )

        logger.info(f"管理员 {user.username} 清空表 {db_name}.{table_name}，删除 {original_count} 条记录")

        return {
            "success": True,
            "message": f"已清空表 {table_name}，删除 {original_count} 条记录",
            "data": {"deleted_count": original_count}
        }

    except Exception as e:
        logger.error(f"清空表失败: {e}")
        raise HTTPException(500, f"清空表失败: {str(e)}")


@router.get("/check-integrity", summary="检查数据库完整性")
async def check_database_integrity(user: User = Depends(require_configured_api_permission(API_DATABASE_INTEGRITY, "GET", allow_missing=False))):
    """检查所有数据库的表完整性"""
    if not is_admin_user(user):
        raise HTTPException(403, "只有管理员可以访问")

    from utils.db_integrity import check_database_integrity_on_startup, REQUIRED_TABLES, REQUIRED_COLUMNS

    result = {
        "status": "ok",
        "missing_tables": [],
        "missing_columns": [],
        "error_databases": [],
        "checked_at": datetime.now().isoformat()
    }

    for db_name, required_tables in REQUIRED_TABLES.items():
        db_path = os.path.join(DATABASES_DIR, db_name)

        if not os.path.exists(db_path):
            for table in required_tables:
                result["missing_tables"].append({
                    "database": db_name,
                    "table": table,
                    "reason": "数据库文件不存在"
                })
            result["status"] = "error"
            continue

        try:
            conn = get_sqlite_connection(db_path)
            cursor = conn.cursor()

            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            existing_tables = set(row[0] for row in cursor.fetchall())

            for table in required_tables:
                if table not in existing_tables:
                    result["missing_tables"].append({
                        "database": db_name,
                        "table": table,
                        "reason": "表不存在"
                    })
                    result["status"] = "warning"
                else:
                    # 检查字段
                    expected_columns = REQUIRED_COLUMNS.get(db_name, {}).get(table, [])
                    if expected_columns:
                        cursor.execute(f"PRAGMA table_info({table})")
                        existing_columns = [row[1] for row in cursor.fetchall()]
                        missing_cols = [col for col in expected_columns if col not in existing_columns]
                        if missing_cols:
                            result["missing_columns"].append({
                                "database": db_name,
                                "table": table,
                                "missing": missing_cols
                            })
                            result["status"] = "warning"

            conn.close()

        except Exception as e:
            result["error_databases"].append({
                "database": db_name,
                "reason": str(e)
            })
            result["status"] = "error"

    return {"success": True, "data": result}
