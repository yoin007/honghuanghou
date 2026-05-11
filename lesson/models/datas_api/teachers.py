# -*- coding: utf-8 -*-
"""教师管理模块 - 教师CRUD、密码修改"""

import logging
import os
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from models.datas_api.auth import (
    User,
    get_current_user,
    get_users_dict,
    get_user,
    hash_password,
    verify_password_compat,
    is_admin_user
)
from utils.teacher_db import (
    create_teacher_record,
    update_teacher_record,
    delete_teacher_record,
    get_all_teacher_records,
)
from utils.sqlite_moral_db import MoralDatabase as SQLiteMoralDatabase

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/teachers", tags=["教师管理"])


def calculate_level_from_role(role: str) -> int:
    """
    根据角色计算等级：
    - teacher: 10
    - cleader: 20
    - g_leader: 30
    - xuefa/jiaowu: 40
    - admin: 50
    """
    role_levels = {
        "teacher": 10,
        "cleader": 20,
        "g_leader": 30,
        "xuefa": 40,
        "jiaowu": 40,
        "admin": 50,
    }
    # 多角色情况，取最高等级
    if not role:
        return 10
    roles = role.split("/")
    max_level = 10
    for r in roles:
        level = role_levels.get(r.strip(), 10)
        if level > max_level:
            max_level = level
    return max_level


# ==================== Request Models ====================

class TeacherCreate(BaseModel):
    username: str
    subject: str
    course: str
    notice: int = 1  # 通知开关（原 active）
    password: str
    role: str = "teacher"
    level: Optional[int] = None  # 可手动覆盖，否则按 role 自动计算


class TeacherUpdate(BaseModel):
    username: Optional[str] = None
    wxid: Optional[str] = None
    subject: Optional[str] = None
    course: Optional[str] = None
    notice: Optional[int] = None  # 通知开关
    active: Optional[int] = None  # 登录权限
    role: Optional[str] = None
    level: Optional[int] = None  # 可手动覆盖，否则按 role 自动计算
    score: Optional[int] = None
    balance: Optional[int] = None
    model: Optional[str] = None
    ai_flag: Optional[int] = None
    birthday: Optional[str] = None
    note: Optional[str] = None
    identity_type: Optional[str] = None


class PasswordChangeRequest(BaseModel):
    old_password: str
    new_password: str


class TeachingClassItem(BaseModel):
    class_id: int
    subject: Optional[str] = None


class TeachingClassUpdate(BaseModel):
    classes: List[TeachingClassItem] = []


def _ensure_teaching_class_table(db):
    db.execute(
        """CREATE TABLE IF NOT EXISTS teacher_teaching_class (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            teacher_id TEXT NOT NULL,
            teacher_name TEXT,
            class_id INTEGER NOT NULL,
            subject TEXT,
            is_active INTEGER DEFAULT 1,
            created_at TEXT DEFAULT (datetime('now', 'localtime')),
            updated_at TEXT DEFAULT (datetime('now', 'localtime')),
            UNIQUE(teacher_id, class_id, subject)
        )"""
    )
    db.execute("CREATE INDEX IF NOT EXISTS idx_teacher_teaching_teacher ON teacher_teaching_class(teacher_id)")
    db.execute("CREATE INDEX IF NOT EXISTS idx_teacher_teaching_class ON teacher_teaching_class(class_id)")


# ==================== Teacher Routes ====================

