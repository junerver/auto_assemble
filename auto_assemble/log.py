import logging
import os
import sys
from datetime import datetime

from auto_assemble.config import config


def setup_logging(clear_log_file: bool = False, task_name: str = "任务"):
    """
    配置日志系统
    Args:
        clear_log_file: 是否在设置日志前清空日志文件
        task_name: 任务名称，用于日志分隔显示
    """
    # 如果需要清空日志文件且文件存在
    if clear_log_file and os.path.exists(config.LOG_FILE):
        os.remove(config.LOG_FILE)

    # 配置日志
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler(
                config.LOG_FILE, encoding="utf-8", mode="a" if not clear_log_file else "w"
            ),
            logging.StreamHandler(sys.stdout),
        ],
    )

    # 添加分隔线，区分不同任务的日志
    logging.info("=" * 50)
    logging.info(f"开始{task_name} - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logging.info("=" * 50)
