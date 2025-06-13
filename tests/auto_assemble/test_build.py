import pytest
from unittest.mock import patch, Mock, MagicMock
from pathlib import Path

from auto_assemble.build import (
    get_build_output_name,
    get_distribution_target_dir,
    execute_gradle_build,
    copy_build_outputs,
    build,
    parse_metadata,
    update_git_info,
)
from common.api import record_task_metadata
from common.types import BuildMetadata, SignConfig
from common.commit_label import get_build_resp_message, parse_build_req_message


class TestGetBuildRespMessage:
    def test_build_response_message(self):
        """测试构建响应消息生成"""
        with patch("auto_assemble.build.get_build_req_label", return_value="#test_resp#"):
            result = get_build_resp_message("test", "test commit message")
            assert result == "#test_resp#test commit message"


class TestParseBuildReqMessage:
    def test_valid_build_request_message(self):
        """测试有效的构建请求消息解析"""
        message = "#dev_req# 更新版本到1.2.3"
        build_mode, commit_message = parse_build_req_message(message)

        assert build_mode == "dev"
        assert commit_message == "更新版本到1.2.3"

    def test_production_build_request(self):
        """测试生产环境构建请求"""
        message = "#prod_req# 发布正式版本"
        build_mode, commit_message = parse_build_req_message(message)

        assert build_mode == "prod"
        assert commit_message == "发布正式版本"

    def test_invalid_build_request_message(self):
        """测试无效的构建请求消息"""
        invalid_messages = [
            "普通的提交消息",
            "#invalid format",
            "req# 缺少开头",
            "#_req# 空的构建模式",
        ]

        for message in invalid_messages:
            build_mode, commit_message = parse_build_req_message(message)
            assert build_mode is None
            assert commit_message is None

    def test_empty_commit_message(self):
        """测试空的提交消息"""
        message = "#test_req# "
        build_mode, commit_message = parse_build_req_message(message)

        assert build_mode == "test"
        assert commit_message == ""


class TestGetBuildOutputName:
    @patch("auto_assemble.build.config")
    @patch("os.listdir")
    def test_find_release_apk(self, mock_listdir, mock_config):
        """测试查找release APK文件"""
        mock_config.BUILD_RELEASE_OUTPUT_DIR = "/test/release"
        mock_listdir.return_value = ["app-release-202312251430.apk", "other.txt"]

        result = get_build_output_name(release=True)
        assert result == "app-release-202312251430.apk"
        mock_listdir.assert_called_once_with("/test/release")

    @patch("auto_assemble.build.config")
    @patch("os.listdir")
    def test_find_debug_apk(self, mock_listdir, mock_config):
        """测试查找debug APK文件"""
        mock_config.BUILD_DEBUG_OUTPUT_DIR = "/test/debug"
        mock_listdir.return_value = ["app-debug-202312251430.apk"]

        result = get_build_output_name(release=False)
        assert result == "app-debug-202312251430.apk"
        mock_listdir.assert_called_once_with("/test/debug")

    @patch("auto_assemble.build.config")
    @patch("os.listdir")
    def test_no_apk_found(self, mock_listdir, mock_config):
        """测试未找到APK文件"""
        mock_config.BUILD_RELEASE_OUTPUT_DIR = "/test/empty"
        mock_listdir.return_value = ["other.txt", "readme.md"]

        with pytest.raises(FileNotFoundError) as exc_info:
            get_build_output_name(release=True)

        assert "未找到符合yyyyMMddHHmm格式的APK文件" in str(exc_info.value)

    @patch("auto_assemble.build.config")
    @patch("os.listdir")
    def test_multiple_apk_files(self, mock_listdir, mock_config):
        """测试多个APK文件时返回第一个"""
        mock_config.BUILD_RELEASE_OUTPUT_DIR = "/test/release"
        mock_listdir.return_value = ["app-release-202312251430.apk", "app-release-202312251431.apk"]

        result = get_build_output_name(release=True)
        assert result.endswith(".apk")
        assert result in ["app-release-202312251430.apk", "app-release-202312251431.apk"]


