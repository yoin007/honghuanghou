# -*- coding: utf-8 -*-
"""
学期末德育评价生成 API

提供学期末德育评价的生成、查询和导出功能。
包含 AI 生成的学期末总结和建议。
"""

import json
import logging
import re
import time
import uuid
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
    record_in_scope,
    target_student_in_scope,
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
from .api_permission import require_configured_api_permission
from models.datas_api.auth import User

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/semester-evaluations", tags=["学期末评价"])

# API 路径常量
API_GENERATE = "/api/moral/semester-evaluations/generate"
API_BATCH_GENERATE = "/api/moral/semester-evaluations/batch-generate"
API_BATCH_STATUS = "/api/moral/semester-evaluations/batch-status/{job_id}"
API_BATCH_LATEST = "/api/moral/semester-evaluations/batch-latest"
API_BATCH_CANCEL = "/api/moral/semester-evaluations/batch-cancel/{job_id}"
API_BATCH_DELETE = "/api/moral/semester-evaluations/batch-delete/{job_id}"
API_LIST = "/api/moral/semester-evaluations/list"
API_DETAIL = "/api/moral/semester-evaluations/{record_id}"
SEMESTER_EVALUATION_JOBS: Dict[str, Dict[str, Any]] = {}
SEMESTER_EVALUATION_JOB_TTL_SECONDS = 60 * 60
FINISHED_BATCH_JOB_STATUSES = {"success", "partial_success", "failed", "cancelled"}


def _cleanup_semester_evaluation_jobs() -> None:
    now = time.time()
    expired = [
        job_id for job_id, job in SEMESTER_EVALUATION_JOBS.items()
        if now - job.get('created_at', now) > SEMESTER_EVALUATION_JOB_TTL_SECONDS
    ]
    for job_id in expired:
        SEMESTER_EVALUATION_JOBS.pop(job_id, None)


def _ensure_batch_job_table(db) -> None:
    db.execute(
        """CREATE TABLE IF NOT EXISTS semester_evaluation_batch_job (
            job_id TEXT PRIMARY KEY,
            created_by TEXT NOT NULL,
            status TEXT NOT NULL,
            message TEXT,
            semester_id INTEGER,
            generate_ai INTEGER DEFAULT 1,
            total_count INTEGER DEFAULT 0,
            success_count INTEGER DEFAULT 0,
            error_count INTEGER DEFAULT 0,
            current INTEGER DEFAULT 0,
            current_student_id TEXT,
            current_student_name TEXT,
            cancel_requested INTEGER DEFAULT 0,
            errors TEXT DEFAULT '[]',
            created_at TEXT DEFAULT (datetime('now', 'localtime')),
            updated_at TEXT DEFAULT (datetime('now', 'localtime')),
            finished_at TEXT
        )"""
    )
    db.execute(
        "CREATE INDEX IF NOT EXISTS idx_semester_eval_batch_job_user_status ON semester_evaluation_batch_job(created_by, status, updated_at)"
    )
    columns = {row["name"] for row in db.query_all("PRAGMA table_info(semester_evaluation_batch_job)")}
    if "cancel_requested" not in columns:
        db.execute("ALTER TABLE semester_evaluation_batch_job ADD COLUMN cancel_requested INTEGER DEFAULT 0")


def _persist_batch_job(job: Dict[str, Any]) -> None:
    try:
        with get_moral_db() as db:
            _ensure_batch_job_table(db)
            db.execute(
                """INSERT INTO semester_evaluation_batch_job
                   (job_id, created_by, status, message, semester_id, generate_ai,
                    total_count, success_count, error_count, current,
                    current_student_id, current_student_name, cancel_requested, errors, finished_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                   ON CONFLICT(job_id) DO UPDATE SET
                    status = excluded.status,
                    message = excluded.message,
                    success_count = excluded.success_count,
                    error_count = excluded.error_count,
                    current = excluded.current,
                    current_student_id = excluded.current_student_id,
                    current_student_name = excluded.current_student_name,
                    cancel_requested = excluded.cancel_requested,
                    errors = excluded.errors,
                    finished_at = excluded.finished_at,
                    updated_at = datetime('now', 'localtime')""",
                (
                    job.get("job_id"),
                    job.get("created_by"),
                    job.get("status") or "queued",
                    job.get("message") or "",
                    job.get("semester_id"),
                    1 if job.get("generate_ai") else 0,
                    int(job.get("total_count") or 0),
                    int(job.get("success_count") or 0),
                    int(job.get("error_count") or 0),
                    int(job.get("current") or 0),
                    job.get("current_student_id"),
                    job.get("current_student_name"),
                    1 if job.get("cancel_requested") else 0,
                    json.dumps(job.get("errors") or [], ensure_ascii=False),
                    datetime.now().isoformat() if job.get("finished_at") else None,
                ),
            )
    except Exception as exc:
        logger.warning("持久化学期末评价批量任务状态失败: %s", exc)


