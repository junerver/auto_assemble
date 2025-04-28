from cbr.types import ThirdPartyConfig


def parse_third_party_configs(
        third_party_configs: list[ThirdPartyConfig],
) -> dict[str, dict]:
    """
    将从服务器获取的第三方配置列表解析为字典对象
    Args:
        third_party_configs: 从服务器获取的第三方配置

    Returns:

    """
    # 提取第三方配置成正确的格式
    third_party_config = {}
    if third_party_configs:
        # 按provider分组配置
        provider_configs = {}
        for config in third_party_configs:
            provider = config["provider"]
            if provider not in provider_configs:
                provider_configs[provider] = {}
            provider_configs[provider][config["dict_value"]] = config["config_value"]

        # 将分组后的配置添加到third_party_config
        for provider, config in provider_configs.items():
            third_party_config[provider] = config
    return third_party_config
