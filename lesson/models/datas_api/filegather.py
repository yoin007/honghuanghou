# -*- coding: utf-8 -*-
"""
文件收集系统 API 路由模块

功能:
- 教师上传文件
- 教务管理文件
- 文件状态追踪
"""

import os
import logging
from typing import Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from fastapi.responses import FileResponse
from pydantic import BaseModel

from models.datas_api.auth import User, get_current_user, is_admin_user
from models.filegather_db import FileGatherDB, MAX_FILE_SIZE
from sendqueue import send_text
from models.lesson.lesson import Lesson

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/filegather", tags=["文件收集"])

# 初始化数据库
db = FileGatherDB()


# ==================== Helper Functions ====================

def is_jiaowu_user(user: User) -> bool:
    """
    检查是否为教务角色

    Args:
        user: 用户对象

    Returns:
        是否为教务或管理员
    """
    if not user:
        return False
    role = str(user.role) if user.role else ""
    # 教务角色或管理员都可以访问
    return role == "jiaowu" or "jiaowu" in role or is_admin_user(user)


# ==================== Request/Response Models ====================

class MarkDoneRequest(BaseModel):
    """标记完成请求"""
    id: int


class DeleteRequest(BaseModel):
    """删除请求"""
    id: int


# ==================== Teacher Routes (教师端) ====================

@router.post("/upload", summary="上传文件", description="教师上传需要打印的文件")
async def upload_file(
    file: UploadFile = File(...),
    copies: int = Form(...),
    use_date: str = Form(...),
    note: Optional[str] = Form(None),
    current_user: User = Depends(get_current_user),
):
    """
    上传文件

    - **file**: 要上传的文件
    - **copies**: 打印份数
    - **use_date**: 使用日期 (YYYY-MM-DD)
    - **note**: 备注 (可选)
    """
    # 检查文件扩展名
    if not db.check_extension(file.filename):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="不允许的文件格式，仅支持: jpg, png, doc, docx, xlsx, xls, ppt, pptx, pdf"
        )

    # 检查文件大小
    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"文件大小超过限制 ({MAX_FILE_SIZE // 1024 // 1024}MB)"
        )

    # 验证打印份数
    try:
        copies_val = int(copies)
        if copies_val <= 0:
            raise ValueError()
    except (ValueError, TypeError):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="打印份数应为正整数"
        )

    # 解析使用日期
    try:
        use_date_iso, month = db.parse_use_date(use_date)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

    # 保存文件
    try:
        stored_path = db.save_file(month, file.filename, content)
    except Exception as e:
        logger.error(f"Failed to save file: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="文件保存失败"
        )

    # 插入数据库记录
    note_val = (note or "").strip() or None
    try:
        file_id = db.insert_file(
            username=current_user.username,
            original_name=file.filename,
            stored_path=stored_path,
            content_type=file.content_type,
            copies=copies_val,
            use_date=use_date_iso,
            month=month,
            note=note_val,
        )
    except Exception as e:
        logger.error(f"Failed to insert file record: {e}")
        # 清理已保存的文件
        try:
            os.remove(stored_path)
        except:
            pass
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="文件记录保存失败"
        )

    logger.info(f"File uploaded: id={file_id}, user={current_user.username}, name={file.filename}")

    return {
        "id": file_id,
        "username": current_user.username,
        "original_name": file.filename,
        "status": "否",
        "copies": copies_val,
        "use_date": use_date_iso,
        "month": month,
        "note": note_val,
    }


@router.get("/my-files", summary="获取我的文件", description="获取当前用户上传的文件列表")
async def get_my_files(
    month: Optional[str] = None,
    current_user: User = Depends(get_current_user),
):
    """
    获取我的文件列表

    - **month**: 月份筛选 (YYYYMM格式，可选)
    """
    # 默认当前月份
    m = month.strip() if isinstance(month, str) and month.strip() else datetime.utcnow().strftime("%Y%m")
    items = db.query_files(username=current_user.username, month=m)
    return {"items": items, "month": m}


@router.delete("/my-files/{file_id}", summary="删除文件", description="删除自己上传的文件")
async def delete_my_file(
    file_id: int,
    current_user: User = Depends(get_current_user),
):
    """
    删除文件

    - **file_id**: 文件ID
    """
    try:
        db.delete_file(file_id, current_user.username)
        logger.info(f"File deleted: id={file_id}, user={current_user.username}")
        return {"ok": True, "id": file_id}
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))


# ==================== Admin Routes (教务端) ====================

