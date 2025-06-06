from dataclasses import dataclass
from pathlib import Path
from typing import NotRequired, TypedDict, Optional, TypeAlias
import xml.etree.ElementTree as ET

from dataclasses_json import DataClassJsonMixin


class ManifestInfo(TypedDict):
    hbx_version: str
    version_name: str
    version_code: str
    uniapp_id: str
    uniapp_key: str
    third_party_config: NotRequired[dict[str, dict]]
    # 解析权限文本后，合并的完整权限、特性字典
    permissions: NotRequired["PermissionsFeatures"]
    # 用于构建 README.md 文件填充到权限说明的完整文本内容
    permissions_content: NotRequired[str]
    modules: list[str]
    abi_filters: str
    schemes: str


class PermissionsFeatures(TypedDict):
    """
    全部权限与特性的字典，其中键为全名称，例如 "android.permission.INTERNET"，
    值为真实的 ET.Element 实例，例如 ET.Element("uses-permission", {"android:name": "android.permission.INTERNET"})
    """

    # 权限名称-xml实例
    permissions: NotRequired[dict[str, ET.Element]]
    # 特性名称-xml实例
    features: NotRequired[dict[str, ET.Element]]


class ManifestPermissions(TypedDict):
    """
    从manifest中解析出的三个权限分区
    """

    default: PermissionsFeatures
    add: PermissionsFeatures
    del_: PermissionsFeatures


@dataclass
class CbrEnvVars:
    # 分发仓库位置
    DISTRIBUTION_PATH: Path
    # 项目标识
    PROD_NAME: str
    # hbuilderx 版本
    HBX_VERSION: str
    # 项目id
    UNIAPP_ID: str
    # 项目key
    UNIAPP_APPKEY: str
    # 本地地址
    UNIAPP_WORKSPACE: Path
    # 是否为cli项目
    UNIAPP_IS_CLI: bool


class ThirdPartyConfig(TypedDict):
    # 第三方配置项的描述
    description: str
    # 第三方配置项的key，该key与基座中的manifestPlaceholders中一致
    dict_key: str
    # 第三方配置项的提供者
    provider: str
    # 第三方配置项的值
    dict_value: str
    # 实际配置的值
    config_value: str


# 在业务逻辑使用的折叠后的第三方配置的总字典，键值为第三方[服务提供者的名称]，值为实际该服务的[配置字典]
# 配置字典键值为[第三方服务的key]，值为[第三方服务的value]
AllThirdPartyConfigsDict: TypeAlias = dict[str, dict[str, str]]


@dataclass
class Metadata:
    package_name: str
    version_name: str
    version_code: int
    build_type: str
    flavor: str
    build_date: str
    file_size: int
    md5: str
    is_normalized: bool
    is_obfuscated: bool


@dataclass
class TaskInfo(DataClassJsonMixin):
    # 任务id
    id: str
    # 任务提交人
    author: str
    commit_title: str
    commit_message: str
    commit_url: str
    priority: int
    retries: int
    created_at: Optional[str]
    started_at: Optional[str]
    completed_at: Optional[str]
    status: Optional[str]
    error: Optional[str]
    commit_hash: Optional[str]
    response_hash: Optional[str]
    metadata: Optional[Metadata]
    source_task_id: Optional[str]
    project: str
    task: str
