# -*- coding: utf-8 -*-
"""Legacy Students API - 学生和班级信息相关接口。

Batch35: 从 datas_api_legacy.py 拆分学生/班级信息逻辑。
"""

import io
import logging

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from models.datas_api.auth import User
from models.datas_api.moral.api_permission import require_configured_api_permission
from models.datas_api.moral.base import (
    get_teacher_class_ids,
    get_teacher_grade_ids,
    get_teacher_teaching_class_ids,
)
from models.daily.inout import InOut
from models.lesson.lesson import Lesson
from utils.sqlite_moral_db import MoralDatabase

logger = logging.getLogger(__name__)

router = APIRouter()


# ============================================================
# Model Classes
# ============================================================

class StudentInfoRequest(BaseModel):
    """学生信息请求参数"""
    sid: str
    classCode: str


# ============================================================
# Helper Functions
# ============================================================

def get_stu_dict(sid):
    """获取学生信息的字典格式"""
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


def _user_roles(user: User) -> set[str]:
    if not user or not getattr(user, "role", None):
        return set()
    return {role.strip() for role in str(user.role).split("/") if role.strip()}


def _class_row_for_code(db: MoralDatabase, class_code: str):
    return db.query_one(
        """SELECT class_id, grade_id, class_code, class_name
           FROM class
           WHERE is_active = 1 AND (class_code = ? OR class_name = ?)""",
        (str(class_code), str(class_code)),
    )


def _ensure_legacy_class_access(user: User, class_code: str, *, allow_teaching: bool = True) -> None:
    """旧版班级/学生接口的班级范围控制。"""
    roles = _user_roles(user)
    if roles.intersection({"admin", "xuefa", "jiaowu"}):
        return

    with MoralDatabase() as db:
        class_row = _class_row_for_code(db, class_code)
        if not class_row:
            raise HTTPException(status_code=404, detail="班级不存在")

        class_id = int(class_row["class_id"])
        grade_id = int(class_row["grade_id"]) if class_row.get("grade_id") is not None else None

        if "cleader" in roles and class_id in get_teacher_class_ids(user, db):
            return
        if "g_leader" in roles and grade_id in get_teacher_grade_ids(user, db):
            return
        if allow_teaching and "teacher" in roles and class_id in get_teacher_teaching_class_ids(user, db):
            return

    raise HTTPException(status_code=403, detail="无权访问该班级数据")


# ============================================================
# Routes: Class Information
# ============================================================

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


# ============================================================
# Routes: Students Management
# ============================================================

@router.get("/students/{class_code}", summary="获取学生列表", description="获取指定班级的学生列表")
async def get_students(
    class_code: str,
    current_user: User = Depends(require_configured_api_permission("/api/students/{class_code}", "GET", allow_missing=False)),
):
    """获取指定班级的学生名单"""
    _ensure_legacy_class_access(current_user, class_code)
    l = Lesson()
    students_df = l.get_cache_data("students")
    students = students_df[students_df["cname"] == class_code]["name"].tolist()
    return {"students": students}


@router.get("/students/export/{class_code}")
async def export_students_excel(
    class_code: str,
    current_user: User = Depends(require_configured_api_permission("/api/students/export/{class_code}", "GET", allow_missing=False)),
):
    """导出班级学生 Excel"""
    _ensure_legacy_class_access(current_user, class_code, allow_teaching=False)
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
async def import_students_excel(
    class_code: str,
    file: UploadFile = File(...),
    current_user: User = Depends(require_configured_api_permission("/api/students/import/{class_code}", "POST", allow_missing=False)),
):
    """导入学生 Excel"""
    _ensure_legacy_class_access(current_user, class_code, allow_teaching=False)
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


@router.get("/students_status/{class_code}")
async def get_students_status(
    class_code: str,
    current_user: User = Depends(require_configured_api_permission("/api/students_status/{class_code}", "GET", allow_missing=False)),
):
    """获取所有学生状态 - 数据源改为德育系统"""
    _ensure_legacy_class_access(current_user, class_code)
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
                    except Exception:
                        pass
        except Exception as e:
            logger.warning(f"获取InOut状态失败: {e}")

        return result


@router.post("/student_info/")
async def get_student_info(
    request: StudentInfoRequest,
    current_user: User = Depends(require_configured_api_permission("/api/student_info/", "POST", allow_missing=False)),
):
    """获取指定学生信息"""
    sid = request.sid
    class_code = request.classCode
    _ensure_legacy_class_access(current_user, class_code)
    student = get_stu_dict(sid)
    if not student:
        raise HTTPException(status_code=404, detail="学生不存在")
    if student['cname'] != class_code:
        raise HTTPException(status_code=403, detail="无权查看其他班级的学生信息")
    return student
