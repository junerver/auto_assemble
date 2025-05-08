import argparse
import logging
import sys

from common.err_code import unified_error_code
from common.error import BusinessException
from fork_task.copy_source import copy_source
from fork_task.modify_uni_res import modify_uni_res
from fork_task.re_req import re_req


def main():
    parser = argparse.ArgumentParser(
        description="Load environment variables from a specified .env file and execute the program."
    )
    # fork task id，派生任务id，由`打包项目,请求的任务`目录拼接而成
    parser.add_argument("--fork", type=str, help="ForkTask id: prod_name,task_dir")
    args = parser.parse_args()
    fork_task_id = args.fork
    print(fork_task_id)

    # 根据fork_task_id，复制源文件到临时目录
    try:
        logging.info(f"复制源文件: {fork_task_id}")
        temp_dir, fork_task_info = copy_source(fork_task_id)

        # 修改 uni-res 资源
        modify_uni_res(temp_dir, fork_task_info)

        # 创建新的派生任务
        re_req(temp_dir, fork_task_info)

        return 0
    except Exception as e:
        if isinstance(e, BusinessException):
            logging.error(f"业务错误: {e.code} {e.message}")
            return unified_error_code(e.code)
        else:
            logging.error(f"未知错误: {e}")
            return 1


if __name__ == "__main__":
    sys.exit(main())
