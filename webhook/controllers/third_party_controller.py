from flask import jsonify, request, Request

from . import third_party_bp
from ..models.third_party import ThirdPartyDict
from ..services.third_party_service import ThirdPartyService


@third_party_bp.route("/dict", methods=["GET"])
def get_third_party_dict():
    """获取所有第三方配置字典"""
    try:
        dict_items = ThirdPartyService.get_all_dict_items()
        return jsonify({"items": [item.to_dict() for item in dict_items]}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@third_party_bp.route("/dict", methods=["POST"])
def add_third_party_dict():
    """添加新的第三方配置字典项"""
    try:
        try:
            dict_item = parse_third_party_config_dict(request)
        except Exception as e:
            return jsonify({"error": str(e)}), 400
        if ThirdPartyService.add_dict_item(dict_item):
            return jsonify({"message": "Third party dictionary item added successfully"}), 201
        else:
            return jsonify({"error": "Dictionary key already exists"}), 400

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@third_party_bp.route("/dict/<key>", methods=["GET"])
def get_third_party_dict_item(key):
    """获取单个第三方配置字典项"""
    try:
        item = ThirdPartyService.get_dict_item(key)
        if not item:
            return jsonify({"error": "Dictionary item not found"}), 404

        return jsonify(item.to_dict()), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@third_party_bp.route("/dict/<key>", methods=["PUT"])
def update_third_party_dict_item(key):
    """更新第三方配置字典项"""
    try:
        try:
            dict_item = parse_third_party_config_dict(request)
        except Exception as e:
            return jsonify({"error": str(e)}), 400
        if ThirdPartyService.update_dict_item(key, dict_item):
            return jsonify({"message": "Third party dictionary item updated successfully"}), 200
        else:
            return jsonify({"error": "Dictionary item not found or key already exists"}), 404

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@third_party_bp.route("/dict/<key>", methods=["DELETE"])
def delete_third_party_dict_item(key):
    """删除第三方配置字典项"""
    try:
        if ThirdPartyService.delete_dict_item(key):
            return jsonify({"message": "Third party dictionary item deleted successfully"}), 200
        else:
            return jsonify({"error": "Dictionary item not found or is in use"}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@third_party_bp.route("/dict/unconfigured", methods=["GET"])
def get_unconfigured_dict_items():
    """获取项目未配置的字典项"""
    try:
        project_id = request.args.get("project_id")
        if not project_id:
            return jsonify({"error": "Project ID is required"}), 400

        unconfigured_items = ThirdPartyService.get_unconfigured_dict_items(project_id)
        return jsonify({"items": [item.to_dict() for item in unconfigured_items]}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


def parse_third_party_config_dict(api_request: Request) -> ThirdPartyDict:
    """解析第三方配置字典项"""
    data = api_request.get_json()
    if not data:
        raise ValueError("No JSON data received")

    required_fields = ["provider", "dict_key", "dict_value", "description"]
    for field in required_fields:
        if field not in data:
            raise ValueError(f"Missing required field: {field}")

    dict_item = ThirdPartyDict(
        provider=data["provider"],
        dict_key=data["dict_key"],
        dict_value=data["dict_value"],
        description=data["description"],
    )
    return dict_item
