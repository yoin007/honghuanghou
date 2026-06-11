# -*- coding: utf-8 -*-
"""
待完善日常记录 API

学发部创建待完善记录（不含学生字段），通过微信通知班主任和任课教师。
班主任在页面或微信中补充学生后，自动写入日常表现记录表。
"""

import logging
import os
import json
import uuid
import re
from datetime import datetime, timezone, timedelta
from typing import Optional, List

GMT8 = timezone(timedelta(hours=8))

from fastapi import APIRouter, Depends, HTTPException, Query, Request, UploadFile, File, Form
from pydantic import BaseModel, Field

from .api_permission import require_configured_api_permission
from .base import (
    get_moral_db,
    check_moral_permission_for_roles,
    get_api_scoped_user_roles,
    get_current_semester,
    get_student_class_snapshot,
    log_operation,
    get_record_data_scope,
    append_record_scope_condition,
    record_in_scope,
    record_action_flags,
    target_student_in_scope,
    has_user_role,
    get_class_leader_ids,
    get_class_leader_names,
)
from .evaluation import calculate_evaluation
from .escalation import check_and_trigger_escalation
from models.datas_api.auth import User, is_admin_user
from utils.teacher_db import get_teacher_by_name

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/pending-records", tags=["待完善记录"])

API_PENDING_LIST = "/api/moral/pending-records"
API_PENDING_CREATE = "/api/moral/pending-records/create"
API_PENDING_COMPLETE = "/api/moral/pending-records/complete"
API_PENDING_DELETE = "/api/moral/pending-records/delete"
API_PENDING_UPLOAD = "/api/moral/pending-records/upload"
API_PENDING_COMPLETE_WX = "/api/moral/pending-records/complete-wx"

# 上传图片存储目录
def _get_pending_image_dir():
    """获取待完善记录图片存储目录，从 moral_config 读取 filegather_storage_dir，在其下创建 images 子目录"""
    from models.datas_api.moral.base import get_moral_db
    with get_moral_db() as db:
        row = db.query_one("SELECT config_value FROM moral_config WHERE config_key = 'filegather_storage_dir'")
        base_dir = row["config_value"] if row and row.get("config_value") else ""
    if not base_dir:
        # 回退到默认路径
        base_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), "storage", "filegather")
    upload_dir = os.path.join(base_dir, "images")
    os.makedirs(upload_dir, exist_ok=True)
    return upload_dir


def _ensure_pending_record_table(db):
    """确保 pending_daily_record 表存在"""
    db.execute("""
        CREATE TABLE IF NOT EXISTS pending_daily_record (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            class_id INTEGER NOT NULL,
            student_count INTEGER NOT NULL,
            event_id INTEGER NOT NULL,
            teacher_name TEXT DEFAULT '',
            record_date TEXT NOT NULL,
            images TEXT DEFAULT '',
            remark TEXT DEFAULT '',
            is_completed INTEGER DEFAULT 0,
            student_ids TEXT DEFAULT '',
            semester_id INTEGER,
            grade_id INTEGER,
            recorder TEXT DEFAULT '',
            created_at TEXT DEFAULT (datetime('now', 'localtime')),
            updated_at TEXT DEFAULT (datetime('now', 'localtime'))
        )
    """)
    db.execute("CREATE INDEX IF NOT EXISTS idx_pending_class ON pending_daily_record(class_id)")
    db.execute("CREATE INDEX IF NOT EXISTS idx_pending_completed ON pending_daily_record(is_completed)")


# =============================================================================
# 微信通知辅助
# =============================================================================

def _get_class_leader_wxids(db, class_id: int) -> List[str]:
    """获取班主任 wxid 列表"""
    wxids = []
    leader_ids = get_class_leader_ids(class_id, db)
    for leader_id in leader_ids:
        teacher = db.query_one("SELECT wxid FROM teacher WHERE teacher_id = ?", (leader_id,))
        if teacher and teacher.get("wxid"):
            wxids.append(teacher["wxid"])
    if not wxids:
        leader_names = get_class_leader_names(class_id, db)
        for name in leader_names:
            t = get_teacher_by_name(name)
            if t and t.get("wxid"):
                wxids.append(t["wxid"])
    # 回退: class 表 leader_wxid
    if not wxids:
        cls = db.query_one("SELECT leader_wxid FROM class WHERE class_id = ?", (class_id,))
        if cls and cls.get("leader_wxid"):
            wxids.append(cls["leader_wxid"])
    return [w for w in wxids if w]


