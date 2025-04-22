import logging
import os
from datetime import datetime

import colorlog

from auto_assemble.config import config


def setup_logging(clear_log_file: bool = False, task_name: str = "任务"):
    """
    配置日志系统
    Args:
        clear_log_file: 是否在设置日志前清空日志文件
        task_name: 任务名称，用于日志分隔显示
    """
    # 获取根日志记录器
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    # 移除所有现有的处理器
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)

    # 如果需要清空日志文件且文件存在
    if clear_log_file and os.path.exists(config.LOG_FILE):
        os.remove(config.LOG_FILE)

    # 文件处理器
    file_handler = logging.FileHandler(config.LOG_FILE, encoding="utf-8")
    file_handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))

    # 控制台处理器（带颜色）
    console_handler = colorlog.StreamHandler()
    console_handler.setFormatter(
        colorlog.ColoredFormatter(
            "%(log_color)s%(asctime)s - %(levelname)s - %(message)s",
            datefmt=None,
            reset=True,
            log_colors={
                "DEBUG": "cyan",
                "INFO": "green",
                "WARNING": "yellow",
                "ERROR": "red",
                "CRITICAL": "red,bg_white",
            },
            secondary_log_colors={},
            style="%",
        )
    )

    # 添加处理器
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    # 添加分隔线，区分不同任务的日志
    logging.info("=" * 50)
    logging.info(f"开始{task_name} - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logging.info("=" * 50)
