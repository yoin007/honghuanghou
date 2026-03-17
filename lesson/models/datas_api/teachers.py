# -*- coding: utf-8 -*-
"""教师管理模块 - 教师CRUD、密码修改"""

import os
import logging
import pandas as pd
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from config.config import Config
from models.datas_api.auth import (
    User,
    get_current_user,
    get_users_dict,
    get_user,
    hash_password,
    verify_password_compat,
    is_admin_user
)
from models.datas_api.utils import backup_excel_file, refresh_teacher_cache

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/teachers", tags=["教师管理"])


# ==================== Request Models ====================

class TeacherCreate(BaseModel):
    username: str
    subject: str
    course: str
    active: int = 1
    password: str
    role: str = "teacher"
    level: int = 5


class TeacherUpdate(BaseModel):
    subject: Optional[str] = None
    course: Optional[str] = None
    active: Optional[int] = None
    role: Optional[str] = None
    level: Optional[int] = None


class PasswordChangeRequest(BaseModel):
    old_password: str
    new_password: str


# ==================== Teacher Routes ====================

@router.get("", summary="获取教师列表")
async def get_teachers(current_user: User = Depends(get_current_user)):
    """获取所有教师列表"""
    users_data = get_users_dict()
    teachers_list = []

    for username, user_info in users_data.items():
        teachers_list.append({
            "username": str(username),
            "role": str(user_info.get("role", "teacher")),
            "level": int(user_info.get("level", 0)) if user_info.get("level") is not None else 0
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
        lesson_dir = Config().get_config("lesson_dir", "lesson.yaml")
        template_path = os.path.join(lesson_dir, "checkTemplate.xlsx")

        xl = pd.ExcelFile(template_path)
        sheets = {sheet: pd.read_excel(template_path, sheet_name=sheet) for sheet in xl.sheet_names}

        if "teachers" not in sheets:
            raise HTTPException(status_code=404, detail="teachers sheet 不存在")

        df = sheets["teachers"]
        df['name'] = df['name'].astype(str)

        # 检查是否已存在
        if teacher.username in df['name'].values:
            raise HTTPException(status_code=400, detail="教师已存在")

        hashed_password = hash_password(str(teacher.password))

        new_row = {
            'name': teacher.username,
            'subject': teacher.subject,
            'course': teacher.course,
            'active': teacher.active,
            'pwd': str(hashed_password),
            'role': teacher.role,
            'level': teacher.level,
            'raw_pwd': teacher.password,
            'logined': 1,
            'is_password_changed': 1
        }

        df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
        sheets["teachers"] = df

        backup_excel_file(template_path)

        with pd.ExcelWriter(template_path, engine='openpyxl', mode='w') as writer:
            for sheet_name, sheet_df in sheets.items():
                sheet_df.to_excel(writer, sheet_name=sheet_name, index=False)

        refresh_teacher_cache()

        logger.info(f"Admin {current_user.username} created teacher {teacher.username}")
        return {"message": f"教师 {teacher.username} 创建成功", "success": True}

    except HTTPException:
        raise
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
        lesson_dir = Config().get_config("lesson_dir", "lesson.yaml")
        template_path = os.path.join(lesson_dir, "checkTemplate.xlsx")

        xl = pd.ExcelFile(template_path)
        sheets = {sheet: pd.read_excel(template_path, sheet_name=sheet) for sheet in xl.sheet_names}

        if "teachers" not in sheets:
            raise HTTPException(status_code=404, detail="teachers sheet 不存在")

        df = sheets["teachers"]
        df['name'] = df['name'].astype(str)
        mask = df['name'] == str(username)

        if not mask.any():
            raise HTTPException(status_code=404, detail="教师不存在")

        if teacher.subject is not None:
            df.loc[mask, 'subject'] = teacher.subject
        if teacher.course is not None:
            df.loc[mask, 'course'] = teacher.course
        if teacher.active is not None:
            df.loc[mask, 'active'] = teacher.active
        if teacher.role is not None:
            df.loc[mask, 'role'] = teacher.role
        if teacher.level is not None:
            df.loc[mask, 'level'] = teacher.level

        sheets["teachers"] = df

        backup_excel_file(template_path)

        with pd.ExcelWriter(template_path, engine='openpyxl', mode='w') as writer:
            for sheet_name, sheet_df in sheets.items():
                sheet_df.to_excel(writer, sheet_name=sheet_name, index=False)

        refresh_teacher_cache()

        logger.info(f"Admin {current_user.username} updated teacher {username}")
        return {"message": f"教师 {username} 更新成功", "success": True}

    except HTTPException:
        raise
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
        lesson_dir = Config().get_config("lesson_dir", "lesson.yaml")
        template_path = os.path.join(lesson_dir, "checkTemplate.xlsx")

        xl = pd.ExcelFile(template_path)
        sheets = {sheet: pd.read_excel(template_path, sheet_name=sheet) for sheet in xl.sheet_names}

        if "teachers" not in sheets:
            raise HTTPException(status_code=404, detail="teachers sheet 不存在")

        df = sheets["teachers"]
        df['name'] = df['name'].astype(str)
        mask = df['name'] == str(username)

        if not mask.any():
            raise HTTPException(status_code=404, detail="教师不存在")

        df = df[~mask]
        sheets["teachers"] = df

        backup_excel_file(template_path)

        with pd.ExcelWriter(template_path, engine='openpyxl', mode='w') as writer:
            for sheet_name, sheet_df in sheets.items():
                sheet_df.to_excel(writer, sheet_name=sheet_name, index=False)

        refresh_teacher_cache()

        logger.info(f"Admin {current_user.username} deleted teacher {username}")
        return {"message": f"教师 {username} 已删除", "success": True}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete teacher: {e}")
        raise HTTPException(status_code=500, detail=f"删除教师失败: {str(e)}")


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
        lesson_dir = Config().get_config("lesson_dir", "lesson.yaml")
        template_path = os.path.join(lesson_dir, "checkTemplate.xlsx")

        xl = pd.ExcelFile(template_path)
        sheets = {sheet: pd.read_excel(template_path, sheet_name=sheet) for sheet in xl.sheet_names}

        if "teachers" not in sheets:
            raise HTTPException(status_code=404, detail="用户不存在")

        df = sheets["teachers"]
        df['name'] = df['name'].astype(str)
        mask = df['name'] == str(username)

        if mask.any():
            df.loc[mask, 'pwd'] = str(hashed_password)
            if 'raw_pwd' in df.columns:
                df.loc[mask, 'raw_pwd'] = str(request.new_password)
            if 'is_password_changed' in df.columns:
                df.loc[mask, 'is_password_changed'] = 1
            sheets["teachers"] = df

            backup_excel_file(template_path)

            with pd.ExcelWriter(template_path, engine='openpyxl', mode='w') as writer:
                for sheet_name, sheet_df in sheets.items():
                    sheet_df.to_excel(writer, sheet_name=sheet_name, index=False)

            refresh_teacher_cache()

            logger.info(f"Teacher {username} changed password")
            return {"message": "密码修改成功", "success": True}
        else:
            raise HTTPException(status_code=404, detail="用户不存在")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to change password: {e}")
        raise HTTPException(status_code=500, detail=f"密码修改失败: {str(e)}")