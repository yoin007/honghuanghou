# -*- coding: utf-8 -*-
"""
导师制 API - 导师名单管理 + 导师谈话记录

- 名单按学期管理：学生每学期恰有一位导师，期中可换导师
- 谈话记录冗余导师快照，换导师后历史记录仍显示原导师
- 风险等级联动德育预警：红→严重(error)，黄→一般(warning)，绿→无
- 升级路径：grade(年级)/xuefa(学发)/psychology(心理)/principal(校领导)
"""

import logging
import io
import json
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field, field_validator
from datetime import date

from .base import (
    get_moral_db,
    log_operation,
    get_current_semester,
    get_student_class_snapshot,
    get_record_data_scope,
    append_record_scope_condition,
    record_in_scope,
    record_action_flags,
    target_student_in_scope,
    _teacher_identity_candidates,
)
from .api_permission import require_configured_api_permission
from models.datas_api.auth import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/mentor-roster", tags=["导师名单"])
talk_router = APIRouter(prefix="/mentor-talks", tags=["导师谈话"])

API_ROSTER_LIST = "/api/moral/mentor-roster"
API_ROSTER_ASSIGN = "/api/moral/mentor-roster/assign"
API_ROSTER_BATCH = "/api/moral/mentor-roster/batch"
API_ROSTER_DELETE = "/api/moral/mentor-roster/delete"
API_ROSTER_TEMPLATE = "/api/moral/mentor-roster/template"
API_ROSTER_MY_STUDENTS = "/api/moral/mentor-roster/my-students"

API_TALK_LIST = "/api/moral/mentor-talks"
API_TALK_CREATE = "/api/moral/mentor-talks/create"
API_TALK_UPDATE = "/api/moral/mentor-talks/update"
API_TALK_DELETE = "/api/moral/mentor-talks/delete"
API_TALK_STATISTICS = "/api/moral/mentor-talks/statistics"
API_TALK_NOT_TALKED = "/api/moral/mentor-talks/not-talked"
API_TALK_BATCH = "/api/moral/mentor-talks/batch"
API_TALK_TEMPLATE = "/api/moral/mentor-talks/template"
API_TALK_CATEGORIES = "/api/moral/mentor-talks/categories"
API_TALK_CATEGORIES_UPDATE = "/api/moral/mentor-talks/categories/update"
API_TALK_STUDENT_STATUS = "/api/moral/mentor-talks/student-status"

TALK_CATEGORIES = ["思想引导", "学业辅导", "心理疏导", "生活指导", "生涯向导"]
TALK_CATEGORIES_CONFIG_KEY = "mentor_talk_categories"
RISK_LEVELS = ["green", "yellow", "red"]
ESCALATE_PATHS = ["grade", "xuefa", "psychology", "principal"]


def _get_talk_categories(db) -> List[str]:
    """读取谈话类别（moral_config 可人工配置，未配置时用默认五类）"""
    row = db.query_one(
        "SELECT config_value FROM moral_config WHERE config_key = ?", (TALK_CATEGORIES_CONFIG_KEY,)
    )
    if row and row.get("config_value"):
        try:
            categories = json.loads(row["config_value"])
            if isinstance(categories, list) and categories:
                return [str(c).strip() for c in categories if str(c).strip()]
        except Exception:
            pass
    return list(TALK_CATEGORIES)


ESCALATE_PATH_LABELS = {
    "grade": "年级",
    "xuefa": "学发",
    "psychology": "心理",
    "principal": "校领导",
}


def _model_dict(model) -> dict:
    """Pydantic 模型转 dict，date 字段转 ISO 字符串（供操作日志 JSON 序列化）"""
    return {
        key: (value.isoformat() if isinstance(value, date) else value)
        for key, value in model.dict().items()
    }


def _ensure_schema(db):
    """确保导师制相关表结构完整（幂等）"""
    db.execute("""
        CREATE TABLE IF NOT EXISTS teacher_mentor_student (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            teacher_id TEXT NOT NULL,
            teacher_name TEXT NOT NULL,
            student_id TEXT NOT NULL,
            student_name TEXT,
            class_id INTEGER,
            grade_id INTEGER,
            semester_id INTEGER NOT NULL,
            is_active INTEGER DEFAULT 1,
            assigned_by TEXT,
            assigned_at TEXT DEFAULT (datetime('now','localtime')),
            created_at TEXT DEFAULT (datetime('now','localtime')),
            updated_at TEXT DEFAULT (datetime('now','localtime')),
            UNIQUE(student_id, semester_id)
        )
    """)
    db.execute(
        "CREATE INDEX IF NOT EXISTS idx_mentor_roster_teacher ON teacher_mentor_student(teacher_id, semester_id)"
    )
    db.execute(
        "CREATE INDEX IF NOT EXISTS idx_mentor_roster_class ON teacher_mentor_student(class_id, semester_id)"
    )

    db.execute("""
        CREATE TABLE IF NOT EXISTS mentor_talk_record (
            record_id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id TEXT NOT NULL,
            class_id INTEGER NOT NULL,
            grade_id INTEGER NOT NULL,
            semester_id INTEGER NOT NULL,
            mentor_id TEXT NOT NULL,
            mentor_name TEXT NOT NULL,
            talk_date TEXT NOT NULL,
            talk_category TEXT NOT NULL,
            subject TEXT,
            location TEXT,
            reason TEXT,
            student_statement TEXT,
            summary TEXT,
            diagnosis TEXT,
            risk_level TEXT DEFAULT 'green',
            need_follow_up INTEGER DEFAULT 0,
            next_talk_date TEXT,
            escalated INTEGER DEFAULT 0,
            escalate_path TEXT,
            escalated_at TEXT,
            recorder TEXT NOT NULL,
            is_deleted INTEGER DEFAULT 0,
            created_at TEXT DEFAULT (datetime('now','localtime')),
            updated_at TEXT DEFAULT (datetime('now','localtime'))
        )
    """)
    db.execute(
        "CREATE INDEX IF NOT EXISTS idx_mentor_talk_student ON mentor_talk_record(student_id, talk_date)"
    )
    db.execute(
        "CREATE INDEX IF NOT EXISTS idx_mentor_talk_mentor ON mentor_talk_record(mentor_id, semester_id)"
    )
    db.execute(
        "CREATE INDEX IF NOT EXISTS idx_mentor_talk_risk ON mentor_talk_record(risk_level)"
    )

    # 待办联动：记录关联的待办 series（后续版本新增列，幂等补齐）
    columns = [row['name'] for row in db.query_all("PRAGMA table_info(mentor_talk_record)") or []]
    if 'todo_series_id' not in columns:
        db.execute("ALTER TABLE mentor_talk_record ADD COLUMN todo_series_id INTEGER")

    # 预警规则行（warning_log.rule_id 非空外键，必须有对应 warning_config 行）
    # trigger_type 不以 score_/count_/escalation_ 开头，日常预警调度任务会自动跳过
    db.execute("""
        INSERT INTO warning_config (rule_name, trigger_type, trigger_value, notify_roles, is_active, is_deleted)
        SELECT '导师谈话风险', 'mentor_talk_risk', 0, '["cleader","xuefa"]', 1, 0
        WHERE NOT EXISTS (
            SELECT 1 FROM warning_config WHERE trigger_type = 'mentor_talk_risk'
        )
    """)


def _resolve_semester(db, semester_id: Optional[int]) -> dict:
    """解析学期参数：未传则取当前学期"""
    if semester_id:
        semester = db.query_one(
            "SELECT * FROM semester WHERE semester_id = ?", (semester_id,)
        )
        if not semester:
            raise HTTPException(404, f"学期 {semester_id} 不存在")
        return semester
    semester = get_current_semester(db)
    if not semester:
        raise HTTPException(400, "未配置当前学期，请先在学年学期配置中设置")
    return semester


def _resolve_teacher(db, teacher_id: Optional[str], teacher_name: Optional[str]) -> dict:
    """解析导师身份：优先 teacher_id，其次姓名"""
    teacher = None
    if teacher_id:
        teacher = db.query_one(
            "SELECT teacher_id, name, wxid, is_active FROM teacher WHERE teacher_id = ?",
            (teacher_id,),
        )
    if not teacher and teacher_name:
        teacher = db.query_one(
            "SELECT teacher_id, name, wxid, is_active FROM teacher WHERE name = ? AND is_active = 1",
            (teacher_name,),
        )
    if not teacher:
        raise HTTPException(404, f"教师不存在：{teacher_id or teacher_name}")
    return teacher


# =============================================================================
# 导师名单
# =============================================================================

