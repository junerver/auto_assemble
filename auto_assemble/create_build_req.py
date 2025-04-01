import argparse
import logging
import os
import shutil
import zipfile
from datetime import datetime
from textwrap import dedent

from auto_assemble.check_uni_project import check_uni_project
from auto_assemble.config import config
from auto_assemble.create_env_file import check_and_create_env
from auto_assemble.log import setup_logging


def create_readme_file(req_dir: str, manifest_info: dict):
    """
    创建readme.txt文件
    Args:
        req_dir: 请求目录路径
        manifest_info: manifest.json解析信息
    """
    readme_file_path = os.path.join(req_dir, "README.md")
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

               [申请 Appkey](https://nativesupport.dcloud.net.cn/AppDocs/usesdk/appkey.html)

            5. AbiFilters：`{abi_filters}`

               支持的 CPU 类型，多个CPU使用`,`隔开

            6. UrlSchemes：`{schemes}`

               设置 UrlSchemes，多个scheme使用`,`隔开（默认为空），例如`test,test1`，[参考文档](https://uniapp.dcloud.net.cn/tutorial/app-android-schemes.html)

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
                    f"""\
               10. 第三方平台配置信息：

                  ```yml
{third_party_config_text}                  ```
            """
                )
            )

        logging.info(f"已创建README.md文件：{readme_file_path}")


def create_build_req():
    """
    创建构建请求
    """
    parser = argparse.ArgumentParser(
        description="Load environment variables from a specified .env file and execute the program."
    )
    # 指定.env文件路径
    parser.add_argument("--env", type=str, help="Path to the .env file")

    args = parser.parse_args()
    env_file = args.env if args.env else os.path.join(os.getcwd(), ".env")
    setup_logging(True, "创建构建请求")
    check_and_create_env(env_file, "4")

    is_ready, manifest_info, resources_dir = check_uni_project()
    if not is_ready:
        logging.error("本地资源文件校验失败")
        return 1
    # 更新UNI_APP_ID
    config.UNI_APP_ID = manifest_info["uniapp_id"]
    # 创建时间
    req_date = datetime.now().strftime("%Y%m%d%H%M")
    # 压缩资源目录下的名称为config.UNI_APP_ID的目录，并重命名为req_date.zip
    zip_file_path = os.path.join(resources_dir, f"{req_date}.zip")
    # 压缩资源目录下的名称为config.UNI_APP_ID的目录
    target_dir = os.path.join(resources_dir, config.UNI_APP_ID)
    if not os.path.exists(target_dir):
        logging.error(f"目录 {target_dir} 不存在")
        return 1
    # 压缩资源目录下的名称为config.UNI_APP_ID的目录
    with zipfile.ZipFile(zip_file_path, "w", zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(target_dir):
            for file in files:
                file_path = os.path.join(root, file)
                arcname = os.path.join(config.UNI_APP_ID, os.path.relpath(file_path, target_dir))
                zipf.write(file_path, arcname)
    logging.info(f"已将 {target_dir} 目录压缩为 {zip_file_path}")

    # 在分发目录的PROD_DIR目录下创建req_date目录
    req_date_dir = os.path.join(config.DISTRIBUTION_PATH, config.PROD_DIR, req_date)
    os.makedirs(req_date_dir, exist_ok=True)
    # 复制zip文件到指定目录
    shutil.copy(zip_file_path, req_date_dir)
    os.remove(zip_file_path)
    logging.info(f"本次请求的资源文件已压缩为{zip_file_path}，并已复制到{req_date_dir}目录下")
    create_readme_file(req_date_dir, manifest_info)


if __name__ == "__main__":
    create_build_req()
