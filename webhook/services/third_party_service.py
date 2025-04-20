from typing import Optional

from ..models.third_party import ThirdPartyDict, ThirdPartyConfig


class ThirdPartyService:
    """第三方配置服务"""

    @staticmethod
    def get_all_dict_items() -> list[ThirdPartyDict]:
        """获取所有第三方配置字典项"""
        return ThirdPartyDict.get_all()

    @staticmethod
    def get_dict_item(dict_key: str) -> Optional[ThirdPartyDict]:
        """获取单个第三方配置字典项"""
        return ThirdPartyDict.get_by_key(dict_key)

    @staticmethod
    def add_dict_item(item: ThirdPartyDict) -> bool:
        """添加新的第三方配置字典项"""
        return item.save()

    @staticmethod
    def update_dict_item(dict_key: str, item: ThirdPartyDict) -> bool:
        """更新第三方配置字典项"""
        return item.update()

    @staticmethod
    def delete_dict_item(dict_key: str) -> bool:
        """删除第三方配置字典项"""
        return ThirdPartyDict.delete(dict_key)

    @staticmethod
    def get_project_configs(project_id: str) -> list[ThirdPartyConfig]:
        """获取项目的所有第三方配置"""
        return ThirdPartyConfig.get_by_project(project_id)

    @staticmethod
    def get_unconfigured_dict_items(project_id: str) -> list[ThirdPartyDict]:
        """获取项目未配置的字典项"""
        return ThirdPartyConfig.get_unconfigured_dict_items(project_id)
