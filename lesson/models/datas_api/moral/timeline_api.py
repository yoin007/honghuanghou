# -*- coding: utf-8 -*-
"""
一生一册 API - 学生成长时光轴

班主任只可查看本班学生；教发部/管理员可查看所有学生
"""

import logging
from fastapi import APIRouter, Depends, Query, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import date

from .base import (
    get_moral_db,
    get_current_user,
    get_record_data_scope,
    append_record_scope_condition,
    record_in_scope,
)
from models.datas_api.auth import User

router = APIRouter(prefix="/timeline", tags=["一生一册"])
logger = logging.getLogger(__name__)

API_TIMELINE = "/api/moral/timeline"
API_TIMELINE_SEARCH = "/api/moral/timeline/search"


def _timeline_scope(db, user: User, api_path: str = API_TIMELINE) -> dict:
    return get_record_data_scope(
        db,
        user,
        api_path,
        all_permissions=['profile_view_all'],
        own_class_permissions=['profile_view_own_class'],
        own_permissions=[],
    )


def _ensure_timeline_student_access(db, user: User, student: dict, api_path: str = API_TIMELINE) -> None:
    scope = _timeline_scope(db, user, api_path)
    if (student['status'] != '在校' or student.get('grade_archived')) and not scope.get("can_all"):
        raise HTTPException(403, "只能查看在校学生档案，已归档学生需管理员权限")
    if not record_in_scope(student, scope, username=user.username):
        raise HTTPException(403, "只能查看授权范围内学生的一生一册")


