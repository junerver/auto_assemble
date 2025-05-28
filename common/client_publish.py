import threading

import requests

from common.config import config


def _client_publish(event_type: str, title: str, message: str):
    """客户端主动想服务器推送事件

    例如，在构建过程中推送构建进度
    """
    url = f"{config.SERVER_HOST_URL}/events/publish"
    requests.post(url, json={"type": event_type, "title": title, "message": message})


def client_publish_async(event_type: str, title: str, message: str):
    threading.Thread(target=_client_publish, args=(event_type, title, message), daemon=True).start()
