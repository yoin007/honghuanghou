# -*- coding: utf-8 -*-
"""
监考安排 API 模块

实现考试项目和监考安排的完整管理功能
"""

import sqlite3
import os
import json
import logging
import re
from datetime import datetime, date
from typing import Optional, List, Dict, Any
from decimal import Decimal
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException, Query, Request, UploadFile, File, Body
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
import io

from models.datas_api.auth import User, get_current_user, is_admin_user
from models.datas_api.moral.api_permission import require_configured_api_permission
from utils.db_config import INVIGILATION_DB
from utils.sqlite_moral_db import MoralDatabase as SQLiteMoralDatabase
from sendqueue import send_text

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/invigilation", tags=["监考安排"])


# =============================================================================
# Pydantic 模型
# =============================================================================

class ExamProjectCreate(BaseModel):
    """创建考试项目"""
    name: str = Field(..., description="考试名称")
    school_year: Optional[str] = Field(None, description="学年")
    semester: Optional[str] = Field(None, description="学期")
    start_date: Optional[str] = Field(None, description="开始日期")
    end_date: Optional[str] = Field(None, description="结束日期")
    grade_ids: List[int] = Field(..., description="参与年级ID列表")


class ExamProjectUpdate(BaseModel):
    """更新考试项目"""
    name: Optional[str] = Field(None, description="考试名称")
    school_year: Optional[str] = Field(None, description="学年")
    semester: Optional[str] = Field(None, description="学期")
    start_date: Optional[str] = Field(None, description="开始日期")
    end_date: Optional[str] = Field(None, description="结束日期")
    grade_ids: Optional[List[int]] = Field(None, description="参与年级ID列表")


class InvigilationSlotCreate(BaseModel):
    """创建监考安排"""
    grade_id: int = Field(..., description="年级ID")
    grade_name: Optional[str] = Field(None, description="年级名称")
    exam_date: str = Field(..., description="考试日期")
    start_time: str = Field(..., description="开始时间")
    end_time: str = Field(..., description="结束时间")
    subject: str = Field(..., description="学科")
    room_name: str = Field(..., description="考场名称")
    room_order: Optional[int] = Field(0, description="考场序号")
    teacher_id: Optional[str] = Field(None, description="主监教师ID")
    teacher_name: Optional[str] = Field(None, description="主监教师姓名")
    assistant_teacher_id: Optional[str] = Field(None, description="副监教师ID")
    assistant_teacher_name: Optional[str] = Field(None, description="副监教师姓名")


class InvigilationSlotsBatch(BaseModel):
    """批量保存监考安排"""
    slots: List[InvigilationSlotCreate] = Field(..., description="安排列表")


class NotifyRequest(BaseModel):
    """发送通知请求"""
    notify_added: bool = Field(True, description="通知新增监考的老师")
    notify_changed: bool = Field(True, description="通知有变更的老师")
    notify_removed: bool = Field(True, description="通知被取消的老师")


class NotifyRequestV2(BaseModel):
    """发送通知请求V2 - 支持学科筛选"""
    subjects: Optional[List[str]] = Field(None, description="筛选学科列表，空=全部")
    notify_added: bool = Field(True, description="通知新增监考的老师")
    notify_changed: bool = Field(True, description="通知有变更的老师")
    notify_removed: bool = Field(True, description="通知被取消的老师")
    notify_reminder: bool = Field(False, description="发送提醒给无变化的老师")


# =============================================================================
# 数据库连接
# =============================================================================

from models.datas_api.repositories.sqlite_base import get_sqlite_connection

# ---------------------------------------------------------------------------
# 主副监公共常量 / 辅助
# ---------------------------------------------------------------------------
# 一场考试可以有主监 + 副监两位老师；副监可留空。
# 数据库列：主监 -> teacher_id / teacher_name / teacher_wxid
#           副监 -> assistant_teacher_id / assistant_teacher_name / assistant_teacher_wxid
SLOT_ROLES = ("primary", "assistant")


def _slot_role_columns(role: str) -> tuple:
    """按角色返回 (id_col, name_col, wxid_col)。"""
    if role == "primary":
        return "teacher_id", "teacher_name", "teacher_wxid"
    if role == "assistant":
        return "assistant_teacher_id", "assistant_teacher_name", "assistant_teacher_wxid"
    raise ValueError(f"未知角色：{role}")


def _slot_role_teacher(slot: Optional[dict], role: str) -> dict:
    """从 slot dict / Row 里按角色抽出 {teacher_id, teacher_name, teacher_wxid}。空 slot 返回全 None。"""
    if not slot:
        return {"teacher_id": None, "teacher_name": None, "teacher_wxid": None}
    id_col, name_col, wxid_col = _slot_role_columns(role)
    return {
        "teacher_id": slot.get(id_col) if isinstance(slot, dict) else slot[id_col],
        "teacher_name": slot.get(name_col) if isinstance(slot, dict) else slot[name_col],
        "teacher_wxid": slot.get(wxid_col) if isinstance(slot, dict) else slot[wxid_col],
    }


def get_invigilation_db():
    """获取监考安排数据库连接"""
    conn = get_sqlite_connection(INVIGILATION_DB, row_factory=sqlite3.Row)
    return conn


# ---------------------------------------------------------------------------
# 导入用：日期/时间归一化
# ---------------------------------------------------------------------------
# Excel 单元格进来 pandas 时类型很杂：datetime.datetime、datetime.date、
# pandas.Timestamp、datetime.time、"2026-07-07"、"2026-07-07 00:00:00"、
# "2026/7/7"、"08:00"、"08:00:00"、"8:0" 等。若直接 str(...)，同一场次会因
# 表面字符串不同而"绕过"冲突检测；库里也会同时存 '08:00' 与 '08:00:00' 两种。
# 这里统一归一化：日期 -> 'YYYY-MM-DD'，时间 -> 'HH:MM:SS'。


def _normalize_date_cell(value) -> Optional[str]:
    """把日期单元格归一到 'YYYY-MM-DD'。识别不了返回 None。"""
    if value is None:
        return None
    # pandas Timestamp / datetime / date
    if hasattr(value, "date") and callable(value.date):
        try:
            return value.date().isoformat()
        except Exception:
            pass
    if isinstance(value, date):
        return value.isoformat()

    s = str(value).strip()
    if not s or s.lower() in ("nan", "nat", "none"):
        return None
    # 常见字符串格式挨个试：ISO、含时分秒、斜杠分隔、无零填充
    for fmt in (
        "%Y-%m-%d", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M",
        "%Y/%m/%d", "%Y/%m/%d %H:%M:%S", "%Y/%m/%d %H:%M",
        "%Y.%m.%d",
    ):
        try:
            return datetime.strptime(s, fmt).date().isoformat()
        except ValueError:
            continue
    return None


