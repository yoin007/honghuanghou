# -*- coding: utf-8 -*-
"""
通用附件管理模块

为德育事件、教师待办等业务提供统一的图片/文档/音频附件上传、存储、
查询和下载能力。

安全设计：
- 扩展名 + MIME + magic bytes 三重校验
- 图片用 Pillow 重新编码，剥离 EXIF，防止嵌入脚本
- 文件系统使用 UUID 文件名，禁止路径遍历
- 下载必须通过鉴权接口，不允许静态目录直接暴露
"""

import io
import logging
import mimetypes
import os
import uuid
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional

from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    UploadFile,
    status,
)
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from models.datas_api.auth import User, is_admin_user
from utils.paths import get_filegather_storage_root
from .api_permission import (
    require_configured_api_permission,
    ensure_api_permission_schema,
    _ensure_module,
    _json_dump,
    _json_dict_dump,
)
from .base import get_moral_db, get_record_data_scope, record_in_scope

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/attachments", tags=["通用附件"])

API_ATTACHMENT_UPLOAD = "/api/moral/attachments/upload"
API_ATTACHMENT_DOWNLOAD = "/api/moral/attachments/{attachment_id}"
API_ATTACHMENT_DELETE = "/api/moral/attachments/{attachment_id}"

# =============================================================================
# 允许上传的类型配置
# =============================================================================

ALLOWED_IMAGE_EXTENSIONS = {"jpg", "jpeg", "png", "gif", "webp", "bmp"}
ALLOWED_DOCUMENT_EXTENSIONS = {"pdf", "xlsx", "xls", "docx", "doc", "pptx", "ppt"}
ALLOWED_AUDIO_EXTENSIONS = {"mp3", "wav"}
ALLOWED_EXTENSIONS = (
    ALLOWED_IMAGE_EXTENSIONS
    | ALLOWED_DOCUMENT_EXTENSIONS
    | ALLOWED_AUDIO_EXTENSIONS
)

_EXTENSION_TO_FILE_TYPE = {
    ext: "image"
    for ext in ALLOWED_IMAGE_EXTENSIONS
}
_EXTENSION_TO_FILE_TYPE.update({ext: "document" for ext in ALLOWED_DOCUMENT_EXTENSIONS})
_EXTENSION_TO_FILE_TYPE.update({ext: "audio" for ext in ALLOWED_AUDIO_EXTENSIONS})

_EXTENSION_TO_MIME = {
    "jpg": "image/jpeg",
    "jpeg": "image/jpeg",
    "png": "image/png",
    "gif": "image/gif",
    "webp": "image/webp",
    "bmp": "image/bmp",
    "pdf": "application/pdf",
    "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "xls": "application/vnd.ms-excel",
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "doc": "application/msword",
    "pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    "ppt": "application/vnd.ms-powerpoint",
    "mp3": "audio/mpeg",
    "wav": "audio/wav",
}

MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
MAX_ATTACHMENTS_PER_RECORD = 3
IMAGE_MAX_DIMENSION = 1280
THUMBNAIL_MAX_DIMENSION = 400
JPEG_QUALITY = 85

