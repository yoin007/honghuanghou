# -*- coding: utf-8 -*-
"""管理员模块 - 用户管理、密码重置"""

import logging
import random
import string
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from models.datas_api.auth import (
    User,
    get_current_user,
    get_users_dict,
    hash_password,
    verify_password_compat,
    is_admin_user,
    get_password_hash,
    authenticate_user
)
from models.datas_api.moral.api_permission import require_configured_api_permission
from utils.teacher_db import update_teacher_record

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", tags=["管理员"])


# ==================== Request Models ====================

class PasswordResetRequest(BaseModel):
    username: str


class AdminSetPasswordRequest(BaseModel):
    """管理员设置用户密码"""
    username: str
    new_password: str


class PasswordChangeRequest(BaseModel):
    old_password: str
    new_password: str


class ResetPasswordChangeRequest(BaseModel):
    username: str


# ==================== Admin Routes ====================

@router.get("/users", summary="获取用户列表")
async def list_users(current_user: User = Depends(require_configured_api_permission("/api/admin/users", "GET", allow_missing=False))):
    """获取所有用户列表（需要管理员权限）"""
    if not is_admin_user(current_user):
        raise HTTPException(status_code=403, detail="只有管理员可以访问")

    users_data = get_users_dict()
    users_list = []

    for username, user_info in users_data.items():
        users_list.append({
            "username": username,
            "role": user_info.get("role", "teacher"),
            "level": user_info.get("level", 0)
        })

    return {"users": users_list, "total": len(users_list)}


@router.post("/reset-password")
async def admin_reset_password(
    request: PasswordResetRequest,
    current_user: User = Depends(require_configured_api_permission("/api/admin/reset-password", "POST", allow_missing=False))
):
    """管理员重置用户密码（生成随机密码）"""
    if not is_admin_user(current_user):
        raise HTTPException(status_code=403, detail="只有管理员可以执行此操作")

    import secrets
    import string
    # 使用 secrets 模块生成安全随机密码，强制包含字母和数字
    alphabet = string.ascii_letters + string.digits
    # 确保至少包含一个字母和一个数字
    password_chars = [
        secrets.choice(string.ascii_letters),  # 至少一个字母
        secrets.choice(string.digits),         # 至少一个数字
    ]
    # 剩余字符从完整字母表随机选择
    remaining_length = 8 - len(password_chars)
    password_chars.extend(secrets.choice(alphabet) for _ in range(remaining_length))
    # 打乱顺序避免固定模式
    secrets.SystemRandom().shuffle(password_chars)
    new_password = ''.join(password_chars)

    try:
        hashed_password = hash_password(new_password)
        # 不再写入 raw_pwd 明文，只保存哈希值
        update_teacher_record(
            request.username,
            pwd=str(hashed_password),
            is_password_changed=1,
        )
        admin_name = str(current_user.username)
        logger.info(f"Admin {admin_name} reset password for {request.username}")
        # 临时密码只在响应中显示，不落库
        return {"message": f"密码已重置为: {new_password}", "success": True}

    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to reset password: {e}")
        raise HTTPException(status_code=500, detail=f"密码重置失败: {str(e)}")


@router.post("/set-password")
async def admin_set_password(
    request: AdminSetPasswordRequest,
    current_user: User = Depends(require_configured_api_permission("/api/admin/set-password", "POST", allow_missing=False))
):
    """管理员为用户设置密码"""
    if not is_admin_user(current_user):
        raise HTTPException(status_code=403, detail="只有管理员可以执行此操作")

    try:
        hashed_password = hash_password(str(request.new_password))
        # 不再写入 raw_pwd 明文，只保存哈希值
        update_teacher_record(
            request.username,
            pwd=str(hashed_password),
            is_password_changed=1,
        )
        admin_name = str(current_user.username)
        logger.info(f"Admin {admin_name} set password for {request.username}")
        return {"message": f"用户 {request.username} 密码已更新", "success": True}

    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to set password: {e}")
        raise HTTPException(status_code=500, detail=f"密码更新失败: {str(e)}")


@router.post("/reset-password-changed")
async def admin_reset_password_changed(
    request: ResetPasswordChangeRequest,
    current_user: User = Depends(get_current_user)
):
    """管理员重置用户的密码修改状态为未修改（is_password_changed=0），使用明文验证"""
    if not is_admin_user(current_user):
        raise HTTPException(status_code=403, detail="只有管理员可以执行此操作")

    username = request.username

    try:
        update_teacher_record(username, is_password_changed=0)
        logger.info(f"Admin reset password_changed to 0 for user {username}")
        return {"message": f"用户 {username} 的密码状态已重置为未修改", "success": True}

    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to reset password_changed: {e}")
        raise HTTPException(status_code=500, detail=f"重置失败: {str(e)}")
