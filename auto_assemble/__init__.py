"""
Auto Assemble - 自动化打包工具
"""

__version__ = "0.1.0"
__author__ = "Junerver"
__email__ = "junerver@gmail.com"

from .parse_manifest import parse_and_merge_permissions
from .parse_readme import parse_readme

__all__ = [
    "parse_and_merge_permissions",
    "parse_readme",
]
