import json
import logging
import os
from typing import Dict

import json5

from auto_assemble.parse_manifest import parse_and_merge_permissions

# 默认权限列表
DEFAULT_PERMISSIONS = """```xml
<uses-permission android:name="android.permission.INTERNET" />
<uses-permission android:name="android.permission.READ_EXTERNAL_STORAGE" />
<uses-permission android:name="android.permission.WRITE_EXTERNAL_STORAGE" />
<uses-permission android:name="android.permission.READ_PHONE_STATE" />
<uses-permission android:name="android.permission.ACCESS_NETWORK_STATE" />
<uses-permission android:name="android.permission.ACCESS_WIFI_STATE" />
<uses-permission android:name="com.asus.msa.SupplementaryDID.ACCESS" />
<uses-permission android:name="com.huawei.android.launcher.permission.CHANGE_BADGE" />
<uses-permission android:name="android.permission.INSTALL_PACKAGES" />
<uses-permission android:name="android.permission.REQUEST_INSTALL_PACKAGES" />
```"""


def parse_uni_manifest(manifest_path: str) -> Dict[str, str]:
    """
    解析uniapp的manifest.json文件
    Args:
        manifest_path: manifest.json文件路径
    Returns:
        Dict[str, str]: 包含版本信息的字典，包括以下键：
            - hbx_version: HBuilderX 版本
            - version_name: 版本名称
            - version_code: 版本号
            - uniapp_id: Uniapp App ID
            - uniapp_key: Uniapp App key
            - third_party_config: 第三方配置信息
            - permissions: permissions 和 features 的合并结果
        如果解析失败则对应值为空字符串
    """
    logging.info(f"解析manifest.json文件: {manifest_path}")
    try:
        with open(manifest_path, "r", encoding="utf-8") as f:
            manifest_data = json5.load(f)

        # 提取基本信息
        version_name = manifest_data.get("versionName", "")
        version_code = manifest_data.get("versionCode", "")
        uniapp_id = manifest_data.get("appid", "")

        # 提取第三方配置
        third_party_config = {}
        if "app-plus" in manifest_data:
            app_plus = manifest_data["app-plus"]
            if "distribute" in app_plus:
                distribute = app_plus["distribute"]
                if "sdkConfigs" in distribute:
                    sdk_configs = distribute["sdkConfigs"]
                    # 提取微信配置
                    if "oauth" in sdk_configs and "weixin" in sdk_configs["oauth"]:
                        third_party_config["wechat"] = {
                            "appid": sdk_configs["oauth"]["weixin"].get("appid", "")
                        }
                    # 提取高德地图配置
                    if "maps" in sdk_configs and "amap" in sdk_configs["maps"]:
                        third_party_config["amap"] = {
                            "appkey": sdk_configs["maps"]["amap"].get("appkey_android", "")
                        }

        # 构建权限处理的内容
        permissions_content = DEFAULT_PERMISSIONS + "\n\n"

        # 添加manifest.json中的额外权限
        if "app-plus" in manifest_data:
            app_plus = manifest_data["app-plus"]
            if "distribute" in app_plus:
                distribute = app_plus["distribute"]
                if "android" in distribute:
                    android_config = distribute["android"]
                    # 添加额外权限
                    if "permissions" in android_config:
                        permissions_content += "需要额外添加：\n\n```xml\n"
                        for perm in android_config["permissions"]:
                            permissions_content += f"{perm}\n"
                        permissions_content += "```\n\n"

                    # 添加排除权限
                    if "excludePermissions" in android_config:
                        permissions_content += "需要移除：\n\n```xml\n"
                        for perm in android_config["excludePermissions"]:
                            permissions_content += f"{perm}\n"
                        permissions_content += "```\n"

        # 使用parse_and_merge_permissions处理权限
        permissions = parse_and_merge_permissions(permissions_content)

        result = {
            "hbx_version": os.getenv(
                "HBX_VERSION"
            ),  # manifest.json中不包含HBuilderX版本信息, 使用环境变量HBX_VERSION
            "version_name": version_name,
            "version_code": version_code,
            "uniapp_id": uniapp_id,
            "uniapp_key": os.getenv(
                "UNIAPP_APPKEY"
            ),  # manifest.json中不包含uniapp_key信息, 使用环境变量UNIAPP_APPKEY
            "third_party_config": third_party_config,
            "permissions": permissions,
        }

        if all(result.values()):
            logging.info(
                f"成功解析manifest.json信息 - versionName: {result['version_name']}, "
                f"versionCode: {result['version_code']}, "
                f"uniapp_id: {result['uniapp_id']}"
            )
        else:
            logging.warning(f"未能完整解析manifest.json信息，解析结果：{result}")

        return result
    except Exception as e:
        logging.error(f"解析manifest.json文件时发生错误: {e}")
        return {
            "hbx_version": "",
            "version_name": "",
            "version_code": "",
            "uniapp_id": "",
            "uniapp_key": "",
            "third_party_config": {},
            "permissions": {},
        }


if __name__ == "__main__":
    # 配置日志
    logging.basicConfig(level=logging.INFO)

    # 测试文件路径
    manifest_paths = [
        "mainfest.json5",  # JSON5格式
    ]

    for manifest_path in manifest_paths:
        try:
            print(f"\n测试解析文件: {manifest_path}")
            # 解析manifest文件
            result = parse_uni_manifest(manifest_path)

            # 打印结果
            print("\n解析结果:")
            print(f"版本名称: {result['version_name']}")
            print(f"版本号: {result['version_code']}")
            print(f"AppID: {result['uniapp_id']}")
            print("\n第三方配置:")
            print(json.dumps(result["third_party_config"], ensure_ascii=False, indent=2))
            print("\n权限信息:")
            print(f"权限数量: {len(result['permissions']['permissions'])}")
            print(f"特性数量: {len(result['permissions']['features'])}")
            print("\n权限列表:")
            for perm_name in result["permissions"]["permissions"]:
                print(f"- {perm_name}")
        except FileNotFoundError:
            print(f"文件不存在: {manifest_path}")
        except Exception as e:
            print(f"解析出错: {e}")
