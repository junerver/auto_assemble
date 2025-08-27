import logging
import sqlite3
from datetime import datetime, timezone, timedelta
from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse

from common.commit_label import parse_build_req_message
from common.git import parse_git_author
from webhook.config import PORT, LOCAL_REF_FLAG
from webhook.controllers.webhook_controller import webhook
from webhook.types import GitLabPushEventReq


def mock_request_body(author: str, prod_name: str, task: str, commit_message: str, md5: str = None):
    """
    mock请求体
    Args:
        author: git格式的作者信息，即：xxx <xxx@xxx.com>
        prod_name: 项目标识
        task: 任务时间戳
        commit_message: 提交信息
        md5: apk 文件的md5，当不传递该字段时构建cbr请求，传递时构建auto-assemble响应请求

    Returns:

    """
    if md5 is None:
        # cbr请求体
        file_list = [
            f"{prod_name}/{task}/{task}.zip",
            f"{prod_name}/{task}/README.md",
        ]
    else:
        build_mode = parse_build_req_message(commit_message)[0]
        apk_name = f"{task}_debug.apk" if build_mode == "dev" else f"{task}.apk"
        # auto_assemble 响应体
        file_list = [
            f"{prod_name}/{task}/{apk_name}",
            f"{prod_name}/{task}/release-metadata.md",
            f"{prod_name}/{task}/{md5}",
        ]
    username, email = parse_git_author(author)
    return {
        "object_kind": "push",
        "event_name": "push",
        "before": "c27d5f0a725a6fc14b4942b74a0fa4b0c82b6784",
        "after": "d00bd7c7eecefd593a8e188e31a3ef23803655c0",
        "ref": "refs/heads/master",
        "ref_protected": True,
        "checkout_sha": "d00bd7c7eecefd593a8e188e31a3ef23803655c0",
        "message": None,
        "user_id": 116,
        "user_name": "\u4faf\u6587\u541b",
        "user_username": "houwenjun",
        "user_email": None,
        "user_avatar": None,
        "project_id": 377,
        "project": {
            "id": 377,
            "name": "app-distribution",
            "description": "\u5e94\u7528\u5206\u53d1",
            "web_url": "http://192.168.187.232:28088/rdcenter/app-distribution",
            "avatar_url": None,
            "git_ssh_url": "git@192.168.187.232:rdcenter/app-distribution.git",
            "git_http_url": "http://192.168.187.232:28088/rdcenter/app-distribution.git",
            "namespace": "rdcenter",
            "visibility_level": 0,
            "path_with_namespace": "rdcenter/app-distribution",
            "default_branch": "master",
            "ci_config_path": None,
            "homepage": "http://192.168.187.232:28088/rdcenter/app-distribution",
            "url": "git@192.168.187.232:rdcenter/app-distribution.git",
            "ssh_url": "git@192.168.187.232:rdcenter/app-distribution.git",
            "http_url": "http://192.168.187.232:28088/rdcenter/app-distribution.git",
        },
        "total_commits_count": 1,
        "push_options": {},
        "repository": {
            "name": "app-distribution",
            "url": "git@192.168.187.232:rdcenter/app-distribution.git",
            "description": "\u5e94\u7528\u5206\u53d1",
            "homepage": "http://192.168.187.232:28088/rdcenter/app-distribution",
            "git_http_url": "http://192.168.187.232:28088/rdcenter/app-distribution.git",
            "git_ssh_url": "git@192.168.187.232:rdcenter/app-distribution.git",
            "visibility_level": 0,
        },
        "commits": [
            {
                "id": LOCAL_REF_FLAG,
                "message": f"{commit_message}\n",
                "title": f"{commit_message}",
                "timestamp": datetime.now(timezone(timedelta(hours=8))).replace(microsecond=0).isoformat(),
                "url": "http://192.168.187.232:28088/rdcenter/app-distribution/-/commit/LOCAL_FILE_SERVER",
                "author": {"name": username, "email": email},
                "added": file_list,
                "modified": [],
                "removed": [],
            }
        ],
    }


def mock_request_headers(is_cache: bool = False):
    headers = {
        "content-type": "application/json",
        "user-agent": "GitLab/17.5.1",
        "idempotency-key": "7bafea1a-a1bf-4948-9a37-3f912777dedc",
        "x-gitlab-event": "Push Hook",
        "x-gitlab-webhook-uuid": "d96cd136-d798-4abc-b542-07c41d1d9333",
        "x-gitlab-instance": "http://192.168.187.232:28088",
        "x-gitlab-event-uuid": "1697b63f-d1eb-4c59-b2c1-e65b12e635c0",
        "accept-encoding": "gzip;q=1.0,deflate;q=0.6,identity;q=0.3",
        "accept": "*/*",
        "connection": "close",
        "host": "192.168.189.243:5005",
        "content-length": "1987",
    }
    if is_cache:
        headers["X-Webhook-Request-Cache"] = "true"
    return headers


async def send_mock_request(request_body, headers, db: sqlite3.Connection, is_cache: bool = False) -> JSONResponse:
    """
    发送模拟的 GitLab Push Hook 请求
    Args:
        request_body: 模拟的请求体
        headers: 模拟的请求头
        db: 数据库连接
        is_cache: 是否缓存请求，重播任务时需要注明
    Returns:
        模拟的响应
    """
    try:
        # 构造 GitLabPushEventReq 对象
        event = GitLabPushEventReq(**request_body)

        # 确保 headers 安全，转换为字符串并添加 X-Webhook-Request-Cache
        safe_headers = {str(k).lower(): str(v) for k, v in headers.items() if v is not None}
        if is_cache:
            safe_headers["x-webhook-request-cache"] = "true"  # 统一小写，确保大小写一致
        logging.info(f"构造的 headers: {safe_headers}")

        # 构造正确的 scope 字典
        scope = {
            "type": "http",
            "http_version": "1.1",
            "method": "POST",
            "path": "/webhook",
            "headers": [(k.encode("utf-8"), v.encode("utf-8")) for k, v in safe_headers.items()],
            "scheme": "http",
            "server": ("localhost", PORT),
            "client": ("127.0.0.1", 0),
        }

        # 构造 Request 对象
        request = Request(scope=scope)
        logging.info(f"构造的 Request headers: {dict(request.headers)}")

        # 直接调用 webhook 函数
        response = await webhook(event=event, request=request, db=db)

        if isinstance(response, JSONResponse):
            return JSONResponse(
                status_code=response.status_code,
                content={
                    "message": "Webhook请求重放成功" if response.status_code == 200 else "Webhook请求重放失败",
                    "response": response.body.decode("utf-8") if isinstance(response.body, bytes) else response.body,
                },
            )
        return response
    except Exception as e:
        logging.error(f"重放webhook请求时发生错误: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
