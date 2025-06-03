# tests/conftest.py
import sys
from pathlib import Path

# 获取项目根目录路径
root_dir = Path(__file__).parent.parent
src_dir = root_dir / "src"

# 将 src 目录添加到 Python 路径
sys.path.insert(0, str(src_dir))
