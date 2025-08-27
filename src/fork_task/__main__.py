import logging
import sys

import click

from common.client_publish import client_publish_async
from common.err_code import unified_error_code
from common.error import BusinessException
from fork_task.copy_source import copy_source
from fork_task.modify_uni_res import modify_uni_res
from fork_task.re_req import re_req


@click.command(help="Load environment variables from a specified .env file and execute the program.")
@click.option("--fork", type=str, help="ForkTask id: prod_name,task_dir")
def main(fork: str):
    fork_task_id = fork
    print(fork_task_id)

    try:
        # 根据fork_task_id，复制源文件到临时目录
        client_publish_async("fork", "派生任务", f"开始从{fork_task_id}拷贝资源")
        logging.info(f"复制源文件: {fork_task_id}")
        temp_dir, fork_task_info = copy_source(fork_task_id)

        # 修改 uni-res 资源
        client_publish_async("fork", "派生任务", "资源拷贝完成，开始修改 uni-res 资源")
        modify_uni_res(temp_dir, fork_task_info)

        client_publish_async("fork", "派生任务", "修改 uni-res 资源完成，开始创建新的派生任务")
        # 创建新的派生任务
        re_req(temp_dir, fork_task_info)

        client_publish_async("fork", "派生任务", "创建新的派生任务完成，等待任务执行...")
        return 0
    except Exception as e:
        if isinstance(e, BusinessException):
            logging.error(f"业务错误: {e.code} {e.message}")
            return unified_error_code(e.code)
        else:
            logging.exception(f"未知错误: {e}")
            return 1


if __name__ == "__main__":
    sys.exit(main())
