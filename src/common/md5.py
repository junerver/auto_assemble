import hashlib
import zipfile
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


def calculate_zip_fingerprint(zip_path: Path) -> str:
    """
    生成 zip 包的“内容感知” fingerprint（与元数据、顺序无关），
    通过该函数可以为原始Uni资源包计算出一个资源包指纹，如果资源包
    指纹一致，可以直接复用之前的构建响应的结果内容？
    """
    entries = []
    with zipfile.ZipFile(zip_path, "r") as zf:
        for info in zf.infolist():
            if info.is_dir():
                continue
            with zf.open(info.filename) as f:
                content = f.read()
                file_hash = hashlib.md5(content).hexdigest()
                entries.append((info.filename, file_hash))

    # 排序确保不受压缩顺序影响
    entries.sort()

    # 拼接成唯一字符串再 hash 一次
    concat_str = "".join([f"{name}:{entry_hash}" for name, entry_hash in entries])
    final_fingerprint = hashlib.sha256(concat_str.encode()).hexdigest()

    return final_fingerprint
