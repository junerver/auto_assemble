import logging
import os
import re

import requests
import yaml

from auto_assemble.config import config
from auto_assemble.parse_permissions import parse_and_merge_permissions
from auto_assemble.parse_third_party_configs import parse_third_party_configs
from cbr.types import ManifestInfo


def parse_uni_modules(content: str) -> list[str]:
    """
    从README.md内容中解析模块信息
    Args:
        content: README.md文件内容
    Returns:
        list[str]: 解析出的模块列表，每个元素为模块名称
    """
    try:
        # 使用正则表达式匹配模块信息部分
        modules_section = re.search(
            r"9\. 模块信息：\n\n(.*?)(?=\n\n|$)", content, re.DOTALL
        )
        if not modules_section:
            logging.warning("未找到模块信息部分")
            return []

        modules_text = modules_section.group(1)
        # 匹配每个模块行，直接提取 > - 后面的内容，直到行尾
        modules = re.findall(r"> - (.*?)(?=\n|$)", modules_text)

        # 清理每个模块名称
        modules = [module.strip() for module in modules]

        logging.info(f"成功解析模块信息: {modules}")
        return modules
    except Exception as e:
        logging.error(f"解析模块信息时发生错误: {e}")
        return []


def parse_yaml_block(content: str) -> dict[str, dict[str, str]]:
    """
    从内容中解析 YAML 代码块
    Args:
        content: 文件内容
    Returns:
        dict[str, dict[str, str]]: 解析后的 YAML 配置信息
    """
    try:
        # 使用更宽松的匹配模式
        yaml_match = re.search(r"```(?:yml|yaml)\s*\n(.*?)\n\s*```", content, re.DOTALL)
        if not yaml_match:
            logging.warning("未找到 YAML 代码块")
            return {}

        yaml_content = yaml_match.group(1)

        # 预处理：将包含 % 的值用引号包裹
        lines = yaml_content.split("\n")
        processed_lines = []
        for line in lines:
            if ":" in line:
                key, value = line.split(":", 1)
                value = value.strip()
                if value.startswith("%"):
                    processed_lines.append(f"{key}: '{value}'")
                else:
                    processed_lines.append(line)
            else:
                processed_lines.append(line)

        yaml_content = "\n".join(processed_lines)

        # 解析 YAML 内容
        third_party_config_yaml = yaml.safe_load(yaml_content)

        # 重新组织配置结构
        result = {}
        for key, value in third_party_config_yaml.items():
            if isinstance(value, dict):
                result[key] = value
            elif key in ["appid", "secret"]:
                if "wechat" not in result:
                    result["wechat"] = {}
                result["wechat"][key] = value
            elif key == "appkey":
                if "amap" not in result:
                    result["amap"] = {}
                result["amap"][key] = value
            elif key == "appkey":
                if "baidu" not in result:
                    result["baidu"] = {}
                result["baidu"][key] = value

        return result
    except Exception as e:
        logging.error(f"解析 YAML 代码块时发生错误: {e}")
        return {}


