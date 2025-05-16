"""
Description:
Author: 侯文君
Date: 2025-04-29 11:32:44
LastEditors: 侯文君
LastEditTime: 2025-05-15 18:05:29
"""

import sqlite3
from typing import Optional

from ..models.third_party import ThirdPartyDict, ThirdPartyConfig


class ThirdPartyService:
    """第三方配置服务"""

    @staticmethod
    def get_all_dict_items(db: sqlite3.Connection = None) -> list[ThirdPartyDict]:
        """获取所有第三方配置字典项"""
        return ThirdPartyDict.get_all(db)

    @staticmethod
    def get_dict_item(dict_key: str, db: sqlite3.Connection = None) -> Optional[ThirdPartyDict]:
        """获取单个第三方配置字典项"""
        return ThirdPartyDict.get_by_key(dict_key, db)

    @staticmethod
    def add_dict_item(item: ThirdPartyDict, db: sqlite3.Connection = None) -> bool:
        """添加新的第三方配置字典项"""
        return item.save(db)

    @staticmethod
    def update_dict_item(_dict_key: str, item: ThirdPartyDict, db: sqlite3.Connection = None) -> bool:
        """更新第三方配置字典项"""
        return item.update(db)

    @staticmethod
    def delete_dict_item(dict_key: str, db: sqlite3.Connection = None) -> bool:
        """删除第三方配置字典项"""
        return ThirdPartyDict.delete(dict_key, db)

    @staticmethod
    def get_project_configs(project_id: str, db: sqlite3.Connection = None) -> list[ThirdPartyConfig]:
        """获取项目的所有第三方配置"""
        return ThirdPartyConfig.get_by_project(project_id, db)

    @staticmethod
    def get_unconfigured_dict_items(project_id: str, db: sqlite3.Connection = None) -> list[ThirdPartyDict]:
        """获取项目未配置的字典项"""
        return ThirdPartyConfig.get_unconfigured_dict_items(project_id, db)
