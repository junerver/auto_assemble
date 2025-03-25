import os
import shutil
import zipfile
import patoolib
import subprocess
import logging
import sys
from datetime import datetime
from typing import Optional, Tuple
from .config import config
from .parse_readme import parse_readme
import xml.etree.ElementTree as ET
import sys
import shutil
from xml.dom import minidom  # 用于格式化 XML
import re
from .log import setup_logging


def get_git_info(repo_path: str) -> Tuple[str, str, str]:
    """
    获取Git仓库信息
    Args:
        repo_path: Git仓库路径
    Returns:
        Tuple[str, str, str]: (最后提交时间, 最后提交人, 最后提交信息)
    """
    try:
        # 获取最后一次提交信息
        last_commit = subprocess.run(
            [
                "git",
                "log",
                "-1",
                "--format=%cd,%an,%s",
                "--date=format:%Y-%m-%d %H:%M:%S",
            ],
            capture_output=True,
            text=True,
            encoding="utf-8",  # 指定编码为utf-8
            cwd=repo_path,
        )
        if last_commit.returncode == 0:
            commit_date, author, message = last_commit.stdout.strip().split(",", 2)
            return commit_date, author, message
    except Exception as e:
        logging.error(f"获取Git信息失败: {e}")
    return "", "", ""


def check_dependencies():
    """
    检查必要的依赖是否已安装
    Raises:
        ImportError: 当缺少必要的依赖时抛出
    """
    try:
        import rarfile
        import zipfile
    except ImportError as e:
        logging.error(f"缺少必要的依赖: {e}")
        raise


def check_paths():
    """
    检查必要的路径是否存在
    Raises:
        FileNotFoundError: 当必要的路径不存在时抛出
    """
    paths_to_check = {
        "仓库路径": config.DISTRIBUTION_PATH,
        "应用目录": config.APPS_DIRECTORY,
        "Gradle文件": config.BUILD_GRADLE_PATH,
    }

    for name, path in paths_to_check.items():
        if not os.path.exists(path):
            error_msg = f"{name}不存在: {path}"
            logging.error(error_msg)
            raise FileNotFoundError(error_msg)


def sync_repository(repo_path: str) -> bool:
    """
    同步Git仓库到最新状态
    Args:
        repo_path: Git仓库路径
    Returns:
        bool: 同步是否成功
    """
    try:
        os.chdir(repo_path)

        # 获取更新前的提交信息
        before_date, before_author, before_message = get_git_info(repo_path)
        if before_date:
            logging.info(
                f"当前版本 - 提交时间: {before_date}, 提交人: {before_author}, 提交信息: {before_message}"
            )

        # 检查远程是否有更新
        fetch_result = subprocess.run(
            ["git", "fetch"], capture_output=True, text=True, encoding="utf-8"
        )
        if fetch_result.returncode != 0:
            logging.error(f"Git fetch失败: {fetch_result.stderr}")
            return False

        # 检查是否需要更新
        status = subprocess.run(
            ["git", "status", "-uno"], capture_output=True, text=True, encoding="utf-8"
        )
        if "Your branch is up to date" in status.stdout:
            logging.info("本地代码已是最新版本，无需更新")
            return True

        # 执行更新
        result = subprocess.run(["git", "pull"], capture_output=True, text=True, encoding="utf-8")
        if result.returncode == 0:
            # 获取更新后的提交信息
            after_date, after_author, after_message = get_git_info(repo_path)
            if after_date:
                logging.info(f"更新成功 - 新版本信息:")
                logging.info(f"提交时间: {after_date}")
                logging.info(f"提交人: {after_author}")
                logging.info(f"提交信息: {after_message}")
            return True
        else:
            logging.error(f"Git仓库同步失败: {result.stderr}")
            return False
    except subprocess.CalledProcessError as e:
        logging.error(f"Git命令执行失败: {e}")
        return False
    except Exception as e:
        logging.error(f"同步仓库时发生错误: {e}")
        return False


