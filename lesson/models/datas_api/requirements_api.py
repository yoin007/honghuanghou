# -*- coding: utf-8 -*-
"""需求中心：老师提交功能需求、跟踪处理进度；教务/管理员管理状态。

数据存 moral.db（与教师待办同库），表结构幂等自动迁移，不动服务器既有数据。

权限口径（yaml 配置 + 代码双重校验）：
- 提交需求 / 查看自己的需求 / 追加说明：全体登录角色
- 查看全部需求 / 更新状态：jiaowu + admin

流程状态（与 docs/process/collaboration-workflow.md 六阶段对应）：
pending 待澄清 → designing 设计中 → reviewing 待审核 → developing 开发中
→ accepting 待验收 → done 已上线；任意阶段可转 deferred 已搁置。
"""

import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from models.datas_api.auth import User, is_admin_user
from models.datas_api.moral.api_permission import require_configured_api_permission
from models.datas_api.moral.base import get_moral_db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/requirements", tags=["需求中心"])

REQUIREMENT_STATUSES = {
    "pending": "待澄清",
    "designing": "设计中",
    "reviewing": "待审核",
    "developing": "开发中",
    "accepting": "待验收",
    "done": "已上线",
    "deferred": "已搁置",
}

MANAGE_ROLES = ("jiaowu", "admin")

TABLE_SQL = [
    """CREATE TABLE IF NOT EXISTS requirement (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        problem TEXT NOT NULL,
        scenario TEXT,
        expectation TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'pending',
        submitter_id TEXT NOT NULL,
        submitter_name TEXT NOT NULL,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    )""",
    """CREATE TABLE IF NOT EXISTS requirement_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        requirement_id INTEGER NOT NULL,
        actor_name TEXT NOT NULL,
        action TEXT NOT NULL,
        note TEXT,
        created_at TEXT NOT NULL
    )""",
    "CREATE INDEX IF NOT EXISTS idx_requirement_submitter ON requirement(submitter_id)",
    "CREATE INDEX IF NOT EXISTS idx_requirement_log_req ON requirement_log(requirement_id)",
]


def _ensure_requirements_schema():
    """幂等建表（自动迁移）。"""
    with get_moral_db() as db:
        for sql in TABLE_SQL:
            db.execute(sql)
        db.commit()


def _is_manager(user: User) -> bool:
    """jiaowu 或 admin（与 require_jiaowu 同口径）。"""
    return is_admin_user(user) or "jiaowu" in (user.role or "").split("/")


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _requirement_no(row_id: int) -> str:
    return f"REQ-{datetime.now().year}-{row_id:03d}"


