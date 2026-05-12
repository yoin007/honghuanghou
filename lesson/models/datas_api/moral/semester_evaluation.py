# -*- coding: utf-8 -*-
"""
学期末德育评价生成 API

提供学期末德育评价的生成、查询和导出功能。
包含 AI 生成的学期末总结和建议。
"""

import json
import logging
import re
from datetime import datetime
from decimal import Decimal
from typing import Optional, Dict, Any, List

from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from pydantic import BaseModel, Field

from .base import (
    get_current_semester,
    get_record_data_scope,
    get_teacher_grade_ids,
    get_teacher_class_ids,
    is_class_leader,
    is_grade_leader,
    check_moral_permission_for_roles,
    get_api_scoped_user_roles,
    calculate_moral_level,
    get_moral_db,
)
from .evaluation import (
    calculate_evaluation,
    get_daily_statistics,
    get_school_statistics,
    get_task_statistics,
    get_collective_statistics,
    get_punishment_statistics,
    get_recent_evaluation_records,
)
from .ai_model_config import get_current_model
from models.datas_api.auth import User, get_current_user

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/semester-evaluations", tags=["学期末评价"])

# API 路径常量
API_GENERATE = "/api/moral/semester-evaluations/generate"
API_BATCH_GENERATE = "/api/moral/semester-evaluations/batch-generate"
API_LIST = "/api/moral/semester-evaluations/list"


# =============================================================================
# 权限检查函数
# =============================================================================

def _has_generate_permission(db, user: User, student_id: str = None) -> bool:
    """检查是否具有生成权限（配置驱动，支持多角色）"""
    scoped_roles = get_api_scoped_user_roles(db, user, API_GENERATE)

    # admin/xuefa 有全部权限
    if check_moral_permission_for_roles(scoped_roles, 'moral_record_manage'):
        return True

    # g_leader 只能操作本年级学生
    if 'g_leader' in scoped_roles:
        if student_id:
            student = db.query_one("SELECT grade_id FROM student WHERE student_id = ?", (student_id,))
            if student:
                my_grade_ids = get_teacher_grade_ids(user, db)
                return student['grade_id'] in my_grade_ids
        return False

    # cleader 只能操作本班学生
    if 'cleader' in scoped_roles:
        if student_id:
            student = db.query_one("SELECT class_id FROM student WHERE student_id = ?", (student_id,))
            if student:
                return is_class_leader(user, student['class_id'], db)
        return False

    return False


def _check_batch_permission(db, user: User, class_id: int = None, grade_id: int = None) -> bool:
    """检查批量生成权限和数据范围"""
    scoped_roles = get_api_scoped_user_roles(db, user, API_BATCH_GENERATE)

    # admin/xuefa 有全部权限
    if check_moral_permission_for_roles(scoped_roles, 'moral_record_manage'):
        return True

    # g_leader 只能操作本年级
    if 'g_leader' in scoped_roles:
        if grade_id:
            my_grade_ids = get_teacher_grade_ids(user, db)
            return grade_id in my_grade_ids
        return False

    # cleader 只能操作本班
    if 'cleader' in scoped_roles:
        if class_id:
            return is_class_leader(user, class_id, db)
        return False

    return False


# =============================================================================
# AI 总结生成函数
# =============================================================================

def build_evaluation_system_prompt() -> str:
    """构建 System Prompt"""
    return """你是学校德育评价助手，擅长基于真实德育数据为学生生成具有教育温度、真实客观的学期末德育成长总结。

你的输出将直接用于学校正式德育评价场景，需要体现：
- 语言积极、客观、真实，避免空泛套话
- 注重鼓励与成长引导
- 对存在的问题以"成长建议"方式委婉表达
- 字数控制在300~600字
- 不同学生生成内容应有明显差异化，体现数据支撑下的个性化评价"""


