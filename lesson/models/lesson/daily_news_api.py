# -*- coding: utf-8 -*-
"""每日早报接口

- GET  /api/daily-news             读取早报（默认今日；date=YYYY-MM-DD 查历史）
- GET  /api/daily-news/dates       返回已缓存的日期列表（前端 DatePicker 标注）
- POST /api/daily-news/refresh     强制刷新当日（忽略缓存）
"""

import logging
import re
from datetime import datetime

from fastapi import APIRouter, HTTPException, Query

from models.api import daily_news
from models.daily_news_db import get_cached, list_dates

router = APIRouter()
logger = logging.getLogger(__name__)

_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _today_str() -> str:
    return datetime.now().strftime("%Y-%m-%d")


@router.get("/daily-news")
async def get_daily_news(
    date: str | None = Query(None, description="日期 YYYY-MM-DD，缺省=今日"),
    force: int = Query(0, ge=0, le=1, description="仅对今日生效：1=强制刷新"),
):
    """获取早报。

    - 未传 date 或 date=今日：走 daily_news() —— 先查库，缺失则请求 alapi。
    - date=历史日期：只查库；查不到直接 404，不请求外部 API（alapi 只返回当天）。
    """
    today = _today_str()
    target = date or today

    if not _DATE_RE.match(target):
        raise HTTPException(status_code=400, detail="日期格式应为 YYYY-MM-DD")

    if target > today:
        raise HTTPException(status_code=400, detail="日期不能晚于今天")

    if target != today:
        # 历史日期：只查库
        cached = get_cached(target)
        if not cached:
            raise HTTPException(status_code=404, detail=f"{target} 暂无早报数据")
        return {"success": True, "data": cached, "date": target, "from_cache": True}

    # 今日：走缓存 + 远端
    try:
        data = daily_news(force_refresh=bool(force))
    except Exception as exc:
        logger.error(f"daily_news 调用失败: {exc}")
        raise HTTPException(status_code=502, detail="每日早报获取失败")

    if not data:
        raise HTTPException(status_code=503, detail="暂无每日早报数据")

    return {"success": True, "data": data, "date": today, "from_cache": not bool(force)}


@router.get("/daily-news/dates")
async def get_daily_news_dates(limit: int = Query(90, ge=1, le=365)):
    """已缓存的日期列表（新→旧），供前端 DatePicker 标注可选项。"""
    return {"success": True, "data": list_dates(limit)}
