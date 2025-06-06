from unittest.mock import patch
import logging

from auto_assemble.push import validate_timestamp_format, validate_files, push_distribution


class TestValidateTimestampFormat:
    def test_valid_timestamp(self):
        """测试有效的时间戳格式"""
        valid_timestamps = [
            "202312251430",  # 2023年12月25日14:30
            "202401010000",  # 2024年1月1日00:00
            "202412312359",  # 2024年12月31日23:59
        ]

        for timestamp in valid_timestamps:
            assert validate_timestamp_format(timestamp) is True

    def test_invalid_timestamp_format(self):
        """测试无效的时间戳格式"""
        invalid_timestamps = [
            "20231225143",  # 少一位
            "2023122514300",  # 多一位
            "abcd12251430",  # 包含字母
            "202313251430",  # 无效月份
            "202212321430",  # 无效日期
            "202212252560",  # 无效时间
            "",  # 空字符串
        ]

        for timestamp in invalid_timestamps:
            assert validate_timestamp_format(timestamp) is False

    def test_invalid_datetime_value(self):
        """测试无效的日期时间值"""
        # 格式正确但日期无效
        invalid_dates = [
            "202202291430",  # 2022年不是闰年，没有2月29日
            "202204311430",  # 4月没有31日
        ]

        for timestamp in invalid_dates:
            assert validate_timestamp_format(timestamp) is False


class TestValidateFiles:
    def test_valid_files(self, caplog):
        """测试有效的文件列表"""
        files = [
            "test_project/202312251430/202312251430.apk",  # APK文件名以时间戳开头
            "test_project/202312251430/release-metadata.md",
        ]

        is_valid, timestamp = validate_files(files)

        assert is_valid is True
        assert timestamp == "202312251430"

    def test_missing_apk_file(self, caplog):
        """测试缺少APK文件"""
        caplog.set_level(logging.ERROR)

        files = ["test_project/202312251430/release-metadata.md"]

        is_valid, timestamp = validate_files(files)

        assert is_valid is False
        assert timestamp is None
        assert "缺少必要的文件" in caplog.text

    def test_missing_metadata_file(self, caplog):
        """测试缺少metadata文件"""
        caplog.set_level(logging.ERROR)

        files = ["test_project/202312251430/202312251430.apk"]

        is_valid, timestamp = validate_files(files)

        assert is_valid is False
        assert timestamp is None
        assert "缺少必要的文件" in caplog.text

    def test_invalid_timestamp_in_path(self, caplog):
        """测试路径中的无效时间戳"""
        caplog.set_level(logging.ERROR)

        files = [
            "test_project/invalid_timestamp/invalid_timestamp.apk",
            "test_project/invalid_timestamp/release-metadata.md",
        ]

        is_valid, timestamp = validate_files(files)

        assert is_valid is False
        assert timestamp is None
        assert "目录名格式不正确" in caplog.text

    def test_windows_path_separators(self):
        """测试Windows路径分隔符处理"""
        files = [
            "test_project\\202312251430\\202312251430.apk",
            "test_project\\202312251430\\release-metadata.md",
        ]

        is_valid, timestamp = validate_files(files)

        assert is_valid is True
        assert timestamp == "202312251430"

    def test_apk_name_mismatch(self, caplog):
        """测试APK文件名与目录名不匹配"""
        caplog.set_level(logging.ERROR)

        files = [
            "test_project/202312251430/app-release.apk",  # 文件名不以时间戳开头
            "test_project/202312251430/release-metadata.md",
        ]

        is_valid, timestamp = validate_files(files)

        assert is_valid is False
        assert timestamp is None
        assert "APK文件名与目录名不匹配" in caplog.text


class TestGetModifiedApk:
    @patch("auto_assemble.push.config")
    def test_successful_apk_detection(self, mock_config):
        """测试成功检测到已修改的APK文件"""
        mock_config.DISTRIBUTION_PATH = "/test/path"

        mock_output = " M test_project/202312251430/202312251430.apk"
        with patch("subprocess.run") as mock_run:
            mock_run.return_value.returncode = 0
            mock_run.return_value.stdout = mock_output

            from auto_assemble.push import get_modified_apk

            result = get_modified_apk()

            assert result == "202312251430"
            mock_run.assert_called_once_with(
                ["git", "status", "--porcelain"], capture_output=True, text=True, cwd="/test/path"
            )

    @patch("auto_assemble.push.config")
    def test_git_command_failure(self, mock_config):
        """测试git命令执行失败"""
        mock_config.DISTRIBUTION_PATH = "/test/path"

        with patch("subprocess.run") as mock_run:
            mock_run.return_value.returncode = 1
            mock_run.return_value.stderr = "git command failed"

            from auto_assemble.push import get_modified_apk

            result = get_modified_apk()

            assert result is None

    @patch("auto_assemble.push.config")
    def test_exception_handling(self, mock_config):
        """测试异常处理"""
        mock_config.DISTRIBUTION_PATH = "/test/path"

        with patch("subprocess.run", side_effect=Exception("Test error")):
            from auto_assemble.push import get_modified_apk

            result = get_modified_apk()

            assert result is None