def find_latest_directory(base_path: str) -> str:
    """
    查找最新的目录（基于时间戳命名）
    Args:
        base_path: 基础路径
    Returns:
        最新目录的完整路径
    Raises:
        ValueError: 当没有找到符合条件的目录时抛出
    """
    try:
        directories = [
            d for d in os.listdir(base_path) if os.path.isdir(os.path.join(base_path, d))
        ]
        if not directories:
            raise ValueError(f"在 {base_path} 中没有找到目录")

        latest_dir = max(directories, key=lambda d: datetime.strptime(d, "%Y%m%d%H%M"))
        latest_path = os.path.join(base_path, latest_dir)
        logging.info(f"找到最新目录: {latest_path}")
        return latest_path
    except ValueError as e:
        logging.error(f"查找最新目录失败: {e}")
        raise


def find_compressed_file(directory: str) -> Optional[str]:
    """
    在指定目录中查找压缩文件（.zip或.rar）
    Args:
        directory: 要搜索的目录
    Returns:
        压缩文件的完整路径，如果未找到则返回None
    """
    try:
        for file in os.listdir(directory):
            if file.endswith((".zip", ".rar")):
                file_path = os.path.join(directory, file)
                logging.info(f"找到压缩文件: {file_path}")
                return file_path
        logging.warning(f"在 {directory} 中未找到压缩文件")
        return None
    except Exception as e:
        logging.error(f"查找压缩文件时发生错误: {e}")
        return None


def clear_directory(directory: str) -> bool:
    """
    清空指定目录中的所有文件和子目录
    Args:
        directory: 要清空的目录
    Returns:
        bool: 清空是否成功
    """
    try:
        for filename in os.listdir(directory):
            file_path = os.path.join(directory, filename)
            if os.path.isfile(file_path) or os.path.islink(file_path):
                os.unlink(file_path)
            elif os.path.isdir(file_path):
                shutil.rmtree(file_path)
        logging.info(f"成功清空目录: {directory}")
        return True
    except Exception as e:
        logging.error(f"清空目录时发生错误: {e}")
        return False


def check_compressed_file_content(compressed_file: str) -> Tuple[bool, str]:
    """
    检查压缩文件中的目录结构是否符合要求
    Args:
        compressed_file: 压缩文件路径
    Returns:
        Tuple[bool, str]: (是否符合要求, 临时目录路径)
    """
    # 创建临时目录用于检查压缩文件内容
    temp_dir = os.path.join(os.path.dirname(compressed_file), "temp_check")
    try:
        logging.info(f"开始检查压缩文件内容: {compressed_file}")
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)
        os.makedirs(temp_dir)
        logging.info(f"创建临时目录: {temp_dir}")

        # 解压文件到临时目录
        logging.info("开始解压文件到临时目录")
        patoolib.extract_archive(compressed_file, outdir=temp_dir)

        # 检查目录结构
        contents = os.listdir(temp_dir)
        logging.info(f"压缩文件内容: {contents}")
        if len(contents) != 1:
            logging.error(f"压缩文件中包含多个目录或文件: {contents}")
            # 检查失败，清理临时目录
            shutil.rmtree(temp_dir)
            return False, ""
        # 检查目录名称是否与UNI_APP_ID一致
        if contents[0] != config.UNI_APP_ID:
            logging.error(
                f"压缩文件中的目录名称与UNI_APP_ID不匹配: {contents[0]} != {config.UNI_APP_ID}"
            )
            # 检查失败，清理临时目录
            shutil.rmtree(temp_dir)
            return False, ""

        logging.info("压缩文件内容检查通过")
        # 检查通过，保留临时目录
        return True, temp_dir
    except Exception as e:
        logging.error(f"检查压缩文件内容时发生错误: {e}")
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)
        return False, ""


