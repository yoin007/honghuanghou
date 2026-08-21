# -*- coding: utf-8 -*-
"""
院校信息搜索 API

读取 colleges.db（院校库），为毕业学生录取院校/专业录入提供搜索下拉数据
"""

import logging

from fastapi import APIRouter, Depends, Query

from utils.db_config import COLLEGES_DB
from utils.sqlite_moral_db import MoralDatabase
from .api_permission import require_configured_api_permission

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/colleges", tags=["院校信息"])

API_COLLEGES_SEARCH = "/api/moral/colleges/search"
API_MAJORS_SEARCH = "/api/moral/colleges/majors/search"


@router.get("/search", summary="搜索录取院校")
async def search_colleges(
    keyword: str = Query("", description="院校名称关键词"),
    limit: int = Query(20, ge=1, le=50, description="返回条数上限"),
    user=Depends(require_configured_api_permission(API_COLLEGES_SEARCH, "GET", allow_missing=False))
):
    """按名称关键词搜索院校库，用于录取院校下拉选择"""
    with MoralDatabase(COLLEGES_DB) as db:
        rows = db.query_all(
            """SELECT school_name, belong, nature, dual_class, level, location
            FROM schools WHERE school_name LIKE ?
            ORDER BY school_name LIMIT ?""",
            (f"%{keyword}%", limit)
        )
    return {"success": True, "data": [dict(r) for r in rows]}


@router.get("/majors/search", summary="搜索录取专业")
async def search_majors(
    keyword: str = Query("", description="专业名称关键词"),
    limit: int = Query(20, ge=1, le=50, description="返回条数上限"),
    user=Depends(require_configured_api_permission(API_MAJORS_SEARCH, "GET", allow_missing=False))
):
    """按名称关键词搜索专业库，用于录取专业下拉选择"""
    with MoralDatabase(COLLEGES_DB) as db:
        rows = db.query_all(
            """SELECT DISTINCT zymc, zydm, zyl FROM zyk
            WHERE zymc LIKE ? ORDER BY zymc LIMIT ?""",
            (f"%{keyword}%", limit)
        )
    return {"success": True, "data": [dict(r) for r in rows]}
