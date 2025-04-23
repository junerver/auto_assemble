"""
Auto Assemble 命令行入口
"""

import argparse
import logging
import os
import sys
import textwrap

from dotenv import load_dotenv

from auto_assemble.auto_flow import main as auto_flow
from auto_assemble.config import config
from auto_assemble.create_env_file import check_and_create_env
from auto_assemble.welcome import welcome


def main():
    """
    主函数，用于执行命令行入口
    """
    try:
        parser = argparse.ArgumentParser(
            description="Load environment variables from a specified .env file and execute the program."
        )
        # 指定.env文件路径
        parser.add_argument("--env", type=str, help="Path to the .env file")
        # 指定执行的功能序号
        parser.add_argument("--fn", type=str, help="function name")
        # task id，任务id，由`打包项目,请求的任务`目录拼接而成
        parser.add_argument("--task", type=str, help="Task id: prod_name,task_dir")
        args = parser.parse_args()
        env_file = args.env if args.env else os.path.join(os.getcwd(), ".env")
        fn = args.fn if args.fn else None
        if fn:
            select_func = fn
            config.work_mode = "cli"

        if config.work_mode == "ui":
            welcome()
            print(
                textwrap.dedent(
                    """
                    请输入下面序号选择功能：
                    1. 从分发仓库拉取资源进行打包
                    """
                )
            )
            select_func = input("请输入功能序号：").strip()

        if (
                os.getenv("DISTRIBUTION_PATH") is not None
                and os.getenv("ANDROID_UNI_BASE_PATH") is not None
                and os.getenv("WEBHOOK_URL") is not None
        ):
            # 从环境变量中加载相关变量
            print(f"DISTRIBUTION_PATH: {os.getenv('DISTRIBUTION_PATH')}")
            print(f"ANDROID_UNI_BASE_PATH: {os.getenv('ANDROID_UNI_BASE_PATH')}")
            print(f"WEBHOOK_URL: {os.getenv('WEBHOOK_URL')}")
            print("已从环境变量中加载相关变量，不再从.env文件中加载。")
        else:
            check_and_create_env(env_file, select_func)
            # 加载指定的 .env 文件
            load_dotenv(env_file)
            print(f"已从 {env_file} 加载环境变量。")

        if select_func == "1":
            # 从分发仓库拉取资源进行打包
            result = auto_flow(task_id=args.task if args.task else None)
        else:
            print("输入错误，请重新输入。")

        if result != 0:
            logging.error(f"\n{result} 程序执行中断，请查看日志文件了解详细信息。")
        if config.work_mode == "ui":
            input("按回车键退出...")
        return result
    except Exception as e:
        print(f"\n程序发生异常: {e}")
        print("请查看日志文件了解详细信息。")
        if config.work_mode == "ui":
            input("按回车键退出...")
        return 1


if __name__ == "__main__":
    sys.exit(main())
