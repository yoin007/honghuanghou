# -*- coding: utf-8 -*-
"""
监考安排 API 模块

实现考试项目和监考安排的完整管理功能
"""

import sqlite3
import os
import json
import logging
from datetime import datetime, date
from typing import Optional, List, Dict, Any
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query, Request, UploadFile, File
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
import io

from models.datas_api.auth import User, get_current_user, is_admin_user
from utils.db_config import INVIGILATION_DB
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
    """删除考试项目（归档）"""
    with get_invigilation_db() as db:
        cursor = db.cursor()

        cursor.execute("SELECT id FROM exam_project WHERE id = ?", (project_id,))
        if not cursor.fetchone():
            raise HTTPException(404, "考试项目不存在")

        # 软删除：改为归档状态
        cursor.execute(
            "UPDATE exam_project SET status = 'archived', updated_at = datetime('now', 'localtime') WHERE id = ?",
            (project_id,)
        )
        db.commit()

        return {"success": True, "message": "已归档"}


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

        # 检查冲突
        for slot in batch.slots:
            # 检查年级是否属于项目
            if slot.grade_id not in allowed_grades:
                raise HTTPException(400, f"年级 {slot.grade_id} 不属于该考试项目")

            # 检查同一老师同一时间是否在多个考场
            if slot.teacher_id:
                cursor.execute("""
                    SELECT id FROM invigilation_slot
                    WHERE project_id = ? AND teacher_id = ?
                    AND exam_date = ? AND start_time = ?
                    AND room_name != ?
                """, (project_id, slot.teacher_id, slot.exam_date, slot.start_time, slot.room_name))
                conflict = cursor.fetchone()
                if conflict:
                    raise HTTPException(400, f"教师 {slot.teacher_name} 在 {slot.exam_date} {slot.start_time} 已有其他考场安排")

        # 删除旧安排
        cursor.execute("DELETE FROM invigilation_slot WHERE project_id = ?", (project_id,))

        # 插入新安排
        for slot in batch.slots:
            cursor.execute("""
                INSERT INTO invigilation_slot
                (project_id, grade_id, grade_name, exam_date, start_time, end_time, subject, room_name, room_order, teacher_id, teacher_name, source)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'manual')
            """, (
                project_id, slot.grade_id, slot.grade_name, slot.exam_date,
                slot.start_time, slot.end_time, slot.subject, slot.room_name,
                slot.room_order or 0, slot.teacher_id, slot.teacher_name
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

@router.post("/projects/{project_id}/notify", summary="发送监考通知")
async def send_notifications(
    project_id: int,
    request: NotifyRequest,
    user: User = Depends(require_jiaowu)
):
    """发送监考通知给老师"""
    with get_invigilation_db() as db:
        cursor = db.cursor()

        # 获取项目信息
        cursor.execute("SELECT * FROM exam_project WHERE id = ?", (project_id,))
        project = cursor.fetchone()
        if not project:
            raise HTTPException(404, "考试项目不存在")

        # 获取所有安排
        cursor.execute("""
            SELECT * FROM invigilation_slot
            WHERE project_id = ?
            ORDER BY teacher_id, exam_date, start_time
        """, (project_id,))

        slots = [dict(row) for row in cursor.fetchall()]

        # 按教师聚合
        teacher_slots = {}
        for slot in slots:
            teacher_id = slot['teacher_id']
            if teacher_id:
                if teacher_id not in teacher_slots:
                    teacher_slots[teacher_id] = {
                        'teacher_name': slot['teacher_name'],
                        'teacher_wxid': slot['teacher_wxid'],
                        'slots': []
                    }
                teacher_slots[teacher_id]['slots'].append(slot)

        # 发送通知
        success_count = 0
        failed_count = 0
        skipped_count = 0
        logs = []

        new_version = project['version_no'] + 1

        for teacher_id, data in teacher_slots.items():
            teacher_name = data['teacher_name']
            teacher_wxid = data['teacher_wxid']
            slots_list = data['slots']

            # 构建通知内容
            content = f"""【监考安排通知】
考试：{project['name']}
{teacher_name}老师，您的监考安排如下：
"""

            for i, slot in enumerate(slots_list, 1):
                content += f"{i}. {slot['exam_date']} {slot['start_time']}-{slot['end_time']} {slot['subject']} {slot['grade_name']} {slot['room_name']}\n"

            content += "请准时到岗。"

            log_entry = {
                'project_id': project_id,
                'version_no': new_version,
                'teacher_name': teacher_name,
                'teacher_id': teacher_id,
                'receiver': teacher_wxid,
                'message': content,
                'change_type': 'initial',
                'slots_json': json.dumps(slots_list)
            }

            if teacher_wxid:
                try:
                    send_text(content, teacher_wxid, producer='invigilation')
                    log_entry['sent_status'] = 'success'
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
                log_entry['error_message'] = '未配置接收人'
                skipped_count += 1

            logs.append(log_entry)

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
                "total": len(teacher_slots)
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
    """下载监考安排导入模板（横向布局，场次和时间分开）"""
    import pandas as pd

    # 横向布局：同一学科不同考场横向排列，场次和时间分开
    template_data = {
        '年级': ['高一', '高一', '高一', '高二', '高二', '高三'],
        '日期': ['2026-05-10', '2026-05-10', '2026-05-11', '2026-05-10', '2026-05-10', '2026-05-11'],
        '场次': ['第一场', '第二场', '第三场', '第一场', '第二场', '第一场'],
        '开始时间': ['08:00', '10:20', '14:00', '08:00', '10:20', '08:00'],
        '结束时间': ['10:00', '12:00', '16:00', '10:00', '12:00', '10:00'],
        '学科': ['语文', '数学', '英语', '语文', '数学', '物理'],
        '第1考场监考': ['张三', '王五', '周九', '赵六', '吴十', '孙八'],
        '第2考场监考': ['李四', '钱七', '郑十一', '冯十二', '陈十三', '褚十四'],
        '第3考场监考': ['卫十五', '蒋十六', '沈十七', '韩十八', '杨十九', '朱二十']
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

        # 检测布局格式：横向布局有"第X考场监考"列
        is_horizontal = any('考场监考' in col or '第' in col and '监考' in col for col in df.columns)

        # 获取教师列表用于匹配
        cursor.execute("SELECT teacher_id, name FROM teacher WHERE is_active = 1")
        teachers = {row['name']: row['teacher_id'] for row in cursor.fetchall()}

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

            room_cols = [col for col in df.columns if '考场监考' in col or ('第' in col and '监考' in col)]

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
                        # 解析考场名称：如 "第1考场监考" → "第1考场"，序号=1
                        import re
                        room_match = re.search(r'第(\d+)考场', room_col)
                        if room_match:
                            room_order = int(room_match.group(1))
                            room_name = f"第{room_order}考场"
                        else:
                            room_order = 0
                            room_name = room_col.replace('监考', '').strip()

                        teacher_name = row.get(room_col)
                        if pd.isna(teacher_name) or not teacher_name:
                            continue  # 空单元格跳过

                        teacher_name = str(teacher_name)
                        teacher_id = teachers.get(teacher_name)
                        if not teacher_id:
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
                            'teacher_id': teacher_id,
                            'teacher_name': teacher_name,
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

                    teacher_id = teachers.get(teacher_name)
                    if not teacher_id:
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
                        'teacher_id': teacher_id,
                        'teacher_name': teacher_name,
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
                (project_id, grade_id, grade_name, exam_date, start_time, end_time, subject, room_name, room_order, teacher_id, teacher_name, source)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                project_id, slot['grade_id'], slot['grade_name'], slot['exam_date'],
                slot['start_time'], slot['end_time'], slot['subject'], slot['room_name'],
                slot['room_order'], slot['teacher_id'], slot['teacher_name'], slot['source']
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