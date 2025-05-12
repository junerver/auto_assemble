from flask import jsonify, request

from . import auth_bp

ROLE_MAP = {
    "admin": [
        "create_project",
        "update_project",
        "delete_project",
        "show_project_detail",
        "replay_task",
        "stop_task",
        "fork_task",
        "delete_task",
    ],
    "user": ["replay_task", "fork_task", "show_project_detail"],
    "guest": [],
}

# 授权用户IP，与权限等级的映射
AUTHORIZED_IP_ROLE_MAP = {
    "192.168.172.110": "user",
    "172.18.0.1": "admin",
}


@auth_bp.route("/check-ip", methods=["GET"])
def check_ip():
    """检查客户端IP是否授权"""
    client_ip = request.remote_addr
    is_authorized = client_ip in AUTHORIZED_IP_ROLE_MAP
    role = AUTHORIZED_IP_ROLE_MAP[client_ip]
    if is_authorized:
        permissions = ROLE_MAP[role]
    else:
        permissions = []

    return jsonify(
        {
            "authorized": is_authorized,
            "client_ip": client_ip,
            "role": role,
            "permissions": permissions,
        }
    )
