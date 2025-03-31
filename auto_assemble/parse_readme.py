import logging
import os
import re
from typing import Dict

import yaml

from auto_assemble.parse_permissions import parse_and_merge_permissions


def parse_yaml_block(content: str) -> Dict[str, Dict[str, str]]:
    """
    从内容中解析 YAML 代码块
    Args:
        content: 文件内容
    Returns:
        Dict[str, Dict[str, str]]: 解析后的 YAML 配置信息
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
        config = yaml.safe_load(yaml_content)

        # 重新组织配置结构
        result = {}
        for key, value in config.items():
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


def parse_readme(readme_path: str) -> Dict[str, str]:
    """
    从 README.md 文件中解析版本信息
    Args:
        readme_path: README.md 文件路径
    Returns:
        Dict[str, str]: 包含版本信息的字典，包括以下键：
            - hbx_version: HBuilderX 版本
            - version_name: 版本名称
            - version_code: 版本号
            - uniapp_id: Uniapp App ID
            - uniapp_key: Uniapp App key
            - third_party_config: 第三方配置信息
            - permissions: permissions 和 features 的合并结果
            - abi_filters: abiFilters 配置
            - schemes: 注册schema在其它App中打开当前App，多个scheme使用','号分割，例如：test1,test2
        如果解析失败则对应值为空字符串
    """
    try:
        if not os.path.exists(readme_path):
            logging.warning(f"README.md 文件不存在: {readme_path}")
            return {
                "version_name": "",
                "version_code": "",
                "uniapp_id": "",
                "uniapp_key": "",
                "third_party_config": {},
                "permissions": {},
            }

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
        third_party_config = parse_yaml_block(content)

        # 解析权限
        permissions = parse_and_merge_permissions(content)

        # todo: 解析模块使用，未来自动根据使用的模块配置依赖

        result = {
            "hbx_version": hbx_version_match.group(1) if hbx_version_match else "",
            "version_name": version_name_match.group(1) if version_name_match else "",
            "version_code": version_code_match.group(1) if version_code_match else "",
            "uniapp_id": uniapp_id_match.group(1) if uniapp_id_match else "",
            "uniapp_key": uniapp_key_match.group(1) if uniapp_key_match else "",
            "third_party_config": third_party_config,
            "permissions": permissions,
            "abi_filters": abi_filters_match.group(1) if abi_filters_match else "",
            "schemes": schemes_match.group(1) if schemes_match else "",
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
                f"schemes: {result['schemes']}"
            )
        else:
            logging.warning(f"未能完整解析README.md信息，解析结果：{result}")

        return result
    except Exception as e:
        logging.error(f"解析 README.md 文件时发生错误: {e}")
        return {
            "version_name": "",
            "version_code": "",
            "uniapp_id": "",
            "uniapp_key": "",
            "third_party_config": {},
            "permissions": {},
        }


if __name__ == "__main__":
    result = parse_readme(os.path.join(r"./", "list.md"))
    print(result)
