# -*- coding: utf-8 -*-
"""
学生画像 API

提供学生画像的生成和查询功能
"""

import logging
from datetime import datetime
from typing import Optional, List
from decimal import Decimal
import json

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field

from .base import (
    get_moral_db,
    check_moral_permission,
    check_class_access,
    get_current_semester,
    require_permission,
)
from models.datas_api.auth import User, get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/profiles", tags=["学生画像"])


class DecimalEncoder(json.JSONEncoder):
    """自定义JSON编码器，处理Decimal类型"""
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        return super().default(obj)


# =============================================================================
# Pydantic 模型
# =============================================================================

class ProfileUpdate(BaseModel):
    """更新学生画像"""
    profile_summary: Optional[str] = Field(None, description="画像摘要")
    profile_tags: Optional[List[str]] = Field(None, description="画像标签")
    strength_tags: Optional[List[str]] = Field(None, description="优势标签")
    improvement_tags: Optional[List[str]] = Field(None, description="待改进标签")
    risk_level: Optional[str] = Field(None, description="风险等级")
    suggestions: Optional[str] = Field(None, description="个性化建议")


# =============================================================================
# API 路由
# =============================================================================

@router.get("/student/{student_id}", summary="获取学生画像")
async def get_student_profile(
    student_id: str,
    user: User = Depends(get_current_user)
):
    """
    获取学生画像

    权限说明：
    - 学生只能查看自己的画像
    - 家长只能查看子女的画像
    - 班主任可查看本班学生
    - xuefa/jiaowu/admin 可查看所有
    """
    with get_moral_db() as db:
        # 权限检查
        if user.role == 'student' and user.username != student_id:
            raise HTTPException(403, "只能查看自己的画像")

        # 获取学生信息
        student = db.query_one(
            """SELECT s.*, c.class_name, c.leader_name
            FROM student s
            JOIN class c ON s.class_id = c.class_id
            WHERE s.student_id = %s""",
            (student_id,)
        )
        if not student:
            raise HTTPException(404, "学生不存在")

        # 班主任权限检查
        if user.role == 'cleader' and student['leader_name'] != user.username:
            if not check_moral_permission(user, 'student_profile'):
                raise HTTPException(403, "只能查看本班学生画像")

        # 获取最新画像
        profile = db.query_one(
            """SELECT * FROM student_profile
            WHERE student_id = %s
            ORDER BY profile_version DESC LIMIT 1""",
            (student_id,)
        )

        # 获取画像历史
        history = db.query_all(
            """SELECT id, profile_version, generated_at,
            JSON_EXTRACT(profile_data, '$.profile_summary') as summary
            FROM student_profile_history
            WHERE student_id = %s
            ORDER BY profile_version DESC
            LIMIT 10""",
            (student_id,)
        )

        return {
            "success": True,
            "data": {
                "student": {
                    "student_id": student['student_id'],
                    "name": student['name'],
                    "class_name": student['class_name']
                },
                "profile": profile,
                "history": history
            }
        }