def parse_readme(readme_path: str) -> ManifestInfo | None:
    """
    从 README.md 文件中解析版本信息
    Args:
        readme_path: README.md 文件路径
    Returns:
        dict[str, str]: 包含版本信息的字典，包括以下键：
            - hbx_version: HBuilderX 版本
            - version_name: 版本名称
            - version_code: 版本号
            - uniapp_id: Uniapp App ID
            - uniapp_key: Uniapp App key
            - third_party_config: 第三方配置信息
            - permissions: permissions 和 features 的合并结果
            - abi_filters: abiFilters 配置
            - schemes: 注册schema在其它App中打开当前App，多个scheme使用','号分割，例如：test1,test2
            - modules: 项目使用的模块列表
        如果解析失败则对应值为空字符串
    """
    try:
        if not os.path.exists(readme_path):
            logging.warning(f"README.md 文件不存在: {readme_path}")
            return None

        with open(readme_path, "r", encoding="utf-8") as file:
            content = file.read()

        # 使用正则表达式匹配版本信息
        hbx_version_match = re.search(r"HBuilderX 版本：`([^`]+)`", content)
        uniapp_id_match = re.search(r"Uniapp App ID：`([^`]+)`", content)
        uniapp_key_match = re.search(r"Uniapp App key：`([^`]+)`", content)
        version_name_match = re.search(r"versionName：`([^`]+)`", content)
        version_code_match = re.search(r"versionCode：`([^`]+)`", content)
        abi_filters_match = re.search(r"AbiFilters：`([^`]+)`", content)
        schemes_match = re.search(r"UrlSchemes：`([^`]+)`", content)

        # 解析第三方配置
        # todo: 重构第三方配置读取，修改为从服务器接口读取，不再解析yaml代码块
        response = requests.get(
            f"{os.getenv('SERVER_HOST_URL')}/api/config/project?name={config.PROD_NAME}"
        )
        if response.status_code == 200:
            data = response.json()
            third_party_configs = data["third_party_configs"]
            third_party_config = parse_third_party_configs(third_party_configs)
        else:
            # 如果从服务器接口读取失败，则使用本地解析
            third_party_config = parse_yaml_block(content)
            if config.PROD_NAME == "identify_field":
                logging.info("识田间项目使用正式微信配置")
                third_party_config.pop("wechat", None)
                third_party_config["wechat"] = {
                    "appid": "wx4d4456070d11a01a",
                    "secret": "b8ad75cd1cd6715de7d27b350e1814a5",
                }

        # 普通项目正常读取
        abi_filters = (
            abi_filters_match.group(1)
            if abi_filters_match
            else '"armeabi-v7a", "arm64-v8a"'
        )
        # 识田间项目使用armeabi-v7a，arm64-v8a
        if config.PROD_NAME == "identify_field":
            abi_filters = '"armeabi-v7a", "arm64-v8a"'

        # 解析权限
        permissions = parse_and_merge_permissions(content)

        # 解析模块信息
        modules = parse_uni_modules(content)

        result: ManifestInfo = {
            "hbx_version": hbx_version_match.group(1) if hbx_version_match else "",
            "version_name": version_name_match.group(1) if version_name_match else "",
            "version_code": version_code_match.group(1) if version_code_match else "",
            "uniapp_id": uniapp_id_match.group(1) if uniapp_id_match else "",
            "uniapp_key": uniapp_key_match.group(1) if uniapp_key_match else "",
            "third_party_config": third_party_config,
            "permissions": permissions,
            "abi_filters": abi_filters,
            "schemes": schemes_match.group(1) if schemes_match else "",
            "modules": modules,
        }

        if all(result.values()):
            logging.info(
                f"成功解析版本信息 - "
                f"hbx_version: {result['hbx_version']}, "
                f"versionName: {result['version_name']}, "
                f"versionCode: {result['version_code']}, "
                f"uniapp_id: {result['uniapp_id']}, "
                f"uniapp_key: {result['uniapp_key']}, "
                f"abi_filters: {result['abi_filters']}, "
                f"schemes: {result['schemes']}, "
                f"modules: {result['modules']}"
            )
        else:
            logging.warning(f"未能完整解析README.md信息，解析结果：{result}")

        return result
    except Exception as e:
        logging.error(f"解析 README.md 文件时发生错误: {e}")
        return None


if __name__ == "__main__":
    # 模块依赖映射字典
    _result = parse_readme(os.path.join(r"./", "list.md"))
    print(_result)
    _modules = _result.get("modules", [])
    if "Maps : amap" in _modules and "Geolocation : amap" in _modules:
        # 同时存在高德地图与高德定位
        _modules.remove("Maps : amap")
        _modules.remove("Geolocation : amap")
        _modules.append("Maps : amap & Geolocation : amap")
    from auto_assemble.update_build_gradle import MODULE_DEPENDENCY_MAP

    deps = [dep for m in _modules if (dep := MODULE_DEPENDENCY_MAP.get(m)) is not None]
    [print(dep) for dep in deps]
