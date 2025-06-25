"""
Description:
Author: 侯文君
Date: 2025-05-12 15:20:50
LastEditors: 侯文君
LastEditTime: 2025-05-15 18:06:21
"""

import pathlib
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from dataclasses_json import DataClassJsonMixin, config

from common.time import safe_convert_datetime


@dataclass
class Project(DataClassJsonMixin):
    """项目配置"""

    id: Optional[str] = None
    project_url: Optional[str] = None
    prod_name: Optional[str] = None
    hbx_version: Optional[str] = None
    uniapp_id: Optional[str] = None
    uniapp_appkey: Optional[str] = None
    uniapp_is_cli: bool = False
    created_at: Optional[datetime] = field(
        default=datetime.now(),
        metadata=config(
            encoder=datetime.isoformat,
            decoder=datetime.fromisoformat,
        ),
    )
    updated_at: Optional[datetime] = field(
        default=datetime.now(),
        metadata=config(
            encoder=datetime.isoformat,
            decoder=datetime.fromisoformat,
        ),
    )
    # 签名文件路径
    key_store: Optional[str] = None
    # 签名文件密码
    ks_pass: Optional[str] = None
    # 签名文件别名
    key_alias: Optional[str] = None
    # 签名文件别名密码
    key_pass: Optional[str] = None

    def __post_init__(self):
        """在初始化后确保datetime字段的类型正确"""
        for _field in ["created_at", "updated_at"]:
            value = getattr(self, _field)
            setattr(self, _field, safe_convert_datetime(value))

    @classmethod
    def get_by_id(cls, project_id: str, db: sqlite3.Connection) -> Optional["Project"]:
        """根据ID获取项目"""
        cursor = db.cursor()
        cursor.execute("SELECT * FROM project_config WHERE id = ?", (project_id,))
        row = cursor.fetchone()
        if row:
            row_dict = dict(row)
            # 转换datetime字段
            for _field in ["created_at", "updated_at"]:
                # noinspection PyTypeChecker
                row_dict[_field] = safe_convert_datetime(row_dict.get(_field))
            return cls(**row_dict)
        return None

    @classmethod
    def get_by_url(cls, project_url: str, db: sqlite3.Connection) -> Optional["Project"]:
        """根据URL获取项目"""
        cursor = db.cursor()
        cursor.execute("SELECT * FROM project_config WHERE project_url = ?", (project_url,))
        row = cursor.fetchone()
        if row:
            row_dict = dict(row)
            # 转换datetime字段
            for _field in ["created_at", "updated_at"]:
                # noinspection PyTypeChecker
                row_dict[_field] = safe_convert_datetime(row_dict.get(_field))
            return cls(**row_dict)
        return None

    @classmethod
    def get_by_name(cls, prod_name: str, db: sqlite3.Connection) -> Optional["Project"]:
        """根据产品名称获取项目"""
        cursor = db.cursor()
        cursor.execute("SELECT * FROM project_config WHERE prod_name = ?", (prod_name,))
        row = cursor.fetchone()
        if row:
            row_dict = dict(row)
            # 转换datetime字段
            for _field in ["created_at", "updated_at"]:
                # noinspection PyTypeChecker
                row_dict[_field] = safe_convert_datetime(row_dict.get(_field))
            return cls(**row_dict)
        return None

    @classmethod
    def get_all(cls, db: sqlite3.Connection) -> list["Project"]:
        """获取所有项目"""
        cursor = db.cursor()
        cursor.execute("SELECT * FROM project_config ORDER BY prod_name")
        projects = []
        for row in cursor.fetchall():
            row_dict = dict(row)
            # 转换datetime字段
            for _field in ["created_at", "updated_at"]:
                # noinspection PyTypeChecker
                row_dict[_field] = safe_convert_datetime(row_dict.get(_field))
            projects.append(cls(**row_dict))
        return projects

    def delete(self, db: sqlite3.Connection):
        """删除项目配置"""
        cursor = db.cursor()
        cursor.execute("DELETE FROM project_config WHERE id = ?", (self.id,))
        db.commit()

    def save(self, db: sqlite3.Connection) -> None:
        """保存项目配置"""
        cursor = db.cursor()
        cursor.execute(
            """
            INSERT OR REPLACE INTO project_config 
            (id, project_url, prod_name, hbx_version, uniapp_id, uniapp_appkey, uniapp_is_cli,
             created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                self.id,
                self.project_url,
                self.prod_name,
                self.hbx_version,
                self.uniapp_id,
                self.uniapp_appkey,
                self.uniapp_is_cli,
                self.created_at,
                self.updated_at,
            ),
        )
        db.commit()

    def update(self, db: sqlite3.Connection, **kwargs) -> None:
        """更新项目配置"""
        cursor = db.cursor()

        update_fields = []
        update_values = []
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
                update_fields.append(f"{key} = ?")
                update_values.append(value)

        if update_fields:
            update_values.append(self.id)
            cursor.execute(
                f"""
                UPDATE project_config 
                SET {", ".join(update_fields)}, updated_at = datetime('now', 'localtime')
                WHERE id = ?
            """,
                update_values,
            )
            db.commit()

    def get_sign_config(self) -> dict | None:
        """获取项目签名配置"""
        if (
            self.key_store
            and pathlib.Path(self.key_store).exists()
            and self.key_alias
            and self.key_pass
            and self.ks_pass
        ):
            return {
                "key_store": self.key_store,
                "ks_pass": self.ks_pass,
                "key_alias": self.key_alias,
                "key_pass": self.key_pass,
            }
        else:
            return None
