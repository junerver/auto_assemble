from dataclasses import dataclass
from pathlib import Path
from typing import NotRequired, TypedDict, Optional, TypeAlias
import xml.etree.ElementTree as ET

from dataclasses_json import DataClassJsonMixin


# 在业务逻辑使用的折叠后的第三方配置的总字典，键值为第三方[服务提供者的名称]，值为实际该服务的[配置字典]
# 配置字典键值为[第三方服务的key]，值为[第三方服务的value]
AllThirdPartyConfigsDict: TypeAlias = dict[str, dict[str, str]]


class ManifestInfo(TypedDict):
    hbx_version: str
    version_name: str
    version_code: str
    uniapp_id: str
    uniapp_key: str
    third_party_config: NotRequired["AllThirdPartyConfigsDict"]
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
    # 状态
    status: Optional[str]
    # 错误信息
    error: Optional[str]
    # 构建请求hash，通过该hash可以指向构建请求的Uni资源包
    commit_hash: Optional[str]
    # 构建响应hash，通过该hash可以指向构建响应apk文件
    response_hash: Optional[str]
    # 构建成功后的apk文件元信息
    metadata: Optional[Metadata]
    # 如果来自派生任务，则为派生任务id
    source_task_id: Optional[str]
    # 项目标识
    project: str
    # 任务时间戳
    task: str


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
