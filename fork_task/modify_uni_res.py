import logging
import os
import re
import shutil
import zipfile


def modify_uni_res(temp_dir: str, fork_task_info: dict) -> None:
    """
    修改 uni-app 项目中的 uni-res 资源
    Args:
        temp_dir: 临时目录，其中包含了解压后的资源目录 extract，与 readme.md 文件
        fork_task_info: 派生任务详情
    """
    # 确保使用正确的路径分隔符
    temp_dir = os.path.normpath(temp_dir)
    extract_dir = os.path.join(temp_dir, "extract")
    # 向下前进两层，第一层是可变的<uni_id>目录，第二层是www目录，找到其下的 manifest.json
    contents = os.listdir(extract_dir)
    uni_id_dir = contents[0]
    logging.info(f"uni_id_dir: {uni_id_dir}")
    manifest_path = os.path.join(extract_dir, uni_id_dir, "www", "manifest.json")
    logging.info(f"manifest_path: {manifest_path}")

    target_version_name = fork_task_info["target_version_name"]
    target_version_code = fork_task_info["target_version_code"]
    # 读取 manifest.json 文件, 修改 manifest.json 文件，正则替换 "version":{"name":"1.0.0","code":"100"} ，将其替换为
    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest_content = f.read()
    # 正则表达式："version":{"name":"1.0.0","code":"100"}
    pattern = r'"version":{"name":"(.*?)","code":"(.*?)"}'
    # 替换为
    manifest_content = re.sub(
        pattern,
        f'"version":{{"name":"{target_version_name}","code":"{target_version_code}"}}',
        manifest_content,
    )
    # 写入 manifest.json 文件
    with open(manifest_path, "w", encoding="utf-8") as f:
        f.write(manifest_content)
    logging.info(f"修改 manifest.json 文件成功: {manifest_path}")
    # 重新打包
    zip_file_path = os.path.join(temp_dir, f"{os.path.basename(temp_dir)}.zip")
    # 压缩目标是提取目录下的对应uni_id目录
    target_dir = os.path.join(extract_dir, uni_id_dir)
    with zipfile.ZipFile(zip_file_path, "w", zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(target_dir):
            for file in files:
                file_path = os.path.join(root, file)
                arcname = os.path.join(uni_id_dir, os.path.relpath(file_path, target_dir))
                zipf.write(file_path, arcname)
    logging.info(f"重新打包成功: {zip_file_path}")
    # 删除解压目录
    if os.path.exists(extract_dir):
        shutil.rmtree(extract_dir)
        logging.info(f"删除解压目录: {extract_dir}")

    # 修改 readme.md 文件
    readme_path = os.path.join(temp_dir, "README.md")
    # 读取 readme.md 文件, 修改 readme.md 文件，正则替换 versionName\versionCode
    with open(readme_path, "r", encoding="utf-8") as f:
        readme_content = f.read()
    # 正则表达式：versionName：`([^`]+)`
    pattern = r"versionName：`([^`]+)`"
    # 替换为
    readme_content = re.sub(
        pattern,
        f"versionName：`{target_version_name}`",
        readme_content,
    )
    # 正则表达式：versionCode：`([^`]+)`
    pattern = r"versionCode：`([^`]+)`"
    # 替换为
    readme_content = re.sub(
        pattern,
        f"versionCode：`{target_version_code}`",
        readme_content,
    )
    # 写入 readme.md 文件
    with open(readme_path, "w", encoding="utf-8") as f:
        f.write(readme_content)
    logging.info(f"修改 readme.md 文件成功: {readme_path}")
