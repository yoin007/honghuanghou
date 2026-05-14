# -*- coding: utf-8 -*-
"""认证模块 - 用户登录、密码验证、JWT Token"""

import os
import bcrypt
from datetime import datetime, timedelta
from typing import Optional
import logging
import yaml
import jwt
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel
from config.config import Config
from utils.teacher_db import get_teacher_by_name, get_all_teachers

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
oauth2_scheme_optional = OAuth2PasswordBearer(tokenUrl="api/token", auto_error=False)


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
    """从数据库获取用户数据"""
    teachers = get_all_teachers()
    users_data = {}

    for teacher in teachers:
        name = teacher['name']
        is_password_changed = teacher.get('is_password_changed', 0)
        stored_password = _get_compat_stored_password(teacher, is_password_changed)
        users_data[name] = {
            'teacher_id': teacher.get('teacher_id', ''),
            'username': name,
            'stored_password': stored_password,
            'is_password_changed': is_password_changed,
            'active': teacher.get('active', 1),
            'notice': teacher.get('notice', 1),
            'subject': teacher.get('subject', ''),
            'course': teacher.get('course', ''),
            'role': teacher.get('role', 'teacher'),
            'level': teacher.get('level', 10)
        }

    return users_data


def _is_password_changed(value) -> bool:
    """兼容 SQLite / DataFrame 读出的数字或字符串状态。"""
    try:
        return int(value or 0) == 1
    except (TypeError, ValueError):
        return False


def _get_compat_stored_password(teacher: dict, is_password_changed: int = 0) -> str:
    """根据改密状态选择验证用密码字段。"""
    if _is_password_changed(is_password_changed):
        return str(teacher.get('pwd', '') or '')
    return str(teacher.get('raw_pwd') or teacher.get('pwd', '') or '')


def verify_password_compat(plain_password, stored_password, is_password_changed=0):
    """
    验证密码，根据 is_password_changed 决定验证方式
    - is_password_changed=1: 使用 bcrypt 验证
    - is_password_changed=0: 使用明文验证
    """
    if _is_password_changed(is_password_changed):
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
    """验证用户登录（从数据库）"""
    teacher = get_teacher_by_name(username)

    if not teacher:
        return False

    # 检查是否允许登录
    if teacher.get('active', 1) == 0:
        return False

    is_password_changed = teacher.get('is_password_changed', 0)
    stored_password = _get_compat_stored_password(teacher, is_password_changed)

    if not verify_password_compat(password, stored_password, is_password_changed):
        return False

    return teacher


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


async def get_current_user_optional(token: Optional[str] = Depends(oauth2_scheme_optional)) -> Optional[User]:
    """获取当前登录用户（可选）- 有token返回User，无token返回None，不强制要求登录"""
    if token is None:
        return None
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            return None
        token_data = TokenData(username=username)
    except jwt.PyJWTError:
        return None
    user = get_user(token_data.username)
    return user


def is_admin_user(user):
    """检查用户是否为管理员（纯 admin 角色）

    Batch75: 语义明确 - 只判断 admin 角色，不含 teacher/xuefa 等兼容角色
    """
    if not user:
        return False
    if hasattr(user, 'role'):
        role = str(user.role) if user.role else ""
    else:
        role = str(user.get("role", "")) if isinstance(user, dict) else ""
    return role == "admin" or "admin" in role


def is_admin_or_role(user, role_name: str) -> bool:
    """检查用户是否为管理员或具有特定角色

    Batch75: 语义清晰的组合判断 helper
    用于 jiaowu、xuefa 等需要 admin + 特定角色的场景
    """
    return is_admin_user(user) or _has_role(user, role_name)


def _has_role(user, role_name: str) -> bool:
    """检查用户是否具有特定角色（内部 helper）"""
    if not user:
        return False
    if hasattr(user, 'role'):
        role = str(user.role) if user.role else ""
    else:
        role = str(user.get("role", "")) if isinstance(user, dict) else ""
    roles = role.split('/')
    return role_name in roles


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
        data={"sub": user["name"], "role": user.get("role", "user")}, expires_delta=access_token_expires
    )

    # 记录登录日志
    logger.info(f"User {user['name']} logged in successfully")

    return {"access_token": access_token, "token_type": "bearer"}
