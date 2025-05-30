distributionUrl = "http://192.168.187.232:28088/rdcenter/app-distribution/"


def build_gitlab_url(commit_hash: str, task_id: str, file_name: str):
    """构建gitlab的文件url

    Args:
        commit_hash: 对应提交的hash值
        task_id: 任务id（能指向文件路径）
        file_name: 文件名
    """
    prod_name, task = task_id.split(",")
    return f"{distributionUrl}-/raw/{commit_hash}/{prod_name}/{task}/{file_name}"
