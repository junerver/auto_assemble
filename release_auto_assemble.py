import os
import shutil
import subprocess

import toml


# 读取 pyproject.toml 信息
def get_metadata():
    """解析 pyproject.toml 并获取项目信息"""
    with open("pyproject.toml", "r", encoding="utf-8") as f:
        data = toml.load(f)

    project = data["project"]

    return {
        "version": tuple(map(int, project["version"].split("."))),  # 转换为 (x, y, z, 0) 形式
        "product_name": project["name"],
        "description": project.get("description", ""),
        "author": (project["authors"][0]["name"] if "authors" in project and project["authors"] else ""),
        "license": project["license"]["text"] if "license" in project else "MIT",
    }


# 生成 PyInstaller 需要的 version.txt
def generate_version_file(metadata):
    """生成 version.txt 以供 PyInstaller 使用"""
    version_txt = f"""
VSVersionInfo(
    ffi=FixedFileInfo(
        filevers={metadata["version"] + (0,)},  # 1.2.3 → (1,2,3,0)
        prodvers={metadata["version"] + (0,)},
        mask=0x3f,
        flags=0x0,
        OS=0x40004,
        fileType=0x1,
        subtype=0x0,
        date=(0, 0)
    ),
    kids=[
        StringFileInfo([
            StringTable(
                '040904B0',
                [StringStruct('CompanyName', '{metadata["author"]}'),
                 StringStruct('FileDescription', '{metadata["description"]}'),
                 StringStruct('FileVersion', '{metadata["version"]}'),
                 StringStruct('ProductVersion', '{metadata["version"]}'),
                 StringStruct('ProductName', '{metadata["product_name"]}'),
                 StringStruct('LegalCopyright', '{metadata["license"]}')])
        ]),
        VarFileInfo([VarStruct('Translation', [1033, 1200])])
    ]
)
    """
    with open("version.txt", "w", encoding="utf-8") as f:
        f.write(version_txt.strip())
    print("✅ 生成 version.txt 成功！")


# 清理旧的 build/ dist/ 目录
def clean_old_builds():
    """删除旧的 dist 和 build 目录"""
    for folder in ["build", "dist"]:
        if os.path.exists(folder):
            shutil.rmtree(folder)
            print(f"🗑️ 已删除 {folder}/ 目录")


# 运行 PyInstaller 进行打包
def run_pyinstaller(metadata):
    """运行 PyInstaller 打包"""
    version_str = ".".join(map(str, metadata["version"]))
    exe_name = f"{metadata['product_name']}({version_str})"
    cmd = [
        "pyinstaller",
        "--clean",
        "--onefile",
        f"--name={exe_name}",
        "--version-file=version.txt",
        "auto_assemble/__main__.py",
    ]

    print("🚀 开始打包...")
    subprocess.run(cmd, check=True)
    print(f"🎉 打包完成！可执行文件路径：dist/{exe_name}.exe")
    return exe_name


# 复制文件到 release 目录
def copy_to_release(exe_name):
    """将打包好的文件复制到 release 目录"""
    release_dir = "release"
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


# 显示生成的 exe 版本信息
def check_exe_version(metadata):
    """检查 .exe 的版本信息"""
    exe_path = f"dist/{metadata['product_name']}.exe"
    if os.path.exists(exe_path):
        print("🔍 检查 EXE 版本信息...")
        subprocess.run(["powershell", "-Command", f'(Get-Item "{exe_path}").VersionInfo'])


# 主流程
if __name__ == "__main__":
    print("📦 读取 pyproject.toml...")
    metadata = get_metadata()

    print("📝 生成 version.txt...")
    generate_version_file(metadata)

    print("🧹 清理旧的打包文件...")
    clean_old_builds()

    print("🛠️ 开始打包...")
    exe_name = run_pyinstaller(metadata)

    print("🔍 验证打包结果...")
    check_exe_version(metadata)

    print("📋 复制到 release 目录...")
    copy_to_release(exe_name)

    print("✅ 打包流程完成！")
