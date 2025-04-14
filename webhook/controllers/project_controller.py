import sqlite3
import uuid

from flask import jsonify, request

from . import project_bp
from ..config import DB_FILE


@project_bp.route("/api/config/project", methods=["POST"])
def configure_project():
    """配置项目信息"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No JSON data received"}), 400

        # 生成UUID作为项目ID
        project_id = str(uuid.uuid4())

        # 提取项目基础配置
        project_config = {
            "id": project_id,
            "project_url": data.get("project_url"),
            "prod_name": data.get("prod_name"),
            "hbx_version": data.get("hbx_version"),
            "uniapp_id": data.get("uniapp_id"),
            "uniapp_appkey": data.get("uniapp_appkey"),
            "uniapp_is_cli": data.get("uniapp_is_cli", False),
        }

        # 提取第三方配置
        third_party_configs = data.get("third_party_configs", [])

        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()

        try:
            # 插入项目配置
            cursor.execute(
                """
                INSERT INTO project_config 
                (id, project_url, prod_name, hbx_version, uniapp_id, uniapp_appkey, uniapp_is_cli)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    project_config["id"],
                    project_config["project_url"],
                    project_config["prod_name"],
                    project_config["hbx_version"],
                    project_config["uniapp_id"],
                    project_config["uniapp_appkey"],
                    project_config["uniapp_is_cli"],
                ),
            )

            # 插入第三方配置
            for config in third_party_configs:
                cursor.execute(
                    """
                    INSERT INTO third_party_config 
                    (project_id, dict_key, config_value)
                    VALUES (?, ?, ?)
                    """,
                    (project_id, config["key"], config["value"]),
                )

            conn.commit()
            return (
                jsonify({"message": "Project configured successfully", "project_id": project_id}),
                200,
            )

        except sqlite3.IntegrityError as e:
            conn.rollback()
            return jsonify({"error": f"Database integrity error: {str(e)}"}), 400
        finally:
            conn.close()

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@project_bp.route("/api/config/project", methods=["GET"])
def get_project_config():
    """获取项目配置信息"""
    try:
        # 获取查询参数
        project_url = request.args.get("url")
        prod_name = request.args.get("name")

        if not project_url and not prod_name:
            return jsonify({"error": "Must provide either url or name parameter"}), 400

        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()

        # 构建查询条件
        query_conditions = []
        query_params = []

        if project_url:
            query_conditions.append("project_url = ?")
            query_params.append(project_url)
        if prod_name:
            query_conditions.append("prod_name = ?")
            query_params.append(prod_name)

        # 获取项目基础配置
        query = f"""
            SELECT * FROM project_config 
            WHERE {' AND '.join(query_conditions)}
        """
        cursor.execute(query, query_params)
        project_config = cursor.fetchone()

        if not project_config:
            return jsonify({"error": "Project not found"}), 404

        # 获取项目ID
        project_id = project_config[0]

        # 获取第三方配置
        cursor.execute(
            """
            SELECT tpc.dict_key, tpc.config_value, tpd.provider, tpd.description
            FROM third_party_config tpc
            JOIN third_party_dict tpd ON tpc.dict_key = tpd.dict_key
            WHERE tpc.project_id = ?
            """,
            (project_id,),
        )
        third_party_configs = cursor.fetchall()

        # 构建响应数据
        response_data = {
            "project_config": {
                "id": project_config[0],
                "project_url": project_config[1],
                "prod_name": project_config[2],
                "hbx_version": project_config[3],
                "uniapp_id": project_config[4],
                "uniapp_appkey": project_config[5],
                "uniapp_is_cli": bool(project_config[6]),
            },
            "third_party_configs": [
                {
                    "key": config[0],
                    "value": config[1],
                    "provider": config[2],
                    "description": config[3],
                }
                for config in third_party_configs
            ],
        }

        return jsonify(response_data), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()


