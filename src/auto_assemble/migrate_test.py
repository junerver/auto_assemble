import json
import logging
from pathlib import Path
from typing import Optional

from auto_assemble.build import exec_normalized_apk, sign_apk, update_metadata_md, parse_metadata
from auto_assemble.push import push_distribution
from common.api import fetch_project_info_by_prod_name, record_task_metadata
from common.config import config
from common.error import BusinessException
from common.gitlab import download_task_resp
from common.types import TaskInfo, ProjectConfig, SignConfig, BuildMetadata


def migrate_test(old_task: TaskInfo):
    """
    跳过构建过程，直接对 test 的产物进行归一化、签名
    Args:
        old_task:

    Returns:

    """
    # 下载文件
    download_task_resp(old_task, config.cur_task_dir)
    # 未执行归一化的apk
    source_apk: Path = config.cur_task_dir / f"{config.cur_task_dir.name}.apk"
    metadata_md: Path = config.cur_task_dir / "release-metadata.md"
    obfuscated_bak: Path = config.cur_task_dir / f"{config.cur_task_dir.name}_obfuscated.bak"
    # 归一化后的apk文件（注意使用完毕后删除）
    normalized_apk: Path = Path("/app") / "temp" / "normalized.apk"

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
            # todo: 更新 metadata 文件，需要更新更多字段
            md5, content = update_metadata_md(
                metadata_md,
                signed_md5,
                signed_size,
                True,
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
            if (push_code := push_distribution()) != 0:
                logging.warning("push.py执行中断")
                raise BusinessException(push_code)
            # 执行成功跳出后续步骤
            raise BusinessException(0)
        except Exception as e:
            logging.exception(f"执行归一化时发生错误: {e}")
            cleanup()
            raise BusinessException(12015)
    else:
        logging.info("签名配置无效")
        cleanup()
        raise BusinessException(12016)