def _row_to_dict(row: dict) -> dict:
    return {
        "id": row["id"],
        "requirement_no": _requirement_no(row["id"]),
        "title": row["title"],
        "problem": row["problem"],
        "scenario": row["scenario"],
        "expectation": row["expectation"],
        "status": row["status"],
        "status_label": REQUIREMENT_STATUSES.get(row["status"], row["status"]),
        "submitter_name": row["submitter_name"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def _get_requirement(db, requirement_id: int) -> Optional[dict]:
    return db.query_one("SELECT * FROM requirement WHERE id = ?", (requirement_id,))


def _add_log(db, requirement_id: int, actor: str, action: str, note: Optional[str]):
    db.execute(
        """INSERT INTO requirement_log (requirement_id, actor_name, action, note, created_at)
           VALUES (?, ?, ?, ?, ?)""",
        (requirement_id, actor, action, note, _now()),
    )


class RequirementCreate(BaseModel):
    """提交需求"""
    title: str = Field(..., min_length=2, max_length=60, description="一句话概括")
    problem: str = Field(..., min_length=5, max_length=2000, description="遇到什么问题")
    scenario: Optional[str] = Field(None, max_length=1000, description="谁在什么场景遇到（选填）")
    expectation: str = Field(..., min_length=5, max_length=2000, description="希望达到什么效果")


class StatusUpdate(BaseModel):
    """更新需求状态（教务/管理员）"""
    status: str = Field(..., description="目标状态，见 REQUIREMENT_STATUSES")
    note: Optional[str] = Field(None, max_length=2000, description="处理说明")


class CommentCreate(BaseModel):
    """追加补充说明"""
    note: str = Field(..., min_length=1, max_length=2000)


@router.post("", summary="提交功能需求")
def submit_requirement(
    request: RequirementCreate,
    user: User = Depends(require_configured_api_permission("/api/requirements", "POST")),
):
    """老师提交新需求，全员可用。"""
    _ensure_requirements_schema()
    with get_moral_db() as db:
        now = _now()
        db.execute(
            """INSERT INTO requirement
               (title, problem, scenario, expectation, status,
                submitter_id, submitter_name, created_at, updated_at)
               VALUES (?, ?, ?, ?, 'pending', ?, ?, ?, ?)""",
            (request.title.strip(), request.problem.strip(), (request.scenario or "").strip(),
             request.expectation.strip(), user.username, user.username, now, now),
        )
        requirement_id = db.lastrowid()
        _add_log(db, requirement_id, user.username, "submit", "提交需求")
        db.commit()

    logger.info(f"[requirements] 新需求 {_requirement_no(requirement_id)}：{request.title}（{user.username}）")
    return {"success": True, "data": {
        "id": requirement_id,
        "requirement_no": _requirement_no(requirement_id),
        "status": "pending",
        "status_label": REQUIREMENT_STATUSES["pending"],
    }}


@router.get("", summary="查询需求列表")
def list_requirements(
    scope: str = "mine",
    user: User = Depends(require_configured_api_permission("/api/requirements", "GET")),
):
    """scope=mine 查自己的（全员）；scope=all 查全部（仅 jiaowu/admin）。"""
    _ensure_requirements_schema()
    if scope == "all":
        if not _is_manager(user):
            raise HTTPException(403, "只有教务或管理员可以查看全部需求")
        where, params = "", ()
    else:
        where, params = "WHERE submitter_id = ?", (user.username,)

    with get_moral_db() as db:
        rows = db.query_all(
            f"SELECT * FROM requirement {where} ORDER BY updated_at DESC, id DESC",
            params,
        )
    return {"success": True, "data": [_row_to_dict(r) for r in rows]}


@router.get("/{requirement_id}", summary="需求详情与进展时间线")
def get_requirement_detail(
    requirement_id: int,
    user: User = Depends(require_configured_api_permission("/api/requirements/{requirement_id}", "GET")),
):
    _ensure_requirements_schema()
    with get_moral_db() as db:
        row = _get_requirement(db, requirement_id)
        if not row:
            raise HTTPException(404, "需求不存在")
        if row["submitter_id"] != user.username and not _is_manager(user):
            raise HTTPException(403, "只能查看自己提交的需求")
        logs = db.query_all(
            "SELECT * FROM requirement_log WHERE requirement_id = ? ORDER BY created_at DESC, id DESC",
            (requirement_id,),
        )
    data = _row_to_dict(row)
    data["logs"] = [{
        "actor_name": l["actor_name"],
        "action": l["action"],
        "note": l["note"],
        "created_at": l["created_at"],
    } for l in logs]
    return {"success": True, "data": data}


@router.put("/{requirement_id}/status", summary="更新需求状态")
def update_requirement_status(
    requirement_id: int,
    request: StatusUpdate,
    user: User = Depends(require_configured_api_permission("/api/requirements/{requirement_id}/status", "PUT")),
):
    """推进需求状态，仅 jiaowu/admin（yaml 权限 + 代码双重校验）；动作留痕。"""
    if not _is_manager(user):
        raise HTTPException(403, "只有教务或管理员可以更新需求状态")
    if request.status not in REQUIREMENT_STATUSES:
        raise HTTPException(400, f"未知状态：{request.status}，可选：{'/'.join(REQUIREMENT_STATUSES)}")
    _ensure_requirements_schema()
    with get_moral_db() as db:
        row = _get_requirement(db, requirement_id)
        if not row:
            raise HTTPException(404, "需求不存在")
        db.execute(
            "UPDATE requirement SET status = ?, updated_at = ? WHERE id = ?",
            (request.status, _now(), requirement_id),
        )
        note = request.note or f"状态更新为「{REQUIREMENT_STATUSES[request.status]}」"
        _add_log(db, requirement_id, user.username, "status", note)
        db.commit()
    return {"success": True, "data": {"status": request.status, "status_label": REQUIREMENT_STATUSES[request.status]}}


@router.post("/{requirement_id}/comments", summary="追加补充说明")
def add_requirement_comment(
    requirement_id: int,
    request: CommentCreate,
    user: User = Depends(require_configured_api_permission("/api/requirements/{requirement_id}/comments", "POST")),
):
    """提交人补充信息，或教务/管理员留痕沟通记录。"""
    _ensure_requirements_schema()
    with get_moral_db() as db:
        row = _get_requirement(db, requirement_id)
        if not row:
            raise HTTPException(404, "需求不存在")
        if row["submitter_id"] != user.username and not _is_manager(user):
            raise HTTPException(403, "没有权限操作这条需求")
        _add_log(db, requirement_id, user.username, "comment", request.note.strip())
        db.execute("UPDATE requirement SET updated_at = ? WHERE id = ?", (_now(), requirement_id))
        db.commit()
    return {"success": True}
