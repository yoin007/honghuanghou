# Batch38: 从 datas_api_legacy.py 拆分成员管理逻辑。

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

class MemberCreate(BaseModel):
    """会员创建请求参数"""
    uuid: str
    wxid: str
    alias: str
    active: int = 1
    score: int = 50
    balance: int = 0
    level: int = 1
    model: str = "basic"
    ai_flag: int = 0
    birthday: str = ""
    note: str = ""


class MemberUpdate(BaseModel):
    """会员更新请求参数"""
    alias: Optional[str] = None
    active: Optional[int] = None
    score: Optional[int] = None
    balance: Optional[int] = None
    level: Optional[int] = None
    model: Optional[str] = None
    ai_flag: Optional[int] = None
    birthday: Optional[str] = None


# ============================================================
# Routes: Members Management
# ============================================================

@router.get("/members", summary="获取成员列表", description="获取所有成员列表")
async def get_members(
    page: int = 1,
    page_size: int = 10,
    search: str = None,
    active: int = None,
    current_user: User = Depends(require_configured_api_permission("/api/members", "GET", allow_missing=False))
):
    """获取会员列表"""
    try:
        with Member() as m:
            rows = m.member_info() or []
            columns = m.member_columns()

            if search:
                keyword = str(search).lower()
                rows = [
                    row for row in rows
                    if any(keyword in str(value or "").lower() for value in (row[1], row[2], row[3]))
                ]

            if active is not None:
                rows = [row for row in rows if int(row[4] or 0) == int(active)]

            total = len(rows)
            offset = (page - 1) * page_size
            rows = rows[offset:offset + page_size]

            members = []
            for row in rows:
                members.append(dict(zip(columns, row)))

            return {
                "total": total,
                "page": page,
                "page_size": page_size,
                "data": members
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取会员列表失败: {str(e)}")


@router.post("/members")
async def create_member(member: MemberCreate, current_user: User = Depends(require_configured_api_permission("/api/members", "POST", allow_missing=False))):
    """创建会员"""
    try:
        with Member() as m:
            # Check if uuid exists
            if m.member_info(member.uuid):
                raise HTTPException(status_code=400, detail="会员UUID已存在")

            rowcount = m.insert_member(
                uuid=member.uuid,
                wxid=member.wxid,
                alias=member.alias,
                active=member.active,
                score=member.score,
                balance=member.balance,
                level=member.level,
                model=member.model,
                ai_flag=member.ai_flag,
                birthday=member.birthday,
                note=member.note
            )
            if rowcount > 0:
                return {"status": "success", "message": "会员创建成功"}
            else:
                raise HTTPException(status_code=500, detail="会员创建失败")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"创建会员失败: {str(e)}")


@router.put("/members/{uuid}")
async def update_member(uuid: str, member: MemberUpdate, current_user: User = Depends(require_configured_api_permission("/api/members/{uuid}", "PUT", allow_missing=False))):
    """更新会员信息"""
    try:
        update_data = {k: v for k, v in member.dict().items() if v is not None}
        if not update_data:
            raise HTTPException(status_code=400, detail="没有提供更新数据")

        with Member() as m:
            if not m.member_info(uuid):
                raise HTTPException(status_code=404, detail="会员不存在")

            rowcount = m.update_member(uuid, **update_data)
            if rowcount > 0:
                return {"status": "success", "message": "会员更新成功"}
            else:
                return {"status": "success", "message": "没有数据被修改"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"更新会员失败: {str(e)}")


@router.delete("/members/{uuid}")
async def delete_member(uuid: str, current_user: User = Depends(require_configured_api_permission("/api/members/{uuid}", "DELETE", allow_missing=False))):
    """删除会员"""
    try:
        with Member() as m:
            if not m.member_info(uuid):
                raise HTTPException(status_code=404, detail="会员不存在")

            rowcount = m.delte_member(uuid)
            if rowcount > 0:
                return {"status": "success", "message": "会员删除成功"}
            else:
                raise HTTPException(status_code=500, detail="会员删除失败")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"删除会员失败: {str(e)}")
