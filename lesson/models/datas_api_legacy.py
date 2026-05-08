from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel
from datetime import datetime
import logging
import os
import pandas as pd
import jwt
import yaml

from config.config import Config
from models.lesson.lesson import Lesson
from models.datas_api.auth import hash_password, verify_password
from models.datas_api.auth import (
    verify_password_compat,
    create_access_token,
    get_password_hash,
    Token,
    TokenData,
    User,
)

# 获取日志记录器
logger = logging.getLogger(__name__)

router = APIRouter()

# Batch33: schedule 相关函数已迁移到 legacy_schedule.py 和 utils.py
# 此处保留兼容导入
from models.datas_api.legacy_schedule import router as schedule_router
router.include_router(schedule_router)

# 兼容旧名称导入
from models.datas_api.legacy_schedule import (
    get_schedule_data_cached,
    get_teachers_data_cached,
    get_periods_cached,
    static_url,
)
from models.datas_api.utils import (
    WEEKDAYS as weekdays,
    get_schedule_data,
    get_teacher_data,
    get_time_table,
    refresh_teacher_cache,
    backup_excel_file,
)


# Batch34: homework/announcement 相关代码已迁移到 legacy_homework.py
# 此处保留兼容导入
from models.datas_api.legacy_homework import router as homework_router
router.include_router(homework_router)

# 兼容导入
from models.datas_api.legacy_homework import TEACHER_MESSAGES

# Batch35: students/class-info 相关代码已迁移到 legacy_students.py
# 此处保留兼容导入
from models.datas_api.legacy_students import router as students_router
router.include_router(students_router)

# 兼容导入（delay/leave 等旧代码仍引用 StudentInfoRequest 和 get_stu_dict）
from models.datas_api.legacy_students import StudentInfoRequest, get_stu_dict

# Batch36: attendance/leave/delay 相关代码已迁移到 legacy_attendance.py
# 此处保留兼容导入
from models.datas_api.legacy_attendance import router as attendance_router
router.include_router(attendance_router)

# 兼容导入（后续路由可能引用 helper 函数）
from models.datas_api.legacy_attendance import (
    LeaveRecordRequest,
    _user_has_role,
    _user_has_any_role,
    _user_has_admin_role,
    _ensure_leave_permission,
    _can_manage_all_classes,
    _get_cleader_class_rows,
    _resolve_class_row,
)

# Batch37: daily 相关代码已迁移到 legacy_daily.py
# 此处保留兼容导入
from models.datas_api.legacy_daily import router as daily_router
router.include_router(daily_router)

# 兼容导入
from models.datas_api.legacy_daily import DailyInfoRequest

# Batch38: members 相关代码已迁移到 legacy_members.py
# 此处保留兼容导入
from models.datas_api.legacy_members import router as members_router
router.include_router(members_router)

# 兼容导入
from models.datas_api.legacy_members import MemberCreate, MemberUpdate

# Batch39: permissions 相关代码已迁移到 legacy_permissions.py
# 此处保留兼容导入
from models.datas_api.legacy_permissions import router as permissions_router
router.include_router(permissions_router)

# 兼容导入
from models.datas_api.legacy_permissions import PermissionCreate, PermissionUpdate

# JWT配置
config = Config()
try:
    config_data = config.get_config("auth", "token.yaml")
except (FileNotFoundError, yaml.YAMLError, Exception) as e:
    logging.warning(f"Failed to load token.yaml config: {e}")
    config_data = {}

# 安全修复: 强制要求设置 JWT 密钥，不允许默认值
SECRET_KEY = os.getenv("JWT_SECRET_KEY") or config_data.get("jwt_secret")
if not SECRET_KEY:
    raise ValueError("JWT_SECRET_KEY environment variable is not set! Please set it in .env or system environment.")

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(config_data.get("token_expire_minutes") or 120)  # 默认2小时

# 密码哈希函数已从 models.datas_api.auth 导入，此处不再重复定义

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
        # 存储的密码可能是明文也可能是哈希值
        users_data[teacher]["stored_password"] = str(
            teacher_row["pwd"].values[0]
        )

        # 读取 is_password_changed 字段（默认为 0，未修改密码）
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

        # 确定角色
        role = "teacher"
        if has_role:
            r = teacher_row["role"].values[0]
            if pd.notna(r):
                role = str(r)

        # if teacher in admin_names:
        #     role = "admin"

        users_data[teacher]["role"] = role

        # 确定等级
        level = 0
        if has_level:
            l_val = teacher_row["level"].values[0]
            if pd.notna(l_val):
                level = l_val
        users_data[teacher]["level"] = level

    return users_data


