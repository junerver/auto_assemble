import sqlite3
import uuid
from typing import Optional

from webhook.models.project import Project


class ProjectService:
    @staticmethod
    def create_project(
        project_url,
        prod_name,
        hbx_version=None,
        uniapp_id=None,
        uniapp_appkey=None,
        uniapp_is_cli=False,
        db: sqlite3.Connection = None,
    ):
        project = Project(
            id=str(uuid.uuid4()),
            project_url=project_url,
            prod_name=prod_name,
            hbx_version=hbx_version,
            uniapp_id=uniapp_id,
            uniapp_appkey=uniapp_appkey,
            uniapp_is_cli=uniapp_is_cli,
        )
        project.save(db)
        return project

    @staticmethod
    def get_project(
        project_id=None, project_url=None, prod_name=None, db: sqlite3.Connection = None
    ) -> Optional[Project]:
        if project_id:
            return Project.get_by_id(project_id, db)
        elif project_url:
            return Project.get_by_url(project_url, db)
        elif prod_name:
            return Project.get_by_name(prod_name, db)
        return None

    @staticmethod
    def get_all_projects(db: sqlite3.Connection = None):
        return Project.get_all(db)

    @staticmethod
    def update_project(project_id, db: sqlite3.Connection, **kwargs):
        """更新项目"""
        project = Project.get_by_id(project_id, db)
        if project:
            project.update(db, **kwargs)
            return project
        return None

    @staticmethod
    def configure_project(project_data, db: sqlite3.Connection = None):
        """配置项目"""
        # 检查项目是否已存在
        project = Project.get_by_url(project_data.get("project_url"), db)
        if not project:
            # 创建新项目
            project = ProjectService.create_project(
                project_url=project_data.get("project_url"),
                prod_name=project_data.get("prod_name"),
                hbx_version=project_data.get("hbx_version"),
                uniapp_id=project_data.get("uniapp_id"),
                uniapp_appkey=project_data.get("uniapp_appkey"),
                uniapp_is_cli=project_data.get("uniapp_is_cli", False),
            )
        else:
            # 更新现有项目
            project.update(
                db=db,
                prod_name=project_data.get("prod_name"),
                hbx_version=project_data.get("hbx_version"),
                uniapp_id=project_data.get("uniapp_id"),
                uniapp_appkey=project_data.get("uniapp_appkey"),
                uniapp_is_cli=project_data.get("uniapp_is_cli", False),
            )

        return project
