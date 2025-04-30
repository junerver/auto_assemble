from typing import Optional

from webhook.models.metadata import BuildMetadata


class MetadataService:
    @staticmethod
    def create_metadata(
            task_id: str,
            package_name: str,
            version_name: str,
            version_code: int,
            build_type: str,
            flavor: str,
            build_date: str,
            file_size: int,
            md5: str,
    ) -> BuildMetadata:
        """创建构建任务产物元数据"""
        # 检查是否存在相同任务ID的元数据
        existing_metadata = BuildMetadata.get_by_task_id(task_id)
        if existing_metadata:
            raise ValueError(f"任务ID {task_id} 已存在元数据")

        metadata = BuildMetadata(
            task_id=task_id,
            package_name=package_name,
            version_name=version_name,
            version_code=version_code,
            build_type=build_type,
            flavor=flavor,
            build_date=build_date,
            file_size=file_size,
            md5=md5,
        )
        metadata.save()
        return metadata

    @staticmethod
    def get_metadata_by_task_id(task_id: str) -> Optional[BuildMetadata]:
        """根据任务ID获取构建任务产物元数据"""
        return BuildMetadata.get_by_task_id(task_id)
