"""
## 执行流程

1. 执行 copy_res.py，拉取最新资源，拷贝到项目构建工程，填充必要信息，此后需要人工核对内容，确认是否存在模块更新、权限列表增加删除；
2. 在确认完毕后执行 build.py 进行项目构建，拷贝打包后的内容到分发仓库
3. 执行 push.py 添加、提交、推送到分发仓库
"""

import logging
import sys


def main():
    """主函数，按顺序执行所有步骤"""
    try:
        # 导入放在函数内部，避免循环导入
        from auto_assemble.copy_res import main as copy_res_main
        from auto_assemble.build import main as build_main
        from auto_assemble.push import main as push_main

        # 执行copy_res.py
        if copy_res_main() != 0:
            logging.warning("copy_res.py执行中断")
            return 1

        # 执行build.py
        if build_main() != 0:
            logging.warning("build.py执行中断")
            return 1

        # 执行push.py
        if push_main() != 0:
            logging.warning("push.py执行中断")
            return 1

        return 0
    except Exception as e:
        logging.error(f"执行过程中发生错误: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
