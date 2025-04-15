import uuid

from ..models.project import Project


class ProjectService:
    @staticmethod
    def create_project(
            project_url,
            prod_name,
            hbx_version=None,
            uniapp_id=None,
            uniapp_appkey=None,
            uniapp_is_cli=False,
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
        project.save()
        return project

    @staticmethod
    def get_project(project_id=None, project_url=None, prod_name=None):
        if project_id:
            return Project.get_by_id(project_id)
        elif project_url:
            return Project.get_by_url(project_url)
        elif prod_name:
            return Project.get_by_name(prod_name)
        return None

    @staticmethod
    def get_all_projects():
        return Project.get_all()

    @staticmethod
    def update_project(project_id, **kwargs):
        """更新项目"""
        project = Project.get_by_id(project_id)
        if project:
            project.update(**kwargs)
            return project
        return None

    @staticmethod
    def configure_project(project_data):
        """配置项目"""
        # 检查项目是否已存在
        project = Project.get_by_url(project_data.get("project_url"))
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
                prod_name=project_data.get("prod_name"),
                hbx_version=project_data.get("hbx_version"),
                uniapp_id=project_data.get("uniapp_id"),
                uniapp_appkey=project_data.get("uniapp_appkey"),
                uniapp_is_cli=project_data.get("uniapp_is_cli", False),
            )

        return project
