# -*- coding: utf-8 -*-
"""
一生一册 API - 学生成长时光轴

班主任只可查看本班学生；教发部/管理员可查看所有学生
"""

from fastapi import APIRouter, Depends, Query, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import date

from .base import (
    get_moral_db,
    get_current_user,
    check_moral_permission,
    get_teacher_class_id,
)
from models.datas_api.auth import User

router = APIRouter(prefix="/timeline", tags=["一生一册"])


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

        # 权限过滤
        if not check_moral_permission(user, 'profile_view_all'):
            my_class_id = get_teacher_class_id(user, db)
            if my_class_id:
                conditions.append("s.class_id = %s")
                params.append(my_class_id)
            else:
                return {"success": True, "data": {"items": [], "total": 0}}

        if class_id:
            conditions.append("s.class_id = %s")
            params.append(class_id)

        if student_name:
            conditions.append("s.name LIKE %s")
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
            LIMIT %s OFFSET %s
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
    event_types: Optional[str] = Query(None, description="事件类型筛选：moment,daily,school,punishment,task"),
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
            WHERE s.student_id = %s
        """, (student_id,))

        if not student:
            raise HTTPException(404, f"学生 {student_id} 不存在")

        # 归档学生权限检查：只有管理员/教发部可查看
        if student['status'] != '在校' or student.get('grade_archived'):
            if not check_moral_permission(user, 'profile_view_all'):
                raise HTTPException(403, "只能查看在校学生档案，已归档学生需管理员权限")

        # 在校学生权限检查：班主任只能看本班
        if student['status'] == '在校' and not check_moral_permission(user, 'profile_view_all'):
            my_class_id = get_teacher_class_id(user, db)
            if my_class_id is None or my_class_id != student['class_id']:
                raise HTTPException(403, "只能查看本班学生的档案")

        # 解析筛选类型
        type_filter = event_types.split(',') if event_types else None

        timeline = []

        # 1. 点滴记录
        if not type_filter or 'moment' in type_filter:
            moments = db.query_all("""
                SELECT mr.record_id, mr.content, mr.record_date, mr.record_type,
                       mr.tags, mr.recorder, 'moment' as source
                FROM moment_record mr
                WHERE mr.student_id = %s AND mr.is_private = 1
                  AND (%s IS NULL OR mr.record_date >= %s)
                  AND (%s IS NULL OR mr.record_date <= %s)
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
                WHERE dr.student_id = %s AND dr.is_deleted = 0
                  AND (%s IS NULL OR dr.record_date >= %s)
                  AND (%s IS NULL OR dr.record_date <= %s)
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
                WHERE ssr.student_id = %s AND ssr.is_deleted = 0
                  AND (%s IS NULL OR ssr.get_date >= %s)
                  AND (%s IS NULL OR ssr.get_date <= %s)
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
                WHERE pr.student_id = %s AND pr.is_revoked = 0
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
                WHERE stf.student_id = %s AND stf.status = 1
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

        # 按日期排序
        timeline.sort(key=lambda x: x['date'] or '', reverse=True)

        # 统计信息
        stats = {
            "moment_count": len([x for x in timeline if x['type'] == 'moment']),
            "daily_count": len([x for x in timeline if x['type'] == 'daily']),
            "school_count": len([x for x in timeline if x['type'] == 'school']),
            "punishment_count": len([x for x in timeline if x['type'] == 'punishment']),
            "task_count": len([x for x in timeline if x['type'] == 'task']),
            "total": len(timeline)
        }

        # 加减分汇总（改进点）
        score_summary = {
            "daily_positive": 0,      # 日常表现加分
            "daily_negative": 0,      # 日常表现扣分
            "school_positive": 0,     # 校级事件加分
            "school_negative": 0,     # 校级事件扣分
            "task_total": 0,          # 任务完成总分
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
            score_summary['task_total'] -
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
                