class TestGetDistributionTargetDir:
    @patch("auto_assemble.build.config")
    def test_distribution_target_directory(self, mock_config):
        """测试分发目标目录生成"""
        mock_config.DISTRIBUTION_PATH = "/test/distribution"
        mock_config.PROD_NAME = "test_project"

        result = get_distribution_target_dir("app-release-202312251430.apk")
        expected = Path("/test/distribution/test_project/app-release-202312251430")

        assert result == expected

    @patch("auto_assemble.build.config")
    def test_apk_extension_removal(self, mock_config):
        """测试APK扩展名移除"""
        mock_config.DISTRIBUTION_PATH = "/test/distribution"
        mock_config.PROD_NAME = "test_project"

        result = get_distribution_target_dir("my-app.apk")
        expected = Path("/test/distribution/test_project/my-app")

        assert result == expected


class TestExecuteGradleBuild:
    @patch("auto_assemble.build.subprocess.run")
    @patch("auto_assemble.build.os.chdir")
    @patch("auto_assemble.build.Path")
    @patch("auto_assemble.build.config")
    def test_successful_gradle_build(self, mock_config, mock_path, mock_chdir, mock_run):
        """测试成功的gradle构建"""
        mock_config.ANDROID_UNI_BASE_PATH = "/test/project"
        mock_path.return_value.exists.return_value = True
        mock_run.return_value.returncode = 0

        result = execute_gradle_build(release=True)

        assert result is True
        mock_chdir.assert_called_with("/test/project")
        mock_run.assert_called_once()

    @patch("auto_assemble.build.subprocess.run")
    @patch("auto_assemble.build.os.chdir")
    @patch("auto_assemble.build.Path")
    @patch("auto_assemble.build.config")
    def test_failed_gradle_build(self, mock_config, mock_path, mock_chdir, mock_run):
        """测试失败的gradle构建"""
        mock_config.ANDROID_UNI_BASE_PATH = "/test/project"
        mock_path.return_value.exists.return_value = True
        mock_run.return_value.returncode = 1
        mock_run.return_value.stderr = "Build failed"

        result = execute_gradle_build(release=True)

        assert result is False

    @patch("auto_assemble.build.Path")
    @patch("auto_assemble.build.config")
    def test_project_directory_not_exists(self, mock_config, mock_path):
        """测试项目目录不存在"""
        mock_config.ANDROID_UNI_BASE_PATH = "/nonexistent/project"
        mock_path.return_value.exists.return_value = False

        result = execute_gradle_build(release=True)

        assert result is False


class TestRecordTaskMetadata:
    @patch("common.api.config")
    @patch("common.api.requests.post")
    @patch("auto_assemble.build.config")
    def test_successful_metadata_recording(self, mock_config, mock_post, mock_api_config):
        """测试成功记录元数据"""
        mock_config.SERVER_HOST_URL = "http://test.com"
        mock_api_config.SERVER_HOST_URL = "http://test.com"
        mock_config.cur_task_id = "test_task_123"
        mock_response = Mock()
        mock_response.status_code = 201
        mock_post.return_value = mock_response

        metadata: BuildMetadata = {
            "package_name": "com.test.app",
            "version_name": "1.0.0",
            "version_code": 1,
            "build_type": "release",
            "flavor": "default",
            "build_date": "2023-12-25 14:30:00",
            "file_size": 1024,
            "md5": "abc123",
            "is_normalized": True,
            "is_obfuscated": False,
        }

        result = record_task_metadata("test_task_123", metadata)

        assert result is True
        mock_post.assert_called_once_with("http://test.com/api/metadata/test_task_123", json=metadata)

    @patch("common.api.requests.post")
    @patch("auto_assemble.build.config")
    def test_failed_metadata_recording(self, mock_config, mock_post):
        """测试记录元数据失败"""
        mock_config.SERVER_HOST_URL = "http://test.com"
        mock_config.cur_task_id = "test_task_123"
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        mock_post.return_value = mock_response

        metadata: BuildMetadata = {}
        result = record_task_metadata("test_task_123", metadata)

        assert result is False

    @patch("common.api.requests.post")
    @patch("auto_assemble.build.config")
    def test_network_error(self, mock_config, mock_post):
        """测试网络错误"""
        mock_config.SERVER_HOST_URL = "http://test.com"
        mock_config.cur_task_id = "test_task_123"
        mock_post.side_effect = Exception("Network error")

        metadata: BuildMetadata = {}
        result = record_task_metadata("test_task_123", metadata)

        assert result is False