@router.get("", summary="获取教师列表")
async def get_teachers(
    include_all: int = Query(0, description="管理员维护用：1=返回 teacher 表全部身份记录"),
    current_user: User = Depends(get_current_user),
):
    """获取教师列表。默认只返回可登录系统的正式教师。"""
    if include_all:
        if not is_admin_user(current_user):
            raise HTTPException(status_code=403, detail="只有管理员可以查看全部身份记录")
        users_data = {
            row["name"]: {
                "username": row["name"],
                "stored_password": row.get("pwd", ""),
                **row,
            }
            for row in get_all_teacher_records()
        }
    else:
        users_data = get_users_dict()
    teachers_list = []

    for username, user_info in users_data.items():
        teachers_list.append({
            "teacher_id": str(user_info.get("teacher_id", "")),
            "username": str(username),
            "wxid": str(user_info.get("wxid", "")) if user_info.get("wxid") else "",
            "subject": str(user_info.get("subject", "")) if user_info.get("subject") else "",
            "course": str(user_info.get("course", "")) if user_info.get("course") else "",
            "role": str(user_info.get("role", "teacher")),
            "level": int(user_info.get("level", 0)) if user_info.get("level") is not None else 0,
            "notice": int(user_info.get("notice", 1)) if user_info.get("notice") is not None else 1,
            "active": int(user_info.get("active", 1)) if user_info.get("active") is not None else 1,
            "is_password_changed": int(user_info.get("is_password_changed", 0)) if user_info.get("is_password_changed") is not None else 0,
            "score": int(user_info.get("score", 50)) if user_info.get("score") is not None else 50,
            "balance": int(user_info.get("balance", 0)) if user_info.get("balance") is not None else 0,
            "model": str(user_info.get("model", "basic")) if user_info.get("model") else "",
            "ai_flag": int(user_info.get("ai_flag", 0)) if user_info.get("ai_flag") is not None else 0,
            "birthday": str(user_info.get("birthday", "")) if user_info.get("birthday") else "",
            "note": str(user_info.get("note", "")) if user_info.get("note") else "",
            "identity_type": str(user_info.get("identity_type", "teacher") or "teacher"),
            "created_at": str(user_info.get("created_at", "")) if user_info.get("created_at") else "",
            "updated_at": str(user_info.get("updated_at", "")) if user_info.get("updated_at") else "",
        })

    return {"teachers": teachers_list, "total": len(teachers_list)}


@router.post("", summary="创建教师")
async def create_teacher(
    teacher: TeacherCreate,
    current_user: User = Depends(get_current_user)
):
    """创建新教师（需要管理员权限）"""
    if not is_admin_user(current_user):
        raise HTTPException(status_code=403, detail="只有管理员可以创建教师")

    try:
        hashed_password = hash_password(str(teacher.password))
        # 如果前端传了 level，使用传来的值；否则按角色自动计算
        final_level = teacher.level if teacher.level is not None else calculate_level_from_role(teacher.role)
        create_teacher_record(
            name=teacher.username,
            subject=teacher.subject,
            course=teacher.course,
            notice=teacher.notice,
            password_hash=str(hashed_password),
            role=teacher.role,
            level=final_level,
            active=1,
            is_password_changed=1,
        )

        logger.info(f"Admin {current_user.username} created teacher {teacher.username} with role={teacher.role}, level={final_level}")
        return {"message": f"教师 {teacher.username} 创建成功", "success": True, "level": final_level}

    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to create teacher: {e}")
        raise HTTPException(status_code=500, detail=f"创建教师失败: {str(e)}")


@router.put("/{username}", summary="更新教师")
async def update_teacher(
    username: str,
    teacher: TeacherUpdate,
    current_user: User = Depends(get_current_user)
):
    """更新教师信息"""
    if not is_admin_user(current_user):
        raise HTTPException(status_code=403, detail="只有管理员可以更新教师")

    try:
        # 计算最终 level：前端传值则使用，否则按 role 自动计算
        final_level = None
        if teacher.level is not None:
            final_level = teacher.level
        elif teacher.role:
            final_level = calculate_level_from_role(teacher.role)
        update_teacher_record(
            username,
            name=teacher.username,
            wxid=teacher.wxid,
            subject=teacher.subject,
            course=teacher.course,
            notice=teacher.notice,
            active=teacher.active,
            role=teacher.role,
            level=final_level,
            score=teacher.score,
            balance=teacher.balance,
            model=teacher.model,
            ai_flag=teacher.ai_flag,
            birthday=teacher.birthday,
            note=teacher.note,
            identity_type=teacher.identity_type,
            all_records=True,
        )

        logger.info(f"Admin {current_user.username} updated teacher record {username}, role={teacher.role}, level={final_level}")
        return {"message": f"记录 {username} 更新成功", "success": True, "level": final_level}

    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to update teacher: {e}")
        raise HTTPException(status_code=500, detail=f"更新教师失败: {str(e)}")


