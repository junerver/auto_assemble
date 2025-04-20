import json
import logging

import json5

from auto_assemble.parse_permissions import parse_and_merge_permissions
from auto_assemble.parse_third_party_configs import parse_third_party_configs
from cbr.env_vars import CbrEnvVars

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

modules_map = {
    "Geolocation": "Geolocation（定位）",
    "Push": "Push（消息推送）",
    "Share": "Share（分享）",
    "OAuth": "OAuth（登录鉴权）",
    "Maps": "Maps（地图）",
    "Payment": "Payment（支付）",
    "Speech": "Speech（语音输入）",
    "Statistic": "Statistic（统计）",
    "Webview-x5": "Android X5 Webview（腾讯 TBS）",
    "VideoPlayer": "VideoPlayer（视频播放）",
    "LivePusher": "LivePusher（直播推流）",
    "Barcode": "Barcode（扫码）",
    "Bluetooth": "Bluetooth（低功耗蓝牙）",
    "Camera": "Camera（相机/相册）",
    "Contacts": "Contacts（通讯录）",
    "Fingerprint": "Fingerprint（指纹识别）",
    "Messaging": "Messaging（短彩邮件消息）",
    "Recorder": "Record（录音）",
    "SQLite": "SQLite（数据库）",
}


def parse_uni_manifest(
        manifest_path: str,
        env_vars: CbrEnvVars | None = None,
        third_party_configs: list[dict[str, str]] | None = None,
) -> dict[str, str]:
    """
    解析uniapp的manifest.json文件
    Args:
        manifest_path: manifest.json文件路径
        env_vars:
        third_party_configs:
    Returns:
        dict[str, str]: 包含版本信息的字典，包括以下键：
            - hbx_version: HBuilderX 版本
            - version_name: 版本名称
            - version_code: 版本号
            - uniapp_id: Uniapp App ID
            - uniapp_key: Uniapp App key
            - third_party_config: 第三方配置信息
            - permissions: permissions 和 features 的合并结果
            - permissions_content: 完整的权限文本内容
            - modules: 模块信息数组, [模块名称-子模块]
            - abi_filters: abiFilters 配置, 取出的字符串数组需要补充 " " 包裹，例如："armeabi-v7a", "arm64-v8a"
            - schemes: 注册schema在其它App中打开当前App，多个scheme使用','号分割，例如：test1,test2
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
        third_party_config = parse_third_party_configs(third_party_configs)

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

                    # 添加abi_filters
                    if "abiFilters" in android_config:
                        # 取出的字符串数组需要补充 " " 包裹
                        abi_filters = ", ".join(f'"{abi}"' for abi in android_config["abiFilters"])

                    # 添加schemes
                    if "schemes" in android_config:
                        schemes = android_config["schemes"]

        # 使用parse_and_merge_permissions处理权限
        permissions = parse_and_merge_permissions(permissions_content)

        # 解析模块信息
        modules = []
        if "app-plus" in manifest_data:
            app_plus = manifest_data["app-plus"]
            # 获取基础模块列表
            if "modules" in app_plus:
                base_modules = app_plus["modules"]
                # 获取SDK配置中的子模块信息
                if "distribute" in app_plus and "sdkConfigs" in app_plus["distribute"]:
                    sdk_configs = app_plus["distribute"]["sdkConfigs"]
                    # 遍历基础模块
                    for module_name in base_modules:
                        # 检查是否有对应的SDK配置
                        if module_name.lower() in sdk_configs:
                            sdk_module = sdk_configs[module_name.lower()]
                            # 遍历SDK模块的子模块
                            for sub_module in sdk_module:
                                if sub_module != "__platform__":
                                    modules.append(f"{module_name} : {sub_module}")
                        else:
                            # 如果没有子模块，直接添加基础模块
                            modules.append(module_name)
        hbx_version = env_vars.HBX_VERSION if env_vars else ""
        uniapp_key = env_vars.UNIAPP_APPKEY if env_vars else ""
        result = {
            "hbx_version": hbx_version,  # manifest.json中不包含HBuilderX版本信息, 使用环境变量HBX_VERSION
            "version_name": version_name,
            "version_code": version_code,
            "uniapp_id": uniapp_id,
            "uniapp_key": uniapp_key,  # manifest.json中不包含uniapp_key信息, 使用环境变量UNIAPP_APPKEY
            "third_party_config": third_party_config,
            "permissions": permissions,
            "permissions_content": permissions_content,  # 添加完整的权限文本内容
            "modules": modules,  # 添加模块信息
            "abi_filters": abi_filters,
            "schemes": schemes,
        }

        if not all(result.values()):
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
            "permissions_content": "",  # 添加空的权限文本内容
            "modules": [],  # 添加空的模块列表
            "abi_filters": "",
            "schemes": "",
        }


if __name__ == "__main__":
    """
    本地测试代码
    """
    # 配置日志
    logging.basicConfig(level=logging.INFO)

    # 测试文件路径
    manifest_path = "manifest.json5"  # 项目根目录下的manifest.json5

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
        print("\n模块信息:")
        for module in result["modules"]:
            print(f"- {module}")
        print(f"\nABI过滤器: {result['abi_filters']}")
        print(f"Schemes: {result['schemes']}")
    except FileNotFoundError:
        print(f"文件不存在: {manifest_path}")
    except Exception as e:
        print(f"解析出错: {e}")