def extract_compressed_file(compressed_file: str, extract_to: str) -> bool:
    """
    解压文件到指定目录，如果临时解压目录已存在，则直接复制文件
    Args:
        compressed_file: 压缩文件路径
        extract_to: 解压目标目录
    Returns:
        bool: 解压是否成功
    """
    try:
        # 检查临时解压目录是否存在
        temp_dir = os.path.join(os.path.dirname(compressed_file), "temp_check")
        if os.path.exists(temp_dir) and os.listdir(temp_dir):
            logging.info(f"发现临时解压目录，直接复制文件: {temp_dir} -> {extract_to}")
            # 获取临时目录中的应用目录
            app_dir = os.path.join(temp_dir, config.UNI_APP_ID)
            if os.path.exists(app_dir):
                # 复制应用目录到目标目录
                target_dir = os.path.join(extract_to, config.UNI_APP_ID)
                if not os.path.exists(target_dir):
                    os.makedirs(target_dir)
                # 复制文件
                for item in os.listdir(app_dir):
                    s = os.path.join(app_dir, item)
                    d = os.path.join(target_dir, item)
                    if os.path.isdir(s):
                        shutil.copytree(s, d, dirs_exist_ok=True)
                    else:
                        shutil.copy2(s, d)
                logging.info(f"成功从临时目录复制文件到: {extract_to}")
                # 清理临时目录
                shutil.rmtree(temp_dir)
                return True
            else:
                logging.error(f"临时目录中未找到应用目录: {app_dir}")
                return False
        else:
            # 临时目录不存在，执行正常解压
            logging.info(f"临时解压目录不存在，执行正常解压: {compressed_file} -> {extract_to}")
            patoolib.extract_archive(compressed_file, outdir=extract_to)
            logging.info(f"成功解压文件到: {extract_to}")
            return True
    except Exception as e:
        logging.error(f"解压文件时发生错误: {e}")
        return False