@router.delete("/{username}", summary="删除教师")
async def delete_teacher(
    username: str,
    current_user: User = Depends(get_current_user)
):
    """删除教师"""
    if not is_admin_user(current_user):
        raise HTTPException(status_code=403, detail="只有管理员可以删除教师")

    try:
        delete_teacher_record(username, all_records=True)

        logger.info(f"Admin {current_user.username} deleted teacher record {username}")
        return {"message": f"记录 {username} 已删除", "success": True}

    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to delete teacher: {e}")
        raise HTTPException(status_code=500, detail=f"删除教师失败: {str(e)}")


@router.get("/{teacher_id}/teaching-classes", summary="获取教师任教班级")
async def get_teacher_teaching_classes(
    teacher_id: str,
    current_user: User = Depends(get_current_user)
):
    """获取教师任教班级关系（管理员维护权限）。"""
    if not is_admin_user(current_user):
        raise HTTPException(status_code=403, detail="只有管理员可以查看任教班级关系")

    with SQLiteMoralDatabase() as db:
        _ensure_teaching_class_table(db)
        teacher = db.query_one(
            "SELECT teacher_id, name, subject FROM teacher WHERE teacher_id = %s OR name = %s",
            (teacher_id, teacher_id),
        )
        real_teacher_id = teacher.get("teacher_id") if teacher else teacher_id
        rows = db.query_all(
            """SELECT ttc.id, ttc.teacher_id, ttc.teacher_name, ttc.class_id, ttc.subject,
                      c.class_name, g.grade_name
               FROM teacher_teaching_class ttc
               LEFT JOIN class c ON ttc.class_id = c.class_id
               LEFT JOIN grade g ON c.grade_id = g.grade_id
               WHERE ttc.teacher_id = %s AND ttc.is_active = 1
               ORDER BY g.enrollment_year DESC, c.class_number""",
            (real_teacher_id,),
        )
        return {
            "success": True,
            "data": {
                "teacher": teacher or {"teacher_id": teacher_id, "name": teacher_id},
                "items": rows,
            }
        }


@router.put("/{teacher_id}/teaching-classes", summary="更新教师任教班级")
async def update_teacher_teaching_classes(
    teacher_id: str,
    payload: TeachingClassUpdate,
    current_user: User = Depends(get_current_user)
):
    """全量更新教师任教班级关系。"""
    if not is_admin_user(current_user):
        raise HTTPException(status_code=403, detail="只有管理员可以维护任教班级关系")

    with SQLiteMoralDatabase() as db:
        _ensure_teaching_class_table(db)
        teacher = db.query_one(
            "SELECT teacher_id, name, subject FROM teacher WHERE teacher_id = %s OR name = %s",
            (teacher_id, teacher_id),
        )
        teacher_name = teacher.get("name") if teacher else teacher_id
        real_teacher_id = teacher.get("teacher_id") if teacher else teacher_id

        class_ids = [item.class_id for item in payload.classes]
        if class_ids:
            placeholders = ", ".join(["%s"] * len(class_ids))
            existing_count = db.query_value(
                f"SELECT COUNT(*) FROM class WHERE class_id IN ({placeholders})",
                tuple(class_ids),
            )
            if int(existing_count or 0) != len(set(class_ids)):
                raise HTTPException(status_code=400, detail="存在无效班级")

        db.execute("DELETE FROM teacher_teaching_class WHERE teacher_id = %s", (real_teacher_id,))
        seen = set()
        for item in payload.classes:
            subject = item.subject or (teacher.get("subject") if teacher else None)
            key = (item.class_id, subject or "")
            if key in seen:
                continue
            seen.add(key)
            db.execute(
                """INSERT INTO teacher_teaching_class
                   (teacher_id, teacher_name, class_id, subject, is_active)
                   VALUES (%s, %s, %s, %s, 1)""",
                (real_teacher_id, teacher_name, item.class_id, subject),
            )

        return {
            "success": True,
            "message": "任教班级已更新",
            "data": {"teacher_id": real_teacher_id, "count": len(seen)}
        }


