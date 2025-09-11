import os
import sys
import shutil
import subprocess
from pathlib import Path


def is_python_file(file_path):
    """
    判断文件是否为Python文件

    Args:
        file_path: 文件路径

    Returns:
        bool: 是否为Python文件
    """
    return file_path.endswith(".py")


def obfuscate_with_pyarmor(src_dir, output_dir, expire=None, inside=True, packages=None):
    """
    使用pyarmor对源代码目录进行混淆

    Args:
        src_dir: 源代码目录
        output_dir: 输出目录
        expire: 过期时间，可以是天数或日期字符串
        inside: 是否将运行时文件放在包内部

    Returns:
        bool: 混淆是否成功
    """
    try:
        # 确保输出目录存在
        os.makedirs(output_dir, exist_ok=True)

        # 构建基本命令
        cmd = [
            "pyarmor",
            "gen",
            "-r",  # 递归处理子目录
            "-O",
            output_dir,  # 输出目录
        ]

        # 如果指定了包列表，则只混淆这些包
        if packages:
            # 将包列表转换为包含路径
            package_paths = [os.path.join(src_dir, pkg) for pkg in packages]
            # 检查这些路径是否存在
            valid_paths = [p for p in package_paths if os.path.exists(p) and os.path.isdir(p)]
            if not valid_paths:
                print(f"⚠️ 警告: 未找到指定的包: {packages}")
                return False
            # 修改命令，只处理指定的包
            cmd = [
                "pyarmor",
                "gen",
                "-O",
                output_dir,  # 输出目录
            ]

        # 添加内部运行时选项
        if inside:
            cmd.append("-i")

        # 添加过期时间选项
        if expire:
            cmd.extend(["-e", str(expire)])

        # 添加源目录或包路径
        if packages:
            # 添加所有有效的包路径
            cmd.extend(valid_paths)
        else:
            # 添加整个源目录
            cmd.append(src_dir)

        print(f"🔒 正在使用pyarmor混淆代码: {' '.join(cmd)}")
        subprocess.run(cmd, check=True, capture_output=True, text=True)
        print("✅ 代码混淆成功!")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ 混淆代码时出错: {e}")
        print(f"错误输出: {e.stderr}")
        return False
    except Exception as e:
        print(f"❌ 发生未知错误: {e}")
        return False


def clean_extra_directories(output_dir, src_dir_name):
    """
    清理输出目录中的多余目录，只保留src目录、指定的包目录和pyarmor运行时目录

    Args:
        output_dir: 输出目录
        src_dir_name: 源目录名称

    Returns:
        int: 清理的目录数量
    """
    count = 0
    # 需要保留的目录名前缀列表
    keep_prefixes = [
        "pyarmor_runtime",  # PyArmor运行时目录
    ]

    # 需要保留的包目录
    keep_packages = [
        "auto_assemble",
        "webhook",
        "fork_task",
        "common",
    ]

    # 获取输出目录中的所有子目录
    try:
        items = os.listdir(output_dir)
        for item in items:
            item_path = os.path.join(output_dir, item)

            # 如果不是目录，跳过
            if not os.path.isdir(item_path):
                continue

            # 如果是src目录，保留
            if item == src_dir_name:
                continue

            # 检查是否是需要保留的目录前缀
            should_keep = False
            for prefix in keep_prefixes:
                if item.startswith(prefix):
                    should_keep = True
                    break

            # 检查是否是需要保留的包目录
            if not should_keep:
                for pkg in keep_packages:
                    if item == pkg:
                        should_keep = True
                        break

            # 如果不需要保留，则删除
            if not should_keep:
                print(f"🧹 清理多余目录: {item_path}")
                shutil.rmtree(item_path)
                count += 1
    except Exception as e:
        print(f"⚠️ 清理多余目录时出错: {e}")

    return count


def verify_obfuscation_result(output_dir):
    """
    验证混淆结果是否成功

    Args:
        output_dir: 输出目录

    Returns:
        bool: 验证是否通过
    """
    # 检查输出目录是否存在
    if not os.path.exists(output_dir):
        print(f"❌ 输出目录不存在: {output_dir}")
        return False

    # 检查是否存在src子目录，如果存在，则使用它作为验证目录
    src_dir_name = "src"
    src_in_output = os.path.join(output_dir, src_dir_name)
    verify_dir = src_in_output if os.path.exists(src_in_output) and os.path.isdir(src_in_output) else output_dir

    print(f"🔍 验证目录: {verify_dir}")

    # 检查是否有Python文件生成
    python_files = []
    for root, _, files in os.walk(verify_dir):
        for file in files:
            if file.endswith(".py"):
                python_files.append(os.path.join(root, file))

    if not python_files:
        print("❌ 未找到混淆后的Python文件")
        return False

    # 检查是否有pyarmor运行时文件
    runtime_found = False
    for root, dirs, _ in os.walk(verify_dir):
        for dir_name in dirs:
            if dir_name.startswith("pyarmor_runtime"):
                runtime_found = True
                break
        if runtime_found:
            break

    if not runtime_found:
        print("❌ 未找到PyArmor运行时文件")
        return False

    # 检查混淆后的Python文件内容
    for py_file in python_files[:1]:  # 只检查第一个文件
        try:
            with open(py_file, "r", encoding="utf-8") as f:
                content = f.read()
                if "__pyarmor__" not in content:
                    print(f"❌ 文件未被正确混淆: {py_file}")
                    return False
        except Exception as e:
            print(f"❌ 读取混淆文件时出错: {e}")
            return False

    print("✅ 验证通过: 文件已成功混淆")
    return True


