# -*- coding: utf-8 -*-
"""
数据库备份管理 API

提供数据库文件的备份、恢复、历史查询等功能
仅限管理员访问
"""

import os
import logging
import zipfile
import json
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from models.datas_api.auth import User
from models.datas_api.moral.api_permission import require_configured_api_permission
from models.datas_api.moral.base import log_operation, get_moral_db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin/database-backup", tags=["数据库备份"])

# API 路径常量
API_BACKUP_CONFIG = "/api/moral/admin/database-backup/config"
API_BACKUP_MANUAL = "/api/moral/admin/database-backup/manual"
API_BACKUP_HISTORY = "/api/moral/admin/database-backup/history"
API_BACKUP_DELETE = "/api/moral/admin/database-backup/delete/{backup_id}"
API_BACKUP_DOWNLOAD = "/api/moral/admin/database-backup/download/{backup_id}"
API_BACKUP_SCHEDULE = "/api/moral/admin/database-backup/schedule"

# 数据库目录
DATABASES_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), "databases")


def is_admin_user(user: User) -> bool:
    """检查是否是管理员"""
    return user.role in ["admin", "jiaowu"]


def get_backup_config(db) -> dict:
    """获取备份配置"""
    config = db.query_one(
        "SELECT config_value FROM moral_config WHERE config_key = 'backup_config'"
    )
    if config:
        try:
            return json.loads(config['config_value'])
        except:
            pass
    # 默认配置
    default_dir = os.path.join(os.path.dirname(DATABASES_DIR), "backups")
    return {
        "backup_dir": default_dir,
        "max_backups": 10,
        "include_wal": True
    }


def save_backup_config(db, config: dict):
    """保存备份配置"""
    config_value = json.dumps(config, ensure_ascii=False)
    existing = db.query_one(
        "SELECT config_id FROM moral_config WHERE config_key = 'backup_config'"
    )
    if existing:
        db.execute(
            "UPDATE moral_config SET config_value = ?, updated_at = datetime('now','localtime') WHERE config_key = 'backup_config'",
            (config_value,)
        )
    else:
        db.execute(
            "INSERT INTO moral_config (config_key, config_value, description) VALUES ('backup_config', ?, '数据库备份配置')",
            (config_value,)
        )


def get_backup_schedule_config(db) -> dict:
    """获取定时备份配置"""
    config = db.query_one(
        "SELECT config_value FROM moral_config WHERE config_key = 'backup_schedule'"
    )
    if config:
        try:
            return json.loads(config['config_value'])
        except:
            pass
    return {
        "enabled": False,
        "day_of_week": "sun",
        "hour": 3,
        "minute": 0
    }


def save_backup_schedule_config(db, config: dict):
    """保存定时备份配置"""
    config_value = json.dumps(config, ensure_ascii=False)
    existing = db.query_one(
        "SELECT config_id FROM moral_config WHERE config_key = 'backup_schedule'"
    )
    if existing:
        db.execute(
            "UPDATE moral_config SET config_value = ?, updated_at = datetime('now','localtime') WHERE config_key = 'backup_schedule'",
            (config_value,)
        )
    else:
        db.execute(
            "INSERT INTO moral_config (config_key, config_value, description) VALUES ('backup_schedule', ?, '定时备份配置')",
            (config_value,)
        )


def execute_backup_internal(db, backup_type: str = 'manual', operator: str = None,
                            operator_role: str = None, ip_address: str = None) -> dict:
    """
    执行数据库备份的核心函数

    Args:
        db: 数据库连接
        backup_type: 备份类型 ('manual'/'scheduled')
        operator: 操作者
        operator_role: 操作者角色
        ip_address: 请求 IP

    Returns:
        {"success": bool, "backup_id": int, "backup_name": str, "file_size": int, "error": str}
    """
    config = get_backup_config(db)
    backup_dir = os.path.expanduser(config.get('backup_dir', '~/backups'))
    backup_dir = os.path.abspath(backup_dir)

    # 确保备份目录存在
    try:
        os.makedirs(backup_dir, exist_ok=True)
    except Exception as e:
        return {"success": False, "error": f"无法创建备份目录: {str(e)}"}

    # 生成备份文件名
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_name = f"databases_backup_{timestamp}.zip"
    backup_path = os.path.join(backup_dir, backup_name)

    # 收集要备份的文件
    db_files = []
    try:
        for filename in os.listdir(DATABASES_DIR):
            if filename.endswith('.db') and 'backup' not in filename:
                db_files.append(filename)
                if config.get('include_wal'):
                    # 添加 WAL 和 SHM 文件
                    for ext in ['-wal', '-shm']:
                        wal_file = filename + ext
                        wal_path = os.path.join(DATABASES_DIR, wal_file)
                        if os.path.exists(wal_path):
                            db_files.append(wal_file)
    except Exception as e:
        return {"success": False, "error": f"扫描数据库目录失败: {str(e)}"}

    if not db_files:
        return {"success": False, "error": "未找到数据库文件"}

    # 创建 zip 压缩包（跨平台）
    try:
        with zipfile.ZipFile(backup_path, 'w', zipfile.ZIP_DEFLATED) as zf:
            for filename in db_files:
                file_path = os.path.join(DATABASES_DIR, filename)
                zf.write(file_path, arcname=filename)

        file_size = os.path.getsize(backup_path)
        file_count = len(db_files)

        # 记录备份历史
        db.execute(
            """INSERT INTO backup_history
            (backup_type, backup_name, backup_path, file_size, file_count, databases_list,
             backup_status, operator, operator_role, ip_address, completed_at)
            VALUES (?, ?, ?, ?, ?, ?, 'success', ?, ?, ?, datetime('now','localtime'))""",
            (backup_type, backup_name, backup_path, file_size, file_count,
             json.dumps(db_files), operator, operator_role, ip_address)
        )
        backup_id = db.lastrowid()

        # 清理旧备份
        cleanup_old_backups(db, backup_dir, config.get('max_backups', 10))

        return {"success": True, "backup_id": backup_id, "backup_name": backup_name, "file_size": file_size}

    except Exception as e:
        # 记录失败
        db.execute(
            """INSERT INTO backup_history
            (backup_type, backup_name, backup_path, backup_status, error_message, operator, operator_role)
            VALUES (?, ?, ?, 'failed', ?, ?, ?)""",
            (backup_type, backup_name, backup_path, str(e), operator, operator_role)
        )
        return {"success": False, "error": str(e)}


