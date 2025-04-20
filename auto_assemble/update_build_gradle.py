import logging
from typing import Any

from auto_assemble.config import config

# 模块依赖映射字典
MODULE_DEPENDENCY_MAP = {
    "Share : weixin": "implementation(libs.bundles.uni.share.wechat)",
    "Maps : amap": "implementation(libs.bundles.uni.map.amap.maponly)",
    "Maps : amap & Geolocation : amap": "implementation(libs.bundles.uni.amap.map.location)",
    "Maps : baidu": "implementation(libs.bundles.uni.map.baidu)",
    "Payment : weixin": "implementation(libs.bundles.uni.payment.wechat)",
    "Payment : alipay": "implementation(libs.bundles.uni.payment.alipay)",
    "Geolocation : system": None,
    "Geolocation : amap": "implementation(libs.bundles.uni.location.amap.locationonly)",
    "Geolocation : baidu": "implementation(libs.bundles.uni.location.baidu)",
    "LivePusher": "implementation(libs.bundles.uni.livepusher)",
    "Camera": None,
    "VideoPlayer": "implementation(libs.bundles.uni.videoplayer)",
    "OAuth : weixin": "implementation(libs.bundles.uni.oauth.wechat)",
    "Webview-x5": "implementation(libs.bundles.uni.x5)",
}
THIRD_PARTY_BEGIN = "//--------------third party dependencies begin--------------"
THIRD_PARTY_END = "//---------------third party dependencies end---------------"


def _process_line(
        line: str,
        artifact_name: str,
        version_info: dict[str, Any],
) -> str:
    """
    处理单行内容，根据不同的行类型返回处理后的内容
    
    Args:
        line: 当前处理的行
        artifact_name: 最终产物名称
        version_info: 包含版本信息的字典
        
    Returns:
        str: 处理后的行内容
    """
    # 从字典中读取版本信息
    hbx_version = version_info.get("hbx_version", "")
    version_name = version_info.get("version_name", "")
    version_code = version_info.get("version_code", "")
    uniapp_id = version_info.get("uniapp_id", "")
    uniapp_key = version_info.get("uniapp_key", "")
    third_party_config = version_info.get("third_party_config", {})
    abi_filters = version_info.get("abi_filters", '"armeabi-v7a", "arm64-v8a"')

    stripped_line = line.strip()

    match stripped_line.split()[0] if stripped_line else "":
        case "def" if "reqDate" in stripped_line:
            # 处理 reqDate
            indent = line[: line.index("def")]
            quote_char = '"' if '"' in line else "'"
            before_value = line[: line.index(quote_char) + 1]
            after_value = line[line.rindex(quote_char):]
            if config.build_mode == "dev":
                artifact_name = artifact_name + "_debug"
            return f"{before_value}{artifact_name}{after_value}"

        case "abiFilters" if abi_filters:
            # 处理 abiFilters
            indent = line[: line.index("abiFilters")]
            return f"{indent}abiFilters {abi_filters}\n"

        case "versionName" if version_name:
            # 处理 versionName
            indent = line[: line.index("versionName")]
            quote_char = '"' if '"' in line else "'"
            before_value = line[: line.index(quote_char) + 1]
            after_value = line[line.rindex(quote_char):]
            return f"{indent}versionName {quote_char}{version_name}{quote_char}\n"

        case "versionCode" if version_code:
            # 处理 versionCode
            indent = line[: line.index("versionCode")]
            return f"{indent}versionCode {version_code}\n"

        case '"DCLOUD_APPID"' if uniapp_id:
            # 处理 DCLOUD_APPID
            indent = line[: line.index('"DCLOUD_APPID"')]
            return f'{indent}"DCLOUD_APPID"          : "{uniapp_id}",\n'

        case '"DCLOUD_APPKEY"' if uniapp_key:
            # 处理 DCLOUD_APPKEY
            indent = line[: line.index('"DCLOUD_APPKEY"')]
            return f'{indent}"DCLOUD_APPKEY"         : "{uniapp_key}",\n'

        case '"WX_APPID"' if (third_party_config.get("wechat", {}).get("appid")):
            # 处理 WX_APPID
            indent = line[: line.index('"WX_APPID"')]
            return f'{indent}"WX_APPID"              : "{third_party_config["wechat"]["appid"]}",\n'

        case '"WX_SECRET"' if (third_party_config.get("wechat", {}).get("secret")):
            # 处理 WX_SECRET
            indent = line[: line.index('"WX_SECRET"')]
            return f'{indent}"WX_SECRET"             : "{third_party_config["wechat"]["secret"]}",\n'

        case '"AMAP_APIKEY"' if (third_party_config.get("amap", {}).get("appkey")):
            # 处理 AMAP_APIKEY
            indent = line[: line.index('"AMAP_APIKEY"')]
            return f'{indent}"AMAP_APIKEY"           : "{third_party_config["amap"]["appkey"]}",\n'

        case '"BAIDU_MAP_APIKEY"' if (third_party_config.get("baidu", {}).get("appkey")):
            # 处理 BAIDU_MAP_APIKEY
            indent = line[: line.index('"BAIDU_MAP_APIKEY"')]
            return f'{indent}"BAIDU_MAP_APIKEY"       : "{third_party_config["baidu"]["appkey"]}",\n'

        case _:
            return line


