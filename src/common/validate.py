import re
from datetime import datetime


def validate_timestamp_format(timestamp) -> bool:
    """验证时间戳格式是否为yyyyMMddHHmm"""
    pattern = r"^\d{12}$"
    if not re.match(pattern, timestamp):
        return False
    try:
        datetime.strptime(timestamp, "%Y%m%d%H%M")
        return True
    except ValueError:
        return False


def validate_git_author(author: str) -> bool:
    """
    校验作者信息格式是否符合要求
    Args:
        author:

    Returns:

    """
    pattern = r"^[^\s<]+(?:\s+[^\s<]+)*\s+<[^@]+@[^@]+\.[^@]+>$"
    return bool(re.match(pattern, author.strip()))
