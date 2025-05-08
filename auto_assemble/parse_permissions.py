import re
import xml.etree.ElementTree as ET

from common.types import PermissionsFeatures, ManifestPermissions

"""
文件名称: parse_permissions.py
作者: junerver
日期: 2025-03-19
描述: 这个脚本用于解析 Android Manifest 权限，并进行合并和过滤操作。

函数说明:
    _extract_permissions(xml_content): 解析 XML 代码块，提取 <uses-permission> 元素的 android:name 值作为 key，<uses-permission> 元素作为 value
    parse_manifest_permission(content): 解析包含默认权限、添加权限和移除权限的内容，返回一个字典
    merge_permissions(permissions): 合并 default 和 add 中的权限，并移除 del 里的权限
    parse_and_merge_permissions(content): 入口函数，解析包含默认权限、添加权限和移除权限的内容，返回一个字典
"""

__all__ = ["parse_and_merge_permissions"]

# Android 命名空间
namespaces = {"android": "http://schemas.android.com/apk/res/android"}


def _extract_permissions(xml_content: str) -> PermissionsFeatures:
    """
    解析 XML 代码块，提取 <uses-permission> 和 <uses-feature> 元素

    Args:
        xml_content: 包含 XML 代码块的文本
    Returns:
        dict: 一个字典，包含：
            - "permissions": {android:name -> <uses-permission> 元素}
            - "features": {android:name -> <uses-feature> 元素}
    """
    permissions: PermissionsFeatures = {"permissions": {}, "features": {}}
    try:
        # 确保 XML 结构正确
        wrapped_xml = f"<root xmlns:android='{namespaces['android']}'>{xml_content.strip()}</root>"
        root = ET.fromstring(wrapped_xml)

        # 提取 <uses-permission>
        for perm in root.findall(".//uses-permission"):
            name = perm.get(f"{{{namespaces['android']}}}name")
            if name:
                permissions["permissions"][name] = perm

        # 提取 <uses-feature>
        for feature in root.findall(".//uses-feature"):
            name = feature.get(f"{{{namespaces['android']}}}name")
            if name:
                permissions["features"][name] = feature

    except ET.ParseError as e:
        print("解析失败, 错误信息:", e)
    return permissions


def _parse_manifest_permission(permissions_content: str) -> ManifestPermissions:
    """
    解析出文档中的xml块，按照顺序排列，依次为default、add、del，对xml块进行解析，提取出<uses-permission> 和 <uses-feature> 元素

    Args:
        permissions_content: 包含 XML 代码块的文本

    Returns:
        dict: 一个字典，包含：
            - "default": 字典，包含：
                - "permissions": {android:name -> <uses-permission> 元素}
                - "features": {android:name -> <uses-feature> 元素}
            - "add": 字典，包含：
                - "permissions": {android:name -> <uses-permission> 元素}
                - "features": {android:name -> <uses-feature> 元素}
            - "del": 字典，包含：
                - "permissions": {android:name -> <uses-permission> 元素}
                - "features": {android:name -> <uses-feature> 元素}
    """
    sections: dict[str, str] = {"default": "", "add": "", "del": ""}
    # 修正正则匹配，确保提取完整 XML 代码块
    matches = re.findall(r"```xml\s*(.*?)\s*```", permissions_content, re.DOTALL)

    if len(matches) > 0:
        sections["default"] = matches[0]
    if len(matches) > 1:
        sections["add"] = matches[1]
    if len(matches) > 2:
        sections["del"] = matches[2]

    return {
        "default": _extract_permissions(sections["default"]),
        "add": _extract_permissions(sections["add"]),
        "del_": _extract_permissions(sections["del"]),
    }


def _merge_permissions(permissions: ManifestPermissions):
    """
    合并 default 和 add 中的权限，并移除 del 里的权限（包括 uses-permission 和 uses-feature），
    但移除的权限不是直接删除，而是添加 tools:node="remove" 属性。

    Args:
        permissions: 包含 "permissions" 和 "features" 的字典

    Returns:
        dict: {"permissions": 合并后的权限, "features": 合并后的特性}
    """
    merged = {
        "permissions": {
            key: ET.Element("uses-permission", {"android:name": key})
            for key in permissions["default"]["permissions"]
        },  # 复制 default 的 permissions
        "features": {
            key: ET.Element("uses-feature", {"android:name": key})
            for key in permissions["default"]["features"]
        },  # 复制 default 的 features
    }

    # 添加 add 里的权限和特性
    for key in permissions["add"]["permissions"]:
        merged["permissions"][key] = ET.Element(
            "uses-permission", {"android:name": key}
        )
    for key in permissions["add"]["features"]:
        merged["features"][key] = ET.Element("uses-feature", {"android:name": key})

    # 处理 del 里的权限和特性，不直接删除，而是添加 tools:node="remove"
    for del_key in permissions["del_"]["permissions"]:
        merged["permissions"][del_key] = ET.Element(
            "uses-permission", {"android:name": del_key, "tools:node": "remove"}
        )
    for del_key in permissions["del_"]["features"]:
        merged["features"][del_key] = ET.Element(
            "uses-feature", {"android:name": del_key, "tools:node": "remove"}
        )

    # 增加判断，如果最终的 merged["permissions"] 中包含 android.permission.ACCESS_FINE_LOCATION，则需要添加 android.permission.ACCESS_COARSE_LOCATION
    if "android.permission.ACCESS_FINE_LOCATION" in merged["permissions"]:
        merged["permissions"]["android.permission.ACCESS_COARSE_LOCATION"] = ET.Element(
            "uses-permission",
            {"android:name": "android.permission.ACCESS_COARSE_LOCATION"},
        )

    return merged


def parse_and_merge_permissions(permissions_content: str) -> dict:
    """
    解析包含默认权限、添加权限和移除权限的内容，返回一个字典

    Args:
        permissions_content: 包含 XML 代码块的文本

    Returns:
        dict: 一个字典，包含：
            - "permissions": 合并后的权限
            - "features": 合并后的特性
    """
    permissions = _parse_manifest_permission(permissions_content)
    merged_permissions = _merge_permissions(permissions)
    return merged_permissions


if __name__ == "__main__":
    # 示例输入
    content = """6. 提供 Android 基座需要添加、移除的权限列表，基座默认权限如下：

    ```xml
    <uses-feature android:name="android.hardware.Camera"/>
    <uses-permission android:name="android.permission.INTERNET" />
    <uses-permission android:name="android.permission.WRITE_EXTERNAL_STORAGE" />
    <uses-permission android:name="android.permission.ACCESS_FINE_LOCATION" />
    ```

    需要额外添加：

    ```xml
    <uses-feature android:name="android.hardware.camera.autofocus" />
    <uses-permission android:name="android.permission.CAMERA" />
    <uses-permission android:name="android.permission.READ_PHONE_STATE" />
    ```  

    需要移除：

    ```xml
    <uses-permission android:name="android.permission.READ_EXTERNAL_STORAGE" />
    ```  
    """

    # 解析权限
    _merged_permissions = parse_and_merge_permissions(content)

    print("\n合并后权限:")
    print(
        _merged_permissions["permissions"][
            "android.permission.READ_EXTERNAL_STORAGE"
        ].attrib
    )
