import logging
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Any

from dataclasses_json import config, DataClassJsonMixin

from common.normalize import normalize_bool_fields
from common.time import safe_convert_datetime


@dataclass
class BuildMetadata(DataClassJsonMixin):
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
    created_at: Optional[datetime] = field(
        default=None,
        metadata=config(
            encoder=datetime.isoformat,
            decoder=datetime.fromisoformat,
        ),
    )
    # 是否已经ApkNormalize归一化
    is_normalized: Optional[bool] = False
    # 是否UniApp资源已经混淆
    is_obfuscated: Optional[bool] = False

    def save(self, db: sqlite3.Connection):
        """保存构建任务产物元数据"""
        self.created_at = datetime.now()
        cursor = db.cursor()
        cursor.execute(
            """
            INSERT INTO build_task_metadata (task_id, package_name, version_name, version_code, build_type, flavor,
                                             build_date, file_size, md5, created_at, is_normalized, is_obfuscated)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?,?,?)
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
                self.is_normalized,
                self.is_obfuscated,
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
            row_dict: dict[str, Any] = dict(row)
            if row_dict.get("created_at"):
                row_dict["created_at"] = safe_convert_datetime(row_dict["created_at"])

            row_dict = normalize_bool_fields(row_dict, ["is_normalized", "is_obfuscated"])
            return cls(**row_dict)
        return None
