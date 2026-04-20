from fastapi import APIRouter, HTTPException, Depends, Request, File, UploadFile
from fastapi.responses import StreamingResponse
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel
from datetime import datetime
import pandas as pd
import os
import shutil
import json
import numpy as np
import math
import io
import sqlite3
import logging

from config.config import Config
from models.lesson.lesson import Lesson
from models.lesson.homework import Homework
from models.daily.inout import InOut
from models.daily.daily import Daily
from models.parking import get_parking_records
from models.manage.member import Member
from utils.rate_limit import rate_limiter
from utils.cache import cache
from utils.operation_log import operation_logger

# 获取日志记录器
logger = logging.getLogger(__name__)

static_url = Config().get_config('static_url', 'wechat.yaml')
router = APIRouter()

weekdays = {
    "1": "monday",
    "2": "tuesday",
    "3": "wednesday",
    "4": "thursday",
    "5": "friday",
    "6": "sat",
    "7": "sun",
}


def refresh_teacher_cache():
    """刷新教师相关缓存"""
    try:
        cache.delete("teacher_template")
        l = Lesson()
        l.refresh_cache()
    except Exception as e:
        logger.error(f"刷新教师缓存失败: {e}")


def backup_excel_file(file_path: str) -> str:
    """备份 Excel 文件"""
    if not os.path.exists(file_path):
        return None
    backup_path = f"{file_path}.bak"
    shutil.copy2(file_path, backup_path)
    return backup_path


def get_schedule_data(next_week: bool = False, weekdays: dict = weekdays):
    l = Lesson()
    class_template = l.get_cache_data("class_template")
    if next_week:
        df_schedule = l.get_cache_data("next_schedule")
    else:
        df_schedule = l.get_cache_data("current_schedule")
    schedule_data = {}
    for class_name in df_schedule.columns[4:]:
        if class_name not in class_template["class_name"].tolist():
            continue
        # class_code = str(
        #     class_template[class_template["class_name"] == class_name][
        #         "class_code"
        #     ].values[0]
        # )
        schedule_data[class_name] = {}
        for week, group in df_schedule[[class_name, "week"]].groupby("week"):
            schedule_data[class_name][weekdays[str(week)]] = group[class_name].tolist()
    return schedule_data


SCHEDULE_DATA = get_schedule_data()

def get_teacher_data():
    l = Lesson()
    subject_teacher = l.get_cache_data("teacher_template")
    teachers_data = {}
    for teacher in subject_teacher["name"].tolist():
        teachers_data[teacher] = (
            subject_teacher[subject_teacher["name"] == teacher]["subject"]
            .values[0]
            .split("/")
        )
    return teachers_data


TEACHERS_DATA = get_teacher_data()


def get_time_table():
    l = Lesson()
    time_table = {}
    time_periods = l.get_cache_data("time_table")
    for index, row in time_periods.iterrows():
        order = row["label"]
        time_table[order] = row["show_time"]
    return time_table


PERIODS = get_time_table()

# 作息时间
# PERIODS = {
#     "早读": "07:30-08:00",
# }


# 模拟不同班级的班主任寄语数据
TEACHER_MESSAGES = {
    "202401": {
        "content": "亲爱的同学们，在新的学期里，希望大家能够以饱满的热情投入学习。记住，成功不是偶然的，而是来自于每一天的积累和努力。让我们携手共创一个积极向上、团结互助的班级氛围！",
        "teacher": "张明",
        "date": "2024-12-08",
    }
}

from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from typing import Optional
from datetime import datetime, timedelta
import jwt
from pydantic import BaseModel
import bcrypt

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

# 密码哈希配置 (使用 bcrypt)
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

    # # 获取管理员名单
    # admin_wxids = l.admin
    # admin_names = set()
    # if admin_wxids:
    #     for wxid in admin_wxids:
    #         name = l.get_alias(wxid)
    #         if name:
    #             admin_names.add(name)

    # print(admin_names)
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
class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    username: Optional[str] = None


class User(BaseModel):
    username: str
    role: str


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


# 认证相关函数
def verify_password_compat(plain_password, stored_password, is_password_changed=0):
    """
    验证密码，根据 is_password_changed 决定验证方式
    - is_password_changed=1: 使用 bcrypt 验证
    - is_password_changed=0: 使用明文验证
    """
    # 已修改密码：使用 bcrypt 验证
    if is_password_changed == 1:
        if stored_password and stored_password.startswith(('$2a$', '$2b$', '$2y$')):
            try:
                return verify_password(plain_password, stored_password)
            except Exception as e:
                print(f"Password verification failed: {e}")
                return False
        return False

    # 未修改密码：使用明文验证
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
        # 确保 role 是字符串类型，避免 numpy 类型序列化问题
        role = str(user_dict.get("role", "user")) if user_dict.get("role") else "user"
        return User(username=str(user_dict["username"]), role=role)
    return None


def authenticate_user(username: str, password: str):
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


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


async def get_current_user(token: str = Depends(oauth2_scheme)):
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
    """检查用户是否为管理员"""
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


# 基于 config/api_level.yaml 的权限检查
def _match_route(path: str, pattern: str) -> bool:
    path_parts = [p for p in path.strip("/").split("/") if p != ""]
    pattern_parts = [p for p in pattern.strip("/").split("/") if p != ""]
    if len(path_parts) != len(pattern_parts):
        return False
    for pp, tp in zip(path_parts, pattern_parts):
        if tp.startswith("{") and tp.endswith("}"):
            continue
        if pp != tp:
            return False
    return True


def _get_api_rule(path: str):
    # 兼容带有 /api 前缀的路由
    norm_path = path
    if norm_path.startswith("/api/"):
        norm_path = norm_path[4:]
    cfg_all = Config().get_config_all("api_level.yaml")
    defaults = cfg_all.get("defaults", {})
    routes = cfg_all.get("routes", {})
    for patt, conf in routes.items():
        if _match_route(norm_path, patt):
            merged = dict(defaults)
            merged.update(conf or {})
            return merged
    return defaults


async def check_api_permission(request: Request):
    rule = _get_api_rule(request.url.path)
    allowed_roles = rule.get("allowed_roles", [])
    min_level = int(rule.get("min_level", 0))
    if "all" in allowed_roles and min_level == 0:
        return
    jwt_required = rule.get("jwt_required", True)
    if not jwt_required:
        return
    auth_header = request.headers.get("Authorization", "")
    token = ""
    if auth_header.startswith("Bearer "):
        token = auth_header.split(" ", 1)[1]
    if not token:
        raise HTTPException(status_code=401, detail="Unauthorized")
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
    users_data = get_users_dict()
    user = users_data.get(username)
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    roles = user.get("role", "").split('/')
    level = int(user.get("level") or 0)
    if allowed_roles and not any(role in allowed_roles for role in roles):
        raise HTTPException(status_code=403, detail="Forbidden: role not allowed")
    if level < min_level:
        raise HTTPException(status_code=403, detail="Forbidden: level too low")
    return


# =============================================================================
# 课程表接口
# =============================================================================

# 获取所有班级代码
@router.get("/class-codes/", summary="获取班级代码列表", description="获取所有班级的代码列表")
@router.get("/class-codes/")
async def get_class_codes(request: Request, ip: str = None):
    """获取所有可用的班级代码"""
    # 尝试从缓存获取
    cache_key = "api:class_codes"
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    if ip:
        terminal_ip = ip
    else:
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            terminal_ip = forwarded_for.split(",")[0].strip()
        else:
            terminal_ip = request.headers.get("x-real-ip") or (
                request.client.host if request.client else ""
            )
    # print(terminal_ip)
    l = Lesson()
    class_template = l.get_cache_data("class_template")
    class_codes = [str(c) for c in class_template["class_code"].tolist()]
    ips = [str(i) for i in class_template["ip"].tolist()]
    class_ip = [class_code for class_code, ip_addr in zip(class_codes, ips) if ip_addr == terminal_ip]
    if not class_ip:
        class_ip = class_codes

    result = {"class_codes": class_ip}
    # 缓存 5 分钟
    cache.set(cache_key, result, 300)
    return result


