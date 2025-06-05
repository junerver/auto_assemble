"""
## 执行流程

1. 执行 copy_res.py，拉取最新资源，拷贝到项目构建工程，填充必要信息，此后需要人工核对内容，确认是否存在模块更新、权限列表增加删除；
2. 在确认完毕后执行 build.py 进行项目构建，拷贝打包后的内容到分发仓库
3. 执行 push.py 添加、提交、推送到分发仓库
"""

import logging
import sys

from common.client_publish import client_publish_async
from common.config import config


def auto_flow(task_id: str = None) -> int:
    """
    主函数，按顺序执行所有步骤

    Args:
        task_id: 任务ID，由项目名称与任务目录拼接而成，用于指定构建的目录
    """
    try:
        # 导入放在函数内部，避免循环导入
        from auto_assemble.copy_res import copy_res
        from auto_assemble.build import build
        from auto_assemble.push import push_distribution

        # 执行copy_res.py
        prod_name = None
        task_dir = None
        if task_id is not None:
            prod_name, task_dir = task_id.split(",")
            config.cur_task_id = task_id

        # 执行copy_res.py，拷贝资源，解析请求文件，对基座项目进行写覆盖操作
        client_publish_async("build", "构建任务:copy_res", f"开始执行copy_res，任务id{task_id}")
        if (copy_res_code := copy_res(prod_name, task_dir)) != 0:
            logging.warning("copy_res.py执行中断")
            return copy_res_code

        # 执行build.py，只有dev模式时才打debug包，其他时候打release包，在copy_res_main执行完毕后cur_task_dir被赋值，可以使用
        client_publish_async("build", "构建任务:build", f"开始执行build，任务id{task_id}")
        if (
            build_code := build(
                target_dir=config.cur_task_dir,
                release=False if config.build_mode == "dev" else True,
                is_distribution=True,
            )
        ) != 0:
            logging.warning("build.py执行中断")
            return build_code

        # 执行push.py
        client_publish_async("build", "构建任务:push", f"开始执行push，任务id{task_id}")
        if (push_code := push_distribution()) != 0:
            logging.warning("push.py执行中断")
            return push_code
        client_publish_async("build", "构建任务:push", "构建任务执行完毕")
        return 0
    except Exception as e:
        logging.exception(f"执行过程中发生错误: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(auto_flow())