def _normalize_time_cell(value) -> Optional[str]:
    """把时间单元格归一到 'HH:MM:SS'。识别不了返回 None。"""
    if value is None:
        return None
    # datetime.time
    if hasattr(value, "hour") and hasattr(value, "minute") and not hasattr(value, "year"):
        return f"{value.hour:02d}:{value.minute:02d}:{getattr(value, 'second', 0):02d}"
    # datetime.datetime / pandas.Timestamp -> 取时间部分
    if hasattr(value, "time") and callable(value.time):
        try:
            t = value.time()
            return f"{t.hour:02d}:{t.minute:02d}:{t.second:02d}"
        except Exception:
            pass

    s = str(value).strip()
    if not s or s.lower() in ("nan", "nat", "none"):
        return None
    # 兼容 '8:00'/'08:00'/'08:00:00'/'8:0:0'
    m = re.match(r"^(\d{1,2}):(\d{1,2})(?::(\d{1,2}))?$", s)
    if m:
        hh, mm, ss = int(m.group(1)), int(m.group(2)), int(m.group(3) or 0)
        if 0 <= hh < 24 and 0 <= mm < 60 and 0 <= ss < 60:
            return f"{hh:02d}:{mm:02d}:{ss:02d}"
    # 兜底试 datetime 解析
    for fmt in ("%H:%M:%S", "%H:%M", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M"):
        try:
            t = datetime.strptime(s, fmt).time()
            return f"{t.hour:02d}:{t.minute:02d}:{t.second:02d}"
        except ValueError:
            continue
    return None


# ---------------------------------------------------------------------------
# 变更 diff 公共实现（changes preview 与 notify 共用）
# ---------------------------------------------------------------------------
def _norm_date_key(v) -> str:
    """把日期字符串归一到 'YYYY-MM-DD'，供 diff key 使用。
    容忍历史遗留的 '2026-07-07 00:00:00' 与新写入的 '2026-07-07' 混用，
    避免同一场次因表面文本不同被判成'取消 + 新增'。"""
    if not v:
        return ''
    return str(v).split(' ')[0]


def _norm_time_key(v) -> str:
    """把时间字符串归一到 'HH:MM:SS'，供 diff key 使用。"""
    if not v:
        return ''
    s = str(v)
    return s if len(s) == 8 else (s + ':00' if len(s) == 5 else s)


def _slot_change_key(slot: dict) -> str:
    """场次唯一键（不含角色）。所有字段做归一化，防止历史遗留脏格式造成误判。"""
    return (
        f"{slot['grade_id']}|"
        f"{_norm_date_key(slot.get('exam_date'))}|"
        f"{_norm_time_key(slot.get('start_time'))}|"
        f"{slot.get('room_name')}"
    )


def _compute_slot_changes(
    current_slots: List[dict],
    previous_slots: List[dict],
    subject_filter: Optional[List[str]] = None,
):
    """
    对比两次快照，按 (slot_key, role) 二元组产出 added/removed/swaps/unchanged。

    主监与副监被视作独立的"位置"：同一场考试的主监换人或副监换人各自触发一条变更；
    swap 检测跨 slot、跨 role 都能配对（例：A 场主监 ↔ B 场副监）。
    """
    current_map = {_slot_change_key(s): s for s in current_slots}
    previous_map = {_slot_change_key(s): s for s in previous_slots}

    added: List[dict] = []
    removed: List[dict] = []
    changed: List[dict] = []
    unchanged: List[dict] = []

    all_keys = set(current_map.keys()) | set(previous_map.keys())

    for key in all_keys:
        current_slot = current_map.get(key)
        previous_slot = previous_map.get(key)

        # 学科筛选
        if subject_filter:
            slot_subject = (current_slot or previous_slot).get('subject', '')
            if slot_subject not in subject_filter:
                continue

        for role in SLOT_ROLES:
            prev_t = _slot_role_teacher(previous_slot, role)
            curr_t = _slot_role_teacher(current_slot, role)
            prev_id, curr_id = prev_t["teacher_id"], curr_t["teacher_id"]

            # 场次整体新增：以当前 slot 全量存在为准
            if not previous_slot and current_slot:
                if curr_id:
                    added.append({
                        'teacher_id': curr_id,
                        'teacher_name': curr_t["teacher_name"],
                        'teacher_wxid': curr_t["teacher_wxid"],
                        'role': role,
                        'slot': current_slot,
                    })
                continue

            # 场次整体取消
            if previous_slot and not current_slot:
                if prev_id:
                    removed.append({
                        'teacher_id': prev_id,
                        'teacher_name': prev_t["teacher_name"],
                        'teacher_wxid': prev_t["teacher_wxid"],
                        'role': role,
                        'slot': previous_slot,
                        'reason': '场次取消',
                    })
                continue

            # 场次仍在，比对角色内的教师变化
            if prev_id != curr_id:
                if prev_id and curr_id:
                    removed.append({
                        'teacher_id': prev_id,
                        'teacher_name': prev_t["teacher_name"],
                        'teacher_wxid': prev_t["teacher_wxid"],
                        'role': role,
                        'slot': previous_slot,
                        'reason': '教师替换',
                    })
                    added.append({
                        'teacher_id': curr_id,
                        'teacher_name': curr_t["teacher_name"],
                        'teacher_wxid': curr_t["teacher_wxid"],
                        'role': role,
                        'slot': current_slot,
                    })
                    changed.append({
                        'type': 'replace',
                        'old_teacher_id': prev_id,
                        'old_teacher_name': prev_t["teacher_name"],
                        'old_teacher_wxid': prev_t["teacher_wxid"],
                        'old_role': role,
                        'new_teacher_id': curr_id,
                        'new_teacher_name': curr_t["teacher_name"],
                        'new_teacher_wxid': curr_t["teacher_wxid"],
                        'new_role': role,
                        'slot': current_slot,
                        'old_slot': previous_slot,
                    })
                elif prev_id and not curr_id:
                    removed.append({
                        'teacher_id': prev_id,
                        'teacher_name': prev_t["teacher_name"],
                        'teacher_wxid': prev_t["teacher_wxid"],
                        'role': role,
                        'slot': previous_slot,
                        'reason': '教师取消',
                    })
                elif not prev_id and curr_id:
                    added.append({
                        'teacher_id': curr_id,
                        'teacher_name': curr_t["teacher_name"],
                        'teacher_wxid': curr_t["teacher_wxid"],
                        'role': role,
                        'slot': current_slot,
                    })
            else:
                if curr_id:
                    unchanged.append({
                        'teacher_id': curr_id,
                        'teacher_name': curr_t["teacher_name"],
                        'teacher_wxid': curr_t["teacher_wxid"],
                        'role': role,
                        'slot': current_slot,
                    })

    # swap 检测：(old_id, new_id) 与 (new_id, old_id) 同时存在即为一次互换
    swaps: List[dict] = []
    replace_map: Dict[tuple, dict] = {}
    for ch in changed:
        replace_map[(ch['old_teacher_id'], ch['new_teacher_id'])] = ch

    processed_keys: set = set()
    swap_teacher_ids: set = set()
    for (old_id, new_id), ch in replace_map.items():
        if (new_id, old_id) in replace_map and (new_id, old_id) not in processed_keys:
            ch2 = replace_map[(new_id, old_id)]
            swaps.append({
                'type': 'swap',
                'teacher_a_id': old_id,
                'teacher_a_name': ch['old_teacher_name'],
                'teacher_a_wxid': ch['old_teacher_wxid'],
                'teacher_b_id': new_id,
                'teacher_b_name': ch['new_teacher_name'],
                'teacher_b_wxid': ch['new_teacher_wxid'],
                'slot_a': ch['slot'],   # A 现在的位置（也是 B 原来的位置）
                'slot_b': ch2['slot'],  # B 现在的位置（也是 A 原来的位置）
            })
            swap_teacher_ids.add(old_id)
            swap_teacher_ids.add(new_id)
            processed_keys.add((old_id, new_id))
            processed_keys.add((new_id, old_id))

    removed = [r for r in removed if r['teacher_id'] not in swap_teacher_ids]
    added = [a for a in added if a['teacher_id'] not in swap_teacher_ids]

    return added, removed, swaps, unchanged


def require_jiaowu(user: User = Depends(get_current_user)) -> User:
    """检查教务权限（保留旧判断，统一鉴权后可逐步移除）"""
    if not is_admin_user(user) and 'jiaowu' not in (user.role or '').split('/'):
        raise HTTPException(403, "需要教务或管理员权限")
    return user


def require_invigilation_permission(api_path: str, http_method: str = "*"):
    """监考模块统一鉴权依赖"""
    return require_configured_api_permission(api_path, http_method, allow_missing=False)


# =============================================================================
# 教师列表 API（从 moral.db 获取）
# =============================================================================

@router.get("/teachers", summary="获取教师列表")
async def get_teachers_for_invigilation(user: User = Depends(require_invigilation_permission("/api/invigilation/teachers", "GET"))):
    """获取教师列表用于监考安排"""
    with SQLiteMoralDatabase() as moral_db:
        teachers_data = moral_db.query_all(
            """SELECT teacher_id, name
            FROM teacher
            WHERE is_active = 1 AND COALESCE(identity_type, 'teacher') = 'teacher'
            ORDER BY name"""
        )
    return {"success": True, "data": teachers_data}


# =============================================================================
# 考试项目 API
# =============================================================================

@router.get("/projects", summary="获取考试项目列表")
async def get_exam_projects(
    status: Optional[str] = Query(None),
    user: User = Depends(require_invigilation_permission("/api/invigilation/projects", "GET"))
):
    """获取考试项目列表"""
    with get_invigilation_db() as db:
        cursor = db.cursor()

        if status:
            cursor.execute(
                "SELECT * FROM exam_project WHERE status = ? ORDER BY created_at DESC",
                (status,)
            )
        else:
            cursor.execute("SELECT * FROM exam_project ORDER BY created_at DESC")

        projects = []
        for row in cursor.fetchall():
            project = dict(row)
            if project.get('grade_ids'):
                try:
                    project['grade_ids'] = json.loads(project['grade_ids'])
                except:
                    project['grade_ids'] = []
            projects.append(project)

        return {"success": True, "data": projects}


@router.post("/projects", summary="创建考试项目")
async def create_exam_project(
    project: ExamProjectCreate,
    user: User = Depends(require_invigilation_permission("/api/invigilation/projects", "POST"))
):
    """创建考试项目"""
    with get_invigilation_db() as db:
        cursor = db.cursor()

        grade_ids_json = json.dumps(project.grade_ids)

        cursor.execute("""
            INSERT INTO exam_project
            (name, school_year, semester, start_date, end_date, grade_ids, status, created_by)
            VALUES (?, ?, ?, ?, ?, ?, 'draft', ?)
        """, (
            project.name, project.school_year, project.semester,
            project.start_date, project.end_date, grade_ids_json,
            user.username
        ))

        project_id = cursor.lastrowid
        db.commit()

        return {
            "success": True,
            "message": "创建成功",
            "data": {"id": project_id}
        }


@router.get("/projects/{project_id}", summary="获取考试项目详情")
async def get_exam_project(
    project_id: int,
    user: User = Depends(require_invigilation_permission("/api/invigilation/projects/{project_id}", "GET"))
):
    """获取考试项目详情"""
    with get_invigilation_db() as db:
        cursor = db.cursor()

        cursor.execute("SELECT * FROM exam_project WHERE id = ?", (project_id,))
        row = cursor.fetchone()

        if not row:
            raise HTTPException(404, "考试项目不存在")

        project = dict(row)
        if project.get('grade_ids'):
            try:
                project['grade_ids'] = json.loads(project['grade_ids'])
            except:
                project['grade_ids'] = []

        # 获取各年级的安排数量
        cursor.execute("""
            SELECT grade_id, grade_name, COUNT(*) as count
            FROM invigilation_slot
            WHERE project_id = ?
            GROUP BY grade_id
        """, (project_id,))

        grade_stats = []
        for stat_row in cursor.fetchall():
            grade_stats.append(dict(stat_row))

        project['grade_stats'] = grade_stats

        return {"success": True, "data": project}


@router.put("/projects/{project_id}", summary="更新考试项目")
async def update_exam_project(
    project_id: int,
    project: ExamProjectUpdate,
    user: User = Depends(require_invigilation_permission("/api/invigilation/projects/{project_id}", "PUT"))
):
    """更新考试项目基础信息"""
    with get_invigilation_db() as db:
        cursor = db.cursor()

        cursor.execute("SELECT id FROM exam_project WHERE id = ?", (project_id,))
        if not cursor.fetchone():
            raise HTTPException(404, "考试项目不存在")

        updates = []
        params = []

        if project.name is not None:
            updates.append("name = ?")
            params.append(project.name)

        if project.school_year is not None:
            updates.append("school_year = ?")
            params.append(project.school_year)

        if project.semester is not None:
            updates.append("semester = ?")
            params.append(project.semester)

        if project.start_date is not None:
            updates.append("start_date = ?")
            params.append(project.start_date)

        if project.end_date is not None:
            updates.append("end_date = ?")
            params.append(project.end_date)

        if project.grade_ids is not None:
            updates.append("grade_ids = ?")
            params.append(json.dumps(project.grade_ids))

        if updates:
            updates.append("updated_at = datetime('now', 'localtime')")
            params.append(project_id)

            cursor.execute(
                f"UPDATE exam_project SET {', '.join(updates)} WHERE id = ?",
                params
            )
            db.commit()

        return {"success": True, "message": "更新成功"}


@router.delete("/projects/{project_id}", summary="删除考试项目")
async def delete_exam_project(
    project_id: int,
    user: User = Depends(require_invigilation_permission("/api/invigilation/projects/{project_id}", "DELETE"))
):
    """删除考试项目及相关数据（真删除）"""
    with get_invigilation_db() as db:
        cursor = db.cursor()

        cursor.execute("SELECT id, name FROM exam_project WHERE id = ?", (project_id,))
        project = cursor.fetchone()
        if not project:
            raise HTTPException(404, "考试项目不存在")

        # 删除通知日志
        cursor.execute("DELETE FROM invigilation_notification_log WHERE project_id = ?", (project_id,))

        # 删除监考安排
        cursor.execute("DELETE FROM invigilation_slot WHERE project_id = ?", (project_id,))

        # 删除项目
        cursor.execute("DELETE FROM exam_project WHERE id = ?", (project_id,))

        db.commit()

        return {"success": True, "message": f"项目「{project['name']}」已删除"}


# =============================================================================
# 监考安排 API
# =============================================================================

@router.get("/projects/{project_id}/slots", summary="获取监考安排列表")
async def get_invigilation_slots(
    project_id: int,
    grade_id: Optional[int] = Query(None),
    exam_date: Optional[str] = Query(None),
    teacher_name: Optional[str] = Query(None),
    user: User = Depends(require_invigilation_permission("/api/invigilation/projects/{project_id}/slots", "GET"))
):
    """获取项目的监考安排列表"""
    with get_invigilation_db() as db:
        cursor = db.cursor()

        conditions = ["project_id = ?"]
        params = [project_id]

        if grade_id:
            conditions.append("grade_id = ?")
            params.append(grade_id)

        if exam_date:
            conditions.append("exam_date = ?")
            params.append(exam_date)

        if teacher_name:
            conditions.append("teacher_name LIKE ?")
            params.append(f"%{teacher_name}%")

        where_clause = " AND ".join(conditions)

        cursor.execute(f"""
            SELECT * FROM invigilation_slot
            WHERE {where_clause}
            ORDER BY exam_date, start_time, room_order
        """, params)

        slots = [dict(row) for row in cursor.fetchall()]

        return {"success": True, "data": slots}


@router.put("/projects/{project_id}/slots", summary="批量保存监考安排")
async def save_invigilation_slots(
    project_id: int,
    batch: InvigilationSlotsBatch,
    user: User = Depends(require_invigilation_permission("/api/invigilation/projects/{project_id}/slots", "PUT"))
):
    """批量保存监考安排（覆盖模式）"""
    with get_invigilation_db() as db:
        cursor = db.cursor()

        # 验证项目存在
        cursor.execute("SELECT id, grade_ids FROM exam_project WHERE id = ?", (project_id,))
        project = cursor.fetchone()
        if not project:
            raise HTTPException(404, "考试项目不存在")

        try:
            allowed_grades = json.loads(project['grade_ids'])
        except:
            allowed_grades = []

        # 检查年级是否属于项目
        for slot in batch.slots:
            if slot.grade_id not in allowed_grades:
                raise HTTPException(400, f"年级 {slot.grade_id} 不属于该考试项目")

        # 冲突校验：
        # 1. 同一教师在同一 (date, start_time) 只能出现一次（主监副监都算）
        # 2. 同一场考试主监 ≠ 副监
        teacher_time_map = {}
        for slot in batch.slots:
            if slot.teacher_id and slot.assistant_teacher_id \
                    and slot.teacher_id == slot.assistant_teacher_id:
                raise HTTPException(
                    400,
                    f"{slot.exam_date} {slot.start_time} {slot.room_name} "
                    f"的主监与副监不能是同一位老师（{slot.teacher_name}）"
                )

            for role in SLOT_ROLES:
                if role == "primary":
                    tid, tname = slot.teacher_id, slot.teacher_name
                else:
                    tid, tname = slot.assistant_teacher_id, slot.assistant_teacher_name
                if not tid:
                    continue
                key = f"{tid}|{slot.exam_date}|{slot.start_time}"
                if key in teacher_time_map:
                    raise HTTPException(
                        400,
                        f"教师 {tname} 在 {slot.exam_date} {slot.start_time} 被安排了多个考场"
                    )
                teacher_time_map[key] = slot.room_name

        # 只删除本次 PUT 推送涉及的年级，避免"前端只加载了一个年级、保存时把其他年级洗掉"。
        # 前端 convertToVertical() 会遍历 [1,2,3] 所有年级，但空年级不产生 slot，会漏在删除范围外。
        # 这里以本次 batch 里出现的 grade_id 集合为准。
        submitted_grade_ids = sorted({slot.grade_id for slot in batch.slots})
        if submitted_grade_ids:
            placeholders = ",".join("?" * len(submitted_grade_ids))
            cursor.execute(
                f"DELETE FROM invigilation_slot WHERE project_id = ? AND grade_id IN ({placeholders})",
                (project_id, *submitted_grade_ids),
            )
        # 若 batch 为空（用户什么都没勾选），什么都不删——保护现有数据

        # 获取教师wxid映射（从moral.db）
        with SQLiteMoralDatabase() as moral_db:
            teacher_wxid_map = moral_db.query_all(
                """SELECT teacher_id, wxid
                FROM teacher
                WHERE is_active = 1 AND COALESCE(identity_type, 'teacher') = 'teacher'"""
            )
        wxid_dict = {row['teacher_id']: row['wxid'] for row in teacher_wxid_map}

        # 插入新安排
        for slot in batch.slots:
            teacher_wxid = wxid_dict.get(slot.teacher_id)
            assistant_wxid = wxid_dict.get(slot.assistant_teacher_id) if slot.assistant_teacher_id else None
            cursor.execute("""
                INSERT INTO invigilation_slot
                (project_id, grade_id, grade_name, exam_date, start_time, end_time, subject, room_name, room_order,
                 teacher_id, teacher_name, teacher_wxid,
                 assistant_teacher_id, assistant_teacher_name, assistant_teacher_wxid,
                 source)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'manual')
            """, (
                project_id, slot.grade_id, slot.grade_name, slot.exam_date,
                slot.start_time, slot.end_time, slot.subject, slot.room_name,
                slot.room_order or 0,
                slot.teacher_id, slot.teacher_name, teacher_wxid,
                slot.assistant_teacher_id, slot.assistant_teacher_name, assistant_wxid,
            ))

        # 更新项目状态
        cursor.execute("""
            UPDATE exam_project
            SET status = 'saved',
                first_saved_at = COALESCE(first_saved_at, datetime('now', 'localtime')),
                updated_at = datetime('now', 'localtime')
            WHERE id = ?
        """, (project_id,))

        db.commit()

        return {"success": True, "message": "保存成功", "data": {"count": len(batch.slots)}}


@router.post("/projects/{project_id}/slots/swap-teachers", summary="交换监考老师")
async def swap_teachers(
    project_id: int,
    slot_id_1: int = Query(...),
    slot_id_2: int = Query(...),
    role_1: str = Query("primary", description="slot_id_1 交换的角色：primary/assistant"),
    role_2: str = Query("primary", description="slot_id_2 交换的角色：primary/assistant"),
    user: User = Depends(require_invigilation_permission("/api/invigilation/projects/{project_id}/slots/swap-teachers", "POST"))
):
    """
    交换两条安排的监考老师（支持主监 / 副监两个角色任意组合互换）。

    role_1、role_2 均默认 primary，与旧接口兼容。
    """
    if role_1 not in SLOT_ROLES or role_2 not in SLOT_ROLES:
        raise HTTPException(400, "role 参数必须是 primary 或 assistant")

    with get_invigilation_db() as db:
        cursor = db.cursor()

        # 获取两条安排
        cursor.execute("SELECT * FROM invigilation_slot WHERE id = ? AND project_id = ?", (slot_id_1, project_id))
        slot1 = cursor.fetchone()
        if not slot1:
            raise HTTPException(404, "安排1不存在")

        cursor.execute("SELECT * FROM invigilation_slot WHERE id = ? AND project_id = ?", (slot_id_2, project_id))
        slot2 = cursor.fetchone()
        if not slot2:
            raise HTTPException(404, "安排2不存在")

        # 按角色拿出当前教师信息
        t1 = _slot_role_teacher(slot1, role_1)
        t2 = _slot_role_teacher(slot2, role_2)

        # 交换后自冲校验：如果目标 slot 内的另一角色已经是要换过去的教师，则拒绝
        def _other_role(role: str) -> str:
            return "assistant" if role == "primary" else "primary"

        for target_slot, target_role, incoming in (
            (slot1, role_1, t2),
            (slot2, role_2, t1),
        ):
            if not incoming["teacher_id"]:
                continue
            other = _slot_role_teacher(target_slot, _other_role(target_role))
            if other["teacher_id"] and other["teacher_id"] == incoming["teacher_id"]:
                raise HTTPException(
                    400,
                    f"交换后 {target_slot['exam_date']} {target_slot['start_time']} "
                    f"{target_slot['room_name']} 会出现主监与副监相同（{incoming['teacher_name']}）"
                )

        # 分别更新两条 slot 对应角色的教师列
        id_col_1, name_col_1, wxid_col_1 = _slot_role_columns(role_1)
        id_col_2, name_col_2, wxid_col_2 = _slot_role_columns(role_2)

        cursor.execute(
            f"""UPDATE invigilation_slot
                SET {id_col_1} = ?, {name_col_1} = ?, {wxid_col_1} = ?,
                    updated_at = datetime('now', 'localtime')
                WHERE id = ?""",
            (t2["teacher_id"], t2["teacher_name"], t2["teacher_wxid"], slot_id_1)
        )
        cursor.execute(
            f"""UPDATE invigilation_slot
                SET {id_col_2} = ?, {name_col_2} = ?, {wxid_col_2} = ?,
                    updated_at = datetime('now', 'localtime')
                WHERE id = ?""",
            (t1["teacher_id"], t1["teacher_name"], t1["teacher_wxid"], slot_id_2)
        )

        db.commit()

        return {"success": True, "message": "交换成功"}


# =============================================================================
# 通知 API
# =============================================================================

@router.get("/projects/{project_id}/changes", summary="获取变更预览")
async def get_changes_preview(
    project_id: int,
    subjects: Optional[str] = Query(None, description="筛选学科，逗号分隔"),
    user: User = Depends(require_invigilation_permission("/api/invigilation/projects/{project_id}/changes", "GET"))
):
    """获取监考安排变更预览（对比上次通知版本）"""
    with get_invigilation_db() as db:
        cursor = db.cursor()

        # 获取项目信息
        cursor.execute("SELECT * FROM exam_project WHERE id = ?", (project_id,))
        project = cursor.fetchone()
        if not project:
            raise HTTPException(404, "考试项目不存在")

        current_version = project['version_no']

        # 获取当前安排
        subject_filter = subjects.split(',') if subjects else None
        cursor.execute("""
            SELECT * FROM invigilation_slot
            WHERE project_id = ?
            ORDER BY grade_id, exam_date, start_time, room_order
        """, (project_id,))
        current_slots = [dict(row) for row in cursor.fetchall()]

        # 从快照表获取上次通知时的全量安排
        cursor.execute("""
            SELECT slots_json FROM invigilation_snapshot
            WHERE project_id = ? AND version_no = ?
            ORDER BY version_no DESC LIMIT 1
        """, (project_id, current_version))
        snapshot_row = cursor.fetchone()

        previous_slots = []
        if snapshot_row and snapshot_row['slots_json']:
            previous_slots = json.loads(snapshot_row['slots_json'])

        added, removed, swaps, unchanged = _compute_slot_changes(
            current_slots, previous_slots, subject_filter
        )

        stats = {
            'added_count': len(added),
            'removed_count': len(removed),
            'swapped_count': len(swaps),
            'unchanged_count': len(unchanged),
            'has_wxid_added': sum(1 for a in added if a['teacher_wxid']),
            'has_wxid_removed': sum(1 for r in removed if r['teacher_wxid']),
            'has_wxid_swapped': sum(1 for s in swaps if s['teacher_a_wxid'] or s['teacher_b_wxid']),
        }

        return {
            "success": True,
            "data": {
                "added": added,
                "removed": removed,
                "swapped": swaps,
                "unchanged": unchanged,
                "stats": stats
            }
        }

@router.post("/projects/{project_id}/notify", summary="发送监考通知")
async def send_notifications(
    project_id: int,
    user: User = Depends(require_invigilation_permission("/api/invigilation/projects/{project_id}/notify", "POST")),
    request: NotifyRequestV2 = Body(default=NotifyRequestV2())
):
    """发送监考通知给老师（支持学科筛选和变更检测）"""
    with get_invigilation_db() as db:
        cursor = db.cursor()

        # 获取项目信息
        cursor.execute("SELECT * FROM exam_project WHERE id = ?", (project_id,))
        project = cursor.fetchone()
        if not project:
            raise HTTPException(404, "考试项目不存在")

        project_name = project['name']
        current_version = project['version_no']
        new_version = current_version + 1

        # 获取变更数据
        subject_filter = request.subjects

        # 获取当前安排
        cursor.execute("""
            SELECT * FROM invigilation_slot
            WHERE project_id = ?
            ORDER BY grade_id, exam_date, start_time, room_order
        """, (project_id,))
        current_slots = [dict(row) for row in cursor.fetchall()]

        # 从快照表获取上次通知时的全量安排
        cursor.execute("""
            SELECT slots_json FROM invigilation_snapshot
            WHERE project_id = ? AND version_no = ?
            ORDER BY version_no DESC LIMIT 1
        """, (project_id, current_version))
        snapshot_row = cursor.fetchone()

        previous_slots = []
        if snapshot_row and snapshot_row['slots_json']:
            previous_slots = json.loads(snapshot_row['slots_json'])

        added, removed, swaps, unchanged = _compute_slot_changes(
            current_slots, previous_slots, subject_filter
        )

        # 发送通知
        success_count = 0
        failed_count = 0
        skipped_count = 0
        logs = []

        def format_slot(slot):
            return f"{slot['exam_date']} {slot['start_time']}-{slot['end_time']} {slot['subject']} {slot['grade_name']} {slot['room_name']}"

        def send_and_log(content, teacher_id, teacher_name, teacher_wxid, change_type, slots_json):
            nonlocal success_count, failed_count, skipped_count, logs
            log_entry = {
                'project_id': project_id,
                'version_no': new_version,
                'teacher_name': teacher_name,
                'teacher_id': teacher_id,
                'receiver': teacher_wxid,
                'message': content,
                'change_type': change_type,
                'slots_json': json.dumps(slots_json)
            }

            if teacher_wxid:
                try:
                    send_text(content, teacher_wxid, producer='invigilation')
                    log_entry['sent_status'] = 'success'
                    log_entry['error_message'] = None
                    log_entry['sent_at'] = datetime.now().isoformat()
                    success_count += 1
                except Exception as e:
                    log_entry['sent_status'] = 'failed'
                    log_entry['error_message'] = str(e)
                    log_entry['sent_at'] = datetime.now().isoformat()
                    failed_count += 1
                    logger.error(f"通知发送失败: {teacher_name} - {e}")
            else:
                log_entry['sent_status'] = 'skipped'
                log_entry['error_message'] = '未配置wxid'
                log_entry['sent_at'] = None
                skipped_count += 1

            logs.append(log_entry)

        # 1. 发送新增通知
        if request.notify_added:
            for item in added:
                content = f"""【新增监考】
考试：{project_name}
{item['teacher_name']}老师，新增您的监考安排：
{format_slot(item['slot'])}
请准时到岗。"""
                send_and_log(content, item['teacher_id'], item['teacher_name'],
                           item['teacher_wxid'], 'added', [item['slot']])

        # 2. 发送取消通知
        if request.notify_removed:
            for item in removed:
                content = f"""【取消监考】
考试：{project_name}
{item['teacher_name']}老师，您原定的监考安排已取消：
{format_slot(item['slot'])}
原因：{item['reason']}
感谢您的配合。"""
                send_and_log(content, item['teacher_id'], item['teacher_name'],
                           item['teacher_wxid'], 'removed', [item['slot']])

        # 3. 替换已通过removed+added通知，这里跳过
        # remaining_changed只用于交换检测的中间数据，不直接发通知

        # 4. 发送交换通知（通知双方，不显示对方名字）
        if request.notify_changed:
            for sw in swaps:
                # 通知教师A
                content_a = f"""【监考调整】
考试：{project_name}
{sw['teacher_a_name']}老师，您的监考安排已调整：
原安排：{format_slot(sw['slot_a'])}
新安排：{format_slot(sw['slot_b'])}
请准时到岗。"""
                send_and_log(content_a, sw['teacher_a_id'], sw['teacher_a_name'],
                           sw['teacher_a_wxid'], 'swap', [sw['slot_a'], sw['slot_b']])

                # 通知教师B
                content_b = f"""【监考调整】
考试：{project_name}
{sw['teacher_b_name']}老师，您的监考安排已调整：
原安排：{format_slot(sw['slot_b'])}
新安排：{format_slot(sw['slot_a'])}
请准时到岗。"""
                send_and_log(content_b, sw['teacher_b_id'], sw['teacher_b_name'],
                           sw['teacher_b_wxid'], 'swap', [sw['slot_a'], sw['slot_b']])

        # 5. 发送提醒（无变化的教师）
        if request.notify_reminder:
            # 按教师聚合 unchanged；同一 slot 可能因主/副双份出现，需以 slot.id 去重
            teacher_unchanged = {}
            for item in unchanged:
                tid = item['teacher_id']
                if tid not in teacher_unchanged:
                    teacher_unchanged[tid] = {
                        'teacher_name': item['teacher_name'],
                        'teacher_wxid': item['teacher_wxid'],
                        'slots': [],
                        '_slot_ids': set(),
                    }
                slot = item['slot']
                slot_uid = slot.get('id') or _slot_change_key(slot)
                if slot_uid in teacher_unchanged[tid]['_slot_ids']:
                    continue
                teacher_unchanged[tid]['_slot_ids'].add(slot_uid)
                teacher_unchanged[tid]['slots'].append(slot)

            for tid, data in teacher_unchanged.items():
                slots_str = '\n'.join([f"{i+1}. {format_slot(s)}" for i, s in enumerate(data['slots'])])
                content = f"""【监考提醒】
考试：{project_name}
{data['teacher_name']}老师，您的监考安排：
{slots_str}
请准时到岗。"""
                send_and_log(content, tid, data['teacher_name'],
                           data['teacher_wxid'], 'reminder', data['slots'])

        # 写入通知日志
        for log in logs:
            cursor.execute("""
                INSERT INTO invigilation_notification_log
                (project_id, version_no, teacher_name, teacher_id, receiver, message, change_type, slots_json, sent_status, error_message, sent_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                log['project_id'], log['version_no'], log['teacher_name'],
                log['teacher_id'], log['receiver'], log['message'],
                log['change_type'], log['slots_json'], log['sent_status'],
                log['error_message'], log['sent_at']
            ))

        # 存快照到snapshot表（新版本）
        cursor.execute("""
            INSERT INTO invigilation_snapshot (project_id, version_no, slots_json, created_at)
            VALUES (?, ?, ?, datetime('now', 'localtime'))
        """, (project_id, new_version, json.dumps(current_slots)))

        # 更新项目版本和通知时间
        cursor.execute("""
            UPDATE exam_project
            SET version_no = ?, status = 'notified', notified_at = datetime('now', 'localtime'), updated_at = datetime('now', 'localtime')
            WHERE id = ?
        """, (new_version, project_id))

        db.commit()

        return {
            "success": True,
            "message": "通知发送完成",
            "data": {
                "success": success_count,
                "failed": failed_count,
                "skipped": skipped_count,
                "added": len(added),
                "removed": len(removed),
                "swapped": len(swaps),
                "reminded": len(unchanged) if request.notify_reminder else 0
            }
        }


@router.get("/projects/{project_id}/notification-logs", summary="获取通知日志")
async def get_notification_logs(
    project_id: int,
    user: User = Depends(require_invigilation_permission("/api/invigilation/projects/{project_id}/notification-logs", "GET"))
):
    """获取项目的通知日志"""
    with get_invigilation_db() as db:
        cursor = db.cursor()

        cursor.execute("""
            SELECT * FROM invigilation_notification_log
            WHERE project_id = ?
            ORDER BY sent_at DESC
        """, (project_id,))

        logs = [dict(row) for row in cursor.fetchall()]

        return {"success": True, "data": logs}


# =============================================================================
# Excel API
# =============================================================================

@router.get("/template", summary="下载导入模板")
async def download_template(user: User = Depends(require_invigilation_permission("/api/invigilation/template", "GET"))):
    """
    下载监考安排导入模板（横向布局）

    每个考场拆成两列：`考场N主监` `考场N副监`。副监列允许留空。
    """
    import pandas as pd

    template_data = {
        '年级': ['高一', '高一', '高一', '高二', '高二', '高三'],
        '日期': ['2026-05-10', '2026-05-10', '2026-05-11', '2026-05-10', '2026-05-10', '2026-05-11'],
        '开始时间': ['08:00', '10:20', '14:00', '08:00', '10:20', '08:00'],
        '结束时间': ['10:00', '12:00', '16:00', '10:00', '12:00', '10:00'],
        '学科': ['语文', '数学', '英语', '语文', '数学', '物理'],
        '考场1主监': ['任庆叶', '侯莹', '刘亚利', '刘斌', '张炜', '戴建海'],
        '考场1副监': ['任秀辉', '冯秀珍', '', '刘晓玲', '张鹏飞', ''],
        '考场2主监': ['宋文燕', '张鹏飞', '刘斌', '任秀辉', '侯莹', '任庆叶'],
        '考场2副监': ['', '', '', '', '', ''],
        '考场3主监': ['', '', '', '', '', ''],
        '考场3副监': ['', '', '', '', '', ''],
    }

    df = pd.DataFrame(template_data)

    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='监考安排')

    output.seek(0)

    return StreamingResponse(
        output,
        media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        headers={'Content-Disposition': 'attachment; filename=invigilation_template.xlsx'}
    )


@router.post("/projects/{project_id}/import", summary="导入监考安排")
async def import_invigilation(
    project_id: int,
    file: UploadFile = File(...),
    user: User = Depends(require_invigilation_permission("/api/invigilation/projects/{project_id}/import", "POST"))
):
    """导入监考安排 Excel"""
    import pandas as pd

    with get_invigilation_db() as db:
        cursor = db.cursor()

        # 验证项目存在
        cursor.execute("SELECT id, grade_ids FROM exam_project WHERE id = ?", (project_id,))
        project = cursor.fetchone()
        if not project:
            raise HTTPException(404, "考试项目不存在")

        try:
            allowed_grades = json.loads(project['grade_ids'])
        except:
            allowed_grades = []

        # 读取Excel
        content = await file.read()
        df = pd.read_excel(io.BytesIO(content))

        # 检测布局格式：横向布局有考场列（支持"考场1"和"第1考场监考"两种格式）
        is_horizontal = any(
            '考场监考' in col or
            ('第' in col and '监考' in col) or
            re.match(r'考场\d+', col)
            for col in df.columns
        )

        # 获取教师列表用于匹配（从moral.db）
        with SQLiteMoralDatabase() as moral_db:
            teachers_data = moral_db.query_all(
                """SELECT teacher_id, name, wxid
                FROM teacher
                WHERE is_active = 1 AND COALESCE(identity_type, 'teacher') = 'teacher'"""
            )
        teachers = {row['name']: {'teacher_id': row['teacher_id'], 'wxid': row['wxid']} for row in teachers_data}

        # 导入数据
        imported = []
        errors = []

        # 年级名称映射
        grade_map = {'高一': 1, '高二': 2, '高三': 3}

        # 场次时间解析：从"场次"列解析时间（备用）
        def parse_session(session_str):
            """解析场次字符串，如 '第一场(08:00-10:00)' """
            import re
            match = re.search(r'\((\d{2}:\d{2})-(\d{2}:\d{2})\)', session_str)
            if match:
                return match.group(1), match.group(2)
            return '08:00', '10:00'  # 默认值

        if is_horizontal:
            # 横向布局：每行展开为多条slot记录
            required_cols = ['年级', '日期', '学科']
            missing_cols = [col for col in required_cols if col not in df.columns]
            if missing_cols:
                raise HTTPException(400, f"缺少必要列: {', '.join(missing_cols)}")

            # 列名两类：
            #   1) `考场N主监` / `考场N副监`（新格式，主副拆列）
            #   2) `考场N` / `第N考场监考`（旧格式，只有主监）
            # 用统一正则同时提取 room_order 与 role（默认 primary）
            room_col_pattern = re.compile(r'(?:考场(\d+)|(?:第)?(\d+)考场)(主监|副监)?')
            room_cols = [col for col in df.columns if room_col_pattern.search(col)]

            has_time_cols = '开始时间' in df.columns and '结束时间' in df.columns

            # 用 (grade_id, date, start, end, subject, room_order) 汇聚主/副
            slot_bag: Dict[tuple, dict] = {}

            for idx, row in df.iterrows():
                row_no = idx + 2  # Excel 1-based + 表头一行
                try:
                    grade_name = str(row['年级']).strip()
                    grade_id = grade_map.get(grade_name)
                    if grade_id is None:
                        errors.append(f"第{row_no}行 · 年级列：'{grade_name}' 无法识别（应为 高一/高二/高三）")
                        continue

                    if grade_id not in allowed_grades:
                        errors.append(f"第{row_no}行 · 年级列：'{grade_name}' 不在本考试项目的年级范围内")
                        continue

                    exam_date = _normalize_date_cell(row['日期'])
                    if not exam_date:
                        errors.append(f"第{row_no}行 · 日期列：'{row['日期']}' 无法解析（示例 2026-07-07 或 2026/7/7）")
                        continue

                    subject = str(row['学科']).strip()

                    if has_time_cols:
                        start_time = _normalize_time_cell(row['开始时间'])
                        end_time = _normalize_time_cell(row['结束时间'])
                        if not start_time:
                            errors.append(f"第{row_no}行 · 开始时间列：'{row['开始时间']}' 无法解析（示例 08:00）")
                            continue
                        if not end_time:
                            errors.append(f"第{row_no}行 · 结束时间列：'{row['结束时间']}' 无法解析（示例 10:00）")
                            continue
                    elif '场次' in df.columns:
                        start_time, end_time = parse_session(str(row['场次']))
                        start_time = _normalize_time_cell(start_time)
                        end_time = _normalize_time_cell(end_time)
                    else:
                        errors.append(f"第{row_no}行：缺少时间信息（需要 开始时间/结束时间 或 场次 列）")
                        continue

                    if start_time and end_time and start_time >= end_time:
                        errors.append(
                            f"第{row_no}行 · {subject}：开始时间 {start_time} 不早于结束时间 {end_time}"
                        )
                        continue

                    for room_col in room_cols:
                        m = room_col_pattern.search(room_col)
                        if not m:
                            continue
                        room_order = int(m.group(1) or m.group(2))
                        role_label = m.group(3) or '主监'  # 未标注的当主监
                        role = 'assistant' if role_label == '副监' else 'primary'
                        room_name = f"考场{room_order}"

                        teacher_name = row.get(room_col)
                        if pd.isna(teacher_name) or not teacher_name or not str(teacher_name).strip():
                            continue

                        teacher_name = str(teacher_name).strip()
                        teacher_info = teachers.get(teacher_name)
                        if not teacher_info:
                            errors.append(
                                f"第{row_no}行 · {subject} · {room_col}：教师 '{teacher_name}' 不在教师库中"
                            )
                            continue

                        key = (grade_id, exam_date, start_time, end_time, subject, room_order)
                        bucket = slot_bag.setdefault(key, {
                            'grade_id': grade_id,
                            'grade_name': grade_name,
                            'exam_date': exam_date,
                            'start_time': start_time,
                            'end_time': end_time,
                            'subject': subject,
                            'room_name': room_name,
                            'room_order': room_order,
                            'teacher_id': None,
                            'teacher_name': None,
                            'teacher_wxid': None,
                            'assistant_teacher_id': None,
                            'assistant_teacher_name': None,
                            'assistant_teacher_wxid': None,
                            'source': 'import',
                            '_row_primary': None,
                            '_row_assistant': None,
                        })
                        if role == 'primary':
                            if bucket['teacher_id']:
                                errors.append(
                                    f"第{row_no}行 · {subject} · {room_col}：{grade_name}{room_name} "
                                    f"已由第{bucket['_row_primary']}行的 {bucket['teacher_name']} 担任主监，"
                                    f"现在又要指派 {teacher_name}，请合并同一场次的主监列"
                                )
                                continue
                            bucket['teacher_id'] = teacher_info['teacher_id']
                            bucket['teacher_name'] = teacher_name
                            bucket['teacher_wxid'] = teacher_info['wxid']
                            bucket['_row_primary'] = row_no
                        else:
                            if bucket['assistant_teacher_id']:
                                errors.append(
                                    f"第{row_no}行 · {subject} · {room_col}：{grade_name}{room_name} "
                                    f"已由第{bucket['_row_assistant']}行的 {bucket['assistant_teacher_name']} 担任副监，"
                                    f"现在又要指派 {teacher_name}，请合并同一场次的副监列"
                                )
                                continue
                            bucket['assistant_teacher_id'] = teacher_info['teacher_id']
                            bucket['assistant_teacher_name'] = teacher_name
                            bucket['assistant_teacher_wxid'] = teacher_info['wxid']
                            bucket['_row_assistant'] = row_no

                except Exception as e:
                    errors.append(f"第{row_no}行：数据格式错误 - {str(e)}")

            imported.extend(slot_bag.values())

        else:
            # 纵向布局（传统格式）
            #  - 旧模板必要列：年级 日期 开始时间 结束时间 学科 考场 监考老师
            #  - 新模板必要列：年级 日期 开始时间 结束时间 学科 考场 主监老师（副监老师可空）
            required_cols_new = ['年级', '日期', '开始时间', '结束时间', '学科', '考场', '主监老师']
            required_cols_legacy = ['年级', '日期', '开始时间', '结束时间', '学科', '考场', '监考老师']

            if all(c in df.columns for c in required_cols_new):
                primary_col, assistant_col = '主监老师', '副监老师'
            elif all(c in df.columns for c in required_cols_legacy):
                primary_col, assistant_col = '监考老师', None  # 兼容旧格式
            else:
                missing_cols = [c for c in required_cols_new if c not in df.columns]
                raise HTTPException(400, f"缺少必要列: {', '.join(missing_cols)}")

            for idx, row in df.iterrows():
                row_no = idx + 2
                try:
                    grade_name = str(row['年级']).strip()
                    grade_id = grade_map.get(grade_name)
                    if grade_id is None:
                        errors.append(f"第{row_no}行 · 年级列：'{grade_name}' 无法识别（应为 高一/高二/高三）")
                        continue

                    if grade_id not in allowed_grades:
                        errors.append(f"第{row_no}行 · 年级列：'{grade_name}' 不在本考试项目的年级范围内")
                        continue

                    exam_date = _normalize_date_cell(row['日期'])
                    if not exam_date:
                        errors.append(f"第{row_no}行 · 日期列：'{row['日期']}' 无法解析（示例 2026-07-07 或 2026/7/7）")
                        continue

                    start_time = _normalize_time_cell(row['开始时间'])
                    end_time = _normalize_time_cell(row['结束时间'])
                    if not start_time:
                        errors.append(f"第{row_no}行 · 开始时间列：'{row['开始时间']}' 无法解析（示例 08:00）")
                        continue
                    if not end_time:
                        errors.append(f"第{row_no}行 · 结束时间列：'{row['结束时间']}' 无法解析（示例 10:00）")
                        continue
                    if start_time >= end_time:
                        errors.append(
                            f"第{row_no}行：开始时间 {start_time} 不早于结束时间 {end_time}"
                        )
                        continue

                    subject = str(row['学科']).strip()
                    room_name = str(row['考场']).strip()
                    room_order = int(row.get('考场序号', 0)) if '考场序号' in df.columns else 0

                    def _resolve(col_name):
                        raw = row.get(col_name)
                        if pd.isna(raw) or not raw or not str(raw).strip():
                            return None
                        name = str(raw).strip()
                        info = teachers.get(name)
                        if not info:
                            errors.append(
                                f"第{row_no}行 · {subject} · {col_name}：教师 '{name}' 不在教师库中"
                            )
                            return None
                        return {'name': name, **info}

                    primary = _resolve(primary_col)
                    assistant = _resolve(assistant_col) if assistant_col else None

                    if not primary and not assistant:
                        errors.append(
                            f"第{row_no}行 · {subject} · {room_name}：主监与副监均为空，至少填一位"
                        )
                        continue

                    imported.append({
                        'grade_id': grade_id,
                        'grade_name': grade_name,
                        'exam_date': exam_date,
                        'start_time': start_time,
                        'end_time': end_time,
                        'subject': subject,
                        'room_name': room_name,
                        'room_order': room_order,
                        'teacher_id': primary['teacher_id'] if primary else None,
                        'teacher_name': primary['name'] if primary else None,
                        'teacher_wxid': primary['wxid'] if primary else None,
                        'assistant_teacher_id': assistant['teacher_id'] if assistant else None,
                        'assistant_teacher_name': assistant['name'] if assistant else None,
                        'assistant_teacher_wxid': assistant['wxid'] if assistant else None,
                        'source': 'import',
                        '_row_primary': row_no if primary else None,
                        '_row_assistant': row_no if assistant else None,
                    })

                except Exception as e:
                    errors.append(f"第{row_no}行：数据格式错误 - {str(e)}")

        if errors:
            return {
                "success": False,
                "message": "导入有错误",
                "data": {
                    "imported_count": len(imported),
                    "error_count": len(errors),
                    "errors": errors
                }
            }

        # 检查导入数据内部的冲突：
        # 1) 同一场考试的主监与副监是同一人
        # 2) 同一教师同一日期出现时段交叠（主/副都算，跨考场也算）
        # 因为现在支持"分年级分批导入"，还要检查本次数据与库中【其他年级已有场次】的冲突，
        #   避免高一 Excel 中的张三与库里已存在的高二安排重叠。
        # 报错消息统一格式：
        #   冲突：教师 X 在 2026-07-07 08:00:00-10:00:00 高一·数学·考场1（主监，第3行）
        #         与 08:30:00-10:30:00 高一·语文·考场2（副监，第7行）时间重叠
        def _slot_label(slot, role) -> str:
            role_label = '主监' if role == 'primary' else '副监'
            row_no = slot.get('_row_primary' if role == 'primary' else '_row_assistant')
            # 库中已存在的场次没有 _row_* ，改成"已存在"提示
            row_part = f"，第{row_no}行" if row_no else "，已存在"
            return (
                f"{slot['exam_date']} {slot['start_time']}-{slot['end_time']} "
                f"{slot['grade_name']}·{slot['subject']}·{slot['room_name']}"
                f"（{role_label}{row_part}）"
            )

        # 预加载：库里本项目【非本次导入年级】的场次，作为冲突检测的底盘
        # （本次要导入的年级会被 DELETE 覆盖，不需要参与冲突判断）
        imported_grade_ids_preview = sorted({slot['grade_id'] for slot in imported})
        teacher_day_slots: Dict[tuple, list] = {}
        if imported_grade_ids_preview:
            placeholders = ",".join("?" * len(imported_grade_ids_preview))
            cursor.execute(
                f"""SELECT grade_id, grade_name, exam_date, start_time, end_time,
                           subject, room_name,
                           teacher_id, teacher_name,
                           assistant_teacher_id, assistant_teacher_name
                    FROM invigilation_slot
                    WHERE project_id = ? AND grade_id NOT IN ({placeholders})""",
                (project_id, *imported_grade_ids_preview),
            )
            for existing in cursor.fetchall():
                base = dict(existing)  # sqlite3.Row -> dict
                for role, id_key in (('primary', 'teacher_id'), ('assistant', 'assistant_teacher_id')):
                    tid = base.get(id_key)
                    if not tid:
                        continue
                    teacher_day_slots.setdefault((tid, base['exam_date']), []).append((base, role))

        for slot in imported:
            if slot.get('teacher_id') and slot.get('assistant_teacher_id') \
                    and slot['teacher_id'] == slot['assistant_teacher_id']:
                row_hint = ''
                if slot.get('_row_primary'):
                    row_hint = f"（第{slot['_row_primary']}行）"
                errors.append(
                    f"冲突：{slot['exam_date']} {slot['start_time']}-{slot['end_time']} "
                    f"{slot['grade_name']}·{slot['subject']}·{slot['room_name']}"
                    f"{row_hint} 的主监与副监同为 {slot['teacher_name']}，请拆分为两位老师"
                )
                continue
            for role, id_key in (('primary', 'teacher_id'), ('assistant', 'assistant_teacher_id')):
                tid = slot.get(id_key)
                if not tid:
                    continue
                bucket = teacher_day_slots.setdefault((tid, slot['exam_date']), [])
                # 与已登记的 slot 逐一比时段交叠（[s1,e1) 与 [s2,e2) 相交等价于 s1 < e2 and s2 < e1）
                for other_slot, other_role in bucket:
                    if slot['start_time'] < other_slot['end_time'] and other_slot['start_time'] < slot['end_time']:
                        name_key = 'teacher_name' if role == 'primary' else 'assistant_teacher_name'
                        errors.append(
                            f"冲突：教师 {slot[name_key]} 在 {_slot_label(other_slot, other_role)} "
                            f"与 {_slot_label(slot, role)} 时间重叠"
                        )
                bucket.append((slot, role))

        if errors:
            return {
                "success": False,
                "message": "导入有错误（存在时间冲突）",
                "data": {
                    "imported_count": 0,
                    "error_count": len(errors),
                    "errors": errors
                }
            }

        # 只清理本次导入涉及的年级，避免"分年级分批导入"时互相覆盖。
        # 例如：先导高二、后导高一，若按 project_id 全删，会把之前的高二清空。
        imported_grade_ids = sorted({slot['grade_id'] for slot in imported})
        if imported_grade_ids:
            placeholders = ",".join("?" * len(imported_grade_ids))
            cursor.execute(
                f"DELETE FROM invigilation_slot WHERE project_id = ? AND grade_id IN ({placeholders})",
                (project_id, *imported_grade_ids),
            )

        for slot in imported:
            cursor.execute("""
                INSERT INTO invigilation_slot
                (project_id, grade_id, grade_name, exam_date, start_time, end_time, subject, room_name, room_order,
                 teacher_id, teacher_name, teacher_wxid,
                 assistant_teacher_id, assistant_teacher_name, assistant_teacher_wxid,
                 source)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                project_id, slot['grade_id'], slot['grade_name'], slot['exam_date'],
                slot['start_time'], slot['end_time'], slot['subject'], slot['room_name'],
                slot['room_order'],
                slot.get('teacher_id'), slot.get('teacher_name'), slot.get('teacher_wxid'),
                slot.get('assistant_teacher_id'), slot.get('assistant_teacher_name'), slot.get('assistant_teacher_wxid'),
                slot['source'],
            ))

        db.commit()

        # 上报本次覆盖的年级，前端可给用户一个明确回执
        grade_names = sorted({slot['grade_name'] for slot in imported})
        return {
            "success": True,
            "message": f"导入成功，已更新 {'、'.join(grade_names)} 的监考安排",
            "data": {
                "count": len(imported),
                "grades": grade_names,
            }
        }