def update_build_gradle(
        build_gradle_path: str,
        artifact_name: str,
        version_info: dict,
) -> bool:
    """
    更新build.gradle文件中的reqDate变量和版本信息，
    如果version_info中包含hbx_version，则更新hbx_version，
    如果version_info中包含version_name，则更新versionName，
    如果version_info中包含version_code，则更新versionCode，
    如果version_info中包含uniapp_id，则更新uniapp_id，
    如果version_info中包含uniapp_key，则更新uniapp_key，
    如果version_info中包含third_party_config，则更新third_party_config。

    Args:
        build_gradle_path: build.gradle文件路径
        artifact_name: 最终产物名称
        version_info: 包含版本信息的字典，可能包含以下键：
            - version_name: 新的versionName值
            - version_code: 新的versionCode值
            - uniapp_id: 新的uniapp_id值
            - uniapp_key: 新的uniapp_key值
            - hbx_version: 新的hbx_version值
            - abi_filters: 新的abi_filters值
            - third_party_config: 新的third_party_config值
    Returns:
        bool: 更新是否成功
    """
    try:
        # 如果设置了hbx_version，需要修改version.toml文件中的hbx_version
        hbx_version = version_info.get("hbx_version", "")
        modules = version_info.get("modules", [])
        if hbx_version:
            with open(config.VERSIONS_TOML_PATH, "r", encoding="utf-8") as file:
                lines = file.readlines()

            # 查找并替换uniSdkVersion
            for i, line in enumerate(lines):
                if line.strip().startswith("uniSdkVersion = "):
                    lines[i] = f'uniSdkVersion = "{hbx_version}"\n'  # 修改对应行

            # 将修改后的内容重新写回文件
            with open(config.VERSIONS_TOML_PATH, "w", encoding="utf-8") as file:
                file.writelines(lines)  # 写入所有行
            logging.info(f"更新version.toml文件中的uniSdkVersion为: {hbx_version}")

        # 打开build.gradle文件，根据解析到的版本信息，更新build.gradle文件中的reqDate变量和版本信息
        with open(build_gradle_path, "r", encoding="utf-8") as file:
            lines = file.readlines()
        # 查找并记录旧的reqDate值
        old_artifact_name = None
        for line in lines:
            if line.strip().startswith("def reqDate ="):
                quote_char = '"' if '"' in line else "'"
                old_artifact_name = line[line.index(quote_char) + 1: line.rindex(quote_char)]
                logging.info(f"当前reqDate值: {old_artifact_name}")
                break
        # 处理每一行并写入新文件
        with open(build_gradle_path, "w", encoding="utf-8") as file:
            for line in lines:
                processed_line = _process_line(
                    line,
                    artifact_name,
                    version_info,
                )
                file.write(processed_line)

        # todo: 映射勾选模块到实际依赖项目
        if "Maps : amap" in modules and "Geolocation : amap" in modules:
            # 同时存在高德地图与高德定位
            modules.remove("Maps : amap")
            modules.remove("Geolocation : amap")
            modules.append("Maps : amap & Geolocation : amap")
        # 最终模块映射的依赖，如果MODULE_DEPENDENCY_MAP中找不到对应的key，则抛出异常
        deps = []
        for m in modules:
            if m not in MODULE_DEPENDENCY_MAP:
                raise KeyError(f"Module '{m}' not found in MODULE_DEPENDENCY_MAP")
            dep = MODULE_DEPENDENCY_MAP[m]
            if dep is not None:
                deps.append(dep)

        # 记录更新日志
        logging.info(
            f"成功更新build.gradle文件，reqDate从 {old_artifact_name} 更新为 {artifact_name}"
        )
        if hbx_version:
            logging.info(f"更新 hbx_version 为: {hbx_version}")
        if version_info.get("version_name"):
            logging.info(f"更新 versionName 为: {version_info['version_name']}")
        if version_info.get("version_code"):
            logging.info(f"更新 versionCode 为: {version_info['version_code']}")
        if version_info.get("uniapp_id"):
            logging.info(f"更新 uniapp_id 为: {version_info['uniapp_id']}")
        if version_info.get("uniapp_key"):
            logging.info(f"更新 uniapp_key 为: {version_info['uniapp_key']}")
        if version_info.get("third_party_config"):
            logging.info(f"更新 third_party_config 为: {version_info['third_party_config']}")
        if version_info.get("abi_filters"):
            logging.info(f"更新 abi_filters 为: {version_info['abi_filters']}")

        # 处理第三方依赖
        if deps:
            with open(build_gradle_path, "r", encoding="utf-8") as file:
                content = file.read()

            # 使用正则表达式匹配第三方依赖区域
            import re
            pattern = re.compile(
                f"{re.escape(THIRD_PARTY_BEGIN)}.*?{re.escape(THIRD_PARTY_END)}",
                re.DOTALL
            )

            # 构建新的依赖内容
            new_deps_content = f"{THIRD_PARTY_BEGIN}\n"
            for dep in deps:
                new_deps_content += f"    {dep}\n"
            new_deps_content += f"    {THIRD_PARTY_END}"

            # 替换内容
            new_content = pattern.sub(new_deps_content, content)

            # 写回文件
            with open(build_gradle_path, "w", encoding="utf-8") as file:
                file.write(new_content)

            logging.info(f"更新第三方依赖: {deps}")

        return True
    except Exception as e:
        logging.error(f"更新build.gradle文件时发生错误: {e}")
        if isinstance(e, KeyError):
            logging.error(f"模块 '{e.args[0]}' 未找到在MODULE_DEPENDENCY_MAP中")
            raise e
        return False
