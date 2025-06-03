import sys
import time

from cbr.create_build_req import create_build_req, rolling_req_build_status
from common.config import config


def main():
    # 构建打包请求
    if create_build_req() != 0:
        print("构建打包请求失败")
        input("按回车键退出")
        exit(1)
    # 等待5秒后开始轮询构建状态
    time.sleep(5)
    rolling_req_build_status()
    if config.work_mode == "ui":
        input("按回车键退出")


if __name__ == "__main__":
    sys.exit(main())
