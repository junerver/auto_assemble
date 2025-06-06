import json
import unittest
from pathlib import Path
from unittest.mock import mock_open, patch

from cbr.parse_uni_manifest import parse_uni_manifest
from common.types import CbrEnvVars


class TestParseUniManifest(unittest.TestCase):
    """测试 parse_uni_manifest 函数"""

    @patch("cbr.parse_uni_manifest.parse_third_party_configs")
    @patch("builtins.open", new_callable=mock_open)
    def test_parse_uni_manifest_success(self, mock_file, mock_parse_third_party):
        """测试成功解析 manifest.json 文件"""
        # 设置测试数据
        manifest_data = {
            "versionName": "1.0.0",
            "versionCode": "1",
            "appid": "test_app_id",
            "app-plus": {
                "compatible": {"ignoreVersion": True},
                "modules": {"OAuth": {}},
                "distribute": {
                    "android": {
                        "abiFilters": ["armeabi-v7a", "arm64-v8a"],
                        "schemes": ["test1", "test2"],
                        "permissions": ['<uses-permission android:name="android.permission.INTERNET" />'],
                    },
                    "sdkConfigs": {
                        "oauth": {"weixin": {"appid": "wx123456", "appsecret": "secret123"}},
                    },
                },
            },
        }

        # 配置 mock
        mock_file.return_value.read.return_value = json.dumps(manifest_data)
        mock_parse_third_party.return_value = {"test_vendor": {"key": "value"}}

        # 设置参数 - 提供所有必需的 CbrEnvVars 参数
        manifest_path = Path("/test/manifest.json")
        env_vars = CbrEnvVars(
            DISTRIBUTION_PATH=Path("/test/distribution"),
            PROD_NAME="test_product",
            HBX_VERSION="3.8.0",
            UNIAPP_ID="test_uniapp_id",
            UNIAPP_APPKEY="test_app_key",
            UNIAPP_WORKSPACE=Path("/test/workspace"),
            UNIAPP_IS_CLI=False,
        )
        third_party_configs = []

        # 执行测试
        result = parse_uni_manifest(manifest_path, env_vars, third_party_configs)

        # 验证结果 - 使用字典键检查替代 isinstance
        self.assertIsInstance(result, dict)
        self.assertIn("version_name", result)
        self.assertIn("version_code", result)
        self.assertIn("uniapp_id", result)
        self.assertEqual(result["version_name"], "1.0.0")
        self.assertEqual(result["version_code"], "1")
        self.assertEqual(result["uniapp_id"], "test_app_id")
        self.assertEqual(result["abi_filters"], '"armeabi-v7a", "arm64-v8a"')
        self.assertEqual(result["schemes"], ["test1", "test2"])
        self.assertIn("OAuth : weixin", result["modules"])

        # 验证文件操作
        mock_file.assert_called_once_with(manifest_path, "r", encoding="utf-8")

    @patch("builtins.open", side_effect=FileNotFoundError("文件不存在"))
    def test_parse_uni_manifest_file_not_found(self, mock_file):
        """测试文件不存在的情况"""
        # 设置参数
        manifest_path = Path("/test/nonexistent.json")

        # 执行测试
        result = parse_uni_manifest(manifest_path)

        # 验证结果 - 使用字典键检查替代 isinstance
        self.assertIsInstance(result, dict)
        self.assertIn("version_name", result)
        self.assertIn("version_code", result)
        self.assertIn("uniapp_id", result)
        self.assertEqual(result["version_name"], "")
        self.assertEqual(result["version_code"], "")
        self.assertEqual(result["uniapp_id"], "")

    @patch("builtins.open", new_callable=mock_open)
    def test_parse_uni_manifest_invalid_json(self, mock_file):
        """测试无效 JSON 的情况"""
        # 设置无效 JSON
        mock_file.return_value.read.return_value = "invalid json content"

        # 设置参数
        manifest_path = Path("/test/invalid.json")

        # 执行测试
        result = parse_uni_manifest(manifest_path)

        # 验证结果 - 使用字典键检查替代 isinstance
        self.assertIsInstance(result, dict)
        self.assertIn("version_name", result)
        self.assertIn("version_code", result)
        self.assertIn("uniapp_id", result)
        self.assertEqual(result["version_name"], "")
        self.assertEqual(result["version_code"], "")
        self.assertEqual(result["uniapp_id"], "")

    @patch("cbr.parse_uni_manifest.parse_third_party_configs")
    @patch("builtins.open", new_callable=mock_open)
    def test_parse_uni_manifest_minimal_data(self, mock_file, mock_parse_third_party):
        """测试最小数据集的解析"""
        # 设置最小测试数据
        manifest_data = {"appid": "minimal_app_id"}

        # 配置 mock
        mock_file.return_value.read.return_value = json.dumps(manifest_data)
        mock_parse_third_party.return_value = {}

        # 设置参数
        manifest_path = Path("/test/minimal.json")

        # 执行测试
        result = parse_uni_manifest(manifest_path)

        # 验证结果 - 使用字典键检查替代 isinstance
        self.assertIsInstance(result, dict)
        self.assertIn("uniapp_id", result)
        self.assertIn("version_name", result)
        self.assertIn("version_code", result)
        self.assertIn("abi_filters", result)
        self.assertIn("schemes", result)
        self.assertEqual(result["uniapp_id"], "minimal_app_id")
        self.assertEqual(result["version_name"], "")  # 默认空值
        self.assertEqual(result["version_code"], "")  # 默认空值
        self.assertEqual(result["abi_filters"], '"armeabi-v7a", "arm64-v8a"')  # 默认的abi为v7a和v8a
        self.assertEqual(result["schemes"], "")  # 默认空字符串

    # 新增测试用例 - 权限处理测试
    # 修复权限处理测试
    @patch("common.parse_permissions.parse_and_merge_permissions")  # 修改这里
    @patch("cbr.parse_uni_manifest.parse_third_party_configs")
    @patch("builtins.open", new_callable=mock_open)
    def test_permissions_content_processing(self, mock_file, mock_parse_third_party, mock_parse_permissions):
        """测试权限内容处理"""
        manifest_data = {
            "appid": "test_app",
            "app-plus": {
                "distribute": {
                    "android": {
                        "permissions": [
                            '<uses-permission android:name="android.permission.CAMERA" />',
                            '<uses-permission android:name="android.permission.RECORD_AUDIO" />',
                        ],
                        "excludePermissions": [
                            '<uses-permission android:name="android.permission.READ_EXTERNAL_STORAGE" />'
                        ],
                    }
                }
            },
        }

        mock_file.return_value.read.return_value = json.dumps(manifest_data)
        mock_parse_third_party.return_value = {}
        mock_parse_permissions.return_value = {"permissions": {}, "features": {}}

        result = parse_uni_manifest(Path("/test/manifest.json"))

        # 验证权限内容包含默认权限、额外权限和排除权限
        permissions_content = result["permissions_content"]
        self.assertIn("需要额外添加：", permissions_content)
        self.assertIn("android.permission.CAMERA", permissions_content)
        self.assertIn("android.permission.RECORD_AUDIO", permissions_content)
        self.assertIn("需要移除：", permissions_content)
        self.assertIn("android.permission.READ_EXTERNAL_STORAGE", permissions_content)

        # 验证parse_and_merge_permissions被调用
        mock_parse_permissions.assert_called_once()

    # 新增测试用例 - 部分app-plus配置
    @patch("cbr.parse_uni_manifest.parse_third_party_configs")
    @patch("builtins.open", new_callable=mock_open)
    def test_partial_app_plus_config(self, mock_file, mock_parse_third_party):
        """测试部分app-plus配置（缺少distribute或android）"""
        # 测试只有modules没有distribute
        manifest_data = {"appid": "test_app", "app-plus": {"modules": {"OAuth": {}, "Payment": {}}}}

        mock_file.return_value.read.return_value = json.dumps(manifest_data)
        mock_parse_third_party.return_value = {}

        result = parse_uni_manifest(Path("/test/manifest.json"))

        # 验证默认值
        self.assertEqual(result["abi_filters"], '"armeabi-v7a", "arm64-v8a"')
        self.assertEqual(result["schemes"], "")
        # 校验了modules配置同时要求必须存在distribute配置与sdkConfigs，缺少配置时不解析modules
        self.assertEqual(result["modules"], [])

    @patch("cbr.parse_uni_manifest.parse_third_party_configs")
    @patch("builtins.open", new_callable=mock_open)
    def test_app_plus_with_distribute_no_android(self, mock_file, mock_parse_third_party):
        """测试有distribute但没有android配置"""
        manifest_data = {
            "appid": "test_app",
            "app-plus": {"distribute": {"sdkConfigs": {"oauth": {"weixin": {"appid": "wx123"}}}}},
        }

        mock_file.return_value.read.return_value = json.dumps(manifest_data)
        mock_parse_third_party.return_value = {}

        result = parse_uni_manifest(Path("/test/manifest.json"))

        # 验证默认值
        self.assertEqual(result["abi_filters"], '"armeabi-v7a", "arm64-v8a"')
        self.assertEqual(result["schemes"], "")
        self.assertEqual(result["modules"], [])  # 没有modules配置

    # 新增测试用例 - 复杂模块解析
    @patch("cbr.parse_uni_manifest.parse_third_party_configs")
    @patch("builtins.open", new_callable=mock_open)
    def test_complex_modules_parsing(self, mock_file, mock_parse_third_party):
        """测试复杂的模块解析（多个子模块）"""
        manifest_data = {
            "appid": "test_app",
            "app-plus": {
                "modules": {"OAuth": {}, "Payment": {}, "Maps": {}},
                "distribute": {
                    "sdkConfigs": {
                        "oauth": {"weixin": {"appid": "wx123"}, "qq": {"appid": "qq123"}, "__platform__": ["android"]},
                        "payment": {"alipay": {"scheme": "alipay123"}, "wxpay": {"appid": "wx456"}},
                    }
                },
            },
        }

        mock_file.return_value.read.return_value = json.dumps(manifest_data)
        mock_parse_third_party.return_value = {}

        result = parse_uni_manifest(Path("/test/manifest.json"))

        # 验证模块解析结果
        modules = result["modules"]
        self.assertIn("OAuth : weixin", modules)
        self.assertIn("OAuth : qq", modules)
        self.assertIn("Payment : alipay", modules)
        self.assertIn("Payment : wxpay", modules)
        self.assertIn("Maps", modules)  # 没有对应SDK配置的模块直接添加
        # 验证__platform__被排除
        self.assertNotIn("OAuth : __platform__", modules)

    # 新增测试用例 - 日志记录验证
    @patch("cbr.parse_uni_manifest.logging")
    @patch("cbr.parse_uni_manifest.parse_third_party_configs")
    @patch("builtins.open", new_callable=mock_open)
    def test_logging_warning_for_incomplete_parsing(self, mock_file, mock_parse_third_party, mock_logging):
        """测试不完整解析的警告日志"""
        # 创建一个会导致不完整解析的manifest（某些字段为空）
        manifest_data = {
            "appid": "test_app"
            # 缺少versionName和versionCode
        }

        mock_file.return_value.read.return_value = json.dumps(manifest_data)
        mock_parse_third_party.return_value = {}

        parse_uni_manifest(Path("/test/manifest.json"))

        # 验证警告日志被调用
        mock_logging.warning.assert_called()
        warning_call_args = mock_logging.warning.call_args[0][0]
        self.assertIn("未能完整解析manifest.json信息", warning_call_args)

    @patch("cbr.parse_uni_manifest.logging")
    @patch("builtins.open", side_effect=Exception("测试异常"))
    def test_logging_exception_on_error(self, mock_file, mock_logging):
        """测试异常时的错误日志"""
        parse_uni_manifest(Path("/test/manifest.json"))

        # 验证异常日志被调用
        mock_logging.exception.assert_called()
        exception_call_args = mock_logging.exception.call_args[0][0]
        self.assertIn("解析manifest.json文件时发生错误", exception_call_args)

    # 新增测试用例 - 环境变量测试
    @patch("cbr.parse_uni_manifest.parse_third_party_configs")
    @patch("builtins.open", new_callable=mock_open)
    def test_env_vars_none(self, mock_file, mock_parse_third_party):
        """测试env_vars为None的情况"""
        manifest_data = {"appid": "test_app"}
        mock_file.return_value.read.return_value = json.dumps(manifest_data)
        mock_parse_third_party.return_value = {}

        result = parse_uni_manifest(Path("/test/manifest.json"), env_vars=None)

        # 验证环境变量相关字段为空
        self.assertEqual(result["hbx_version"], "")
        self.assertEqual(result["uniapp_key"], "")

    @patch("cbr.parse_uni_manifest.parse_third_party_configs")
    @patch("builtins.open", new_callable=mock_open)
    def test_env_vars_partial(self, mock_file, mock_parse_third_party):
        """测试部分填充的env_vars"""
        manifest_data = {"appid": "test_app"}
        mock_file.return_value.read.return_value = json.dumps(manifest_data)
        mock_parse_third_party.return_value = {}

        # 创建部分填充的env_vars（只设置必需字段）
        env_vars = CbrEnvVars(
            DISTRIBUTION_PATH=Path("/test"),
            PROD_NAME="test",
            HBX_VERSION="3.8.0",  # 只设置这个
            UNIAPP_ID="test_id",
            UNIAPP_APPKEY="",  # 这个为空
            UNIAPP_WORKSPACE=Path("/test"),
            UNIAPP_IS_CLI=False,
        )

        result = parse_uni_manifest(Path("/test/manifest.json"), env_vars=env_vars)

        # 验证部分字段有值，部分为空
        self.assertEqual(result["hbx_version"], "3.8.0")
        self.assertEqual(result["uniapp_key"], "")

    # 新增测试用例 - 边缘情况
    @patch("cbr.parse_uni_manifest.parse_third_party_configs")
    @patch("builtins.open", new_callable=mock_open)
    def test_invalid_abi_filters_format(self, mock_file, mock_parse_third_party):
        """测试无效的abiFilters格式"""
        manifest_data = {
            "appid": "test_app",
            "app-plus": {
                "distribute": {
                    "android": {
                        "abiFilters": "invalid_string_instead_of_array"  # 错误格式
                    }
                }
            },
        }

        mock_file.return_value.read.return_value = json.dumps(manifest_data)
        mock_parse_third_party.return_value = {}

        # 这应该不会崩溃，而是使用默认值或处理错误
        result = parse_uni_manifest(Path("/test/manifest.json"))

        # 验证函数仍然返回有效结果
        self.assertIsInstance(result, dict)
        self.assertIn("abi_filters", result)

    @patch("cbr.parse_uni_manifest.parse_third_party_configs")
    @patch("builtins.open", new_callable=mock_open)
    def test_invalid_schemes_format(self, mock_file, mock_parse_third_party):
        """测试无效的schemes格式"""
        manifest_data = {
            "appid": "test_app",
            "app-plus": {
                "distribute": {
                    "android": {
                        "schemes": {"invalid": "object_instead_of_array"}  # 错误格式
                    }
                }
            },
        }

        mock_file.return_value.read.return_value = json.dumps(manifest_data)
        mock_parse_third_party.return_value = {}

        result = parse_uni_manifest(Path("/test/manifest.json"))

        # 验证函数仍然返回有效结果
        self.assertIsInstance(result, dict)
        self.assertIn("schemes", result)

    @patch("cbr.parse_uni_manifest.parse_third_party_configs")
    @patch("builtins.open", new_callable=mock_open)
    def test_special_characters_in_manifest(self, mock_file, mock_parse_third_party):
        """测试manifest.json字段中的特殊字符"""
        manifest_data = {
            "appid": "test_app_with_特殊字符_and_emoji_🚀",
            "versionName": "1.0.0-beta+build.123",
            "app-plus": {
                "distribute": {"android": {"permissions": ['<uses-permission android:name="com.example.特殊权限" />']}}
            },
        }

        mock_file.return_value.read.return_value = json.dumps(manifest_data, ensure_ascii=False)
        mock_parse_third_party.return_value = {}

        result = parse_uni_manifest(Path("/test/manifest.json"))

        # 验证特殊字符被正确处理
        self.assertEqual(result["uniapp_id"], "test_app_with_特殊字符_and_emoji_🚀")
        self.assertEqual(result["version_name"], "1.0.0-beta+build.123")
        self.assertIn("com.example.特殊权限", result["permissions_content"])
