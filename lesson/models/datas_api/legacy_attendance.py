# -*- coding: utf-8 -*-
"""Legacy Attendance API - 考勤/请假/延时相关接口。

Batch36: 从 datas_api_legacy.py 拆分考勤/请假/延时逻辑。
"""

import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from models.daily.inout import InOut
from models.datas_api.auth import User, get_current_user
from models.datas_api.moral.api_permission import require_configured_api_permission
from models.datas_api.legacy_students import StudentInfoRequest, get_stu_dict, _ensure_legacy_class_access
from models.lesson.lesson import Lesson
from utils.sqlite_moral_db import MoralDatabase as SQLiteMoralDatabase

logger = logging.getLogger(__name__)

router = APIRouter()


# ============================================================
# Model Classes
# ============================================================

class LeaveRecordRequest(BaseModel):
    """请假记录请求参数"""
    class_code: str
    names: list[str]
    style: str
    days: int = 1
    note: str = ""


# ============================================================
# Helper Functions
# ============================================================

def _user_has_role(user, role: str):
    """检查用户是否有指定角色"""
    if not user or not getattr(user, "role", None):
        return False
    return role in str(user.role).split("/")


def _user_has_any_role(user, roles: list[str]):
    """检查用户是否有任意指定角色"""
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
    """确保用户有请假操作权限"""
    if not _user_has_any_role(user, ["cleader", "g_leader", "xuefa", "admin"]) and not _user_has_admin_role(user):
        raise HTTPException(status_code=403, detail="无权限操作请假记录")


def _can_manage_all_classes(user):
    """检查用户是否可以管理所有班级"""
    return _user_has_any_role(user, ["xuefa", "admin"]) or _user_has_admin_role(user)


def _get_cleader_class_rows(username: str):
    """获取班主任负责的班级数据行"""
    l = Lesson()
    class_template = l.get_cache_data("class_template")
    if class_template is None or class_template.empty:
        return class_template
    class_template = class_template.copy()
    class_template["leaders"] = class_template["leaders"].fillna("")
    mask = class_template["leaders"].apply(lambda leaders: username in str(leaders).split("/"))
    return class_template[mask]


def _resolve_class_row(class_template, class_code: str):
    """根据班级代码或名称查找班级数据行"""
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


def _get_gleader_class_names(user):
    """获取年级主任管理的年级下所有班级名称"""
    with SQLiteMoralDatabase() as db:
        # 获取年级主任管理的年级ID
        username = user.username if hasattr(user, 'username') else ''
        user_candidates = [username]
        if not username.startswith('T_'):
            user_candidates.append(f'T_{username}')

        grade_ids = set()

        # 方式1：通过 grade.leader_ids 字段匹配
        for uid in user_candidates:
            rows = db.query_all(
                "SELECT grade_id, leader_ids FROM grade WHERE leader_ids LIKE ?",
                (f'%{uid}%',)
            )
            for row in rows:
                leader_ids_str = row.get('leader_ids', '')
                leader_ids = [lid.strip() for lid in leader_ids_str.split(',') if lid.strip()]
                if uid in leader_ids:
                    grade_ids.add(row['grade_id'])

        if not grade_ids:
            return []

        # 方式2：获取这些年级下的所有班级名称
        placeholders = ','.join(['?'] * len(grade_ids))
        classes = db.query_all(
            f"SELECT class_name FROM class WHERE grade_id IN ({placeholders}) AND is_active = 1",
            tuple(grade_ids)
        )
        return [c['class_name'] for c in classes if c.get('class_name')]


# ============================================================
# Routes: Delay (延时)
# ============================================================

@router.post("/insert_delay/")
async def insert_delay(
    request: StudentInfoRequest,
    current_user: Optional[User] = Depends(require_configured_api_permission("/api/insert_delay/", "POST", allow_missing=False)),
):
    """插入学生延迟"""
    _ensure_legacy_class_access(current_user, request.classCode)
    try:
        with InOut() as i:
            did = i.insert_inout(request.sid, "延时", request.classCode, status="已申请")
        return {"delay_id": did, "status": "已申请"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"提交失败：{str(e)}")


