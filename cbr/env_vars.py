from dataclasses import dataclass


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
