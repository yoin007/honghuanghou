# -*- coding: utf-8 -*-
"""认证模块 - 用户登录、密码验证、JWT Token"""

import os
import bcrypt
from datetime import datetime, timedelta
from typing import Optional
import pandas as pd
import logging
import yaml
import jwt
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel
from config.config import Config
from models.lesson.lesson import Lesson

logger = logging.getLogger(__name__)

# 加载配置
config = Config()
try:
    config_data = config.get_config("auth", "token.yaml")
except (FileNotFoundError, yaml.YAMLError, Exception) as e:
    logger.warning(f"Failed to load token.yaml config: {e}")
    config_data = {}

# JWT配置
SECRET_KEY = os.getenv("JWT_SECRET_KEY") or config_data.get("jwt_secret")
if not SECRET_KEY:
    raise ValueError("JWT_SECRET_KEY environment variable is not set! Please set it in .env or system environment.")

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(config_data.get("token_expire_minutes") or 120)  # 默认2小时


# ==================== Pydantic Models ====================

class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    username: Optional[str] = None


class User(BaseModel):
    username: str
    role: str


# ==================== Security ====================

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/token")


# ==================== Password Functions ====================

def hash_password(password: str) -> str:
    """生成密码哈希"""
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """验证密码"""
    try:
        return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))
    except Exception:
        return False


def get_users_dict():
    """动态获取用户数据，支持缓存刷新"""
    l = Lesson()
    subject_teacher = l.get_cache_data("teacher_template")
    users_data = {}

    has_role = "role" in subject_teacher.columns
    has_level = "level" in subject_teacher.columns
    has_is_password_changed = "is_password_changed" in subject_teacher.columns
    has_active = "active" in subject_teacher.columns  # 登录权限
    has_notice = "notice" in subject_teacher.columns  # 通知开关
    has_subject = "subject" in subject_teacher.columns
    has_course = "course" in subject_teacher.columns

    for teacher in subject_teacher["name"].tolist():
        users_data[teacher] = {}
        users_data[teacher]["username"] = teacher
        teacher_row = subject_teacher[subject_teacher["name"] == teacher]
        users_data[teacher]["stored_password"] = str(teacher_row["pwd"].values[0])

        # 读取 is_password_changed 字段
        is_password_changed = 0
        if has_is_password_changed:
            val = teacher_row["is_password_changed"].values[0]
            if pd.notna(val):
                is_password_changed = int(val)
        users_data[teacher]["is_password_changed"] = is_password_changed

        # 读取 active 字段（登录权限，原 logined）
        active = 1
        if has_active:
            val = teacher_row["active"].values[0]
            if pd.notna(val):
                active = int(val)
        users_data[teacher]["active"] = active

        # 读取 notice 字段（通知开关，原 active）
        notice = 1
        if has_notice:
            val = teacher_row["notice"].values[0]
            if pd.notna(val):
                notice = int(val)
        users_data[teacher]["notice"] = notice

        # 读取 subject 字段
        subject = ""
        if has_subject:
            val = teacher_row["subject"].values[0]
            if pd.notna(val):
                subject = str(val)
        users_data[teacher]["subject"] = subject

        # 读取 course 字段
        course = ""
        if has_course:
            val = teacher_row["course"].values[0]
            if pd.notna(val):
                course = str(val)
        users_data[teacher]["course"] = course

        # 角色
        role = "teacher"
        if has_role:
            r = teacher_row["role"].values[0]
            if pd.notna(r):
                role = str(r)
        users_data[teacher]["role"] = role

        # 等级
        level = 0
        if has_level:
            l_val = teacher_row["level"].values[0]
            if pd.notna(l_val):
                level = int(l_val)
        users_data[teacher]["level"] = level

    return users_data


def verify_password_compat(plain_password, stored_password, is_password_changed=0):
    """
    验证密码，根据 is_password_changed 决定验证方式
    - is_password_changed=1: 使用 bcrypt 验证
    - is_password_changed=0: 使用明文验证
    """
    if is_password_changed == 1:
        if stored_password and stored_password.startswith(('$2a$', '$2b$', '$2y$')):
            try:
                return verify_password(plain_password, stored_password)
            except Exception as e:
                logger.error(f"Password verification failed: {e}")
                return False
        return False

    if stored_password and plain_password == stored_password:
        return True

    return False


def get_password_hash(password):
    """生成密码哈希"""
    return hash_password(password)


def get_user(username: str):
    """动态获取用户信息"""
    users_data = get_users_dict()
    if username in users_data:
        user_dict = users_data[username]
        role = str(user_dict.get("role", "user")) if user_dict.get("role") else "user"
        return User(username=str(user_dict["username"]), role=role)
    return None


def authenticate_user(username: str, password: str):
    """验证用户登录"""
    # 只刷新教师模板缓存，确保用户数据是最新的
    l = Lesson()
    l.cache_datas["teacher_template"] = l.teacher_template

    users_data = get_users_dict()
    if username not in users_data:
        return False
    user = users_data[username]

    # 检查是否允许登录
    active = user.get("active", 1)
    if active == 0:
        return False

    is_password_changed = user.get("is_password_changed", 0)
    if not verify_password_compat(password, user["stored_password"], is_password_changed):
        return False
    return user


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """创建访问令牌"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


async def get_current_user(token: str = Depends(oauth2_scheme)) -> User:
    """获取当前登录用户"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        token_data = TokenData(username=username)
    except jwt.PyJWTError:
        raise credentials_exception
    user = get_user(token_data.username)
    if user is None:
        raise credentials_exception
    return user


def is_admin_user(user):
    """检查用户是否为管理员"""
    if not user:
        return False
    if hasattr(user, 'role'):
        role = str(user.role) if user.role else ""
    else:
        role = str(user.get("role", "")) if isinstance(user, dict) else ""
    return role == "admin" or "admin" in role or role == "teacher/xuefa"


def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    """获取当前活跃用户"""
    return current_user


# ==================== Auth Router ====================

router = APIRouter(prefix="", tags=["认证"])


@router.post("/token", summary="用户登录", description="使用用户名和密码登录，获取访问令牌")
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    """用户登录接口"""
    user = authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user["username"], "role": user.get("role", "user")}, expires_delta=access_token_expires
    )

    # 记录登录日志
    logger.info(f"User {user['username']} logged in successfully")

    return {"access_token": access_token, "token_type": "bearer"}