def _batch_job_status_payload(job: Dict[str, Any]) -> Dict[str, Any]:
    total_count = int(job.get("total_count") or 0)
    current = int(job.get("current") or 0)
    progress = int(current * 100 / total_count) if total_count else 100
    return {
        "job_id": job.get("job_id"),
        "status": job.get("status"),
        "message": job.get("message"),
        "total_count": total_count,
        "success_count": int(job.get("success_count") or 0),
        "error_count": int(job.get("error_count") or 0),
        "current": current,
        "progress": min(progress, 100),
        "current_student_id": job.get("current_student_id"),
        "current_student_name": job.get("current_student_name"),
        "errors": job.get("errors") or [],
        "evaluations": job.get("evaluations") or [],
        "finished_at": job.get("finished_at"),
        "cancel_requested": bool(job.get("cancel_requested")),
    }


def _batch_job_row_payload(row: Dict[str, Any]) -> Dict[str, Any]:
    try:
        errors = json.loads(row.get("errors") or "[]")
    except Exception:
        errors = []
    return _batch_job_status_payload({
        "job_id": row.get("job_id"),
        "status": row.get("status"),
        "message": row.get("message"),
        "total_count": row.get("total_count"),
        "success_count": row.get("success_count"),
        "error_count": row.get("error_count"),
        "current": row.get("current"),
        "current_student_id": row.get("current_student_id"),
        "current_student_name": row.get("current_student_name"),
        "errors": errors,
        "finished_at": row.get("finished_at"),
        "cancel_requested": bool(row.get("cancel_requested")),
    })


def _mark_orphaned_cancel_requested_job_cancelled(db, row: Dict[str, Any]) -> Dict[str, Any]:
    if not row:
        return row
    if row.get("status") not in {"queued", "running"} or not row.get("cancel_requested"):
        return row
    if SEMESTER_EVALUATION_JOBS.get(row.get("job_id")):
        return row

    success_count = int(row.get("success_count") or 0)
    error_count = int(row.get("error_count") or 0)
    db.execute(
        """UPDATE semester_evaluation_batch_job
           SET status = 'cancelled',
               message = ?,
               current_student_id = NULL,
               current_student_name = NULL,
               finished_at = datetime('now', 'localtime'),
               updated_at = datetime('now', 'localtime')
           WHERE job_id = ?""",
        (f"批量生成已停止：成功 {success_count} 个，失败 {error_count} 个", row.get("job_id")),
    )
    return db.query_one(
        "SELECT * FROM semester_evaluation_batch_job WHERE job_id = ?",
        (row.get("job_id"),),
    )


