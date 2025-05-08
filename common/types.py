from dataclasses import dataclass
from typing import NotRequired, TypedDict
from xml.dom.minidom import Element


class ManifestInfo(TypedDict):
    hbx_version: str
    version_name: str
    version_code: str
    uniapp_id: str
    uniapp_key: str
    third_party_config: dict[str, dict]
    permissions: dict[str, dict]
    permissions_content: NotRequired[str]
    modules: list[str]
    abi_filters: str
    schemes: str


class PermissionsFeatures(TypedDict):
    """
    全部权限与特性的字典
    """

    # 权限名称-xml实例
    permissions: dict[str, Element]
    # 特性名称-xml实例
    features: dict[str, Element]


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
    DISTRIBUTION_PATH: str
    # 项目标识
    PROD_NAME: str
    # hbuilderx 版本
    HBX_VERSION: str
    # 项目id
    UNIAPP_ID: str
    # 项目key
    UNIAPP_APPKEY: str
    # 本地地址
    UNIAPP_WORKSPACE: str
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