class TestParseMetadata:
    def test_parse_metadata_success(self):
        """测试成功解析元数据"""
        metadata_text = """Package Name: com.test.app
Version Name: 1.0.0
Version Code: 1
Build Type: release
Flavor: default
Build Date: 2023-12-25 14:30:00
File Size: 1024 bytes (1 KB)
MD5: abc123
是否Normalized: true
UniApp资源包是否混淆: false
打包请求: test request"""

        result = parse_metadata(metadata_text)

        expected = {
            "package_name": "com.test.app",
            "version_name": "1.0.0",
            "version_code": "1",
            "build_type": "release",
            "flavor": "default",
            "build_date": "2023-12-25 14:30:00",
            "file_size": 1,
            "md5": "abc123",
            "is_normalized": "true",
            "is_obfuscated": "false",
        }

        assert result == expected

    def test_parse_metadata_with_missing_fields(self):
        """测试解析缺少字段的元数据"""
        metadata_text = """Package Name: com.test.app
Version Name: 1.0.0
MD5: abc123"""

        result = parse_metadata(metadata_text)

        expected = {"package_name": "com.test.app", "version_name": "1.0.0", "md5": "abc123"}

        assert result == expected


class TestUpdateGitInfo:
    @patch("auto_assemble.build.git_push")
    @patch("auto_assemble.build.git_commit")
    @patch("auto_assemble.build.get_staged_files")
    @patch("auto_assemble.build.git_add")
    @patch("auto_assemble.build.os.chdir")
    @patch("auto_assemble.build.config")
    def test_successful_git_update(
        self, mock_config, mock_chdir, mock_git_add, mock_get_staged, mock_git_commit, mock_git_push
    ):
        """测试成功的git更新"""
        mock_config.ANDROID_UNI_BASE_PATH = "/test/project"
        mock_git_add.return_value = True
        mock_get_staged.return_value = ["file1.txt", "file2.txt"]
        mock_git_commit.return_value = True
        mock_git_push.return_value = True

        result = update_git_info("test commit message")

        assert result == 0
        mock_chdir.assert_called_with("/test/project")
        mock_git_add.assert_called_once()
        mock_git_commit.assert_called_once()
        mock_git_push.assert_called_once()

    @patch("auto_assemble.build.git_add")
    @patch("auto_assemble.build.os.chdir")
    @patch("auto_assemble.build.config")
    def test_git_add_failure(self, mock_config, mock_chdir, mock_git_add):
        """测试git add失败"""
        mock_config.ANDROID_UNI_BASE_PATH = "/test/project"
        mock_git_add.return_value = False

        result = update_git_info("test commit message")

        assert result == 12008


