from flask import request, jsonify

from webhook.services.metadata_service import MetadataService
from . import metadata_bp


@metadata_bp.route("/<task_id>", methods=["POST"])
def create_metadata(task_id: str):
    """
    创建构建任务产物元数据

    通过接口提交的json格式如下：
    {
        "package_name": "com.jkr.identify_field",
        "version_name": "1.0.0",
        "version_code": 109,
        "build_type": "release",
        "flavor": "",
        "build_date": "2025-04-30 10:06:31",
        "file_size": 50140,
        "md5": "6c53fc10a93a0fee08a24e63957ad4f7"
    }
    """
    data = request.get_json()
    try:
        metadata = MetadataService.create_metadata(
            task_id=task_id,
            package_name=data["package_name"],
            version_name=data["version_name"],
            version_code=data["version_code"],
            build_type=data["build_type"],
            flavor=data["flavor"],
            build_date=data["build_date"],
            file_size=data["file_size"],
            md5=data["md5"],
        )
        return jsonify(metadata.to_dict()), 201
    except KeyError as e:
        return jsonify({"error": f"Missing required field: {str(e)}"}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@metadata_bp.route("/<task_id>", methods=["GET"])
def get_metadata(task_id: str):
    """获取指定任务ID的构建任务产物元数据"""
    metadata = MetadataService.get_metadata_by_task_id(task_id)
    if metadata:
        return jsonify(metadata.to_dict())
    return jsonify({"error": "Metadata not found"}), 404
