import re


def is_valid_build_task(added_files):
    """验证是否是有效的构建任务"""
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
    has_archive = any(
        file_path.endswith((".zip", ".rar", ".7z", ".tar.gz", ".tar.bz2"))
        for file_path in added_files
    )
    has_md = any(file_path.endswith(".md") for file_path in added_files)

    return has_archive and has_md


def parse_build_task(added_files):
    """解析构建任务信息"""
    file_path = added_files[0]
    parts = file_path.split("/")
    prod_name = parts[0]
    task_name = parts[1]
    return prod_name, task_name