@router.get("/delay_infos/{classCode}")
async def get_delay_infos(
    classCode: str,
    current_user: Optional[User] = Depends(require_configured_api_permission("/api/delay_infos/{classCode}", "GET", allow_missing=False)),
):
    """获取所有学生延迟"""
    _ensure_legacy_class_access(current_user, classCode)
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
async def del_delay(id: int, current_user: User = Depends(require_configured_api_permission("/api/del_delay/{id}", "GET", allow_missing=False))):
    """删除延时记录（统一鉴权已完成角色校验，保留班级范围判断）"""
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


# ============================================================
# Routes: Leave Records (请假)
# ============================================================

@router.get("/cleader-classes/")
async def get_cleader_classes(current_user: User = Depends(require_configured_api_permission("/api/cleader-classes/", "GET", allow_missing=False))):
    """获取班主任负责的班级列表（统一鉴权已完成角色校验，保留范围判断）"""
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


@router.post("/leave-records/", summary="提交请假记录", description="提交学生请假/外出记录")
async def insert_leave_records(
    request: LeaveRecordRequest, current_user: User = Depends(require_configured_api_permission("/api/leave-records/", "POST", allow_missing=False))
):
    """提交请假记录（统一鉴权已完成角色校验，保留班级范围判断）"""
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


@router.get("/leave-records/")
async def get_leave_records(
    page: int = 1,
    page_size: int = 10,
    class_code: str = None,
    current_user: User = Depends(require_configured_api_permission("/api/leave-records/", "GET", allow_missing=False)),
):
    """获取请假记录列表（统一鉴权已完成角色校验，保留班级/年级范围判断）"""
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
        # 区分班主任和年级主任
        if _user_has_role(current_user, "g_leader"):
            # 年级主任查看本年级班级
            grade_class_names = _get_gleader_class_names(current_user)
            if not grade_class_names:
                return {"total": 0, "page": page, "page_size": page_size, "records": []}
            class_template = l.get_cache_data("class_template")
            if class_template is None or class_template.empty:
                class_names = grade_class_names
                class_rows = None
            else:
                class_rows = class_template[class_template["class_name"].astype(str).isin(grade_class_names)]
                class_names = class_rows["class_name"].astype(str).tolist() if not class_rows.empty else grade_class_names

            if class_code:
                # 验证 class_code 是否在年级主任管理的班级内
                class_row = _resolve_class_row(class_rows if class_rows is not None else class_template, class_code)
                if class_row is None:
                    raise HTTPException(status_code=404, detail="班级不存在")
                class_name_from_row = str(class_row.get("class_name", class_code))
                if class_name_from_row not in grade_class_names:
                    raise HTTPException(status_code=403, detail="无权查看该班级")
                class_names = [class_name_from_row]
        else:
            # 班主任查看本班
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
    if class_rows is not None and "class_name" in class_rows.columns and "class_code" in class_rows.columns:
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


@router.post("/leave-records/{record_id}/consume")
async def consume_leave_record(
    record_id: int, current_user: User = Depends(require_configured_api_permission("/api/leave-records/{record_id}/consume", "POST", allow_missing=False))
):
    """销假（统一鉴权已完成角色校验，保留班级/年级范围判断）"""
    _ensure_leave_permission(current_user)
    l = Lesson()
    manage_all = _can_manage_all_classes(current_user)
    class_rows = None
    grade_class_names = []
    is_g_leader = _user_has_role(current_user, "g_leader")

    if not manage_all:
        if is_g_leader:
            # 年级主任获取管理的班级
            grade_class_names = _get_gleader_class_names(current_user)
            if not grade_class_names:
                raise HTTPException(status_code=403, detail="无权操作")
        else:
            # 班主任获取管理的班级
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
        if is_g_leader:
            # 年级主任检查班级是否属于自己管理的年级
            if class_name not in grade_class_names:
                raise HTTPException(status_code=403, detail="无权操作该记录")
        else:
            # 班主任检查班级是否属于自己管理的班级
            if class_name not in class_rows["class_name"].astype(str).tolist():
                raise HTTPException(status_code=403, detail="无权操作该记录")

    with InOut() as i:
        i.in_inout(record_id, consumer=current_user.username)
    return {"status": "已销假"}
