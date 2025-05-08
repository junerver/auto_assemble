import os
from typing import Literal


Work_Mode = Literal["ui", "cli"]


class Config:
    def __init__(self):
        # 应用分发资源包目录
        self._distribution_path = None
        # Android基座的项目目录
        self._android_uni_base_path = None

        # UniApp的资源包目录
        self._apps_directory = None
        # 应用的AndroidManifest.xml文件路径
        self._android_manifest_path = None
        # UniApp的 dcloud_control.xml 文件位置
        self._control_file_path = None
        # 应用的build.gradle文件路径
        self._build_gradle_path = None
        # 应用的version.toml文件路径
        self._versions_toml_path = None
        # 日志文件路径
        self.LOG_FILE = os.path.join(os.getcwd(), "auto_assemble.log")

        # 构建输出配置
        self._build_release_output_dir = None
        self._build_debug_output_dir = None

        # Git相关配置
        self._prod_branch = None
        self._prod_name = None

        # 应用配置
        self.UNI_APP_ID: str = ""
        # Git提交信息
        self.last_commit_message = ""
        # 工作模式：ui 或 cli , 默认ui，ui模式下需要用户确认，cli 模式下通过 --fn 直接指定功能序号，不再进行input确认
        self.work_mode: Work_Mode = "ui"
        # 当前任务目录，用于指向本次构建任务的目录
        self.cur_task_dir: str = ""
        # 构建模式，默认dev，可选值：dev、test、release
        self.build_mode: str = "release"
        # 当前任务id，即 prod_name,req_date
        self.cur_task_id: str = ""
        # 打包机主机地址
        self.SERVER_HOST_URL: str = "http://192.168.189.243:5005"
        # 是否混淆
        self.is_obfuscated: bool = False

    @property
    def DISTRIBUTION_PATH(self):
        if self._distribution_path is None:
            self._distribution_path = os.getenv("DISTRIBUTION_PATH")
        return self._distribution_path

    @property
    def ANDROID_UNI_BASE_PATH(self):
        if self._android_uni_base_path is None:
            self._android_uni_base_path = os.getenv("ANDROID_UNI_BASE_PATH")
        return self._android_uni_base_path

    @property
    def APPS_DIRECTORY(self):
        if self._apps_directory is None:
            self._apps_directory = f"{self.ANDROID_UNI_BASE_PATH}/app/src/main/assets/apps"
        return self._apps_directory

    @property
    def ANDROID_MANIFEST_PATH(self):
        if self._android_manifest_path is None:
            self._android_manifest_path = (
                rf"{self.ANDROID_UNI_BASE_PATH}/app/src/main/AndroidManifest.xml"
            )
        return self._android_manifest_path

    @property
    def CONTROL_FILE_PATH(self):
        if self._control_file_path is None:
            self._control_file_path = (
                f"{self.ANDROID_UNI_BASE_PATH}/app/src/main/assets/data/dcloud_control.xml"
            )
        return self._control_file_path

    @property
    def BUILD_GRADLE_PATH(self):
        if self._build_gradle_path is None:
            self._build_gradle_path = f"{self.ANDROID_UNI_BASE_PATH}/app/build.gradle"
        return self._build_gradle_path

    @property
    def VERSIONS_TOML_PATH(self):
        if self._versions_toml_path is None:
            self._versions_toml_path = f"{self.ANDROID_UNI_BASE_PATH}/gradle/libs.versions.toml"
        return self._versions_toml_path

    @property
    def BUILD_RELEASE_OUTPUT_DIR(self):
        if self._build_release_output_dir is None:
            self._build_release_output_dir = (
                f"{self.ANDROID_UNI_BASE_PATH}/app/build/outputs/apk/release"
            )
        return self._build_release_output_dir

    @property
    def BUILD_DEBUG_OUTPUT_DIR(self):
        if self._build_debug_output_dir is None:
            self._build_debug_output_dir = (
                f"{self.ANDROID_UNI_BASE_PATH}/app/build/outputs/apk/debug"
            )
        return self._build_debug_output_dir

    @property
    def PROD_NAME(self):
        if self._prod_name is None:
            raise ValueError("未设置 PROD_NAME")
        return self._prod_name

    @PROD_NAME.setter
    def PROD_NAME(self, value):
        self._prod_name = value
        self._prod_branch = rf"prod_{value}"

    @property
    def PROD_BRANCH(self):
        if self._prod_branch is None:
            self._prod_branch = rf"prod_{self.PROD_NAME}"
        return self._prod_branch


# 创建全局配置实例
config = Config()