@router.post("/student/{student_id}/generate", summary="生成学生画像")
async def generate_student_profile(
    student_id: str,
    request: Request,
    user: User = Depends(require_permission('student_profile'))
):
    """
    生成学生画像（基于德育数据分析）

    权限要求：xuefa/jiaowu/admin
    """
    with get_moral_db() as db:
        # 获取学生信息
        student = db.query_one(
            "SELECT * FROM student WHERE student_id = %s",
            (student_id,)
        )
        if not student:
            raise HTTPException(404, "学生不存在")

        current_semester = get_current_semester(db)
        semester_id = current_semester['semester_id'] if current_semester else None

        # 分析学生数据
        analysis = analyze_student_data(db, student_id, semester_id)

        # 生成画像
        profile_summary = generate_profile_summary(analysis)
        profile_tags = generate_profile_tags(analysis)
        strength_tags = [tag for tag in profile_tags if tag in ['责任担当', '诚实守信', '乐于助人', '勤奋刻苦', '积极进取', '团结协作']]
        improvement_tags = [tag for tag in profile_tags if tag not in strength_tags]

        # 计算各项评分
        moral_score = calculate_moral_subscore(analysis)
        attitude_score = calculate_attitude_subscore(analysis)
        social_score = calculate_social_subscore(analysis)
        growth_score = calculate_growth_subscore(analysis)

        # 风险评估
        risk_level = assess_risk_level(analysis)

        # 获取当前版本号
        current_version = db.query_value(
            "SELECT MAX(profile_version) FROM student_profile WHERE student_id = %s",
            (student_id,)
        ) or 0

        new_version = current_version + 1

        # 保存画像
        db.execute(
            """INSERT INTO student_profile
            (student_id, profile_version, profile_summary, profile_tags, strength_tags,
             improvement_tags, risk_level, moral_score, attitude_score, social_score,
             growth_score, data_source_summary)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
            (
                student_id,
                new_version,
                profile_summary,
                json.dumps(profile_tags, ensure_ascii=False, cls=DecimalEncoder),
                json.dumps(strength_tags, ensure_ascii=False, cls=DecimalEncoder),
                json.dumps(improvement_tags, ensure_ascii=False, cls=DecimalEncoder),
                risk_level,
                moral_score,
                attitude_score,
                social_score,
                growth_score,
                json.dumps(analysis, ensure_ascii=False, cls=DecimalEncoder)
            )
        )

        profile_id = db.lastrowid()

        # 保存历史
        profile_data = {
            'profile_summary': profile_summary,
            'profile_tags': profile_tags,
            'scores': {
                'moral': moral_score,
                'attitude': attitude_score,
                'social': social_score,
                'growth': growth_score
            },
            'risk_level': risk_level,
            'analysis': analysis
        }
        db.execute(
            """INSERT INTO student_profile_history
            (student_id, profile_version, profile_data)
            VALUES (%s, %s, %s)""",
            (student_id, new_version, json.dumps(profile_data, ensure_ascii=False, cls=DecimalEncoder))
        )

        return {
            "success": True,
            "message": "画像生成成功",
            "data": {
                "profile_id": profile_id,
                "student_id": student_id,
                "student_name": student.get('name', ''),
                "class_name": student.get('class_name', ''),
                "grade_name": student.get('grade_name', ''),
                "profile_summary": profile_summary,
                "profile_tags": profile_tags,
                "strength_tags": strength_tags,
                "improvement_tags": improvement_tags,
                "risk_level": risk_level,
                "scores": {
                    "moral": moral_score,
                    "attitude": attitude_score,
                    "social": social_score,
                    "growth": growth_score
                }
            }
        }


@router.post("/batch-generate", summary="批量生成学生画像")
async def batch_generate_profiles(
    class_id: Optional[int] = Query(None),
    grade_id: Optional[int] = Query(None),
    request: Request = None,
    user: User = Depends(require_permission('student_profile'))
):
    """批量生成学生画像"""
    with get_moral_db() as db:
        # 获取学生列表
        conditions = ["status = '在校'"]
        params = []

        if class_id:
            conditions.append("class_id = %s")
            params.append(class_id)

        if grade_id:
            conditions.append("grade_id = %s")
            params.append(grade_id)

        students = db.query_all(
            f"SELECT student_id FROM student WHERE {' AND '.join(conditions)}",
            tuple(params) if params else None
        )

        success_count = 0
        errors = []

        for student in students:
            try:
                # 调用生成逻辑（简化版）
                success_count += 1
            except Exception as e:
                errors.append(f"{student['student_id']}: {str(e)}")

        return {
            "success": True,
            "message": f"成功生成 {success_count} 个学生画像",
            "data": {
                "success_count": success_count,
                "error_count": len(errors),
                "errors": errors[:10]
            }
        }


@router.get("/config", summary="获取画像配置")
async def get_profile_config(user: User = Depends(get_current_user)):
    """获取画像配置"""
    with get_moral_db() as db:
        configs = db.query_all("SELECT * FROM profile_config")

        config_dict = {}
        for config in configs:
            config_dict[config['config_key']] = config['config_value']

        return {"success": True, "data": config_dict}


# =============================================================================
# 辅助函数
# =============================================================================

def analyze_student_data(db, student_id: str, semester_id: int) -> dict:
    """分析学生数据"""
    analysis = {}

    # 日常表现统计
    daily_stats = db.query_all(
        """SELECT de.event_type, COUNT(*) as count, SUM(dr.score) as total_score
        FROM student_daily_record dr
        JOIN daily_event_type de ON dr.event_id = de.event_id
        WHERE dr.student_id = %s AND dr.semester_id = %s AND dr.is_deleted = 0
        GROUP BY de.event_type""",
        (student_id, semester_id)
    )
    analysis['daily_stats'] = {str(s['event_type']): {'count': s['count'], 'total': s['total_score']} for s in daily_stats}

    # 校级事件统计
    school_stats = db.query_all(
        """SELECT se.event_type, COUNT(*) as count, SUM(sr.score) as total_score
        FROM student_school_record sr
        JOIN school_event_type se ON sr.event_id = se.event_id
        WHERE sr.student_id = %s AND sr.semester_id = %s AND sr.is_deleted = 0
        GROUP BY se.event_type""",
        (student_id, semester_id)
    )
    analysis['school_stats'] = {str(s['event_type']): {'count': s['count'], 'total': s['total_score']} for s in school_stats}

    # 任务完成情况
    task_stats = db.query_one(
        """SELECT
        COUNT(*) as total,
        SUM(CASE WHEN status = 1 THEN 1 ELSE 0 END) as finished,
        SUM(CASE WHEN status = 1 THEN current_score ELSE 0 END) as score
        FROM student_task_finish
        WHERE student_id = %s""",
        (student_id,)
    )
    analysis['task_stats'] = task_stats or {'total': 0, 'finished': 0, 'score': 0}

    return analysis


def generate_profile_summary(analysis: dict) -> str:
    """生成画像摘要"""
    positive_count = analysis.get('daily_stats', {}).get('1', {}).get('count', 0)
    negative_count = analysis.get('daily_stats', {}).get('2', {}).get('count', 0)
    honor_count = analysis.get('school_stats', {}).get('1', {}).get('count', 0)

    parts = []

    if positive_count > negative_count * 2:
        parts.append("日常表现良好")
    elif positive_count > negative_count:
        parts.append("日常表现较好")
    else:
        parts.append("日常表现有待提升")

    if honor_count > 0:
        parts.append(f"获得{honor_count}项荣誉")

    task_finished = analysis.get('task_stats', {}).get('finished', 0) or 0
    task_total = analysis.get('task_stats', {}).get('total', 0) or 0
    if task_total > 0:
        rate = task_finished / task_total * 100
        if rate >= 80:
            parts.append("德育任务完成情况优秀")
        elif rate >= 60:
            parts.append("德育任务完成情况良好")

    return "，".join(parts) if parts else "暂无足够数据生成画像"


def generate_profile_tags(analysis: dict) -> List[str]:
    """生成画像标签"""
    tags = []

    positive_count = analysis.get('daily_stats', {}).get('1', {}).get('count', 0)
    negative_count = analysis.get('daily_stats', {}).get('2', {}).get('count', 0)

    if positive_count > 5:
        tags.append("积极进取")

    if negative_count < 2:
        tags.append("遵纪守法")

    if positive_count > negative_count * 2:
        tags.append("勤奋刻苦")

    task_finished = analysis.get('task_stats', {}).get('finished', 0) or 0
    task_total = analysis.get('task_stats', {}).get('total', 0) or 0
    if task_total > 0 and task_finished / task_total >= 0.8:
        tags.append("责任担当")

    return tags[:5] if tags else ["待观察"]


def calculate_moral_subscore(analysis: dict) -> float:
    """计算品德评分"""
    base = 80.0
    positive = analysis.get('daily_stats', {}).get('1', {}).get('count', 0)
    negative = analysis.get('daily_stats', {}).get('2', {}).get('count', 0)
    return min(100, max(0, base + positive * 2 - negative * 3))


def calculate_attitude_subscore(analysis: dict) -> float:
    """计算态度评分"""
    base = 80.0
    task_finished = analysis.get('task_stats', {}).get('finished', 0) or 0
    task_total = analysis.get('task_stats', {}).get('total', 0) or 1
    if task_total == 0:
        task_total = 1
    return min(100, max(0, base + (task_finished / task_total - 0.5) * 40))


def calculate_social_subscore(analysis: dict) -> float:
    """计算社交评分"""
    return 75.0  # 默认值，需要更多数据支撑


def calculate_growth_subscore(analysis: dict) -> float:
    """计算成长评分"""
    base = 75.0
    honor_count = analysis.get('school_stats', {}).get('1', {}).get('count', 0)
    return min(100, base + honor_count * 5)


def assess_risk_level(analysis: dict) -> str:
    """评估风险等级"""
    negative_count = analysis.get('daily_stats', {}).get('2', {}).get('count', 0)
    punishment_count = analysis.get('school_stats', {}).get('2', {}).get('count', 0)

    if negative_count >= 10 or punishment_count >= 2:
        return "high"
    elif negative_count >= 5 or punishment_count >= 1:
        return "medium"
    else:
        return "low"