class MentorAssign(BaseModel):
    """分配导师"""
    teacher_id: Optional[str] = Field(None, description="导师教师ID（与 teacher.teacher_id 一致）")
    teacher_name: Optional[str] = Field(None, description="导师姓名（teacher_id 缺省时按姓名解析）")
    student_ids: List[str] = Field(..., description="学生学号列表")
    semester_id: Optional[int] = Field(None, description="学期ID，默认当前学期")


class MentorBatchItem(BaseModel):
    """批量导入行"""
    teacher_id: Optional[str] = None
    teacher_name: Optional[str] = None
    student_id: str
    student_name: Optional[str] = None


class MentorBatchImport(BaseModel):
    """批量导入导师名单"""
    semester_id: Optional[int] = None
    items: List[MentorBatchItem]


@router.get("", summary="获取导师名单")
async def get_mentor_roster(
    semester_id: Optional[int] = Query(None),
    grade_id: Optional[int] = Query(None),
    class_id: Optional[int] = Query(None),
    teacher_id: Optional[str] = Query(None),
    keyword: Optional[str] = Query(None, description="学生姓名/学号/导师姓名模糊搜索"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=10000),
    user: User = Depends(require_configured_api_permission(API_ROSTER_LIST, "GET", allow_missing=False)),
):
    """获取导师名单（按学期）

    权限说明：
    - teacher: 只能查看自己的导生
    - g_leader: 只能查看管理年级的名单
    - admin/jiaowu/xuefa: 全部名单
    """
    with get_moral_db() as db:
        _ensure_schema(db)
        semester = _resolve_semester(db, semester_id)

        conditions = ["mr.semester_id = ?"]
        params = [semester["semester_id"]]

        # 数据范围：teacher 只看自己导生，g_leader 只看管理年级
        teacher_ids, teacher_names = _teacher_identity_candidates(user, db)
        is_admin_like = any(r in ("admin", "jiaowu", "xuefa") for r in (user.role or "").split("/"))
        is_grade_leader = any(r == "g_leader" for r in (user.role or "").split("/"))

        if not is_admin_like:
            scope_parts = []
            scope_params = []
            if teacher_ids or teacher_names:
                id_match = " OR ".join(["mr.teacher_id = ?"] * len(teacher_ids))
                name_match = " OR ".join(["mr.teacher_name = ?"] * len(teacher_names))
                scope_parts.append(f"({id_match} OR {name_match})")
                scope_params.extend(teacher_ids + teacher_names)
            if is_grade_leader:
                from .base import get_teacher_grade_ids
                my_grade_ids = get_teacher_grade_ids(user, db)
                if my_grade_ids:
                    placeholders = ", ".join(["?"] * len(my_grade_ids))
                    scope_parts.append(f"mr.grade_id IN ({placeholders})")
                    scope_params.extend(my_grade_ids)
            if not scope_parts:
                raise HTTPException(403, "无导师名单查看权限")
            conditions.append("(" + " OR ".join(scope_parts) + ")")
            params.extend(scope_params)

        if grade_id:
            conditions.append("mr.grade_id = ?")
            params.append(grade_id)
        if class_id:
            conditions.append("mr.class_id = ?")
            params.append(class_id)
        if teacher_id:
            conditions.append("mr.teacher_id = ?")
            params.append(teacher_id)
        if keyword:
            conditions.append("(mr.student_name LIKE ? OR mr.student_id LIKE ? OR mr.teacher_name LIKE ?)")
            params.extend([f"%{keyword}%"] * 3)

        where_clause = " AND ".join(conditions)
        total = db.query_value(
            f"SELECT COUNT(*) FROM teacher_mentor_student mr WHERE {where_clause}",
            tuple(params),
        )

        offset = (page - 1) * page_size
        rows = db.query_all(f"""
            SELECT mr.*, c.class_name, g.grade_name, sem.semester_name
            FROM teacher_mentor_student mr
            LEFT JOIN class c ON mr.class_id = c.class_id
            LEFT JOIN grade g ON mr.grade_id = g.grade_id
            LEFT JOIN semester sem ON mr.semester_id = sem.semester_id
            WHERE {where_clause}
            ORDER BY mr.teacher_name, c.class_name, mr.student_id
            LIMIT ? OFFSET ?
        """, tuple(params) + (page_size, offset))

        return {
            "success": True,
            "data": {
                "items": rows,
                "total": total,
                "page": page,
                "page_size": page_size,
                "semester_id": semester["semester_id"],
                "semester_name": semester["semester_name"],
            },
        }


@router.get("/my-students", summary="我的导生列表")
async def get_my_mentor_students(
    semester_id: Optional[int] = Query(None),
    user: User = Depends(require_configured_api_permission(API_ROSTER_MY_STUDENTS, "GET", allow_missing=False)),
):
    """获取当前用户作为导师的导生列表（当前学期）"""
    with get_moral_db() as db:
        _ensure_schema(db)
        semester = _resolve_semester(db, semester_id)

        teacher_ids, teacher_names = _teacher_identity_candidates(user, db)
        if not teacher_ids and not teacher_names:
            return {"success": True, "data": {"items": [], "semester_id": semester["semester_id"]}}

        id_match = " OR ".join(["teacher_id = ?"] * len(teacher_ids))
        name_match = " OR ".join(["teacher_name = ?"] * len(teacher_names))
        rows = db.query_all(f"""
            SELECT mr.*, c.class_name, g.grade_name
            FROM teacher_mentor_student mr
            LEFT JOIN class c ON mr.class_id = c.class_id
            LEFT JOIN grade g ON mr.grade_id = g.grade_id
            WHERE mr.semester_id = ? AND mr.is_active = 1
              AND ({id_match} OR {name_match})
            ORDER BY c.class_name, mr.student_id
        """, tuple([semester["semester_id"]] + teacher_ids + teacher_names))

        return {
            "success": True,
            "data": {
                "items": rows,
                "semester_id": semester["semester_id"],
                "semester_name": semester["semester_name"],
            },
        }


@router.get("/template", summary="下载导师名单导入模板")
async def download_roster_template(
    user: User = Depends(require_configured_api_permission(API_ROSTER_TEMPLATE, "GET", allow_missing=False)),
):
    """下载导师名单 Excel 导入模板"""
    from openpyxl import Workbook

    wb = Workbook()
    ws = wb.active
    ws.title = "导师名单"
    ws.append(["教师ID", "教师姓名", "学号", "学生姓名"])

    sample_rows = [
        ["T_张三", "张三", "20240101", "李四"],
        ["", "张三", "20240102", "王五"],
    ]
    for row in sample_rows:
        ws.append(row)

    output = io.BytesIO()
    wb.save(output)
    output.seek(0)

    from urllib.parse import quote
    filename = quote("导师名单导入模板.xlsx")
    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{filename}"},
    )


@router.post("/assign", summary="分配/更换导师")
async def assign_mentor(
    data: MentorAssign,
    request: Request,
    user: User = Depends(require_configured_api_permission(API_ROSTER_ASSIGN, "POST", allow_missing=False)),
):
    """给学生分配导师（同一学期同一学生仅一位导师，重复分配即更换导师）"""
    with get_moral_db() as db:
        _ensure_schema(db)
        semester = _resolve_semester(db, data.semester_id)
        teacher = _resolve_teacher(db, data.teacher_id, data.teacher_name)

        if not data.student_ids:
            raise HTTPException(400, "请选择要分配的学生")

        success_count = 0
        update_count = 0
        errors = []
        for student_id in data.student_ids:
            student = db.query_one(
                "SELECT student_id, name, class_id, grade_id, status FROM student WHERE student_id = ?",
                (student_id,),
            )
            if not student:
                errors.append({"student_id": student_id, "reason": "学生不存在"})
                continue
            if not target_student_in_scope(db, user, API_ROSTER_ASSIGN, student):
                raise HTTPException(403, f"学生 {student_id} 超出授权范围，禁止分配")

            existing = db.query_one(
                "SELECT id FROM teacher_mentor_student WHERE student_id = ? AND semester_id = ?",
                (student_id, semester["semester_id"]),
            )
            if existing:
                db.execute("""
                    UPDATE teacher_mentor_student
                    SET teacher_id = ?, teacher_name = ?, student_name = ?, class_id = ?,
                        grade_id = ?, is_active = 1, assigned_by = ?,
                        updated_at = datetime('now','localtime')
                    WHERE id = ?
                """, (
                    teacher["teacher_id"], teacher["name"], student["name"],
                    student["class_id"], student["grade_id"], user.username, existing["id"],
                ))
                update_count += 1
            else:
                db.execute("""
                    INSERT INTO teacher_mentor_student
                    (teacher_id, teacher_name, student_id, student_name, class_id, grade_id,
                     semester_id, is_active, assigned_by)
                    VALUES (?, ?, ?, ?, ?, ?, ?, 1, ?)
                """, (
                    teacher["teacher_id"], teacher["name"], student_id, student["name"],
                    student["class_id"], student["grade_id"], semester["semester_id"], user.username,
                ))
                success_count += 1

        log_operation(
            db, user.username, user.role, 'MENTOR_ASSIGN', 'teacher_mentor_student',
            teacher["teacher_id"], semester["semester_id"],
            new_data={
                "teacher": teacher["name"],
                "student_ids": data.student_ids,
                "inserted": success_count,
                "updated": update_count,
            },
            ip_address=request.client.host if request.client else None,
        )

        return {
            "success": True,
            "message": f"分配完成：新增 {success_count} 人，更换导师 {update_count} 人",
            "data": {
                "success_count": success_count,
                "update_count": update_count,
                "errors": errors,
            },
        }