# 认证相关模型
# Batch74: Token/TokenData/User 已迁移到 auth.py
# 此处保留兼容导出（已在顶部导入）
# 注意：oauth2_scheme 不能代理，因为 tokenUrl 不同
#   - legacy: tokenUrl="token" (旧路径)
#   - auth: tokenUrl="api/token" (新路径)
#   - 保留 legacy 版本以兼容旧客户端


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


# Batch73: verify_password_compat 和 create_access_token 已迁移到 auth.py
# 此处保留兼容导出（从 auth.py 导入）
# 注意：get_password_hash 已是 hash_password 的代理，无需重复定义


def get_user(username: str):
    """动态获取用户信息（Batch74: 不可代理，依赖 get_users_dict）

    不可代理原因：get_users_dict 使用缓存，auth.py 版本使用数据库
    """
    users_data = get_users_dict()
    if username in users_data:
        user_dict = users_data[username]
        # 确保 role 是字符串类型，避免 numpy 类型序列化问题
        role = str(user_dict.get("role", "user")) if user_dict.get("role") else "user"
        return User(username=str(user_dict["username"]), role=role)
    return None


def authenticate_user(username: str, password: str):
    """验证用户登录（Batch74: 不可代理，数据源不同）

    不可代理原因：
    - legacy 使用缓存（get_users_dict）
    - auth.py 使用数据库（get_teacher_by_name）
    """
    users_data = get_users_dict()
    if username not in users_data:
        return False
    user = users_data[username]

    # 检查是否允许登录
    active = user.get("active", 1)
    if active == 0:
        return False

    # 使用兼容版本验证，根据 is_password_changed 决定验证方式
    is_password_changed = user.get("is_password_changed", 0)
    if not verify_password_compat(password, user["stored_password"], is_password_changed):
        return False
    return user


# Batch73: create_access_token 已迁移到 auth.py
# 此处使用导入的版本（已在顶部导入）


async def get_current_user(token: str = Depends(oauth2_scheme)):
    """获取当前登录用户（Batch74: 不可代理，依赖 get_user）

    不可代理原因：依赖 get_user，而 get_user 依赖 get_users_dict（缓存）
    """
    credentials_exception = HTTPException(
        status_code=401,
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
    user = get_user(username=token_data.username)
    if user is None:
        raise credentials_exception
    return user


# =============================================================================
# 认证接口 - 已迁移到 datas_api/auth.py
# =============================================================================

# 登录接口已迁移到 datas_api/auth.py


# 管理员接口：用户管理
class PasswordResetRequest(BaseModel):
    username: str
    new_password: str


# 教师管理模型
class TeacherCreate(BaseModel):
    username: str
    password: str
    subject: str = ""
    course: str = ""
    role: str = "teacher"
    active: bool = True
    level: int = 1


class TeacherUpdate(BaseModel):
    subject: str = ""
    course: str = ""
    role: str = "teacher"
    active: bool = True
    level: int = 1


class PasswordChangeRequest(BaseModel):
    old_password: str
    new_password: str


def is_admin_user(user):
    """检查用户是否为管理员（Batch74: 不可代理，实现不同）

    不可代理原因：
    - legacy: "admin" in role.lower() or role == "teacher/xuefa"
    - auth.py: role == "admin" or "admin" in role
    - legacy 包含 teacher/xuefa 特殊兼容
    """
    if not user:
        return False
    # 支持 Pydantic User 模型和字典两种类型
    if hasattr(user, 'role'):
        role = str(user.role) if user.role else ""
    else:
        role = str(user.get("role", "")) if isinstance(user, dict) else ""
    # admin 或包含 admin 关键字的角色，或 teacher/xuefa（学发部）
    return "admin" in role.lower() or role == "teacher/xuefa"


# =============================================================================
# 认证接口 - 用户管理 - 已迁移到 datas_api/admin.py
# =============================================================================

# 已迁移到 datas_api/admin.py


# =============================================================================
# 教师管理接口 - 已迁移到 datas_api/teachers.py
# =============================================================================

# 已迁移到 datas_api/teachers.py


# Batch72: 权限检查函数已迁移到 legacy_common.py
# 此处保留兼容导出
from models.datas_api.legacy_common import (
    check_api_permission,
    check_legacy_api_permission,
    _match_route,
    _get_api_rule,
)


# Batch32: tasks 相关路由已迁移到 legacy_tasks.py，此处保留兼容导入
from models.datas_api.legacy_tasks import router as tasks_router
router.include_router(tasks_router)

# Batch40: parking 相关路由已迁移到 legacy_parking.py
from models.datas_api.legacy_parking import router as parking_router
router.include_router(parking_router)
