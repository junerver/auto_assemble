import logging
from pathlib import Path
from textwrap import dedent

from common.types import ManifestInfo


def create_readme_file(req_dir: Path, manifest_info: ManifestInfo):
    """
    创建readme.txt文件
    Args:
        req_dir: 请求目录路径
        manifest_info: manifest.json解析信息
    """
    readme_file_path = req_dir / "README.md"
    with open(readme_file_path, "w", encoding="utf-8") as f:
        # 写入标题和基本要求
        f.write(
            dedent(
                """\
            # 打包要求

            1. 打包使用的 HBuilderX 版本号，必须使用 4.45 以上

               HBuilderX 版本：`{hbx_version}`

            2. Uniapp 打包后的资源包

            3. Uniapp App ID：`{uniapp_id}`

            4. Uniapp App key：`{uniapp_key}`

            5. AbiFilters：`{abi_filters}`

            6. UrlSchemes：`{schemes}`

            7. manifest.json 中配置的版本名称 versionName、版本号 versionCode

               版本名称 versionName：`{version_name}`

               版本号 versionCode：`{version_code}`

            8. 提供 Android 基座需要添加、移除的权限列表，基座默认权限如下：

            {permissions_content}
        """
            ).format(
                hbx_version=manifest_info["hbx_version"],
                uniapp_id=manifest_info["uniapp_id"],
                uniapp_key=manifest_info["uniapp_key"],
                abi_filters=manifest_info["abi_filters"],
                schemes=manifest_info["schemes"],
                version_name=manifest_info["version_name"],
                version_code=manifest_info["version_code"],
                permissions_content=manifest_info["permissions_content"],
            )
        )
        # 写入模块信息
        if manifest_info["modules"]:
            f.write("9. 模块信息：\n\n")
            for module in manifest_info["modules"]:
                f.write(f"    > - {module}\n")

        # 写入第三方配置
        if manifest_info["third_party_config"]:
            third_party_config_text = ""
            for platform, config in manifest_info["third_party_config"].items():
                third_party_config_text += f"               {platform}:\n"
                for key, value in config.items():
                    third_party_config_text += f"                 {key}: {value}\n"

            f.write(
                dedent(
                    f"""
               10. 第三方平台配置信息：

               ```yaml
{third_party_config_text}               ```
            """
                )
            )

        logging.info(f"已创建README.md文件：{readme_file_path}")