# 各业务类型查看附件所需的数据范围权限配置
_RECORD_TYPE_VIEW_META = {
    "student_daily_record": {
        "api_path": "/api/moral/daily-records",
        "all_permissions": ["moral_record_manage", "report_view_all"],
        "own_class_permissions": ["moral_record_own_class", "report_view_own_class"],
        "own_permissions": ["moral_record_input", "moral_record_view_own"],
        "id_column": "record_id",
        "record_query": "SELECT record_id, class_id, recorder FROM student_daily_record WHERE record_id = ?",
    },
    "student_school_record": {
        "api_path": "/api/moral/school-records",
        "all_permissions": ["moral_record_manage", "report_view_all"],
        "own_class_permissions": ["moral_record_own_class", "report_view_own_class"],
        "own_permissions": ["moral_record_input", "moral_record_view_own"],
        "id_column": "record_id",
        "record_query": "SELECT record_id, class_id, recorder FROM student_school_record WHERE record_id = ?",
    },
    "punishment_record": {
        "api_path": "/api/moral/punishments",
        "all_permissions": ["punishment_manage", "report_view_all"],
        "own_class_permissions": ["moral_record_own_class", "report_view_own_class"],
        "own_permissions": ["moral_record_input", "moral_record_view_own"],
        "id_column": "id",
        "record_query": "SELECT id AS record_id, class_id, recorder FROM punishment_record WHERE id = ?",
    },
    "moment_record": {
        "api_path": "/api/moral/moment-records",
        "all_permissions": ["moment_view_all", "moral_record_manage", "report_view_all"],
        "own_class_permissions": ["moral_record_own_class", "report_view_own_class"],
        "own_permissions": ["moment_create", "moment_view_own"],
        "id_column": "record_id",
        "record_query": "SELECT record_id, class_id, recorder FROM moment_record WHERE record_id = ?",
    },
    "collective_event": {
        "api_path": "/api/moral/collective-events",
        "all_permissions": ["report_view_all", "moral_record_manage"],
        "own_class_permissions": ["moral_record_own_class", "report_view_own_class"],
        "own_permissions": [],
        "id_column": "event_id",
        "record_query": "SELECT event_id AS record_id, class_id, created_by AS recorder FROM collective_event WHERE event_id = ?",
    },
    "teacher_todo_series": {
        "api_path": "/api/teacher/todos",
        "all_permissions": [],
        "own_class_permissions": [],
        "own_permissions": [],
        "id_column": "id",
        "record_query": "SELECT id AS record_id, creator_teacher_id AS recorder FROM teacher_todo_series WHERE id = ?",
    },
}


# =============================================================================
# Pydantic 模型
# =============================================================================

class AttachmentIdsPayload(BaseModel):
    """用于业务接口接收附件 ID 列表"""
    attachment_ids: Optional[List[int]] = Field(None, description="附件 ID 列表，最多 3 个")


# =============================================================================
# 存储路径
# =============================================================================

def _get_config_storage_root() -> str:
    """附件/文件收集存储根目录，从 lesson.yaml 读取，失败时使用默认路径。"""
    return get_filegather_storage_root()


def _get_attachments_root() -> str:
    """附件存储根目录。"""
    return os.path.join(_get_config_storage_root(), "attachments")


def _get_record_attachment_dir(record_type: str) -> str:
    """某类业务记录的附件目录：attachments/{record_type}/{YYYYMM}"""
    now = datetime.now()
    path = os.path.join(_get_attachments_root(), record_type, f"{now.year}{now.month:02d}")
    os.makedirs(path, exist_ok=True)
    return path


def _resolve_stored_path(stored_path: str) -> str:
    """将数据库存储的相对路径解析为绝对路径。"""
    if os.path.isabs(stored_path):
        return stored_path
    return os.path.join(_get_attachments_root(), stored_path)


# =============================================================================
# Schema
# =============================================================================

def ensure_attachment_schema(db) -> None:
    """幂等创建附件表和索引。"""
    db.execute(
        """
        CREATE TABLE IF NOT EXISTS record_attachment (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            record_type TEXT NOT NULL,
            record_id INTEGER NOT NULL DEFAULT 0,
            uploader TEXT NOT NULL,
            original_name TEXT NOT NULL,
            stored_path TEXT NOT NULL,
            thumbnail_path TEXT,
            file_size INTEGER NOT NULL,
            file_type TEXT NOT NULL,
            mime_type TEXT,
            created_at TEXT DEFAULT (datetime('now', 'localtime'))
        )
        """
    )
    db.execute(
        "CREATE INDEX IF NOT EXISTS idx_attachment_record ON record_attachment(record_type, record_id)"
    )
    db.execute(
        "CREATE INDEX IF NOT EXISTS idx_attachment_uploader ON record_attachment(uploader)"
    )
    db.execute(
        "CREATE INDEX IF NOT EXISTS idx_attachment_created ON record_attachment(created_at)"
    )
    _ensure_attachment_api_permissions(db)