def _get_teacher_wxid(teacher_name: str) -> Optional[str]:
    """根据教师姓名获取 wxid"""
    t = get_teacher_by_name(teacher_name)
    if t and t.get("wxid"):
        return t["wxid"]
    return None


def _send_pending_notifications(db, record_id: int, class_id: int, teacher_name: str,
                                 event_name: str, student_count: int, remark: str,
                                 record_date: str, image_paths: List[str]):
    """创建记录后发送微信通知给班主任和任课教师"""
    try:
        from sendqueue import send_text, send_image
        from config.config import Config
        config = Config()
        static_url = config.get_config("static_url", "wechat.yaml")
    except Exception:
        logger.warning("sendqueue 或 config 导入失败，跳过通知")
        return

    # ---- 班主任通知 ----
    leader_wxids = _get_class_leader_wxids(db, class_id)
    teacher_label = teacher_name or "无"
    

    # 第 1 条：概要
    remark_line = f"\n备注：{remark}" if remark else ""
    msg1 = (
        f"记录ID：{record_id}\n"
        f"时间：{record_date}\n"
        f"事件类型：{event_name}\n"
        f"任课教师：{teacher_label}{remark_line}\n"
        f"学生数：{student_count}\n"
        f"请将下面的学生名称补充完整后，发给我"
    )

    # 第 2 条：待完善学生列表
    student_lines = "\n".join(f"学生{i}：" for i in range(1, student_count + 1))
    msg2 = (
        f"待完善记录：{record_id}\n"
        f"任课教师：{teacher_label}\n"
        f"时间：{record_date}\n"
        f"事件类型：{event_name}{remark_line}\n"
        f"{student_lines}"
    )

    for wxid in leader_wxids:
        try:
            send_text(msg1, wxid, producer="moral_pending")
            send_text(msg2, wxid, producer="moral_pending")
        except Exception as e:
            logger.error(f"发送班主任通知失败 {wxid}: {e}")

    # ---- 任课教师通知 ----
    if teacher_name:
        teacher_wxid = _get_teacher_wxid(teacher_name)
        if teacher_wxid and teacher_wxid not in leader_wxids:
            msg_teacher = (
                f"待完善日常记录：\n"
                f"{event_name}-{teacher_name}-{remark or ''}"
            )
            try:
                send_text(msg_teacher, teacher_wxid, producer="moral_pending")
            except Exception as e:
                logger.error(f"发送任课教师通知失败 {teacher_wxid}: {e}")

    # ---- 发送图片 ----
    # 图片路径为 /pending-uploads/xxx.jpg，用 static_url 的基址拼接
    base_url = static_url.rstrip('/static/')
    if base_url.endswith('/'):
        base_url = base_url.rstrip('/')
    for img_path in image_paths:
        if img_path.startswith("http://") or img_path.startswith("https://"):
            img_url = img_path
        elif img_path.startswith("blob:"):
            logger.warning(f"跳过 blob URL: {img_path}")
            continue
        elif img_path.startswith("/"):
            img_url = f"{base_url}{img_path}"
        else:
            img_url = f"{base_url}/{img_path}"
        all_recipients = list(set(leader_wxids + ([_get_teacher_wxid(teacher_name)] if teacher_name else [])))
        for wxid in all_recipients:
            if wxid:
                try:
                    send_image(img_url, wxid, producer="moral_pending")
                except Exception as e:
                    logger.error(f"发送图片失败 {wxid}: {e}")


# =============================================================================
# API 路由
# =============================================================================

@router.post("/upload", summary="上传待完善记录图片")
async def upload_pending_image(
    files: List[UploadFile] = File(...),
    user: User = Depends(require_configured_api_permission(API_PENDING_UPLOAD, "POST", allow_missing=True))
):
    """上传图片，返回相对路径列表"""
    saved = []
    for f in files:
        ext = os.path.splitext(f.filename or ".jpg")[1]
        if ext.lower() not in (".jpg", ".jpeg", ".png", ".gif", ".webp"):
            raise HTTPException(400, f"不支持的图片格式: {ext}")
        content = await f.read()
        if len(content) > 10 * 1024 * 1024:
            raise HTTPException(400, "图片大小不能超过 10MB")
        filename = f"{uuid.uuid4().hex}{ext}"
        filepath = os.path.join(_get_pending_image_dir(), filename)
        with open(filepath, "wb") as fp:
            fp.write(content)
        saved.append(f"/pending-uploads/{filename}")
    return {"success": True, "data": saved}


