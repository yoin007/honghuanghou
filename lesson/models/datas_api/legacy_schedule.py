# -*- coding: utf-8 -*-
"""Legacy Schedule API - 课表和班级相关接口。

Batch33: 从 datas_api_legacy.py 拆分课表/班级逻辑。
"""

import json
import math
import os
import shutil
import logging
import numpy as np
import pandas as pd
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile, File
from config.config import Config
from models.lesson.lesson import Lesson
from models.datas_api.auth import User, is_admin_user
from models.datas_api.moral.api_permission import require_configured_api_permission
from models.datas_api.legacy_common import check_legacy_api_permission
from utils.cache import cache
from utils.operation_log import operation_logger

# 导入 utils.py 中的共享函数
from models.datas_api.utils import (
    WEEKDAYS,
    get_schedule_data,
    get_teacher_data,
    get_time_table,
)


router = APIRouter()

logger = logging.getLogger(__name__)
static_url = Config().get_config('static_url', 'wechat.yaml')

# ============================================================
# 惰性缓存：避免 import 时触发 I/O 副作用
# ============================================================
_cached_schedule_data = None
_cached_teachers_data = None
_cached_periods = None


def get_schedule_data_cached():
    """惰性获取课表数据缓存，避免 import 时 I/O"""
    global _cached_schedule_data
    if _cached_schedule_data is None:
        _cached_schedule_data = get_schedule_data()
    return _cached_schedule_data


def get_teachers_data_cached():
    """惰性获取教师数据缓存，避免 import 时 I/O"""
    global _cached_teachers_data
    if _cached_teachers_data is None:
        _cached_teachers_data = get_teacher_data()
    return _cached_teachers_data


def get_periods_cached():
    """惰性获取时间段缓存，避免 import 时 I/O"""
    global _cached_periods
    if _cached_periods is None:
        _cached_periods = get_time_table()
    return _cached_periods


def clear_schedule_module_cache():
    """清除课表模块的惰性缓存，供外部刷新调用"""
    global _cached_schedule_data, _cached_teachers_data, _cached_periods
    _cached_schedule_data = None
    _cached_teachers_data = None
    _cached_periods = None


# ============================================================
# 路由：课表和班级相关接口
# ============================================================

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

    schedule_data = get_schedule_data_cached()
    if class_name not in schedule_data:
        raise HTTPException(status_code=404, detail="未找到该班级的课程表")

    result = {"schedule": schedule_data[class_name]}
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


@router.get("/periods")
async def get_periods():
    """获取课程时间安排"""
    return {"periods": get_periods_cached()}


@router.get("/current-classes")
async def get_current_classes(user: User = Depends(require_configured_api_permission("/api/current-classes", "GET", allow_missing=False))):
    """获取当前所有班级正在上的课程（统一鉴权已完成角色校验）"""
    schedule_data = get_schedule_data_cached()
    periods = get_periods_cached()
    teachers_data = get_teachers_data_cached()

    current_time = datetime.now().strftime("%H:%M")
    current_classes = {}

    for class_code, schedule in schedule_data.items():
        current_period = None

        for period, time_range in periods.items():
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
                period_index = list(periods.keys()).index(current_period)

                if 0 <= period_index < len(day_schedule):
                    subject = day_schedule[period_index]
                    # 根据科目查找对应的教师
                    teacher = None
                    for t, subjects in teachers_data.items():
                        if subject in subjects:
                            teacher = t
                            break

                    current_classes[class_code] = {
                        "subject": subject,
                        "teacher": teacher or "未知教师",
                        "period": current_period,
                    }

    return {"current_classes": current_classes}


@router.get("/teacher-schedule/{teacher_name}")
async def get_teacher_schedule(teacher_name: str, user: User = Depends(require_configured_api_permission("/api/teacher-schedule/{teacher_name}", "GET", allow_missing=False))):
    """获取指定教师的本周课表（教师仅本人，管理员可查看全部）。"""
    if not is_admin_user(user) and user.username != teacher_name:
        raise HTTPException(status_code=403, detail="无权查看其他教师的课表")

    teachers_data = get_teachers_data_cached()
    periods = get_periods_cached()

    if teacher_name not in teachers_data:
        raise HTTPException(status_code=404, detail="教师不存在")

    teacher_subjects = teachers_data[teacher_name]
    teacher_schedule = {str(i): {} for i in range(1, 6)}  # 周一到周五
    weekday_map = {
        "monday": "1",
        "tuesday": "2",
        "wednesday": "3",
        "thursday": "4",
        "friday": "5",
    }
    schedule_data = get_schedule_data()

    for class_code, schedule in schedule_data.items():
        for day_name, day_schedule in schedule.items():
            day_number = weekday_map.get(day_name)
            if day_number:
                for period_index, subject in enumerate(day_schedule):
                    if subject in teacher_subjects:
                        period = list(periods.keys())[period_index]
                        if period not in teacher_schedule[day_number]:
                            teacher_schedule[day_number][period] = []
                        teacher_schedule[day_number][period].append(
                            {"class_code": class_code, "subject": subject}
                        )

    return {"schedule": teacher_schedule}


@router.get("/teacher-schedule-nextweek/{teacher_name}")
async def get_teacher_schedule_nextweek(teacher_name: str, current_user: User = Depends(require_configured_api_permission("/api/teacher-schedule-nextweek/{teacher_name}", "GET", allow_missing=False))):
    """获取指定教师的下周课表（统一鉴权已完成角色校验，保留本人判断）"""
    # 权限检查
    if not is_admin_user(current_user) and current_user.username != teacher_name:
        raise HTTPException(status_code=403, detail="无权查看其他教师的课表")

    teachers_data = get_teachers_data_cached()
    periods = get_periods_cached()

    if teacher_name not in teachers_data:
        raise HTTPException(status_code=404, detail="教师不存在")

    teacher_subjects = teachers_data[teacher_name]
    teacher_schedule = {str(i): {} for i in range(1, 8)}  # 周一到周日
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
                        period = list(periods.keys())[period_index]
                        if period not in teacher_schedule[day_number]:
                            teacher_schedule[day_number][period] = []
                        teacher_schedule[day_number][period].append(
                            {"class_code": class_code, "subject": subject}
                        )

    return {"schedule": teacher_schedule}


@router.post("/upload-schedule")
async def upload_schedule(file: UploadFile = File(...), current_user: User = Depends(require_configured_api_permission("/api/upload-schedule", "POST", allow_missing=False))):
    """上传课表文件（统一鉴权已完成教务/管理员校验）"""
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
