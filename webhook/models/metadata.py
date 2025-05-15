import logging
import sqlite3
from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class BuildMetadata:
    """构建任务产物元数据"""

    # 主键
    id: Optional[int] = None
    # 任务id
    task_id: Optional[str] = None
    # 包名
    package_name: Optional[str] = None
    # 版本名
    version_name: Optional[str] = None
    # 版本号
    version_code: Optional[int] = None
    # 构建类型
    build_type: Optional[str] = None
    # 构建变体
    flavor: Optional[str] = None
    # 构建日期
    build_date: Optional[str] = None
    # 文件大小
    file_size: Optional[int] = None
    # md5
    md5: Optional[str] = None
    # 创建时间
    created_at: Optional[datetime] = None

    def save(self, db: sqlite3.Connection):
        """保存构建任务产物元数据"""
        self.created_at = datetime.now()
        cursor = db.cursor()
        cursor.execute(
            """
            INSERT INTO build_task_metadata (task_id, package_name, version_name, version_code, build_type, flavor,
                                             build_date, file_size, md5, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                self.task_id,
                self.package_name,
                self.version_name,
                self.version_code,
                self.build_type,
                self.flavor,
                self.build_date,
                self.file_size,
                self.md5,
                self.created_at,
            ),
        )
        self.id = cursor.lastrowid
        db.commit()

    @classmethod
    def get_by_task_id(cls, task_id: str, db: sqlite3.Connection) -> Optional["BuildMetadata"]:
        """根据任务id获取构建任务产物元数据"""
        logging.info(f"查询id{task_id}")
        cursor = db.cursor()
        cursor.execute(
            """
            SELECT *
            FROM build_task_metadata
            WHERE task_id = ?
            """,
            (task_id,),
        )
        row = cursor.fetchone()
        if row:
            row_dict = dict(row)
            if row_dict.get("created_at"):
                row_dict["created_at"] = datetime.fromisoformat(row_dict["created_at"])
            return cls(**row_dict)
        return None

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "id": self.id,
            "task_id": self.task_id,
            "package_name": self.package_name,
            "version_name": self.version_name,
            "version_code": self.version_code,
            "build_type": self.build_type,
            "flavor": self.flavor,
            "build_date": self.build_date,
            "file_size": self.file_size,
            "md5": self.md5,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
