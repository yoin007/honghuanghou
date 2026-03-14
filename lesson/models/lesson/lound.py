from __future__ import annotations

import asyncio
import time
from typing import Dict, List

from fastapi import APIRouter, Query
from pydantic import BaseModel, Field


class LoudPKUpsertIn(BaseModel):
    class_code: str = Field(min_length=1, max_length=64)
    decibel: float = Field(ge=0, le=140)


class LoudPKItem(BaseModel):
    class_code: str
    decibel: float
    max_decibel: float
    updated_at_ms: int


class LoudPKStatsOut(BaseModel):
    stats: List[LoudPKItem]


class LoudPKStore:
    def __init__(self) -> None:
        self._lock = asyncio.Lock()
        self._data: Dict[str, LoudPKItem] = {}

    async def upsert(self, class_code: str, decibel: float) -> LoudPKItem:
        now_ms = int(time.time() * 1000)

        async with self._lock:
            existing = self._data.get(class_code)
            if existing:
                max_db = existing.max_decibel if existing.max_decibel >= decibel else decibel
            else:
                max_db = decibel

            item = LoudPKItem(
                class_code=class_code,
                decibel=decibel,
                max_decibel=max_db,
                updated_at_ms=now_ms,
            )
            self._data[class_code] = item
            return item

    async def list(self, ttl_seconds: int) -> List[LoudPKItem]:
        now_ms = int(time.time() * 1000)
        cutoff_ms = now_ms - ttl_seconds * 1000

        async with self._lock:
            if ttl_seconds > 0:
                self._data = {
                    k: v for k, v in self._data.items() if v.updated_at_ms >= cutoff_ms
                }
            return sorted(self._data.values(), key=lambda x: x.decibel, reverse=True)


store = LoudPKStore()
router = APIRouter()


@router.post("/loudpk", response_model=LoudPKItem)
async def loudpk_upsert(payload: LoudPKUpsertIn) -> LoudPKItem:
    return await store.upsert(payload.class_code, payload.decibel)


@router.get("/loudpk", response_model=LoudPKStatsOut)
async def loudpk_stats(
    ttl: int = Query(default=30, ge=0, le=3600),
) -> LoudPKStatsOut:
    stats = await store.list(ttl_seconds=ttl)
    return LoudPKStatsOut(stats=stats)