@router.post("/batch", summary="批量导入导师名单")
async def batch_import_roster(
    data: MentorBatchImport,
    request: Request,
    user: User = Depends(require_configured_api_permission(API_ROSTER_BATCH, "POST", allow_missing=False)),
):
    """批量导入导师名单（前端解析 Excel 后提交 JSON 行）"""
    with get_moral_db() as db:
        _ensure_schema(db)
        semester = _resolve_semester(db, data.semester_id)

        if not data.items:
            raise HTTPException(400, "导入数据为空")

        success_count = 0
        update_count = 0
        errors = []
        for index, item in enumerate(data.items, start=2):  # Excel 首行为表头
            row_no = index
            try:
                teacher = _resolve_teacher(db, item.teacher_id, item.teacher_name)
            except HTTPException:
                errors.append({"row": row_no, "student_id": item.student_id,
                               "reason": f"教师不存在：{item.teacher_id or item.teacher_name}"})
                continue

            student = db.query_one(
                "SELECT student_id, name, class_id, grade_id FROM student WHERE student_id = ?",
                (item.student_id,),
            )
            if not student:
                errors.append({"row": row_no, "student_id": item.student_id, "reason": "学生不存在"})
                continue
            if item.student_name and item.student_name.strip() and item.student_name.strip() != student["name"]:
                errors.append({
                    "row": row_no, "student_id": item.student_id,
                    "reason": f"学生姓名与学号不匹配（学号 {item.student_id} 对应：{student['name']}）",
                })
                continue
            if not target_student_in_scope(db, user, API_ROSTER_BATCH, student):
                errors.append({"row": row_no, "student_id": item.student_id, "reason": "学生超出授权范围"})
                continue

            existing = db.query_one(
                "SELECT id FROM teacher_mentor_student WHERE student_id = ? AND semester_id = ?",
                (student["student_id"], semester["semester_id"]),
            )
            if existing:
                db.execute("""
                    UPDATE teacher_mentor_student
                    SET teacher_id = ?, teacher_name = ?, student_name = ?, class_id = ?,
                        grade_id = ?, is_active = 1, assigned_by = ?,
                        updated_at = datetime('now','localtime')
                    WHERE id = ?
                """, (
                    teacher["teacher_id"], teacher["name"], student["name"],
                    student["class_id"], student["grade_id"], user.username, existing["id"],
                ))
                update_count += 1
            else:
                db.execute("""
                    INSERT INTO teacher_mentor_student
                    (teacher_id, teacher_name, student_id, student_name, class_id, grade_id,
                     semester_id, is_active, assigned_by)
                    VALUES (?, ?, ?, ?, ?, ?, ?, 1, ?)
                """, (
                    teacher["teacher_id"], teacher["name"], student["student_id"], student["name"],
                    student["class_id"], student["grade_id"], semester["semester_id"], user.username,
                ))
                success_count += 1

        log_operation(
            db, user.username, user.role, 'BATCH_IMPORT', 'teacher_mentor_student',
            0, semester["semester_id"],
            new_data={
                "total": len(data.items),
                "inserted": success_count,
                "updated": update_count,
                "failed": len(errors),
            },
            ip_address=request.client.host if request.client else None,
        )

        return {
            "success": True,
            "message": f"导入完成：新增 {success_count} 行，更换导师 {update_count} 行，失败 {len(errors)} 行",
            "data": {
                "success_count": success_count,
                "update_count": update_count,
                "errors": errors,
            },
        }


@router.delete("/{assignment_id}", summary="删除导师分配")
async def delete_roster_assignment(
    assignment_id: int,
    request: Request,
    user: User = Depends(require_configured_api_permission(API_ROSTER_DELETE, "DELETE", allow_missing=False)),
):
    """删除一条导师分配记录"""
    with get_moral_db() as db:
        _ensure_schema(db)
        assignment = db.query_one(
            "SELECT * FROM teacher_mentor_student WHERE id = ?", (assignment_id,)
        )
        if not assignment:
            raise HTTPException(404, "分配记录不存在")

        # 范围校验：g_leader 只能删管理年级的分配
        user_roles = (user.role or "").split("/")
        is_admin_like = any(r in ("admin", "jiaowu", "xuefa") for r in user_roles)
        if not is_admin_like:
            if any(r == "g_leader" for r in user_roles):
                from .base import get_teacher_grade_ids
                my_grade_ids = get_teacher_grade_ids(user, db)
                if assignment["grade_id"] not in my_grade_ids:
                    raise HTTPException(403, "只能删除管理年级的导师分配")
            else:
                raise HTTPException(403, "无删除导师分配权限")

        db.execute("DELETE FROM teacher_mentor_student WHERE id = ?", (assignment_id,))

        log_operation(
            db, user.username, user.role, 'DELETE', 'teacher_mentor_student', assignment_id,
            old_data=dict(assignment),
            ip_address=request.client.host if request.client else None,
        )

        return {"success": True, "message": "分配已删除"}


# =============================================================================
# 导师谈话记录
# =============================================================================

class MentorTalkCreate(BaseModel):
    """创建导师谈话记录"""
    student_id: str = Field(..., description="学生学号")
    talk_date: date = Field(..., description="谈话日期")
    talk_category: str = Field(..., description="谈话类别（可配置，默认五类）")
    subject: Optional[str] = Field(None, description="主题")
    location: Optional[str] = Field(None, description="地点")
    reason: Optional[str] = Field(None, description="事由")
    student_statement: Optional[str] = Field(None, description="学生自述")
    summary: str = Field(..., min_length=1, description="谈话纪要（必填）")
    diagnosis: Optional[str] = Field(None, description="导师诊断")
    risk_level: str = Field("green", description="风险等级：green/yellow/red")
    need_follow_up: int = Field(0, description="是否继续跟进：1/0")
    next_talk_date: Optional[date] = Field(None, description="下次谈话时间")
    escalated: int = Field(0, description="是否升级：1/0")
    escalate_path: Optional[str] = Field(None, description="升级路径：grade/xuefa/psychology/principal")

    @field_validator("subject", "location", "reason", "student_statement", "diagnosis",
                     "escalate_path", "next_talk_date", mode="before")
    @classmethod
    def _empty_str_to_none(cls, v):
        """可选字段的空字符串归一为 None（前端清空日期/路径时可能传 ""）"""
        if isinstance(v, str) and not v.strip():
            return None
        return v


class MentorTalkUpdate(BaseModel):
    """更新导师谈话记录"""
    talk_date: Optional[date] = None
    talk_category: Optional[str] = None
    subject: Optional[str] = None
    location: Optional[str] = None
    reason: Optional[str] = None
    student_statement: Optional[str] = None
    summary: Optional[str] = None
    diagnosis: Optional[str] = None
    risk_level: Optional[str] = None
    need_follow_up: Optional[int] = None
    next_talk_date: Optional[date] = None
    escalated: Optional[int] = None
    escalate_path: Optional[str] = None

    @field_validator("subject", "location", "reason", "student_statement", "diagnosis",
                     "escalate_path", "next_talk_date", mode="before")
    @classmethod
    def _empty_str_to_none(cls, v):
        if isinstance(v, str) and not v.strip():
            return None
        return v


def _validate_talk_fields(db, data) -> None:
    """校验谈话记录枚举字段（谈话类别按可配置列表校验）"""
    if data.talk_category and data.talk_category not in _get_talk_categories(db):
        raise HTTPException(400, f"谈话类别无效，可选：{'、'.join(_get_talk_categories(db))}")
    if data.risk_level and data.risk_level not in RISK_LEVELS:
        raise HTTPException(400, "风险等级无效，可选：green/yellow/red")
    if data.escalate_path and data.escalate_path not in ESCALATE_PATHS:
        raise HTTPException(400, f"升级路径无效，可选：{'、'.join(ESCALATE_PATHS)}")
    if getattr(data, "escalated", 0) and not data.escalate_path:
        raise HTTPException(400, "升级时必须选择升级路径")