def build_evaluation_user_prompt(
    student: dict,
    semester: dict,
    evaluation: dict,
    details: dict,
    events: list
) -> str:
    """构建 User Prompt（合并优化版）"""

    # 格式化关键事件表格
    events_table = ""
    if events:
        events_table = "| 日期 | 类型 | 事件 | 分值 |\n|------|------|------|------|\n"
        for e in events[:8]:
            events_table += f"| {e.get('date', '')} | {e.get('type', '')} | {e.get('title', '')} | {e.get('score', 0)} |\n"

    return f"""请根据以下《学期末德育评价报告》中的数据内容，为学生生成一份完整、真实、具有教育温度的"学期德育成长总结"。

【学生信息】
姓名：{student.get('name', '')}
班级：{student.get('class_name', '')}
年级：{student.get('grade_name', '')}
学期：{semester.get('semester_name', '')}

【评价结果】
德育总分：{evaluation.get('total_score', 0)}分
评价等级：{evaluation.get('level', '')}

【分项得分】
| 分项 | 得分 | 说明 |
| 日常表现分 | {evaluation.get('daily_score', 0)}分 | 正向{details.get('positive_count', 0)}次/{details.get('positive_total', 0)}分，需改进{details.get('negative_count', 0)}次/{details.get('negative_total', 0)}分 |
| 校级事件分 | {evaluation.get('school_score', 0)}分 | 荣誉{details.get('honor_count', 0)}次 |
| 任务完成分 | {evaluation.get('task_score', 0)}分 | 完成率{details.get('task_completion_rate', 0)*100:.0f}% |
| 集体事件分 | {evaluation.get('collective_score', 0)}分 | 参与{details.get('collective_count', 0)}次 |
| 处分扣分 | {evaluation.get('punishment_score', 0)}分 | {details.get('punishment_count', 0)}条 |

【近期关键事件】（最近8条）
{events_table}

【输出要求】
请严格按照以下结构生成（JSON格式）：
{{
  "summary": "【学生学期德育总结】综合评价（300字内）。重点体现：思想品德与行为习惯、学习态度与责任意识、集体参与与团队精神、自律意识与规则意识、成长进步与亮点表现。",
  "strengths": "【优势与亮点】2~3项最突出的优点（150字内）。",
  "improvements": "【需提升方向】以鼓励成长为主，不使用否定批评语言（150字内）。",
  "suggestions": {{
    "student": "【学生个人成长建议】",
    "teacher": "【班主任教育建议】",
    "parent": "【家长家庭教育建议】"
  }}
}}

【生成逻辑】
- 德育总分较高、正向记录较多时，侧重表扬与激励
- 存在违纪、处分或负向记录时，客观分析问题，同时突出成长空间
- 任务完成率较低时，体现执行力与时间管理建议
- 集体活动参与较多时，体现团队意识与责任感
- 有校级荣誉时，体现榜样作用与综合素养

【语言风格】
- 符合高中学校正式德育评价场景
- 语言积极、客观、真实，避免空泛套话
- 不要简单复述数据，不要逐项罗列分数
- 形成自然连贯的评价文字"""


