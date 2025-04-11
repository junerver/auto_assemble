import time

from auto_assemble.config import config
from cbr.create_build_req import create_build_req, rolling_req_build_status

if __name__ == "__main__":
    # 构建打包请求
    create_build_req()
    # 等待5秒后开始轮询构建状态
    time.sleep(5)
    rolling_req_build_status()
    if config.work_mode == "ui":
        input("按回车键退出")
