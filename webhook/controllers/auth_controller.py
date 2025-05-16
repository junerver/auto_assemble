from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from webhook.types import AuthResponse

router = APIRouter(tags=["auth"])

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
    "192.168.172.110": "admin",
    "172.18.0.1": "admin",
}


@router.get("/check-ip", response_model=AuthResponse)
async def check_ip(request: Request):
    """检查客户端IP是否授权"""
    client_ip = request.client.host
    is_authorized = client_ip in AUTHORIZED_IP_ROLE_MAP
    role = AUTHORIZED_IP_ROLE_MAP.get(client_ip) or "guest"

    response_date = AuthResponse(
        authorized=is_authorized,
        client_ip=client_ip,
        role=role,
        permissions=ROLE_MAP[role] if is_authorized else [],
    )

    return JSONResponse(
        status_code=200,
        content=response_date.model_dump(),
    )
