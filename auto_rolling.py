import logging
import os
import subprocess
import time

from auto_assemble.config import config
from auto_assemble.git import git_fetch

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler("auto_rolling.log"), logging.StreamHandler()],
)


def main():
    logging.info("开始运行自动轮询脚本")

    while True:
        try:
            # 检查git仓库是否有更新
            if git_fetch(config.DISTRIBUTION_PATH):
                logging.info("检测到远程仓库有更新，开始执行自动构建")
                # 执行自动构建命令，注意移除capture_output=True,text=True,encoding="utf-8"这些选项，因为auto-assemble脚本执行时输出到控制台
                result = subprocess.run(
                    ["auto-assemble", "--fn", "1"],
                    cwd=os.path.dirname(os.path.abspath(__file__)),
                )
                if result.returncode == 0:
                    logging.info("自动构建执行成功")
                else:
                    logging.error(f"自动构建执行失败: {result.stderr or '未知错误'}")

            # 等待5秒后继续下一次检查
            time.sleep(5)

        except Exception as e:
            logging.error(f"轮询过程中发生错误: {str(e)}")
            time.sleep(5)  # 发生错误时也等待5秒后继续


if __name__ == "__main__":
    main()
