import logging
import xml.etree.ElementTree as ET
from xml.dom import minidom

from common.types import ManifestInfo


def prettify_xml(elem):
    """格式化 XML 并去除多余空行"""
    rough_string = ET.tostring(elem, encoding="utf-8")
    reparsed = minidom.parseString(rough_string)
    # 过滤掉多余的空行
    return "\n".join([line for line in reparsed.toprettyxml(indent="  ").splitlines() if line.strip()])


def clear_namespaces(root: ET.Element) -> None:
    """
    清除根元素上的所有命名空间声明

    Args:
        root: XML根元素
    """
    # 获取所有属性名
    attrs = list(root.attrib.keys())
    # 移除所有命名空间声明
    for attr in attrs:
        if attr.startswith("xmlns:"):
            del root.attrib[attr]


# Android 命名空间
namespaces = {
    "android": "http://schemas.android.com/apk/res/android",
    "tools": "http://schemas.android.com/tools",
    "app": "http://schemas.android.com/apk/res-auto",
}


def update_android_manifest(
    android_manifest_path: str,
    update_info: ManifestInfo,
    launch_activity: str = "io.dcloud.PandoraEntry",
) -> bool:
    """
    更新 AndroidManifest.xml 文件中的权限和特性（uses-permission 和 uses-feature）,
    并处理schemes

    Args:
        android_manifest_path: AndroidManifest.xml 文件的路径
        update_info: 更新信息，包含permissions和schemes
        launch_activity: 启动Activity，默认是io.dcloud.PandoraEntry

    Returns:
        bool: 更新成功返回 True，失败返回 False
    """
    # 备份原始文件
    # backup_path = os.path.join(
    #     os.path.dirname(android_manifest_path), "AndroidManifest_backup.xml"
    # )
    # 暂时不备份，因为git本身会追踪文件的修改
    # shutil.copy(android_manifest_path, backup_path)
    permissions = update_info["permissions"]
    # 注册schema在其它App中打开当前App，多个scheme使用','号分割，需要解析成数组，例如：test1,test2
    if "schemes" in update_info:
        logging.info(f"解析schemes: {update_info['schemes']}")
        schemes = update_info["schemes"].split(",")
    else:
        schemes = []

    try:
        # 定义 namespace
        for prefix, uri in namespaces.items():
            ET.register_namespace(prefix, uri)

        # 解析 XML
        parser = ET.XMLParser(target=ET.TreeBuilder())
        tree = ET.parse(android_manifest_path, parser)
        root = tree.getroot()

        # 先清除所有命名空间声明
        clear_namespaces(root)

        # 重新添加必要的命名空间声明
        root.set("xmlns:tools", namespaces["tools"])
        root.set("xmlns:app", namespaces["app"])

        # **移除所有 <uses-permission> 和 <uses-feature> 元素**
        for element in root.findall("./uses-permission") + root.findall("./uses-feature"):
            root.remove(element)
        logging.info("移除所有 <uses-permission> 和 <uses-feature> 元素")

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
        elements_to_insert = list(permissions["permissions"].values()) + list(permissions["features"].values())
        for element in reversed(elements_to_insert):  # 反向插入，确保顺序正确
            element.tail = "\n"  # 添加换行
            root.insert(insert_index, element)

        logging.info("添加新的 <uses-permission> 和 <uses-feature> 元素")

        # 处理schemes
        logging.info(f"处理schemes: {schemes}")
        # 查找PandoraEntry activity
        for activity in root.findall(".//activity"):
            # 使用正确的命名空间获取name属性
            name = activity.get(f"{{{namespaces['android']}}}name")
            if name == launch_activity:
                # 查找包含VIEW action的intent-filter
                for intent_filter in activity.findall("intent-filter"):
                    has_view_action = False
                    for action in intent_filter.findall("action"):
                        action_name = action.get(f"{{{namespaces['android']}}}name")
                        if action_name == "android.intent.action.VIEW":
                            has_view_action = True
                            break

                    if has_view_action:
                        # 移除现有的data标签
                        for data in intent_filter.findall("data"):
                            intent_filter.remove(data)

                        # 添加新的data标签
                        if schemes:
                            for scheme in schemes:
                                data = ET.Element("data")
                                data.set(f"{{{namespaces['android']}}}scheme", scheme.strip())
                                intent_filter.append(data)
                        else:
                            # 如果没有schemes，添加默认的空scheme
                            data = ET.Element("data")
                            data.set(f"{{{namespaces['android']}}}scheme", " ")
                            intent_filter.append(data)

                break

        # **使用 ElementTree 格式化 XML**
        formatted_xml = prettify_xml(root)
        with open(android_manifest_path, "w", encoding="utf-8") as f:
            f.write(formatted_xml)

        logging.info("写回文件")
        return True

    except Exception as e:
        logging.error(f"更新 AndroidManifest.xml 文件时发生错误: {e}")
        return False