def _maybe_create_risk_warning(db, record: dict) -> None:
    """红色/黄色风险谈话记录 → 写入德育预警

    红 → error（严重预警），黄 → warning（一般预警），绿 → 无。
    同学生 + 同规则 + 同学期 + 同级别已有活跃预警则去重跳过。
    """
    risk_level = record.get("risk_level")
    if risk_level not in ("red", "yellow"):
        return

    rule = db.query_one(
        "SELECT id FROM warning_config WHERE trigger_type = 'mentor_talk_risk' AND is_active = 1 AND is_deleted = 0"
    )
    if not rule:
        logger.warning("导师谈话预警规则缺失（mentor_talk_risk），跳过预警写入")
        return

    warning_level = "error" if risk_level == "red" else "warning"
    existing = db.query_one(
        """SELECT id FROM warning_log
           WHERE student_id = ? AND rule_id = ? AND semester_id = ?
             AND warning_level = ? AND status = 'active'
           LIMIT 1""",
        (record["student_id"], rule["id"], record["semester_id"], warning_level),
    )
    if existing:
        return

    student = db.query_one(
        """SELECT s.name, c.class_name FROM student s
           LEFT JOIN class c ON s.class_id = c.class_id
           WHERE s.student_id = ?""",
        (record["student_id"],),
    )
    student_label = f"{student['name']}（{record['student_id']}）" if student else record["student_id"]
    risk_label = "红" if risk_level == "red" else "黄"
    level_label = "严重" if risk_level == "red" else "一般"

    message = (
        f"【导师谈话预警】\n"
        f"学生：{student_label}\n"
        f"班级：{student.get('class_name') if student else '-'}\n"
        f"风险等级：{risk_label}（{level_label}预警）\n"
        f"谈话类别：{record.get('talk_category') or '-'}\n"
        f"主题：{record.get('subject') or '-'}\n"
        f"导师诊断：{record.get('diagnosis') or '-'}\n"
        f"导师：{record.get('mentor_name') or '-'}\n"
        f"谈话时间：{record.get('talk_date') or '-'}\n"
        f"请及时关注并采取干预措施。"
    )

    db.execute(
        """INSERT INTO warning_log
           (student_id, rule_id, semester_id, warning_level, message, status)
           VALUES (?, ?, ?, ?, ?, 'active')""",
        (record["student_id"], rule["id"], record["semester_id"], warning_level, message),
    )


def _send_mentor_escalation_notification(db, record: dict, student: dict) -> None:
    """升级通知：按升级路径发送给对应层级（微信 sendqueue）

    - grade: 年级主任（grade.leader_ids → teacher.wxid）
    - xuefa: moral_config 的 xuefa_notify_wxid
    - psychology / principal: moral_config 的 psychology_notify_wxid / principal_notify_wxid
      （管理员在 moral_config 中配置微信接收人；未配置则记录日志跳过）
    """
    from sendqueue import send_text

    path = record.get("escalate_path")
    if not path:
        return

    student_label = f"{student['name']}（{record['student_id']}）" if student else record["student_id"]
    message = (
        f"【导师谈话升级】\n"
        f"学生：{student_label}\n"
        f"风险等级：{ {'red': '红', 'yellow': '黄'}.get(record.get('risk_level'), record.get('risk_level')) }\n"
        f"谈话类别：{record.get('talk_category') or '-'}\n"
        f"主题：{record.get('subject') or '-'}\n"
        f"导师诊断：{record.get('diagnosis') or '-'}\n"
        f"导师：{record.get('mentor_name') or '-'}\n"
        f"谈话时间：{record.get('talk_date') or '-'}\n"
        f"升级路径：{ESCALATE_PATH_LABELS.get(path, path)}，请及时跟进处理。"
    )

    recipients = []
    if path == "grade":
        grade_id = record.get("grade_id") or (student or {}).get("grade_id")
        if grade_id:
            leader_ids = db.query_one(
                "SELECT leader_ids FROM grade WHERE grade_id = ?", (grade_id,)
            )
            for lid in (leader_ids.get("leader_ids") or "").split(",") if leader_ids else []:
                lid = lid.strip()
                if not lid:
                    continue
                teacher = db.query_one("SELECT wxid FROM teacher WHERE teacher_id = ?", (lid,))
                if teacher and teacher.get("wxid"):
                    recipients.append(teacher["wxid"])
    else:
        config_key = {
            "xuefa": "xuefa_notify_wxid",
            "psychology": "psychology_notify_wxid",
            "principal": "principal_notify_wxid",
        }.get(path)
        if config_key:
            config = db.query_one(
                "SELECT config_value FROM moral_config WHERE config_key = ?", (config_key,)
            )
            if config and config.get("config_value"):
                recipients.append(config["config_value"])
            else:
                logger.warning("升级通知接收人未配置（moral_config.%s），跳过发送", config_key)

    for recipient in recipients:
        try:
            send_text(message, recipient, producer="mentor_escalation")
            logger.info("导师谈话升级通知已发送: %s -> %s", path, recipient)
        except Exception as e:
            logger.error("发送导师谈话升级通知失败: %s", e)


def _sync_next_talk_todo(db, record: dict) -> None:
    """下次谈话时间联动教师待办

    - 设置了下次谈话时间：为导师创建/更新一条一次性待办（one_off，到日期提醒）
    - 清空了下次谈话时间：停用对应待办
    待办归属导师（mentor_id），通过 todo_series_id 关联，编辑记录时同步更新。
    """
    from models.datas_api.teacher_todo import ensure_teacher_todo_schema

    ensure_teacher_todo_schema(db)

    series_id = record.get("todo_series_id")
    next_talk_date = record.get("next_talk_date")

    if not next_talk_date:
        if series_id:
            db.execute(
                "UPDATE teacher_todo_series SET is_active = 0, updated_at = datetime('now','localtime') WHERE id = ?",
                (series_id,),
            )
        return

    student = db.query_one(
        "SELECT name FROM student WHERE student_id = ?", (record["student_id"],)
    )
    student_label = student["name"] if student else record["student_id"]
    title = f"导师谈话跟进：{student_label}"
    desc_parts = [f"谈话记录ID：{record['record_id']}"]
    if record.get("subject"):
        desc_parts.append(f"主题：{record['subject']}")
    description = "\n".join(desc_parts)

    if series_id:
        existing = db.query_one(
            "SELECT id, is_active FROM teacher_todo_series WHERE id = ?", (series_id,)
        )
        if existing:
            db.execute(
                """UPDATE teacher_todo_series
                   SET title = ?, description = ?, start_date = ?, is_active = 1,
                       updated_at = datetime('now','localtime')
                   WHERE id = ?""",
                (title, description, next_talk_date, series_id),
            )
            # 重建一次性实例（仅替换未完成的旧实例）
            db.execute(
                "DELETE FROM teacher_todo_occurrence WHERE todo_series_id = ? AND status = 'pending'",
                (series_id,),
            )
            db.execute(
                """INSERT INTO teacher_todo_occurrence (todo_series_id, occurrence_date, scheduled_at, status)
                   VALUES (?, ?, ?, 'pending')""",
                (series_id, next_talk_date, f"{next_talk_date} 08:00:00"),
            )
            return
        series_id = None

    # 新建待办（归属导师，微信提醒默认开启）
    creator_id = record.get("recorder") or "system"
    creator = db.query_one(
        "SELECT teacher_id, name FROM teacher WHERE teacher_id = ? OR name = ? LIMIT 1",
        (creator_id, creator_id),
    )
    db.execute(
        """INSERT INTO teacher_todo_series
           (title, description, creator_teacher_id, creator_name, todo_type,
            start_date, time_of_day, wechat_notify_enabled, is_active)
           VALUES (?, ?, ?, ?, 'one_off', ?, '08:00', 1, 1)""",
        (title, description,
         creator["teacher_id"] if creator else creator_id,
         creator["name"] if creator else creator_id,
         next_talk_date),
    )
    series_id = db.lastrowid()

    # 指派给导师
    assignee = db.query_one(
        "SELECT teacher_id, name FROM teacher WHERE teacher_id = ? OR name = ? LIMIT 1",
        (record.get("mentor_id"), record.get("mentor_name")),
    )
    mentor_teacher_id = assignee["teacher_id"] if assignee else record.get("mentor_id")
    db.execute(
        """INSERT OR IGNORE INTO teacher_todo_assignee (todo_series_id, teacher_id, teacher_name)
           VALUES (?, ?, ?)""",
        (series_id, mentor_teacher_id, record.get("mentor_name")),
    )
    db.execute(
        """INSERT INTO teacher_todo_occurrence (todo_series_id, occurrence_date, scheduled_at, status)
           VALUES (?, ?, ?, 'pending')""",
        (series_id, next_talk_date, f"{next_talk_date} 08:00:00"),
    )

    db.execute(
        "UPDATE mentor_talk_record SET todo_series_id = ? WHERE record_id = ?",
        (series_id, record["record_id"]),
    )


