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

from fastapi import APIRouter, Depends, HTTPException, Query, Request, UploadFile, File, Body
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
import io

from models.datas_api.auth import User, get_current_user, is_admin_user
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
    teacher_id: Optional[str] = Field(None, description="教师ID")
    teacher_name: Optional[str] = Field(None, description="教师姓名")


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

def get_invigilation_db():
    """获取监考安排数据库连接"""
    conn = sqlite3.connect(INVIGILATION_DB)
    conn.row_factory = sqlite3.Row
    return conn


def require_jiaowu(user: User = Depends(get_current_user)) -> User:
    """检查教务权限"""
    if not is_admin_user(user) and 'jiaowu' not in (user.role or '').split('/'):
        raise HTTPException(403, "需要教务或管理员权限")
    return user


# =============================================================================
# 教师列表 API（从 moral.db 获取）
# =============================================================================

@router.get("/teachers", summary="获取教师列表")
async def get_teachers_for_invigilation(user: User = Depends(require_jiaowu)):
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
    user: User = Depends(require_jiaowu)
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
    user: User = Depends(require_jiaowu)
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
    user: User = Depends(require_jiaowu)
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
    user: User = Depends(require_jiaowu)
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
    user: User = Depends(require_jiaowu)
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
    user: User = Depends(require_jiaowu)
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
    user: User = Depends(require_jiaowu)
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

        # 检查batch内部是否有冲突（同一教师同一时间多个考场）
        teacher_time_map = {}
        for slot in batch.slots:
            if slot.teacher_id:
                key = f"{slot.teacher_id}|{slot.exam_date}|{slot.start_time}"
                if key in teacher_time_map:
                    raise HTTPException(400, f"教师 {slot.teacher_name} 在 {slot.exam_date} {slot.start_time} 安排了多个考场")
                teacher_time_map[key] = slot.room_name

        # 删除旧安排
        cursor.execute("DELETE FROM invigilation_slot WHERE project_id = ?", (project_id,))

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
            cursor.execute("""
                INSERT INTO invigilation_slot
                (project_id, grade_id, grade_name, exam_date, start_time, end_time, subject, room_name, room_order, teacher_id, teacher_name, teacher_wxid, source)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'manual')
            """, (
                project_id, slot.grade_id, slot.grade_name, slot.exam_date,
                slot.start_time, slot.end_time, slot.subject, slot.room_name,
                slot.room_order or 0, slot.teacher_id, slot.teacher_name, teacher_wxid
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
    user: User = Depends(require_jiaowu)
):
    """交换两条安排的监考老师"""
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

        # 交换教师信息
        cursor.execute("""
            UPDATE invigilation_slot
            SET teacher_id = ?, teacher_name = ?, updated_at = datetime('now', 'localtime')
            WHERE id = ?
        """, (slot2['teacher_id'], slot2['teacher_name'], slot_id_1))

        cursor.execute("""
            UPDATE invigilation_slot
            SET teacher_id = ?, teacher_name = ?, updated_at = datetime('now', 'localtime')
            WHERE id = ?
        """, (slot1['teacher_id'], slot1['teacher_name'], slot_id_2))

        db.commit()

        return {"success": True, "message": "交换成功"}


# =============================================================================
# 通知 API
# =============================================================================

@router.get("/projects/{project_id}/changes", summary="获取变更预览")
async def get_changes_preview(
    project_id: int,
    subjects: Optional[str] = Query(None, description="筛选学科，逗号分隔"),
    user: User = Depends(require_jiaowu)
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

        # 构建唯一键：grade_id + exam_date + start_time + room_name
        def get_key(slot):
            return f"{slot['grade_id']}|{slot['exam_date']}|{slot['start_time']}|{slot['room_name']}"

        current_map = {get_key(s): s for s in current_slots}
        previous_map = {get_key(s): s for s in previous_slots}

        # 检测变更
        added = []      # 新增监考
        removed = []    # 取消监考
        changed = []    # 教师变更（替换/交换）
        unchanged = []  # 无变化

        all_keys = set(current_map.keys()) | set(previous_map.keys())

        for key in all_keys:
            current_slot = current_map.get(key)
            previous_slot = previous_map.get(key)

            # 学科筛选
            if subject_filter:
                slot_subject = (current_slot or previous_slot).get('subject', '')
                if slot_subject not in subject_filter:
                    continue

            if not previous_slot and current_slot:
                # 新增
                if current_slot['teacher_id']:
                    added.append({
                        'teacher_id': current_slot['teacher_id'],
                        'teacher_name': current_slot['teacher_name'],
                        'teacher_wxid': current_slot['teacher_wxid'],
                        'slot': current_slot
                    })

            elif previous_slot and not current_slot:
                # 删除（整个场次取消）
                if previous_slot['teacher_id']:
                    removed.append({
                        'teacher_id': previous_slot['teacher_id'],
                        'teacher_name': previous_slot['teacher_name'],
                        'teacher_wxid': previous_slot['teacher_wxid'],
                        'slot': previous_slot,
                        'reason': '场次取消'
                    })

            elif previous_slot and current_slot:
                prev_teacher = previous_slot.get('teacher_id')
                curr_teacher = current_slot.get('teacher_id')

                if prev_teacher != curr_teacher:
                    # 教师变更
                    if prev_teacher and curr_teacher:
                        # 替换：拆成取消原教师 + 新增新教师
                        removed.append({
                            'teacher_id': prev_teacher,
                            'teacher_name': previous_slot['teacher_name'],
                            'teacher_wxid': previous_slot['teacher_wxid'],
                            'slot': previous_slot,
                            'reason': '教师替换'
                        })
                        added.append({
                            'teacher_id': curr_teacher,
                            'teacher_name': current_slot['teacher_name'],
                            'teacher_wxid': current_slot['teacher_wxid'],
                            'slot': current_slot
                        })
                        # 同时记录changed用于交换检测
                        changed.append({
                            'type': 'replace',
                            'old_teacher_id': prev_teacher,
                            'old_teacher_name': previous_slot['teacher_name'],
                            'old_teacher_wxid': previous_slot['teacher_wxid'],
                            'new_teacher_id': curr_teacher,
                            'new_teacher_name': current_slot['teacher_name'],
                            'new_teacher_wxid': current_slot['teacher_wxid'],
                            'slot': current_slot
                        })
                    elif prev_teacher and not curr_teacher:
                        # 取消该教师的监考
                        removed.append({
                            'teacher_id': prev_teacher,
                            'teacher_name': previous_slot['teacher_name'],
                            'teacher_wxid': previous_slot['teacher_wxid'],
                            'slot': previous_slot,
                            'reason': '教师取消'
                        })
                    elif not prev_teacher and curr_teacher:
                        # 新增教师
                        added.append({
                            'teacher_id': curr_teacher,
                            'teacher_name': current_slot['teacher_name'],
                            'teacher_wxid': current_slot['teacher_wxid'],
                            'slot': current_slot
                        })
                else:
                    # 无变化
                    if current_slot['teacher_id']:
                        unchanged.append({
                            'teacher_id': current_slot['teacher_id'],
                            'teacher_name': current_slot['teacher_name'],
                            'teacher_wxid': current_slot['teacher_wxid'],
                            'slot': current_slot
                        })

        # 检测交换：old→new 和 new→old 同时存在
        swaps = []
        # 构建替换映射
        replace_map = {}
        for ch in changed:
            if ch['type'] == 'replace':
                key_pair = (ch['old_teacher_id'], ch['new_teacher_id'])
                replace_map[key_pair] = ch

        # 检测交换并从removed/added中过滤
        processed_keys = set()
        swap_teacher_ids = set()
        for (old_id, new_id), ch in replace_map.items():
            if (new_id, old_id) in replace_map and (new_id, old_id) not in processed_keys:
                # 发现交换：A→B 和 B→A 同时存在
                ch2 = replace_map[(new_id, old_id)]
                swaps.append({
                    'type': 'swap',
                    'teacher_a_id': old_id,
                    'teacher_a_name': ch['old_teacher_name'],
                    'teacher_a_wxid': ch['old_teacher_wxid'],
                    'teacher_b_id': new_id,
                    'teacher_b_name': ch['new_teacher_name'],
                    'teacher_b_wxid': ch['new_teacher_wxid'],
                    'slot_a': ch['slot'],  # A原位置
                    'slot_b': ch2['slot']  # B原位置
                })
                # 交换教师从removed/added中移除（避免重复）
                swap_teacher_ids.add(old_id)
                swap_teacher_ids.add(new_id)
                processed_keys.add((old_id, new_id))
                processed_keys.add((new_id, old_id))

        # 从removed/added过滤掉交换教师
        removed = [r for r in removed if r['teacher_id'] not in swap_teacher_ids]
        added = [a for a in added if a['teacher_id'] not in swap_teacher_ids]

        # 汇总统计（changed仅用于交换检测，不再单独统计）
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
    user: User = Depends(require_jiaowu),
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

        # 检测变更（复用get_changes_preview的逻辑）
        def get_key(slot):
            return f"{slot['grade_id']}|{slot['exam_date']}|{slot['start_time']}|{slot['room_name']}"

        current_map = {get_key(s): s for s in current_slots}
        previous_map = {get_key(s): s for s in previous_slots}

        added = []
        removed = []
        changed = []
        unchanged = []

        all_keys = set(current_map.keys()) | set(previous_map.keys())

        for key in all_keys:
            current_slot = current_map.get(key)
            previous_slot = previous_map.get(key)

            # 学科筛选
            if subject_filter:
                slot_subject = (current_slot or previous_slot).get('subject', '')
                if slot_subject not in subject_filter:
                    continue

            if not previous_slot and current_slot:
                if current_slot['teacher_id']:
                    added.append({
                        'teacher_id': current_slot['teacher_id'],
                        'teacher_name': current_slot['teacher_name'],
                        'teacher_wxid': current_slot['teacher_wxid'],
                        'slot': current_slot
                    })
            elif previous_slot and current_slot:
                prev_teacher = previous_slot.get('teacher_id')
                curr_teacher = current_slot.get('teacher_id')

                if prev_teacher != curr_teacher:
                    if prev_teacher and curr_teacher:
                        # 替换：拆成取消原教师 + 新增新教师
                        removed.append({
                            'teacher_id': prev_teacher,
                            'teacher_name': previous_slot['teacher_name'],
                            'teacher_wxid': previous_slot['teacher_wxid'],
                            'slot': previous_slot,
                            'reason': '教师替换'
                        })
                        added.append({
                            'teacher_id': curr_teacher,
                            'teacher_name': current_slot['teacher_name'],
                            'teacher_wxid': current_slot['teacher_wxid'],
                            'slot': current_slot
                        })
                        # 同时记录changed用于交换检测
                        changed.append({
                            'old_teacher_id': prev_teacher,
                            'old_teacher_name': previous_slot['teacher_name'],
                            'old_teacher_wxid': previous_slot['teacher_wxid'],
                            'new_teacher_id': curr_teacher,
                            'new_teacher_name': current_slot['teacher_name'],
                            'new_teacher_wxid': current_slot['teacher_wxid'],
                            'slot': current_slot,
                            'old_slot': previous_slot
                        })
                    elif prev_teacher and not curr_teacher:
                        removed.append({
                            'teacher_id': prev_teacher,
                            'teacher_name': previous_slot['teacher_name'],
                            'teacher_wxid': previous_slot['teacher_wxid'],
                            'slot': previous_slot,
                            'reason': '教师取消'
                        })
                    elif not prev_teacher and curr_teacher:
                        added.append({
                            'teacher_id': curr_teacher,
                            'teacher_name': current_slot['teacher_name'],
                            'teacher_wxid': current_slot['teacher_wxid'],
                            'slot': current_slot
                        })
                else:
                    if current_slot['teacher_id']:
                        unchanged.append({
                            'teacher_id': current_slot['teacher_id'],
                            'teacher_name': current_slot['teacher_name'],
                            'teacher_wxid': current_slot['teacher_wxid'],
                            'slot': current_slot
                        })

        # 检测交换
        swaps = []

        replace_map = {}
        for ch in changed:
            key_pair = (ch['old_teacher_id'], ch['new_teacher_id'])
            replace_map[key_pair] = ch

        # 检测交换并过滤
        processed_keys = set()
        swap_teacher_ids = set()
        for (old_id, new_id), ch in replace_map.items():
            if (new_id, old_id) in replace_map and (new_id, old_id) not in processed_keys:
                ch2 = replace_map[(new_id, old_id)]
                swaps.append({
                    'teacher_a_id': old_id,
                    'teacher_a_name': ch['old_teacher_name'],
                    'teacher_a_wxid': ch['old_teacher_wxid'],
                    'teacher_b_id': new_id,
                    'teacher_b_name': ch['new_teacher_name'],
                    'teacher_b_wxid': ch['new_teacher_wxid'],
                    'slot_a': ch['slot'],
                    'slot_b': ch2['slot']
                })
                swap_teacher_ids.add(old_id)
                swap_teacher_ids.add(new_id)
                processed_keys.add((old_id, new_id))
                processed_keys.add((new_id, old_id))

        # 从removed/added过滤掉交换教师
        removed = [r for r in removed if r['teacher_id'] not in swap_teacher_ids]
        added = [a for a in added if a['teacher_id'] not in swap_teacher_ids]

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
            # 按教师聚合unchanged
            teacher_unchanged = {}
            for item in unchanged:
                tid = item['teacher_id']
                if tid not in teacher_unchanged:
                    teacher_unchanged[tid] = {
                        'teacher_name': item['teacher_name'],
                        'teacher_wxid': item['teacher_wxid'],
                        'slots': []
                    }
                teacher_unchanged[tid]['slots'].append(item['slot'])

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
    user: User = Depends(require_jiaowu)
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
async def download_template(user: User = Depends(require_jiaowu)):
    """下载监考安排导入模板（横向布局）"""
    import pandas as pd

    # 横向布局：同一学科不同考场横向排列，只有时间没有场次
    template_data = {
        '年级': ['高一', '高一', '高一', '高二', '高二', '高三'],
        '日期': ['2026-05-10', '2026-05-10', '2026-05-11', '2026-05-10', '2026-05-10', '2026-05-11'],
        '开始时间': ['08:00', '10:20', '14:00', '08:00', '10:20', '08:00'],
        '结束时间': ['10:00', '12:00', '16:00', '10:00', '12:00', '10:00'],
        '学科': ['语文', '数学', '英语', '语文', '数学', '物理'],
        '考场1': ['任庆叶', '侯莹', '刘亚利', '刘斌', '张炜', '戴建海'],
        '考场2': ['任秀辉', '冯秀珍', '单俊杰', '刘晓玲', '张鹏飞', '宋文燕'],
        '考场3': ['', '', '', '', '', '']  # 空示例，可选
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
    user: User = Depends(require_jiaowu)
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

            room_cols = [col for col in df.columns if re.match(r'(?:考场\d+|第?\d+考场)', col)]

            # 检查是否有独立的时间列
            has_time_cols = '开始时间' in df.columns and '结束时间' in df.columns

            for idx, row in df.iterrows():
                try:
                    grade_name = str(row['年级'])
                    grade_id = grade_map.get(grade_name)
                    if grade_id is None:
                        errors.append(f"第{idx+2}行: 年级 '{grade_name}' 无法识别")
                        continue

                    if grade_id not in allowed_grades:
                        errors.append(f"第{idx+2}行: 年级 '{grade_name}' 不属于该考试项目")
                        continue

                    exam_date = str(row['日期'])
                    subject = str(row['学科'])

                    # 获取时间：优先使用独立列，否则从场次解析
                    if has_time_cols:
                        start_time = str(row['开始时间'])
                        end_time = str(row['结束时间'])
                    elif '场次' in df.columns:
                        session = str(row['场次'])
                        start_time, end_time = parse_session(session)
                    else:
                        errors.append(f"第{idx+2}行: 缺少时间信息")
                        continue

                    # 展开横向考场列
                    for room_col in room_cols:
                        # 解析考场名称：支持 "考场1" 或 "第1考场监考" 格式
                        room_match = re.search(r'(?:考场(\d+)|(?:第)?(\d+)考场)', room_col)
                        if room_match:
                            # 取第一个匹配的数字组
                            room_order = int(room_match.group(1) or room_match.group(2))
                            room_name = f"考场{room_order}"
                        else:
                            room_order = 0
                            room_name = room_col

                        teacher_name = row.get(room_col)
                        if pd.isna(teacher_name) or not teacher_name:
                            continue  # 空单元格跳过

                        teacher_name = str(teacher_name)
                        teacher_info = teachers.get(teacher_name)
                        if not teacher_info:
                            errors.append(f"第{idx+2}行 {room_col}: 教师 '{teacher_name}' 未找到")
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
                            'teacher_id': teacher_info['teacher_id'],
                            'teacher_name': teacher_name,
                            'teacher_wxid': teacher_info['wxid'],
                            'source': 'import'
                        })

                except Exception as e:
                    errors.append(f"第{idx+2}行: 数据格式错误 - {str(e)}")

        else:
            # 纵向布局（传统格式）
            required_cols = ['年级', '日期', '开始时间', '结束时间', '学科', '考场', '监考老师']
            missing_cols = [col for col in required_cols if col not in df.columns]
            if missing_cols:
                raise HTTPException(400, f"缺少必要列: {', '.join(missing_cols)}")

            for idx, row in df.iterrows():
                try:
                    grade_name = str(row['年级'])
                    grade_id = grade_map.get(grade_name)
                    if grade_id is None:
                        errors.append(f"第{idx+2}行: 年级 '{grade_name}' 无法识别")
                        continue

                    if grade_id not in allowed_grades:
                        errors.append(f"第{idx+2}行: 年级 '{grade_name}' 不属于该考试项目")
                        continue

                    exam_date = str(row['日期'])
                    start_time = str(row['开始时间'])
                    end_time = str(row['结束时间'])
                    subject = str(row['学科'])
                    room_name = str(row['考场'])
                    teacher_name = str(row['监考老师'])
                    room_order = int(row.get('考场序号', 0)) if '考场序号' in df.columns else 0

                    teacher_info = teachers.get(teacher_name)
                    if not teacher_info:
                        errors.append(f"第{idx+2}行: 教师 '{teacher_name}' 未找到")
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
                        'teacher_id': teacher_info['teacher_id'],
                        'teacher_name': teacher_name,
                        'teacher_wxid': teacher_info['wxid'],
                        'source': 'import'
                    })

                except Exception as e:
                    errors.append(f"第{idx+2}行: 数据格式错误 - {str(e)}")

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

        # 清除旧数据并插入新数据
        cursor.execute("DELETE FROM invigilation_slot WHERE project_id = ?", (project_id,))

        for slot in imported:
            cursor.execute("""
                INSERT INTO invigilation_slot
                (project_id, grade_id, grade_name, exam_date, start_time, end_time, subject, room_name, room_order, teacher_id, teacher_name, teacher_wxid, source)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                project_id, slot['grade_id'], slot['grade_name'], slot['exam_date'],
                slot['start_time'], slot['end_time'], slot['subject'], slot['room_name'],
                slot['room_order'], slot['teacher_id'], slot['teacher_name'], slot['teacher_wxid'], slot['source']
            ))

        db.commit()

        return {
            "success": True,
            "message": "导入成功",
            "data": {"count": len(imported)}
        }


@router.get("/projects/{project_id}/export", summary="导出监考安排")
async def export_invigilation(
    project_id: int,
    user: User = Depends(require_jiaowu)
):
    """导出监考安排 Excel"""
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
            SELECT grade_name, exam_date, start_time, end_time, subject, room_name, teacher_name, room_order
            FROM invigilation_slot
            WHERE project_id = ?
            ORDER BY grade_id, exam_date, start_time, room_order
        """, (project_id,))

        slots = [dict(row) for row in cursor.fetchall()]

        # 按年级分组
        grade_slots = {}
        for slot in slots:
            grade = slot['grade_name']
            if grade not in grade_slots:
                grade_slots[grade] = []
            grade_slots[grade].append(slot)

        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            # 每个年级一个 sheet
            for grade_name, grade_data in grade_slots.items():
                df = pd.DataFrame(grade_data)
                df = df[['exam_date', 'start_time', 'end_time', 'subject', 'room_name', 'teacher_name', 'room_order']]
                df.columns = ['日期', '开始时间', '结束时间', '学科', '考场', '监考老师', '考场序号']
                df.to_excel(writer, index=False, sheet_name=grade_name)

            # 如果没有数据，创建空sheet
            if not grade_slots:
                df = pd.DataFrame(columns=['年级', '日期', '开始时间', '结束时间', '学科', '考场', '监考老师', '考场序号'])
                df.to_excel(writer, index=False, sheet_name='监考安排')

        output.seek(0)

        filename = f"{project['name']}_监考安排.xlsx"

        return StreamingResponse(
            output,
            media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            headers={'Content-Disposition': f'attachment; filename={filename}'}
        )


