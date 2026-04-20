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
            """SELECT id, profile_version, created_at,
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
        # 获取学生信息（包含班级和年级名称）
        student = db.query_one(
            """SELECT s.*, c.class_name, g.grade_name
            FROM student s
            LEFT JOIN class c ON s.class_id = c.class_id
            LEFT JOIN grade g ON s.grade_id = g.grade_id
            WHERE s.student_id = %s""",
            (student_id,)
        )
        if not student:
            raise HTTPException(404, "学生不存在")

        current_semester = get_current_semester(db)
        semester_id = current_semester['semester_id'] if current_semester else None

        # 分析学生数据
        analysis = analyze_student_data(db, student_id, semester_id)

        # 获取配置
        config = get_all_profile_config(db)

        # 生成画像
        profile_summary = generate_profile_summary(analysis)
        profile_tags = generate_profile_tags(analysis, config.get('tag_rules', {}))
        strength_tags = [tag for tag in profile_tags if tag in ['责任担当', '诚实守信', '乐于助人', '勤奋刻苦', '积极进取', '团结协作', '文明礼貌']]
        improvement_tags = [tag for tag in profile_tags if tag not in strength_tags]

        # 计算各项评分（使用配置）
        moral_score = calculate_moral_subscore(analysis, config.get('scoring_weights', {}).get('moral', {}))
        attitude_score = calculate_attitude_subscore(analysis, config.get('scoring_weights', {}).get('attitude', {}))
        social_score = calculate_social_subscore(analysis, config.get('scoring_weights', {}).get('social', {}))
        growth_score = calculate_growth_subscore(analysis, config.get('scoring_weights', {}).get('growth', {}))

        # 风险评估
        risk_level = assess_risk_level(analysis, config.get('risk_thresholds', {}))

        # 生成个性化建议
        suggestions = generate_suggestions(analysis, risk_level)

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
             growth_score, suggestions, data_source_summary)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
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
                suggestions,
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
            'suggestions': suggestions,
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
                "suggestions": suggestions,
                "scores": {
                    "moral": moral_score,
                    "attitude": attitude_score,
                    "social": social_score,
                    "growth": growth_score
                }
            }
        }


def generate_single_profile_internal(db, student_id: str, semester_id: int) -> dict:
    """
    单个学生画像生成的内部函数（用于批量生成）

    Args:
        db: 数据库连接
        student_id: 学生ID
        semester_id: 学期ID

    Returns:
        dict: 生成结果
    """
    # 获取学生信息
    student = db.query_one(
        """SELECT s.*, c.class_name, g.grade_name
        FROM student s
        LEFT JOIN class c ON s.class_id = c.class_id
        LEFT JOIN grade g ON s.grade_id = g.grade_id
        WHERE s.student_id = %s""",
        (student_id,)
    )
    if not student:
        raise ValueError(f"学生不存在: {student_id}")

    # 分析学生数据
    analysis = analyze_student_data(db, student_id, semester_id)

    # 获取配置
    config = get_all_profile_config(db)

    # 生成画像
    profile_summary = generate_profile_summary(analysis)
    profile_tags = generate_profile_tags(analysis, config.get('tag_rules', {}))
    strength_tags = [tag for tag in profile_tags if tag in ['责任担当', '诚实守信', '乐于助人', '勤奋刻苦', '积极进取', '团结协作', '文明礼貌']]
    improvement_tags = [tag for tag in profile_tags if tag not in strength_tags]

    # 计算各项评分（使用配置）
    moral_score = calculate_moral_subscore(analysis, config.get('scoring_weights', {}).get('moral', {}))
    attitude_score = calculate_attitude_subscore(analysis, config.get('scoring_weights', {}).get('attitude', {}))
    social_score = calculate_social_subscore(analysis, config.get('scoring_weights', {}).get('social', {}))
    growth_score = calculate_growth_subscore(analysis, config.get('scoring_weights', {}).get('growth', {}))

    # 风险评估
    risk_level = assess_risk_level(analysis, config.get('risk_thresholds', {}))

    # 生成个性化建议
    suggestions = generate_suggestions(analysis, risk_level)

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
         growth_score, suggestions, data_source_summary)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
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
            suggestions,
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
        'suggestions': suggestions,
        'analysis': analysis
    }
    db.execute(
        """INSERT INTO student_profile_history
        (student_id, profile_version, profile_data)
        VALUES (%s, %s, %s)""",
        (student_id, new_version, json.dumps(profile_data, ensure_ascii=False, cls=DecimalEncoder))
    )

    return {
        "profile_id": profile_id,
        "student_id": student_id,
        "student_name": student.get('name', ''),
        "class_name": student.get('class_name', ''),
        "grade_name": student.get('grade_name', ''),
        "risk_level": risk_level,
        "scores": {
            "moral": moral_score,
            "attitude": attitude_score,
            "social": social_score,
            "growth": growth_score
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
        # 获取当前学期
        current_semester = get_current_semester(db)
        semester_id = current_semester['semester_id'] if current_semester else None

        if not semester_id:
            raise HTTPException(400, "无法获取当前学期信息")

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
            f"SELECT student_id, name FROM student WHERE {' AND '.join(conditions)}",
            tuple(params) if params else None
        )

        if not students:
            return {
                "success": True,
                "message": "没有找到需要生成画像的学生",
                "data": {
                    "success_count": 0,
                    "error_count": 0,
                    "errors": []
                }
            }

        success_count = 0
        errors = []
        generated_profiles = []

        for student in students:
            try:
                # 调用单人生成逻辑
                result = generate_single_profile_internal(db, student['student_id'], semester_id)
                success_count += 1
                generated_profiles.append(result)
            except Exception as e:
                error_msg = f"{student['student_id']}({student['name']}): {str(e)}"
                errors.append(error_msg)
                logger.error(f"批量生成画像失败: {error_msg}")

        return {
            "success": True,
            "message": f"成功生成 {success_count} 个学生画像，失败 {len(errors)} 个",
            "data": {
                "success_count": success_count,
                "error_count": len(errors),
                "total_count": len(students),
                "errors": errors[:10],
                "generated_profiles": generated_profiles[:20]  # 返回前20个成功结果
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
# 配置管理
# =============================================================================

# 默认配置（当数据库无配置时使用）
DEFAULT_CONFIG = {
    "scoring_weights": {
        "moral": {"base": 80, "positive_weight": 2, "negative_weight": 3},
        "attitude": {"base": 80, "completion_weight": 40},
        "social": {"base": 75, "collective_weight": 2},
        "growth": {"base": 75, "honor_weight": 5}
    },
    "tag_rules": {
        "积极进取": {"positive_count_min": 5},
        "遵纪守法": {"negative_count_max": 2},
        "勤奋刻苦": {"positive_negative_ratio_min": 2},
        "责任担当": {"task_completion_rate_min": 0.8},
        "诚实守信": {"negative_count_max": 0},
        "乐于助人": {"collective_count_min": 3},
        "团结协作": {"collective_count_min": 5},
        "文明礼貌": {"positive_rate_min": 0.8}
    },
    "risk_thresholds": {
        "high": {"negative_count": 10, "punishment_count": 2},
        "medium": {"negative_count": 5, "punishment_count": 1}
    }
}


def get_profile_config_value(db, key: str, default=None) -> dict:
    """获取画像配置参数"""
    try:
        config = db.query_one(
            "SELECT config_value FROM profile_config WHERE config_key = ?",
            (key,)
        )
        if config:
            return json.loads(config['config_value'])
        return default if default is not None else DEFAULT_CONFIG.get(key, {})
    except Exception as e:
        logger.warning(f"获取配置失败: {key}, {str(e)}")
        return default if default is not None else DEFAULT_CONFIG.get(key, {})


def get_all_profile_config(db) -> dict:
    """获取所有画像配置"""
    config = DEFAULT_CONFIG.copy()
    try:
        configs = db.query_all("SELECT config_key, config_value FROM profile_config")
        for row in configs:
            try:
                config[row['config_key']] = json.loads(row['config_value'])
            except json.JSONDecodeError:
                pass
    except Exception as e:
        logger.warning(f"获取配置失败: {str(e)}")
    return config


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

    # 集体活动参与统计（用于社交评分）
    collective_stats = db.query_one(
        """SELECT COUNT(*) as collective_count
        FROM collective_event_distribution d
        JOIN collective_event e ON d.event_id = e.event_id
        WHERE d.student_id = %s AND e.semester_id = %s""",
        (student_id, semester_id)
    )
    analysis['collective_stats'] = collective_stats or {'collective_count': 0}

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


def generate_profile_tags(analysis: dict, config: dict = None) -> List[str]:
    """生成画像标签（支持配置化规则）"""
    if config is None:
        config = DEFAULT_CONFIG['tag_rules']

    tags = []

    positive_count = analysis.get('daily_stats', {}).get('1', {}).get('count', 0) or 0
    negative_count = analysis.get('daily_stats', {}).get('2', {}).get('count', 0) or 0
    total_daily_count = positive_count + negative_count

    task_finished = analysis.get('task_stats', {}).get('finished', 0) or 0
    task_total = analysis.get('task_stats', {}).get('total', 0) or 0
    if task_total == 0:
        task_total = 1
    task_completion_rate = task_finished / task_total

    collective_count = analysis.get('collective_stats', {}).get('collective_count', 0) or 0

    # 计算正向事件比例（用于"文明礼貌"标签）
    positive_rate = positive_count / max(1, total_daily_count)

    # 积极进取：正向事件达到阈值
    rule = config.get('积极进取', {})
    if positive_count >= rule.get('positive_count_min', 5):
        tags.append("积极进取")

    # 遵纪守法：消极事件不超过阈值
    rule = config.get('遵纪守法', {})
    if negative_count <= rule.get('negative_count_max', 2):
        tags.append("遵纪守法")

    # 勤奋刻苦：正向/消极比例达到阈值
    rule = config.get('勤奋刻苦', {})
    ratio_min = rule.get('positive_negative_ratio_min', 2)
    if negative_count == 0 or (positive_count / max(1, negative_count)) >= ratio_min:
        tags.append("勤奋刻苦")

    # 责任担当：任务完成率达到阈值
    rule = config.get('责任担当', {})
    if task_completion_rate >= rule.get('task_completion_rate_min', 0.8):
        tags.append("责任担当")

    # 诚实守信：消极事件为0
    rule = config.get('诚实守信', {})
    if negative_count <= rule.get('negative_count_max', 0):
        tags.append("诚实守信")

    # 乐于助人：集体活动参与达到阈值
    rule = config.get('乐于助人', {})
    if collective_count >= rule.get('collective_count_min', 3):
        tags.append("乐于助人")

    # 团结协作：集体活动参与达到更高阈值
    rule = config.get('团结协作', {})
    if collective_count >= rule.get('collective_count_min', 5):
        tags.append("团结协作")

    # 文明礼貌：正向事件比例达到阈值
    rule = config.get('文明礼貌', {})
    if positive_rate >= rule.get('positive_rate_min', 0.8):
        tags.append("文明礼貌")

    return tags[:8] if tags else ["待观察"]


def calculate_moral_subscore(analysis: dict, config: dict = None) -> float:
    """计算品德评分（支持配置化权重）"""
    if config is None:
        config = DEFAULT_CONFIG['scoring_weights']['moral']

    base = float(config.get('base', 80))
    positive_weight = float(config.get('positive_weight', 2))
    negative_weight = float(config.get('negative_weight', 3))

    positive = analysis.get('daily_stats', {}).get('1', {}).get('count', 0) or 0
    negative = analysis.get('daily_stats', {}).get('2', {}).get('count', 0) or 0

    return min(100, max(0, base + positive * positive_weight - negative * negative_weight))


def calculate_attitude_subscore(analysis: dict, config: dict = None) -> float:
    """计算态度评分（支持配置化权重）"""
    if config is None:
        config = DEFAULT_CONFIG['scoring_weights']['attitude']

    base = float(config.get('base', 80))
    completion_weight = float(config.get('completion_weight', 40))

    task_finished = analysis.get('task_stats', {}).get('finished', 0) or 0
    task_total = analysis.get('task_stats', {}).get('total', 0) or 1
    if task_total == 0:
        task_total = 1

    completion_rate = task_finished / task_total
    return min(100, max(0, base + (completion_rate - 0.5) * completion_weight))


def calculate_social_subscore(analysis: dict, config: dict = None) -> float:
    """计算社交评分（基于集体活动参与）"""
    if config is None:
        config = DEFAULT_CONFIG['scoring_weights']['social']

    base = float(config.get('base', 75))
    collective_weight = float(config.get('collective_weight', 2))

    # 获取集体活动参与次数
    collective_count = analysis.get('collective_stats', {}).get('collective_count', 0) or 0

    # 计算社交评分：基础分 + 集体活动参与加分
    return min(100, max(0, base + collective_count * collective_weight))


def calculate_growth_subscore(analysis: dict, config: dict = None) -> float:
    """计算成长评分（支持配置化权重）"""
    if config is None:
        config = DEFAULT_CONFIG['scoring_weights']['growth']

    base = float(config.get('base', 75))
    honor_weight = float(config.get('honor_weight', 5))

    honor_count = analysis.get('school_stats', {}).get('1', {}).get('count', 0) or 0

    return min(100, max(0, base + honor_count * honor_weight))


def assess_risk_level(analysis: dict, config: dict = None) -> str:
    """评估风险等级（支持配置化阈值）"""
    if config is None:
        config = DEFAULT_CONFIG['risk_thresholds']

    negative_count = analysis.get('daily_stats', {}).get('2', {}).get('count', 0) or 0
    punishment_count = analysis.get('school_stats', {}).get('2', {}).get('count', 0) or 0

    # 高风险阈值
    high_threshold = config.get('high', {})
    high_negative = high_threshold.get('negative_count', 10)
    high_punishment = high_threshold.get('punishment_count', 2)

    # 中风险阈值
    medium_threshold = config.get('medium', {})
    medium_negative = medium_threshold.get('negative_count', 5)
    medium_punishment = medium_threshold.get('punishment_count', 1)

    if negative_count >= high_negative or punishment_count >= high_punishment:
        return "high"
    elif negative_count >= medium_negative or punishment_count >= medium_punishment:
        return "medium"
    else:
        return "low"


def generate_suggestions(analysis: dict, risk_level: str) -> str:
    """根据画像分析生成个性化建议"""
    suggestions = []

    # 根据消极事件数量
    negative_count = analysis.get('daily_stats', {}).get('2', {}).get('count', 0) or 0
    if negative_count > 10:
        suggestions.append("日常行为规范方面存在较多问题，建议加强纪律意识培养和行为矫正")
    elif negative_count > 5:
        suggestions.append("日常行为规范方面需要关注，建议加强自律意识培养")

    # 根据惩罚事件
    punishment_count = analysis.get('school_stats', {}).get('2', {}).get('count', 0) or 0
    if punishment_count >= 2:
        suggestions.append("存在校级违纪记录，建议进行深度教育和家校沟通")

    # 根据任务完成情况
    task_finished = analysis.get('task_stats', {}).get('finished', 0) or 0
    task_total = analysis.get('task_stats', {}).get('total', 0) or 1
    task_rate = task_finished / max(1, task_total)
    if task_rate < 0.4:
        suggestions.append("德育任务完成率较低，建议制定任务完成计划并定期督促")
    elif task_rate < 0.6:
        suggestions.append("德育任务完成情况需要关注，建议加强任务跟踪和督促")

    # 根据集体活动参与情况
    collective_count = analysis.get('collective_stats', {}).get('collective_count', 0) or 0
    if collective_count < 2:
        suggestions.append("集体活动参与较少，建议鼓励参与班级和校级活动，培养团队协作精神")

    # 根据荣誉获取情况
    honor_count = analysis.get('school_stats', {}).get('1', {}).get('count', 0) or 0
    positive_count = analysis.get('daily_stats', {}).get('1', {}).get('count', 0) or 0
    if honor_count == 0 and positive_count < 3:
        suggestions.append("正向表现记录较少，建议设置阶段性目标，激励积极行为")

    # 根据风险等级给出针对性建议
    if risk_level == "high":
        suggestions.append("建议启动重点关注机制，定期进行行为评估和家校沟通")
    elif risk_level == "medium":
        suggestions.append("建议加强日常观察和引导，预防问题进一步发展")

    # 如果表现良好，给出正面建议
    if not suggestions:
        positive_rate = positive_count / max(1, positive_count + negative_count)
        if positive_rate > 0.8 and collective_count >= 3:
            suggestions.append("表现优秀，继续保持良好习惯，可尝试担任班级职务发挥带头作用")
        else:
            suggestions.append("继续保持良好表现，争取在更多方面取得进步")

    return "；".join(suggestions) if suggestions else "继续保持良好表现"