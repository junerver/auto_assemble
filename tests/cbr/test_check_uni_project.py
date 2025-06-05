import unittest
from pathlib import Path
from unittest.mock import MagicMock, mock_open, patch

from cbr.check_uni_project import check_uni_project, scan_uni_project
from common.types import CbrEnvVars


class TestScanUniProject(unittest.TestCase):
    """测试 scan_uni_project 函数"""

    @patch("requests.get")
    @patch("builtins.open", new_callable=mock_open)
    def test_scan_uni_project_success(self, mock_file, mock_requests_get):
        """测试成功扫描 UniApp 项目"""
        # 设置 mock 对象
        mock_project_root = MagicMock()
        mock_cbr_dir = MagicMock()
        mock_cbr_dir.resolve.return_value.parent = Path("/test/distribution")

        # 配置 git 配置路径
        mock_git_config_path = MagicMock()
        mock_git_config_path.exists.return_value = True
        mock_project_root.__truediv__.return_value.__truediv__.return_value = mock_git_config_path

        # 配置文件内容 mock - 修复文件读取方式
        git_config_content = """[remote "origin"]
    url = https://github.com/test/project.git
    fetch = +refs/heads/*:refs/remotes/origin/*"""

        # 创建一个可以正确迭代的mock文件对象
        mock_file_instance = mock_open(read_data=git_config_content).return_value
        mock_file_instance.__iter__ = lambda self: iter(git_config_content.splitlines())
        mock_file.return_value = mock_file_instance

        # 配置 API 响应 mock
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "project_config": {
                "prod_name": "test_prod",
                "hbx_version": "4.45",
                "uniapp_id": "test_app_id",
                "uniapp_appkey": "test_app_key",
                "uniapp_is_cli": True,
            },
            "third_party_configs": [],
        }
        mock_requests_get.return_value = mock_response

        # Mock config 对象
        with patch("common.config.config") as mock_config:
            mock_config.SERVER_HOST_URL = "http://test-server"
            mock_config.DISTRIBUTION_PATH = "/test/distribution"

            # 执行测试
            result = scan_uni_project(mock_project_root, mock_cbr_dir)

            # 验证结果
            self.assertIsInstance(result, tuple)
            self.assertEqual(len(result), 2)
            env_vars, third_party_configs = result
            self.assertIsInstance(env_vars, CbrEnvVars)
            self.assertIsInstance(third_party_configs, list)

            # 验证 API 调用
            mock_requests_get.assert_called_once()

    def test_scan_uni_project_git_config_not_exists(self):
        """测试 Git 配置文件不存在的情况"""
        # 设置 mock 对象
        mock_project_root = MagicMock()
        mock_cbr_dir = MagicMock()

        # 配置 git 配置路径不存在
        mock_git_config_path = MagicMock()
        mock_git_config_path.exists.return_value = False
        mock_project_root.__truediv__.return_value.__truediv__.return_value = mock_git_config_path

        # 执行测试并验证异常
        with self.assertRaises(FileNotFoundError) as context:
            scan_uni_project(mock_project_root, mock_cbr_dir)

        self.assertIn("Git配置文件不存在", str(context.exception))


class TestCheckUniProject(unittest.TestCase):
    """测试 check_uni_project 函数"""

    @patch("cbr.check_uni_project.parse_uni_manifest")
    def test_check_uni_project_success(self, mock_parse_manifest):
        """测试成功检查 UniApp 项目"""
        # 创建 mock workspace
        mock_workspace = MagicMock()
        mock_manifest_path = MagicMock()
        mock_resources_path = MagicMock()
        mock_app_id_dir = MagicMock()

        # 配置 mock 对象
        mock_manifest_path.exists.return_value = True
        mock_resources_path.exists.return_value = True
        mock_app_id_dir.name = "test_app_id"
        mock_resources_path.iterdir.return_value = [mock_app_id_dir]

        # 配置路径构建 - 使用 side_effect 而不是直接修改 __truediv__
        def workspace_side_effect(path):
            if "manifest.json" in str(path):
                return mock_manifest_path
            elif "unpackage" in str(path):
                unpackage_mock = MagicMock()
                unpackage_mock.__truediv__.return_value = mock_resources_path
                return unpackage_mock
            return MagicMock()

        mock_workspace.__truediv__.side_effect = workspace_side_effect

        # 设置环境变量 - 提供所有必需参数
        env_vars = CbrEnvVars(
            UNIAPP_WORKSPACE=mock_workspace,
            DISTRIBUTION_PATH=Path("/test/distribution"),
            PROD_NAME="test_prod",
            HBX_VERSION="4.45",
            UNIAPP_ID="test_app_id",
            UNIAPP_APPKEY="test_app_key",
            UNIAPP_IS_CLI=False,
        )
        third_party_configs = []

        # 配置 parse_uni_manifest mock
        mock_manifest_info = {
            "hbx_version": "4.45",
            "version_name": "1.0.0",
            "version_code": "1",
            "uniapp_id": "test_app_id",
            "uniapp_key": "test_key",
            "third_party_config": {},
            "permissions": {},
            "modules": [],
            "abi_filters": "",
            "schemes": "",
        }
        mock_parse_manifest.return_value = mock_manifest_info

        # 执行测试
        result = check_uni_project(env_vars, third_party_configs)

        # 验证结果
        self.assertIsNotNone(result)
        manifest_info, resources_dir = result
        self.assertEqual(manifest_info, mock_manifest_info)
        self.assertEqual(resources_dir, mock_resources_path)

    def test_check_uni_project_no_workspace(self):
        """测试未设置工作空间的情况"""
        # 设置环境变量 - 提供所有必需参数，但 UNIAPP_WORKSPACE 为 None
        env_vars = CbrEnvVars(
            UNIAPP_WORKSPACE=None,
            DISTRIBUTION_PATH=Path("/test/distribution"),
            PROD_NAME="test_prod",
            HBX_VERSION="4.45",
            UNIAPP_ID="test_app_id",
            UNIAPP_APPKEY="test_app_key",
            UNIAPP_IS_CLI=False,
        )
        third_party_configs = []

        # 执行测试
        result = check_uni_project(env_vars, third_party_configs)

        # 验证结果
        self.assertIsNone(result)

    def test_check_uni_project_manifest_not_exists(self):
        """测试 manifest.json 文件不存在的情况"""
        # 创建 mock workspace
        mock_workspace = MagicMock()
        mock_manifest_path = MagicMock()
        mock_manifest_path.exists.return_value = False

        # 配置路径构建
        mock_workspace.__truediv__.return_value = mock_manifest_path

        # 设置环境变量 - 提供所有必需参数
        env_vars = CbrEnvVars(
            UNIAPP_WORKSPACE=mock_workspace,
            DISTRIBUTION_PATH=Path("/test/distribution"),
            PROD_NAME="test_prod",
            HBX_VERSION="4.45",
            UNIAPP_ID="test_app_id",
            UNIAPP_APPKEY="test_app_key",
            UNIAPP_IS_CLI=False,
        )
        third_party_configs = []

        # 执行测试
        result = check_uni_project(env_vars, third_party_configs)

        # 验证结果
        self.assertIsNone(result)


if __name__ == "__main__":
    unittest.main()