def _run_semester_evaluation_batch_job(job_id: str) -> None:
    job = SEMESTER_EVALUATION_JOBS.get(job_id)
    if not job:
        return
    students = job.get('students') or []
    user = job.get('user')
    semester_id = job.get('semester_id')
    generate_ai = bool(job.get('generate_ai'))
    job.update({
        "status": "running",
        "message": "正在批量生成学期末评价",
        "started_at": time.time(),
    })
    _persist_batch_job(job)
    success_count = 0
    errors = []
    results = []
    try:
        for index, student in enumerate(students, start=1):
            if job.get("cancel_requested"):
                job.update({
                    "status": "cancelled",
                    "message": f"批量生成已停止：成功 {success_count} 个，失败 {len(errors)} 个",
                    "current_student_id": None,
                    "current_student_name": None,
                    "finished_at": time.time(),
                })
                _persist_batch_job(job)
                return
            job.update({
                "current": index,
                "current_student_id": student.get('student_id'),
                "current_student_name": student.get('name') or student.get('student_id'),
                "message": f"正在生成 {index}/{len(students)}",
            })
            _persist_batch_job(job)
            try:
                with get_moral_db() as db:
                    result = generate_semester_evaluation_with_ai(
                        db, student['student_id'], semester_id, user, generate_ai
                    )
                success_count += 1
                if len(results) < 20:
                    results.append(result)
            except Exception as exc:
                error_msg = f"{student.get('student_id')}: {str(exc)}"
                errors.append(error_msg)
                logger.error("批量生成学期末评价失败: %s", error_msg)
            job.update({
                "success_count": success_count,
                "error_count": len(errors),
                "errors": errors[:10],
                "evaluations": results,
            })
            _persist_batch_job(job)

        job.update({
            "status": "success" if not errors else "partial_success",
            "message": f"批量生成完成：成功 {success_count} 个，失败 {len(errors)} 个",
            "success_count": success_count,
            "error_count": len(errors),
            "errors": errors[:10],
            "evaluations": results,
            "finished_at": time.time(),
        })
        _persist_batch_job(job)
    except Exception as exc:
        logger.exception("学期末评价批量生成任务失败: %s", exc)
        job.update({
            "status": "failed",
            "message": str(exc) or "批量生成任务失败",
            "success_count": success_count,
            "error_count": len(errors) + 1,
            "errors": (errors + [str(exc)])[:10],
            "finished_at": time.time(),
        })
        _persist_batch_job(job)


# =============================================================================
# 权限检查函数
# =============================================================================

def _has_generate_permission(db, user: User, student_id: str = None) -> bool:
    """检查是否具有生成权限（配置驱动，支持多角色）"""
    if not student_id:
        return False
    student = db.query_one(
        "SELECT student_id, class_id, grade_id FROM student WHERE student_id = ?",
        (student_id,),
    )
    if not student:
        return False
    return target_student_in_scope(db, user, API_GENERATE, student)


def _check_batch_permission(db, user: User, class_id: int = None, grade_id: int = None) -> bool:
    """检查批量生成权限和数据范围"""
    scope = get_record_data_scope(
        db,
        user,
        API_BATCH_GENERATE,
        all_permissions=['moral_record_manage'],
        own_class_permissions=['moral_record_own_class'],
        own_permissions=[],
    )
    if scope.get('can_all'):
        return True

    if scope.get('can_own_grade'):
        if grade_id:
            return grade_id in get_teacher_grade_ids(user, db)
        if class_id:
            return class_id in (scope.get('my_grade_class_ids') or [])
        return False

    if scope.get('can_own_class'):
        if class_id:
            return class_id in (scope.get('my_class_ids') or [])
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
    # 先提交德育总评缓存，避免 AI 调用期间长时间持有 SQLite 写锁。
    if hasattr(db, "commit"):
        db.commit()

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
    user: User = Depends(require_configured_api_permission(API_GENERATE, "POST", allow_missing=False))
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
    background_tasks: BackgroundTasks,
    class_id: Optional[int] = Query(None, description="班级ID"),
    grade_id: Optional[int] = Query(None, description="年级ID"),
    semester_id: Optional[int] = Query(None, description="学期ID"),
    generate_ai: bool = Query(True, description="是否生成AI总结"),
    user: User = Depends(require_configured_api_permission(API_BATCH_GENERATE, "POST", allow_missing=False))
):
    """
    批量生成学期末德育评价。

    权限要求：
    - admin/xuefa：全部数据
    - g_leader：仅本年级
    - cleader：仅本班
    """
    with get_moral_db() as db:
        _cleanup_semester_evaluation_jobs()
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
                class_ids = scope.get('my_class_ids') or []
                if class_ids:
                    conditions.append(f"class_id IN ({','.join(map(str, class_ids))})")

        students = db.query_all(
            f"SELECT student_id FROM student WHERE {' AND '.join(conditions)}",
            tuple(params) if params else None
        )

        if not students:
            return {
                "success": True,
                "message": "没有需要生成的学生",
                "data": {"success_count": 0, "error_count": 0, "total_count": 0, "errors": []}
            }

        job_id = uuid.uuid4().hex
        SEMESTER_EVALUATION_JOBS[job_id] = {
            "job_id": job_id,
            "status": "queued",
            "message": "批量生成任务已提交",
            "created_by": user.username,
            "created_at": time.time(),
            "semester_id": semester_id,
            "generate_ai": generate_ai,
            "students": [dict(student) for student in students],
            "total_count": len(students),
            "success_count": 0,
            "error_count": 0,
            "current": 0,
            "errors": [],
            "evaluations": [],
            "user": user,
        }
        _ensure_batch_job_table(db)
        _persist_batch_job(SEMESTER_EVALUATION_JOBS[job_id])
        background_tasks.add_task(_run_semester_evaluation_batch_job, job_id)

        return {
            "success": True,
            "message": "批量生成任务已提交",
            "data": {
                "job_id": job_id,
                "status": "queued",
                "total_count": len(students),
                "success_count": 0,
                "error_count": 0,
                "errors": [],
            }
        }