def call_ai_for_evaluation(prompt: str, system_prompt: str) -> dict:
    """调用大模型生成学期末评价总结"""
    from openai import OpenAI
    from config.config import Config

    try:
        client = OpenAI(
            api_key=Config().get_config("bailian_token", "token.yaml"),
            base_url="https://coding.dashscope.aliyuncs.com/v1",
            timeout=60,  # 增加超时时间
        )
        completion = client.chat.completions.create(
            model=get_current_model('semester_evaluation'),
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt},
            ],
            temperature=0.3,
            max_tokens=1500,
        )
        content = completion.choices[0].message.content.strip()
        logger.debug(f"AI raw response: {content[:200]}")

        # 解析 JSON 返回 - 增强容错
        # 1. 清理markdown代码块
        if content.startswith("```"):
            content = content.strip("`").strip()
            if content.startswith("json"):
                content = content[4:].strip()

        # 2. 提取JSON部分
        if not content.startswith("{"):
            start = content.find("{")
            end = content.rfind("}")
            if start >= 0 and end > start:
                content = content[start:end + 1]

        # 3. 清理常见格式问题
        content = content.replace('\n', '')  # 移除换行
        content = re.sub(r',\s*}', '}', content)  # 移除末尾多余逗号
        content = re.sub(r'}\s*"', '},"', content)  # 修复缺少逗号

        # 4. 解析JSON
        parsed = json.loads(content)

        # 5. 检测并处理嵌套JSON（模型可能把整个JSON作为summary字段值）
        if isinstance(parsed.get('summary'), str) and parsed.get('summary', '').startswith('{'):
            # summary 字段是嵌套的JSON字符串，需要二次解析
            try:
                inner_parsed = json.loads(parsed['summary'])
                if isinstance(inner_parsed, dict):
                    parsed = inner_parsed  # 使用嵌套的内容作为正确结构
                    logger.info("检测到嵌套JSON，已自动提取正确内容")
            except json.JSONDecodeError:
                pass  # 保持原样

        return {
            'summary': parsed.get('summary', ''),
            'strengths': parsed.get('strengths', ''),
            'improvements': parsed.get('improvements', ''),
            'suggestions': parsed.get('suggestions', {}),
        }

    except json.JSONDecodeError as e:
        logger.error(f"AI JSON解析失败: {e}, raw content: {content[:500] if 'content' in dir() else 'N/A'}")

        # JSON解析失败时，用正则提取各字段
        def extract_field_with_regex(text, field_name):
            """用正则提取JSON字段值"""
            pattern = '"' + field_name + '"\\s*:\\s*"((?:[^"\\\\]|\\\\.|[^"])*?)"'
            match = re.search(pattern, text)
            if match:
                # 解码转义引号
                value = match.group(1)
                value = value.replace('\\"', '"')
                value = value.replace('\\n', '\n')
                return value.strip()
            return ''

        def extract_suggestions(text):
            """提取suggestions对象"""
            result = {}
            for sub in ['student', 'teacher', 'parent']:
                result[sub] = extract_field_with_regex(text, sub)
            return result

        # 用正则提取各字段
        summary = extract_field_with_regex(content, 'summary')
        strengths = extract_field_with_regex(content, 'strengths')
        improvements = extract_field_with_regex(content, 'improvements')
        suggestions = extract_suggestions(content)

        # 如果正则提取失败，才fallback到原始内容
        if not summary:
            summary = content if 'content' in dir() and content else 'AI返回内容解析失败'

        logger.info(f"正则提取结果: summary={len(summary)}, strengths={len(strengths)}, improvements={len(improvements)}")

        return {
            'summary': summary,
            'strengths': strengths,
            'improvements': improvements,
            'suggestions': suggestions,
        }
    except Exception as e:
        logger.error(f"AI 总结生成失败: {e}")
        return {
            'summary': 'AI 总结生成失败，请稍后重试。',
            'strengths': '',
            'improvements': '',
            'suggestions': {},
            'error': str(e)
        }


# =============================================================================
# 核心生成函数
# =============================================================================

def get_evaluation_details(db, student_id: str, semester_id: int) -> dict:
    """获取评价详情统计"""
    daily_stats = get_daily_statistics(db, student_id, semester_id)
    school_stats = get_school_statistics(db, student_id, semester_id)
    task_stats = get_task_statistics(db, student_id, semester_id)
    collective_stats = get_collective_statistics(db, student_id, semester_id)
    punishment_stats = get_punishment_statistics(db, student_id, semester_id)

    return {
        'positive_count': daily_stats.get('positive', {}).get('count', 0),
        'positive_total': daily_stats.get('positive', {}).get('total', 0),
        'negative_count': daily_stats.get('negative', {}).get('count', 0),
        'negative_total': daily_stats.get('negative', {}).get('total', 0),
        'honor_count': school_stats.get('honor', {}).get('count', 0),
        'punishment_count': punishment_stats.get('count', 0),
        'task_completion_rate': task_stats.get('completion_rate', 0),
        'collective_count': collective_stats.get('count', 0),
    }


def format_events_for_prompt(db, student_id: str, semester_id: int) -> list:
    """格式化关键事件用于 Prompt"""
    records = get_recent_evaluation_records(db, student_id, semester_id)

    events = []
    for record in records.get('daily_records', [])[:4]:
        events.append({
            'date': record.get('date', ''),
            'type': '日常表现',
            'title': record.get('title', ''),
            'score': record.get('score', 0),
        })

    for record in records.get('school_records', [])[:2]:
        events.append({
            'date': record.get('date', ''),
            'type': '校级事件',
            'title': record.get('title', ''),
            'score': record.get('score', 0),
        })

    for record in records.get('punishment_records', [])[:2]:
        events.append({
            'date': record.get('date', ''),
            'type': '处分',
            'title': record.get('title', ''),
            'score': -abs(record.get('score', 0)),  # 处分扣分显示负数
        })

    # 按日期排序
    events.sort(key=lambda x: x.get('date', ''), reverse=True)
    return events[:8]


