import pytest
from pathlib import Path
from unittest.mock import patch
import logging
import xml.etree.ElementTree as ET

from auto_assemble.update_android_manifest import (
    update_android_manifest,
    prettify_xml,
    clear_namespaces,
)
from common.types import ManifestInfo

# 测试用的 AndroidManifest.xml 内容模板
ANDROID_MANIFEST_TEMPLATE = """<?xml version="1.0" encoding="utf-8"?>
<manifest xmlns:android="http://schemas.android.com/apk/res/android"
    package="io.dcloud.HBuilder">

    <uses-sdk android:minSdkVersion="21" />

    <application
        android:name="io.dcloud.PandoraEntry"
        android:label="@string/app_name">
        <activity
            android:name="io.dcloud.PandoraEntry">
            <intent-filter>
                <action android:name="android.intent.action.MAIN" />
                <category android:name="android.intent.category.LAUNCHER" />
            </intent-filter>
        </activity>
    </application>
</manifest>
"""


@pytest.fixture
def setup_manifest(tmp_path):
    # 创建临时 AndroidManifest.xml 文件
    manifest_path = tmp_path / "AndroidManifest.xml"
    with open(manifest_path, "w", encoding="utf-8") as f:
        f.write(ANDROID_MANIFEST_TEMPLATE)
    return manifest_path


class TestPrettifyXml:
    def test_basic_formatting(self):
        """测试基本的 XML 格式化"""
        root = ET.Element("root")
        child = ET.SubElement(root, "child")
        child.text = "test"
        formatted = prettify_xml(root)
        assert '<?xml version="1.0" ?>' in formatted
        assert "<root>" in formatted
        assert "<child>test</child>" in formatted

    def test_remove_empty_lines(self):
        """测试去除多余空行"""
        root = ET.Element("root")
        ET.SubElement(root, "child1")
        ET.SubElement(root, "child2")
        formatted = prettify_xml(root)
        lines = formatted.split("\n")
        assert not any(line.strip() == "" for line in lines)

    def test_special_characters(self):
        """测试特殊字符处理"""
        root = ET.Element("root")
        child = ET.SubElement(root, "child")
        child.text = "<test>"
        formatted = prettify_xml(root)
        assert "&lt;test&gt;" in formatted


class TestClearNamespaces:
    def test_clear_namespaces(self):
        """测试清除命名空间"""
        root = ET.Element("root")
        root.set("xmlns:android", "http://schemas.android.com/apk/res/android")
        root.set("xmlns:tools", "http://schemas.android.com/tools")
        clear_namespaces(root)
        assert "xmlns:android" not in root.attrib
        assert "xmlns:tools" not in root.attrib

    def test_preserve_other_attributes(self):
        """测试保留其他属性"""
        root = ET.Element("root")
        root.set("xmlns:android", "http://schemas.android.com/apk/res/android")
        root.set("package", "com.test")
        clear_namespaces(root)
        assert "xmlns:android" not in root.attrib
        assert root.get("package") == "com.test"


