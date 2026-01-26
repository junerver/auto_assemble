import logging
import shutil
import subprocess
import sys
import zipfile
from datetime import datetime, timedelta
from pathlib import Path
from typing import Literal

from common.config import config
from common.extract import modern_extract

ObfuscatePreset = Literal["default", "low", "medium", "high"]

PRESET_MAP = {
    "default": "default",
    "low": "low-obfuscation",
    "medium": "medium-obfuscation",
    "high": "high-obfuscation",
}

# 结果保留时间（小时）
RESULT_TTL_HOURS = 24

# 混淆结果存储
OBFUSCATE_RESULTS: dict[str, dict] = {}


class ObfuscateService:
    @staticmethod
    def get_obfuscate_dir() -> Path:
        """获取混淆工作目录"""
        obfuscate_dir = config.TEMP_PATH / "obfuscate"
        obfuscate_dir.mkdir(parents=True, exist_ok=True)
        return obfuscate_dir

    @staticmethod
    def extract_zip(zip_path: Path, extract_dir: Path) -> None:
        """解压 zip 文件"""
        extract_dir.mkdir(parents=True, exist_ok=True)
        modern_extract(zip_path, extract_dir)

    @staticmethod
    def run_obfuscator(source_dir: Path, preset: ObfuscatePreset) -> tuple[bool, str]:
        """执行 javascript-obfuscator 混淆

        Args:
            source_dir: 要混淆的源目录
            preset: 混淆等级

        Returns:
            (成功标志, 错误信息)
        """
        if sys.platform == "win32":
            obfuscator_cmd = "javascript-obfuscator.cmd"
        else:
            obfuscator_cmd = "javascript-obfuscator"

        cmd = [
            obfuscator_cmd,
            str(source_dir),
            "--output",
            str(source_dir),
            "--options-preset",
            PRESET_MAP[preset],
        ]

        logging.info(f"执行混淆命令: {cmd}")
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            logging.info(f"混淆成功: {result.stdout}")
            return True, ""
        except subprocess.CalledProcessError as e:
            error_msg = f"混淆失败: {e.stderr or e.stdout or str(e)}"
            logging.error(error_msg)
            return False, error_msg
        except FileNotFoundError:
            error_msg = "javascript-obfuscator 未安装，请先执行 npm install -g javascript-obfuscator"
            logging.error(error_msg)
            return False, error_msg

    @staticmethod
    def create_obfuscated_zip(source_dir: Path, output_path: Path) -> Path:
        """将混淆后的目录打包为 zip 文件

        Args:
            source_dir: 混淆后的源目录
            output_path: 输出 zip 文件路径

        Returns:
            zip 文件路径
        """
        with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as zipf:
            for file_path in source_dir.rglob("*"):
                if file_path.is_file():
                    arcname = file_path.relative_to(source_dir)
                    zipf.write(file_path, arcname)
        logging.info(f"打包混淆结果: {output_path}")
        return output_path

    @staticmethod
    def store_result(task_uuid: str, zip_path: Path, original_filename: str) -> dict:
        """存储混淆结果"""
        expires_at = datetime.now() + timedelta(hours=RESULT_TTL_HOURS)
        result = {
            "path": zip_path,
            "filename": f"{original_filename.replace('.zip', '')}_obfuscated.zip",
            "expires_at": expires_at,
        }
        OBFUSCATE_RESULTS[task_uuid] = result
        return result

    @staticmethod
    def get_result(task_uuid: str) -> dict | None:
        """获取混淆结果"""
        return OBFUSCATE_RESULTS.get(task_uuid)

    @staticmethod
    def remove_result(task_uuid: str) -> None:
        """移除混淆结果记录"""
        if task_uuid in OBFUSCATE_RESULTS:
            del OBFUSCATE_RESULTS[task_uuid]

    @staticmethod
    def cleanup_work_dir(work_dir: Path) -> None:
        """清理工作目录"""
        if work_dir.exists():
            shutil.rmtree(work_dir)
            logging.info(f"清理工作目录: {work_dir}")

    @staticmethod
    def cleanup_expired_files() -> int:
        """清理过期的混淆结果文件

        Returns:
            清理的文件数量
        """
        now = datetime.now()
        expired_uuids = []

        for task_uuid, result in OBFUSCATE_RESULTS.items():
            if now > result["expires_at"]:
                expired_uuids.append(task_uuid)
                work_dir = result["path"].parent
                if work_dir.exists():
                    shutil.rmtree(work_dir)
                    logging.info(f"清理过期混淆结果: {task_uuid}")

        for task_uuid in expired_uuids:
            del OBFUSCATE_RESULTS[task_uuid]

        return len(expired_uuids)