def generate_semester_evaluation_with_ai(
    db,
    student_id: str,
    semester_id: int,
    user: User,
    generate_ai: bool = True
) -> dict:
    """
    生成学期末评价（包含 AI 总结）

    Args:
        db: 数据库连接
        student_id: 学生ID
        semester_id: 学期ID
        user: 当前用户
        generate_ai: 是否生成 AI 总结

    Returns:
        评价结果字典
    """
    # 1. 获取学生信息
    student = db.query_one(
        """SELECT s.*, c.class_name, g.grade_name
        FROM student s
        LEFT JOIN class c ON s.class_id = c.class_id
        LEFT JOIN grade g ON s.grade_id = g.grade_id
        WHERE s.student_id = ?""",
        (student_id,)
    )
    if not student:
        raise ValueError(f"学生不存在: {student_id}")

    # 2. 获取学期信息
    semester = db.query_one(
        "SELECT * FROM semester WHERE semester_id = ?",
        (semester_id,)
    )
    if not semester:
        raise ValueError(f"学期不存在: {semester_id}")

    # 3. 计算评价（复用现有函数）
    evaluation = calculate_evaluation(
        db, student_id, semester_id,
        student.get('class_id'), student.get('grade_id')
    )

    # 4. 获取详细数据和关键事件
    details = get_evaluation_details(db, student_id, semester_id)
    events = format_events_for_prompt(db, student_id, semester_id)

    # 5. AI 总结生成
    ai_summary = None
    ai_generated_at = None
    if generate_ai:
        system_prompt = build_evaluation_system_prompt()
        user_prompt = build_evaluation_user_prompt(student, semester, evaluation, details, events)
        ai_summary = call_ai_for_evaluation(user_prompt, system_prompt)
        ai_generated_at = datetime.now().isoformat()

    # 6. 保存评价记录
    existing = db.query_one(
        "SELECT record_id FROM semester_evaluation_record WHERE student_id = ? AND semester_id = ?",
        (student_id, semester_id)
    )

    record_data = {
        'student_id': student_id,
        'semester_id': semester_id,
        'class_id': student.get('class_id'),
        'grade_id': student.get('grade_id'),
        'total_score': evaluation.get('total_score'),
        'level': evaluation.get('level'),
        'score_details': json.dumps(evaluation, ensure_ascii=False),
        'statistics': json.dumps(details, ensure_ascii=False),
        'key_events': json.dumps(events, ensure_ascii=False),
        'ai_summary': json.dumps(ai_summary, ensure_ascii=False) if ai_summary else None,
        'generated_by': user.username,
        'generated_at': datetime.now().isoformat(),
        'ai_generated_at': ai_generated_at,
    }

    if existing:
        db.execute(
            """UPDATE semester_evaluation_record SET
            total_score = ?, level = ?, score_details = ?, statistics = ?,
            key_events = ?, ai_summary = ?, generated_by = ?, generated_at = ?,
            ai_generated_at = ?
            WHERE record_id = ?""",
            (
                record_data['total_score'], record_data['level'],
                record_data['score_details'], record_data['statistics'],
                record_data['key_events'], record_data['ai_summary'],
                record_data['generated_by'], record_data['generated_at'],
                record_data['ai_generated_at'],
                existing['record_id']
            )
        )
    else:
        db.execute(
            """INSERT INTO semester_evaluation_record
            (student_id, semester_id, class_id, grade_id, total_score, level,
             score_details, statistics, key_events, ai_summary, generated_by,
             generated_at, ai_generated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                record_data['student_id'], record_data['semester_id'],
                record_data['class_id'], record_data['grade_id'],
                record_data['total_score'], record_data['level'],
                record_data['score_details'], record_data['statistics'],
                record_data['key_events'], record_data['ai_summary'],
                record_data['generated_by'], record_data['generated_at'],
                record_data['ai_generated_at']
            )
        )

    return {
        'student': {
            'student_id': student.get('student_id'),
            'name': student.get('name'),
            'class_name': student.get('class_name'),
            'grade_name': student.get('grade_name'),
        },
        'semester': {
            'semester_id': semester.get('semester_id'),
            'semester_name': semester.get('semester_name'),
        },
        'evaluation': evaluation,
        'details': details,
        'key_events': events,
        'ai_summary': ai_summary,
        'generated_at': record_data['generated_at'],
    }


# =============================================================================
# API 端点
# =============================================================================

@router.post("/generate", summary="生成单学生学期末评价")
async def api_generate_semester_evaluation(
    student_id: str = Query(..., description="学生ID"),
    semester_id: Optional[int] = Query(None, description="学期ID（默认当前学期）"),
    generate_ai: bool = Query(True, description="是否生成AI总结"),
    user: User = Depends(get_current_user)
):
    """
    生成单个学生的学期末德育评价报告。

    权限要求：
    - admin/xuefa：全部学生
    - g_leader：仅本年级学生
    - cleader：仅本班学生
    """
    with get_moral_db() as db:
        if not _has_generate_permission(db, user, student_id):
            raise HTTPException(403, "权限不足：只能为授权范围内的学生生成评价")

        # 获取当前学期
        if not semester_id:
            current_semester = get_current_semester(db)
            if not current_semester:
                raise HTTPException(400, "未设置当前学期")
            semester_id = current_semester['semester_id']

        try:
            result = generate_semester_evaluation_with_ai(
                db, student_id, semester_id, user, generate_ai
            )
            return {"success": True, "message": "评价生成成功", "data": result}

        except ValueError as e:
            raise HTTPException(404, str(e))
        except Exception as e:
            logger.exception(f"学期末评价生成失败: {e}")
            raise HTTPException(500, f"生成失败: {str(e)}")


@router.post("/batch-generate", summary="批量生成学期末评价")
async def api_batch_generate_semester_evaluations(
    class_id: Optional[int] = Query(None, description="班级ID"),
    grade_id: Optional[int] = Query(None, description="年级ID"),
    semester_id: Optional[int] = Query(None, description="学期ID"),
    generate_ai: bool = Query(True, description="是否生成AI总结"),
    user: User = Depends(get_current_user)
):
    """
    批量生成学期末德育评价。

    权限要求：
    - admin/xuefa：全部数据
    - g_leader：仅本年级
    - cleader：仅本班
    """
    with get_moral_db() as db:
        # 权限检查
        if not _check_batch_permission(db, user, class_id, grade_id):
            raise HTTPException(403, "权限不足或超出数据范围")

        # 获取当前学期
        if not semester_id:
            current_semester = get_current_semester(db)
            if not current_semester:
                raise HTTPException(400, "未设置当前学期")
            semester_id = current_semester['semester_id']

        # 获取目标学生
        conditions = ["status = '在校'"]
        params = []

        if class_id:
            conditions.append("class_id = ?")
            params.append(class_id)
        elif grade_id:
            conditions.append("grade_id = ?")
            params.append(grade_id)

        # 数据范围过滤
        scope = get_record_data_scope(
            db, user, API_BATCH_GENERATE,
            all_permissions=['moral_record_manage'],
            own_class_permissions=['moral_record_own_class'],
            own_permissions=[]
        )

        if not scope.get('can_all'):
            if scope.get('can_own_grade'):
                grade_class_ids = scope.get('my_grade_class_ids', [])
                if grade_class_ids:
                    conditions.append(f"class_id IN ({','.join(map(str, grade_class_ids))})")
            elif scope.get('can_own_class'):
                conditions.append("class_id = ?")
                params.append(scope.get('my_class_id'))

        students = db.query_all(
            f"SELECT student_id FROM student WHERE {' AND '.join(conditions)}",
            tuple(params) if params else None
        )

        if not students:
            return {
                "success": True,
                "message": "没有需要生成的学生",
                "data": {"success_count": 0, "error_count": 0, "errors": []}
            }

        # 批量生成
        success_count = 0
        errors = []
        results = []

        for student in students:
            try:
                result = generate_semester_evaluation_with_ai(
                    db, student['student_id'], semester_id, user, generate_ai
                )
                success_count += 1
                results.append(result)
            except Exception as e:
                errors.append(f"{student['student_id']}: {str(e)}")
                logger.error(f"批量生成失败: {errors[-1]}")

        return {
            "success": True,
            "message": f"成功生成 {success_count} 个评价，失败 {len(errors)} 个",
            "data": {
                "success_count": success_count,
                "error_count": len(errors),
                "total_count": len(students),
                "errors": errors[:10],
                "evaluations": results[:20],
            }
        }


@router.get("/list", summary="查询学期末评价列表")
async def api_get_semester_evaluation_list(
    class_id: Optional[int] = Query(None),
    grade_id: Optional[int] = Query(None),
    semester_id: Optional[int] = Query(None),
    page: int = Query(1, ge=1),
    pageSize: int = Query(20, ge=1, le=100),
    user: User = Depends(get_current_user)
):
    """查询学期末评价记录列表"""
    with get_moral_db() as db:
        # 获取当前学期
        if not semester_id:
            current_semester = get_current_semester(db)
            semester_id = current_semester['semester_id'] if current_semester else None

        # 构建查询条件
        conditions = ["ser.semester_id = ?"]
        params = [semester_id]

        if class_id:
            conditions.append("ser.class_id = ?")
            params.append(class_id)
        elif grade_id:
            conditions.append("ser.grade_id = ?")
            params.append(grade_id)

        # 数据范围过滤
        scope = get_record_data_scope(db, user, API_LIST,
            all_permissions=['moral_record_manage'],
            own_class_permissions=['moral_record_own_class'],
            own_permissions=[]
        )

        if not scope.get('can_all'):
            if scope.get('can_own_grade'):
                grade_class_ids = scope.get('my_grade_class_ids', [])
                if grade_class_ids:
                    conditions.append(f"ser.class_id IN ({','.join(map(str, grade_class_ids))})")
            elif scope.get('can_own_class'):
                conditions.append("ser.class_id = ?")
                params.append(scope.get('my_class_id'))

        # 分页查询
        offset = (page - 1) * pageSize
        records = db.query_all(
            f"""SELECT ser.record_id, ser.student_id, s.name, c.class_name,
               ser.total_score, ser.level, ser.generated_at, ser.generated_by,
               ser.ai_generated_at
            FROM semester_evaluation_record ser
            JOIN student s ON ser.student_id = s.student_id
            LEFT JOIN class c ON ser.class_id = c.class_id
            WHERE {' AND '.join(conditions)}
            ORDER BY ser.generated_at DESC
            LIMIT ? OFFSET ?""",
            tuple(params) + (pageSize, offset)
        )

        # 总数
        total = db.query_value(
            f"""SELECT COUNT(*) FROM semester_evaluation_record ser
            WHERE {' AND '.join(conditions)}""",
            tuple(params)
        )

        return {
            "success": True,
            "data": {
                "list": records,
                "total": total,
                "page": page,
                "pageSize": pageSize,
            }
        }


@router.get("/{record_id}", summary="获取学期末评价详情")
async def api_get_semester_evaluation_detail(
    record_id: int,
    user: User = Depends(get_current_user)
):
    """获取单个学期末评价记录详情"""
    with get_moral_db() as db:
        record = db.query_one(
            """SELECT ser.*, s.name, s.gender, c.class_name, g.grade_name, sem.semester_name
            FROM semester_evaluation_record ser
            JOIN student s ON ser.student_id = s.student_id
            LEFT JOIN class c ON ser.class_id = c.class_id
            LEFT JOIN grade g ON ser.grade_id = g.grade_id
            LEFT JOIN semester sem ON ser.semester_id = sem.semester_id
            WHERE ser.record_id = ?""",
            (record_id,)
        )

        if not record:
            raise HTTPException(404, "评价记录不存在")

        # 解析 JSON 字段
        result = dict(record)
        result['score_details'] = json.loads(record.get('score_details') or '{}')
        result['statistics'] = json.loads(record.get('statistics') or '{}')
        result['key_events'] = json.loads(record.get('key_events') or '[]')
        result['ai_summary'] = json.loads(record.get('ai_summary') or '{}') if record.get('ai_summary') else None

        return {"success": True, "data": result}