@router.get("/schedule/{class_name}", summary="获取班级课表", description="获取指定班级的本周课表")
async def get_class_schedule(class_name: str):
    """获取指定班级的课程表"""
    # 尝试从缓存获取
    cache_key = f"api:schedule:{class_name}"
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    if class_name not in SCHEDULE_DATA:
        raise HTTPException(status_code=404, detail="未找到该班级的课程表")

    result = {"schedule": SCHEDULE_DATA[class_name]}
    # 缓存 5 分钟
    cache.set(cache_key, result, 300)
    return result

@router.get("/todays")
async def get_todays_schedule(date: str = None):
    """获取指定日期的课程，默认今日"""
    # 尝试从缓存获取
    cache_key = f"api:todays:{date or 'today'}"
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    l = Lesson()
    
    def get_schedule_for_date(target_date):
        df = l.get_cache_data("current_schedule")
        if df is None or df.empty:
            return pd.DataFrame()
        if "date" not in df.columns:
            return pd.DataFrame()
        
        try:
            if target_date:
                target_dt = datetime.strptime(target_date, "%Y-%m-%d")
                target_day = target_dt.day
                target_weekday = target_dt.weekday() + 1
            else:
                now = l.get_cache_data("now")
                target_day = now.day
                target_weekday = now.weekday() + 1
        except (ValueError, TypeError, KeyError) as e:
            logging.warning(f"Failed to parse target_date: {e}")
            now = l.get_cache_data("now")
            target_day = now.day
            target_weekday = now.weekday() + 1
        
        df["date"] = df["date"].astype(int)
        
        if "weekday" in df.columns:
            df["weekday"] = df["weekday"].astype(int)
            schedule_df = df[(df["date"] == target_day) & (df["weekday"] == target_weekday)]
        else:
            schedule_df = df[df["date"] == target_day]
        
        return schedule_df
    
    r = get_schedule_for_date(date)
    
    if r is not None:
        class NpEncoder(json.JSONEncoder):
            def default(self, obj):
                if isinstance(obj, np.integer):
                    return int(obj)
                if isinstance(obj, np.floating):
                    if np.isnan(obj) or math.isnan(obj):
                        return None
                    if np.isinf(obj) or math.isinf(obj):
                        if obj > 0:
                            return "Infinity"
                        else:
                            return "-Infinity"
                    return float(obj)
                if isinstance(obj, np.ndarray):
                    return obj.tolist()
                return super(NpEncoder, self).default(obj)

        r = r.replace({np.nan: None})
        result_dict = r.to_dict("records")
        result = json.loads(json.dumps(result_dict, cls=NpEncoder))
    else:
        result = []

    # 缓存 1 分钟
    cache.set(cache_key, result, 60)
    return result

@router.get("/schedules")
async def get_schedules():
    """获取课表数据"""
    l = Lesson()
    schedule_file = l.get_cache_data("schedule_file")
    current = schedule_file[0]
    week_next = schedule_file[1]
    def replace_url(url):
        new_url = ''
        if url:
            new_url = static_url + url.split('lesson')[-1].replace('\\', '/')
        return new_url
    return [replace_url(current), replace_url(week_next)]


# =============================================================================
# 作业和公告接口
# =============================================================================

@router.get("/homework/{class_code}", summary="获取班级作业", description="获取指定班级的所有作业列表")
async def get_homework(class_code: str):
    """获取作业列表，按类型分类，按学科和老师分组"""
    n = Homework()
    n.__enter__()
    subjects = n.subjects
    homework_by_type = {"日常": {}, "周末": {}}
    
    for subject in subjects:
        daily = n.get_homework(class_code, subject, "日常")
        weekly = n.get_homework(class_code, subject, "周末")
        
        if daily:
            homework_by_type["日常"][subject] = daily
        if weekly:
            homework_by_type["周末"][subject] = weekly
    
    n.__exit__(None, None, None)
    return homework_by_type


@router.get("/announcements/{class_code}")
async def get_class_announcements(class_code: str):
    """获取指定班级的公告"""
    n = Homework()
    n.__enter__()
    announcements = n.get_announcement(class_code)
    return {"announcements": announcements}


class HomeworkForm(BaseModel):
    classCode: str
    subject: str
    teacher: str = "管理员"
    content: str
    deadline: str
    duration: int
    type: str


@router.post("/homework/", dependencies=[Depends(get_current_user)])
async def create_homework(homework: HomeworkForm, current_user: User = Depends(get_current_user)):
    """发布作业（需要登录）"""
    if not current_user:
        raise HTTPException(status_code=401, detail="请先登录")

    # 直接使用当前登录用户的用户名作为老师，不依赖前端传递
    teacher_name = current_user.username

    try:
        n = Homework()
        n.__enter__()
        n.add_homework(
            class_code=homework.classCode,
            subject=homework.subject,
            teacher=teacher_name,
            content=homework.content,
            deadline=homework.deadline,
            duration=homework.duration,
            type=homework.type,
            wxid=""
        )
        result = {"id": n.cursor.lastrowid, "message": "作业发布成功"}
        n.__exit__(None, None, None)

        # 记录操作日志
        operation_logger.info(
            "发布作业",
            username=teacher_name,
            details={
                "class_code": homework.classCode,
                "subject": homework.subject,
                "type": homework.type,
                "teacher": teacher_name
            }
        )

        # WebSocket 通知
        try:
            from websocket import notify_homework_update
            await notify_homework_update(homework.classCode, {"action": "create", "subject": homework.subject})
        except Exception as ws_err:
            logger.warning(f"WebSocket notification failed: {ws_err}")

        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class HomeworkIds(BaseModel):
    ids: list[int]
    classCode: str


