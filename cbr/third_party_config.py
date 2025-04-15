from dataclasses import dataclass


@dataclass
class ThirdPartyConfig:
    # 第三方配置项的描述
    description: str
    # 第三方配置项的key，该key与基座中的manifestPlaceholders中一致
    key: str
    # 第三方配置项的提供者
    provider: str
    # 第三方配置项的值
    value: str