class TestPushMain:
    @patch("auto_assemble.push.config")
    @patch("auto_assemble.push.setup_logging")
    def test_successful_push(self, mock_setup_logging, mock_config):
        """测试成功的推送流程"""
        mock_config.DISTRIBUTION_PATH = "/test/path"

        mock_files = [
            "test_project/202312251430/202312251430.apk",
            "test_project/202312251430/release-metadata.md",
        ]

        with (
            patch("auto_assemble.push.Path") as mock_path,
            patch("auto_assemble.push.has_changes", return_value=True),
            patch("auto_assemble.push.get_untracked_files", return_value=mock_files),
            patch("auto_assemble.push.validate_files", return_value=(True, "202312251430")),
            patch("auto_assemble.push.git_add", return_value=True),
            patch("auto_assemble.push.get_staged_files", return_value=mock_files),
            patch("auto_assemble.build.get_build_resp_message", return_value="test commit"),
            patch("auto_assemble.push.git_commit", return_value=True),
            patch("auto_assemble.push.confirm_push", return_value=True),
            patch("auto_assemble.push.git_push", return_value=True),
        ):
            mock_path.return_value.exists.return_value = True

            result = push_distribution()

            assert result == 0

    @patch("auto_assemble.push.config")
    @patch("auto_assemble.push.setup_logging")
    @patch("auto_assemble.push.logging")
    def test_no_changes(self, mock_logging, mock_setup_logging, mock_config):
        """测试没有变更需要提交"""
        mock_config.DISTRIBUTION_PATH = "/test/path"

        with (
            patch("auto_assemble.push.Path") as mock_path,
            patch("auto_assemble.push.has_changes", return_value=False),
        ):
            mock_path.return_value.exists.return_value = True

            result = push_distribution()

            assert result == 11006
            # 验证日志调用
            mock_logging.info.assert_any_call("没有需要提交的修改")

    @patch("auto_assemble.push.config")
    @patch("auto_assemble.push.setup_logging")
    @patch("auto_assemble.push.logging")
    def test_directory_not_exists(self, mock_logging, mock_setup_logging, mock_config):
        """测试目录不存在"""
        mock_config.DISTRIBUTION_PATH = "/nonexistent/path"

        with patch("auto_assemble.push.Path") as mock_path:
            mock_path.return_value.exists.return_value = False

            result = push_distribution()

            assert result == 11001
            # 验证日志调用
            mock_logging.error.assert_any_call("目录不存在: /nonexistent/path")

    @patch("auto_assemble.push.config")
    @patch("auto_assemble.push.setup_logging")
    def test_invalid_files(self, mock_setup_logging, mock_config):
        """测试无效文件"""
        mock_config.DISTRIBUTION_PATH = "/test/path"

        mock_files = ["invalid_file.txt"]

        with (
            patch("auto_assemble.push.Path") as mock_path,
            patch("auto_assemble.push.has_changes", return_value=True),
            patch("auto_assemble.push.get_untracked_files", return_value=mock_files),
            patch("auto_assemble.push.validate_files", return_value=(False, None)),
        ):
            mock_path.return_value.exists.return_value = True

            result = push_distribution()

            assert result == 11007

    @patch("auto_assemble.push.config")
    @patch("auto_assemble.push.setup_logging")
    @patch("auto_assemble.push.logging")
    def test_exception_handling(self, mock_logging, mock_setup_logging, mock_config):
        """测试异常处理"""
        mock_config.DISTRIBUTION_PATH = "/test/path"

        with patch("auto_assemble.push.Path", side_effect=Exception("Test error")):
            result = push_distribution()

            assert result == 1
            # 验证日志调用
            mock_logging.exception.assert_any_call("执行过程中发生错误: Test error")

    @patch("auto_assemble.push.config")
    @patch("auto_assemble.push.setup_logging")
    def test_no_untracked_files_with_modified_apk(self, mock_setup_logging, mock_config):
        """测试没有未跟踪文件但有已修改的APK"""
        mock_config.DISTRIBUTION_PATH = "/test/path"

        with (
            patch("auto_assemble.push.Path") as mock_path,
            patch("auto_assemble.push.has_changes", return_value=True),
            patch("auto_assemble.push.get_untracked_files", return_value=[]),
            patch("auto_assemble.push.get_modified_apk", return_value="202312251430"),
            patch("auto_assemble.push.git_add", return_value=True),
            patch("auto_assemble.push.get_staged_files", return_value=["test.apk"]),
            patch("auto_assemble.push.validate_files", return_value=(True, "202312251430")),
            patch("auto_assemble.build.get_build_resp_message", return_value="test commit"),
            patch("auto_assemble.push.git_commit", return_value=True),
            patch("auto_assemble.push.confirm_push", return_value=True),
            patch("auto_assemble.push.git_push", return_value=True),
        ):
            mock_path.return_value.exists.return_value = True

            result = push_distribution()

            assert result == 0

    @patch("auto_assemble.push.config")
    @patch("auto_assemble.push.setup_logging")
    def test_no_modified_apk_found(self, mock_setup_logging, mock_config):
        """测试未找到符合格式的已修改APK文件"""
        mock_config.DISTRIBUTION_PATH = "/test/path"

        with (
            patch("auto_assemble.push.Path") as mock_path,
            patch("auto_assemble.push.has_changes", return_value=True),
            patch("auto_assemble.push.get_untracked_files", return_value=[]),
            patch("auto_assemble.push.get_modified_apk", return_value=None),
        ):
            mock_path.return_value.exists.return_value = True

            result = push_distribution()

            assert result == 11008

    @patch("auto_assemble.push.config")
    @patch("auto_assemble.push.setup_logging")
    def test_git_add_failure(self, mock_setup_logging, mock_config):
        """测试git add失败"""
        mock_config.DISTRIBUTION_PATH = "/test/path"

        with (
            patch("auto_assemble.push.Path") as mock_path,
            patch("auto_assemble.push.has_changes", return_value=True),
            patch("auto_assemble.push.get_untracked_files", return_value=["test.apk"]),
            patch("auto_assemble.push.validate_files", return_value=(True, "202312251430")),
            patch("auto_assemble.push.git_add", return_value=False),
        ):
            mock_path.return_value.exists.return_value = True

            result = push_distribution()

            assert result == 11009

    @patch("auto_assemble.push.config")
    @patch("auto_assemble.push.setup_logging")
    def test_git_commit_failure(self, mock_setup_logging, mock_config):
        """测试git commit失败"""
        mock_config.DISTRIBUTION_PATH = "/test/path"

        with (
            patch("auto_assemble.push.Path") as mock_path,
            patch("auto_assemble.push.has_changes", return_value=True),
            patch("auto_assemble.push.get_untracked_files", return_value=["test.apk"]),
            patch("auto_assemble.push.validate_files", return_value=(True, "202312251430")),
            patch("auto_assemble.push.git_add", return_value=True),
            patch("auto_assemble.push.get_staged_files", return_value=["test.apk"]),
            patch("auto_assemble.build.get_build_resp_message", return_value="test commit"),
            patch("auto_assemble.push.git_commit", return_value=False),
        ):
            mock_path.return_value.exists.return_value = True

            result = push_distribution()

            assert result == 11012

    @patch("auto_assemble.push.config")
    @patch("auto_assemble.push.setup_logging")
    def test_git_push_failure(self, mock_setup_logging, mock_config):
        """测试git push失败"""
        mock_config.DISTRIBUTION_PATH = "/test/path"

        with (
            patch("auto_assemble.push.Path") as mock_path,
            patch("auto_assemble.push.has_changes", return_value=True),
            patch("auto_assemble.push.get_untracked_files", return_value=["test.apk"]),
            patch("auto_assemble.push.validate_files", return_value=(True, "202312251430")),
            patch("auto_assemble.push.git_add", return_value=True),
            patch("auto_assemble.push.get_staged_files", return_value=["test.apk"]),
            patch("auto_assemble.build.get_build_resp_message", return_value="test commit"),
            patch("auto_assemble.push.git_commit", return_value=True),
            patch("auto_assemble.push.confirm_push", return_value=True),
            patch("auto_assemble.push.git_push", return_value=False),
        ):
            mock_path.return_value.exists.return_value = True

            result = push_distribution()

            assert result == 11014

    @patch("auto_assemble.push.config")
    @patch("auto_assemble.push.setup_logging")
    def test_user_cancels_push(self, mock_setup_logging, mock_config):
        """测试用户取消推送"""
        mock_config.DISTRIBUTION_PATH = "/test/path"

        with (
            patch("auto_assemble.push.Path") as mock_path,
            patch("auto_assemble.push.has_changes", return_value=True),
            patch("auto_assemble.push.get_untracked_files", return_value=["test.apk"]),
            patch("auto_assemble.push.validate_files", return_value=(True, "202312251430")),
            patch("auto_assemble.push.git_add", return_value=True),
            patch("auto_assemble.push.get_staged_files", return_value=["test.apk"]),
            patch("auto_assemble.build.get_build_resp_message", return_value="test commit"),
            patch("auto_assemble.push.git_commit", return_value=True),
            patch("auto_assemble.push.confirm_push", return_value=False),
        ):
            mock_path.return_value.exists.return_value = True

            result = push_distribution()

            assert result == 11013