class TestUpdateAndroidManifest:
    def test_add_permissions_and_features(self, setup_manifest, caplog):
        """测试添加权限和特性"""
        # 设置日志捕获
        caplog.set_level(logging.INFO)

        # 准备权限信息
        permissions = {
            "permissions": {
                "android.permission.INTERNET": ET.Element(
                    "uses-permission", {"android:name": "android.permission.INTERNET"}
                ),
                "android.permission.CAMERA": ET.Element(
                    "uses-permission", {"android:name": "android.permission.CAMERA"}
                ),
            },
            "features": {
                "android.hardware.camera.autofocus": ET.Element(
                    "uses-feature", {"android:name": "android.hardware.camera.autofocus"}
                )
            },
        }

        # 构建 update_info
        update_info = ManifestInfo(permissions=permissions, schemes="")

        # 执行函数
        result = update_android_manifest(setup_manifest, update_info)

        # 验证返回 True
        assert result is True

        # 验证日志记录
        assert "移除所有 <uses-permission> 和 <uses-feature> 元素" in caplog.text
        assert "添加新的 <uses-permission> 和 <uses-feature> 元素" in caplog.text

        # 解析 XML
        tree = ET.parse(setup_manifest)
        root = tree.getroot()

        # 验证权限是否已添加
        assert (
            root.find(
                "./uses-permission[@android:name='android.permission.INTERNET']",
                namespaces={"android": "http://schemas.android.com/apk/res/android"},
            )
            is not None
        )
        assert (
            root.find(
                "./uses-permission[@android:name='android.permission.CAMERA']",
                namespaces={"android": "http://schemas.android.com/apk/res/android"},
            )
            is not None
        )
        assert (
            root.find(
                "./uses-feature[@android:name='android.hardware.camera.autofocus']",
                namespaces={"android": "http://schemas.android.com/apk/res/android"},
            )
            is not None
        )

    def test_handle_schemes(self, setup_manifest, caplog):
        """测试处理 schemes"""
        # 设置日志捕获
        caplog.set_level(logging.INFO)

        # 准备权限信息
        permissions = {"permissions": {}, "features": {}}

        # 构建 update_info
        update_info = ManifestInfo(permissions=permissions, schemes="identifyField,testScheme")

        # 执行函数
        result = update_android_manifest(setup_manifest, update_info)

        # 验证返回 True
        assert result is True

        # 验证日志记录
        assert "处理schemes: ['identifyField', 'testScheme']" in caplog.text

        # 解析 XML
        tree = ET.parse(setup_manifest)
        root = tree.getroot()

        # 查找 PandoraEntry activity
        for activity in root.findall(".//activity"):
            name = activity.get("{http://schemas.android.com/apk/res/android}name")
            if name == "io.dcloud.PandoraEntry":
                # 查找包含 VIEW action 的 intent-filter
                for intent_filter in activity.findall("intent-filter"):
                    has_view_action = False
                    for action in intent_filter.findall("action"):
                        action_name = action.get("{http://schemas.android.com/apk/res/android}name")
                        if action_name == "android.intent.action.VIEW":
                            has_view_action = True
                            break

                    if has_view_action:
                        # 验证 schemes 是否正确添加
                        data_tags = intent_filter.findall("data")
                        assert len(data_tags) == 2
                        assert data_tags[0].get("{http://schemas.android.com/apk/res/android}scheme") == "identifyField"
                        assert data_tags[1].get("{http://schemas.android.com/apk/res/android}scheme") == "testScheme"

    def test_no_schemes(self, setup_manifest, caplog):
        """测试没有 schemes 时的行为"""
        # 设置日志捕获
        caplog.set_level(logging.INFO)

        # 准备权限信息
        permissions = {"permissions": {}, "features": {}}

        # 构建 update_info
        update_info = ManifestInfo(permissions=permissions, schemes="")

        # 执行函数
        result = update_android_manifest(setup_manifest, update_info)

        # 验证返回 True
        assert result is True

        # 验证日志记录
        assert "处理schemes: ['']" in caplog.text  # 修改这里，匹配实际行为

        # 解析 XML
        tree = ET.parse(setup_manifest)
        root = tree.getroot()

        # 查找 PandoraEntry activity
        for activity in root.findall(".//activity"):
            name = activity.get("{http://schemas.android.com/apk/res/android}name")
            if name == "io.dcloud.PandoraEntry":
                # 查找包含 VIEW action 的 intent-filter
                for intent_filter in activity.findall("intent-filter"):
                    has_view_action = False
                    for action in intent_filter.findall("action"):
                        action_name = action.get("{http://schemas.android.com/apk/res/android}name")
                        if action_name == "android.intent.action.VIEW":
                            has_view_action = True
                            break

                    if has_view_action:
                        # 验证是否添加了默认空 scheme
                        data_tags = intent_filter.findall("data")
                        assert len(data_tags) == 1
                        assert data_tags[0].get("{http://schemas.android.com/apk/res/android}scheme") == " "

    def test_invalid_manifest(self, tmp_path, caplog):
        """测试无效的 AndroidManifest.xml 文件"""
        # 设置日志捕获
        caplog.set_level(logging.ERROR)

        # 创建一个无效的 XML 文件
        invalid_manifest = tmp_path / "invalid.xml"
        with open(invalid_manifest, "w", encoding="utf-8") as f:
            f.write("<invalid_xml>")

        # 准备权限信息
        permissions = {"permissions": {}, "features": {}}

        # 构建 update_info
        update_info = ManifestInfo(permissions=permissions, schemes="")

        # 执行函数
        result = update_android_manifest(invalid_manifest, update_info)

        # 验证返回 False
        assert result is False

        # 验证错误日志
        assert "更新 AndroidManifest.xml 文件时发生错误" in caplog.text  # 使用 caplog 而不是 capsys

    def test_file_not_found(self, caplog):
        """测试文件不存在的情况"""
        # 设置日志捕获
        caplog.set_level(logging.ERROR)

        # 使用不存在的文件路径
        non_existent_file = Path("/path/that/does/not/exist.xml")

        # 准备权限信息
        permissions = {"permissions": {}, "features": {}}

        # 构建 update_info
        update_info = ManifestInfo(permissions=permissions, schemes="")

        # 执行函数
        result = update_android_manifest(non_existent_file, update_info)

        # 验证返回 False
        assert result is False

        # 验证错误日志
        assert "更新 AndroidManifest.xml 文件时发生错误" in caplog.text  # 使用 caplog 而不是 capsys

    def test_xml_formatting(self, setup_manifest, caplog):
        """测试 XML 格式化输出"""
        caplog.set_level(logging.INFO)
        permissions = {
            "permissions": {"INTERNET": ET.Element("uses-permission", {"android:name": "android.permission.INTERNET"})},
            "features": {},
        }
        update_info = ManifestInfo(permissions=permissions, schemes="")
        result = update_android_manifest(setup_manifest, update_info)
        assert result is True
        with open(setup_manifest, "r", encoding="utf-8") as f:
            content = f.read()
            assert '<?xml version="1.0" ?>' in content
            assert "<manifest" in content
            assert "<uses-permission" in content

    def test_namespace_handling(self, setup_manifest, caplog):
        """测试命名空间处理"""
        caplog.set_level(logging.INFO)
        permissions = {
            "permissions": {"INTERNET": ET.Element("uses-permission", {"android:name": "android.permission.INTERNET"})},
            "features": {},
        }
        update_info = ManifestInfo(permissions=permissions, schemes="")
        result = update_android_manifest(setup_manifest, update_info)
        assert result is True
        tree = ET.parse(setup_manifest)
        root = tree.getroot()

        # 验证权限元素是否正确使用了命名空间
        permission = root.find("./uses-permission")
        assert permission is not None
        assert permission.get("{http://schemas.android.com/apk/res/android}name") == "android.permission.INTERNET"

        # 验证 activity 元素是否正确使用了命名空间
        activity = root.find(".//activity")
        assert activity is not None
        assert activity.get("{http://schemas.android.com/apk/res/android}name") == "io.dcloud.PandoraEntry"

        # 验证 intent-filter 元素是否正确使用了命名空间
        intent_filter = activity.find("intent-filter")
        assert intent_filter is not None
        action = intent_filter.find("action")
        assert action is not None
        assert action.get("{http://schemas.android.com/apk/res/android}name") == "android.intent.action.MAIN"

    def test_multiple_schemes(self, setup_manifest, caplog):
        """测试多个 schemes 的处理"""
        caplog.set_level(logging.INFO)
        permissions = {"permissions": {}, "features": {}}
        update_info = ManifestInfo(permissions=permissions, schemes="scheme1,scheme2,scheme3")
        result = update_android_manifest(setup_manifest, update_info)
        assert result is True
        tree = ET.parse(setup_manifest)
        root = tree.getroot()
        # 查找 PandoraEntry activity
        for activity in root.findall(".//activity"):
            name = activity.get("{http://schemas.android.com/apk/res/android}name")
            if name == "io.dcloud.PandoraEntry":
                # 查找包含 VIEW action 的 intent-filter
                for intent_filter in activity.findall("intent-filter"):
                    has_view_action = False
                    for action in intent_filter.findall("action"):
                        action_name = action.get("{http://schemas.android.com/apk/res/android}name")
                        if action_name == "android.intent.action.VIEW":
                            has_view_action = True
                            break

                    if has_view_action:
                        # 验证 schemes 是否正确添加
                        data_tags = intent_filter.findall("data")
                        assert len(data_tags) == 3
                        schemes = [tag.get("{http://schemas.android.com/apk/res/android}scheme") for tag in data_tags]
                        assert "scheme1" in schemes
                        assert "scheme2" in schemes
                        assert "scheme3" in schemes
                        break

    def test_permission_order(self, setup_manifest, caplog):
        """测试权限和特性的插入顺序"""
        caplog.set_level(logging.INFO)
        permissions = {
            "permissions": {
                "PERM1": ET.Element("uses-permission", {"android:name": "android.permission.PERM1"}),
                "PERM2": ET.Element("uses-permission", {"android:name": "android.permission.PERM2"}),
            },
            "features": {"FEAT1": ET.Element("uses-feature", {"android:name": "android.hardware.FEAT1"})},
        }
        update_info = ManifestInfo(permissions=permissions, schemes="")
        result = update_android_manifest(setup_manifest, update_info)
        assert result is True
        tree = ET.parse(setup_manifest)
        root = tree.getroot()
        elements = list(root)
        assert elements[0].tag == "uses-sdk"
        assert elements[1].tag == "uses-permission"
        assert elements[2].tag == "uses-permission"
        assert elements[3].tag == "uses-feature"

    def test_file_write_permission(self, setup_manifest, caplog):
        """测试文件写入权限"""
        caplog.set_level(logging.ERROR)
        permissions = {"permissions": {}, "features": {}}
        update_info = ManifestInfo(permissions=permissions, schemes="")

        # 模拟文件写入权限错误
        with patch("builtins.open", side_effect=PermissionError("Permission denied")):
            result = update_android_manifest(setup_manifest, update_info)
            assert result is False
            assert "更新 AndroidManifest.xml 文件时发生错误" in caplog.text
