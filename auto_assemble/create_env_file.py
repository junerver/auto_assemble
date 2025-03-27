import os
from dataclasses import dataclass
from typing import Dict, Optional, Set


@dataclass
class EnvVarConfig:
    """环境变量配置类"""

    description: str
    validator: Optional[callable] = None
    default: Optional[str] = None


class EnvVarManager:
    """环境变量管理器"""

    def __init__(self):
        self.var_configs: Dict[str, EnvVarConfig] = {
            "DISTRIBUTION_PATH": EnvVarConfig("分发仓库的本地目录", self._validate_directory),
            "ANDROID_UNI_BASE_PATH": EnvVarConfig(
                "Android 基座项目所在目录", self._validate_directory
            ),
            "PROD_NAME": EnvVarConfig("要构建的项目标识（即分发仓库中项目目录名）"),
            "HBX_VERSION": EnvVarConfig("UniApp SDK 版本", self._validate_sdk_version, "4.45"),
            "UNIAPP_ID": EnvVarConfig("该项目的 UniApp APPID"),
            "UNIAPP_APPKEY": EnvVarConfig("该项目的 UniApp AppKey"),
            "UNIAPP_WORKSPACE": EnvVarConfig("本地UniApp项目所在目录", self._validate_directory),
            "UNIAPP_IS_CLI": EnvVarConfig(
                "该 UniApp 项目是否为CLI创建（y/n）", self._validate_yes_no
            ),
            "APK_OUTPUT_DIR": EnvVarConfig("最终 APK 产物输出目录", self._validate_directory),
        }

        # 定义不同功能需要的环境变量
        self.function_vars: Dict[str, Set[str]] = {
            "1": {
                "DISTRIBUTION_PATH",
                "ANDROID_UNI_BASE_PATH",
                "PROD_NAME",
                "HBX_VERSION",
            },  # 分发打包
            "2": {
                "PROD_NAME",
                "HBX_VERSION",
                "ANDROID_UNI_BASE_PATH",
                "UNIAPP_WORKSPACE",
                "UNIAPP_IS_CLI",
                "UNIAPP_ID",
                "UNIAPP_APPKEY",
                "APK_OUTPUT_DIR",
            },  # 本地打包
            "3": {
                "PROD_NAME",
                "HBX_VERSION",
                "ANDROID_UNI_BASE_PATH",
                "UNIAPP_WORKSPACE",
                "UNIAPP_IS_CLI",
                "UNIAPP_ID",
                "UNIAPP_APPKEY",
            },  # 本地构建离线基座
        }

    def _validate_directory(self, path: str) -> bool:
        """验证目录是否有效"""
        return os.path.isdir(path)

    def _validate_sdk_version(self, version: str) -> bool:
        """验证SDK版本是否有效"""
        return version in ["4.45", "4.56"]

    def _validate_yes_no(self, value: str) -> bool:
        """验证yes/no输入是否有效"""
        return value.lower() in ["y", "n"]

    def get_required_vars(self, select_func: Optional[str] = None) -> Set[str]:
        """获取指定功能所需的环境变量"""
        if not select_func:
            return set(self.var_configs.keys())
        return self.function_vars.get(select_func, set())

    def read_env_file(self, env_file: str) -> Dict[str, str]:
        """读取环境变量文件"""
        existing_vars = {}
        if os.path.exists(env_file):
            try:
                with open(env_file, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith("#") and "=" in line:
                            key, value = line.split("=", 1)
                            existing_vars[key.strip()] = value.strip()
            except Exception as e:
                print(f"读取现有环境变量文件时发生错误: {e}")
        return existing_vars

    def write_env_file(self, env_file: str, env_vars: Dict[str, str]) -> bool:
        """写入环境变量文件"""
        try:
            with open(env_file, "w", encoding="utf-8") as f:
                for var_name, config in self.var_configs.items():
                    if var_name in env_vars:
                        f.write(f"# {config.description}\n")
                        f.write(f"{var_name}={env_vars[var_name]}\n\n")
            return True
        except Exception as e:
            print(f"写入环境变量文件时发生错误: {e}")
            return False

    def get_var_value(self, var_name: str, existing_value: Optional[str] = None) -> str:
        """获取环境变量的值"""
        config = self.var_configs[var_name]

        if existing_value:
            return existing_value

        while True:
            prompt = f"请输入{config.description}"
            if config.default:
                prompt += f"（默认：{config.default}）"
            prompt += ": "

            value = input(prompt).strip()

            if not value and config.default:
                return config.default

            if config.validator and not config.validator(value):
                print(f"错误：输入的值无效，请重新输入。")
                continue

            return value


def create_env_file(env_file=".env", select_func=None):
    """
    创建或更新.env文件，根据功能选择只提示用户输入必要的环境变量
    Args:
        env_file: 环境变量文件路径
        select_func: 用户选择的功能，决定需要哪些环境变量
    Returns:
        bool: 是否成功创建/更新.env文件
    """
    manager = EnvVarManager()
    needed_vars = manager.get_required_vars(select_func)
    existing_vars = manager.read_env_file(env_file)

    print("\n请按照以下步骤操作，补充必要的环境变量：")

    # 收集新的环境变量
    new_vars = {}
    for var_name in needed_vars:
        if var_name not in existing_vars:
            new_vars[var_name] = manager.get_var_value(var_name)

    # 合并现有变量和新变量
    all_vars = {**existing_vars, **new_vars}

    if manager.write_env_file(env_file, all_vars):
        print(
            f"\n已成功{'更新' if os.path.exists(env_file) else '创建'} '{env_file}' 文件，"
            "你可以创建多个不同的 .env 文件，用于不同的项目。使用时通过 --env 参数指定。"
        )
        return True
    return False


def check_and_create_env(env_file: str, select_func: str):
    """检查并创建环境变量文件"""
    manager = EnvVarManager()

    if not os.path.exists(env_file):
        print(f"环境变量文件 '{env_file}' 不存在，请按照下面步骤引导，创建环境变量文件。")
        if create_env_file(env_file, select_func):
            return 0
        else:
            print("\n无法创建环境变量文件，请手动创建。")
            input("按回车键退出...")
            return 1

    # 检查必要的环境变量
    existing_vars = manager.read_env_file(env_file)
    required_vars = manager.get_required_vars(select_func)
    missing_vars = [var for var in required_vars if var not in existing_vars]

    if missing_vars:
        print(f"环境变量文件 '{env_file}' 缺少以下环境变量: {', '.join(missing_vars)}")
        print("请按照下面步骤引导，补充环境变量文件。")
        if create_env_file(env_file, select_func):
            return 0
        else:
            print("\n无法更新环境变量文件，请手动创建。")
            input("按回车键退出...")
            return 1

    print("请确认下面的环境变量：")
    print(
        "\n".join(
            f"# {config.description}\n{var_name}={existing_vars[var_name]}\n"
            for var_name, config in manager.var_configs.items()
            if var_name in existing_vars and var_name in required_vars
        )
    )
    input("按回车键继续...")
    return 0