@router.get("/projects/{project_id}/export", summary="导出监考安排")
async def export_invigilation(
    project_id: int,
    user: User = Depends(require_invigilation_permission("/api/invigilation/projects/{project_id}/export", "GET"))
):
    """导出监考安排 Excel（横向布局，同一学科不同考场横向排列）"""
    import pandas as pd

    with get_invigilation_db() as db:
        cursor = db.cursor()

        # 获取项目信息
        cursor.execute("SELECT name FROM exam_project WHERE id = ?", (project_id,))
        project = cursor.fetchone()
        if not project:
            raise HTTPException(404, "考试项目不存在")

        # 获取所有安排
        cursor.execute("""
            SELECT grade_id, grade_name, exam_date, start_time, end_time, subject, room_name,
                   teacher_name, assistant_teacher_name, room_order
            FROM invigilation_slot
            WHERE project_id = ?
            ORDER BY grade_id, exam_date, start_time, room_order
        """, (project_id,))

        slots = [dict(row) for row in cursor.fetchall()]

        # 按年级分组，转换为横向布局
        grade_slots = {}
        for slot in slots:
            grade = slot['grade_name']
            if grade not in grade_slots:
                grade_slots[grade] = []

        # 每个年级单独处理
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            for grade_name in sorted(grade_slots.keys(), key=lambda x: {'高一': 1, '高二': 2, '高三': 3}.get(x, 0)):
                grade_slots_raw = [s for s in slots if s['grade_name'] == grade_name]

                # 转换为横向布局：按 (日期, 开始时间, 学科) 分组
                horizontal_data = []
                grouped = {}

                for slot in grade_slots_raw:
                    key = (slot['exam_date'], slot['start_time'], slot['end_time'], slot['subject'])
                    if key not in grouped:
                        grouped[key] = {
                            '年级': grade_name,
                            '日期': slot['exam_date'],
                            '开始时间': slot['start_time'],
                            '结束时间': slot['end_time'],
                            '学科': slot['subject']
                        }
                    # 主监 + 副监各占一列
                    grouped[key][f"考场{slot['room_order']}主监"] = slot['teacher_name'] or ''
                    grouped[key][f"考场{slot['room_order']}副监"] = slot['assistant_teacher_name'] or ''

                # 获取最大考场数
                max_room = max(
                    (s['room_order'] for s in grade_slots_raw),
                    default=0
                )

                # 构建DataFrame
                for key in sorted(grouped.keys()):
                    row_data = grouped[key]
                    for i in range(1, max_room + 1):
                        row_data.setdefault(f"考场{i}主监", '')
                        row_data.setdefault(f"考场{i}副监", '')
                    horizontal_data.append(row_data)

                room_cols = []
                for i in range(1, max_room + 1):
                    room_cols.extend([f"考场{i}主监", f"考场{i}副监"])

                if horizontal_data:
                    columns = ['年级', '日期', '开始时间', '结束时间', '学科'] + room_cols
                    df = pd.DataFrame(horizontal_data)
                    df = df[columns]
                    df.to_excel(writer, index=False, sheet_name=grade_name)
                else:
                    df = pd.DataFrame(columns=['年级', '日期', '开始时间', '结束时间', '学科', '考场1主监', '考场1副监'])
                    df.to_excel(writer, index=False, sheet_name=grade_name)

            if not grade_slots:
                df = pd.DataFrame(columns=['年级', '日期', '开始时间', '结束时间', '学科', '考场1主监', '考场1副监'])
                df.to_excel(writer, index=False, sheet_name='监考安排')

        output.seek(0)

        filename = f"{project['name']}_监考安排.xlsx"
        encoded_filename = quote(filename)

        return StreamingResponse(
            output,
            media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            headers={'Content-Disposition': f"attachment; filename*=UTF-8''{encoded_filename}"}
        )


