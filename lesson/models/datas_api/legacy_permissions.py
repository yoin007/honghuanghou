# -*- coding: utf-8 -*-
"""Legacy Permissions API - 权限管理相关接口。

Batch39: 从 datas_api_legacy.py 拆分权限管理逻辑。
"""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from models.manage.member import Member
from models.datas_api.auth import User
from models.datas_api.moral.api_permission import require_configured_api_permission

logger = logging.getLogger(__name__)

router = APIRouter()


# ============================================================
# Model Classes
# ============================================================

class PermissionCreate(BaseModel):
    """权限创建请求参数"""
    func: str = ""
    func_name: str = ""
    pattern: str = ""
    white_list: str
    module: str
    activate: int = 1
    black_list: str = ""
    type: str = ""
    keywords: str = ""
    ai_flag: int = 0
    need_at: int = 0
    reply: str = ""
    level: int = 1
    priority: int = 99
    example: str = ""
    check_permission: int = 1
    score: int = 0
    balance: int = 0
    notes: str = ""


class PermissionUpdate(BaseModel):
    """权限更新请求参数"""
    func_name: Optional[str] = None
    pattern: Optional[str] = None
    activate: Optional[int] = None
    black_list: Optional[str] = None
    white_list: Optional[str] = None
    type: Optional[str] = None
    keywords: Optional[str] = None
    ai_flag: Optional[int] = None
    need_at: Optional[int] = None
    reply: Optional[str] = None
    module: Optional[str] = None
    level: Optional[int] = None
    priority: Optional[int] = None
    example: Optional[str] = None
    check_permission: Optional[int] = None
    score: Optional[int] = None
    balance: Optional[int] = None
    notes: Optional[str] = None


# ============================================================
# Routes: Permissions Management
# ============================================================

@router.get("/permissions")
async def get_permissions(
    page: int = 1,
    page_size: int = 10,
    search: str = None,
    activate: int = None,
    current_user: User = Depends(require_configured_api_permission("/api/permissions", "GET", allow_missing=False))
):
    """获取权限列表"""
    try:
        with Member() as m:
            m.__cursor__.execute("SELECT COUNT(*) FROM permission")
            total = m.__cursor__.fetchone()[0]

            sql = "SELECT * FROM permission"
            params = []
            conditions = []

            if search:
                conditions.append("(func LIKE ? OR func_name LIKE ? OR module LIKE ?)")
                params.extend([f"%{search}%", f"%{search}%", f"%{search}%"])

            if activate is not None:
                conditions.append("activate = ?")
                params.append(activate)

            if conditions:
                sql += " WHERE " + " AND ".join(conditions)
                count_sql = "SELECT COUNT(*) FROM permission WHERE " + " AND ".join(conditions)
                m.__cursor__.execute(count_sql, tuple(params))
                total = m.__cursor__.fetchone()[0]

            sql += " ORDER BY id DESC LIMIT ? OFFSET ?"
            params.extend([page_size, (page - 1) * page_size])

            m.__cursor__.execute(sql, tuple(params))
            rows = m.__cursor__.fetchall()
            # Get columns from cursor description
            columns = [description[0] for description in m.__cursor__.description]

            permissions = []
            for row in rows:
                permissions.append(dict(zip(columns, row)))

            return {
                "total": total,
                "page": page,
                "page_size": page_size,
                "data": permissions
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取权限列表失败: {str(e)}")


@router.post("/permissions")
async def create_permission(perm: PermissionCreate, current_user: User = Depends(require_configured_api_permission("/api/permissions", "POST", allow_missing=False))):
    """创建权限"""
    try:
        with Member() as m:
            rowcount = m.insert_permission(
                func=perm.func,
                func_name=perm.func_name,
                activate=perm.activate,
                black_list=perm.black_list,
                white_list=perm.white_list,
                type=perm.type,
                pattern=perm.pattern,
                keywords=perm.keywords,
                ai_flag=perm.ai_flag,
                need_at=perm.need_at,
                reply=perm.reply,
                module=perm.module,
                level=perm.level,
                priority=perm.priority,
                example=perm.example,
                check_permission=perm.check_permission,
                score=perm.score,
                balance=perm.balance,
                notes=perm.notes
            )
            if rowcount > 0:
                return {"status": "success", "message": "权限创建成功"}
            else:
                raise HTTPException(status_code=500, detail="权限创建失败")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"创建权限失败: {str(e)}")


@router.put("/permissions/{id}")
async def update_permission(id: int, perm: PermissionUpdate, current_user: User = Depends(require_configured_api_permission("/api/permissions/{id}", "PUT", allow_missing=False))):
    """更新权限信息"""
    try:
        update_data = {k: v for k, v in perm.dict().items() if v is not None}
        if not update_data:
            raise HTTPException(status_code=400, detail="没有提供更新数据")

        with Member() as m:
            if not m.get_permission_by_id(id):
                raise HTTPException(status_code=404, detail="权限ID不存在")

            rowcount = m.update_permission(id, **update_data)
            if rowcount > 0:
                return {"status": "success", "message": "权限更新成功"}
            else:
                return {"status": "success", "message": "没有数据被修改"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"更新权限失败: {str(e)}")


@router.delete("/permissions/{id}")
async def delete_permission(id: int, current_user: User = Depends(require_configured_api_permission("/api/permissions/{id}", "DELETE", allow_missing=False))):
    """删除权限"""
    try:
        with Member() as m:
            if not m.get_permission_by_id(id):
                raise HTTPException(status_code=404, detail="权限ID不存在")

            rowcount = m.delte_permission(id)
            if rowcount > 0:
                return {"status": "success", "message": "权限删除成功"}
            else:
                raise HTTPException(status_code=500, detail="权限删除失败")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"删除权限失败: {str(e)}")