@talk_router.get("", summary="获取导师谈话记录列表")
async def get_mentor_talks(
    semester_id: Optional[int] = Query(None),
    student_id: Optional[str] = Query(None),
    risk_level: Optional[str] = Query(None),
    talk_category: Optional[str] = Query(None),
    need_follow_up: Optional[int] = Query(None),
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    scope: Optional[str] = Query(None, description="数据范围: mentor_students(我的导生), own_grade(我的年级), all(全校)"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=10000),
    user: User = Depends(require_configured_api_permission(API_TALK_LIST, "GET", allow_missing=False)),
):
    """获取导师谈话记录列表（数据范围：导师见导生，年级主任见管理年级，管理角色见全部）"""
    with get_moral_db() as db:
        _ensure_schema(db)

        conditions = ["mtr.is_deleted = 0"]
        params = []

        if semester_id:
            conditions.append("mtr.semester_id = ?")
            params.append(semester_id)

        view_scope = get_record_data_scope(
            db, user, API_TALK_LIST,
            all_permissions=['mentor_talk_manage'],
            own_class_permissions=[],
            own_permissions=['mentor_talk_manage'],
        )

        if scope:
            # scope 语义与全系统一致：own=我创建的(recorder)，mentor_students=我的导生(名单表)，
            # own_grade=管理年级，all=全校
            scope_allowed = (
                (scope == "own" and view_scope.get("can_own"))
                or (scope == "mentor_students" and view_scope.get("can_mentor"))
                or (scope == "own_grade" and view_scope.get("can_own_grade"))
                or (scope == "all" and view_scope.get("can_all"))
            )
            if not scope_allowed:
                raise HTTPException(403, f"无权访问 scope={scope} 的数据")

            scope_conditions = []
            scope_params = []
            if scope == "own":
                scope_conditions.append("mtr.recorder = ?")
                scope_params.append(user.username)
            elif scope == "mentor_students":
                mentor_ids = view_scope.get("mentor_student_ids") or []
                if mentor_ids:
                    placeholders = ", ".join(["?"] * len(mentor_ids))
                    scope_conditions.append(f"mtr.student_id IN ({placeholders})")
                    scope_params.extend(mentor_ids)
                else:
                    scope_conditions.append("1 = 0")
            elif scope == "own_grade":
                my_grade_class_ids = view_scope.get("my_grade_class_ids") or []
                if my_grade_class_ids:
                    placeholders = ", ".join(["?"] * len(my_grade_class_ids))
                    scope_conditions.append(f"mtr.class_id IN ({placeholders})")
                    scope_params.extend(my_grade_class_ids)
                else:
                    scope_conditions.append("1 = 0")
            elif scope == "all":
                pass

            if scope_conditions:
                conditions.append("(" + " OR ".join(scope_conditions) + ")")
                params.extend(scope_params)
        else:
            append_record_scope_condition(
                conditions, params, view_scope,
                table_alias="mtr", username=user.username,
            )

        if student_id:
            conditions.append("mtr.student_id = ?")
            params.append(student_id)
        if risk_level:
            conditions.append("mtr.risk_level = ?")
            params.append(risk_level)
        if talk_category:
            conditions.append("mtr.talk_category = ?")
            params.append(talk_category)
        if need_follow_up is not None:
            conditions.append("mtr.need_follow_up = ?")
            params.append(need_follow_up)
        if start_date:
            conditions.append("mtr.talk_date >= ?")
            params.append(start_date)
        if end_date:
            conditions.append("mtr.talk_date <= ?")
            params.append(end_date)

        where_clause = " AND ".join(conditions)
        total = db.query_value(
            f"SELECT COUNT(*) FROM mentor_talk_record mtr WHERE {where_clause}",
            tuple(params),
        )

        offset = (page - 1) * page_size
        rows = db.query_all(f"""
            SELECT mtr.*, s.name as student_name, c.class_name, g.grade_name, sem.semester_name
            FROM mentor_talk_record mtr
            JOIN student s ON mtr.student_id = s.student_id
            LEFT JOIN class c ON mtr.class_id = c.class_id
            LEFT JOIN grade g ON mtr.grade_id = g.grade_id
            LEFT JOIN semester sem ON mtr.semester_id = sem.semester_id
            WHERE {where_clause}
            ORDER BY mtr.talk_date DESC, mtr.created_at DESC
            LIMIT ? OFFSET ?
        """, tuple(params) + (page_size, offset))

        edit_scope = get_record_data_scope(
            db, user, API_TALK_UPDATE,
            all_permissions=['mentor_talk_manage'],
            own_class_permissions=[],
            own_permissions=['mentor_talk_manage'],
        )
        delete_scope = get_record_data_scope(
            db, user, API_TALK_DELETE,
            all_permissions=['mentor_talk_manage'],
            own_class_permissions=[],
            own_permissions=['mentor_talk_manage'],
        )
        for row in rows:
            row.update(record_action_flags(
                row, edit_scope, delete_scope, username=user.username,
            ))

        return {
            "success": True,
            "data": {
                "items": rows,
                "total": total,
                "page": page,
                "page_size": page_size,
            },
        }


