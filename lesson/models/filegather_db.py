# -*- coding: utf-8 -*-
"""
文件收集系统数据库操作模块

功能:
- 文件记录的增删改查
- 文件状态管理
- 月度统计
"""

import os
import sqlite3
import shutil
import logging
from datetime import datetime
from typing import Optional, List, Dict, Any
from contextlib import contextmanager

logger = logging.getLogger(__name__)

# 默认数据库路径
DEFAULT_DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "databases", "filegather.db")

# 默认存储路径
DEFAULT_STORAGE_ROOT = os.path.join(os.path.dirname(os.path.dirname(__file__)), "storage", "filegather")

# 允许的文件扩展名
ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png", "doc", "docx", "xlsx", "xls", "ppt", "pptx", "pdf"}

# 最大文件大小 (50MB)
MAX_FILE_SIZE = 50 * 1024 * 1024


class FileGatherDB:
    """文件收集系统数据库操作类"""

    def __init__(self, db_path: str = None, storage_root: str = None):
        """
        初始化数据库连接

        Args:
            db_path: 数据库文件路径
            storage_root: 存储根目录
        """
        self.db_path = db_path or DEFAULT_DB_PATH
        self.storage_root = storage_root or DEFAULT_STORAGE_ROOT
        self.uploads_dir = os.path.join(self.storage_root, "uploads")
        self.done_dir = os.path.join(self.storage_root, "done")

        # 确保目录存在
        self._ensure_dirs()
        # 初始化数据库表
        self._init_db()

    @contextmanager
    def _get_connection(self):
        """获取数据库连接的上下文管理器"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    def _ensure_dirs(self) -> None:
        """确保存储目录和数据库目录存在"""
        # 确保数据库目录存在
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        # 确保存储目录存在
        os.makedirs(self.uploads_dir, exist_ok=True)
        os.makedirs(self.done_dir, exist_ok=True)

    def _init_db(self) -> None:
        """初始化数据库表"""
        with self._get_connection() as conn:
            # 创建文件表
            conn.execute("""
                CREATE TABLE IF NOT EXISTS files (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT NOT NULL,
                    original_name TEXT NOT NULL,
                    stored_path TEXT NOT NULL,
                    content_type TEXT,
                    status TEXT NOT NULL DEFAULT '否',
                    uploaded_at TEXT NOT NULL,
                    done_at TEXT,
                    copies INTEGER,
                    use_date TEXT,
                    month TEXT,
                    note TEXT
                )
            """)

            # 创建索引
            conn.execute("CREATE INDEX IF NOT EXISTS idx_files_username ON files(username)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_files_status ON files(status)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_files_month ON files(month)")

            conn.commit()
            logger.info("FileGatherDB initialized successfully")

    def check_extension(self, filename: str) -> bool:
        """
        检查文件扩展名是否允许

        Args:
            filename: 文件名

        Returns:
            是否允许
        """
        if "." not in filename:
            return False
        ext = filename.rsplit(".", 1)[-1].lower()
        return ext in ALLOWED_EXTENSIONS

    def parse_use_date(self, raw: str) -> tuple:
        """
        解析使用日期

        Args:
            raw: 日期字符串 (YYYY-MM-DD格式)

        Returns:
            (日期ISO字符串, 月份字符串)
        """
        try:
            dt = datetime.strptime(raw, "%Y-%m-%d")
        except ValueError:
            raise ValueError("使用日期格式应为YYYY-MM-DD")
        month = dt.strftime("%Y%m")
        return dt.date().isoformat(), month

    def save_file(self, month: str, filename: str, file_content: bytes) -> str:
        """
        保存上传的文件

        Args:
            month: 月份 (YYYYMM格式)
            filename: 原始文件名
            file_content: 文件内容

        Returns:
            存储路径
        """
        import uuid

        # 生成安全的文件名
        ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        safe_name = filename.replace("/", "_").replace("\\", "_")
        unique_id = uuid.uuid4().hex[:8]
        stored_name = f"{ts}_{unique_id}_{safe_name}"

        target_dir = os.path.join(self.uploads_dir, month)
        os.makedirs(target_dir, exist_ok=True)

        stored_path = os.path.join(target_dir, stored_name)
        with open(stored_path, "wb") as f:
            f.write(file_content)

        logger.info(f"File saved: {stored_path}")
        return stored_path

    def insert_file(
        self,
        username: str,
        original_name: str,
        stored_path: str,
        content_type: Optional[str],
        copies: int,
        use_date: str,
        month: str,
        note: Optional[str],
    ) -> int:
        """
        插入文件记录

        Args:
            username: 用户名
            original_name: 原始文件名
            stored_path: 存储路径
            content_type: 内容类型
            copies: 打印份数
            use_date: 使用日期
            month: 月份
            note: 备注

        Returns:
            记录ID
        """
        with self._get_connection() as conn:
            cur = conn.execute(
                """
                INSERT INTO files (username, original_name, stored_path, content_type, status, uploaded_at, copies, use_date, month, note)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    username,
                    original_name,
                    stored_path,
                    content_type,
                    "否",
                    datetime.utcnow().isoformat(),
                    copies,
                    use_date,
                    month,
                    note,
                ),
            )
            conn.commit()
            file_id = cur.lastrowid
            logger.info(f"File record inserted: id={file_id}, user={username}, name={original_name}")
            return file_id

    def query_files(
        self,
        username: Optional[str] = None,
        status: Optional[str] = None,
        month: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        查询文件记录

        Args:
            username: 用户名筛选
            status: 状态筛选
            month: 月份筛选

        Returns:
            文件记录列表
        """
        with self._get_connection() as conn:
            sql = "SELECT * FROM files"
            where = []
            params = []

            if username is not None:
                where.append("username = ?")
                params.append(username)

            if status is not None:
                if isinstance(status, (list, tuple)) and len(status) > 0:
                    placeholders = ",".join(["?"] * len(status))
                    where.append(f"status IN ({placeholders})")
                    params.extend(list(status))
                else:
                    where.append("status = ?")
                    params.append(status)

            if month is not None:
                where.append("month = ?")
                params.append(month)

            if where:
                sql += " WHERE " + " AND ".join(where)

            sql += " ORDER BY uploaded_at DESC"

            cur = conn.execute(sql, tuple(params))
            rows = cur.fetchall()
            return [dict(r) for r in rows]

    def get_file_by_id(self, file_id: int) -> Optional[Dict[str, Any]]:
        """
        根据ID获取文件记录

        Args:
            file_id: 文件ID

        Returns:
            文件记录或None
        """
        with self._get_connection() as conn:
            cur = conn.execute("SELECT * FROM files WHERE id = ?", (file_id,))
            row = cur.fetchone()
            return dict(row) if row else None

    def mark_done(self, file_id: int) -> Dict[str, Any]:
        """
        标记文件为已完成

        Args:
            file_id: 文件ID

        Returns:
            更新后的文件信息
        """
        file_info = self.get_file_by_id(file_id)
        if not file_info:
            raise ValueError("文件不存在")

        src_path = file_info["stored_path"]
        if not os.path.exists(src_path):
            raise FileNotFoundError("源文件不存在")

        month = file_info["month"] or datetime.utcnow().strftime("%Y%m")
        target_dir = os.path.join(self.done_dir, month)
        os.makedirs(target_dir, exist_ok=True)

        target_path = os.path.join(target_dir, os.path.basename(src_path))
        shutil.move(src_path, target_path)

        with self._get_connection() as conn:
            conn.execute(
                "UPDATE files SET status = ?, stored_path = ?, done_at = ? WHERE id = ?",
                ("是", target_path, datetime.utcnow().isoformat(), file_id),
            )
            conn.commit()

        logger.info(f"File marked as done: id={file_id}")
        return {"id": file_id, "stored_path": target_path, "status": "是"}

    def update_status(self, file_id: int, status: str) -> bool:
        """
        更新文件状态

        Args:
            file_id: 文件ID
            status: 新状态

        Returns:
            是否成功
        """
        with self._get_connection() as conn:
            conn.execute(
                "UPDATE files SET status = ? WHERE id = ?",
                (status, file_id),
            )
            conn.commit()
        logger.info(f"File status updated: id={file_id}, status={status}")
        return True

    def delete_file(self, file_id: int, username: str) -> bool:
        """
        删除文件记录和文件

        Args:
            file_id: 文件ID
            username: 操作用户名

        Returns:
            是否成功
        """
        file_info = self.get_file_by_id(file_id)
        if not file_info:
            raise ValueError("文件不存在")

        if file_info["username"] != username:
            raise PermissionError("无权删除他人文件")

        if file_info["status"] != "否":
            raise ValueError("仅可删除状态为'否'的文件")

        # 删除物理文件
        path = file_info["stored_path"]
        try:
            if os.path.isfile(path):
                os.remove(path)
        except Exception as e:
            logger.warning(f"Failed to delete file {path}: {e}")

        # 删除数据库记录
        with self._get_connection() as conn:
            conn.execute("DELETE FROM files WHERE id = ?", (file_id,))
            conn.commit()

        logger.info(f"File deleted: id={file_id}, user={username}")
        return True

    def get_months(self) -> List[str]:
        """
        获取所有有文件的月份列表

        Returns:
            月份列表 (YYYYMM格式)
        """
        with self._get_connection() as conn:
            cur = conn.execute(
                "SELECT DISTINCT month FROM files WHERE month IS NOT NULL ORDER BY month DESC"
            )
            return [r["month"] for r in cur.fetchall()]

    def get_statistics(self, month: Optional[str] = None) -> Dict[str, Any]:
        """
        获取统计信息

        Args:
            month: 月份筛选

        Returns:
            统计信息
        """
        with self._get_connection() as conn:
            # 构建基础条件
            month_where = "WHERE month = ?" if month else ""
            month_params = [month] if month else []

            # 总文件数
            cur = conn.execute(f"SELECT COUNT(*) as count FROM files {month_where}", tuple(month_params) if month_params else ())
            total_files = cur.fetchone()["count"]

            # 待处理文件数 (状态不是"是")
            if month:
                cur = conn.execute(
                    "SELECT COUNT(*) as count FROM files WHERE month = ? AND status != '是'",
                    (month,)
                )
            else:
                cur = conn.execute(
                    "SELECT COUNT(*) as count FROM files WHERE status != '是'"
                )
            pending_files = cur.fetchone()["count"]

            # 已完成文件数
            if month:
                cur = conn.execute(
                    "SELECT COUNT(*) as count FROM files WHERE month = ? AND status = '是'",
                    (month,)
                )
            else:
                cur = conn.execute(
                    "SELECT COUNT(*) as count FROM files WHERE status = '是'"
                )
            done_files = cur.fetchone()["count"]

            # 按用户统计
            if month:
                cur = conn.execute(
                    "SELECT username, COUNT(*) as count FROM files WHERE month = ? GROUP BY username ORDER BY count DESC LIMIT 10",
                    (month,)
                )
            else:
                cur = conn.execute(
                    "SELECT username, COUNT(*) as count FROM files GROUP BY username ORDER BY count DESC LIMIT 10"
                )
            by_user = [{"username": r["username"], "count": r["count"]} for r in cur.fetchall()]

            return {
                "total_files": total_files,
                "pending_files": pending_files,
                "done_files": done_files,
                "by_user": by_user,
            }