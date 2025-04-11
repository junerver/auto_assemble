import json
import logging
import os
from typing import Dict, Tuple

from cbr.parse_uni_manifest import parse_uni_manifest


def scan_uni_project(project_root: str, cbr_dir: str) -> Dict[str, str] | None:
    """
    1. 扫描项目目录，拿到.git/config 文件，识别出其中项目的地址（作为依据检查项目配置）
    2. 使用git地址作为查询条件找到在打包服务后台配置的项目
        - DISTRIBUTION_PATH，分发仓库位置，即cbr_dir目录的父目录
        - PROD_NAME，项目标识
        - HBX_VERSION，hbuilderx 版本
        - UNIAPP_ID，项目id
        - UNIAPP_APPKEY，项目key
        - UNIAPP_WORKSPACE，本地地址
        - UNIAPP_IS_CLI，是否为cli项目
    3. 写环境变量到.env.assemble.local
    4. 返回最终创建的环境变量文件

    Args:
        project_root: 项目根目录
        cbr_dir: cbr目录

    Returns:
        Dict[str, str] | None: 环境变量文件对应的数据字典
    """
    try:
        # 1. 读取 .git/config 文件获取项目URL
        git_config_path = os.path.join(project_root, ".git", "config")
        if not os.path.exists(git_config_path):
            logging.error(f"Git配置文件不存在: {git_config_path}")
            return None

        project_url = ""
        in_origin_section = False
        with open(git_config_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line == '[remote "origin"]':
                    in_origin_section = True
                elif line.startswith("[") and line.endswith("]"):
                    in_origin_section = False
                elif in_origin_section and line.startswith("url ="):
                    project_url = line.split("=")[1].strip()
                    break

        if not project_url:
            logging.error("未能在git配置中找到origin远程仓库的URL")
            return None

        # 2. 调用API获取项目配置
        import requests
        from auto_assemble.config import config

        api_url = f"{config.server_host_url}/api/config/project"
        params = {"url": project_url}

        response = requests.get(api_url, params=params)
        if response.status_code != 200:
            logging.error(f"获取项目配置失败: {response.text}")
            return None

        data = response.json()
        if "error" in data:
            logging.error(f"获取项目配置错误: {data['error']}")
            return None

        project_config = data["project_config"]

        # 3. 构建环境变量字典
        env_vars = {
            "UNIAPP_WORKSPACE": project_root,
            "DISTRIBUTION_PATH": os.path.dirname(cbr_dir),  # cbr_dir的父目录
            "PROD_NAME": project_config["prod_name"],
            "HBX_VERSION": project_config["hbx_version"],
            "UNIAPP_ID": project_config["uniapp_id"],
            "UNIAPP_APPKEY": project_config["uniapp_appkey"],
            "UNIAPP_IS_CLI": "y" if project_config["uniapp_is_cli"] else "n",
        }
        config._distribution_path = env_vars["DISTRIBUTION_PATH"]
        config.PROD_NAME = env_vars["PROD_NAME"]
        logging.info(f"读取到项目配置如下:\n {json.dumps(env_vars)}")
        return env_vars

    except Exception as e:
        logging.error(f"扫描项目时发生错误: {str(e)}")
        return None


def check_uni_project(env_vars: Dict[str, str] | None = None) -> Tuple[bool, Dict[str, str], str]:
    """
    根据环境变量设置的 UniApp 项目地址、是否为CLI创建项目，来确定 manifest.json 文件所在目录
    如果是cli项目，则位于{项目目录}/src/manifest.json下
    如果不是 cli 项目，则位于{项目目录}/manifest.json下
    打包后uni资源目录位置在{项目目录}/unpackage/resources下
    工作流程：
    1. 读取环境变量中的 UNIAPP_WORKSPACE、UNIAPP_IS_CLI，确定manifest文件位置
    2. 调用parse_uni_manifest解析文件，获得响应的数据
    3. 校验打包后资源目录是否存在，是否与解析到的uniapp_id值一致
    4. 返回值用于判断是否校验通过

    Args:
        - env_vars: 用来代替环境变量的参数值传递

    Returns:
        Tuple[bool, Dict[str, str], str]: (是否校验通过, manifest解析结果, 资源目录(app_id目录的上级目录))
    """
    try:

        workspace = env_vars["UNIAPP_WORKSPACE"]
        is_cli = env_vars["UNIAPP_IS_CLI"].lower() == "y"

        if not workspace:
            logging.error("未设置 UNIAPP_WORKSPACE 环境变量")
            return False, {}, ""

        # 确定 manifest.json 文件位置
        manifest_path = (
            os.path.join(workspace, "src", "manifest.json")
            if is_cli
            else os.path.join(workspace, "manifest.json")
        )

        if not os.path.exists(manifest_path):
            logging.error(f"manifest.json 文件不存在: {manifest_path}")
            return False, {}, ""

        # 解析 manifest.json 文件
        manifest_info = parse_uni_manifest(manifest_path, env_vars)
        if not manifest_info.get("uniapp_id"):
            logging.error("未能在 manifest.json 中解析到 uniapp_id")
            return False, manifest_info, ""

        # 检查资源目录
        resources_dir = os.path.join(workspace, "unpackage", "resources")
        if not os.path.exists(resources_dir):
            logging.error(f"资源目录不存在: {resources_dir}")
            return False, manifest_info, ""

        # 检查资源目录中是否存在名称为uniapp_id的目录
        resources_contents = os.listdir(resources_dir)
        if not resources_contents:
            logging.error("资源目录为空")
            return False, manifest_info, ""
        for content in resources_contents:
            if content == manifest_info["uniapp_id"]:
                logging.info(
                    f"资源目录名称与 uniapp_id 匹配: {content} == {manifest_info['uniapp_id']}"
                )
                return True, manifest_info, resources_dir
        logging.error(f"资源目录中不存在名称为{manifest_info['uniapp_id']}的目录")
        return False, manifest_info, ""

    except Exception as e:
        error_msg = f"检查 UniApp 项目时发生错误: {str(e)}"
        logging.error(error_msg)
        return False, {}, ""