def update_build_gradle(
    build_gradle_path: str,
    new_req_date: str,
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
        new_req_date: 新的reqDate值
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
        old_req_date = None
        for line in lines:
            if line.strip().startswith("def reqDate ="):
                quote_char = '"' if '"' in line else "'"
                old_req_date = line[line.index(quote_char) + 1 : line.rindex(quote_char)]
                logging.info(f"当前reqDate值: {old_req_date}")
                break

        with open(build_gradle_path, "w", encoding="utf-8") as file:
            for line in lines:
                if line.strip().startswith("def reqDate ="):
                    # 保持原有缩进，只替换引号内的内容
                    indent = line[: line.index("def")]
                    quote_char = '"' if '"' in line else "'"
                    before_value = line[: line.index(quote_char) + 1]
                    after_value = line[line.rindex(quote_char) :]
                    file.write(f"{before_value}{new_req_date}{after_value}")
                elif version_name and line.strip().startswith("versionName"):
                    # 解析到了versionName，更新 versionName
                    indent = line[: line.index("versionName")]
                    quote_char = '"' if '"' in line else "'"
                    before_value = line[: line.index(quote_char) + 1]
                    after_value = line[line.rindex(quote_char) :]
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

        logging.info(f"成功更新build.gradle文件，reqDate从 {old_req_date} 更新为 {new_req_date}")
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


def update_control_file(control_file_path: str, uniapp_id: str) -> bool:
    """
    更新 dcloud_control.xml 文件中的 uniapp_id，
    匹配 <app appid="..."> 并修改 appid 的值。

    :param control_file_path: dcloud_control.xml 文件的路径
    :param uniapp_id: 要替换的新的 appid
    :return: 更新成功返回 True，失败返回 False
    """
    try:
        with open(control_file_path, "r", encoding="utf-8") as file:
            content = file.read()

        # 正则匹配 <app appid="..."> 并替换 appid
        new_content, count = re.subn(r'(<app\s+appid=")[^"]+(")', rf"\1{uniapp_id}\2", content)

        # 如果没有匹配到内容，返回 False
        if count == 0:
            print("未找到匹配的 <app appid>，可能文件格式不正确")
            return False

        # 写回文件
        with open(control_file_path, "w", encoding="utf-8") as file:
            file.write(new_content)
        logging.info(f"成功更新 dcloud_control.xml 文件，替换 appid 为: {uniapp_id}")
        return True
    except Exception as e:
        print(f"更新 dcloud_control.xml 文件失败: {e}")
        return False


def prettify_xml(elem):
    """格式化 XML 并去除多余空行"""
    rough_string = ET.tostring(elem, encoding="utf-8")
    reparsed = minidom.parseString(rough_string)
    # 过滤掉多余的空行
    return "\n".join(
        [line for line in reparsed.toprettyxml(indent="  ").splitlines() if line.strip()]
    )


def update_android_manifest(android_manifest_path: str, permissions: dict) -> bool:
    """
    更新 AndroidManifest.xml 文件中的权限和特性（uses-permission 和 uses-feature）

    Args:
        android_manifest_path: AndroidManifest.xml 文件的路径
        permissions: 包含 "permissions" 和 "features" 的字典

    Returns:
        bool: 更新成功返回 True，失败返回 False
    """
    # 备份原始文件
    backup_path = os.path.join(os.path.dirname(android_manifest_path), "AndroidManifest_backup.xml")
    # 暂时不备份，因为git本身会追踪文件的修改
    # shutil.copy(android_manifest_path, backup_path)

    try:
        # 定义 namespace
        ET.register_namespace("android", "http://schemas.android.com/apk/res/android")
        ET.register_namespace("tools", "http://schemas.android.com/tools")
        ET.register_namespace("app", "http://schemas.android.com/apk/res-auto")

        # 解析 XML
        parser = ET.XMLParser(target=ET.TreeBuilder())
        tree = ET.parse(android_manifest_path, parser)
        root = tree.getroot()

        # **移除所有 <uses-permission> 和 <uses-feature> 元素**
        for element in root.findall("./uses-permission") + root.findall("./uses-feature"):
            root.remove(element)
        logging.info(f"移除所有 <uses-permission> 和 <uses-feature> 元素")

        # **找到正确的插入位置**
        insert_index = 0  # 默认插入到 <manifest> 开头
        for idx, child in enumerate(root):
            if child.tag == "uses-sdk":  # 在 <uses-sdk> 之后插入
                insert_index = idx + 1
                break
            elif child.tag == "application":  # 在 <application> 之前插入
                insert_index = idx
                break

        # **按顺序插入新的权限**
        elements_to_insert = list(permissions["permissions"].values()) + list(
            permissions["features"].values()
        )
        for element in reversed(elements_to_insert):  # 反向插入，确保顺序正确
            element.tail = "\n"  # 添加换行
            root.insert(insert_index, element)

        logging.info(f"添加新的 <uses-permission> 和 <uses-feature> 元素")

        # **使用 minidom 重新格式化 XML**
        formatted_xml = prettify_xml(root)
        with open(android_manifest_path, "w", encoding="utf-8") as f:
            f.write(formatted_xml)

        logging.info(f"写回文件")
        return True

    except Exception as e:
        logging.error(f"更新 AndroidManifest.xml 文件时发生错误: {e}")
        return False


def check_git_branch(project_path: str) -> bool:
    """
    检查Git项目分支状态并尝试切换到目标分支

    返回True的条件：
    1. 当前已在目标分支
    2. 可以安全切换到目标分支且切换成功
    3. 目标分支不存在但在无未提交更改的情况下，
       切换到master分支后创建新分支 config.PROD_BRANCH 成功

    返回False的条件：
    1. 有未提交的更改
    2. Git命令执行失败
    3. 其他异常情况

    Args:
        project_path: Git项目路径
    Returns:
        bool: 是否在目标分支或可以安全切换到目标分支
    """
    try:
        logging.info(f"开始检查Git分支: {project_path}")

        # 1. 获取当前分支
        current_branch_proc = subprocess.run(
            ["git", "branch", "--show-current"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            cwd=project_path,
        )
        if current_branch_proc.returncode != 0:
            logging.error(f"获取当前分支失败: {current_branch_proc.stderr}")
            return False

        current_branch = current_branch_proc.stdout.strip()
        logging.info(f"当前分支: {current_branch}")

        # 2. 如果已经在目标分支，直接返回True
        if current_branch == config.PROD_BRANCH:
            logging.info("已在目标分支上")
            return True

        # 3. 检查是否有未提交的更改（安全切换必须确保工作区干净）
        status_proc = subprocess.run(
            ["git", "status", "--porcelain"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            cwd=project_path,
        )
        if status_proc.returncode != 0:
            logging.error(f"检查工作区状态失败: {status_proc.stderr}")
            return False

        if status_proc.stdout.strip():
            logging.error("存在未提交的更改，无法安全切换分支")
            return False

        # 4. 检查目标分支是否存在
        branches_proc = subprocess.run(
            ["git", "branch", "-a"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            cwd=project_path,
        )
        if branches_proc.returncode != 0:
            logging.error(f"获取分支列表失败: {branches_proc.stderr}")
            return False

        branch_exists = any(
            branch.strip().endswith(config.PROD_BRANCH)
            for branch in branches_proc.stdout.split("\n")
        )

        if branch_exists:
            # 5. 如果目标分支存在，尝试直接切换到目标分支
            switch_proc = subprocess.run(
                ["git", "checkout", config.PROD_BRANCH],
                capture_output=True,
                text=True,
                encoding="utf-8",
                cwd=project_path,
            )
            if switch_proc.returncode != 0:
                logging.error(f"切换到目标分支失败: {switch_proc.stderr}")
                return False

            logging.info(f"成功切换到目标分支: {config.PROD_BRANCH}")
            return True
        else:
            # 6. 如果目标分支不存在，先切换到master分支，再从master创建新分支
            logging.info(f"目标分支 {config.PROD_BRANCH} 不存在，准备从master创建新分支")
            switch_master_proc = subprocess.run(
                ["git", "checkout", "master"],
                capture_output=True,
                text=True,
                encoding="utf-8",
                cwd=project_path,
            )
            if switch_master_proc.returncode != 0:
                logging.error(f"切换到master分支失败: {switch_master_proc.stderr}")
                return False

            logging.info("成功切换到master分支")
            create_branch_proc = subprocess.run(
                ["git", "checkout", "-b", config.PROD_BRANCH],
                capture_output=True,
                text=True,
                encoding="utf-8",
                cwd=project_path,
            )
            if create_branch_proc.returncode != 0:
                logging.error(f"从master创建新分支失败: {create_branch_proc.stderr}")
                return False

            logging.info(f"成功创建并切换到新分支: {config.PROD_BRANCH}")
            return True

    except Exception as e:
        logging.error(f"检查Git分支时发生错误: {e}")
        return False


def check_apps_directory() -> bool:
    """
    检查APPS_DIRECTORY目录下的目录结构是否符合要求
    Returns:
        bool: 是否符合要求
    """
    try:
        logging.info(f"开始检查APPS_DIRECTORY目录结构: {config.APPS_DIRECTORY}")
        contents = os.listdir(config.APPS_DIRECTORY)
        logging.info(f"目录内容: {contents}")
        # 检查目录数量是否为1，不为1则警告
        if len(contents) != 1:
            logging.warning(f"APPS_DIRECTORY中包含多个目录或文件: {contents}")

        # 检查目录名称是否与UNI_APP_ID一致,不一致则警告
        if contents[0] != config.UNI_APP_ID:
            logging.warning(
                f"APPS_DIRECTORY中的目录名称与UNI_APP_ID不匹配: {contents[0]} != {config.UNI_APP_ID}"
            )

        logging.info("APPS_DIRECTORY目录结构检查通过")
        return True
    except Exception as e:
        logging.error(f"检查APPS_DIRECTORY时发生错误: {e}")
        return False


def main():
    """
    主函数：执行整个更新流程
    1. 配置日志系统
    2. 检查依赖和路径
    3. 同步Git仓库
    4. 查找最新目录
    5. 检查是否已存在对应的APK文件，如果不存在则读取README.md获取版本信息
    6. 查找压缩文件
    7. 检查压缩文件内容（确保只有一个目录且目录名与UNI_APP_ID一致）
    8. 检查Git分支（确保在PROJECT_BRANCH分支）
    9. 检查APPS_DIRECTORY目录结构（确保只有一个目录且目录名与UNI_APP_ID一致）
    10. 清空目标目录
    11. 解压文件
    12. 更新build.gradle
    13. 更新control文件
    14. 更新 AndroidManifest.xml 文件，更新权限
    """
    try:
        # 配置日志
        setup_logging(clear_log_file=True, task_name="开始执行更新流程")

        # 检查依赖和路径
        check_dependencies()
        check_paths()

        # 同步仓库
        if not sync_repository(config.DISTRIBUTION_PATH):
            logging.error("Git仓库同步失败，终止执行")
            return

        # 查找最新目录
        identify_field_path = os.path.join(config.DISTRIBUTION_PATH, config.PROD_DIR)
        latest_dir = find_latest_directory(identify_field_path)

        # 查找是否已存在对应的APK文件
        latest_dir_name = os.path.basename(latest_dir)
        apk_file = os.path.join(latest_dir, f"{latest_dir_name}.apk")

        # 如果存在产物，则无需执行打包
        if not os.path.exists(apk_file):
            logging.info(f"已经存在产物 {apk_file} 无需执行打包")
            return 1
        else:
            # 不存在产物，则需要执行打包，读取README.md获取版本信息
            logging.info(f"不存在产物 {apk_file} 需要执行打包")
            readme_path = os.path.join(latest_dir, "README.md")
            readme_info = parse_readme(readme_path)

        # 更新UNI_APP_ID
        config.UNI_APP_ID = readme_info["uniapp_id"]
        # 查找压缩文件
        compressed_file = find_compressed_file(latest_dir)
        if not compressed_file:
            logging.error("未找到压缩文件，终止执行")
            return 1

        # 检查压缩文件内容
        check_result, temp_dir = check_compressed_file_content(compressed_file)
        if not check_result:
            logging.error("压缩文件内容检查失败，终止执行")
            return 1

        # 检查Git分支
        if not check_git_branch(config.ANDROID_UNI_BASE_PATH):
            logging.error("Git分支检查失败，终止执行")
            return 1

        # 检查APPS_DIRECTORY目录结构
        if not check_apps_directory():
            logging.error("APPS_DIRECTORY目录结构检查失败，终止执行")
            return 1

        # 清空目标目录
        if not clear_directory(config.APPS_DIRECTORY):
            logging.error("清空目标目录失败，终止执行")
            return 1

        # 解压文件
        if not extract_compressed_file(compressed_file, config.APPS_DIRECTORY):
            logging.error("解压文件失败，终止执行")
            return 1

        # 更新build.gradle
        if not update_build_gradle(
            config.BUILD_GRADLE_PATH,
            os.path.basename(latest_dir),
            readme_info,
        ):
            logging.error("更新build.gradle失败，终止执行")
            return 1

        # 更新 dcloud_control.xml 文件
        if not update_control_file(config.CONTROL_FILE_PATH, readme_info["uniapp_id"]):
            logging.error("更新 dcloud_control.xml 文件失败，终止执行")
            return 1

        # 跟新 AndroidManifest.xml 文件，更新权限
        if not update_android_manifest(config.ANDROID_MANIFEST_PATH, readme_info["permissions"]):
            logging.error("更新 AndroidManifest.xml 文件失败，终止执行")
            return 1

        logging.info("所有操作执行成功")
        return 0
    except Exception as e:
        logging.error(f"执行过程中发生错误: {e}")
        return 1


if __name__ == "__main__":
    main()
