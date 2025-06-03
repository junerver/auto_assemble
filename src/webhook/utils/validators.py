import re
from typing import Optional

from webhook.types import Commit


def is_valid_assemble_response(commit: Commit) -> tuple[bool, Optional[str]]:
    """
    验证是否是有效的组装响应
    1. 提交信息以 #(.*)_resp# 格式开头
    2. 添加的文件数量至少为3个（apk文件、markdown文件、MD5文件、bak混淆备份文件[可选]）

    Args:
        commit: 提交信息

    Returns:
        tuple[bool, str]: 是否是有效的组装响应, 如果有效，返回组装响应的hash值
    """
    commit_title = commit.title or ""
    if not commit_title or not re.match(r"#\w+_resp#", commit_title):
        return False, None
    added_files = commit.added or []
    if not added_files:
        return False, None
    if len(added_files) < 3:
        return False, None
    pattern = r"^([^/]+)/([^/]+)/([^/]+\.apk|[^/]+\.bak|[^/]+\.md|[^/]+)$"
    for file_path in added_files:
        match = re.match(pattern, file_path)
        if not match:
            return False, None
    return True, commit.id or ""


def is_valid_build_task(commit: Commit) -> bool:
    """
    验证是否是有效的构建任务，有效的任务需要满足：
    1. 提交信息以 #(.*)_req# 格式开头
    2. 添加的文件数量为2个
    3. 添加的文件中包含压缩包和markdown文件

    Args:
        commit: 提交信息

    Returns:
        bool: 是否是有效的构建任务
    """
    # 获取提交信息，正则匹配是否为 #(.*)_req# 格式开头
    commit_title = commit.title or ""
    if not commit_title or not re.match(r"#\w+_req#", commit_title):
        return False
    # 获取添加的文件
    added_files = commit.added or []
    if not added_files:
        return False

    if len(added_files) != 2:
        return False

    pattern = r"^([^/]+)/([^/]+)/([^/]+\.(zip|rar|7z|tar\.gz|tar\.bz2)|[^/]+\.md)$"
    paths = []
    for file_path in added_files:
        match = re.match(pattern, file_path)
        if not match:
            return False
        paths.append(match.groups())

    if paths[0][0] != paths[1][0] or paths[0][1] != paths[1][1]:
        return False

    # 检查是否包含压缩包和markdown文件
    has_archive = any(file_path.endswith((".zip", ".rar", ".7z", ".tar.gz", ".tar.bz2")) for file_path in added_files)
    has_md = any(file_path.endswith(".md") for file_path in added_files)

    return has_archive and has_md


def parse_build_task(commit: Commit):
    """
    解析构建任务信息
    Args:
        commit: 提交信息

    Returns:
        tuple: 构建任务信息
    """
    added_files = commit.added or []
    if not added_files:
        return None, None

    file_path = added_files[0]
    parts = file_path.split("/")
    prod_name = parts[0]
    task_name = parts[1]
    return prod_name, task_name


if __name__ == "__main__":
    commit_dic = {
        "id": "004afed756dc0978b7079aa33c451969d74d7e6c",
        "message": "#dev_resp# 202505281634 打包\n",
        "title": "#dev_resp# 202505281634 打包",
        "timestamp": "2025-05-28T16:35:51+08:00",
        "url": "http://192.168.187.232:28088/rdcenter/app-distribution/-/commit/004afed756dc0978b7079aa33c451969d74d7e6c",
        "author": {"name": "assemble_bot", "email": "[REDACTED]"},
        "added": [
            "identify_field/202505281634/202505281634_debug.apk",
            "identify_field/202505281634/90627c9ab908acced74dd4367d3d14db",
            "identify_field/202505281634/release-metadata.md",
        ],
        "modified": [],
        "removed": [],
    }
    print(is_valid_assemble_response(Commit(**commit_dic)))
