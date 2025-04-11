import logging
import os
from typing import Dict, Tuple

from cbr.parse_uni_manifest import parse_uni_manifest


def check_uni_project() -> Tuple[bool, Dict[str, str], str]:
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
    Returns:
        Tuple[bool, Dict[str, str], str]: (是否校验通过, manifest解析结果, 资源目录(app_id目录的上级目录))
    """
    try:
        # 获取环境变量
        workspace = os.getenv("UNIAPP_WORKSPACE")
        is_cli = os.getenv("UNIAPP_IS_CLI", "n").lower() == "y"

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
        manifest_info = parse_uni_manifest(manifest_path)
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
