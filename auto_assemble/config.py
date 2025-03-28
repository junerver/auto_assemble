import os
from typing import Literal

from dotenv import load_dotenv

load_dotenv()

Work_Mode = Literal["ui", "cli"]


class Config:
    def __init__(self):
        # 应用分发资源包目录
        self.DISTRIBUTION_PATH = os.getenv("DISTRIBUTION_PATH")
        # Android基座的项目目录
        self.ANDROID_UNI_BASE_PATH = os.getenv("ANDROID_UNI_BASE_PATH")

        # UniApp的资源包目录
        self.APPS_DIRECTORY = rf"{self.ANDROID_UNI_BASE_PATH}\app\src\main\assets\apps"
        # 应用的AndroidManifest.xml文件路径
        self.ANDROID_MANIFEST_PATH = (
            rf"{self.ANDROID_UNI_BASE_PATH}\app\src\main\AndroidManifest.xml"
        )
        # UniApp的 dcloud_control.xml 文件位置
        self.CONTROL_FILE_PATH = (
            rf"{self.ANDROID_UNI_BASE_PATH}\app\src\main\assets\data\dcloud_control.xml"
        )
        # 应用的build.gradle文件路径
        self.BUILD_GRADLE_PATH = rf"{self.ANDROID_UNI_BASE_PATH}\app\build.gradle"
        # 应用的version.toml文件路径
        self.VERSIONS_TOML_PATH = rf"{self.ANDROID_UNI_BASE_PATH}\gradle\libs.versions.toml"
        # 日志文件路径
        self.LOG_FILE = os.path.join(os.getcwd(), "auto_assemble.log")

        # 构建输出配置
        self.BUILD_RELEASE_OUTPUT_DIR = os.path.join(
            self.ANDROID_UNI_BASE_PATH, "app", "build", "outputs", "apk", "release"
        )
        self.BUILD_DEBUG_OUTPUT_DIR = os.path.join(
            self.ANDROID_UNI_BASE_PATH, "app", "build", "outputs", "apk", "debug"
        )

        # Git相关配置
        self.PROD_BRANCH = rf"prod_{os.getenv('PROD_NAME')}"
        self.PROD_DIR = os.getenv("PROD_NAME")

        # 应用配置
        self._uni_app_id = None
        # Git提交信息
        self.last_commit_message = ""
        # 工作模式：ui 或 cli , 默认ui，ui模式下需要用户确认，cli 模式下通过 --fn 直接指定功能序号，不再进行input确认
        self.work_mode: Work_Mode = "ui"

    @property
    def UNI_APP_ID(self):
        return self._uni_app_id

    @UNI_APP_ID.setter
    def UNI_APP_ID(self, value):
        self._uni_app_id = value


# 创建全局配置实例
config = Config()