@router.post("/init-teaching-classes", summary="初始化所有教师任教班级")
async def init_all_teaching_classes(
    current_user: User = Depends(get_current_user)
):
    """根据最近一个月的课表数据，批量更新所有教师的任教班级。

    管理员权限：基于 lesson.yaml 中课表数据，提取每个教师涉及的班级作为任教班级。
    已有任教班级记录的教师会被覆盖更新。
    """
    if not is_admin_user(current_user):
        raise HTTPException(status_code=403, detail="只有管理员可以初始化任教班级")

    from datetime import date, timedelta
    from collections import defaultdict
    from models.lesson.lesson import Lesson
    from models.datas_api.dashboard import _schedule_files_for_range, _format_week_schedule_file
    import pandas as pd
    from utils.db_config import MORAL_DB

    # 计算最近一个月的时间范围
    today = date.today()
    start_date = today - timedelta(days=30)
    end_date = today

    lesson = Lesson()
    class_template = lesson.get_cache_data("class_template")
    class_names = class_template["class_name"].tolist() if class_template is not None and not class_template.empty else []

    # 从 moral 数据库获取 class_name -> class_id、teacher_name -> teacher_id 映射
    with SQLiteMoralDatabase() as db:
        _ensure_teaching_class_table(db)
        class_rows = db.query_all("SELECT class_id, class_name FROM class WHERE is_active = 1")
        teacher_rows = db.query_all(
            """SELECT teacher_id, name, subject
               FROM teacher
               WHERE COALESCE(identity_type, 'teacher') = 'teacher'
                 AND COALESCE(is_active, 1) = 1"""
        )
    class_name_to_id = {str(r["class_name"]).strip(): r["class_id"] for r in class_rows if r.get("class_name")}
    if not class_names:
        class_names = list(class_name_to_id.keys())
    teacher_id_by_name = {
        str(r["name"]).strip(): str(r["teacher_id"]).strip()
        for r in teacher_rows
        if r.get("name") and r.get("teacher_id")
    }
    teacher_subject_from_db = {
        str(r["name"]).strip(): str(r.get("subject") or "").strip()
        for r in teacher_rows
        if r.get("name")
    }

    teacher_template = lesson.get_cache_data("teacher_template")
    valid_teachers = {}
    teacher_subject_map = {}
    if teacher_template is not None and not teacher_template.empty and "name" in teacher_template.columns:
        for _, row in teacher_template.iterrows():
            name = str(row.get("name", "")).strip()
            if name and name in teacher_id_by_name:
                valid_teachers[name] = teacher_id_by_name[name]
                teacher_subject_map[name] = str(row.get("subject", "")).strip() or teacher_subject_from_db.get(name, "")

    for name, teacher_id in teacher_id_by_name.items():
        valid_teachers.setdefault(name, teacher_id)
        teacher_subject_map.setdefault(name, teacher_subject_from_db.get(name, ""))

    # 使用 dashboard.py 中的辅助函数遍历课表文件
    teacher_classes = defaultdict(set)  # teacher_name -> set of (class_id, subject)
    class_names_list = [cn for cn in class_names if cn in class_name_to_id]

    schedule_files = _schedule_files_for_range(lesson, start_date, end_date)
    checked_schedule_dirs = []
    for month_key in sorted({d.strftime("%Y%m") for d in [start_date, end_date]}):
        checked_schedule_dirs.append(os.path.join(lesson.lesson_dir or "", month_key, "class_schedule"))
    parsed_rows = 0
    skipped_unknown_teachers = set()

    for item in schedule_files:
        df = _format_week_schedule_file(lesson, item["path"], item["monday"])
        if df.empty:
            continue

        weekday_column = "weekday" if "weekday" in df.columns else "week" if "week" in df.columns else ""
        if not weekday_column:
            continue

        teacher_df = lesson.schedule_service.replace_subject_teacher(df, teacher_flag=True)

        for idx, row in teacher_df.iterrows():
            try:
                weekday = int(row.get(weekday_column))
            except Exception:
                continue
            actual_date = item["monday"] + timedelta(days=weekday - 1)
            if actual_date < start_date or actual_date > end_date:
                continue

            for class_name in class_names_list:
                teacher_value = row.get(class_name)
                if teacher_value is None:
                    continue
                if isinstance(teacher_value, float) and pd.isna(teacher_value):
                    continue
                current_teacher = str(teacher_value).strip()
                if not current_teacher or current_teacher == "-":
                    continue
                if current_teacher not in valid_teachers:
                    skipped_unknown_teachers.add(current_teacher)
                    continue

                class_id = class_name_to_id.get(class_name)
                if not class_id:
                    continue

                # 获取学科
                subject_value = df.at[idx, class_name] if class_name in df.columns and idx in df.index else ""
                subject = str(subject_value or "").strip() or teacher_subject_map.get(current_teacher, "")
                teacher_classes[current_teacher].add((class_id, subject))
                parsed_rows += 1

    # 写入数据库：覆盖已有记录
    with SQLiteMoralDatabase() as db:
        _ensure_teaching_class_table(db)

        initialized_count = 0
        details = []

        for teacher_name, class_subject_pairs in teacher_classes.items():
            teacher_id = valid_teachers.get(teacher_name)
            if not teacher_id:
                continue

            # 先删除该教师的现有任教班级记录（覆盖），兼容清理旧版本用教师姓名写入 teacher_id 的记录。
            db.execute("DELETE FROM teacher_teaching_class WHERE teacher_id = %s", (teacher_id,))
            db.execute("DELETE FROM teacher_teaching_class WHERE teacher_id = %s OR teacher_name = %s", (teacher_name, teacher_name))

            # 插入新的任教班级记录
            for class_id, subject in class_subject_pairs:
                try:
                    db.execute(
                        """INSERT INTO teacher_teaching_class
                           (teacher_id, teacher_name, class_id, subject, is_active)
                           VALUES (%s, %s, %s, %s, 1)""",
                        (teacher_id, teacher_name, class_id, subject),
                    )
                except Exception as e:
                    logger.warning(f"Failed to insert teaching class for {teacher_name}: {e}")

            initialized_count += 1
            details.append({
                "teacher_name": teacher_name,
                "status": "updated",
                "class_count": len(class_subject_pairs)
            })

    return {
        "success": True,
        "message": f"初始化完成：{initialized_count} 位教师任教班级已更新",
        "data": {
            "diagnostic_version": 2,
            "updated": initialized_count,
            "total_teachers_with_lessons": len(teacher_classes),
            "date_range": f"{start_date.isoformat()} 至 {end_date.isoformat()}",
            "lesson_dir": lesson.lesson_dir,
            "moral_db_path": MORAL_DB,
            "cwd": os.getcwd(),
            "source_files": [item["file_name"] for item in schedule_files],
            "checked_schedule_dirs": checked_schedule_dirs,
            "matched_classes": len(class_names_list),
            "matched_teachers": len(valid_teachers),
            "parsed_rows": parsed_rows,
            "skipped_unknown_teachers": sorted(skipped_unknown_teachers)[:20],
            "details": details[:20]  # 只返回前20条详情，避免响应过大
        }
    }


