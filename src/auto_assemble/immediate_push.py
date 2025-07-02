"""
这个脚本文件用于处理直接复用的场景，有时候可能存在前端资源包没有任何变化的情况，
操作人员误操作重新打包，有以下几种情况可以直接推送
新 <- 旧
dev <- dev
test <- test
release <- test  （特殊迁移，需要重新执行归一化、重签名，因为test分支不执行归一化）
release <- release

"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

from auto_assemble.build import exec_normalized_apk, sign_apk, update_metadata_md, parse_metadata
from auto_assemble.push import push_distribution
from common.api import fetch_project_info_by_prod_name, record_task_metadata
from common.config import config
from common.error import BusinessException
from common.gitlab import download_task_resp
from common.types import TaskInfo, ProjectConfig, SignConfig, BuildMetadata


def migrate_test_to_release(old_task: TaskInfo):
    """
    跳过构建过程，直接对 test 的产物进行归一化、签名
    Args:
        old_task:

    Returns:

    """
    # 下载文件（元数据、混淆后的资源包、原始apk）
    metadata_md, obfuscated_bak, source_apk = download_task_resp(old_task, config.cur_task_dir)
    # 归一化后的apk文件（注意使用完毕后删除）
    normalized_apk: Path = config.TEMP_PATH / "normalized.apk"

    def cleanup():
        if source_apk.exists():
            source_apk.unlink()
        if normalized_apk.exists():
            normalized_apk.unlink()
        if metadata_md.exists():
            metadata_md.unlink()
        if obfuscated_bak.exists():
            obfuscated_bak.unlink()

    project_config: Optional[ProjectConfig] = fetch_project_info_by_prod_name(config.PROD_NAME)
    if project_config and project_config.is_sign_config_valid():
        # 签名有效
        sign_config: SignConfig = project_config.get_sign_config()
        try:
            # 执行归一化
            exec_normalized_apk(
                source_apk,
                normalized_apk,
            )
            # 归一化成功移除源文件
            source_apk.unlink()
            # 重新签名
            signed_apk, signed_size, signed_md5 = sign_apk(
                normalized_apk,
                sign_config,
                source_apk,
            )
            normalized_apk.unlink()
            # 更新 metadata 文件
            md5, content = update_metadata_md(
                metadata_md,
                signed_md5,
                signed_size,
                True,
                datetime.now(),
            )

            # 创建MD5空白文件
            md5_path = config.cur_task_dir / md5
            md5_path.touch()
            logging.info("成功复制并更新metadata文件")

            # 解析metadata并记录到服务器
            metadata: BuildMetadata = parse_metadata(content)
            logging.info(f"解析metadata文件结果: {json.dumps(metadata)}，请求接口提交元数据")
            record_task_metadata(config.cur_task_id, metadata)
            # 此时文件已经全部到位，推送分发仓库
            push_code = push_distribution()
            if push_code != 0:
                logging.warning("push.py执行中断")
                raise BusinessException(push_code)
            # 执行成功
            raise BusinessException(0)
        except BusinessException as e:
            # 直接抛出 BusinessException，保留原始错误码
            if e.code != 0:
                cleanup()
            raise
        except Exception as e:
            logging.exception(f"执行归一化时发生错误: {e}")
            cleanup()
            raise BusinessException(12015)
    else:
        logging.info("签名配置无效")
        cleanup()
        raise BusinessException(12016)


def migrate_same_build_mode(old_task: TaskInfo):
    # 下载文件
    metadata_md, obfuscated_bak, apk_file = download_task_resp(old_task, config.cur_task_dir)

    md5, content = update_metadata_md(metadata_md, date_time=datetime.now())
    metadata: BuildMetadata = parse_metadata(content)
    md5_path = config.cur_task_dir / md5
    md5_path.touch()
    logging.info(f"解析metadata文件结果: {json.dumps(metadata)}，请求接口提交元数据")
    record_task_metadata(config.cur_task_id, metadata)
    # 此时文件已经全部到位，推送分发仓库
    if config.BASE_ON_GITLAB:
        push_code = push_distribution()
        if push_code != 0:
            logging.warning("push.py执行中断")
            raise BusinessException(push_code)
    # 执行成功
    raise BusinessException(0)
