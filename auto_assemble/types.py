from dataclasses import dataclass
from pathlib import Path
from typing import TypedDict, NotRequired


class BuildMetadata(TypedDict):
    """
    构建任务产物元数据
    """

    package_name: NotRequired[str]
    version_name: NotRequired[str]
    version_code: NotRequired[int]
    build_type: NotRequired[str]
    flavor: NotRequired[str]
    build_date: NotRequired[str]
    file_size: NotRequired[int]
    md5: NotRequired[str]
    is_normalized: NotRequired[bool]
    is_obfuscated: NotRequired[bool]


@dataclass
class SignConfig:
    """签名配置"""

    # 签名文件别名
    alias: str
    # 签名文件密码
    ks_pass: str
    # 签名文件别名密码
    key_pass: str
    # 签名文件路径
    key_store: Path