class TestCopyBuildOutputs:
    @patch("auto_assemble.build.Path")
    @patch("auto_assemble.build.config")
    @patch("auto_assemble.build.client_publish_async")
    @patch("auto_assemble.build.subprocess.run")
    @patch("auto_assemble.build.shutil.copy2")
    @patch("auto_assemble.build.open")
    @patch("auto_assemble.build.parse_metadata")
    @patch("common.api.record_task_metadata")
    @patch("auto_assemble.build.exec_normalized_apk")
    @patch("auto_assemble.build.sign_apk")
    @patch("auto_assemble.build.update_metadata_md")
    def test_normalized_apk_handling(
        self,
        mock_update_metadata,
        mock_sign_apk,
        mock_exec_normalized,
        mock_record_metadata,
        mock_parse_metadata,
        mock_open,
        mock_copy2,
        mock_run,
        mock_publish,
        mock_config,
        mock_path,
    ):
        """测试APK归一化处理"""
        mock_config.build_mode = "release"
        mock_config.BUILD_RELEASE_OUTPUT_DIR = "/test/output"
        mock_config.cur_task_id = "test_task_123"

        # 设置Path mock的行为
        mock_path.return_value.exists.return_value = True
        mock_path.return_value.mkdir = MagicMock()

        # 设置sign_apk的返回值
        mock_target_apk = MagicMock()
        mock_sign_apk.return_value = (mock_target_apk, 512000, "abc123")

        # 设置update_metadata_md的返回值
        mock_update_metadata.return_value = ("abc123", "updated content")

        mock_parse_metadata.return_value = {"package_name": "com.test.app"}
        mock_record_metadata.return_value = True

        # 模拟文件内容
        mock_file = MagicMock()
        mock_file.read.return_value = "MD5: abc123\nFile Size: 1024 bytes (1 KB)"
        mock_open.return_value.__enter__.return_value = mock_file

        result, apk_name = copy_build_outputs(
            "app-release.apk",
            Path("/test/target"),
            True,
            SignConfig(key_store=Path("/test/keystore"), key_alias="test", ks_pass="pass", key_pass="pass"),
        )

        assert result is True
        assert apk_name == "app-release"
        mock_exec_normalized.assert_called_once()
        mock_sign_apk.assert_called_once()
        mock_publish.assert_called()

    @patch("auto_assemble.build.Path")
    @patch("auto_assemble.build.config")
    def test_source_apk_not_exists(self, mock_config, mock_path):
        """测试源APK文件不存在"""
        mock_config.build_mode = "release"
        mock_path.return_value.exists.return_value = False

        result, apk_name = copy_build_outputs(
            "app-release.apk",
            Path("/test/target"),
            True,
            SignConfig(key_store=Path("/test/keystore"), key_alias="test", ks_pass="pass", key_pass="pass"),
        )

        assert result is False
        assert apk_name == ""

    @patch("auto_assemble.build.Path")
    @patch("auto_assemble.build.config")
    @patch("auto_assemble.build.shutil.copy2")
    def test_source_metadata_not_exists(self, mock_copy2, mock_config, mock_path):
        """测试源metadata文件不存在"""
        mock_config.build_mode = "release"
        mock_path.return_value.exists.side_effect = [True, False]

        result, apk_name = copy_build_outputs(
            "app-release.apk",
            Path("/test/target"),
            True,
            SignConfig(key_store=Path("/test/keystore"), key_alias="test", ks_pass="pass", key_pass="pass"),
        )

        assert result is False
        assert apk_name == ""


class TestSignApk:
    @patch("auto_assemble.build.calculate_file_md5")
    @patch("auto_assemble.build.subprocess.run")
    @patch("auto_assemble.build.Path")  # 直接 mock build 模块中的 Path
    def test_successful_sign(self, mock_path_class, mock_run, mock_calculate_md5):
        """测试成功签名APK"""
        # 设置mock对象
        mock_input_path = MagicMock()
        mock_output_path = MagicMock()
        mock_apksigner_path = MagicMock()
        mock_idsig_path = MagicMock()
        mock_unlink = MagicMock()

        # 直接设置 apksigner 路径的 mock
        mock_path_class.return_value = mock_apksigner_path
        mock_apksigner_path.exists.return_value = True

        # 配置输出路径的行为
        mock_output_path.with_stem.return_value.with_suffix.return_value = mock_output_path
        mock_output_path.with_suffix.return_value = mock_idsig_path
        mock_output_path.as_posix.return_value = "/test/output.apk"
        mock_idsig_path.exists.return_value = True
        mock_idsig_path.unlink = mock_unlink

        # 配置stat的返回值 - sign_apk函数中调用了两次stat()
        mock_stat = MagicMock()
        mock_stat.st_size = 1024
        mock_output_path.stat.return_value = mock_stat

        mock_run.return_value.returncode = 0
        mock_calculate_md5.return_value = "abc123"

        from auto_assemble.build import sign_apk

        sign_config = SignConfig(key_store=Path("/test/keystore"), key_alias="test", ks_pass="pass", key_pass="pass")

        # 直接使用mock对象而不是Path构造函数
        result = sign_apk(mock_input_path, sign_config, mock_output_path)

        assert isinstance(result, tuple)
        assert len(result) == 3
        assert result[0].as_posix() == "/test/output.apk"  # 输出路径
        assert result[1] == 1024  # 文件大小
        assert result[2] == "abc123"  # MD5

        # 验证mock调用
        mock_run.assert_called_once()
        mock_calculate_md5.assert_called_once()

        # 验证stat被调用两次（sign_apk函数中第489行和第492行各调用一次）
        assert mock_output_path.stat.call_count == 2

        # 验证 Path 构造函数被调用（用于创建 apksigner 路径）
        mock_path_class.assert_called_with("/opt/android-sdk/build-tools/34.0.0/apksigner")
        mock_apksigner_path.exists.assert_called_once()
        mock_idsig_path.exists.assert_called_once()
        mock_unlink.assert_called_once()

    @patch("pathlib.Path")
    def test_apksigner_not_exists(self, mock_path):
        """测试apksigner不存在"""
        mock_path_instance = MagicMock()
        mock_path.return_value = mock_path_instance
        mock_path_instance.exists.return_value = False

        from auto_assemble.build import sign_apk

        sign_config = SignConfig(key_store=Path("/test/keystore"), key_alias="test", ks_pass="pass", key_pass="pass")

        with pytest.raises(FileNotFoundError):
            sign_apk(Path("/test/input.apk"), sign_config)

    @patch("pathlib.Path")
    @patch("auto_assemble.build.subprocess.run")
    def test_sign_failure(self, mock_run, mock_path):
        """测试签名失败"""
        mock_path_instance = MagicMock()
        mock_path.return_value = mock_path_instance
        mock_path_instance.exists.return_value = True
        mock_run.return_value.returncode = 1

        from auto_assemble.build import sign_apk

        sign_config = SignConfig(key_store=Path("/test/keystore"), key_alias="test", ks_pass="pass", key_pass="pass")

        with pytest.raises(Exception):
            sign_apk(Path("/test/input.apk"), sign_config)


