"""
Auto Assemble - 自动化打包工具
"""

__author__ = "Junerver"
__email__ = "junerver@gmail.com"

from auto_assemble.parse_permissions import parse_and_merge_permissions
from auto_assemble.parse_readme import parse_readme

__all__ = [
    "parse_and_merge_permissions",
    "parse_readme",
]