@router.get("/batch-status/{job_id}", summary="查询学期末评价批量生成状态")
async def get_semester_evaluation_batch_status(
    job_id: str,
    user: User = Depends(require_configured_api_permission(API_BATCH_STATUS, "GET", allow_missing=False))
):
    _cleanup_semester_evaluation_jobs()
    job = SEMESTER_EVALUATION_JOBS.get(job_id)
    if not job:
        with get_moral_db() as db:
            _ensure_batch_job_table(db)
            row = db.query_one(
                "SELECT * FROM semester_evaluation_batch_job WHERE job_id = ?",
                (job_id,),
            )
        if not row:
            raise HTTPException(404, "批量生成任务不存在或已过期")
        if row.get("created_by") != user.username:
            raise HTTPException(403, "只能查看自己提交的批量生成任务")
        row = _mark_orphaned_cancel_requested_job_cancelled(db, row)
        return {"success": True, "data": _batch_job_row_payload(row)}
    if job.get("created_by") != user.username:
        raise HTTPException(403, "只能查看自己提交的批量生成任务")
    return {"success": True, "data": _batch_job_status_payload(job)}


@router.get("/batch-latest", summary="查询当前用户最近的学期末评价批量任务")
async def get_latest_semester_evaluation_batch_job(
    user: User = Depends(require_configured_api_permission(API_BATCH_LATEST, "GET", allow_missing=False))
):
    with get_moral_db() as db:
        _ensure_batch_job_table(db)
        row = db.query_one(
            """SELECT * FROM semester_evaluation_batch_job
               WHERE created_by = ?
               ORDER BY CASE status WHEN 'running' THEN 0 WHEN 'queued' THEN 1 ELSE 2 END,
                        updated_at DESC
               LIMIT 1""",
            (user.username,),
        )
        row = _mark_orphaned_cancel_requested_job_cancelled(db, row)
    return {"success": True, "data": _batch_job_row_payload(row) if row else None}


