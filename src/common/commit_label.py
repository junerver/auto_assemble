import re
from typing import Optional


def get_build_req_label(build_mode: str, req_resp: str = "req") -> str:
    """
    获取构建请求标签
    Args:
        req_resp: 请求标识、响应标识
        build_mode (str): 构建模式，可选值：dev、test、release
    Returns:
        str: 构建请求标签
    """
    return f"#{build_mode}_{req_resp}# "


def get_build_resp_message(build_mode: str, commit_message: str) -> str:
    return f"{get_build_req_label(build_mode, 'resp')}{commit_message}"


def parse_build_req_message(message: str) -> tuple[Optional[str], Optional[str]]:
    """
    解析构建请求标签
    Args:
        message (str): 构建请求消息，它是一个 `#{build_mode}_req# {commit_message}` 格式的字符串，需要通过正则提取出build_mode和commit_message
    Returns:
        tuple: 构建模式，构建请求的commit message
    """
    pattern = r"#(\w+)_req#\s*(.*)"
    match = re.search(pattern, message)
    if match:
        return match.group(1), match.group(2)
    return None, None


def parse_build_branch(build_mode: str) -> str:
    return "master" if build_mode == "dev" else build_mode
