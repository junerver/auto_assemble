import unittest
from pathlib import Path
from unittest.mock import mock_open, patch

from cbr.create_readme_file import create_readme_file
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
            permissions=["android.permission.INTERNET"],
            permissions_content="完整权限内容",
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
        # 修改这一行，使其符合实际的列表输出格式
        self.assertIn('AbiFilters：`"armeabi-v7a", "arm64-v8a"`', written_content)
        self.assertIn("UrlSchemes：`test1,test2`", written_content)

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
            permissions=[],
            permissions_content="",
            modules=[],
            abi_filters=[],
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


if __name__ == "__main__":
    unittest.main()