@project_bp.route("/api/config/project/<project_id>", methods=["PUT"])
def update_project_config(project_id):
    """更新项目配置信息"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No JSON data received"}), 400

        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()

        try:
            # 更新项目基础配置
            update_fields = []
            update_values = []
            if "project_url" in data:
                update_fields.append("project_url = ?")
                update_values.append(data["project_url"])
            if "prod_name" in data:
                update_fields.append("prod_name = ?")
                update_values.append(data["prod_name"])
            if "hbx_version" in data:
                update_fields.append("hbx_version = ?")
                update_values.append(data["hbx_version"])
            if "uniapp_id" in data:
                update_fields.append("uniapp_id = ?")
                update_values.append(data["uniapp_id"])
            if "uniapp_appkey" in data:
                update_fields.append("uniapp_appkey = ?")
                update_values.append(data["uniapp_appkey"])
            if "uniapp_is_cli" in data:
                update_fields.append("uniapp_is_cli = ?")
                update_values.append(data["uniapp_is_cli"])

            if update_fields:
                update_fields.append("updated_at = datetime('now', 'localtime')")
                update_values.append(project_id)
                cursor.execute(
                    f"""
                    UPDATE project_config 
                    SET {', '.join(update_fields)}
                    WHERE id = ?
                    """,
                    update_values,
                )

            # 处理第三方配置更新
            if "third_party_configs" in data:
                # 获取现有配置
                cursor.execute(
                    """
                    SELECT dict_key, config_value FROM third_party_config 
                    WHERE project_id = ?
                    """,
                    (project_id,),
                )
                existing_configs = {row[0]: row[1] for row in cursor.fetchall()}

                # 新的配置
                new_configs = {
                    config["key"]: config["value"] for config in data["third_party_configs"]
                }

                # 要删除的配置
                to_delete = set(existing_configs.keys()) - set(new_configs.keys())
                if to_delete:
                    cursor.execute(
                        """
                        DELETE FROM third_party_config 
                        WHERE project_id = ? AND dict_key IN ({})
                        """.format(
                            ",".join("?" * len(to_delete))
                        ),
                        (project_id,) + tuple(to_delete),
                    )

                # 更新或插入配置
                for key, value in new_configs.items():
                    if key in existing_configs:
                        if existing_configs[key] != value:
                            # 更新现有配置
                            cursor.execute(
                                """
                                UPDATE third_party_config 
                                SET config_value = ?, updated_at = datetime('now', 'localtime')
                                WHERE project_id = ? AND dict_key = ?
                                """,
                                (value, project_id, key),
                            )
                    else:
                        # 插入新配置
                        cursor.execute(
                            """
                            INSERT INTO third_party_config 
                            (project_id, dict_key, config_value)
                            VALUES (?, ?, ?)
                            """,
                            (project_id, key, value),
                        )

            conn.commit()
            return jsonify({"message": "Project configuration updated successfully"}), 200

        except sqlite3.IntegrityError as e:
            conn.rollback()
            return jsonify({"error": f"Database integrity error: {str(e)}"}), 400
        finally:
            conn.close()

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@project_bp.route("/api/config/projects", methods=["GET"])
def get_projects():
    """获取所有项目配置列表"""
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()

        # 获取所有项目基础配置
        cursor.execute(
            """
            SELECT id, project_url, prod_name, hbx_version, uniapp_id, uniapp_appkey, uniapp_is_cli
            FROM project_config 
            ORDER BY prod_name
        """
        )
        projects = cursor.fetchall()

        # 获取每个项目的第三方配置
        projects_list = []
        for project in projects:
            cursor.execute(
                """
                SELECT tpc.dict_key, tpc.config_value, tpd.provider, tpd.description
                FROM third_party_config tpc
                JOIN third_party_dict tpd ON tpc.dict_key = tpd.dict_key
                WHERE tpc.project_id = ?
            """,
                (project[0],),
            )
            third_party_configs = cursor.fetchall()

            projects_list.append(
                {
                    "id": project[0],
                    "project_url": project[1],
                    "prod_name": project[2],
                    "hbx_version": project[3],
                    "uniapp_id": project[4],
                    "uniapp_appkey": project[5],
                    "uniapp_is_cli": bool(project[6]),
                    "third_party_configs": [
                        {
                            "key": config[0],
                            "value": config[1],
                            "provider": config[2],
                            "description": config[3],
                        }
                        for config in third_party_configs
                    ],
                }
            )

        return jsonify({"projects": projects_list}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()
