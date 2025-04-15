from flask import jsonify, request

from . import auth_bp

AUTHORIZED_IP = "192.168.172.110"


@auth_bp.route("/check-ip", methods=["GET"])
def check_ip():
    """检查客户端IP是否授权"""
    client_ip = request.remote_addr
    is_authorized = client_ip == AUTHORIZED_IP

    return jsonify({"authorized": is_authorized, "client_ip": client_ip})