@router.post("/change-password", summary="修改密码")
async def teacher_change_password(
    request: PasswordChangeRequest,
    current_user: User = Depends(get_current_user)
):
    """教师修改自己的密码"""
    if is_admin_user(current_user):
        raise HTTPException(status_code=403, detail="管理员请使用管理员接口修改密码")

    username = current_user.username if hasattr(current_user, 'username') else current_user.get('username')

    users_data = get_users_dict()
    if username not in users_data:
        raise HTTPException(status_code=404, detail="用户不存在")

    user_info = users_data[username]
    stored_password = user_info.get("stored_password", "")
    is_password_changed = user_info.get("is_password_changed", 0)

    if not verify_password_compat(request.old_password, stored_password, is_password_changed):
        raise HTTPException(status_code=400, detail="旧密码错误")

    try:
        hashed_password = hash_password(str(request.new_password))
    except Exception as e:
        logger.error(f"Hash error: {e}")
        raise HTTPException(status_code=500, detail="密码加密失败")

    try:
        # 不再写入 raw_pwd 明文，只保存哈希值
        update_teacher_record(
            username,
            pwd=str(hashed_password),
            is_password_changed=1,
        )
        logger.info(f"Teacher {username} changed password")
        return {"message": "密码修改成功", "success": True}

    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to change password: {e}")
        raise HTTPException(status_code=500, detail=f"密码修改失败: {str(e)}")
