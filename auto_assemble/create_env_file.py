import os
import textwrap


def create_env_file():
    """
    创建.env文件
    Returns:
        bool: 是否成功创建.env文件
    """
    env_file = ".env"

    def get_valid_directory(prompt):
        while True:
            path = input(prompt).strip()
            if os.path.isdir(path):
                return path
            print(f"错误：'{path}' 不是一个有效的目录，请重新输入。")

    print("\n请按照以下步骤操作：")

    # 1. 获取分发仓库的本地目录
    distribution_path = get_valid_directory("1. 请输入分发仓库的本地目录: ")
    # 2. 获取 Android 基座项目所在目录
    android_uni_base_path = get_valid_directory("2. 请输入 Android 基座项目所在目录: ")
    # 3. 获取项目标识
    prod_name = input("3. 请输入要构建的项目标识（即分发仓库中项目目录名）: ").strip()
    # 4. UniApp SDK 版本，默认使用4.45
    uniapp_sdk_version = input("4. 请输入要使用的 SDK 版本:（例如：4.45） ").strip()
    if not uniapp_sdk_version:
        uniapp_sdk_version = "4.45"
    # 5. 填写该项目的 UniApp ID
    uniapp_id = input("5. 请输入该项目的 UniApp APPID: ").strip()
    # 6. 填写该项目的 UniApp AppKey
    uniapp_appkey = input("6. 请输入该项目的 UniApp AppKey: ").strip()

    env_content = textwrap.dedent(
        f"""
        # 应用分发资源包目录
        DISTRIBUTION_PATH={distribution_path}
        # Android基座的项目目录
        ANDROID_UNI_BASE_PATH={android_uni_base_path}
        # 应用项目目录
        PROD_NAME={prod_name}
        # UniApp SDK 版本
        HBX_VERSION={uniapp_sdk_version}
        # UniApp ID
        UNIAPP_ID={uniapp_id}
        # UniApp AppKey
        UNIAPP_APPKEY={uniapp_appkey}
        """
    )

    try:
        with open(env_file, "w", encoding="utf-8") as f:
            f.write(env_content)
        print(
            f"\n已成功创建 '{env_file}' 文件，你可以创建多个不同的 .env 文件，用于不同的项目。使用时通过 --env 参数指定。"
        )
        return True
    except Exception as e:
        print(f"创建 .env 文件时发生错误: {e}")
        return False


def check_and_create_env(env_file: str):
    if not os.path.exists(env_file):
        print(f"环境变量文件 '{env_file}' 不存在，请按照下面步骤引导，创建环境变量文件。")
        if create_env_file():
            return 0
        else:
            print("\n无法创建环境变量文件，请手动创建。")
            input("按回车键退出...")
            return 1
    else:
        # 环境变量文件存在，输出环境变量要求用户确认
        with open(env_file, "r", encoding="utf-8") as f:
            env_content = f.read()
        print("请确认下面的环境变量：")
        print(env_content)
        input("按回车键继续...")
        return 0