@router.get("/search", summary="搜索学生（用于一生一册筛选）")
async def search_students_for_timeline(
    class_id: Optional[int] = Query(None),
    student_name: Optional[str] = Query(None),
    include_archived: int = Query(0, description="1=包含已归档（毕业/转出）学生"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    user: User = Depends(get_current_user)
):
    """
    搜索学生用于一生一册查看

    权限说明：
    - 班主任只能搜索本班学生
    - 教发部/管理员可搜索所有学生

    改进：
    - 支持查询已归档学生（毕业/转出/休学）
    """
    with get_moral_db() as db:
        conditions = ["1=1"]
        params = []

        # 是否包含已归档学生
        if include_archived == 0:
            conditions.append("s.status = '在校'")
        else:
            # 包含所有状态，但优先显示在校
            pass

        search_scope = _timeline_scope(db, user, API_TIMELINE_SEARCH)
        append_record_scope_condition(
            conditions,
            params,
            search_scope,
            table_alias="s",
            username=user.username,
        )

        if class_id:
            conditions.append("s.class_id = ?")
            params.append(class_id)

        if student_name:
            conditions.append("s.name LIKE ?")
            params.append(f"%{student_name}%")

        where_clause = " AND ".join(conditions)

        # 查询总数
        count_query = f"SELECT COUNT(*) FROM student s WHERE {where_clause}"
        total = db.query_value(count_query, tuple(params))

        # 分页查询
        offset = (page - 1) * page_size
        data_query = f"""
            SELECT s.student_id, s.name, s.gender, s.birthday, s.status,
                   c.class_name, g.grade_name, g.is_archived as grade_archived
            FROM student s
            JOIN class c ON s.class_id = c.class_id
            JOIN grade g ON s.grade_id = g.grade_id
            WHERE {where_clause}
            ORDER BY s.status = '在校' DESC, c.class_name, s.student_id
            LIMIT ? OFFSET ?
        """
        params.extend([page_size, offset])
        students = db.query_all(data_query, tuple(params))

        return {
            "success": True,
            "data": {
                "items": students,
                "total": total,
                "page": page,
                "page_size": page_size
            }
        }


@router.get("/{student_id}", summary="获取学生时光轴")
async def get_student_timeline(
    student_id: str,
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    event_types: Optional[str] = Query(None, description="事件类型筛选：moment,daily,school,punishment,task,collective"),
    include_archived: int = Query(0, description="1=允许查询已归档学生"),
    user: User = Depends(get_current_user)
):
    """
    获取学生成长时光轴

    权限说明：
    - 班主任(cleader): 只能查看本班学生
    - 教发部/管理员: 可查看所有学生，包括已归档

    改进：
    - 支持查询已归档学生档案
    - 添加加减分汇总显示
    """
    with get_moral_db() as db:
        # 获取学生信息
        student = db.query_one("""
            SELECT s.*, c.class_name, c.leader_name, g.grade_name, g.is_archived as grade_archived
            FROM student s
            JOIN class c ON s.class_id = c.class_id
            JOIN grade g ON s.grade_id = g.grade_id
            WHERE s.student_id = ?
        """, (student_id,))

        if not student:
            raise HTTPException(404, f"学生 {student_id} 不存在")

        _ensure_timeline_student_access(db, user, student, API_TIMELINE)

        # 解析筛选类型
        type_filter = event_types.split(',') if event_types else None

        timeline = []

        # 1. 点滴记录
        if not type_filter or 'moment' in type_filter:
            moments = db.query_all("""
                SELECT mr.record_id, mr.content, mr.record_date, mr.record_type,
                       mr.tags, mr.recorder, 'moment' as source
                FROM moment_record mr
                WHERE mr.student_id = ? AND mr.is_private = 1
                  AND (? IS NULL OR mr.record_date >= ?)
                  AND (? IS NULL OR mr.record_date <= ?)
                ORDER BY mr.record_date DESC
            """, (student_id, start_date, start_date, end_date, end_date) if start_date or end_date else (student_id, None, None, None, None))

            for m in moments:
                import json
                tags = json.loads(m['tags']) if m['tags'] else []
                timeline.append({
                    "date": m['record_date'],
                    "type": "moment",
                    "title": "点滴记录",
                    "content": m['content'],
                    "score": None,
                    "recorder": m['recorder'],
                    "source": "点滴记录",
                    "tags": tags,
                    "record_type": m['record_type']
                })

        # 2. 日常表现记录
        if not type_filter or 'daily' in type_filter:
            daily_records = db.query_all("""
                SELECT dr.record_id, de.event_name, de.event_type, dr.score,
                       dr.record_date, dr.remark, dr.recorder, 'daily' as source
                FROM student_daily_record dr
                JOIN daily_event_type de ON dr.event_id = de.event_id
                WHERE dr.student_id = ? AND dr.is_deleted = 0
                  AND (? IS NULL OR dr.record_date >= ?)
                  AND (? IS NULL OR dr.record_date <= ?)
                ORDER BY dr.record_date DESC
            """, (student_id, start_date, start_date, end_date, end_date) if start_date or end_date else (student_id, None, None, None, None))

            for d in daily_records:
                timeline.append({
                    "date": d['record_date'],
                    "type": "daily",
                    "title": d['event_name'],
                    "content": d['remark'] or "",
                    "score": d['score'],
                    "recorder": d['recorder'],
                    "source": "日常表现",
                    "event_type": "积极" if d['event_type'] == 1 else "消极"
                })

        # 3. 校级事件
        if not type_filter or 'school' in type_filter:
            school_records = db.query_all("""
                SELECT ssr.record_id, se.event_name, se.score, ssr.get_date,
                       ssr.proof, 'school' as source
                FROM student_school_record ssr
                JOIN school_event_type se ON ssr.event_id = se.event_id
                WHERE ssr.student_id = ? AND ssr.is_deleted = 0
                  AND (? IS NULL OR ssr.get_date >= ?)
                  AND (? IS NULL OR ssr.get_date <= ?)
                ORDER BY ssr.get_date DESC
            """, (student_id, start_date, start_date, end_date, end_date) if start_date or end_date else (student_id, None, None, None, None))

            for s in school_records:
                timeline.append({
                    "date": s['get_date'],
                    "type": "school",
                    "title": s['event_name'],
                    "content": s['proof'] or "",
                    "score": s['score'],
                    "recorder": None,
                    "source": "校级事件"
                })

        # 4. 处分记录
        if not type_filter or 'punishment' in type_filter:
            punishments = db.query_all("""
                SELECT pr.id, pr.level, pr.reason, pr.punishment_date,
                       pr.revoke_date, 'punishment' as source
                FROM punishment_record pr
                WHERE pr.student_id = ? AND pr.is_revoked = 0
                ORDER BY pr.punishment_date DESC
            """, (student_id,))

            for p in punishments:
                timeline.append({
                    "date": p['punishment_date'][:10] if p['punishment_date'] else None,
                    "type": "punishment",
                    "title": f"处分 - {p['level']}",
                    "content": p['reason'] or "",
                    "score": None,
                    "recorder": None,
                    "source": "处分记录",
                    "revoke_date": p['revoke_date']
                })

        # 5. 任务完成
        if not type_filter or 'task' in type_filter:
            tasks = db.query_all("""
                SELECT stf.id, mt.task_name, stf.finish_date,
                       stf.current_score, 'task' as source
                FROM student_task_finish stf
                JOIN grade_moral_task mt ON stf.task_id = mt.task_id
                WHERE stf.student_id = ? AND stf.status = 1
                ORDER BY stf.finish_date DESC
            """, (student_id,))

            for t in tasks:
                timeline.append({
                    "date": t['finish_date'],
                    "type": "task",
                    "title": f"完成任务: {t['task_name']}",
                    "content": "",
                    "score": t['current_score'],
                    "recorder": None,
                    "source": "德育任务"
                })

        # 6. 集体事件
        if not type_filter or 'collective' in type_filter:
            collective_records = db.query_all("""
                SELECT ced.id, ced.score_assigned, ced.is_participant, ced.remark,
                       ce.event_name, ce.event_type, ce.event_date, 'collective' as source
                FROM collective_event_distribution ced
                JOIN collective_event ce ON ced.event_id = ce.event_id
                WHERE ced.student_id = ?
                  AND (? IS NULL OR ce.event_date >= ?)
                  AND (? IS NULL OR ce.event_date <= ?)
                ORDER BY ce.event_date DESC
            """, (student_id, start_date, start_date, end_date, end_date) if start_date or end_date else (student_id, None, None, None, None))

            for c in collective_records:
                timeline.append({
                    "date": c['event_date'],
                    "type": "collective",
                    "title": c['event_name'],
                    "content": c['remark'] or ("参与" if c['is_participant'] == 1 else "未参与"),
                    "score": c['score_assigned'] if c['is_participant'] == 1 else 0,
                    "recorder": None,
                    "source": "集体事件",
                    "event_type": c['event_type']
                })

        # 按日期排序
        timeline.sort(key=lambda x: x['date'] or '', reverse=True)

        # 统计信息
        stats = {
            "moment_count": len([x for x in timeline if x['type'] == 'moment']),
            "daily_count": len([x for x in timeline if x['type'] == 'daily']),
            "school_count": len([x for x in timeline if x['type'] == 'school']),
            "punishment_count": len([x for x in timeline if x['type'] == 'punishment']),
            "task_count": len([x for x in timeline if x['type'] == 'task']),
            "collective_count": len([x for x in timeline if x['type'] == 'collective']),
            "total": len(timeline)
        }

        # 加减分汇总（改进点）
        score_summary = {
            "daily_positive": 0,      # 日常表现加分
            "daily_negative": 0,      # 日常表现扣分
            "school_positive": 0,     # 校级事件加分
            "school_negative": 0,     # 校级事件扣分
            "task_total": 0,          # 任务完成总分
            "collective_total": 0,    # 集体事件总分
            "punishment_deduct": 0,   # 处分扣分（按级别）
            "total_score": 0          # 总计
        }

        # 计算日常表现加减分
        for item in timeline:
            if item['type'] == 'daily':
                score = item.get('score') or 0
                if item.get('event_type') == '积极':
                    score_summary['daily_positive'] += score
                else:
                    score_summary['daily_negative'] += abs(score)
            elif item['type'] == 'school':
                score = item.get('score') or 0
                if score > 0:
                    score_summary['school_positive'] += score
                else:
                    score_summary['school_negative'] += abs(score)
            elif item['type'] == 'task':
                score_summary['task_total'] += item.get('score') or 0
            elif item['type'] == 'collective':
                score_summary['collective_total'] += item.get('score') or 0
            elif item['type'] == 'punishment':
                # 处分扣分按级别计算
                level = item.get('title', '').split(' - ')[-1] if ' - ' in item.get('title', '') else ''
                punishment_scores = {
                    '警告': 0, '严重警告': 2, '通报': 5, '记过': 10, '留校查看': 20
                }
                score_summary['punishment_deduct'] += punishment_scores.get(level, 0)

        # 总计
        score_summary['total_score'] = (
            score_summary['daily_positive'] +
            score_summary['school_positive'] +
            score_summary['task_total'] +
            score_summary['collective_total'] -
            score_summary['daily_negative'] -
            score_summary['school_negative'] -
            score_summary['punishment_deduct']
        )

        return {
            "success": True,
            "data": {
                "student": {
                    "student_id": student['student_id'],
                    "name": student['name'],
                    "class_name": student['class_name'],
                    "grade_name": student['grade_name'],
                    "gender": student['gender'],
                    "birthday": student['birthday'],
                    "status": student['status'],
                    "grade_archived": student.get('grade_archived', 0)
                },
                "timeline": timeline,
                "stats": stats,
                "score_summary": score_summary
            }
        }


# =============================================================================
# 导出功能
# =============================================================================

import io
import pandas as pd
from fastapi.responses import StreamingResponse
from datetime import datetime as dt


def _get_timeline_data(db, student_id: str, user: User):
    """获取时光轴数据（复用 get_student_timeline 逻辑）"""
    # 获取学生信息
    student = db.query_one("""
        SELECT s.*, c.class_name, c.leader_name, g.grade_name, g.is_archived as grade_archived
        FROM student s
        JOIN class c ON s.class_id = c.class_id
        JOIN grade g ON s.grade_id = g.grade_id
        WHERE s.student_id = ?
    """, (student_id,))

    if not student:
        raise HTTPException(404, f"学生 {student_id} 不存在")

    _ensure_timeline_student_access(db, user, student, API_TIMELINE)

    timeline = []

    # 1. 点滴记录
    moments = db.query_all("""
        SELECT mr.record_id, mr.content, mr.record_date, mr.record_type,
               mr.tags, mr.recorder, 'moment' as source
        FROM moment_record mr
        WHERE mr.student_id = ? AND mr.is_private = 1
        ORDER BY mr.record_date DESC
    """, (student_id,))

    for m in moments:
        import json
        tags = json.loads(m['tags']) if m['tags'] else []
        timeline.append({
            "date": m['record_date'],
            "type": "点滴记录",
            "title": m['record_type'] or "点滴",
            "content": m['content'],
            "score": None,
            "recorder": m['recorder'],
            "source": "点滴记录"
        })

    # 2. 日常表现记录
    daily_records = db.query_all("""
        SELECT dr.record_id, de.event_name, de.event_type, dr.score,
               dr.record_date, dr.remark, dr.recorder, 'daily' as source
        FROM student_daily_record dr
        JOIN daily_event_type de ON dr.event_id = de.event_id
        WHERE dr.student_id = ? AND dr.is_deleted = 0
        ORDER BY dr.record_date DESC
    """, (student_id,))

    for d in daily_records:
        timeline.append({
            "date": d['record_date'],
            "type": "日常表现",
            "title": d['event_name'],
            "content": d['remark'] or "",
            "score": d['score'],
            "recorder": d['recorder'],
            "source": "日常表现",
            "event_type": "积极" if d['event_type'] == 1 else "消极"
        })

    # 3. 校级事件
    school_records = db.query_all("""
        SELECT ssr.record_id, se.event_name, se.score, ssr.get_date,
               ssr.proof, 'school' as source
        FROM student_school_record ssr
        JOIN school_event_type se ON ssr.event_id = se.event_id
        WHERE ssr.student_id = ? AND ssr.is_deleted = 0
        ORDER BY ssr.get_date DESC
    """, (student_id,))

    for s in school_records:
        timeline.append({
            "date": s['get_date'],
            "type": "校级事件",
            "title": s['event_name'],
            "content": s['proof'] or "",
            "score": s['score'],
            "recorder": None,
            "source": "校级事件"
        })

    # 4. 处分记录
    punishments = db.query_all("""
        SELECT pr.id, pr.punishment_date, pr.level, pr.reason, pr.score_deduct,
               pr.is_revoked, pr.revoke_date, 'punishment' as source
        FROM punishment_record pr
        WHERE pr.student_id = ?
        ORDER BY pr.punishment_date DESC
    """, (student_id,))

    for p in punishments:
        revoke_info = f"（已撤销：{p['revoke_date']}）" if p['is_revoked'] else ""
        timeline.append({
            "date": p['punishment_date'],
            "type": "处分记录",
            "title": f"{p['reason']} - {p['level']}{revoke_info}",
            "content": p['reason'],
            "score": -abs(p['score_deduct'] or 0),
            "recorder": None,
            "source": "处分记录"
        })

    # 5. 任务完成
    tasks = db.query_all("""
        SELECT stf.id, mt.task_name, mt.score, stf.finish_date,
               stf.current_score, stf.status, 'task' as source
        FROM student_task_finish stf
        JOIN grade_moral_task mt ON stf.task_id = mt.task_id
        WHERE stf.student_id = ? AND stf.status != 2
        ORDER BY stf.finish_date DESC
    """, (student_id,))

    for t in tasks:
        timeline.append({
            "date": t['finish_date'],
            "type": "德育任务",
            "title": t['task_name'],
            "content": "已完成" if t['status'] == 1 else "未完成",
            "score": t['current_score'],
            "recorder": None,
            "source": "德育任务"
        })

    # 6. 集体事件
    collective_records = db.query_all("""
        SELECT ced.id, ced.score_assigned, ced.is_participant, ced.remark,
               ce.event_name, ce.event_type, ce.event_date, 'collective' as source
        FROM collective_event_distribution ced
        JOIN collective_event ce ON ced.event_id = ce.event_id
        WHERE ced.student_id = ?
        ORDER BY ce.event_date DESC
    """, (student_id,))

    for c in collective_records:
        timeline.append({
            "date": c['event_date'],
            "type": "集体事件",
            "title": c['event_name'],
            "content": c['remark'] or ("参与" if c['is_participant'] == 1 else "未参与"),
            "score": c['score_assigned'] if c['is_participant'] == 1 else 0,
            "recorder": None,
            "source": "集体事件",
            "event_type": c['event_type']
        })

    # 按日期排序
    timeline.sort(key=lambda x: x['date'] or '', reverse=True)

    # 统计和分数汇总
    stats = {
        "点滴记录": len([x for x in timeline if x['type'] == "点滴记录"]),
        "日常表现": len([x for x in timeline if x['type'] == "日常表现"]),
        "校级事件": len([x for x in timeline if x['type'] == "校级事件"]),
        "处分记录": len([x for x in timeline if x['type'] == "处分记录"]),
        "德育任务": len([x for x in timeline if x['type'] == "德育任务"]),
        "集体事件": len([x for x in timeline if x['type'] == "集体事件"]),
        "总计": len(timeline)
    }

    score_summary = {
        "日常加分": sum(x.get('score') or 0 for x in timeline if x['type'] == "日常表现" and x.get('event_type') == "积极"),
        "日常扣分": sum(abs(x.get('score') or 0) for x in timeline if x['type'] == "日常表现" and x.get('event_type') == "消极"),
        "校级加分": sum(x.get('score') or 0 for x in timeline if x['type'] == "校级事件" and (x.get('score') or 0) > 0),
        "校级扣分": sum(abs(x.get('score') or 0) for x in timeline if x['type'] == "校级事件" and (x.get('score') or 0) < 0),
        "任务得分": sum(x.get('score') or 0 for x in timeline if x['type'] == "德育任务"),
        "集体得分": sum(x.get('score') or 0 for x in timeline if x['type'] == "集体事件"),
        "处分扣分": sum(abs(x.get('score') or 0) for x in timeline if x['type'] == "处分记录"),
        "总分": 0
    }
    score_summary["总分"] = (
        score_summary["日常加分"] + score_summary["校级加分"] + score_summary["任务得分"] + score_summary["集体得分"]
        - score_summary["日常扣分"] - score_summary["校级扣分"] - score_summary["处分扣分"]
    )

    return student, timeline, stats, score_summary


@router.get("/export/{student_id}/xlsx", summary="导出学生档案 Excel")
async def export_lifebook_xlsx(
    student_id: str,
    user: User = Depends(get_current_user)
):
    """导出一生一册为 Excel 多Sheet文件"""
    with get_moral_db() as db:
        student, timeline, stats, score_summary = _get_timeline_data(db, student_id, user)

        output = io.BytesIO()

        # Sheet 1: 学生信息
        student_df = pd.DataFrame([{
            "学号": student['student_id'],
            "姓名": student['name'],
            "班级": student['class_name'],
            "年级": student['grade_name'],
            "性别": student['gender'],
            "生日": student['birthday'],
            "状态": student['status'],
            "导出日期": dt.now().strftime('%Y-%m-%d %H:%M'),
            "导出人": user.username
        }])

        # Sheet 2: 时光轴明细
        timeline_df = pd.DataFrame([
            {
                "日期": item['date'],
                "类型": item['type'],
                "标题": item['title'],
                "内容": item['content'],
                "分数": item.get('score'),
                "记录人": item.get('recorder'),
                "来源": item['source']
            }
            for item in timeline
        ])

        # Sheet 3: 分数汇总
        score_df = pd.DataFrame([score_summary])

        # Sheet 4: 分类统计
        stats_df = pd.DataFrame([stats])

        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            student_df.to_excel(writer, sheet_name='学生信息', index=False)
            timeline_df.to_excel(writer, sheet_name='时光轴明细', index=False)
            score_df.to_excel(writer, sheet_name='分数汇总', index=False)
            stats_df.to_excel(writer, sheet_name='分类统计', index=False)

        output.seek(0)

        filename = f"一生一册_{student['name']}_{student['class_name']}_{dt.now().strftime('%Y%m%d')}.xlsx"

        return StreamingResponse(
            output,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f"attachment; filename*=UTF-8''{filename.encode('utf-8').decode('latin-1')}"}
        )