@router.post("/batch-cancel/{job_id}", summary="停止学期末评价批量生成")
async def cancel_semester_evaluation_batch_job(
    job_id: str,
    user: User = Depends(require_configured_api_permission(API_BATCH_CANCEL, "POST", allow_missing=False))
):
    _cleanup_semester_evaluation_jobs()
    job = SEMESTER_EVALUATION_JOBS.get(job_id)
    if job:
        if job.get("created_by") != user.username:
            raise HTTPException(403, "只能停止自己提交的批量生成任务")
        if job.get("status") in FINISHED_BATCH_JOB_STATUSES:
            return {"success": True, "message": "任务已结束", "data": _batch_job_status_payload(job)}
        job.update({
            "cancel_requested": True,
            "message": "已请求停止，当前学生处理完成后停止",
        })
        _persist_batch_job(job)
        return {"success": True, "message": "已请求停止批量生成", "data": _batch_job_status_payload(job)}

    with get_moral_db() as db:
        _ensure_batch_job_table(db)
        row = db.query_one(
            "SELECT * FROM semester_evaluation_batch_job WHERE job_id = ?",
            (job_id,),
        )
        if not row:
            raise HTTPException(404, "批量生成任务不存在或已过期")
        if row.get("created_by") != user.username:
            raise HTTPException(403, "只能停止自己提交的批量生成任务")
        if row.get("status") in FINISHED_BATCH_JOB_STATUSES:
            return {"success": True, "message": "任务已结束", "data": _batch_job_row_payload(row)}
        db.execute(
            """UPDATE semester_evaluation_batch_job
               SET cancel_requested = 1,
                   message = '已请求停止，当前学生处理完成后停止',
                   updated_at = datetime('now', 'localtime')
               WHERE job_id = ?""",
            (job_id,),
        )
        row = db.query_one(
            "SELECT * FROM semester_evaluation_batch_job WHERE job_id = ?",
            (job_id,),
        )
    return {"success": True, "message": "已请求停止批量生成", "data": _batch_job_row_payload(row)}


@router.delete("/batch-delete/{job_id}", summary="删除已结束的学期末评价批量任务")
async def delete_semester_evaluation_batch_job(
    job_id: str,
    user: User = Depends(require_configured_api_permission(API_BATCH_DELETE, "DELETE", allow_missing=False))
):
    _cleanup_semester_evaluation_jobs()
    job = SEMESTER_EVALUATION_JOBS.get(job_id)
    if job:
        if job.get("created_by") != user.username:
            raise HTTPException(403, "只能删除自己提交的批量生成任务")
        if job.get("status") not in FINISHED_BATCH_JOB_STATUSES:
            raise HTTPException(400, "运行中的批量生成任务不能删除，请先停止任务")

    with get_moral_db() as db:
        _ensure_batch_job_table(db)
        row = db.query_one(
            "SELECT * FROM semester_evaluation_batch_job WHERE job_id = ?",
            (job_id,),
        )
        if row:
            if row.get("created_by") != user.username:
                raise HTTPException(403, "只能删除自己提交的批量生成任务")
            row = _mark_orphaned_cancel_requested_job_cancelled(db, row)
            if row.get("status") not in FINISHED_BATCH_JOB_STATUSES:
                raise HTTPException(400, "运行中的批量生成任务不能删除，请先停止任务")
            db.execute(
                "DELETE FROM semester_evaluation_batch_job WHERE job_id = ?",
                (job_id,),
            )
        elif not job:
            raise HTTPException(404, "批量生成任务不存在或已过期")

    SEMESTER_EVALUATION_JOBS.pop(job_id, None)
    return {"success": True, "message": "已删除批量生成任务"}


@router.get("/list", summary="查询学期末评价列表")
async def api_get_semester_evaluation_list(
    class_id: Optional[int] = Query(None),
    grade_id: Optional[int] = Query(None),
    semester_id: Optional[int] = Query(None),
    page: int = Query(1, ge=1),
    pageSize: int = Query(20, ge=1, le=100),
    user: User = Depends(require_configured_api_permission(API_LIST, "GET", allow_missing=False))
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
    user: User = Depends(require_configured_api_permission(API_DETAIL, "GET", allow_missing=False))
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

        scope = get_record_data_scope(
            db, user, API_DETAIL,
            all_permissions=['moral_record_manage'],
            own_class_permissions=['moral_record_own_class'],
            own_permissions=[]
        )
        if not record_in_scope(record, scope, username=user.username):
            raise HTTPException(403, "只能查看授权范围内的学期末评价记录")

        # 解析 JSON 字段
        result = dict(record)
        result['score_details'] = json.loads(record.get('score_details') or '{}')
        result['statistics'] = json.loads(record.get('statistics') or '{}')
        result['key_events'] = json.loads(record.get('key_events') or '[]')
        result['ai_summary'] = json.loads(record.get('ai_summary') or '{}') if record.get('ai_summary') else None

        return {"success": True, "data": result}
