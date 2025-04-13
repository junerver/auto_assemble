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
        "cbr/__main__.py",  # 主脚本
        "--name=create_build_req",  # 生成的exe名称
        "--onefile",  # 打包成单个文件
        "--add-data=auto_assemble;auto_assemble",  # 添加模块目录
        "--add-data=cbr;cbr",  # 添加cbr模块目录
        "--clean",  # 清理临时文件
        "--noconfirm",  # 不确认覆盖
    ]

    # 执行打包
    PyInstaller.__main__.run(params)

    print("打包完成！exe文件位于 dist 目录中。")


# 复制文件到 release 目录
def copy_to_release(exe_name="create_build_req"):
    """将打包好的文件复制到 release 目录"""
    release_dir = r"D:\dev\identify_field\app-distribution\.build_req"
    if not os.path.exists(release_dir):
        os.makedirs(release_dir)
        print(f"📁 创建 {release_dir} 目录")

    src_path = f"dist/{exe_name}.exe"
    dst_path = f"{release_dir}/{exe_name}.exe"

    if os.path.exists(src_path):
        shutil.copy2(src_path, dst_path)
        print(f"📋 已复制到 {dst_path}")
    else:
        print(f"❌ 错误：源文件 {src_path} 不存在")


if __name__ == "__main__":
    """
    构建前端项目打包请求小工具
    """
    build_exe()
    copy_to_release()
