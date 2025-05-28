import logging
from datetime import datetime
from typing import Any, Optional


def safe_convert_datetime(value: Any) -> Optional[datetime]:
    """安全地转换日期时间值

    Args:
        value: 要转换的值，可以是 datetime 对象、ISO 格式字符串或 None

    Returns:
        转换后的 datetime 对象，如果转换失败则返回 None
    """
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value)
        except ValueError:
            return None
    if isinstance(value, int):
        try:
            # 判断是秒还是毫秒级时间戳
            if value > 1e12:
                # 毫秒级，除以 1000
                timestamp = value / 1000
            else:
                # 秒级，直接用
                timestamp = value
            return datetime.fromtimestamp(timestamp)
        except Exception as e:
            logging.error(f"转换失败：{value}，错误信息：{e.with_traceback()}")
            return None
    return None