@router.get("/projects/{project_id}/report", summary="导出监考工作量报表")
async def export_workload_report(
    project_id: int,
    user: User = Depends(require_invigilation_permission("/api/invigilation/projects/{project_id}/report", "GET"))
):
    """
    导出监考工作量报表

    报表内容：
    - Sheet1: 教师工作量汇总（场次数、监考时长）
    - Sheet2: 按年级细化统计
    """
    import pandas as pd

    with get_invigilation_db() as db:
        cursor = db.cursor()

        # 获取项目信息
        cursor.execute("SELECT name FROM exam_project WHERE id = ?", (project_id,))
        project = cursor.fetchone()
        if not project:
            raise HTTPException(404, "考试项目不存在")

        # Sheet1: 教师工作量汇总（主监、副监都算 1 场；同一教师若同时是主+副在不同场次，累加）
        # 时长口径：以 exam_date + start_time/end_time 拼成完整时刻后取秒差 /60。
        #   - exam_date 兼容 'YYYY-MM-DD' 与 'YYYY-MM-DD HH:MM:SS' 两种存法（date() 归一化）
        #   - start_time/end_time 兼容 'HH:MM' 与 'HH:MM:SS' 两种存法（time() 归一化）
        #   - 任一字段格式非法时 strftime 返回 NULL，该行不计入 SUM，避免脏数据污染统计
        cursor.execute("""
            WITH slot_role AS (
                SELECT teacher_id, teacher_name, grade_id, grade_name,
                       exam_date, start_time, end_time
                FROM invigilation_slot
                WHERE project_id = ? AND teacher_name IS NOT NULL AND teacher_name != ''
                UNION ALL
                SELECT assistant_teacher_id AS teacher_id,
                       assistant_teacher_name AS teacher_name,
                       grade_id, grade_name,
                       exam_date, start_time, end_time
                FROM invigilation_slot
                WHERE project_id = ? AND assistant_teacher_name IS NOT NULL AND assistant_teacher_name != ''
            )
            SELECT teacher_name,
                   COUNT(*) AS slot_count,
                   SUM(
                       ( strftime('%s', date(exam_date) || ' ' || time(end_time))
                       - strftime('%s', date(exam_date) || ' ' || time(start_time)) ) / 60
                   ) AS duration_minutes
            FROM slot_role
            GROUP BY teacher_id, teacher_name
            ORDER BY slot_count DESC, duration_minutes DESC
        """, (project_id, project_id))

        summary_data = []
        for row in cursor.fetchall():
            summary_data.append({
                '教师姓名': row['teacher_name'],
                '监考场次': row['slot_count'],
                '监考时长(分钟)': int(row['duration_minutes'] or 0)
            })

        # Sheet2: 按年级细化统计（同上，主副都算；时长口径与 Sheet1 一致）
        cursor.execute("""
            WITH slot_role AS (
                SELECT teacher_id, teacher_name, grade_id, grade_name,
                       exam_date, start_time, end_time
                FROM invigilation_slot
                WHERE project_id = ? AND teacher_name IS NOT NULL AND teacher_name != ''
                UNION ALL
                SELECT assistant_teacher_id AS teacher_id,
                       assistant_teacher_name AS teacher_name,
                       grade_id, grade_name,
                       exam_date, start_time, end_time
                FROM invigilation_slot
                WHERE project_id = ? AND assistant_teacher_name IS NOT NULL AND assistant_teacher_name != ''
            )
            SELECT teacher_name, grade_name,
                   COUNT(*) AS slot_count,
                   SUM(
                       ( strftime('%s', date(exam_date) || ' ' || time(end_time))
                       - strftime('%s', date(exam_date) || ' ' || time(start_time)) ) / 60
                   ) AS duration_minutes
            FROM slot_role
            GROUP BY teacher_id, teacher_name, grade_id, grade_name
            ORDER BY teacher_name, grade_id
        """, (project_id, project_id))

        grade_detail_data = []
        for row in cursor.fetchall():
            grade_detail_data.append({
                '教师姓名': row['teacher_name'],
                '年级': row['grade_name'],
                '监考场次': row['slot_count'],
                '监考时长(分钟)': int(row['duration_minutes'] or 0)
            })

        # 生成Excel
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            # Sheet1: 教师工作量汇总
            df_summary = pd.DataFrame(summary_data)
            if len(df_summary) > 0:
                df_summary.to_excel(writer, index=False, sheet_name='工作量汇总')
            else:
                pd.DataFrame(columns=['教师姓名', '监考场次', '监考时长(分钟)']).to_excel(
                    writer, index=False, sheet_name='工作量汇总'
                )

            # Sheet2: 按年级细化
            df_detail = pd.DataFrame(grade_detail_data)
            if len(df_detail) > 0:
                df_detail.to_excel(writer, index=False, sheet_name='年级细化')
            else:
                pd.DataFrame(columns=['教师姓名', '年级', '监考场次', '监考时长(分钟)']).to_excel(
                    writer, index=False, sheet_name='年级细化'
                )

            # Sheet3: 统计概览
            total_teachers = len(summary_data)
            total_slots = sum(d['监考场次'] for d in summary_data) if summary_data else 0
            total_minutes = sum(d['监考时长(分钟)'] for d in summary_data) if summary_data else 0

            overview_data = [
                {'统计项': '参与监考教师数', '数值': total_teachers},
                {'统计项': '总监考场次数', '数值': total_slots},
                {'统计项': '总监考时长(分钟)', '数值': total_minutes},
                {'统计项': '总监考时长(小时)', '数值': round(total_minutes / 60, 2)},
                {'统计项': '人均监考场次', '数值': round(total_slots / total_teachers, 2) if total_teachers > 0 else 0},
                {'统计项': '人均监考时长(分钟)', '数值': round(total_minutes / total_teachers, 2) if total_teachers > 0 else 0}
            ]
            df_overview = pd.DataFrame(overview_data)
            df_overview.to_excel(writer, index=False, sheet_name='统计概览')

        output.seek(0)

        filename = f"{project['name']}_监考工作量报表.xlsx"
        encoded_filename = quote(filename)

        return StreamingResponse(
            output,
            media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            headers={'Content-Disposition': f"attachment; filename*=UTF-8''{encoded_filename}"}
        )