@router.delete("/homework/batch")
async def delete_homework_batch(homework_ids: HomeworkIds):
    """批量删除作业"""
    try:
        n = Homework()
        n.__enter__()
        deleted_count = 0
        for hw_id in homework_ids.ids:
            n.delete_homework(hw_id)
            deleted_count += 1
        n.__exit__(None, None, None)

        # 记录操作日志
        operation_logger.info(
            "批量删除作业",
            details={
                "class_code": homework_ids.classCode,
                "deleted_ids": homework_ids.ids,
                "count": deleted_count
            }
        )

        # WebSocket 通知
        try:
            from websocket import notify_homework_update
            await notify_homework_update(homework_ids.classCode, {"action": "delete", "count": deleted_count})
        except Exception as ws_err:
            logger.warning(f"WebSocket notification failed: {ws_err}")

        return {"message": f"成功删除 {deleted_count} 条作业"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class AnnouncementForm(BaseModel):
    classCode: str
    title: str
    author: str
    content: str


@router.post("/announcement/")
async def create_announcement(announcement: AnnouncementForm):
    """发布公告"""
    try:
        n = Homework()
        n.__enter__()
        n.add_announcement(
            class_code=announcement.classCode,
            title=announcement.title,
            author=announcement.author,
            content=announcement.content,
            wxid=""
        )
        result = {"id": n.cursor.lastrowid, "message": "公告发布成功"}
        n.__exit__(None, None, None)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class HomeworkUpdateForm(BaseModel):
    subject: Optional[str] = None
    content: Optional[str] = None
    deadline: Optional[str] = None
    duration: Optional[int] = None
    type: Optional[str] = None


@router.put("/homework/{hw_id}")
async def update_homework(hw_id: int, homework: HomeworkUpdateForm, current_user: dict = None):
    """修改作业"""
    print(homework)
    try:
        n = Homework()
        n.__enter__()
        existing = n.get_homework_by_id(hw_id)
        if not existing:
            n.__exit__(None, None, None)
            raise HTTPException(status_code=404, detail="作业不存在")
        
        if existing.get("deleted", 0) == 1:
            n.__exit__(None, None, None)
            raise HTTPException(status_code=404, detail="作业不存在")
        
        if current_user and current_user.get("role") != "admin":
            if existing.get("teacher") != current_user.get("sub"):
                n.__exit__(None, None, None)
                raise HTTPException(status_code=403, detail="无权限修改他人发布的作业")
        
        n.update_homework(
            hw_id=hw_id,
            subject=homework.subject,
            content=homework.content,
            deadline=homework.deadline,
            duration=homework.duration,
            type=homework.type
        )
        n.__exit__(None, None, None)
        return {"message": "作业更新成功"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/homework/{hw_id}")
async def delete_homework(hw_id: int, current_user: dict = None):
    """删除作业"""
    try:
        n = Homework()
        n.__enter__()
        existing = n.get_homework_by_id(hw_id)
        if not existing:
            n.__exit__(None, None, None)
            raise HTTPException(status_code=404, detail="作业不存在")
        
        if existing.get("deleted", 0) == 1:
            n.__exit__(None, None, None)
            raise HTTPException(status_code=404, detail="作业不存在")
        
        if current_user and current_user.get("role") != "admin":
            if existing.get("teacher") != current_user.get("sub"):
                n.__exit__(None, None, None)
                raise HTTPException(status_code=403, detail="无权限删除他人发布的作业")
        
        n.delete_homework(hw_id)
        n.__exit__(None, None, None)
        return {"message": "作业删除成功"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class AnnouncementUpdateForm(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None


@router.put("/announcement/{ann_id}")
async def update_announcement(ann_id: int, announcement: AnnouncementUpdateForm, current_user: dict = None):
    """修改公告"""
    try:
        n = Homework()
        n.__enter__()
        existing = n.get_announcement_by_id(ann_id)
        if not existing:
            n.__exit__(None, None, None)
            raise HTTPException(status_code=404, detail="公告不存在")
        
        if current_user and current_user.get("role") != "admin":
            if existing.get("author") != current_user.get("sub"):
                n.__exit__(None, None, None)
                raise HTTPException(status_code=403, detail="无权限修改他人发布的公告")
        
        n.update_announcement(
            ann_id=ann_id,
            title=announcement.title,
            content=announcement.content
        )
        n.__exit__(None, None, None)
        return {"message": "公告更新成功"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/announcement/{ann_id}")
async def delete_announcement(ann_id: int, current_user: dict = None):
    """删除公告"""
    try:
        n = Homework()
        n.__enter__()
        existing = n.get_announcement_by_id(ann_id)
        if not existing:
            n.__exit__(None, None, None)
            raise HTTPException(status_code=404, detail="公告不存在")
        
        if current_user and current_user.get("role") != "admin":
            if existing.get("author") != current_user.get("sub"):
                n.__exit__(None, None, None)
                raise HTTPException(status_code=403, detail="无权限删除他人发布的公告")
        
        n.delete_announcement(ann_id)
        n.__exit__(None, None, None)
        return {"message": "公告删除成功"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/messages/{class_code}")
async def get_teacher_messages(class_code: str):
    """获取指定班级的老师留言"""
    if class_code not in TEACHER_MESSAGES:
        return {"messages": []}
    return {"messages": [TEACHER_MESSAGES[class_code]]}


@router.get("/class-info/{class_code}")
async def get_class_info(class_code: str):
    """获取指定班级的基本信息 - 数据源改为德育系统"""
    from utils.sqlite_moral_db import MoralDatabase

    with MoralDatabase() as db:
        # 查询班级基本信息，包含学生数实时计算
        class_info = db.query_one("""
            SELECT
                c.class_name,
                c.leader_name,
                c.established,
                c.motto,
                c.location,
                g.grade_name,
                COUNT(s.student_id) as student_count
            FROM class c
            LEFT JOIN student s ON c.class_id = s.class_id AND s.is_active = 1
            JOIN grade g ON c.grade_id = g.grade_id
            WHERE c.class_code = ? AND c.is_active = 1
            GROUP BY c.class_id
        """, (class_code,))

        if not class_info:
            raise HTTPException(status_code=404, detail="班级不存在")

        return {
            "class_info": {
                "className": class_info["class_name"],
                "classTeacher": class_info["leader_name"] or "未设置",
                "studentCount": class_info["student_count"],
                "established": class_info["established"] or "未设置",
                "motto": class_info["motto"] or "未设置",
                "location": class_info["location"] or "未设置"
            }
        }


# =============================================================================
# 学生管理接口
# =============================================================================

@router.get("/students/{class_code}", summary="获取学生列表", description="获取指定班级的学生列表")
async def get_students(class_code: str):
    """获取指定班级的学生名单"""
    l = Lesson()
    students_df = l.get_cache_data("students")
    students = students_df[students_df["cname"] == class_code]["name"].tolist()
    return {"students": students}


@router.get("/students/export/{class_code}")
async def export_students_excel(class_code: str):
    """导出班级学生 Excel"""
    l = Lesson()
    students_df = l.get_cache_data("students")
    if students_df is None or students_df.empty:
        raise HTTPException(status_code=404, detail="暂无学生数据")

    class_students = students_df[students_df["cname"] == class_code].copy()
    if class_students.empty:
        raise HTTPException(status_code=404, detail=f"未找到班级 {class_code} 的学生")

    # 选择需要导出的列
    export_cols = ["sid", "name", "sex", "phone", "roomid", "rpid"]
    available_cols = [col for col in export_cols if col in class_students.columns]
    export_df = class_students[available_cols].copy()

    # 生成 Excel
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        export_df.to_excel(writer, index=False, sheet_name=f"{class_code}")

    output.seek(0)
    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={class_code}_students.xlsx"}
    )


@router.post("/students/import/{class_code}")
async def import_students_excel(class_code: str, file: UploadFile = File(...)):
    """导入学生 Excel"""
    if not file.filename.endswith(('.xlsx', '.xls')):
        raise HTTPException(status_code=400, detail="只允许上传 .xlsx 或 .xls 格式的文件")

    try:
        contents = await file.read()
        df = pd.read_excel(io.BytesIO(contents))

        # 验证必要列
        required_cols = ["sid", "name"]
        missing_cols = [col for col in required_cols if col not in df.columns]
        if missing_cols:
            raise HTTPException(status_code=400, detail=f"缺少必要列: {missing_cols}")

        # 这里只返回预览数据，实际更新需要管理员确认
        preview = df.head(10).to_dict(orient="records")
        return {
            "message": f"成功读取 {len(df)} 条学生数据",
            "preview": preview,
            "total": len(df)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"导入失败: {str(e)}")


@router.get("/periods")
async def get_periods():
    """获取课程时间安排"""
    return {"periods": PERIODS}


@router.get("/current-classes", dependencies=[Depends(check_api_permission)])
async def get_current_classes():
    """获取当前所有班级正在上的课程"""
    current_time = datetime.now().strftime("%H:%M")
    current_classes = {}

    for class_code, schedule in SCHEDULE_DATA.items():
        current_period = None

        for period, time_range in PERIODS.items():
            start_time, end_time = time_range.split("-")
            # 将时间字符串转换为分钟数，以便进行比较
            start_minutes = sum(
                int(x) * 60**i for i, x in enumerate(reversed(start_time.split(":")))
            )
            end_minutes = sum(
                int(x) * 60**i for i, x in enumerate(reversed(end_time.split(":")))
            )
            current_minutes = sum(
                int(x) * 60**i for i, x in enumerate(reversed(current_time.split(":")))
            )

            if start_minutes <= current_minutes <= end_minutes:
                current_period = period
                break
        if current_period is not None:
            # 获取当前是星期几
            weekday = datetime.now().weekday()
            weekday_map = {
                0: "monday",
                1: "tuesday",
                2: "wednesday",
                3: "thursday",
                4: "friday",
                5: "saturday",
                6: "sun",
            }

            if weekday in weekday_map:  # 周一到周五
                day_name = weekday_map[weekday]
                day_schedule = schedule.get(day_name, [])
                period_index = list(PERIODS.keys()).index(current_period)

                if 0 <= period_index < len(day_schedule):
                    subject = day_schedule[period_index]
                    # 根据科目查找对应的教师
                    teacher = None
                    for t, subjects in TEACHERS_DATA.items():
                        if subject in subjects:
                            teacher = t
                            break

                    current_classes[class_code] = {
                        "subject": subject,
                        "teacher": teacher or "未知教师",
                        "period": current_period,
                    }

    return {"current_classes": current_classes}


@router.get("/teacher-schedule/{teacher_name}", dependencies=[Depends(check_api_permission)])
async def get_teacher_schedule(teacher_name: str):
    """获取指定教师的课表"""
    if teacher_name not in TEACHERS_DATA:
        raise HTTPException(status_code=404, detail="教师不存在")

    teacher_subjects = TEACHERS_DATA[teacher_name]
    teacher_schedule = {str(i): {} for i in range(1, 6)}  # 周一到周五
    weekday_map = {
        "monday": "1",
        "tuesday": "2",
        "wednesday": "3",
        "thursday": "4",
        "friday": "5",
    }
    schedule_data = get_schedule_data()
    # print(schedule_data)
    for class_code, schedule in schedule_data.items():
        for day_name, day_schedule in schedule.items():
            day_number = weekday_map.get(day_name)
            if day_number:
                for period_index, subject in enumerate(day_schedule):
                    if subject in teacher_subjects:
                        period = list(PERIODS.keys())[period_index]
                        if period not in teacher_schedule[day_number]:
                            teacher_schedule[day_number][period] = []
                        teacher_schedule[day_number][period].append(
                            {"class_code": class_code, "subject": subject}
                        )

    return {"schedule": teacher_schedule}


@router.get("/teacher-schedule-nextweek/{teacher_name}")
async def get_teacher_schedule_nextweek(teacher_name: str, current_user: User = Depends(get_current_user)):
    """获取指定教师的课表"""
    # 权限检查
    if current_user.role != "admin" and current_user.username != teacher_name:
        raise HTTPException(status_code=403, detail="无权查看其他教师的课表")

    if teacher_name not in TEACHERS_DATA:
        raise HTTPException(status_code=404, detail="教师不存在")

    teacher_subjects = TEACHERS_DATA[teacher_name]
    teacher_schedule = {str(i): {} for i in range(1, 8)}  # 周一到周五
    weekday_map = {
        "monday": "1",
        "tuesday": "2",
        "wednesday": "3",
        "thursday": "4",
        "friday": "5",
    }
    schedule_data = get_schedule_data(next_week=True)

    for class_code, schedule in schedule_data.items():
        for day_name, day_schedule in schedule.items():
            day_number = weekday_map.get(day_name)
            if day_number:
                for period_index, subject in enumerate(day_schedule):
                    if subject in teacher_subjects:
                        period = list(PERIODS.keys())[period_index]
                        if period not in teacher_schedule[day_number]:
                            teacher_schedule[day_number][period] = []
                        teacher_schedule[day_number][period].append(
                            {"class_code": class_code, "subject": subject}
                        )

    return {"schedule": teacher_schedule}


@router.get("/vehicle-inout/{counts}", dependencies=[Depends(check_api_permission)])
async def get_vehicle_inout(counts: int = 20):
    """获取所有车辆进出记录"""
    records = get_parking_records(counts)

    return records

@router.get("/students_status/{class_code}")
async def get_students_status(class_code: str):
    """获取所有学生状态 - 数据源改为德育系统"""
    from utils.sqlite_moral_db import MoralDatabase

    with MoralDatabase() as db:
        # 查询德育系统学生数据，关联班级表获取班级名称
        query = """
            SELECT
                s.student_id as sid,
                s.name,
                c.class_name as cname,
                s.roomid,
                s.rpid,
                s.status,
                s.is_active as active
            FROM student s
            JOIN class c ON s.class_id = c.class_id
            WHERE c.class_name = ? AND s.is_active = 1
            ORDER BY s.roomid, s.rpid, s.student_id
        """
        students = db.query_all(query, (class_code,))

        if not students:
            return []

        # 转换为前端期望的格式
        result = []
        for stu in students:
            result.append({
                'sid': stu['sid'],
                'name': stu['name'],
                'cname': stu['cname'],
                'roomid': stu['roomid'] or '',
                'rpid': str(stu['rpid']) if stu['rpid'] else '',
                'status': stu['status'] or '在校',
                'active': stu['active']
            })

        # 补充请假/离校状态（从InOut系统）
        try:
            with InOut() as i:
                leaves = i.get_inouts(activate=1)
                for leave in leaves:
                    try:
                        sid = str(leave[1])
                        for stu in result:
                            if stu['sid'] == sid:
                                stu['status'] = f"{leave[2]}-{leave[4]}"
                                break
                    except:
                        pass
        except Exception as e:
            logger.warning(f"获取InOut状态失败: {e}")

        return result

class StudentInfoRequest(BaseModel):
    sid: str
    classCode: str

def get_stu_dict(sid):
    l = Lesson()
    students_df = l.get_cache_data("students")
     # 转换 roomid 和 rpid 为整数再转字符串，去除小数点
    def safe_int_str(x):
        try:
            if pd.isna(x):
                return ""
            if isinstance(x, (int, float)):
                return str(int(x))
            return str(x)
        except (ValueError, TypeError) as e:
            logging.warning(f"safe_int_str conversion error: {e}")
            return str(x)

    for col in ['roomid', 'rpid', 'sid']:
        if col in students_df.columns:
            students_df[col] = students_df[col].apply(safe_int_str)
    students_df = students_df[(students_df["sid"] == sid) & (students_df['active'] == 1)].copy()
    if students_df.empty:
        return {}
    else:
        student = students_df.iloc[0].to_dict()
        return student


@router.post("/student_info/")
async def get_student_info(request: StudentInfoRequest):
    """获取指定学生信息"""
    sid = request.sid
    class_code = request.classCode
    student = get_stu_dict(sid)
    if not student:
        raise HTTPException(status_code=404, detail="学生不存在")
    if student['cname'] != class_code:
        raise HTTPException(status_code=403, detail="无权查看其他班级的学生信息")
    return student

@router.post("/insert_delay/")
async def insert_delay(request: StudentInfoRequest):
    """插入学生延迟"""
    try:
        with InOut() as i:
            did = i.insert_inout(request.sid, "延时", request.classCode, status="已申请")
        return {"delay_id": did, "status": "已申请"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"提交失败：{str(e)}")

@router.get("/delay_infos/{classCode}")
async def get_delay_infos(classCode: str):
    """获取所有学生延迟"""
    today = datetime.now().strftime("%Y-%m-%d")
    with InOut() as i:
        delays = i.get_inouts(activate=1, recorder=classCode, date=today)
    if not delays:
        return []
    else:
        result = []
        for row in delays:
            sid = row[1]
            student = get_stu_dict(sid)
            if not student:
                continue
            item = {
                "序号": row[0],
                "姓名": student['name'],
                "宿舍": student['roomid'],
                "床号": student['rpid'],
                "申请时间": row[-1]
            }
            result.append(item)
        return result 

@router.get("/del_delay/{id}")
async def del_delay(id: int, current_user: User = Depends(get_current_user)):
    """删除学生延时记录"""
    # 获取延时记录的班级信息
    with InOut() as i:
        recorder = i.get_recorder(id)
        if not recorder:
            raise HTTPException(status_code=404, detail="记录不存在")

    # 权限检查：管理员可删除所有班级，班主任只能删除自己班级
    if not _user_has_any_role(current_user, ["admin", "xuefa"]):
        # 班主任需要检查是否是本班级的记录
        if not _user_has_role(current_user, "cleader"):
            raise HTTPException(status_code=403, detail="无权限删除")
        # 获取班主任负责的班级
        class_rows = _get_cleader_class_rows(current_user.username)
        if class_rows is None or class_rows.empty:
            raise HTTPException(status_code=403, detail="无权限删除")
        allowed_classes = class_rows["class_code"].tolist()
        if recorder not in allowed_classes:
            raise HTTPException(status_code=403, detail="无权限删除其他班级的记录")

    # 执行删除
    try:
        with InOut() as i:
            i.del_delay(id)
        return {"status": "已取消"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"取消失败：{str(e)}")

class LeaveRecordRequest(BaseModel):
    class_code: str
    names: list[str]
    style: str
    days: int = 1
    note: str = ""

def _user_has_role(user, role: str):
    if not user or not getattr(user, "role", None):
        return False
    return role in str(user.role).split("/")

def _user_has_any_role(user, roles: list[str]):
    if not user or not getattr(user, "role", None):
        return False
    user_roles = str(user.role).split("/")
    return any(role in user_roles for role in roles)

def _user_has_admin_role(user):
    """检查用户是否有管理员角色（包括 admin、管理员）"""
    if not user or not getattr(user, "role", None):
        return False
    role = str(user.role).lower()
    return "admin" in role or "管理员" in role

def _ensure_leave_permission(user):
    if not _user_has_any_role(user, ["cleader", "xuefa", "admin"]) and not _user_has_admin_role(user):
        raise HTTPException(status_code=403, detail="无权限操作请假记录")

def _can_manage_all_classes(user):
    return _user_has_any_role(user, ["xuefa", "admin"]) or _user_has_admin_role(user)

def _get_cleader_class_rows(username: str):
    l = Lesson()
    class_template = l.get_cache_data("class_template")
    if class_template is None or class_template.empty:
        return class_template
    class_template = class_template.copy()
    class_template["leaders"] = class_template["leaders"].fillna("")
    mask = class_template["leaders"].apply(lambda leaders: username in str(leaders).split("/"))
    return class_template[mask]

def _resolve_class_row(class_template, class_code: str):
    if class_template is None or class_template.empty:
        return None
    class_code_str = str(class_code)
    class_rows = class_template[
        (class_template["class_code"].astype(str) == class_code_str)
        | (class_template["class_name"].astype(str) == class_code_str)
    ]
    if class_rows.empty:
        return None
    return class_rows.iloc[0]

@router.get("/cleader-classes/", dependencies=[Depends(check_api_permission)])
async def get_cleader_classes(current_user: User = Depends(get_current_user)):
    _ensure_leave_permission(current_user)

    # 学发部或管理员可以看到所有班级
    if _can_manage_all_classes(current_user):
        l = Lesson()
        class_template = l.get_cache_data("class_template")
        if class_template is None or class_template.empty:
            return {"classes": [], "class_codes": []}
        classes = []
        for _, row in class_template.iterrows():
            classes.append(
                {
                    "class_code": str(row.get("class_code", "")),
                    "class_name": str(row.get("class_name", "")),
                }
            )
        return {"classes": classes, "class_codes": [item["class_code"] for item in classes]}

    # 班主任返回自己负责的班级
    if _user_has_role(current_user, "cleader"):
        class_rows = _get_cleader_class_rows(current_user.username)
        if class_rows is None or class_rows.empty:
            return {"classes": [], "class_codes": []}
        classes = []
        for _, row in class_rows.iterrows():
            classes.append(
                {
                    "class_code": str(row.get("class_code", "")),
                    "class_name": str(row.get("class_name", "")),
                }
            )
        return {"classes": classes, "class_codes": [item["class_code"] for item in classes]}

    # 普通教师没有负责的班级，返回空
    return {"classes": [], "class_codes": []}

@router.post("/leave-records/", dependencies=[Depends(check_api_permission)], summary="提交请假记录", description="提交学生请假/外出记录")
async def insert_leave_records(
    request: LeaveRecordRequest, current_user: User = Depends(get_current_user)
):
    _ensure_leave_permission(current_user)
    if not request.names:
        raise HTTPException(status_code=400, detail="请至少选择一名学生")
    l = Lesson()
    class_template = l.get_cache_data("class_template")
    class_row = _resolve_class_row(class_template, request.class_code)
    if class_row is None:
        raise HTTPException(status_code=404, detail=f"班级 {request.class_code} 不存在")
    if not _can_manage_all_classes(current_user):
        leaders = str(class_row.get("leaders", ""))
        if current_user.username not in leaders.split("/"):
            raise HTTPException(status_code=403, detail="无权操作该班级")
    class_name = str(class_row.get("class_name", request.class_code))
    record_ids = []
    with InOut() as i:
        for name in request.names:
            sid = l.get_sid(class_name, name)
            if not sid:
                continue
            did = i.insert_inout(
                sid,
                request.style,
                current_user.username,
                status="已请假",
                days=str(request.days),
                note=request.note,
            )
            record_ids.append(did)
    return {"inout_ids": record_ids, "status": "已提交"}

# =============================================================================
# 请假记录接口
# =============================================================================

@router.get("/leave-records/", dependencies=[Depends(check_api_permission)])
async def get_leave_records(
    page: int = 1,
    page_size: int = 10,
    class_code: str = None,
    current_user: User = Depends(get_current_user),
):
    _ensure_leave_permission(current_user)
    if page < 1 or page_size < 1:
        raise HTTPException(status_code=400, detail="分页参数不合法")
    l = Lesson()
    if _can_manage_all_classes(current_user):
        class_template = l.get_cache_data("class_template")
        if class_template is None or class_template.empty:
            return {"total": 0, "page": page, "page_size": page_size, "records": []}
        if class_code:
            class_row = _resolve_class_row(class_template, class_code)
            if class_row is None:
                raise HTTPException(status_code=404, detail="班级不存在")
            class_names = [str(class_row.get("class_name", class_code))]
            class_rows = class_template[class_template["class_name"].astype(str).isin(class_names)]
        else:
            class_names = class_template["class_name"].astype(str).tolist()
            class_rows = class_template
    else:
        class_rows = _get_cleader_class_rows(current_user.username)
        if class_rows is None or class_rows.empty:
            return {"total": 0, "page": page, "page_size": page_size, "records": []}
        if class_code:
            class_row = _resolve_class_row(class_rows, class_code)
            if class_row is None:
                raise HTTPException(status_code=403, detail="无权查看该班级")
            class_names = [str(class_row.get("class_name", class_code))]
        else:
            class_names = class_rows["class_name"].astype(str).tolist()
    students_df = l.get_cache_data("students")
    if students_df is None or students_df.empty:
        return {"total": 0, "page": page, "page_size": page_size, "records": []}
    students_df = students_df.copy()
    students_df["sid"] = students_df["sid"].astype(str)
    students_df = students_df[students_df["cname"].isin(class_names)]
    sids = students_df["sid"].astype(str).tolist()
    if not sids:
        return {"total": 0, "page": page, "page_size": page_size, "records": []}
    class_code_map = {}
    if "class_name" in class_rows.columns and "class_code" in class_rows.columns:
        class_code_map = dict(
            zip(
                class_rows["class_name"].astype(str).tolist(),
                class_rows["class_code"].astype(str).tolist(),
            )
        )
    student_map = students_df.set_index("sid")[["name", "cname"]].to_dict(orient="index")
    placeholders = ",".join(["?"] * len(sids))
    base_sql = f"FROM inout WHERE sid IN ({placeholders}) AND style != '延时'"
    with InOut() as i:
        i.__cursor__.execute(f"SELECT COUNT(*) {base_sql}", tuple(sids))
        total = i.__cursor__.fetchone()[0] or 0
        offset = (page - 1) * page_size
        query_sql = f"SELECT * {base_sql} ORDER BY create_at DESC LIMIT ? OFFSET ?"
        params = list(sids) + [page_size, offset]
        i.__cursor__.execute(query_sql, tuple(params))
        rows = i.__cursor__.fetchall()
        columns = i.inout_columns()
    records = []
    for row in rows:
        item = dict(zip(columns, row))
        sid = str(item.get("sid", ""))
        student = student_map.get(sid, {})
        class_name = str(student.get("cname", ""))
        item["name"] = student.get("name", "")
        item["class_name"] = class_name
        item["class_code"] = class_code_map.get(class_name, class_name)
        records.append(item)
    return {"total": total, "page": page, "page_size": page_size, "records": records}

@router.post("/leave-records/{record_id}/consume", dependencies=[Depends(check_api_permission)])
async def consume_leave_record(
    record_id: int, current_user: User = Depends(get_current_user)
):
    _ensure_leave_permission(current_user)
    l = Lesson()
    manage_all = _can_manage_all_classes(current_user)
    class_rows = None
    if not manage_all:
        class_rows = _get_cleader_class_rows(current_user.username)
        if class_rows is None or class_rows.empty:
            raise HTTPException(status_code=403, detail="无权操作")
    with InOut() as i:
        i.__cursor__.execute("SELECT * FROM inout WHERE id = ?", (record_id,))
        row = i.__cursor__.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="记录不存在")
        columns = i.inout_columns()
        record = dict(zip(columns, row))
        sid = str(record.get("sid", ""))
    students_df = l.get_cache_data("students")
    if students_df is None or students_df.empty:
        raise HTTPException(status_code=404, detail="学生不存在")
    students_df = students_df.copy()
    students_df["sid"] = students_df["sid"].astype(str)
    student_row = students_df[students_df["sid"] == sid]
    if student_row.empty:
        raise HTTPException(status_code=404, detail="学生不存在")
    class_name = str(student_row.iloc[0].get("cname", ""))
    if not manage_all:
        if class_name not in class_rows["class_name"].astype(str).tolist():
            raise HTTPException(status_code=403, detail="无权操作该记录")
    with InOut() as i:
        i.in_inout(record_id, consumer=current_user.username)
    return {"status": "已销假"}

class DailyInfoRequest(BaseModel):
    class_code: str
    names: list[str]
    type: str
    event: str
    remark: str = ""
    recorder: str = ""

# =============================================================================
# 日常记录接口
# =============================================================================

@router.post("/insert_daily/", dependencies=[Depends(check_api_permission)])
async def insert_daily(request: DailyInfoRequest):
    """插入学生日常"""
    try:
        l = Lesson()
        class_template = l.get_cache_data("class_template")
        # 查找对应的 class_name
        class_row = class_template[class_template["class_code"].astype(str) == str(request.class_code)]
        if class_row.empty:
             raise HTTPException(status_code=404, detail=f"班级代码 {request.class_code} 不存在")
        
        class_name = class_row["class_name"].values[0]
        
        record_ids = []
        with Daily() as d:
            for name in request.names:
                sid = l.get_sid(class_name, name)
                if not sid:
                    continue
                did = d.insert_daily(request.event, str(int(sid)), request.type, request.recorder, request.remark)
                record_ids.append(did)
        
        return {"daily_ids": record_ids, "status": "已记录"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"提交失败：{str(e)}")

# Deleted conflicting code
async def _get_dailies_data(date: str = None, class_code: str = None, name: str = None, allowed_class_codes: list = None):
    l = Lesson()
    sids = None

    # 如果有班级限制，需要获取允许班级的学生列表
    if allowed_class_codes and not class_code:
        # 获取所有允许班级的学生
        class_template = l.get_cache_data("class_template")
        students = l.get_cache_data("students")

        # 获取允许的班级名称
        allowed_class_names = []
        for cc in allowed_class_codes:
            class_row = class_template[class_template["class_code"].astype(str) == str(cc)]
            if not class_row.empty:
                allowed_class_names.append(str(class_row["class_name"].values[0]))

        if name:
            # 按名字过滤，但限制在允许的班级内
            sids = students[(students["name"] == name) & (students["cname"].isin(allowed_class_names))]["sid"].astype(str).tolist()
        else:
            # 获取所有允许班级的学生
            sids = students[students["cname"].isin(allowed_class_names)]["sid"].astype(str).tolist()

        if not sids:
            return []
    elif class_code:
        class_template = l.get_cache_data("class_template")
        # Ensure string comparison
        class_row = class_template[class_template["class_code"].astype(str) == str(class_code)]
        if not class_row.empty:
            class_name = class_row["class_name"].values[0]
            if name:
                sid = l.get_sid(class_name, name)
                if sid:
                    sids = [str(int(sid))]
                else:
                    return [] # Student not found
            else:
                students = l.get_cache_data("students")
                sids = students[(students["cname"] == class_name)]["sid"].astype(str).tolist()
        else:
             if name:
                 return []
             else:
                 return []
    elif name:
         students = l.get_cache_data("students")
         # Filter by name only
         sids = students[students["name"] == name]["sid"].astype(str).tolist()
         
    with Daily() as d:
        rows = d.get_dailies(date=date, sids=sids)
        columns = d.daily_columns()
    
    result = []
    if not rows:
        return result
        
    # Enrich data
    students_df = l.get_cache_data("students")
    
    student_map = {}
    if students_df is not None:
         # Ensure sid is string for matching
         students_df = students_df.copy()
         students_df["sid"] = students_df["sid"].astype(str)
         student_map = students_df.set_index("sid").to_dict('index')
             
    for row in rows:
        item = dict(zip(columns, row))
        sid = str(item.get("sid", ""))
        stu_info = student_map.get(sid, {})
        item["name"] = stu_info.get("name", "")
        item["class_name"] = stu_info.get("cname", "")
        item["room_info"] = f"{stu_info.get('roomid','')}-{stu_info.get('rpid','')}"
        result.append(item)
    return result

@router.post("/upload-schedule", dependencies=[Depends(check_api_permission)])
async def upload_schedule(file: UploadFile = File(...), current_user: User = Depends(get_current_user)):
    """上传课表文件并触发自动更新"""
    if not file.filename.endswith('.xlsx'):
        raise HTTPException(status_code=400, detail="只允许上传 .xlsx 格式的文件")
    
    try:
        l = Lesson()
        # 获取当前月份目录下的 temp 文件夹路径
        c_month = datetime.now().strftime("%Y%m")
        temp_dir = os.path.join(l.lesson_dir, c_month, "temp")
        
        # 确保目录存在
        os.makedirs(temp_dir, exist_ok=True)
        
        file_path = os.path.join(temp_dir, file.filename)
        
        # 保存上传的文件
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        # 触发课表更新逻辑
        from models.lesson.lesson import manual_update_schedule
        update_result = await manual_update_schedule()

        # 记录操作日志
        operation_logger.info(
            "上传课表",
            username=current_user.username if current_user else None,
            details={
                "filename": file.filename,
                "result": "success" if update_result else "partial_success"
            }
        )

        if update_result:
            return {"status": "success", "message": "文件上传并更新成功", "filename": file.filename}
        else:
            return {"status": "partial_success", "message": "文件已保存，但自动更新失败，请手动检查", "filename": file.filename}
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"处理失败: {str(e)}")

@router.get("/get_dailies/", dependencies=[Depends(check_api_permission)])
async def get_dailies(date: str = None, class_code: str = None, name: str = None, current_user: User = Depends(get_current_user)):
    """获取日常记录"""
    try:
        # 班主任只能查看自己班级学生的记录
        allowed_class_codes = None
        if _user_has_role(current_user, "cleader") and not _can_manage_all_classes(current_user):
            class_rows = _get_cleader_class_rows(current_user.username)
            if class_rows is None or class_rows.empty:
                return []  # 没有负责的班级，返回空
            allowed_class_codes = [str(cc) for cc in class_rows["class_code"].tolist()]

            # 如果请求的 class_code 不在允许列表中，返回空
            if class_code and str(class_code) not in allowed_class_codes:
                return []

        data = await _get_dailies_data(date, class_code, name, allowed_class_codes)
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"查询失败：{str(e)}")

@router.get("/export_dailies/", dependencies=[Depends(check_api_permission)])
async def export_dailies(date: str = None, class_code: str = None, name: str = None, current_user: User = Depends(get_current_user)):
    """导出日常记录"""
    try:
        # 班主任只能导出自己班级学生的记录
        allowed_class_codes = None
        if _user_has_role(current_user, "cleader") and not _can_manage_all_classes(current_user):
            class_rows = _get_cleader_class_rows(current_user.username)
            if class_rows is None or class_rows.empty:
                data = []
            else:
                allowed_class_codes = [str(cc) for cc in class_rows["class_code"].tolist()]
                if class_code and str(class_code) not in allowed_class_codes:
                    data = []
                else:
                    data = await _get_dailies_data(date, class_code, name, allowed_class_codes)
        else:
            data = await _get_dailies_data(date, class_code, name)

        df = pd.DataFrame(data)
        
        column_map = {
            "id": "ID",
            "event": "事件",
            "sid": "学号",
            "name": "姓名",
            "class_name": "班级",
            "note": "备注",
            "recorder": "记录人",
            "style": "类型",
            "create_at": "记录时间",
            "room_info": "宿舍信息"
        }
        
        if not df.empty:
            # Keep only mapped columns
            existing_cols = [c for c in column_map.keys() if c in df.columns]
            df = df[existing_cols].rename(columns=column_map)
        else:
             df = pd.DataFrame(columns=column_map.values())

        output = io.BytesIO()
        with pd.ExcelWriter(output) as writer:
            df.to_excel(writer, index=False, sheet_name='Sheet1')
        output.seek(0)
        
        filename = f"dailies_export_{datetime.now().strftime('%Y%m%d%H%M%S')}.xlsx"
        headers = {
            'Content-Disposition': f'attachment; filename="{filename}"'
        }
        return StreamingResponse(output, headers=headers, media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"导出失败：{str(e)}")

class MemberCreate(BaseModel):
    uuid: str
    wxid: str
    alias: str
    active: int = 1
    score: int = 50
    balance: int = 0
    level: int = 1
    model: str = "basic"
    ai_flag: int = 0
    birthday: str = ""
    note: str = ""

class MemberUpdate(BaseModel):
    alias: Optional[str] = None
    active: Optional[int] = None
    score: Optional[int] = None
    balance: Optional[int] = None
    level: Optional[int] = None
    model: Optional[str] = None
    ai_flag: Optional[int] = None
    birthday: Optional[str] = None

class PermissionCreate(BaseModel):
    func: str = ""
    func_name: str = ""
    pattern: str = ""
    white_list: str
    module: str
    activate: int = 1
    black_list: str = ""
    type: str = ""
    keywords: str = ""
    ai_flag: int = 0
    need_at: int = 0
    reply: str = ""
    level: int = 1
    priority: int = 99
    example: str = ""
    check_permission: int = 1
    score: int = 0
    balance: int = 0
    notes: str = ""

class PermissionUpdate(BaseModel):
    func_name: Optional[str] = None
    pattern: Optional[str] = None
    activate: Optional[int] = None
    black_list: Optional[str] = None
    white_list: Optional[str] = None
    type: Optional[str] = None
    keywords: Optional[str] = None
    ai_flag: Optional[int] = None
    need_at: Optional[int] = None
    reply: Optional[str] = None
    module: Optional[str] = None
    level: Optional[int] = None
    priority: Optional[int] = None
    example: Optional[str] = None
    check_permission: Optional[int] = None
    score: Optional[int] = None
    balance: Optional[int] = None
    notes: Optional[str] = None

# =============================================================================
# 成员和权限管理接口
# =============================================================================

@router.get("/members", dependencies=[Depends(check_api_permission)], summary="获取成员列表", description="获取所有成员列表")
async def get_members(
    page: int = 1,
    page_size: int = 10,
    search: str = None,
    active: int = None,
    current_user: User = Depends(get_current_user)
):
    """获取会员列表"""
    try:
        with Member() as m:
            m.__cursor__.execute("SELECT COUNT(*) FROM member")
            total = m.__cursor__.fetchone()[0]

            sql = "SELECT * FROM member"
            params = []
            conditions = []

            if search:
                conditions.append("(alias LIKE ? OR wxid LIKE ? OR uuid LIKE ?)")
                params.extend([f"%{search}%", f"%{search}%", f"%{search}%"])

            if active is not None:
                conditions.append("active = ?")
                params.append(active)

            if conditions:
                sql += " WHERE " + " AND ".join(conditions)
                count_sql = "SELECT COUNT(*) FROM member WHERE " + " AND ".join(conditions)
                m.__cursor__.execute(count_sql, tuple(params))
                total = m.__cursor__.fetchone()[0]

            sql += " ORDER BY id ASC LIMIT ? OFFSET ?"
            params.extend([page_size, (page - 1) * page_size])

            m.__cursor__.execute(sql, tuple(params))
            rows = m.__cursor__.fetchall()
            columns = m.member_columns()
            
            members = []
            for row in rows:
                members.append(dict(zip(columns, row)))
                
            return {
                "total": total,
                "page": page,
                "page_size": page_size,
                "data": members
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取会员列表失败: {str(e)}")

@router.post("/members", dependencies=[Depends(check_api_permission)])
async def create_member(member: MemberCreate, current_user: User = Depends(get_current_user)):
    """创建会员"""
    try:
        with Member() as m:
            # Check if uuid exists
            if m.member_info(member.uuid):
                raise HTTPException(status_code=400, detail="会员UUID已存在")
                
            rowcount = m.insert_member(
                uuid=member.uuid,
                wxid=member.wxid,
                alias=member.alias,
                active=member.active,
                score=member.score,
                balance=member.balance,
                level=member.level,
                model=member.model,
                ai_flag=member.ai_flag,
                birthday=member.birthday,
                note=member.note
            )
            if rowcount > 0:
                return {"status": "success", "message": "会员创建成功"}
            else:
                raise HTTPException(status_code=500, detail="会员创建失败")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"创建会员失败: {str(e)}")

@router.put("/members/{uuid}", dependencies=[Depends(check_api_permission)])
async def update_member(uuid: str, member: MemberUpdate, current_user: User = Depends(get_current_user)):
    """更新会员信息"""
    try:
        update_data = {k: v for k, v in member.dict().items() if v is not None}
        if not update_data:
            raise HTTPException(status_code=400, detail="没有提供更新数据")
            
        with Member() as m:
            if not m.member_info(uuid):
                raise HTTPException(status_code=404, detail="会员不存在")
                
            rowcount = m.update_member(uuid, **update_data)
            if rowcount > 0:
                return {"status": "success", "message": "会员更新成功"}
            else:
                return {"status": "success", "message": "没有数据被修改"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"更新会员失败: {str(e)}")

@router.delete("/members/{uuid}", dependencies=[Depends(check_api_permission)])
async def delete_member(uuid: str, current_user: User = Depends(get_current_user)):
    """删除会员"""
    try:
        with Member() as m:
            if not m.member_info(uuid):
                raise HTTPException(status_code=404, detail="会员不存在")
                
            rowcount = m.delte_member(uuid)
            if rowcount > 0:
                return {"status": "success", "message": "会员删除成功"}
            else:
                raise HTTPException(status_code=500, detail="会员删除失败")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"删除会员失败: {str(e)}")

@router.get("/permissions", dependencies=[Depends(check_api_permission)])
async def get_permissions(
    page: int = 1,
    page_size: int = 10,
    search: str = None,
    activate: int = None,
    current_user: User = Depends(get_current_user)
):
    """获取权限列表"""
    try:
        with Member() as m:
            m.__cursor__.execute("SELECT COUNT(*) FROM permission")
            total = m.__cursor__.fetchone()[0]

            sql = "SELECT * FROM permission"
            params = []
            conditions = []

            if search:
                conditions.append("(func LIKE ? OR func_name LIKE ? OR module LIKE ?)")
                params.extend([f"%{search}%", f"%{search}%", f"%{search}%"])

            if activate is not None:
                conditions.append("activate = ?")
                params.append(activate)

            if conditions:
                sql += " WHERE " + " AND ".join(conditions)
                count_sql = "SELECT COUNT(*) FROM permission WHERE " + " AND ".join(conditions)
                m.__cursor__.execute(count_sql, tuple(params))
                total = m.__cursor__.fetchone()[0]

            sql += " ORDER BY id DESC LIMIT ? OFFSET ?"
            params.extend([page_size, (page - 1) * page_size])

            m.__cursor__.execute(sql, tuple(params))
            rows = m.__cursor__.fetchall()
            # Get columns from cursor description
            columns = [description[0] for description in m.__cursor__.description]
            
            permissions = []
            for row in rows:
                permissions.append(dict(zip(columns, row)))
                
            return {
                "total": total,
                "page": page,
                "page_size": page_size,
                "data": permissions
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取权限列表失败: {str(e)}")

@router.post("/permissions", dependencies=[Depends(check_api_permission)])
async def create_permission(perm: PermissionCreate, current_user: User = Depends(get_current_user)):
    """创建权限"""
    try:
        with Member() as m:
            rowcount = m.insert_permission(
                func=perm.func,
                func_name=perm.func_name,
                activate=perm.activate,
                black_list=perm.black_list,
                white_list=perm.white_list,
                type=perm.type,
                pattern=perm.pattern,
                keywords=perm.keywords,
                ai_flag=perm.ai_flag,
                need_at=perm.need_at,
                reply=perm.reply,
                module=perm.module,
                level=perm.level,
                priority=perm.priority,
                example=perm.example,
                check_permission=perm.check_permission,
                score=perm.score,
                balance=perm.balance,
                notes=perm.notes
            )
            if rowcount > 0:
                return {"status": "success", "message": "权限创建成功"}
            else:
                raise HTTPException(status_code=500, detail="权限创建失败")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"创建权限失败: {str(e)}")

@router.put("/permissions/{id}", dependencies=[Depends(check_api_permission)])
async def update_permission(id: int, perm: PermissionUpdate, current_user: User = Depends(get_current_user)):
    """更新权限信息"""
    try:
        update_data = {k: v for k, v in perm.dict().items() if v is not None}
        if not update_data:
            raise HTTPException(status_code=400, detail="没有提供更新数据")
            
        with Member() as m:
            if not m.get_permission_by_id(id):
                raise HTTPException(status_code=404, detail="权限ID不存在")
                
            rowcount = m.update_permission(id, **update_data)
            if rowcount > 0:
                return {"status": "success", "message": "权限更新成功"}
            else:
                return {"status": "success", "message": "没有数据被修改"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"更新权限失败: {str(e)}")

@router.delete("/permissions/{id}", dependencies=[Depends(check_api_permission)])
async def delete_permission(id: int, current_user: User = Depends(get_current_user)):
    """删除权限"""
    try:
        with Member() as m:
            if not m.get_permission_by_id(id):
                raise HTTPException(status_code=404, detail="权限ID不存在")
                
            rowcount = m.delte_permission(id)
            if rowcount > 0:
                return {"status": "success", "message": "权限删除成功"}
            else:
                raise HTTPException(status_code=500, detail="权限删除失败")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"删除权限失败: {str(e)}")


