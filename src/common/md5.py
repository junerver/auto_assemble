import hashlib
from pathlib import Path


def calculate_file_md5(file_path: Path, chunk_size=8192) -> str:
    """
    计算文件的 MD5
    Args:
        file_path: 文件路径
        chunk_size: 块大小

    Returns: md5 值

    """
    md5 = hashlib.md5()
    with open(file_path, "rb") as f:
        while chunk := f.read(chunk_size):
            md5.update(chunk)
    return md5.hexdigest()