def should_ignore_directory(dir_path):
    """
    判断目录是否应该被忽略

    Args:
        dir_path: 目录路径

    Returns:
        bool: 是否应该忽略该目录
    """
    # 需要忽略的目录名列表
    ignore_dirs = [
        "__pycache__",  # Python缓存目录
        ".egg-info",  # Python包信息目录
        ".pytest_cache",  # Pytest缓存目录
        ".mypy_cache",  # MyPy缓存目录
        ".ruff_cache",  # Ruff缓存目录
        ".coverage",  # 覆盖率报告目录
        ".tox",  # Tox测试目录
        ".venv",  # 虚拟环境目录
        "venv",  # 虚拟环境目录
        "env",  # 虚拟环境目录
        "build",  # 构建目录
        "dist",  # 分发目录
        "node_modules",  # Node.js模块目录
    ]

    dir_name = os.path.basename(dir_path)

    # 检查目录名是否在忽略列表中
    if dir_name in ignore_dirs:
        return True

    # 检查目录名是否以.egg-info结尾
    if dir_name.endswith(".egg-info"):
        return True

    return False


def copy_non_python_files(src_dir, output_dir, packages=None):
    """
    复制非Python文件到输出目录，忽略特定的目录如__pycache__和.egg-info

    Args:
        src_dir: 源代码目录
        output_dir: 输出目录

    Returns:
        int: 复制的文件数量
    """
    count = 0
    src_path = Path(src_dir)
    Path(output_dir)

    # 确保输出目录存在
    os.makedirs(output_dir, exist_ok=True)

    print("📋 正在复制非Python文件...")

    # 只处理src_dir目录内的文件，不处理外部文件
    for root, dirs, files in os.walk(src_dir):
        # 确保当前目录是src_dir的子目录
        if not str(Path(root)).startswith(str(src_path)):
            continue

        # 如果指定了包列表，则只处理这些包
        if packages:
            # 获取相对于src_dir的路径
            rel_path = os.path.relpath(root, src_dir)
            # 检查当前目录是否属于指定的包
            is_in_package = False
            for pkg in packages:
                # 检查当前目录是否是指定包或其子目录
                if rel_path == pkg or rel_path.startswith(pkg + os.sep):
                    is_in_package = True
                    break
            # 如果不在指定的包中，跳过
            if not is_in_package:
                continue

        # 从dirs列表中移除应该忽略的目录，这样os.walk就不会进入这些目录
        dirs[:] = [d for d in dirs if not should_ignore_directory(os.path.join(root, d))]

        for file in files:
            file_path = os.path.join(root, file)

            # 跳过Python文件，因为它们已经被pyarmor处理
            if is_python_file(file_path):
                continue

            # 计算相对路径，以便在输出目录中创建相同的结构
            rel_path = os.path.relpath(file_path, src_dir)
            dest_path = os.path.join(output_dir, rel_path)

            # 确保目标目录存在
            os.makedirs(os.path.dirname(dest_path), exist_ok=True)

            # 复制文件
            shutil.copy2(file_path, dest_path)
            count += 1

    print(f"✅ 已复制 {count} 个非Python文件")
    return count


def main():
    """
    使用pyarmor混淆指定的Python包并保留非Python文件

    固定混淆以下包:
        - auto_assemble
        - webhook
        - fork_task
        - common

    源目录: ./src
    输出目录: ./dist
    """
    # 固定的源目录和输出目录
    src_dir = os.path.abspath("src")
    output_dir = os.path.abspath("dist")

    # 固定的包列表
    package_list = ["auto_assemble", "webhook", "fork_task", "common"]
    print(f"📦 将只混淆以下包: {', '.join(package_list)}")

    # 检查源目录是否存在
    if not os.path.exists(src_dir):
        print(f"❌ 错误: 源目录 '{src_dir}' 不存在!")
        return 1

    # 清理输出目录
    if os.path.exists(output_dir):
        # 检查是否存在src子目录，如果存在，只清理该子目录
        src_in_output = os.path.join(output_dir, os.path.basename(src_dir))
        if os.path.exists(src_in_output) and os.path.isdir(src_in_output):
            print(f"🧹 清理输出子目录: {src_in_output}")
            shutil.rmtree(src_in_output)
        else:
            # 如果没有找到src子目录，则清理整个输出目录
            print(f"🧹 清理输出目录: {output_dir}")
            shutil.rmtree(output_dir)

    # 创建输出目录
    os.makedirs(output_dir, exist_ok=True)

    # 使用pyarmor混淆Python代码
    if not obfuscate_with_pyarmor(src_dir, output_dir, expire=None, inside=True, packages=package_list):
        return 1

    # 复制非Python文件到相同的输出目录
    # 注意：pyarmor可能会将文件输出到output_dir/src目录下，而不是直接输出到output_dir
    # 检查是否存在output_dir/src目录，如果存在，则将非Python文件复制到该目录
    src_in_output = os.path.join(output_dir, os.path.basename(src_dir))
    if os.path.exists(src_in_output) and os.path.isdir(src_in_output):
        print(f"📂 检测到混淆输出在 {src_in_output} 目录下，将非Python文件复制到该目录")
        copy_non_python_files(src_dir, src_in_output, packages=package_list)
    else:
        # 如果没有找到output_dir/src目录，则直接复制到output_dir
        copy_non_python_files(src_dir, output_dir, packages=package_list)

    # 验证混淆结果
    if verify_obfuscation_result(output_dir):
        # 清理dist目录下可能存在的多余目录（由于之前的bug可能产生的）
        clean_extra_directories(output_dir, os.path.basename(src_dir))
        print(f"🎉 完成! 混淆后的代码已输出到: {output_dir}")
        return 0
    else:
        print(f"⚠️ 警告: 混淆可能未完全成功，请检查输出目录: {output_dir}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
