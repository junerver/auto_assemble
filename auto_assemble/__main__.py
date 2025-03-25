"""
Auto Assemble 命令行入口
"""

import argparse
import os
import sys
import textwrap

from dotenv import load_dotenv

from auto_assemble.auto_flow import main as auto_flow


def create_env_file():
    """
    创建.env文件
    Returns:
        bool: 是否成功创建.env文件
    """
    env_file = ".env"
    env_content = textwrap.dedent(
        """\
        # 应用分发资源包目录
        DISTRIBUTION_PATH=D:\\dev\\identify_field\\app-distribution
        # Android基座的项目目录
        ANDROID_UNI_BASE_PATH=E:\\dev\\uni\\uni-base
        # 应用项目目录
        PROD_NAME=identify_field
        """
    )

    try:
        with open(env_file, "w", encoding="utf-8") as f:
            f.write(env_content)
        print(f"\n已创建 '{env_file}' 文件")
        print("\n请按照以下步骤操作：")
        print("1. 打开新创建的 .env 文件")
        print("2. 修改环境变量值为您的实际路径")
        print("3. 保存文件")
        print("4. 重新运行程序")
        return True
    except Exception as e:
        print(f"创建 .env 文件时发生错误: {e}")
        return False


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
        if create_env_file():
            input("\n按回车键退出...")
        else:
            print("\n无法创建环境变量文件，请手动创建。")
            input("按回车键退出...")
        return 1

    # 加载指定的 .env 文件
    load_dotenv(env_file)
    print(f"从 {env_file} 加载环境变量。")

    try:
        result = auto_flow()
        if result != 0:
            print("\n程序执行中断，请查看日志文件了解详细信息。")
            input("按回车键退出...")
        return result
    except Exception as e:
        print(f"\n程序发生异常: {e}")
        print("请查看日志文件了解详细信息。")
        input("按回车键退出...")
        return 1


if __name__ == "__main__":
    sys.exit(main())
