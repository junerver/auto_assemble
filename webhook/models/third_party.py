import sqlite3
from dataclasses import dataclass
from typing import Optional



@dataclass
class ThirdPartyDict:
    """第三方配置字典项"""

    provider: str
    dict_key: str
    dict_value: str
    description: str
    id: Optional[int] = None

    @classmethod
    def get_all(cls, db: sqlite3.Connection) -> list["ThirdPartyDict"]:
        """获取所有第三方配置字典项"""
        cursor = db.cursor()
        cursor.execute(
            """
            SELECT id, provider, dict_key, dict_value, description 
            FROM third_party_dict 
            ORDER BY provider, dict_key
            """
        )
        return [cls(**dict(row)) for row in cursor.fetchall()]

    @classmethod
    def get_by_key(cls, dict_key: str, db: sqlite3.Connection) -> Optional["ThirdPartyDict"]:
        """获取单个第三方配置字典项"""
        cursor = db.cursor()
        cursor.execute(
            """
            SELECT id, provider, dict_key, dict_value, description 
            FROM third_party_dict 
            WHERE dict_key = ?
            """,
            (dict_key,),
        )
        row = cursor.fetchone()
        if row:
            return cls(**dict(row))
        return None

    def save(self, db: sqlite3.Connection) -> bool:
        """保存字典项"""
        cursor = db.cursor()
        try:
            cursor.execute(
                """
                INSERT INTO third_party_dict (provider, dict_key, dict_value, description)
                VALUES (?, ?, ?, ?)
                """,
                (self.provider, self.dict_key, self.dict_value, self.description),
            )
            db.commit()
            return True
        except sqlite3.IntegrityError:
            db.rollback()
            return False

    def update(self, db: sqlite3.Connection) -> bool:
        """更新字典项"""
        cursor = db.cursor()
        try:
            cursor.execute(
                """
                UPDATE third_party_dict 
                SET provider = ?, dict_key = ?, dict_value = ?, description = ?
                WHERE dict_key = ?
                """,
                (
                    self.provider,
                    self.dict_key,
                    self.dict_value,
                    self.description,
                    self.dict_key,
                ),
            )
            if cursor.rowcount == 0:
                return False
            db.commit()
            return True
        except sqlite3.IntegrityError:
            db.rollback()
            return False

    @classmethod
    def delete(cls, dict_key: str, db: sqlite3.Connection) -> bool:
        """删除字典项"""
        cursor = db.cursor()
        try:
            # 检查是否有项目正在使用这个字典项
            cursor.execute(
                """
                SELECT COUNT(*) FROM third_party_config 
                WHERE dict_key = ?
                """,
                (dict_key,),
            )
            if cursor.fetchone()[0] > 0:
                return False

            cursor.execute(
                """
                DELETE FROM third_party_dict 
                WHERE dict_key = ?
                """,
                (dict_key,),
            )
            if cursor.rowcount == 0:
                return False
            db.commit()
            return True
        finally:
            db.close()

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "provider": self.provider,
            "key": self.dict_key,
            "value": self.dict_value,
            "description": self.description,
        }


@dataclass
class ThirdPartyConfig:
    """项目的第三方配置"""

    project_id: str
    dict_key: str
    config_value: str
    id: Optional[int] = None
    provider: Optional[str] = None
    description: Optional[str] = None
    dict_value: Optional[str] = None

    @classmethod
    def get_by_project(cls, project_id: str, db: sqlite3.Connection) -> list["ThirdPartyConfig"]:
        """获取项目的所有第三方配置"""
        cursor = db.cursor()
        cursor.execute(
            """
            SELECT tpc.id, tpc.project_id, tpc.dict_key, tpc.config_value, 
                   tpd.provider, tpd.description, tpd.dict_value
            FROM third_party_config tpc
            JOIN third_party_dict tpd ON tpc.dict_key = tpd.dict_key
            WHERE tpc.project_id = ?
            """,
            (project_id,),
        )
        return [cls(**dict(row)) for row in cursor.fetchall()]

    @classmethod
    def get_unconfigured_dict_items(cls, project_id: str, db: sqlite3.Connection) -> list[ThirdPartyDict]:
        """获取项目未配置的字典项"""
        cursor = db.cursor()
        # 获取项目已配置的字典项
        cursor.execute(
            """
            SELECT dict_key FROM third_party_config 
            WHERE project_id = ?
            """,
            (project_id,),
        )
        configured_keys = {row[0] for row in cursor.fetchall()}

        # 获取所有字典项
        cursor.execute(
            """
            SELECT id, provider, dict_key, dict_value, description 
            FROM third_party_dict 
            ORDER BY provider, dict_key
            """
        )
        return [
            ThirdPartyDict(**dict(row))
            for row in cursor.fetchall()
            if row["dict_key"] not in configured_keys
        ]

    def save(self, db: sqlite3.Connection) -> bool:
        """保存配置"""
        cursor = db.cursor()
        try:
            # 检查配置是否已存在
            cursor.execute(
                """
                SELECT id FROM third_party_config 
                WHERE project_id = ? AND dict_key = ?
                """,
                (self.project_id, self.dict_key),
            )
            existing_config = cursor.fetchone()

            if existing_config:
                # 如果配置已存在，则更新
                cursor.execute(
                    """
                    UPDATE third_party_config 
                    SET config_value = ?, updated_at = datetime('now', 'localtime')
                    WHERE project_id = ? AND dict_key = ?
                    """,
                    (self.config_value, self.project_id, self.dict_key),
                )
            else:
                # 如果配置不存在，则插入新记录
                cursor.execute(
                    """
                    INSERT INTO third_party_config (project_id, dict_key, config_value)
                    VALUES (?, ?, ?)
                    """,
                    (self.project_id, self.dict_key, self.config_value),
                )

            db.commit()
            return True
        except sqlite3.IntegrityError:
            db.rollback()
            return False

    def update(self, db: sqlite3.Connection) -> bool:
        """更新配置"""
        cursor = db.cursor()
        try:
            cursor.execute(
                """
                UPDATE third_party_config 
                SET config_value = ?
                WHERE project_id = ? AND dict_key = ?
                """,
                (self.config_value, self.project_id, self.dict_key),
            )
            if cursor.rowcount == 0:
                return False
            db.commit()
            return True
        except sqlite3.IntegrityError:
            db.rollback()
            return False

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "provider": self.provider,
            "description": self.description,
            "dict_key": self.dict_key,
            "dict_value": self.dict_value,
            "config_value": self.config_value,
        }