TASK_DB_PATH = "databases/task.db"

class TaskCreate(BaseModel):
    func: str
    type: str = "function"
    trigger_type: str
    trigger_args: str
    args: str = None
    kwargs: str = None
    one_off: bool = True
    description: str = None


class TaskUpdate(BaseModel):
    func: Optional[str] = None
    type: Optional[str] = None
    trigger_type: Optional[str] = None
    trigger_args: Optional[str] = None
    args: Optional[str] = None
    kwargs: Optional[str] = None
    one_off: Optional[bool] = None
    description: Optional[str] = None
    consumed: Optional[bool] = None


def get_tasks_connection():
    conn = sqlite3.connect(TASK_DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


# =============================================================================
# 任务管理接口
# =============================================================================

@router.get("/tasks/funcs", dependencies=[Depends(check_api_permission)])
async def get_available_funcs(current_user: User = Depends(get_current_user)):
    """获取可用的任务函数列表"""
    from models.task import Task
    task_obj = Task()
    funcs = task_obj.get_available_funcs()
    return {"funcs": funcs}


@router.get("/tasks", dependencies=[Depends(check_api_permission)])
async def get_tasks(
    page: int = 1,
    page_size: int = 10,
    search: str = None,
    consumed: str = None,  # 状态筛选: "all" 或 None=全部, "pending"=待执行, "done"=已执行
    current_user: User = Depends(get_current_user)
):
    """获取任务列表"""
    try:
        conn = get_tasks_connection()
        cursor = conn.cursor()

        # 构建基础查询条件
        where_conditions = []
        params = []

        # 搜索条件
        if search:
            where_conditions.append("(func LIKE ? OR description LIKE ?)")
            params.extend([f"%{search}%", f"%{search}%"])

        # 状态筛选
        if consumed == "pending":
            where_conditions.append("consumed = 0")
        elif consumed == "done":
            where_conditions.append("consumed = 1")

        # 构建 WHERE 子句
        where_clause = ""
        count_params = []
        if where_conditions:
            where_clause = " WHERE " + " AND ".join(where_conditions)
            count_params = params.copy()

        # 获取总数
        cursor.execute(f"SELECT COUNT(*) FROM tasks{where_clause}", tuple(count_params))
        total = cursor.fetchone()[0]

        # 获取数据
        sql = f"SELECT * FROM tasks{where_clause} ORDER BY id DESC LIMIT ? OFFSET ?"
        params.extend([page_size, (page - 1) * page_size])

        cursor.execute(sql, tuple(params))
        rows = cursor.fetchall()
        conn.close()
        
        tasks = []
        for row in rows:
            task = dict(row)
            if task.get('trigger_args'):
                try:
                    task['trigger_args'] = json.dumps(json.loads(task['trigger_args']), ensure_ascii=False, indent=2)
                except:
                    pass
            if task.get('args'):
                try:
                    task['args'] = json.dumps(json.loads(task['args']), ensure_ascii=False, indent=2)
                except:
                    pass
            if task.get('kwargs'):
                try:
                    task['kwargs'] = json.dumps(json.loads(task['kwargs']), ensure_ascii=False, indent=2)
                except:
                    pass
            tasks.append(task)
        
        return {
            "total": total,
            "page": page,
            "page_size": page_size,
            "data": tasks
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取任务列表失败: {str(e)}")


@router.post("/tasks", dependencies=[Depends(check_api_permission)])
async def create_task(task: TaskCreate, current_user: User = Depends(get_current_user)):
    """创建任务"""
    try:
        conn = get_tasks_connection()
        cursor = conn.cursor()
        
        cursor.execute(
            """INSERT INTO tasks (func, type, trigger_type, trigger_args, args, kwargs, one_off, description, consumed) 
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                task.func,
                task.type,
                task.trigger_type,
                task.trigger_args,
                task.args,
                task.kwargs,
                task.one_off,
                task.description,
                False
            )
        )
        conn.commit()
        task_id = cursor.lastrowid
        conn.close()
        
        return {"status": "success", "message": "任务创建成功", "id": task_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"创建任务失败: {str(e)}")


@router.put("/tasks/{task_id}", dependencies=[Depends(check_api_permission)])
async def update_task(task_id: int, task: TaskUpdate, current_user: User = Depends(get_current_user)):
    """更新任务"""
    try:
        conn = get_tasks_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
        if not cursor.fetchone():
            conn.close()
            raise HTTPException(status_code=404, detail="任务不存在")
        
        update_fields = []
        update_values = []
        
        if task.func is not None:
            update_fields.append("func = ?")
            update_values.append(task.func)
        if task.type is not None:
            update_fields.append("type = ?")
            update_values.append(task.type)
        if task.trigger_type is not None:
            update_fields.append("trigger_type = ?")
            update_values.append(task.trigger_type)
        if task.trigger_args is not None:
            update_fields.append("trigger_args = ?")
            update_values.append(task.trigger_args)
        if task.args is not None:
            update_fields.append("args = ?")
            update_values.append(task.args)
        if task.kwargs is not None:
            update_fields.append("kwargs = ?")
            update_values.append(task.kwargs)
        if task.one_off is not None:
            update_fields.append("one_off = ?")
            update_values.append(task.one_off)
        if task.description is not None:
            update_fields.append("description = ?")
            update_values.append(task.description)
        if task.consumed is not None:
            update_fields.append("consumed = ?")
            update_values.append(task.consumed)
        
        if not update_fields:
            conn.close()
            raise HTTPException(status_code=400, detail="没有提供更新数据")
        
        update_values.append(task_id)
        sql = f"UPDATE tasks SET {', '.join(update_fields)} WHERE id = ?"
        cursor.execute(sql, tuple(update_values))
        conn.commit()
        conn.close()
        
        return {"status": "success", "message": "任务更新成功"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"更新任务失败: {str(e)}")


@router.delete("/tasks/{task_id}", dependencies=[Depends(check_api_permission)])
async def delete_task(task_id: int, current_user: User = Depends(get_current_user)):
    """删除任务"""
    try:
        conn = get_tasks_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
        if not cursor.fetchone():
            conn.close()
            raise HTTPException(status_code=404, detail="任务不存在")
        
        cursor.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
        conn.commit()
        conn.close()
        
        return {"status": "success", "message": "任务删除成功"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"删除任务失败: {str(e)}")