def cleanup_old_backups(db, backup_dir: str, max_backups: int):
    """清理超过 max_backups 数量的旧备份"""
    try:
        # 获取所有成功的备份记录（按时间排序）
        backups = db.query_all(
            """SELECT id, backup_path FROM backup_history
            WHERE backup_status = 'success'
            ORDER BY created_at DESC"""
        )

        if len(backups) > max_backups:
            # 删除超出数量的备份
            to_delete = backups[max_backups:]
            for backup in to_delete:
                backup_path = backup['backup_path']
                if os.path.exists(backup_path):
                    os.remove(backup_path)
                db.execute(
                    "DELETE FROM backup_history WHERE id = ?",
                    (backup['id'],)
                )
            logger.info(f"清理了 {len(to_delete)} 个旧备份")
    except Exception as e:
        logger.warning(f"清理旧备份失败: {e}")


# ==================== Pydantic 模型 ====================

class BackupConfigRequest(BaseModel):
    """备份配置请求"""
    backup_dir: str = Field(..., description="备份目录路径")
    max_backups: int = Field(default=10, ge=1, le=100, description="最大备份数量")
    include_wal: bool = Field(default=True, description="是否包含 WAL 文件")


class BackupScheduleRequest(BaseModel):
    """定时备份配置请求"""
    enabled: bool = Field(..., description="是否启用定时备份")
    day_of_week: str = Field(default="sun", description="备份日期（mon-sun 或 *）")
    hour: int = Field(default=3, ge=0, le=23, description="备份时间（小时）")
    minute: int = Field(default=0, ge=0, le=59, description="备份时间（分钟）")


# ==================== API 路由 ====================

@router.get("/config", summary="获取备份配置")
async def get_backup_config_api(
    user: User = Depends(require_configured_api_permission(API_BACKUP_CONFIG, "GET", allow_missing=False))
):
    """获取当前备份配置"""
    if not is_admin_user(user):
        raise HTTPException(403, "只有管理员可以访问")

    with get_moral_db() as db:
        config = get_backup_config(db)
        return {"success": True, "data": config}


@router.post("/config", summary="更新备份配置")
async def update_backup_config_api(
    request: BackupConfigRequest,
    req: Request,
    user: User = Depends(require_configured_api_permission(API_BACKUP_CONFIG, "POST", allow_missing=False))
):
    """更新备份配置"""
    if not is_admin_user(user):
        raise HTTPException(403, "只有管理员可以访问")

    with get_moral_db() as db:
        config = {
            "backup_dir": request.backup_dir,
            "max_backups": request.max_backups,
            "include_wal": request.include_wal
        }
        save_backup_config(db, config)

        log_operation(
            db=db,
            operator=user.username,
            operator_role=user.role,
            operation='UPDATE_BACKUP_CONFIG',
            table_name='moral_config',
            record_id=0,
            new_data=config,
            ip_address=req.client.host if req.client else None
        )

        return {"success": True, "message": "备份配置已更新", "data": config}


@router.post("/manual", summary="手动执行备份")
async def execute_manual_backup(
    req: Request,
    user: User = Depends(require_configured_api_permission(API_BACKUP_MANUAL, "POST", allow_missing=False))
):
    """手动触发数据库备份"""
    if not is_admin_user(user):
        raise HTTPException(403, "只有管理员可以执行备份")

    with get_moral_db() as db:
        result = execute_backup_internal(
            db,
            backup_type='manual',
            operator=user.username,
            operator_role=user.role,
            ip_address=req.client.host if req.client else None
        )

        if result['success']:
            log_operation(
                db=db,
                operator=user.username,
                operator_role=user.role,
                operation='MANUAL_BACKUP',
                table_name='backup_history',
                record_id=result['backup_id'],
                new_data={"backup_name": result['backup_name'], "file_size": result['file_size']},
                ip_address=req.client.host if req.client else None
            )
            return {
                "success": True,
                "message": f"备份成功：{result['backup_name']} ({result['file_size']} 字节)",
                "data": result
            }
        else:
            raise HTTPException(500, f"备份失败：{result['error']}")