@router.get("/admin/files", summary="待处理文件列表", description="获取待处理的文件列表")
async def admin_get_pending_files(
    current_user: User = Depends(get_current_user),
):
    """获取待处理文件列表（需要教务或管理员权限）"""
    if not is_jiaowu_user(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="需要教务权限"
        )

    items = db.query_files(status=["否", "打印中"])
    return {"items": items}


@router.get("/admin/done-files", summary="已完成文件列表", description="获取已完成的文件列表")
async def admin_get_done_files(
    month: Optional[str] = None,
    current_user: User = Depends(get_current_user),
):
    """
    获取已完成文件列表（需要教务或管理员权限）

    - **month**: 月份筛选 (YYYYMM格式，可选)
    """
    if not is_jiaowu_user(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="需要教务权限"
        )

    m = month.strip() if isinstance(month, str) and month.strip() else datetime.utcnow().strftime("%Y%m")
    items = db.query_files(status="是", month=m)
    return {"items": items, "month": m}


@router.post("/admin/mark-done/{file_id}", summary="标记完成", description="标记文件为已完成")
async def admin_mark_done(
    file_id: int,
    current_user: User = Depends(get_current_user),
):
    """
    标记文件为已完成（需要教务或管理员权限）

    - **file_id**: 文件ID
    """
    if not is_jiaowu_user(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="需要教务权限"
        )

    try:
        # 获取文件信息（在标记完成前）
        file_info = db.get_file_by_id(file_id)
        if not file_info:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="文件不存在")

        result = db.mark_done(file_id)
        logger.info(f"File marked done: id={file_id}, admin={current_user.username}")

        # 发送微信消息通知上传者
        try:
            username = file_info.get("username", "")
            original_name = file_info.get("original_name", "")

            if username:
                l = Lesson()
                wxid = l.member_wxid(username, active=True)
                if wxid:
                    msg = f"【文件打印完成通知】\n文件「{original_name}」已经打印完成，请及时领取。"
                    send_text(msg, wxid, producer="filegather")
                    logger.info(f"Notification sent to {username} ({wxid})")
                else:
                    logger.warning(f"User {username} has no wxid, notification not sent")
        except Exception as e:
            logger.error(f"Failed to send notification: {e}")

        return result
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except FileNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to mark file done: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="操作失败"
        )


@router.get("/admin/download/{file_id}", summary="下载文件", description="下载指定文件")
async def admin_download_file(
    file_id: int,
    current_user: User = Depends(get_current_user),
):
    """
    下载文件（需要教务或管理员权限）

    - **file_id**: 文件ID
    """
    if not is_jiaowu_user(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="需要教务权限"
        )

    file_info = db.get_file_by_id(file_id)
    if not file_info:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="文件不存在")

    relative_path = file_info["stored_path"]
    name = file_info["original_name"]
    file_status = file_info["status"]

    # 转换为物理路径
    path = db._resolve_path(relative_path)

    # 调试日志：打印路径拼接信息
    logger.info(f"[FileGather Download] file_id={file_id}")
    logger.info(f"[FileGather Download] relative_path={relative_path}")
    logger.info(f"[FileGather Download] storage_root={db.storage_root}")
    logger.info(f"[FileGather Download] resolved_path={path}")
    logger.info(f"[FileGather Download] file_exists={os.path.isfile(path)}")

    # 如果文件状态是"否"，更新为"打印中"
    if file_status == "否":
        try:
            db.update_status(file_id, "打印中")
        except Exception as e:
            logger.warning(f"Failed to update file status: {e}")

    if not os.path.isfile(path):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="文件未找到")

    logger.info(f"File downloaded: id={file_id}, admin={current_user.username}")
    return FileResponse(path, filename=name)


@router.get("/admin/statistics", summary="统计信息", description="获取文件统计信息")
async def admin_get_statistics(
    month: Optional[str] = None,
    current_user: User = Depends(get_current_user),
):
    """
    获取统计信息（需要教务或管理员权限）

    - **month**: 月份筛选 (YYYYMM格式，可选)
    """
    if not is_jiaowu_user(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="需要教务权限"
        )

    stats = db.get_statistics(month)
    return stats


@router.get("/admin/months", summary="获取月份列表", description="获取所有有文件的月份")
async def admin_get_months(
    current_user: User = Depends(get_current_user),
):
    """获取月份列表（需要教务或管理员权限）"""
    if not is_jiaowu_user(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="需要教务权限"
        )

    months = db.get_months()
    return {"months": months}