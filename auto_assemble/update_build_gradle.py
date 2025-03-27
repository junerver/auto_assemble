import logging

from auto_assemble.config import config


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
            - third_party_config: 新的third_party_config值
    Returns:
        bool: 更新是否成功
    """
    try:
        # 从字典中读取版本信息
        hbx_version = version_info.get("hbx_version", "")
        version_name = version_info.get("version_name", "")
        version_code = version_info.get("version_code", "")
        uniapp_id = version_info.get("uniapp_id", "")
        uniapp_key = version_info.get("uniapp_key", "")
        third_party_config = version_info.get("third_party_config", {})

        # 如果设置了hbx_version，需要修改version.toml文件中的hbx_version
        if hbx_version:
            with open(config.VERSIONS_TOML_PATH, "r", encoding="utf-8") as file:
                lines = file.readlines()

            # 查找并替换uniSdkVersion
            for i, line in enumerate(lines):
                if line.strip().startswith("uniSdkVersion = "):
                    lines[i] = f'uniSdkVersion =  "{hbx_version}"\n'  # 修改对应行

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

        with open(build_gradle_path, "w", encoding="utf-8") as file:
            for line in lines:
                if line.strip().startswith("def reqDate ="):
                    # 保持原有缩进，只替换引号内的内容
                    indent = line[: line.index("def")]
                    quote_char = '"' if '"' in line else "'"
                    before_value = line[: line.index(quote_char) + 1]
                    after_value = line[line.rindex(quote_char):]
                    file.write(f"{before_value}{artifact_name}{after_value}")
                elif version_name and line.strip().startswith("versionName"):
                    # 解析到了versionName，更新 versionName
                    indent = line[: line.index("versionName")]
                    quote_char = '"' if '"' in line else "'"
                    before_value = line[: line.index(quote_char) + 1]
                    after_value = line[line.rindex(quote_char):]
                    file.write(f"{indent}versionName {quote_char}{version_name}{quote_char}\n")
                elif version_code and line.strip().startswith("versionCode"):
                    # 解析到了versionCode，更新 versionCode
                    indent = line[: line.index("versionCode")]
                    file.write(f"{indent}versionCode {version_code}\n")
                elif uniapp_id and line.strip().startswith('"DCLOUD_APPID"'):
                    # 解析到了uniapp_id，修改 manifestPlaceholders 中 DCLOUD_APPID 的值
                    indent = line[: line.index('"DCLOUD_APPID"')]
                    file.write(f'{indent}"DCLOUD_APPID"          : "{uniapp_id}",\n')
                elif uniapp_key and line.strip().startswith('"DCLOUD_APPKEY"'):
                    # 解析到了uniapp_key，修改 manifestPlaceholders 中 DCLOUD_APPKEY 的值
                    indent = line[: line.index('"DCLOUD_APPKEY"')]
                    file.write(f'{indent}"DCLOUD_APPKEY"         : "{uniapp_key}",\n')
                elif (
                        third_party_config
                        and third_party_config.get("wechat")
                        and third_party_config["wechat"].get("appid")
                        and line.strip().startswith('"WX_APPID"')
                ):
                    # 解析到了wechat的appid，修改 manifestPlaceholders 中 WECHAT_APPID 的值
                    indent = line[: line.index('"WX_APPID"')]
                    file.write(
                        f'{indent}"WX_APPID"              : "{third_party_config["wechat"]["appid"]}",\n'
                    )
                elif (
                        third_party_config
                        and third_party_config.get("wechat")
                        and third_party_config["wechat"].get("secret")
                        and line.strip().startswith('"WX_SECRET"')
                ):
                    # 解析到了wechat的secret，修改 manifestPlaceholders 中 WX_SECRET 的值
                    indent = line[: line.index('"WX_SECRET"')]
                    file.write(
                        f'{indent}"WX_SECRET"             : "{third_party_config["wechat"]["secret"]}",\n'
                    )
                elif (
                        third_party_config
                        and third_party_config.get("amap")
                        and third_party_config["amap"].get("appkey")
                        and line.strip().startswith('"AMAP_APIKEY"')
                ):
                    # 解析到了amap的appkey，修改 manifestPlaceholders 中 AMAP_APIKEY 的值
                    indent = line[: line.index('"AMAP_APIKEY"')]
                    file.write(
                        f'{indent}"AMAP_APIKEY"           : "{third_party_config["amap"]["appkey"]}",\n'
                    )
                elif (
                        third_party_config
                        and third_party_config.get("baidu")
                        and third_party_config["baidu"].get("appkey")
                        and line.strip().startswith('"BAIDU_MAP_APIKEY"')
                ):
                    # 解析到了baidu的appkey，修改 manifestPlaceholders 中 BAIDU_MAP_APIKEY 的值
                    indent = line[: line.index('"BAIDU_MAP_APIKEY"')]
                    file.write(
                        f'{indent}"BAIDU_MAP_APIKEY"       : "{third_party_config["baidu"]["appkey"]}",\n'
                    )
                else:
                    file.write(line)

        logging.info(f"成功更新build.gradle文件，reqDate从 {old_artifact_name} 更新为 {artifact_name}")
        if hbx_version:
            logging.info(f"更新 hbx_version 为: {hbx_version}")
        if version_name:
            logging.info(f"更新 versionName 为: {version_name}")
        if version_code:
            logging.info(f"更新 versionCode 为: {version_code}")
        if uniapp_id:
            logging.info(f"更新 uniapp_id 为: {uniapp_id}")
        if uniapp_key:
            logging.info(f"更新 uniapp_key 为: {uniapp_key}")
        if third_party_config:
            logging.info(f"更新 third_party_config 为: {third_party_config}")
        return True
    except Exception as e:
        logging.error(f"更新build.gradle文件时发生错误: {e}")
        return False