def _ensure_attachment_api_permissions(db) -> None:
    """为新附件接口自动补齐 API 权限配置，避免未配置导致鉴权失败。"""
    try:
        ensure_api_permission_schema(db)
    except Exception as exc:
        logger.warning(f"补齐 API 权限表结构失败: {exc}")
        return

    module_id = _ensure_module(
        db, "common_attachment", "通用附件", ["teacher", "cleader", "xuefa", "admin"], 0
    )

    # 注意：api_permission_config.api_path 为唯一约束，同一路径只能有一行配置，
    # http_method='*' 表示对所有方法生效。下载(GET)与删除(DELETE)共用同一路径，
    # 因此合并为一行，粗粒度角色门放行登录用户，细粒度鉴权在接口内完成
    # （下载走 _can_view_attachment 记录级数据范围，删除限上传者/管理员）。
    # (api_path, http_method, api_name, allowed_roles, min_level, action_type, match_type)
    # 带路径参数的路径必须用 pattern 匹配，exact 只做整串相等比较
    endpoints = [
        (
            "/api/moral/attachments/upload",
            "POST",
            "上传附件",
            ["teacher", "cleader", "xuefa", "admin"],
            0,
            "operate",
            "exact",
        ),
        (
            "/api/moral/attachments/{attachment_id}",
            "*",
            "附件下载/删除",
            [],
            0,
            "view",
            "pattern",
        ),
    ]

    for api_path, http_method, api_name, allowed_roles, min_level, action_type, match_type in endpoints:
        existing = db.query_one(
            "SELECT id, http_method, match_type FROM api_permission_config WHERE api_path = ?",
            (api_path,),
        )
        if existing:
            # 自愈：早期版本可能以 exact/错误方法写入，纠正匹配方式
            if existing.get("http_method") != http_method or existing.get("match_type") != match_type:
                db.execute(
                    "UPDATE api_permission_config SET http_method = ?, match_type = ? WHERE id = ?",
                    (http_method, match_type, existing["id"]),
                )
            continue
        db.execute(
            """
            INSERT INTO api_permission_config
            (api_path, api_name, api_group, allowed_roles, min_level, module_id,
             http_method, match_type, policy_mode, is_active, enforce_backend,
             resource_type, action_type, data_scope_rules, target_scope_rules, operation_scope_rules)
            VALUES (?, ?, 'common_attachment', ?, ?, ?, ?, ?, 'role_and_level', 1, 1,
                    'common_attachment', ?, ?, ?, ?)
            """,
            (
                api_path,
                api_name,
                _json_dump(allowed_roles),
                min_level,
                module_id,
                http_method,
                match_type,
                action_type,
                _json_dict_dump({}),
                _json_dict_dump({}),
                _json_dict_dump({}),
            ),
        )
        logger.info(f"已自动创建附件接口权限配置: {api_path} {http_method}")


# =============================================================================
# 校验与图片处理
# =============================================================================

def _validate_magic_bytes(content: bytes, ext: str) -> bool:
    """对非图片文件做简单的 magic bytes 校验。"""
    if not content:
        return False

    header = content[:16]

    if ext in ("pdf",):
        return header.startswith(b"%PDF")

    if ext in ("mp3",):
        return (
            header.startswith(b"ID3")
            or header[:2] in (b"\xff\xfb", b"\xff\xf3", b"\xff\xf2")
        )

    if ext in ("wav",):
        return header[:4] == b"RIFF" and header[8:12] == b"WAVE"

    if ext in ("xlsx", "docx", "pptx"):
        return header[:4] == b"PK\x03\x04"

    if ext in ("xls", "doc", "ppt"):
        return header[:8] == b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"

    return True