@router.get("/teachers", summary="获取教师列表（模糊搜索）")
async def search_teachers(
    keyword: Optional[str] = Query(None, description="搜索关键字"),
    user: User = Depends(require_configured_api_permission("/api/moral/pending-records/teachers", "GET", allow_missing=True))
):
    """获取教师列表用于任课教师选择"""
    from utils.teacher_db import get_all_teachers
    teachers = get_all_teachers()
    if keyword:
        teachers = [t for t in teachers if t.get("name", "").startswith(keyword)]
    return {"success": True, "data": [{"name": t["name"], "subject": t.get("subject", "")} for t in teachers]}


@router.get("", summary="获取待完善记录列表")
async def get_pending_records(
    class_id: Optional[int] = Query(None, description="班级ID"),
    is_completed: Optional[int] = Query(None, description="是否已完善: 0=否, 1=是"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    user: User = Depends(require_configured_api_permission(API_PENDING_LIST, "GET", allow_missing=True))
):
    """
    获取待完善记录列表

    权限：
    - 学发/教务/管理员：可查看全部
    - 班主任：只可查看自己班级的记录
    """
    with get_moral_db() as db:
        _ensure_pending_record_table(db)

        conditions = ["1=1"]
        params = []

        if class_id is not None:
            conditions.append("p.class_id = ?")
            params.append(class_id)

        if is_completed is not None:
            conditions.append("p.is_completed = ?")
            params.append(is_completed)

        # 权限过滤
        if not is_admin_user(user) and not has_user_role(user, "xuefa") and not has_user_role(user, "jiaowu"):
            # 非学发/教务/管理员：根据身份查看班级记录
            from .base import get_teacher_class_ids, get_teacher_grade_ids
            my_class_ids = get_teacher_class_ids(user, db)
            if has_user_role(user, "g_leader"):
                # 年级主任还可以看年级所有班级
                my_grade_ids = get_teacher_grade_ids(user, db)
                if my_grade_ids:
                    grade_ids_str = ",".join(map(str, my_grade_ids))
                    rows = db.query_all(
                        f"SELECT class_id FROM class WHERE grade_id IN ({grade_ids_str}) AND is_active = 1"
                    )
                    grade_class_ids = [r["class_id"] for r in rows]
                    my_class_ids = list(set(my_class_ids) | set(grade_class_ids))
            if my_class_ids:
                placeholders = ",".join(["?"] * len(my_class_ids))
                conditions.append(f"p.class_id IN ({placeholders})")
                params.extend(my_class_ids)
            else:
                conditions.append("1=0")

        where_clause = " AND ".join(conditions)

        count_query = f"""
            SELECT COUNT(*) as total FROM pending_daily_record p WHERE {where_clause}
        """
        total = db.query_value(count_query, tuple(params))

        offset = (page - 1) * page_size
        data_query = f"""
            SELECT p.*, c.class_name, g.grade_name, de.event_name, de.event_type, de.score
            FROM pending_daily_record p
            LEFT JOIN class c ON p.class_id = c.class_id
            LEFT JOIN grade g ON p.grade_id = g.grade_id
            LEFT JOIN daily_event_type de ON p.event_id = de.event_id
            WHERE {where_clause}
            ORDER BY p.is_completed ASC, p.created_at DESC
            LIMIT ? OFFSET ?
        """
        params.extend([page_size, offset])
        records = db.query_all(data_query, tuple(params))

        # 补充操作权限
        can_delete = is_admin_user(user) or (hasattr(user, "role") and user.role == "xuefa")

        for r in records:
            r["can_delete"] = can_delete
            r["can_complete"] = True

        return {
            "success": True,
            "data": {
                "items": records,
                "total": total,
                "page": page,
                "page_size": page_size
            }
        }


class PendingRecordCreate(BaseModel):
    """创建待完善记录"""
    class_id: int = Field(..., description="班级ID")
    student_count: int = Field(..., description="学生数", ge=1)
    event_id: int = Field(..., description="事件类型ID")
    teacher_name: Optional[str] = Field("", description="任课教师姓名")
    record_date: Optional[str] = Field(None, description="记录时间")
    images: Optional[str] = Field("", description="图片路径，JSON 数组字符串")
    remark: Optional[str] = Field("", description="备注")


@router.post("", summary="创建待完善记录")
async def create_pending_record(
    record: PendingRecordCreate,
    request: Request,
    user: User = Depends(require_configured_api_permission(API_PENDING_CREATE, "POST", allow_missing=True))
):
    """
    创建待完善记录（仅限学发身份）

    创建后自动通知班主任和任课教师
    """
    # 仅限学发
    if not (is_admin_user(user) or (hasattr(user, "role") and user.role == "xuefa")):
        raise HTTPException(403, "仅限学发身份添加待完善记录")

    # 图片必填验证
    try:
        images_list = json.loads(record.images) if record.images else []
        if not images_list or len(images_list) == 0:
            raise HTTPException(400, "请上传至少一张图片")
    except json.JSONDecodeError:
        raise HTTPException(400, "图片数据格式错误")

    with get_moral_db() as db:
        _ensure_pending_record_table(db)

        current_time = datetime.now(GMT8).replace(tzinfo=None)
        record_date = record.record_date or current_time.strftime("%Y-%m-%d %H:%M")

        # 获取当前学期
        current_semester = get_current_semester(db)
        if not current_semester:
            raise HTTPException(400, "当前学期未配置")
        semester_id = current_semester["semester_id"]

        # 获取班级信息
        class_info = db.query_one("SELECT class_id, grade_id, class_name FROM class WHERE class_id = ?", (record.class_id,))
        if not class_info:
            raise HTTPException(404, "班级不存在")
        grade_id = class_info["grade_id"]

        # 获取事件类型
        event = db.query_one("SELECT * FROM daily_event_type WHERE event_id = ? AND is_active = 1", (record.event_id,))
        if not event:
            raise HTTPException(404, "事件类型不存在或已禁用")

        # 插入待完善记录
        db.execute(
            """INSERT INTO pending_daily_record
            (class_id, student_count, event_id, teacher_name, record_date, images, remark,
             is_completed, semester_id, grade_id, recorder)
            VALUES (?, ?, ?, ?, ?, ?, ?, 0, ?, ?, ?)""",
            (record.class_id, record.student_count, record.event_id, record.teacher_name or "",
             record_date, record.images or "", record.remark or "",
             semester_id, grade_id, user.username)
        )
        record_id = db.lastrowid()

        # 操作日志
        log_operation(
            db, user.username, user.role, "INSERT", "pending_daily_record",
            record_id, semester_id, new_data={
                "class_id": record.class_id,
                "student_count": record.student_count,
                "event_id": record.event_id,
                "teacher_name": record.teacher_name,
            },
            ip_address=request.client.host if request.client else None
        )

        # 发送通知
        image_paths = json.loads(record.images) if record.images else []
        _send_pending_notifications(
            db, record_id, record.class_id, record.teacher_name or "",
            event["event_name"], record.student_count, record.remark or "",
            record_date, image_paths
        )

        return {"success": True, "data": {"id": record_id}}


@router.post("/{record_id}/complete", summary="完善待完善记录（前端页面）")
async def complete_pending_record(
    record_id: int,
    request: Request,
    user: User = Depends(require_configured_api_permission(API_PENDING_COMPLETE, "POST", allow_missing=True))
):
    """
    完善待完善记录

    请求体: {"student_ids": ["学号1", "学号2", ...]}
    """
    body = await request.json()
    student_ids = body.get("student_ids", [])
    if not student_ids:
        raise HTTPException(400, "请选择学生")

    with get_moral_db() as db:
        _ensure_pending_record_table(db)

        # 获取待完善记录
        pending = db.query_one("SELECT * FROM pending_daily_record WHERE id = ?", (record_id,))
        if not pending:
            raise HTTPException(404, "记录不存在")
        if pending["is_completed"]:
            raise HTTPException(400, "该记录已完善")

        # 验证学生数
        if len(student_ids) != pending["student_count"]:
            raise HTTPException(400, f"学生数不匹配，需要 {pending['student_count']} 名学生，已选 {len(student_ids)} 名")

        # 验证学生是否在班级中
        class_id = pending["class_id"]
        for sid in student_ids:
            student_info = get_student_class_snapshot(db, sid)
            if not student_info:
                raise HTTPException(400, f"学生 {sid} 不存在")
            if student_info["class_id"] != class_id:
                raise HTTPException(400, f"学生 {sid} 不在该班级中")

        # 获取事件类型
        event = db.query_one("SELECT * FROM daily_event_type WHERE event_id = ?", (pending["event_id"],))
        if not event:
            raise HTTPException(404, "事件类型不存在")

        semester_id = pending["semester_id"]
        grade_id = pending["grade_id"]
        record_date = pending["record_date"]

        # 合并备注：任课教师 + 原备注
        combined_remark = ""
        if pending["teacher_name"]:
            combined_remark += f"任课教师：{pending['teacher_name']}"
        if pending["remark"]:
            if combined_remark:
                combined_remark += "；"
            combined_remark += pending["remark"]

        # 为每个学生创建日常表现记录
        current_time = datetime.now(GMT8).replace(tzinfo=None)
        created_records = []
        for sid in student_ids:
            student_info = get_student_class_snapshot(db, sid)
            if not student_info:
                continue
            db.execute(
                """INSERT INTO student_daily_record
                (student_id, event_id, semester_id, record_date, class_id, grade_id, score, remark, recorder)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (sid, pending["event_id"], semester_id, record_date,
                 class_id, grade_id, event["score"], combined_remark,
                 pending.get("recorder") or user.username)
            )
            new_record_id = db.lastrowid()
            created_records.append(new_record_id)

            # 检查累进处罚
            if event["event_type"] == 2:
                try:
                    rd = datetime.strptime(record_date, "%Y-%m-%d %H:%M")
                except:
                    rd = current_time
                check_and_trigger_escalation(
                    db=db, student_id=sid, event_id=pending["event_id"],
                    record_id=new_record_id, record_date=rd, semester_id=semester_id
                )

            # 重新计算评价
            calculate_evaluation(db, sid, semester_id, class_id, grade_id)

        # 更新待完善记录
        db.execute(
            """UPDATE pending_daily_record SET is_completed = 1, student_ids = ?, updated_at = datetime('now', 'localtime')
            WHERE id = ?""",
            (json.dumps(student_ids, ensure_ascii=False), record_id)
        )

        # 操作日志
        log_operation(
            db, user.username, user.role, "COMPLETE", "pending_daily_record",
            record_id, semester_id, new_data={"student_ids": student_ids},
            ip_address=request.client.host if request.client else None
        )

        return {"success": True, "message": f"已完善记录，创建了 {len(created_records)} 条日常表现记录"}


class PendingRecordCompleteWx(BaseModel):
    """微信端完善记录"""
    student_names: List[str] = Field(..., description="学生姓名列表")


@router.post("/{record_id}/complete-wx", summary="微信端完善待完善记录")
async def complete_pending_record_wx(
    record_id: int,
    body: PendingRecordCompleteWx,
    request: Request,
    user: User = Depends(require_configured_api_permission(API_PENDING_COMPLETE_WX, "POST", allow_missing=True))
):
    """
    微信端完善待完善记录

    通过正则匹配学生姓名，验证学生在班级中存在后完善记录。
    请求格式：待完善记录：{记录ID}\n学生1：张三\n学生2：李四\n...
    """
    with get_moral_db() as db:
        _ensure_pending_record_table(db)

        pending = db.query_one("SELECT * FROM pending_daily_record WHERE id = ?", (record_id,))
        if not pending:
            raise HTTPException(404, "记录不存在")
        if pending["is_completed"]:
            raise HTTPException(400, "该记录已完善")

        class_id = pending["class_id"]

        # 查找班级学生
        class_students = db.query_all(
            "SELECT student_id, name FROM student WHERE class_id = ? AND status = '在校'",
            (class_id,)
        )
        name_to_id = {s["name"]: s["student_id"] for s in class_students}

        # 匹配学生姓名
        student_ids = []
        not_found = []
        for name in body.student_names:
            name = name.strip()
            if name in name_to_id:
                student_ids.append(name_to_id[name])
            else:
                # 模糊匹配
                matched = [nid for n, nid in name_to_id.items() if name in n]
                if len(matched) == 1:
                    student_ids.append(matched[0])
                else:
                    not_found.append(name)

        if not_found:
            raise HTTPException(400, f"以下学生在班级中未找到: {', '.join(not_found)}")

        if len(student_ids) != pending["student_count"]:
            raise HTTPException(400, f"学生数不匹配，需要 {pending['student_count']} 名学生，已匹配 {len(student_ids)} 名")

        # 以下与前端完善逻辑相同
        event = db.query_one("SELECT * FROM daily_event_type WHERE event_id = ?", (pending["event_id"],))
        if not event:
            raise HTTPException(404, "事件类型不存在")

        semester_id = pending["semester_id"]
        grade_id = pending["grade_id"]
        record_date = pending["record_date"]

        combined_remark = ""
        if pending["teacher_name"]:
            combined_remark += f"任课教师：{pending['teacher_name']}"
        if pending["remark"]:
            if combined_remark:
                combined_remark += "；"
            combined_remark += pending["remark"]

        current_time = datetime.now(GMT8).replace(tzinfo=None)
        created_records = []
        for sid in student_ids:
            student_info = get_student_class_snapshot(db, sid)
            if not student_info:
                continue
            db.execute(
                """INSERT INTO student_daily_record
                (student_id, event_id, semester_id, record_date, class_id, grade_id, score, remark, recorder)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (sid, pending["event_id"], semester_id, record_date,
                 class_id, grade_id, event["score"], combined_remark,
                 pending.get("recorder") or user.username)
            )
            new_record_id = db.lastrowid()
            created_records.append(new_record_id)

            if event["event_type"] == 2:
                try:
                    rd = datetime.strptime(record_date, "%Y-%m-%d %H:%M")
                except:
                    rd = current_time
                check_and_trigger_escalation(
                    db=db, student_id=sid, event_id=pending["event_id"],
                    record_id=new_record_id, record_date=rd, semester_id=semester_id
                )
            calculate_evaluation(db, sid, semester_id, class_id, grade_id)

        db.execute(
            """UPDATE pending_daily_record SET is_completed = 1, student_ids = ?, updated_at = datetime('now', 'localtime')
            WHERE id = ?""",
            (json.dumps(student_ids, ensure_ascii=False), record_id)
        )

        log_operation(
            db, user.username, user.role, "COMPLETE_WX", "pending_daily_record",
            record_id, semester_id, new_data={"student_ids": student_ids},
            ip_address=request.client.host if request.client else None
        )

        return {"success": True, "message": f"已完善记录，创建了 {len(created_records)} 条日常表现记录"}


@router.delete("/{record_id}", summary="删除待完善记录")
async def delete_pending_record(
    record_id: int,
    request: Request,
    user: User = Depends(require_configured_api_permission(API_PENDING_DELETE, "DELETE", allow_missing=True))
):
    """删除待完善记录（仅学发和管理员）"""
    if not (is_admin_user(user) or (hasattr(user, "role") and user.role == "xuefa")):
        raise HTTPException(403, "仅限学发和管理员删除")

    with get_moral_db() as db:
        _ensure_pending_record_table(db)
        pending = db.query_one("SELECT * FROM pending_daily_record WHERE id = ?", (record_id,))
        if not pending:
            raise HTTPException(404, "记录不存在")

        db.execute("DELETE FROM pending_daily_record WHERE id = ?", (record_id,))

        # 删除关联图片文件
        if pending.get("images"):
            try:
                image_paths = json.loads(pending["images"])
                for img_path in image_paths:
                    # 相对路径 /pending-uploads/xxx.jpg
                    filename = img_path.split("/")[-1]
                    full_path = os.path.join(_get_pending_image_dir(), filename)
                    if os.path.exists(full_path):
                        os.remove(full_path)
            except Exception as e:
                logger.error(f"删除图片文件失败: {e}")

        log_operation(
            db, user.username, user.role, "DELETE", "pending_daily_record",
            record_id, None,
            ip_address=request.client.host if request.client else None
        )

        return {"success": True, "message": "记录已删除"}
