import unittest
from pathlib import Path
from unittest.mock import mock_open, patch
import xml.etree.ElementTree as ET

from cbr.create_readme_file import create_readme_file
from common.const import DEFAULT_PERMISSIONS
from common.types import ManifestInfo


class TestCreateReadmeFile(unittest.TestCase):
    """测试 create_readme_file 函数"""

    @patch("builtins.open", new_callable=mock_open)
    def test_create_readme_file_success(self, mock_file):
        """测试成功创建 README 文件"""
        # 设置测试数据
        req_dir = Path("/test/req")
        manifest_info = ManifestInfo(
            hbx_version="4.45",
            version_name="1.0.0",
            version_code="1",
            uniapp_id="test_app_id",
            uniapp_key="test_key",
            third_party_config={"test_vendor": {"key": "value"}},
            permissions_content=DEFAULT_PERMISSIONS,
            modules=["test-module"],
            abi_filters='"armeabi-v7a", "arm64-v8a"',
            schemes="test1,test2",
        )

        # 执行测试
        create_readme_file(req_dir, manifest_info)

        # 验证文件操作
        expected_path = req_dir / "README.md"
        mock_file.assert_called_once_with(expected_path, "w", encoding="utf-8")

        # 验证写入内容
        written_content = "".join(call.args[0] for call in mock_file.return_value.write.call_args_list)

        # 检查关键内容是否存在
        self.assertIn("# 打包要求", written_content)
        self.assertIn("HBuilderX 版本：`4.45`", written_content)
        self.assertIn("版本名称 versionName：`1.0.0`", written_content)
        self.assertIn("版本号 versionCode：`1`", written_content)
        self.assertIn("Uniapp App ID：`test_app_id`", written_content)
        self.assertIn("Uniapp App key：`test_key`", written_content)
        self.assertIn('AbiFilters：`"armeabi-v7a", "arm64-v8a"`', written_content)
        self.assertIn("UrlSchemes：`test1,test2`", written_content)
        self.assertIn(DEFAULT_PERMISSIONS, written_content)

    @patch("builtins.open", new_callable=mock_open)
    def test_create_readme_file_empty_values(self, mock_file):
        """测试使用空值创建 README 文件"""
        # 设置测试数据
        req_dir = Path("/test/req")
        manifest_info = ManifestInfo(
            hbx_version="",
            version_name="",
            version_code="",
            uniapp_id="",
            uniapp_key="",
            third_party_config={},
            permissions_content="",
            modules=[],
            abi_filters="",
            schemes="",
        )

        # 执行测试
        create_readme_file(req_dir, manifest_info)

        # 验证文件操作
        expected_path = req_dir / "README.md"
        mock_file.assert_called_once_with(expected_path, "w", encoding="utf-8")

        # 验证写入内容包含基本结构
        written_content = "".join(call.args[0] for call in mock_file.return_value.write.call_args_list)
        self.assertIn("# 打包要求", written_content)
        self.assertIn("HBuilderX 版本：``", written_content)

    @patch("builtins.open", new_callable=mock_open)
    def test_create_readme_file_partial_data(self, mock_file):
        """测试部分字段有数据的情况"""
        req_dir = Path("/test/req")
        manifest_info = ManifestInfo(
            hbx_version="4.45",
            version_name="1.0.0",
            version_code="1",
            uniapp_id="test_app_id",
            uniapp_key="test_key",
            third_party_config={},  # 空的第三方配置
            permissions_content=DEFAULT_PERMISSIONS,
            modules=["test-module"],  # 有模块但无第三方配置
            abi_filters='"armeabi-v7a"',
            schemes="test1",
        )

        create_readme_file(req_dir, manifest_info)

        written_content = "".join(call.args[0] for call in mock_file.return_value.write.call_args_list)

        # 验证模块信息存在
        self.assertIn("9. 模块信息：", written_content)
        self.assertIn("- test-module", written_content)

        # 验证第三方配置不存在（因为为空）
        self.assertNotIn("10. 第三方平台配置信息：", written_content)

    @patch("builtins.open", new_callable=mock_open)
    def test_create_readme_file_only_third_party_config(self, mock_file):
        """测试只有第三方配置没有模块的情况"""
        req_dir = Path("/test/req")
        manifest_info = ManifestInfo(
            hbx_version="4.45",
            version_name="1.0.0",
            version_code="1",
            uniapp_id="test_app_id",
            uniapp_key="test_key",
            third_party_config={"wechat": {"appid": "wx123456", "secret": "secret123"}},
            permissions_content=DEFAULT_PERMISSIONS,
            modules=[],  # 空模块
            abi_filters='"arm64-v8a"',
            schemes="",
        )

        create_readme_file(req_dir, manifest_info)

        written_content = "".join(call.args[0] for call in mock_file.return_value.write.call_args_list)

        # 验证模块信息不存在（因为为空）
        self.assertNotIn("9. 模块信息：", written_content)

        # 验证第三方配置存在
        self.assertIn("10. 第三方平台配置信息：", written_content)
        self.assertIn("wechat:", written_content)
        self.assertIn("appid: wx123456", written_content)
        self.assertIn("secret: secret123", written_content)

    @patch("cbr.create_readme_file.logging")
    @patch("builtins.open", new_callable=mock_open)
    def test_create_readme_file_logging(self, mock_file, mock_logging):
        """测试日志记录功能"""
        req_dir = Path("/test/req")
        manifest_info = ManifestInfo(
            hbx_version="4.45",
            version_name="1.0.0",
            version_code="1",
            uniapp_id="test_app_id",
            uniapp_key="test_key",
            third_party_config={},
            permissions={},
            permissions_content=DEFAULT_PERMISSIONS,
            modules=[],
            abi_filters="",
            schemes="",
        )

        create_readme_file(req_dir, manifest_info)

        # 验证日志记录
        expected_path = req_dir / "README.md"
        mock_logging.info.assert_called_once_with(f"已创建README.md文件：{expected_path}")

    @patch("builtins.open")
    def test_create_readme_file_write_error(self, mock_open_func):
        """测试文件写入错误的情况"""
        req_dir = Path("/test/req")
        manifest_info = ManifestInfo(
            hbx_version="4.45",
            version_name="1.0.0",
            version_code="1",
            uniapp_id="test_app_id",
            uniapp_key="test_key",
            third_party_config={},
            permissions={},
            permissions_content=DEFAULT_PERMISSIONS,
            modules=[],
            abi_filters="",
            schemes="",
        )

        # 模拟权限错误
        mock_open_func.side_effect = PermissionError("Permission denied")

        # 验证抛出异常
        with self.assertRaises(PermissionError):
            create_readme_file(req_dir, manifest_info)

    @patch("builtins.open", new_callable=mock_open)
    def test_create_readme_file_special_characters(self, mock_file):
        """测试包含特殊字符的情况"""
        req_dir = Path("/test/req")
        manifest_info = ManifestInfo(
            hbx_version="4.45 & special",
            version_name="1.0.0-beta`test`",
            version_code="1",
            uniapp_id="test_app_id<script>",
            uniapp_key='test_key"quoted"',
            third_party_config={"platform*": {"key&": "value<>"}},
            permissions={
                "permissions": {
                    "android.permission.INTERNET": ET.Element(
                        "uses-permission", {"android:name": "android.permission.INTERNET"}
                    ),
                }
            },
            permissions_content=DEFAULT_PERMISSIONS,
            modules=["test-module*special"],
            abi_filters='"armeabi-v7a", "arm64-v8a"',
            schemes="test1,test2",
        )

        create_readme_file(req_dir, manifest_info)

        written_content = "".join(call.args[0] for call in mock_file.return_value.write.call_args_list)

        # 验证特殊字符被正确处理
        self.assertIn("HBuilderX 版本：`4.45 & special`", written_content)
        self.assertIn("版本名称 versionName：`1.0.0-beta`test``", written_content)
        self.assertIn("Uniapp App ID：`test_app_id<script>`", written_content)
        self.assertIn('Uniapp App key：`test_key"quoted"`', written_content)
        self.assertIn("- test-module*special", written_content)
        self.assertIn("platform*:", written_content)
        self.assertIn("key&: value<>", written_content)

    @patch("builtins.open", new_callable=mock_open)
    def test_create_readme_file_large_data(self, mock_file):
        """测试大量数据的情况"""
        req_dir = Path("/test/req")

        # 创建大量模块
        large_modules = [f"module-{i}" for i in range(50)]

        # 创建大量第三方配置
        large_third_party_config = {
            f"platform-{i}": {f"key-{j}": f"value-{i}-{j}" for j in range(10)} for i in range(10)
        }

        manifest_info = ManifestInfo(
            hbx_version="4.45",
            version_name="1.0.0",
            version_code="1",
            uniapp_id="test_app_id",
            uniapp_key="test_key",
            third_party_config=large_third_party_config,
            permissions={
                "permissions": {
                    "android.permission.INTERNET": ET.Element(
                        "uses-permission", {"android:name": "android.permission.INTERNET"}
                    ),
                }
            },
            permissions_content=DEFAULT_PERMISSIONS,
            modules=large_modules,
            abi_filters='"armeabi-v7a", "arm64-v8a"',
            schemes="test1,test2",
        )

        create_readme_file(req_dir, manifest_info)

        written_content = "".join(call.args[0] for call in mock_file.return_value.write.call_args_list)

        # 验证大量数据被正确处理
        self.assertIn("9. 模块信息：", written_content)
        self.assertIn("- module-0", written_content)
        self.assertIn("- module-49", written_content)

        self.assertIn("10. 第三方平台配置信息：", written_content)
        self.assertIn("platform-0:", written_content)
        self.assertIn("platform-9:", written_content)
        self.assertIn("key-0: value-0-0", written_content)
        self.assertIn("key-9: value-9-9", written_content)

    @patch("builtins.open", new_callable=mock_open)
    def test_create_readme_file_none_values(self, mock_file):
        """测试包含 None 值的边缘情况"""
        req_dir = Path("/test/req")
        manifest_info = ManifestInfo(
            hbx_version=None,
            version_name=None,
            version_code=None,
            uniapp_id=None,
            uniapp_key=None,
            third_party_config=None,
            permissions=None,
            permissions_content=None,
            modules=None,
            abi_filters=None,
            schemes=None,
        )

        # 这个测试可能会失败，因为代码没有处理 None 值
        # 但这正是我们想要测试的边缘情况
        try:
            create_readme_file(req_dir, manifest_info)
            written_content = "".join(call.args[0] for call in mock_file.return_value.write.call_args_list)
            # 如果成功，验证 None 被转换为字符串
            self.assertIn("HBuilderX 版本：`None`", written_content)
        except (TypeError, AttributeError) as e:
            # 如果失败，这表明代码需要改进来处理 None 值
            self.fail(f"代码无法处理 None 值: {e}")