def _normalize_image(content: bytes, ext: str) -> tuple:
    """
    用 Pillow 打开并重新编码图片：
    - 自动旋转（根据 EXIF）
    - 等比缩放最大边到 IMAGE_MAX_DIMENSION
    - 统一保存为 JPEG，剥离元数据
    返回 (标准化后的字节, 新的扩展名)
    """
    from PIL import Image, ExifTags, ImageOps

    img = Image.open(io.BytesIO(content))

    # 自动根据 EXIF Orientation 旋转
    try:
        img = ImageOps.exif_transpose(img)
    except Exception as exc:
        logger.debug(f"EXIF 旋转失败: {exc}")

    # 转换为 RGB（处理 CMYK、RGBA 等）
    if img.mode not in ("RGB", "L"):
        # 透明通道转为白色背景
        if img.mode in ("RGBA", "P"):
            rgb_img = Image.new("RGB", img.size, (255, 255, 255))
            rgb_img.paste(img, mask=img.split()[-1] if img.mode == "RGBA" else None)
            img = rgb_img
        else:
            img = img.convert("RGB")

    # 等比缩放
    max_dim = max(img.width, img.height)
    if max_dim > IMAGE_MAX_DIMENSION:
        ratio = IMAGE_MAX_DIMENSION / max_dim
        new_size = (int(img.width * ratio), int(img.height * ratio))
        img = img.resize(new_size, Image.LANCZOS)

    output = io.BytesIO()
    img.save(output, format="JPEG", quality=JPEG_QUALITY, optimize=True)
    output.seek(0)
    return output.read(), "jpg"


def _make_thumbnail(content: bytes) -> bytes:
    """生成缩略图（JPEG），最大边不超过 THUMBNAIL_MAX_DIMENSION。"""
    from PIL import Image

    img = Image.open(io.BytesIO(content))
    if img.mode not in ("RGB", "L"):
        img = img.convert("RGB")
    img.thumbnail((THUMBNAIL_MAX_DIMENSION, THUMBNAIL_MAX_DIMENSION), Image.LANCZOS)
    output = io.BytesIO()
    img.save(output, format="JPEG", quality=JPEG_QUALITY, optimize=True)
    output.seek(0)
    return output.read()


def _validate_attachment(file: UploadFile) -> tuple:
    """
    校验上传文件，返回 (扩展名, 文件类型, MIME 类型)。
    校验失败直接抛出 HTTPException。
    """
    filename = file.filename or ""
    if "." not in filename:
        raise HTTPException(status_code=400, detail="文件名缺少扩展名")

    ext = filename.rsplit(".", 1)[-1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"不支持的文件格式: {ext}，允许的图片/文档/音频格式：{', '.join(sorted(ALLOWED_EXTENSIONS))}",
        )

    file_type = _EXTENSION_TO_FILE_TYPE[ext]
    expected_mime = _EXTENSION_TO_MIME.get(ext)

    # MIME 校验
    guessed_mime, _ = mimetypes.guess_type(filename)
    content_type = file.content_type or guessed_mime
    if expected_mime and content_type and content_type.lower() != expected_mime.lower():
        raise HTTPException(
            status_code=400,
            detail=f"文件扩展名与 MIME 类型不匹配: {ext} vs {content_type}",
        )

    return ext, file_type, expected_mime


def _read_and_validate_content(file: UploadFile, ext: str, file_type: str) -> bytes:
    """读取文件内容并校验大小和 magic bytes。"""
    try:
        content = file.file.read()
    except Exception as exc:
        logger.warning(f"读取上传文件失败: {exc}")
        raise HTTPException(status_code=400, detail="读取文件失败")

    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"文件大小超过 {MAX_FILE_SIZE // 1024 // 1024}MB 限制",
        )

    if file_type != "image" and not _validate_magic_bytes(content, ext):
        raise HTTPException(status_code=400, detail="文件内容格式与扩展名不符")

    return content


# =============================================================================
# 核心 CRUD
# =============================================================================

