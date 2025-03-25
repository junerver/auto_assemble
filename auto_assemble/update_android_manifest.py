import logging
import os
import xml.etree.ElementTree as ET
from xml.dom import minidom


def prettify_xml(elem):
    """格式化 XML 并去除多余空行"""
    rough_string = ET.tostring(elem, encoding="utf-8")
    reparsed = minidom.parseString(rough_string)
    # 过滤掉多余的空行
    return "\n".join(
        [line for line in reparsed.toprettyxml(indent="  ").splitlines() if line.strip()]
    )


def update_android_manifest(android_manifest_path: str, permissions: dict) -> bool:
    """
    更新 AndroidManifest.xml 文件中的权限和特性（uses-permission 和 uses-feature）

    Args:
        android_manifest_path: AndroidManifest.xml 文件的路径
        permissions: 包含 "permissions" 和 "features" 的字典

    Returns:
        bool: 更新成功返回 True，失败返回 False
    """
    # 备份原始文件
    backup_path = os.path.join(os.path.dirname(android_manifest_path), "AndroidManifest_backup.xml")
    # 暂时不备份，因为git本身会追踪文件的修改
    # shutil.copy(android_manifest_path, backup_path)

    try:
        # 定义 namespace
        ET.register_namespace("android", "http://schemas.android.com/apk/res/android")
        ET.register_namespace("tools", "http://schemas.android.com/tools")
        ET.register_namespace("app", "http://schemas.android.com/apk/res-auto")

        # 解析 XML
        parser = ET.XMLParser(target=ET.TreeBuilder())
        tree = ET.parse(android_manifest_path, parser)
        root = tree.getroot()

        # **移除所有 <uses-permission> 和 <uses-feature> 元素**
        for element in root.findall("./uses-permission") + root.findall("./uses-feature"):
            root.remove(element)
        logging.info(f"移除所有 <uses-permission> 和 <uses-feature> 元素")

        # **找到正确的插入位置**
        insert_index = 0  # 默认插入到 <manifest> 开头
        for idx, child in enumerate(root):
            if child.tag == "uses-sdk":  # 在 <uses-sdk> 之后插入
                insert_index = idx + 1
                break
            elif child.tag == "application":  # 在 <application> 之前插入
                insert_index = idx
                break

        # **按顺序插入新的权限**
        elements_to_insert = list(permissions["permissions"].values()) + list(
            permissions["features"].values()
        )
        for element in reversed(elements_to_insert):  # 反向插入，确保顺序正确
            element.tail = "\n"  # 添加换行
            root.insert(insert_index, element)

        logging.info(f"添加新的 <uses-permission> 和 <uses-feature> 元素")

        # **使用 minidom 重新格式化 XML**
        formatted_xml = prettify_xml(root)
        with open(android_manifest_path, "w", encoding="utf-8") as f:
            f.write(formatted_xml)

        logging.info(f"写回文件")
        return True

    except Exception as e:
        logging.error(f"更新 AndroidManifest.xml 文件时发生错误: {e}")
        return False