def _create_single_talk(db, data: MentorTalkCreate, user: User, ip_address: Optional[str]) -> int:
    """创建一条谈话记录的共享内核（单个创建与批量导入复用）。

    返回 record_id；校验失败抛 HTTPException（批量导入按行捕获）。
    """
    _validate_talk_fields(db, data)

    student = get_student_class_snapshot(db, data.student_id)
    if not student:
        raise HTTPException(404, f"学生 {data.student_id} 不存在或不在校")
    student = {**student, "student_id": data.student_id}
    if not target_student_in_scope(db, user, API_TALK_CREATE, student):
        raise HTTPException(403, "只能给授权范围内（自己的导生）的学生创建谈话记录")

    semester = get_current_semester(db)
    if not semester:
        raise HTTPException(400, "未配置当前学期")
    semester_id = semester["semester_id"]

    # 导师快照：优先取名单中的当前导师
    roster = db.query_one(
        "SELECT teacher_id, teacher_name FROM teacher_mentor_student WHERE student_id = ? AND semester_id = ?",
        (data.student_id, semester_id),
    )
    if roster:
        mentor_id, mentor_name = roster["teacher_id"], roster["teacher_name"]
    else:
        teacher_ids, teacher_names = _teacher_identity_candidates(user, db)
        mentor_id = teacher_ids[0] if teacher_ids else user.username
        mentor_name = teacher_names[0] if teacher_names else user.username
        if not any(r in ("admin", "jiaowu", "xuefa", "g_leader") for r in (user.role or "").split("/")):
            raise HTTPException(400, "该学生尚未分配导师，请先在导师名单中分配")

    db.execute("""
        INSERT INTO mentor_talk_record
        (student_id, class_id, grade_id, semester_id, mentor_id, mentor_name,
         talk_date, talk_category, subject, location, reason, student_statement,
         summary, diagnosis, risk_level, need_follow_up, next_talk_date,
         escalated, escalate_path, escalated_at, recorder)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        data.student_id, student["class_id"], student["grade_id"], semester_id,
        mentor_id, mentor_name, data.talk_date, data.talk_category,
        data.subject, data.location, data.reason, data.student_statement,
        data.summary, data.diagnosis, data.risk_level, data.need_follow_up,
        data.next_talk_date, data.escalated, data.escalate_path,
        date.today().isoformat() if data.escalated else None,
        user.username,
    ))
    record_id = db.lastrowid()

    record = db.query_one("SELECT * FROM mentor_talk_record WHERE record_id = ?", (record_id,))
    _maybe_create_risk_warning(db, record)
    _sync_next_talk_todo(db, record)
    if data.escalated:
        student_info = db.query_one(
            "SELECT student_id, name, grade_id FROM student WHERE student_id = ?", (data.student_id,)
        )
        _send_mentor_escalation_notification(db, record, student_info)

    log_operation(
        db, user.username, user.role, 'CREATE', 'mentor_talk_record', record_id,
        semester_id=semester_id, new_data=_model_dict(data),
        ip_address=ip_address,
    )
    return record_id


@talk_router.post("", summary="创建导师谈话记录")
async def create_mentor_talk(
    data: MentorTalkCreate,
    request: Request,
    user: User = Depends(require_configured_api_permission(API_TALK_CREATE, "POST", allow_missing=False)),
):
    """创建导师谈话记录（导师快照取自名单；红/黄风险自动写入德育预警）"""
    with get_moral_db() as db:
        _ensure_schema(db)
        record_id = _create_single_talk(
            db, data, user,
            request.client.host if request.client else None,
        )
        return {"success": True, "message": "谈话记录创建成功", "data": {"record_id": record_id}}


@talk_router.put("/{record_id}", summary="更新导师谈话记录")
async def update_mentor_talk(
    record_id: int,
    data: MentorTalkUpdate,
    request: Request,
    user: User = Depends(require_configured_api_permission(API_TALK_UPDATE, "PUT", allow_missing=False)),
):
    """更新导师谈话记录（风险等级升为红/黄或新升级时补发预警/通知）"""
    with get_moral_db() as db:
        _ensure_schema(db)
        _validate_talk_fields(db, data)

        record = db.query_one(
            "SELECT * FROM mentor_talk_record WHERE record_id = ? AND is_deleted = 0",
            (record_id,),
        )
        if not record:
            raise HTTPException(404, "谈话记录不存在")

        action_scope = get_record_data_scope(
            db, user, API_TALK_UPDATE,
            all_permissions=['mentor_talk_manage'],
            own_class_permissions=[],
            own_permissions=['mentor_talk_manage'],
        )
        if not record_in_scope(record, action_scope, username=user.username):
            raise HTTPException(403, "无权修改该谈话记录")

        updates = []
        params = []
        # 显式传 null 的字段视为清空（如清空下次谈话时间）；未传字段不更新
        provided_fields = set(getattr(data, "model_fields_set", ()) or ())
        for field in ("talk_date", "talk_category", "subject", "location", "reason",
                      "student_statement", "summary", "diagnosis", "risk_level",
                      "need_follow_up", "next_talk_date", "escalated", "escalate_path"):
            value = getattr(data, field)
            if value is not None:
                if field == "next_talk_date" and isinstance(value, date):
                    value = value.isoformat()
                updates.append(f"{field} = ?")
                params.append(value)
            elif field in provided_fields:
                updates.append(f"{field} = ?")
                params.append(None)
        if data.escalated and not record.get("escalated_at") and not (data.escalate_path and not record.get("escalate_path")):
            updates.append("escalated_at = ?")
            params.append(date.today().isoformat())

        if not updates:
            return {"success": True, "message": "无需更新"}

        updates.append("updated_at = datetime('now','localtime')")
        params.append(record_id)
        db.execute(
            f"UPDATE mentor_talk_record SET {', '.join(updates)} WHERE record_id = ?",
            tuple(params),
        )

        updated = db.query_one("SELECT * FROM mentor_talk_record WHERE record_id = ?", (record_id,))
        _maybe_create_risk_warning(db, updated)
        _sync_next_talk_todo(db, updated)
        newly_escalated = updated.get("escalated") and (
            not record.get("escalated") or record.get("escalate_path") != updated.get("escalate_path")
        )
        if newly_escalated:
            student_info = db.query_one(
                "SELECT student_id, name, grade_id FROM student WHERE student_id = ?",
                (updated["student_id"],),
            )
            _send_mentor_escalation_notification(db, updated, student_info)

        log_operation(
            db, user.username, user.role, 'UPDATE', 'mentor_talk_record', record_id,
            old_data=dict(record), new_data=_model_dict(data),
            ip_address=request.client.host if request.client else None,
        )

        return {"success": True, "message": "谈话记录更新成功"}


@talk_router.delete("/{record_id}", summary="删除导师谈话记录")
async def delete_mentor_talk(
    record_id: int,
    request: Request,
    user: User = Depends(require_configured_api_permission(API_TALK_DELETE, "DELETE", allow_missing=False)),
):
    """删除导师谈话记录（软删除）"""
    with get_moral_db() as db:
        _ensure_schema(db)
        record = db.query_one(
            "SELECT * FROM mentor_talk_record WHERE record_id = ? AND is_deleted = 0",
            (record_id,),
        )
        if not record:
            raise HTTPException(404, "谈话记录不存在")

        action_scope = get_record_data_scope(
            db, user, API_TALK_DELETE,
            all_permissions=['mentor_talk_manage'],
            own_class_permissions=[],
            own_permissions=['mentor_talk_manage'],
        )
        if not record_in_scope(record, action_scope, username=user.username):
            raise HTTPException(403, "无权删除该谈话记录")

        db.execute(
            "UPDATE mentor_talk_record SET is_deleted = 1, updated_at = datetime('now','localtime') WHERE record_id = ?",
            (record_id,),
        )

        log_operation(
            db, user.username, user.role, 'DELETE', 'mentor_talk_record', record_id,
            old_data=dict(record),
            ip_address=request.client.host if request.client else None,
        )

        return {"success": True, "message": "谈话记录已删除"}


@talk_router.get("/statistics", summary="导师谈话工作量统计")
async def get_mentor_talk_statistics(
    semester_id: Optional[int] = Query(None),
    grade_id: Optional[int] = Query(None),
    month: Optional[str] = Query(None, description="统计月份 YYYY-MM，默认整个学期"),
    user: User = Depends(require_configured_api_permission(API_TALK_STATISTICS, "GET", allow_missing=False)),
):
    """按导师统计谈话覆盖情况：应谈人数/已谈人数/覆盖率/红黄风险数"""
    with get_moral_db() as db:
        _ensure_schema(db)
        semester = _resolve_semester(db, semester_id)
        semester_id_val = semester["semester_id"]

        conditions = ["r.semester_id = ?"]
        params = [semester_id_val]
        if grade_id:
            conditions.append("r.grade_id = ?")
            params.append(grade_id)

        # 数据范围：admin/jiaowu/xuefa 全校，g_leader 管理年级，teacher 只看自己名下
        user_roles = (user.role or "").split("/")
        if not any(r in ("admin", "jiaowu", "xuefa", "g_leader") for r in user_roles):
            if not any(r == "teacher" for r in user_roles):
                raise HTTPException(403, "无工作量统计权限")
            teacher_ids, teacher_names = _teacher_identity_candidates(user, db)
            identity_parts = []
            identity_params = []
            if teacher_ids:
                placeholders = ", ".join(["?"] * len(teacher_ids))
                identity_parts.append(f"r.teacher_id IN ({placeholders})")
                identity_params.extend(teacher_ids)
            if teacher_names:
                placeholders = ", ".join(["?"] * len(teacher_names))
                identity_parts.append(f"r.teacher_name IN ({placeholders})")
                identity_params.extend(teacher_names)
            if not identity_parts:
                return {"success": True, "data": {"items": [], "semester_id": semester_id_val}}
            conditions.append("(" + " OR ".join(identity_parts) + ")")
            params.extend(identity_params)
        elif not any(r in ("admin", "jiaowu", "xuefa") for r in user_roles):
            # g_leader：只统计管理年级
            from .base import get_teacher_grade_ids
            my_grade_ids = get_teacher_grade_ids(user, db)
            if not my_grade_ids:
                return {"success": True, "data": {"items": [], "semester_id": semester_id_val}}
            placeholders = ", ".join(["?"] * len(my_grade_ids))
            conditions.append(f"r.grade_id IN ({placeholders})")
            params.extend(my_grade_ids)

        where_clause = " AND ".join(conditions)
        month_clause = ""
        if month:
            # month 占位符位于 JOIN 子句（先于 WHERE 的占位符），参数必须放在最前
            month_clause = " AND strftime('%Y-%m', t.talk_date) = ?"

        rows = db.query_all(f"""
            SELECT r.teacher_id, r.teacher_name,
                   COUNT(DISTINCT r.student_id) AS assigned_count,
                   COUNT(DISTINCT CASE WHEN t.record_id IS NOT NULL THEN r.student_id END) AS talked_count,
                   COUNT(DISTINCT CASE WHEN t.risk_level = 'red' THEN t.student_id END) AS red_count,
                   COUNT(DISTINCT CASE WHEN t.risk_level = 'yellow' THEN t.student_id END) AS yellow_count
            FROM teacher_mentor_student r
            LEFT JOIN mentor_talk_record t
              ON t.student_id = r.student_id AND t.semester_id = r.semester_id
              AND t.is_deleted = 0{month_clause}
            WHERE {where_clause}
            GROUP BY r.teacher_id, r.teacher_name
            ORDER BY assigned_count DESC
        """, tuple(([month] if month else []) + params))

        items = []
        for row in rows:
            assigned = row["assigned_count"] or 0
            talked = row["talked_count"] or 0
            items.append({
                "teacher_id": row["teacher_id"],
                "teacher_name": row["teacher_name"],
                "assigned_count": assigned,
                "talked_count": talked,
                "coverage_pct": round(talked / assigned * 100, 1) if assigned else 0,
                "red_count": row["red_count"] or 0,
                "yellow_count": row["yellow_count"] or 0,
            })

        return {
            "success": True,
            "data": {
                "items": items,
                "semester_id": semester_id_val,
                "semester_name": semester["semester_name"],
            },
        }


@talk_router.get("/not-talked", summary="本月未谈话学生列表")
async def get_not_talked_students(
    semester_id: Optional[int] = Query(None),
    grade_id: Optional[int] = Query(None),
    month: Optional[str] = Query(None, description="月份 YYYY-MM，默认当前月"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=10000),
    user: User = Depends(require_configured_api_permission(API_TALK_NOT_TALKED, "GET", allow_missing=False)),
):
    """查询指定月份内导师尚未谈话的学生（用于每月谈话提醒）"""
    from datetime import datetime as _dt

    with get_moral_db() as db:
        _ensure_schema(db)
        semester = _resolve_semester(db, semester_id)
        month = month or _dt.now().strftime("%Y-%m")

        conditions = ["r.semester_id = ?", "r.is_active = 1"]
        params = [semester["semester_id"]]
        if grade_id:
            conditions.append("r.grade_id = ?")
            params.append(grade_id)

        # 数据范围：admin/jiaowu/xuefa 全校，g_leader 管理年级，teacher 只看自己名下
        user_roles = (user.role or "").split("/")
        if not any(r in ("admin", "jiaowu", "xuefa", "g_leader") for r in user_roles):
            if not any(r == "teacher" for r in user_roles):
                raise HTTPException(403, "无未谈话提醒查看权限")
            teacher_ids, teacher_names = _teacher_identity_candidates(user, db)
            identity_parts = []
            identity_params = []
            if teacher_ids:
                placeholders = ", ".join(["?"] * len(teacher_ids))
                identity_parts.append(f"r.teacher_id IN ({placeholders})")
                identity_params.extend(teacher_ids)
            if teacher_names:
                placeholders = ", ".join(["?"] * len(teacher_names))
                identity_parts.append(f"r.teacher_name IN ({placeholders})")
                identity_params.extend(teacher_names)
            if not identity_parts:
                return {"success": True, "data": {"items": [], "total": 0, "month": month}}
            conditions.append("(" + " OR ".join(identity_parts) + ")")
            params.extend(identity_params)
        elif not any(r in ("admin", "jiaowu", "xuefa") for r in user_roles):
            # g_leader：只看管理年级
            from .base import get_teacher_grade_ids
            my_grade_ids = get_teacher_grade_ids(user, db)
            if not my_grade_ids:
                return {"success": True, "data": {"items": [], "total": 0, "month": month}}
            placeholders = ", ".join(["?"] * len(my_grade_ids))
            conditions.append(f"r.grade_id IN ({placeholders})")
            params.extend(my_grade_ids)

        where_clause = " AND ".join(conditions)
        total = db.query_value(f"""
            SELECT COUNT(*) FROM teacher_mentor_student r
            WHERE {where_clause}
              AND NOT EXISTS (
                  SELECT 1 FROM mentor_talk_record t
                  WHERE t.student_id = r.student_id AND t.semester_id = r.semester_id
                    AND t.is_deleted = 0 AND strftime('%Y-%m', t.talk_date) = ?
              )
        """, tuple(params + [month]))

        offset = (page - 1) * page_size
        rows = db.query_all(f"""
            SELECT r.student_id, r.student_name, r.teacher_id, r.teacher_name,
                   c.class_name, g.grade_name
            FROM teacher_mentor_student r
            LEFT JOIN class c ON r.class_id = c.class_id
            LEFT JOIN grade g ON r.grade_id = g.grade_id
            WHERE {where_clause}
              AND NOT EXISTS (
                  SELECT 1 FROM mentor_talk_record t
                  WHERE t.student_id = r.student_id AND t.semester_id = r.semester_id
                    AND t.is_deleted = 0 AND strftime('%Y-%m', t.talk_date) = ?
              )
            ORDER BY r.teacher_name, c.class_name, r.student_id
            LIMIT ? OFFSET ?
        """, tuple(params + [month, page_size, offset]))

        return {
            "success": True,
            "data": {
                "items": rows,
                "total": total,
                "page": page,
                "page_size": page_size,
                "month": month,
            },
        }



class TalkCategoriesUpdate(BaseModel):
    """更新谈话类别配置"""
    categories: List[str] = Field(..., description="谈话类别列表", min_length=1)


@talk_router.get("/categories", summary="获取谈话类别列表")
async def get_talk_categories(
    user: User = Depends(require_configured_api_permission(API_TALK_CATEGORIES, "GET", allow_missing=False)),
):
    """获取谈话类别（moral_config 可人工配置，未配置时返回默认五类）"""
    with get_moral_db() as db:
        _ensure_schema(db)
        return {"success": True, "data": {"categories": _get_talk_categories(db)}}


@talk_router.put("/categories", summary="配置谈话类别")
async def update_talk_categories(
    data: TalkCategoriesUpdate,
    request: Request,
    user: User = Depends(require_configured_api_permission(API_TALK_CATEGORIES_UPDATE, "PUT", allow_missing=False)),
):
    """人工配置谈话类别（管理员/学发部/年级主任）"""
    with get_moral_db() as db:
        _ensure_schema(db)

        user_roles = (user.role or "").split("/")
        if not any(r in ("admin", "jiaowu", "xuefa", "g_leader") for r in user_roles):
            raise HTTPException(403, "只有管理角色可以配置谈话类别")

        categories = [str(c).strip() for c in data.categories if str(c).strip()]
        if not categories:
            raise HTTPException(400, "谈话类别不能为空")
        if len(set(categories)) != len(categories):
            raise HTTPException(400, "谈话类别不能重复")

        existing = db.query_one(
            "SELECT config_value FROM moral_config WHERE config_key = ?", (TALK_CATEGORIES_CONFIG_KEY,)
        )
        if existing:
            db.execute(
                "UPDATE moral_config SET config_value = ? WHERE config_key = ?",
                (json.dumps(categories, ensure_ascii=False), TALK_CATEGORIES_CONFIG_KEY),
            )
        else:
            db.execute(
                "INSERT INTO moral_config (config_key, config_value) VALUES (?, ?)",
                (TALK_CATEGORIES_CONFIG_KEY, json.dumps(categories, ensure_ascii=False)),
            )

        log_operation(
            db, user.username, user.role, 'UPDATE', 'moral_config', 0,
            new_data={"config_key": TALK_CATEGORIES_CONFIG_KEY, "categories": categories},
            ip_address=request.client.host if request.client else None,
        )

        return {"success": True, "message": "谈话类别已更新", "data": {"categories": categories}}


@talk_router.get("/student-status", summary="导生本月谈话状态名单")
async def get_mentor_student_status(
    semester_id: Optional[int] = Query(None),
    grade_id: Optional[int] = Query(None),
    month: Optional[str] = Query(None, description="月份 YYYY-MM，默认当前月"),
    user: User = Depends(require_configured_api_permission(API_TALK_STUDENT_STATUS, "GET", allow_missing=False)),
):
    """名单内每个学生本月是否已谈、谈话次数、最近谈话日期（导师看自己导生，年级主任看管理年级，管理角色看全部）"""
    from datetime import datetime as _dt

    with get_moral_db() as db:
        _ensure_schema(db)
        semester = _resolve_semester(db, semester_id)
        month = month or _dt.now().strftime("%Y-%m")

        conditions = ["r.semester_id = ?", "r.is_active = 1"]
        params = [semester["semester_id"]]
        if grade_id:
            conditions.append("r.grade_id = ?")
            params.append(grade_id)

        # 数据范围：与 not-talked 一致
        user_roles = (user.role or "").split("/")
        if not any(r in ("admin", "jiaowu", "xuefa", "g_leader") for r in user_roles):
            if not any(r == "teacher" for r in user_roles):
                raise HTTPException(403, "无导生名单查看权限")
            teacher_ids, teacher_names = _teacher_identity_candidates(user, db)
            identity_parts = []
            identity_params = []
            if teacher_ids:
                placeholders = ", ".join(["?"] * len(teacher_ids))
                identity_parts.append(f"r.teacher_id IN ({placeholders})")
                identity_params.extend(teacher_ids)
            if teacher_names:
                placeholders = ", ".join(["?"] * len(teacher_names))
                identity_parts.append(f"r.teacher_name IN ({placeholders})")
                identity_params.extend(teacher_names)
            if not identity_parts:
                return {"success": True, "data": {"items": [], "month": month}}
            conditions.append("(" + " OR ".join(identity_parts) + ")")
            params.extend(identity_params)
        elif not any(r in ("admin", "jiaowu", "xuefa") for r in user_roles):
            from .base import get_teacher_grade_ids
            my_grade_ids = get_teacher_grade_ids(user, db)
            if not my_grade_ids:
                return {"success": True, "data": {"items": [], "month": month}}
            placeholders = ", ".join(["?"] * len(my_grade_ids))
            conditions.append(f"r.grade_id IN ({placeholders})")
            params.extend(my_grade_ids)

        where_clause = " AND ".join(conditions)
        rows = db.query_all(f"""
            SELECT r.student_id, r.student_name, r.teacher_id, r.teacher_name,
                   c.class_name, g.grade_name,
                   COUNT(t.record_id) AS talked_count,
                   MAX(t.talk_date) AS last_talk_date
            FROM teacher_mentor_student r
            LEFT JOIN class c ON r.class_id = c.class_id
            LEFT JOIN grade g ON r.grade_id = g.grade_id
            LEFT JOIN mentor_talk_record t
              ON t.student_id = r.student_id AND t.semester_id = r.semester_id
              AND t.is_deleted = 0 AND strftime('%Y-%m', t.talk_date) = ?
            WHERE {where_clause}
            GROUP BY r.student_id, r.student_name, r.teacher_id, r.teacher_name,
                     c.class_name, g.grade_name
            ORDER BY r.teacher_name, c.class_name, r.student_id
        """, tuple([month] + params))

        items = []
        for row in rows:
            talked = int(row["talked_count"] or 0)
            items.append({
                "student_id": row["student_id"],
                "student_name": row["student_name"],
                "teacher_name": row["teacher_name"],
                "class_name": row["class_name"],
                "grade_name": row["grade_name"],
                "talked_count": talked,
                "last_talk_date": row["last_talk_date"],
                "talked": talked > 0,
            })

        return {
            "success": True,
            "data": {
                "items": items,
                "month": month,
                "semester_id": semester["semester_id"],
            },
        }


class MentorTalkBatchItem(BaseModel):
    """批量导入谈话记录行（前端解析 Excel 后提交）"""
    student_id: str
    student_name: Optional[str] = Field(None, description="学生姓名（用于与学号核对）")
    talk_date: str = Field(..., description="谈话日期 YYYY-MM-DD")
    talk_category: str
    summary: str = Field(..., min_length=1, description="谈话纪要（必填）")
    subject: Optional[str] = None
    location: Optional[str] = None
    reason: Optional[str] = None
    student_statement: Optional[str] = None
    diagnosis: Optional[str] = None
    risk_level: str = Field("green", description="green/yellow/red")
    need_follow_up: int = Field(0, description="1/0")
    next_talk_date: Optional[str] = Field(None, description="下次谈话时间 YYYY-MM-DD")
    escalated: int = Field(0, description="1/0")
    escalate_path: Optional[str] = Field(None, description="grade/xuefa/psychology/principal")


class MentorTalkBatchImport(BaseModel):
    """批量导入导师谈话记录"""
    items: List[MentorTalkBatchItem]


@talk_router.post("/batch", summary="批量导入导师谈话记录")
async def batch_import_mentor_talks(
    data: MentorTalkBatchImport,
    request: Request,
    user: User = Depends(require_configured_api_permission(API_TALK_BATCH, "POST", allow_missing=False)),
):
    """批量导入谈话记录。

    逐行校验：学生必须在导入人授权范围内（target_scope，导师即自己的导生），
    超出范围的行记入失败明细，不影响其他行。
    """
    with get_moral_db() as db:
        _ensure_schema(db)
        if not data.items:
            raise HTTPException(400, "导入数据为空")

        ip = request.client.host if request.client else None
        success_count = 0
        errors = []
        for index, item in enumerate(data.items, start=2):  # Excel 首行为表头
            try:
                # 姓名-学号核对：填了姓名且与库中不一致 → 行级失败
                if item.student_name and item.student_name.strip():
                    stu = db.query_one(
                        "SELECT name FROM student WHERE student_id = ?", (item.student_id,)
                    )
                    if stu and stu["name"] != item.student_name.strip():
                        errors.append({
                            "row": index, "student_id": item.student_id,
                            "reason": f"学生姓名与学号不匹配（学号 {item.student_id} 对应：{stu['name']}）",
                        })
                        continue
                talk_data = MentorTalkCreate(
                    student_id=item.student_id,
                    talk_date=item.talk_date,
                    talk_category=item.talk_category,
                    summary=item.summary,
                    subject=item.subject,
                    location=item.location,
                    reason=item.reason,
                    student_statement=item.student_statement,
                    diagnosis=item.diagnosis,
                    risk_level=item.risk_level,
                    need_follow_up=item.need_follow_up,
                    next_talk_date=item.next_talk_date,
                    escalated=item.escalated,
                    escalate_path=item.escalate_path,
                )
                _create_single_talk(db, talk_data, user, ip)
                success_count += 1
            except HTTPException as e:
                errors.append({"row": index, "student_id": item.student_id, "reason": e.detail})
            except Exception as e:
                logger.exception("批量导入谈话记录第 %s 行失败", index)
                errors.append({"row": index, "student_id": item.student_id, "reason": f"导入失败：{e}"})

        log_operation(
            db, user.username, user.role, 'BATCH_IMPORT', 'mentor_talk_record', 0,
            new_data={"total": len(data.items), "inserted": success_count, "failed": len(errors)},
            ip_address=ip,
        )

        return {
            "success": True,
            "message": f"导入完成：成功 {success_count} 条，失败 {len(errors)} 条",
            "data": {"success_count": success_count, "failed_count": len(errors), "errors": errors},
        }


@talk_router.get("/template", summary="下载谈话记录导入模板")
async def download_talk_template(
    user: User = Depends(require_configured_api_permission(API_TALK_TEMPLATE, "GET", allow_missing=False)),
):
    """下载谈话记录 Excel 批量导入模板（含填写说明）"""
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill, Alignment
    from urllib.parse import quote

    wb = Workbook()
    ws = wb.active
    ws.title = "谈话记录"
    headers = ["学号", "学生姓名", "谈话日期", "谈话类别", "主题", "地点", "事由", "学生自述",
               "谈话纪要", "导师诊断", "风险等级", "继续跟进", "下次谈话时间", "是否升级", "升级路径"]
    header_font = Font(name="Arial", bold=True, color="FFFFFF")
    header_fill = PatternFill("solid", start_color="4472C4")
    center = Alignment(horizontal="center", vertical="center")
    for col, title in enumerate(headers, 1):
        c = ws.cell(row=1, column=col, value=title)
        c.font = header_font; c.fill = header_fill; c.alignment = center

    example_rows = [
        ["20240101", "李四", "2026-10-21", "学业辅导", "月考后学习状态", "办公室",
         "月考成绩下滑", "最近上课走神", "学生表示最近熬夜玩手机导致上课困倦，已约定调整作息",
         "需家长配合监督作息", "黄", "是", "2026-11-05", "否", ""],
        ["20240102", "王五", "2026-10-21", "心理疏导", "考前焦虑", "心理辅导室",
         "情绪波动", "考试前紧张失眠", "学生自述对排名过度在意，已进行情绪疏导，状态平稳",
         "持续观察，两周后复谈", "绿", "是", "2026-11-04", "否", ""],
    ]
    for r, row in enumerate(example_rows, 2):
        for c, val in enumerate(row, 1):
            cell = ws.cell(row=r, column=c, value=val)
            cell.font = Font(name="Arial")

    info = wb.create_sheet("填写说明")
    notes = [
        "1. 学号：必填，学生在系统中的学号；只能导入自己导生的记录，非导生该行会失败",
        "2. 谈话日期：必填，格式 YYYY-MM-DD",
        "3. 谈话类别：必填，须与系统配置的类别一致（默认：思想引导/学业辅导/心理疏导/生活指导/生涯向导）",
        "4. 谈话纪要：必填，其余字段选填",
        "5. 风险等级：绿/黄/红（默认绿）；黄色触发一般预警，红色触发严重预警",
        "6. 继续跟进/是否升级：填 是 或 否（默认否）",
        "7. 下次谈话时间：填了会自动为导师创建待办提醒，格式 YYYY-MM-DD",
        "8. 升级路径：是否升级为「是」时必填，可选 年级/学发/心理/校领导",
        "9. 学生姓名：必填，须与学号一致，不一致该行失败并提示学号对应姓名",
        "10. 导师无需填写：系统自动取名单中该学生的当前导师",
    ]
    for r, note in enumerate(notes, 1):
        c = info.cell(row=r, column=1, value=note)
        c.font = Font(name="Arial")
    info.column_dimensions['A'].width = 100
    for col, w in zip("ABCDEFGHIJKLMNO", [14, 12, 12, 18, 12, 16, 20, 40, 20, 10, 10, 14, 10, 10, 12]):
        ws.column_dimensions[col].width = w
    ws.freeze_panes = 'A2'

    output = io.BytesIO()
    wb.save(output)
    output.seek(0)
    filename = quote("导师谈话记录导入模板.xlsx")
    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{filename}"},
    )
