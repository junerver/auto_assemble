from flask import jsonify, request

from . import project_bp
from ..models.third_party import ThirdPartyConfig
from ..services.project_service import ProjectService
from ..services.third_party_service import ThirdPartyService


@project_bp.route("/project", methods=["POST"])
def configure_project():
    """配置项目信息"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No JSON data received"}), 400

        project = ProjectService.configure_project(data)
        return (
            jsonify({"message": "Project configured successfully", "project": project.to_dict()}),
            200,
        )

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@project_bp.route("/project", methods=["GET"])
def get_project_config():
    """获取项目配置信息"""
    try:
        # 获取查询参数
        project_url = request.args.get("url")
        prod_name = request.args.get("name")

        if not project_url and not prod_name:
            return jsonify({"error": "Must provide either url or name parameter"}), 400

        project = ProjectService.get_project(project_url=project_url, prod_name=prod_name)
        if not project:
            return jsonify({"error": "Project not found"}), 404

        # 获取项目的第三方配置
        third_party_configs = ThirdPartyService.get_project_configs(project.id)

        return (
            jsonify(
                {
                    "project_config": project.to_dict(),
                    "third_party_configs": [config.to_dict() for config in third_party_configs],
                    "message": "获取项目配置成功",
                }
            ),
            200,
        )

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@project_bp.route("/project/<project_id>", methods=["PUT"])
def update_project_config(project_id):
    """更新项目配置信息"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No JSON data received"}), 400

        # 分离基础配置和第三方配置
        base_config = {k: v for k, v in data.items() if k not in ["third_party_configs"]}
        third_party_configs = data.get("third_party_configs", [])

        # 更新基础配置
        project = ProjectService.update_project(project_id, **base_config)
        if not project:
            return jsonify({"error": "Project not found"}), 404

        # 更新第三方配置
        if third_party_configs:
            # 获取当前项目的所有第三方配置
            current_configs = {
                config.dict_key: config.config_value
                for config in ThirdPartyService.get_project_configs(project_id)
            }

            for config in third_party_configs:
                dict_key = config.get("key")
                config_value = config.get("value")
                if not dict_key or not config_value:
                    continue

                # 检查字典项是否存在
                dict_item = ThirdPartyService.get_dict_item(dict_key)
                if not dict_item:
                    return jsonify({"error": f"Dictionary item {dict_key} not found"}), 400

                # 只有当配置值发生变化时才更新
                if dict_key not in current_configs or current_configs[dict_key] != config_value:
                    third_party_config = ThirdPartyConfig(
                        project_id=project_id, dict_key=dict_key, config_value=config_value
                    )
                    if not third_party_config.save():
                        return (
                            jsonify({"error": f"Failed to save third party config for {dict_key}"}),
                            500,
                        )

        # 获取更新后的完整项目信息
        project_dict = project.to_dict()
        project_dict["third_party_configs"] = [
            config.to_dict() for config in ThirdPartyService.get_project_configs(project_id)
        ]

        return (
            jsonify(
                {
                    "message": "Project configuration updated successfully",
                    "project": project_dict,
                }
            ),
            200,
        )

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@project_bp.route("/projects", methods=["GET"])
def get_projects():
    """获取所有项目配置列表"""
    try:
        projects = ProjectService.get_all_projects()
        return jsonify({"projects": [project.to_dict() for project in projects]}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
