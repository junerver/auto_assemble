"""
Auto Assemble 命令行入口
"""

import argparse
import os
import sys

from dotenv import load_dotenv

from auto_assemble.auto_flow import main as auto_flow


def main():
    """
    主函数，用于执行命令行入口
    """
    parser = argparse.ArgumentParser(
        description="Load environment variables from a specified .env file and execute the program."
    )
    parser.add_argument("--env", type=str, help="Path to the .env file")

    args = parser.parse_args()
    env_file = args.env if args.env else os.path.join(os.getcwd(), ".env")

    if not os.path.exists(env_file):
        print(f"环境变量文件 '{env_file}' 不存在。")
        sys.exit(1)

    # 加载指定的 .env 文件
    load_dotenv(env_file)
    print(f"从 {env_file} 加载环境变量。")
    auto_flow()
    return 0


if __name__ == "__main__":
    sys.exit(main())