@router.get("/export/class/{class_id}", summary="批量导出班级学生档案")
async def export_class_lifebooks(
    class_id: int,
    user: User = Depends(get_current_user)
):
    """批量导出班级所有学生档案（zip打包）"""
    import zipfile

    with get_moral_db() as db:
        scope = _timeline_scope(db, user, API_TIMELINE)
        if not record_in_scope({"class_id": class_id, "status": "在校"}, scope, username=user.username):
            raise HTTPException(403, "只能导出授权范围内班级的学生档案")

        # 获取班级学生
        students = db.query_all("""
            SELECT s.student_id, s.name, c.class_name
            FROM student s
            JOIN class c ON s.class_id = c.class_id
            WHERE s.class_id = ? AND s.status = '在校'
            ORDER BY s.student_id
        """, (class_id,))

        if not students:
            raise HTTPException(404, "班级无在校学生")

        # 获取班级名称
        class_info = db.query_one("SELECT class_name FROM class WHERE class_id = ?", (class_id,))
        class_name = class_info['class_name'] if class_info else f"class_{class_id}"

        # 批量生成 Excel
        output = io.BytesIO()

        with zipfile.ZipFile(output, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for student in students:
                try:
                    student_data, timeline_data, stats_data, score_data = _get_timeline_data(db, student['student_id'], user)

                    # 生成单个 Excel
                    excel_buffer = io.BytesIO()

                    student_df = pd.DataFrame([{
                        "学号": student['student_id'],
                        "姓名": student['name'],
                        "班级": student['class_name'],
                        "导出日期": dt.now().strftime('%Y-%m-%d'),
                        "导出人": user.username
                    }])

                    timeline_df = pd.DataFrame([
                        {
                            "日期": item['date'],
                            "类型": item['type'],
                            "标题": item['title'],
                            "内容": item['content'],
                            "分数": item.get('score')
                        }
                        for item in timeline_data
                    ])

                    score_df = pd.DataFrame([score_data])
                    stats_df = pd.DataFrame([stats_data])

                    with pd.ExcelWriter(excel_buffer, engine='openpyxl') as writer:
                        student_df.to_excel(writer, sheet_name='学生信息', index=False)
                        timeline_df.to_excel(writer, sheet_name='时光轴', index=False)
                        score_df.to_excel(writer, sheet_name='分数汇总', index=False)
                        stats_df.to_excel(writer, sheet_name='统计', index=False)

                    excel_buffer.seek(0)
                    zipf.writestr(f"{student['name']}.xlsx", excel_buffer.read())

                except Exception as e:
                    logger.warning(f"导出学生 {student['name']} 失败: {e}")
                    continue

        output.seek(0)

        filename = f"班级档案_{class_name}_{dt.now().strftime('%Y%m%d')}.zip"

        return StreamingResponse(
            output,
            media_type="application/zip",
            headers={"Content-Disposition": f"attachment; filename*=UTF-8''{filename.encode('utf-8').decode('latin-1')}"}
        )
                
