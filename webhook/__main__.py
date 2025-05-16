import sys

import uvicorn

from webhook.config import PORT, DEBUG


def main():
    uvicorn.run(
        "webhook.app:app",
        host="0.0.0.0",
        port=PORT,
        reload=DEBUG,
        reload_dirs=["webhook"],  # 🔧 指定监听的目录，避免监听过多文件
        reload_includes=["*.py"],  # ✅ 只监听 .py 文件
        reload_excludes=["*.log", "*.db", "venv/*", "__pycache__/*"],
        log_level="info",
    )


if __name__ == "__main__":
    sys.exit(main())