@router.get("/history", summary="获取备份历史")
async def get_backup_history(
    page: int = 1,
    size: int = 20,
    backup_type: Optional[str] = None,
    user: User = Depends(require_configured_api_permission(API_BACKUP_HISTORY, "GET", allow_missing=False))
):
    """获取备份历史列表（分页）"""
    if not is_admin_user(user):
        raise HTTPException(403, "只有管理员可以访问")

    with get_moral_db() as db:
        conditions = []
        params = []

        if backup_type:
            conditions.append("backup_type = ?")
            params.append(backup_type)

        where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""

        # 查询总数
        count_query = f"SELECT COUNT(*) FROM backup_history {where_clause}"
        total = db.query_value(count_query, tuple(params) if params else None) or 0

        # 分页查询
        offset = (page - 1) * size
        list_query = f"""
            SELECT * FROM backup_history {where_clause}
            ORDER BY created_at DESC
            LIMIT ? OFFSET ?
        """
        params.extend([size, offset])
        backups = db.query_all(list_query, tuple(params))

        return {
            "success": True,
            "data": {
                "backups": backups,
                "total": total,
                "page": page,
                "size": size
            }
        }


@router.delete("/delete/{backup_id}", summary="删除备份文件")
async def delete_backup(
    backup_id: int,
    req: Request,
    user: User = Depends(require_configured_api_permission(API_BACKUP_DELETE, "DELETE", allow_missing=False))
):
    """删除指定备份文件"""
    if not is_admin_user(user):
        raise HTTPException(403, "只有管理员可以删除备份")

    with get_moral_db() as db:
        backup = db.query_one(
            "SELECT * FROM backup_history WHERE id = ?",
            (backup_id,)
        )
        if not backup:
            raise HTTPException(404, "备份记录不存在")

        backup_path = backup['backup_path']

        # 删除文件
        if os.path.exists(backup_path):
            os.remove(backup_path)

        # 删除记录
        db.execute("DELETE FROM backup_history WHERE id = ?", (backup_id,))

        log_operation(
            db=db,
            operator=user.username,
            operator_role=user.role,
            operation='DELETE_BACKUP',
            table_name='backup_history',
            record_id=backup_id,
            old_data={"backup_name": backup['backup_name']},
            ip_address=req.client.host if req.client else None
        )

        return {"success": True, "message": f"已删除备份 {backup['backup_name']}"}


@router.get("/download/{backup_id}", summary="下载备份文件")
async def download_backup(
    backup_id: int,
    user: User = Depends(require_configured_api_permission(API_BACKUP_DOWNLOAD, "GET", allow_missing=False))
):
    """下载备份文件"""
    if not is_admin_user(user):
        raise HTTPException(403, "只有管理员可以下载备份")

    with get_moral_db() as db:
        backup = db.query_one(
            "SELECT * FROM backup_history WHERE id = ?",
            (backup_id,)
        )
        if not backup:
            raise HTTPException(404, "备份记录不存在")

        backup_path = backup['backup_path']
        if not os.path.exists(backup_path):
            raise HTTPException(404, "备份文件不存在")

        return FileResponse(
            backup_path,
            filename=backup['backup_name'],
            media_type='application/zip'
        )


@router.get("/schedule", summary="获取定时备份配置")
async def get_backup_schedule_api(
    user: User = Depends(require_configured_api_permission(API_BACKUP_SCHEDULE, "GET", allow_missing=False))
):
    """获取定时备份配置"""
    if not is_admin_user(user):
        raise HTTPException(403, "只有管理员可以访问")

    with get_moral_db() as db:
        config = get_backup_schedule_config(db)
        return {"success": True, "data": config}


@router.post("/schedule", summary="更新定时备份配置")
async def update_backup_schedule_api(
    request: BackupScheduleRequest,
    req: Request,
    user: User = Depends(require_configured_api_permission(API_BACKUP_SCHEDULE, "POST", allow_missing=False))
):
    """更新定时备份配置"""
    if not is_admin_user(user):
        raise HTTPException(403, "只有管理员可以配置定时备份")

    with get_moral_db() as db:
        config = {
            "enabled": request.enabled,
            "day_of_week": request.day_of_week,
            "hour": request.hour,
            "minute": request.minute
        }
        save_backup_schedule_config(db, config)

        # 更新调度器任务
        from .scheduler import update_backup_job
        update_backup_job(config)

        log_operation(
            db=db,
            operator=user.username,
            operator_role=user.role,
            operation='UPDATE_BACKUP_SCHEDULE',
            table_name='moral_config',
            record_id=0,
            new_data=config,
            ip_address=req.client.host if req.client else None
        )

        return {"success": True, "message": "定时备份配置已更新", "data": config}