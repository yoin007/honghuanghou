# -*- coding: utf-8 -*-
"""Legacy Daily API - 日常记录相关接口。

Batch37: 从 datas_api_legacy.py 拆分日常记录逻辑。
"""

import io
import logging
from datetime import datetime

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from models.daily.daily import Daily
from models.datas_api.auth import User, get_current_user
from models.datas_api.legacy_common import check_api_permission
from models.datas_api.legacy_attendance import (
    _user_has_role,
    _can_manage_all_classes,
    _get_cleader_class_rows,
)
from models.lesson.lesson import Lesson

logger = logging.getLogger(__name__)

router = APIRouter()


# ============================================================
# Model Classes
# ============================================================

class DailyInfoRequest(BaseModel):
    """日常记录请求参数"""
    class_code: str
    names: list[str]
    type: str
    event: str
    remark: str = ""
    recorder: str = ""


# ============================================================
# Helper Functions
# ============================================================

async def _get_dailies_data(date: str = None, class_code: str = None, name: str = None, allowed_class_codes: list = None):
    """获取日常记录数据的辅助函数"""
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
                    return []  # Student not found
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


# ============================================================
# Routes: Daily Records
# ============================================================

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
