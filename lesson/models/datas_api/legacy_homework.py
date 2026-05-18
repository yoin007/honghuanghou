# -*- coding: utf-8 -*-
"""Legacy Homework/Announcement API - 作业和公告相关接口。

Batch34: 从 datas_api_legacy.py 拆分作业/公告逻辑。
"""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from models.datas_api.auth import User, is_admin_user
from models.datas_api.moral.api_permission import require_configured_api_permission
from models.lesson.homework import Homework
from utils.operation_log import operation_logger


router = APIRouter()

logger = logging.getLogger(__name__)

# 模拟不同班级的班主任寄语数据
TEACHER_MESSAGES = {
    "202401": {
        "content": "亲爱的同学们，在新的学期里，希望大家能够以饱满的热情投入学习。记住，成功不是偶然的，而是来自于每一天的积累和努力。让我们携手共创一个积极向上、团结互助的班级氛围！",
        "teacher": "张明",
        "date": "2024-12-08",
    }
}


# ============================================================
# Model Classes
# ============================================================

class HomeworkForm(BaseModel):
    classCode: str
    subject: str
    teacher: str = "管理员"
    content: str
    deadline: str
    duration: int
    type: str


class HomeworkIds(BaseModel):
    ids: list[int]
    classCode: str


class AnnouncementForm(BaseModel):
    classCode: str
    title: str
    author: str
    content: str


class HomeworkUpdateForm(BaseModel):
    subject: Optional[str] = None
    content: Optional[str] = None
    deadline: Optional[str] = None
    duration: Optional[int] = None
    type: Optional[str] = None