def save_attachment(
    db,
    file: UploadFile,
    uploader: str,
    record_type: str = "",
    record_id: int = 0,
) -> Dict:
    """
    保存单个附件。

    返回的 dict 包含：id, record_type, record_id, original_name, file_type,
    file_size, mime_type, url, thumbnail_url。
    """
    ensure_attachment_schema(db)

    ext, file_type, mime_type = _validate_attachment(file)
    content = _read_and_validate_content(file, ext, file_type)

    stored_ext = ext
    thumbnail_content = None
    if file_type == "image":
        content, stored_ext = _normalize_image(content, ext)
        try:
            thumbnail_content = _make_thumbnail(content)
        except Exception as exc:
            logger.warning(f"生成缩略图失败: {exc}")

    file_uuid = uuid.uuid4().hex
    upload_dir = _get_record_attachment_dir(record_type or "unlinked")
    main_filename = f"{file_uuid}.{stored_ext}"
    main_path = os.path.join(upload_dir, main_filename)

    # 相对存储路径，便于迁移
    relative_path = os.path.relpath(main_path, _get_attachments_root())

    with open(main_path, "wb") as fp:
        fp.write(content)

    thumbnail_path = None
    if thumbnail_content:
        thumb_filename = f"{file_uuid}_thumb.jpg"
        thumb_full_path = os.path.join(upload_dir, thumb_filename)
        with open(thumb_full_path, "wb") as fp:
            fp.write(thumbnail_content)
        thumbnail_path = os.path.relpath(thumb_full_path, _get_attachments_root())

    db.execute(
        """
        INSERT INTO record_attachment
        (record_type, record_id, uploader, original_name, stored_path, thumbnail_path,
         file_size, file_type, mime_type)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            record_type or "unlinked",
            record_id,
            uploader,
            file.filename,
            relative_path,
            thumbnail_path,
            len(content),
            file_type,
            mime_type,
        ),
    )
    attachment_id = db.lastrowid()

    return _attachment_to_dict(
        {
            "id": attachment_id,
            "record_type": record_type or "unlinked",
            "record_id": record_id,
            "uploader": uploader,
            "original_name": file.filename,
            "stored_path": relative_path,
            "thumbnail_path": thumbnail_path,
            "file_size": len(content),
            "file_type": file_type,
            "mime_type": mime_type,
        }
    )


def _attachment_to_dict(row: Dict) -> Dict:
    """将附件记录转换为对外返回的字典。"""
    attachment_id = row["id"]
    return {
        "id": attachment_id,
        "record_type": row.get("record_type"),
        "record_id": row.get("record_id"),
        "uploader": row.get("uploader"),
        "original_name": row.get("original_name"),
        "file_type": row.get("file_type"),
        "file_size": row.get("file_size"),
        "mime_type": row.get("mime_type"),
        "url": f"/api/moral/attachments/{attachment_id}",
        "thumbnail_url": f"/api/moral/attachments/{attachment_id}?thumbnail=1"
        if row.get("thumbnail_path")
        else None,
    }


def get_attachments(db, record_type: str, record_id: int) -> List[Dict]:
    """查询某条业务记录关联的所有附件。"""
    ensure_attachment_schema(db)
    rows = db.query_all(
        """
        SELECT id, record_type, record_id, uploader, original_name, stored_path,
               thumbnail_path, file_size, file_type, mime_type
        FROM record_attachment
        WHERE record_type = ? AND record_id = ?
        ORDER BY created_at ASC
        """,
        (record_type, record_id),
    )
    return [_attachment_to_dict(row) for row in rows]


def get_attachment_count(db, record_type: str, record_id: int) -> int:
    """查询某条业务记录的附件数量。"""
    ensure_attachment_schema(db)
    return db.query_value(
        "SELECT COUNT(*) FROM record_attachment WHERE record_type = ? AND record_id = ?",
        (record_type, record_id),
    ) or 0


def get_attachment_export_files(db, record_type: str, record_id: int) -> List[Dict]:
    """
    供 Excel/PDF 导出使用的附件元数据，包含本地文件绝对路径。

    返回每个附件的字典包含：
    - id, original_name, file_type, mime_type
    - abs_path: 主文件绝对路径
    - thumbnail_abs_path: 缩略图绝对路径（图片）
    """
    ensure_attachment_schema(db)
    rows = db.query_all(
        """
        SELECT id, original_name, stored_path, thumbnail_path,
               file_type, mime_type
        FROM record_attachment
        WHERE record_type = ? AND record_id = ?
        ORDER BY created_at ASC
        """,
        (record_type, record_id),
    )
    result = []
    for row in rows:
        abs_path = _resolve_stored_path(row["stored_path"])
        thumb_abs = None
        if row.get("thumbnail_path"):
            thumb_abs = _resolve_stored_path(row["thumbnail_path"])
        result.append({
            "id": row["id"],
            "original_name": row["original_name"],
            "file_type": row["file_type"],
            "mime_type": row["mime_type"],
            "abs_path": abs_path,
            "thumbnail_abs_path": thumb_abs,
        })
    return result


def link_attachments(
    db,
    record_type: str,
    record_id: int,
    attachment_ids: Optional[List[int]],
    uploader: Optional[str] = None,
) -> List[Dict]:
    """
    将一组未关联（record_id=0）的附件绑定到业务记录。

    - 校验 attachment_ids 是否真实存在且未关联其他记录
    - 校验绑定后总数不超过 MAX_ATTACHMENTS_PER_RECORD
    """
    ensure_attachment_schema(db)
    if not attachment_ids:
        return []

    attachment_ids = [int(aid) for aid in attachment_ids]
    if len(attachment_ids) > MAX_ATTACHMENTS_PER_RECORD:
        raise HTTPException(
            status_code=400,
            detail=f"每条记录最多关联 {MAX_ATTACHMENTS_PER_RECORD} 个附件",
        )

    placeholders = ",".join(["?"] * len(attachment_ids))
    rows = db.query_all(
        f"""
        SELECT id, record_id, record_type, uploader
        FROM record_attachment
        WHERE id IN ({placeholders})
        """,
        tuple(attachment_ids),
    )
    found_ids = {row["id"] for row in rows}
    missing = set(attachment_ids) - found_ids
    if missing:
        raise HTTPException(status_code=400, detail=f"附件不存在: {missing}")

    for row in rows:
        if row["record_id"] != 0 and (
            row["record_type"] != record_type or row["record_id"] != record_id
        ):
            raise HTTPException(status_code=400, detail=f"附件 {row['id']} 已关联其他记录")

    existing_count = get_attachment_count(db, record_type, record_id)
    new_count = sum(
        1 for row in rows if row["record_id"] == 0 or row["record_id"] != record_id
    )
    if existing_count + new_count > MAX_ATTACHMENTS_PER_RECORD:
        raise HTTPException(
            status_code=400,
            detail=f"该记录附件总数不能超过 {MAX_ATTACHMENTS_PER_RECORD} 个",
        )

    db.execute(
        f"""
        UPDATE record_attachment
        SET record_type = ?, record_id = ?
        WHERE id IN ({placeholders}) AND record_id = 0
        """,
        (record_type, record_id, *attachment_ids),
    )

    # 重新查询返回
    return get_attachments(db, record_type, record_id)


def update_record_attachments(
    db,
    record_type: str,
    record_id: int,
    attachment_ids: Optional[List[int]],
    operator: str,
) -> List[Dict]:
    """
    更新业务记录的附件列表。

    逻辑：
    - attachment_ids 为最终需要保留的附件 ID 列表
    - 将当前记录关联但不在列表中的附件删除
    - 将未关联的附件绑定到本记录
    """
    ensure_attachment_schema(db)
    attachment_ids = [int(aid) for aid in (attachment_ids or [])]

    current = db.query_all(
        "SELECT id FROM record_attachment WHERE record_type = ? AND record_id = ?",
        (record_type, record_id),
    )
    current_ids = {row["id"] for row in current}
    keep_ids = set(attachment_ids)
    to_delete = current_ids - keep_ids
    to_add = keep_ids - current_ids

    for aid in to_delete:
        delete_attachment(db, aid, operator)

    return link_attachments(db, record_type, record_id, list(to_add), operator)


def delete_attachment(db, attachment_id: int, operator: str) -> bool:
    """
    删除附件（数据库记录 + 物理文件）。

    权限：上传者本人或管理员；业务模块应在调用前自行校验编辑权限。
    """
    ensure_attachment_schema(db)
    row = db.query_one(
        "SELECT * FROM record_attachment WHERE id = ?",
        (attachment_id,),
    )
    if not row:
        return False

    # 删除物理文件
    for path_key in ("stored_path", "thumbnail_path"):
        path = row.get(path_key)
        if path:
            abs_path = _resolve_stored_path(path)
            try:
                if os.path.exists(abs_path):
                    os.remove(abs_path)
            except Exception as exc:
                logger.warning(f"删除附件文件失败 {abs_path}: {exc}")

    db.execute("DELETE FROM record_attachment WHERE id = ?", (attachment_id,))
    return True


def cleanup_orphan_attachments(db, max_age_hours: int = 24) -> int:
    """
    清理 record_id=0 且超过指定时间的孤立附件。
    返回清理数量。
    """
    ensure_attachment_schema(db)
    cutoff = (datetime.now(timezone.utc) - timedelta(hours=max_age_hours)).strftime(
        "%Y-%m-%d %H:%M:%S"
    )
    rows = db.query_all(
        "SELECT id FROM record_attachment WHERE record_id = 0 AND created_at < ?",
        (cutoff,),
    )
    count = 0
    for row in rows:
        try:
            # operator 传空字符串，删除时仅处理物理文件和数据库记录，不校验权限
            _delete_attachment_files(row["id"], db)
            db.execute("DELETE FROM record_attachment WHERE id = ?", (row["id"],))
            count += 1
        except Exception as exc:
            logger.warning(f"清理孤立附件 {row['id']} 失败: {exc}")
    return count


def _delete_attachment_files(attachment_id: int, db) -> None:
    """仅删除物理文件，不删除数据库记录。"""
    row = db.query_one(
        "SELECT stored_path, thumbnail_path FROM record_attachment WHERE id = ?",
        (attachment_id,),
    )
    if not row:
        return
    for path_key in ("stored_path", "thumbnail_path"):
        path = row.get(path_key)
        if path:
            abs_path = _resolve_stored_path(path)
            try:
                if os.path.exists(abs_path):
                    os.remove(abs_path)
            except Exception as exc:
                logger.warning(f"删除附件文件失败 {abs_path}: {exc}")


# =============================================================================
# 权限检查
# =============================================================================

def _can_view_attachment(db, user: User, attachment: Dict) -> bool:
    """判断用户是否有权查看/下载某个附件。"""
    if is_admin_user(user):
        return True
    if user.username == attachment.get("uploader"):
        return True

    record_id = attachment.get("record_id") or 0
    if record_id == 0:
        # 未关联的附件只有上传者/管理员能看
        return False

    record_type = attachment.get("record_type")
    # 教师待办：创建者和关联教师可查看附件
    if record_type == "teacher_todo_series":
        # 局部导入避免循环依赖
        from ..teacher_todo import _get_teacher_identity

        identity = _get_teacher_identity(db, user.username)
        aliases = identity.get("aliases") or []

        series = db.query_one(
            "SELECT creator_teacher_id FROM teacher_todo_series WHERE id = ?",
            (record_id,),
        )
        if not series:
            return False
        if series.get("creator_teacher_id") in aliases:
            return True
        if aliases:
            placeholders = ",".join(["?"] * len(aliases))
            is_assignee = db.query_one(
                f"SELECT 1 FROM teacher_todo_assignee WHERE todo_series_id = ? AND teacher_id IN ({placeholders})",
                (record_id, *aliases),
            )
            return bool(is_assignee)
        return False

    meta = _RECORD_TYPE_VIEW_META.get(record_type)
    if not meta:
        # 未知业务类型默认拒绝
        logger.warning(f"附件关联了未配置权限的业务类型: {record_type}")
        return False

    record = db.query_one(meta["record_query"], (record_id,))
    if not record:
        # 业务记录已不存在，拒绝访问并触发清理
        return False

    scope = get_record_data_scope(
        db,
        user,
        meta["api_path"],
        all_permissions=meta.get("all_permissions", []),
        own_class_permissions=meta.get("own_class_permissions", []),
        own_permissions=meta.get("own_permissions", []),
    )
    return record_in_scope(
        record,
        scope,
        username=user.username,
        recorder_field="recorder",
        class_field="class_id",
    )


# =============================================================================
# API 路由
# =============================================================================

@router.post("/upload", summary="上传附件")
async def upload_attachments(
    files: List[UploadFile] = File(...),
    record_type: Optional[str] = "",
    user: User = Depends(require_configured_api_permission(API_ATTACHMENT_UPLOAD, "POST", allow_missing=False)),
):
    """
    上传通用附件。

    - 每次最多 3 个文件
    - 单个文件 ≤10MB
    - 返回附件 ID 和下载 URL，前端需在创建/编辑记录时回传 attachment_ids
    """
    if len(files) > MAX_ATTACHMENTS_PER_RECORD:
        raise HTTPException(
            status_code=400,
            detail=f"单次最多上传 {MAX_ATTACHMENTS_PER_RECORD} 个附件",
        )

    results = []
    with get_moral_db() as db:
        ensure_attachment_schema(db)
        for f in files:
            saved = save_attachment(db, f, user.username, record_type or "unlinked", 0)
            results.append(saved)

    return {"success": True, "data": results}


@router.get("/{attachment_id}", summary="下载附件")
async def download_attachment(
    attachment_id: int,
    thumbnail: int = 0,
    user: User = Depends(require_configured_api_permission(API_ATTACHMENT_DOWNLOAD, "GET", allow_missing=False)),
):
    """
    下载附件（或缩略图）。

    权限：管理员、上传者，或对该附件关联的业务记录有查看权限的用户。
    """
    with get_moral_db() as db:
        ensure_attachment_schema(db)
        row = db.query_one(
            """
            SELECT id, record_type, record_id, uploader, stored_path,
                   thumbnail_path, file_type, mime_type, original_name
            FROM record_attachment
            WHERE id = ?
            """,
            (attachment_id,),
        )
        if not row:
            raise HTTPException(status_code=404, detail="附件不存在")

        if not _can_view_attachment(db, user, dict(row)):
            raise HTTPException(status_code=403, detail="无权访问该附件")

        use_thumb = thumbnail and row.get("thumbnail_path")
        stored_path = row["thumbnail_path"] if use_thumb else row["stored_path"]
        abs_path = _resolve_stored_path(stored_path)

        if not os.path.exists(abs_path):
            raise HTTPException(status_code=404, detail="附件文件已丢失")

        media_type = row.get("mime_type") or "application/octet-stream"
        filename = row.get("original_name") or f"attachment_{attachment_id}"
        return FileResponse(
            abs_path,
            media_type=media_type,
            filename=filename,
        )


@router.delete("/{attachment_id}", summary="删除附件")
async def delete_attachment_endpoint(
    attachment_id: int,
    user: User = Depends(require_configured_api_permission(API_ATTACHMENT_DELETE, "DELETE", allow_missing=False)),
):
    """
    删除附件。

    权限：管理员或上传者本人。业务记录编辑时建议调用 update_record_attachments
    在事务内处理附件增删，而不是单独调用此接口。
    """
    with get_moral_db() as db:
        ensure_attachment_schema(db)
        row = db.query_one(
            "SELECT uploader FROM record_attachment WHERE id = ?",
            (attachment_id,),
        )
        if not row:
            raise HTTPException(status_code=404, detail="附件不存在")

        if not is_admin_user(user) and user.username != row.get("uploader"):
            raise HTTPException(status_code=403, detail="只能删除自己上传的附件")

        delete_attachment(db, attachment_id, user.username)
        return {"success": True, "message": "附件已删除"}
