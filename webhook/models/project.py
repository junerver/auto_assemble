"""
Description:
Author: 侯文君
Date: 2025-05-12 15:20:50
LastEditors: 侯文君
LastEditTime: 2025-05-15 18:06:21
"""

import sqlite3
from dataclasses import dataclass
from typing import Optional


@dataclass
class Project:
    """项目配置"""

    id: Optional[str] = None
    project_url: Optional[str] = None
    prod_name: Optional[str] = None
    hbx_version: Optional[str] = None
    uniapp_id: Optional[str] = None
    uniapp_appkey: Optional[str] = None
    uniapp_is_cli: bool = False
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    @classmethod
    def get_by_id(cls, project_id: str, db: sqlite3.Connection) -> Optional["Project"]:
        """根据ID获取项目"""
        cursor = db.cursor()
        cursor.execute("SELECT * FROM project_config WHERE id = ?", (project_id,))
        row = cursor.fetchone()
        if row:
            return cls(**dict(row))
        return None

    @classmethod
    def get_by_url(cls, project_url: str, db: sqlite3.Connection) -> Optional["Project"]:
        """根据URL获取项目"""
        cursor = db.cursor()
        cursor.execute("SELECT * FROM project_config WHERE project_url = ?", (project_url,))
        row = cursor.fetchone()
        if row:
            return cls(**dict(row))
        return None

    @classmethod
    def get_by_name(cls, prod_name: str, db: sqlite3.Connection) -> Optional["Project"]:
        """根据产品名称获取项目"""
        cursor = db.cursor()
        cursor.execute("SELECT * FROM project_config WHERE prod_name = ?", (prod_name,))
        row = cursor.fetchone()
        if row:
            return cls(**dict(row))
        return None

    @classmethod
    def get_all(cls, db: sqlite3.Connection) -> list["Project"]:
        """获取所有项目"""
        cursor = db.cursor()
        cursor.execute("SELECT * FROM project_config ORDER BY prod_name")
        return [cls(**dict(row)) for row in cursor.fetchall()]

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

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "id": self.id,
            "project_url": self.project_url,
            "prod_name": self.prod_name,
            "hbx_version": self.hbx_version,
            "uniapp_id": self.uniapp_id,
            "uniapp_appkey": self.uniapp_appkey,
            "uniapp_is_cli": self.uniapp_is_cli,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }
