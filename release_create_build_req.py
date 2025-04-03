import os
import shutil

import PyInstaller.__main__


def build_exe():
    # 清理之前的构建文件
    if os.path.exists("build"):
        shutil.rmtree("build")
    if os.path.exists("dist"):
        shutil.rmtree("dist")

    # PyInstaller参数
    params = [
        "auto_assemble/create_build_req.py",  # 主脚本
        "--name=create_build_req",  # 生成的exe名称
        "--onefile",  # 打包成单个文件
        "--add-data=auto_assemble;auto_assemble",  # 添加模块目录
        "--add-data=.env;.",  # 添加.env文件
        "--clean",  # 清理临时文件
        "--noconfirm",  # 不确认覆盖
    ]

    # 执行打包
    PyInstaller.__main__.run(params)

    print("打包完成！exe文件位于 dist 目录中。")


if __name__ == "__main__":
    """
    构建前端项目打包请求小工具
    """
    build_exe()