class TestMainFunction:
    @patch("auto_assemble.build.git_reset_and_clean")
    @patch("auto_assemble.build.update_git_info")
    @patch("auto_assemble.build.copy_build_outputs")
    @patch("auto_assemble.build.get_build_output_name")
    @patch("auto_assemble.build.get_distribution_target_dir")
    @patch("auto_assemble.build.execute_gradle_build")
    @patch("auto_assemble.build.check_uni_base")
    @patch("auto_assemble.build.setup_logging")
    @patch("auto_assemble.build.client_publish_async")
    def test_successful_main_flow(
        self,
        mock_client_publish,
        mock_setup_logging,
        mock_check_uni_base,
        mock_execute_gradle,
        mock_get_distribution_target,
        mock_get_build_output,
        mock_copy_build_outputs,
        mock_update_git_info,
        mock_git_reset,
    ):
        """测试成功的主流程"""
        mock_check_uni_base.return_value = {"key_store": "/test/keystore"}
        mock_execute_gradle.return_value = True
        mock_get_build_output.return_value = "app-release-202312251430.apk"
        mock_get_distribution_target.return_value = Path("/test/target")
        mock_copy_build_outputs.return_value = (True, "app-release-202312251430")
        mock_update_git_info.return_value = 0

        result = build()

        assert result == 0
        mock_setup_logging.assert_called_once()
        mock_check_uni_base.assert_called_once()
        mock_execute_gradle.assert_called_once_with(True)
        mock_copy_build_outputs.assert_called_once()
        mock_update_git_info.assert_called_once()
        mock_git_reset.assert_called_once()

    @patch("auto_assemble.build.git_reset_and_clean")
    @patch("auto_assemble.build.execute_gradle_build")
    @patch("auto_assemble.build.check_uni_base")
    @patch("auto_assemble.build.setup_logging")
    @patch("auto_assemble.build.client_publish_async")
    def test_gradle_build_failure(
        self,
        mock_client_publish,
        mock_setup_logging,
        mock_check_uni_base,
        mock_execute_gradle,
        mock_git_reset,
    ):
        """测试gradle构建失败"""
        mock_check_uni_base.return_value = {"key_store": "/test/keystore"}
        mock_execute_gradle.return_value = False

        result = build()

        assert result == 20001
        mock_git_reset.assert_called_once()

    @patch("auto_assemble.build.git_reset_and_clean")
    @patch("auto_assemble.build.copy_build_outputs")
    @patch("auto_assemble.build.get_build_output_name")
    @patch("auto_assemble.build.get_distribution_target_dir")
    @patch("auto_assemble.build.execute_gradle_build")
    @patch("auto_assemble.build.check_uni_base")
    @patch("auto_assemble.build.setup_logging")
    @patch("auto_assemble.build.client_publish_async")
    def test_copy_outputs_failure(
        self,
        mock_client_publish,
        mock_setup_logging,
        mock_check_uni_base,
        mock_execute_gradle,
        mock_get_distribution_target,
        mock_get_build_output,
        mock_copy_build_outputs,
        mock_git_reset,
    ):
        """测试复制构建产物失败"""
        mock_check_uni_base.return_value = {"key_store": "/test/keystore"}
        mock_execute_gradle.return_value = True
        mock_get_build_output.return_value = "app-release-202312251430.apk"
        mock_get_distribution_target.return_value = Path("/test/target")
        mock_copy_build_outputs.return_value = (False, "")

        result = build()

        assert result == 20002
        mock_git_reset.assert_called_once()

    @patch("auto_assemble.build.git_reset_and_clean")
    @patch("auto_assemble.build.update_git_info")
    @patch("auto_assemble.build.copy_build_outputs")
    @patch("auto_assemble.build.get_build_output_name")
    @patch("auto_assemble.build.get_distribution_target_dir")
    @patch("auto_assemble.build.execute_gradle_build")
    @patch("auto_assemble.build.check_uni_base")
    @patch("auto_assemble.build.setup_logging")
    @patch("auto_assemble.build.client_publish_async")
    def test_git_update_failure(
        self,
        mock_client_publish,
        mock_setup_logging,
        mock_check_uni_base,
        mock_execute_gradle,
        mock_get_distribution_target,
        mock_get_build_output,
        mock_copy_build_outputs,
        mock_update_git_info,
        mock_git_reset,
    ):
        """测试git更新失败"""
        mock_check_uni_base.return_value = {"key_store": "/test/keystore"}
        mock_execute_gradle.return_value = True
        mock_get_build_output.return_value = "app-release-202312251430.apk"
        mock_get_distribution_target.return_value = Path("/test/target")
        mock_copy_build_outputs.return_value = (True, "app-release-202312251430")
        mock_update_git_info.return_value = 12008

        result = build()

        assert result == 12008
        mock_git_reset.assert_called_once()

    @patch("auto_assemble.build.git_reset_and_clean")
    @patch("auto_assemble.build.execute_gradle_build")
    @patch("auto_assemble.build.check_uni_base")
    @patch("auto_assemble.build.setup_logging")
    def test_file_not_found_error(self, mock_setup_logging, mock_check_uni_base, mock_execute_gradle, mock_git_reset):
        """测试文件未找到错误"""
        mock_check_uni_base.return_value = {"key_store": "/test/keystore"}
        mock_execute_gradle.side_effect = FileNotFoundError("File not found")

        from auto_assemble.build import build

        result = build()

        assert result == 12010
        mock_git_reset.assert_called_once()

    @patch("auto_assemble.build.git_reset_and_clean")
    @patch("auto_assemble.build.update_git_info")
    @patch("auto_assemble.build.copy_build_outputs")
    @patch("auto_assemble.build.get_build_output_name")
    @patch("auto_assemble.build.get_distribution_target_dir")
    @patch("auto_assemble.build.execute_gradle_build")
    @patch("auto_assemble.build.check_uni_base")
    @patch("auto_assemble.build.setup_logging")
    @patch("auto_assemble.build.client_publish_async")
    def test_different_build_modes(
        self,
        mock_client_publish,
        mock_setup_logging,
        mock_check_uni_base,
        mock_execute_gradle,
        mock_get_distribution_target,
        mock_get_build_output,
        mock_copy_build_outputs,
        mock_update_git_info,
        mock_git_reset,
    ):
        """测试不同的构建模式"""
        mock_check_uni_base.return_value = {"key_store": "/test/keystore"}
        mock_execute_gradle.return_value = True
        mock_get_build_output.return_value = "app-release-202312251430.apk"
        mock_get_distribution_target.return_value = Path("/test/target")
        mock_copy_build_outputs.return_value = (True, "app-release-202312251430")
        mock_update_git_info.return_value = 0

        # 测试release模式
        result = build(release=True)
        assert result == 0
        mock_execute_gradle.assert_called_with(True)

        # 测试debug模式
        result = build(release=False)
        assert result == 0
        mock_execute_gradle.assert_called_with(False)

        mock_git_reset.assert_called()
