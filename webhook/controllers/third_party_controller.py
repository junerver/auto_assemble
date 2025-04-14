import sqlite3

from flask import jsonify, request

from . import third_party_bp
from ..config import DB_FILE


@third_party_bp.route("/api/config/third-party/dict", methods=["GET"])
def get_third_party_dict():
    """获取所有第三方配置字典"""
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT provider, dict_key, dict_value, description 
            FROM third_party_dict 
            ORDER BY provider, dict_key
        """
        )
        dict_items = cursor.fetchall()

        return (
            jsonify(
                {
                    "items": [
                        {
                            "provider": item[0],
                            "key": item[1],
                            "value": item[2],
                            "description": item[3],
                        }
                        for item in dict_items
                    ]
                }
            ),
            200,
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()


@third_party_bp.route("/api/config/third-party/dict", methods=["POST"])
def add_third_party_dict():
    """添加新的第三方配置字典项"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No JSON data received"}), 400

        required_fields = ["provider", "dict_key", "dict_value", "description"]
        for field in required_fields:
            if field not in data:
                return jsonify({"error": f"Missing required field: {field}"}), 400

        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()

        try:
            cursor.execute(
                """
                INSERT INTO third_party_dict (provider, dict_key, dict_value, description)
                VALUES (?, ?, ?, ?)
            """,
                (data["provider"], data["dict_key"], data["dict_value"], data["description"]),
            )

            conn.commit()
            return jsonify({"message": "Third party dictionary item added successfully"}), 201
        except sqlite3.IntegrityError:
            conn.rollback()
            return jsonify({"error": "Dictionary key already exists"}), 400
        finally:
            conn.close()
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@third_party_bp.route("/api/config/third-party/dict/<key>", methods=["GET"])
def get_third_party_dict_item(key):
    """获取单个第三方配置字典项"""
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT provider, dict_key, dict_value, description 
            FROM third_party_dict 
            WHERE dict_key = ?
        """,
            (key,),
        )
        item = cursor.fetchone()

        if not item:
            return jsonify({"error": "Dictionary item not found"}), 404

        return (
            jsonify(
                {
                    "provider": item[0],
                    "key": item[1],
                    "value": item[2],
                    "description": item[3],
                }
            ),
            200,
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()


@third_party_bp.route("/api/config/third-party/dict/<key>", methods=["PUT"])
def update_third_party_dict_item(key):
    """更新第三方配置字典项"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No JSON data received"}), 400

        required_fields = ["provider", "dict_key", "dict_value", "description"]
        for field in required_fields:
            if field not in data:
                return jsonify({"error": f"Missing required field: {field}"}), 400

        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()

        try:
            cursor.execute(
                """
                UPDATE third_party_dict 
                SET provider = ?, dict_key = ?, dict_value = ?, description = ?
                WHERE dict_key = ?
            """,
                (data["provider"], data["dict_key"], data["dict_value"], data["description"], key),
            )

            if cursor.rowcount == 0:
                return jsonify({"error": "Dictionary item not found"}), 404

            conn.commit()
            return jsonify({"message": "Third party dictionary item updated successfully"}), 200
        except sqlite3.IntegrityError:
            conn.rollback()
            return jsonify({"error": "Dictionary key already exists"}), 400
        finally:
            conn.close()
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@third_party_bp.route("/api/config/third-party/dict/<key>", methods=["DELETE"])
def delete_third_party_dict_item(key):
    """删除第三方配置字典项"""
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()

        # 检查是否有项目正在使用这个字典项
        cursor.execute(
            """
            SELECT COUNT(*) FROM third_party_config 
            WHERE dict_key = ?
        """,
            (key,),
        )
        if cursor.fetchone()[0] > 0:
            return jsonify({"error": "Cannot delete dictionary item that is in use"}), 400

        cursor.execute(
            """
            DELETE FROM third_party_dict 
            WHERE dict_key = ?
        """,
            (key,),
        )

        if cursor.rowcount == 0:
            return jsonify({"error": "Dictionary item not found"}), 404

        conn.commit()
        return jsonify({"message": "Third party dictionary item deleted successfully"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()


@third_party_bp.route("/api/config/third-party/dict/unconfigured", methods=["GET"])
def get_unconfigured_dict_items():
    """获取项目未配置的字典项"""
    try:
        project_id = request.args.get("project_id")
        if not project_id:
            return jsonify({"error": "Project ID is required"}), 400

        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()

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
            SELECT provider, dict_key, dict_value, description 
            FROM third_party_dict 
            ORDER BY provider, dict_key
        """
        )
        all_items = cursor.fetchall()

        # 过滤出未配置的字典项
        unconfigured_items = [
            {
                "provider": item[0],
                "key": item[1],
                "value": item[2],
                "description": item[3],
            }
            for item in all_items
            if item[1] not in configured_keys
        ]

        return jsonify({"items": unconfigured_items}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()