class AnnouncementUpdateForm(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None


# ============================================================
# Routes: Homework
# ============================================================

@router.get("/homework/{class_code}", summary="获取班级作业", description="获取指定班级的所有作业列表")
async def get_homework(class_code: str):
    """获取作业列表，按类型分类，按学科和老师分组"""
    with Homework() as n:
        subjects = n.subjects
        homework_by_type = {"日常": {}, "周末": {}}

        for subject in subjects:
            daily = n.get_homework(class_code, subject, "日常")
            weekly = n.get_homework(class_code, subject, "周末")

            if daily:
                homework_by_type["日常"][subject] = daily
            if weekly:
                homework_by_type["周末"][subject] = weekly

    return homework_by_type


@router.post("/homework/")
async def create_homework(homework: HomeworkForm, current_user: User = Depends(require_configured_api_permission("/api/homework/", "POST", allow_missing=False))):
    """发布作业（统一鉴权已完成角色校验）"""
    if not current_user:
        raise HTTPException(status_code=401, detail="请先登录")

    # 直接使用当前登录用户的用户名作为老师，不依赖前端传递
    teacher_name = current_user.username

    try:
        with Homework() as n:
            n.add_homework(
                class_code=homework.classCode,
                subject=homework.subject,
                teacher=teacher_name,
                content=homework.content,
                deadline=homework.deadline,
                duration=homework.duration,
                type=homework.type,
                wxid=""
            )
            result = {"id": n.cursor.lastrowid, "message": "作业发布成功"}

        # 记录操作日志
        operation_logger.info(
            "发布作业",
            username=teacher_name,
            details={
                "class_code": homework.classCode,
                "subject": homework.subject,
                "type": homework.type,
                "teacher": teacher_name
            }
        )

        # WebSocket 通知
        try:
            from websocket import notify_homework_update
            await notify_homework_update(homework.classCode, {"action": "create", "subject": homework.subject})
        except Exception as ws_err:
            logger.warning(f"WebSocket notification failed: {ws_err}")

        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/homework/batch")
async def delete_homework_batch(homework_ids: HomeworkIds, current_user: User = Depends(require_configured_api_permission("/api/homework/batch", "DELETE", allow_missing=False))):
    """批量删除作业（管理员可删全部，教师只能删自己发布的）"""
    try:
        deleted_count = 0
        with Homework() as n:
            for hw_id in homework_ids.ids:
                existing = n.get_homework_by_id(hw_id)
                if not existing or existing.get("deleted", 0) == 1:
                    continue
                if not is_admin_user(current_user) and existing.get("teacher") != current_user.username:
                    raise HTTPException(status_code=403, detail="无权限删除他人发布的作业")
                n.delete_homework(hw_id)
                deleted_count += 1

        # 记录操作日志
        operation_logger.info(
            "批量删除作业",
            details={
                "class_code": homework_ids.classCode,
                "deleted_ids": homework_ids.ids,
                "count": deleted_count
            }
        )

        # WebSocket 通知
        try:
            from websocket import notify_homework_update
            await notify_homework_update(homework_ids.classCode, {"action": "delete", "count": deleted_count})
        except Exception as ws_err:
            logger.warning(f"WebSocket notification failed: {ws_err}")

        return {"message": f"成功删除 {deleted_count} 条作业"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/homework/{hw_id}")
async def update_homework(hw_id: int, homework: HomeworkUpdateForm, current_user: User = Depends(require_configured_api_permission("/api/homework/{hw_id}", "PUT", allow_missing=False))):
    """修改作业（统一鉴权已完成角色校验，保留本人判断）"""
    try:
        with Homework() as n:
            existing = n.get_homework_by_id(hw_id)
            if not existing:
                raise HTTPException(status_code=404, detail="作业不存在")

            if existing.get("deleted", 0) == 1:
                raise HTTPException(status_code=404, detail="作业不存在")

            # 本人判断保留：非 admin 只能改自己发布的
            if current_user and not is_admin_user(current_user):
                if existing.get("teacher") != current_user.username:
                    raise HTTPException(status_code=403, detail="无权限修改他人发布的作业")

            n.update_homework(
                hw_id=hw_id,
                subject=homework.subject,
                content=homework.content,
                deadline=homework.deadline,
                duration=homework.duration,
                type=homework.type
            )
        return {"message": "作业更新成功"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/homework/{hw_id}")
async def delete_homework(hw_id: int, current_user: User = Depends(require_configured_api_permission("/api/homework/{hw_id}", "DELETE", allow_missing=False))):
    """删除作业（统一鉴权已完成角色校验，保留本人判断）"""
    try:
        with Homework() as n:
            existing = n.get_homework_by_id(hw_id)
            if not existing:
                raise HTTPException(status_code=404, detail="作业不存在")

            if existing.get("deleted", 0) == 1:
                raise HTTPException(status_code=404, detail="作业不存在")

            # 本人判断保留：非 admin 只能删自己发布的
            if current_user and not is_admin_user(current_user):
                if existing.get("teacher") != current_user.username:
                    raise HTTPException(status_code=403, detail="无权限删除他人发布的作业")

            n.delete_homework(hw_id)
        return {"message": "作业删除成功"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================
# Routes: Announcements
# ============================================================

@router.get("/announcements/{class_code}")
async def get_class_announcements(class_code: str):
    """获取指定班级的公告"""
    with Homework() as n:
        announcements = n.get_announcement(class_code)
    return {"announcements": announcements}


@router.post("/announcement/")
async def create_announcement(announcement: AnnouncementForm, current_user: User = Depends(require_configured_api_permission("/api/announcement/", "POST", allow_missing=False))):
    """发布公告（统一鉴权已完成角色校验）"""
    try:
        with Homework() as n:
            n.add_announcement(
                class_code=announcement.classCode,
                title=announcement.title,
                author=current_user.username,
                content=announcement.content,
                wxid=""
            )
            result = {"id": n.cursor.lastrowid, "message": "公告发布成功"}
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/announcement/{ann_id}")
async def update_announcement(ann_id: int, announcement: AnnouncementUpdateForm, current_user: User = Depends(require_configured_api_permission("/api/announcement/{ann_id}", "PUT", allow_missing=False))):
    """修改公告（统一鉴权已完成角色校验，保留本人判断）"""
    try:
        with Homework() as n:
            existing = n.get_announcement_by_id(ann_id)
            if not existing:
                raise HTTPException(status_code=404, detail="公告不存在")

            # 本人判断保留：非 admin 只能改自己发布的
            if current_user and not is_admin_user(current_user):
                if existing.get("author") != current_user.username:
                    raise HTTPException(status_code=403, detail="无权限修改他人发布的公告")

            n.update_announcement(
                ann_id=ann_id,
                title=announcement.title,
                content=announcement.content
            )
        return {"message": "公告更新成功"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/announcement/{ann_id}")
async def delete_announcement(ann_id: int, current_user: User = Depends(require_configured_api_permission("/api/announcement/{ann_id}", "DELETE", allow_missing=False))):
    """删除公告（统一鉴权已完成角色校验，保留本人判断）"""
    try:
        with Homework() as n:
            existing = n.get_announcement_by_id(ann_id)
            if not existing:
                raise HTTPException(status_code=404, detail="公告不存在")

            # 本人判断保留：非 admin 只能删自己发布的
            if current_user and not is_admin_user(current_user):
                if existing.get("author") != current_user.username:
                    raise HTTPException(status_code=403, detail="无权限删除他人发布的公告")

            n.delete_announcement(ann_id)
        return {"message": "公告删除成功"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================
# Routes: Teacher Messages
# ============================================================

@router.get("/messages/{class_code}")
async def get_teacher_messages(class_code: str):
    """获取指定班级的老师留言"""
    if class_code not in TEACHER_MESSAGES:
        return {"messages": []}
    return {"messages": [TEACHER_MESSAGES[class_code]]}
