import sqlite3
from typing import Optional

from webhook.models.metadata import BuildMetadata
from webhook.types import MetaDataModel


class MetadataService:
    @staticmethod
    def create_metadata(
        task_id: str,
        metadata_model: MetaDataModel,
        db: sqlite3.Connection = None,
    ) -> BuildMetadata:
        """创建构建任务产物元数据"""
        # 检查是否存在相同任务ID的元数据
        existing_metadata = BuildMetadata.get_by_task_id(task_id, db)
        if existing_metadata:
            raise ValueError(f"任务ID {task_id} 已存在元数据")

        # 使用字典解包的方式创建元数据
        metadata = BuildMetadata(task_id=task_id, **metadata_model.model_dump(exclude_unset=True))
        metadata.save(db)
        return metadata

    @staticmethod
    def get_metadata_by_task_id(task_id: str, db: sqlite3.Connection = None) -> Optional[BuildMetadata]:
        """根据任务ID获取构建任务产物元数据"""
        return BuildMetadata.get_by_task_id(task_id, db)