@router.get("/projects/{project_id}/report", summary="导出监考工作量报表")
async def export_workload_report(
    project_id: int,
    user: User = Depends(require_jiaowu)
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

        # Sheet1: 教师工作量汇总
        cursor.execute("""
            SELECT teacher_name,
                   COUNT(*) as slot_count,
                   SUM(
                     (strftime('%s', end_time) - strftime('%s', start_time)) / 60
                   ) as duration_minutes
            FROM invigilation_slot
            WHERE project_id = ? AND teacher_name IS NOT NULL AND teacher_name != ''
            GROUP BY teacher_id, teacher_name
            ORDER BY slot_count DESC, duration_minutes DESC
        """, (project_id,))

        summary_data = []
        for row in cursor.fetchall():
            summary_data.append({
                '教师姓名': row['teacher_name'],
                '监考场次': row['slot_count'],
                '监考时长(分钟)': int(row['duration_minutes'] or 0)
            })

        # Sheet2: 按年级细化统计
        cursor.execute("""
            SELECT teacher_name, grade_name,
                   COUNT(*) as slot_count,
                   SUM(
                     (strftime('%s', end_time) - strftime('%s', start_time)) / 60
                   ) as duration_minutes
            FROM invigilation_slot
            WHERE project_id = ? AND teacher_name IS NOT NULL AND teacher_name != ''
            GROUP BY teacher_id, teacher_name, grade_id, grade_name
            ORDER BY teacher_name, grade_id
        """, (project_id,))

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

        return StreamingResponse(
            output,
            media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            headers={'Content-Disposition': f'attachment; filename={filename}'}
        )
