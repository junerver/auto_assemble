import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
import subprocess
from common.error import BusinessException
from common.types import TaskInfo, ProjectConfig, SignConfig, BuildMetadata
from auto_assemble.immediate_push import migrate_test_to_release


# Mock config for testing
class MockConfig:
    PROD_NAME = "test_product"
    cur_task_dir = Path("/test/task_dir")
    cur_task_id = "test_task_123"
    DISTRIBUTION_PATH = "/test/distribution"


@pytest.fixture
def setup_config(tmp_path):
    # Setup temporary directory and mock config
    config = MockConfig()
    config.cur_task_dir = tmp_path / "task_dir"
    config.cur_task_dir.mkdir(parents=True)
    return config


@pytest.fixture
def task_info():
    return TaskInfo(
        id="test_task_123",
        author="test_user",
        commit_title="Test commit",
        commit_message="Test message",
        commit_url="http://gitlab/test",
        priority=1,
        retries=0,
        created_at="202506110200",
        started_at=None,
        completed_at=None,
        status="pending",
        error=None,
        commit_hash="abc123",
        response_hash=None,
        metadata=None,
        source_task_id=None,
        project="test_product",
        task="202506110200",
    )


def test_migrate_test_success(setup_config, task_info, tmp_path):
    # Mock dependencies
    with (
        patch("auto_assemble.migrate_test.config", setup_config),
        patch("auto_assemble.migrate_test.download_task_resp") as mock_download,
        patch("auto_assemble.migrate_test.fetch_project_info_by_prod_name") as mock_fetch_project,
        patch("auto_assemble.migrate_test.exec_normalized_apk") as mock_normalize,
        patch("auto_assemble.migrate_test.sign_apk") as mock_sign,
        patch("auto_assemble.migrate_test.update_metadata_md") as mock_update_metadata,
        patch("auto_assemble.migrate_test.parse_metadata") as mock_parse_metadata,
        patch("auto_assemble.migrate_test.record_task_metadata") as mock_record_metadata,
        patch("auto_assemble.migrate_test.push_distribution", return_value=0) as mock_push,
        patch("auto_assemble.migrate_test.logging.info") as mock_logging_info,
        patch("pathlib.Path.unlink"),
        patch("pathlib.Path.touch") as mock_touch,
    ):
        # Setup mocks
        mock_project_config = MagicMock(spec=ProjectConfig)
        mock_project_config.is_sign_config_valid.return_value = True
        mock_sign_config = MagicMock(spec=SignConfig)
        mock_project_config.get_sign_config.return_value = mock_sign_config
        mock_fetch_project.return_value = mock_project_config

        mock_sign.return_value = (setup_config.cur_task_dir / "signed.apk", 1024, "abc123md5")
        mock_update_metadata.return_value = ("new_md5", "metadata_content")
        mock_parse_metadata.return_value = BuildMetadata(
            package_name="com.example.test",
            version_name="1.0.0",
            version_code=1,
            build_type="release",
            flavor="default",
            build_date="20250611",
            file_size=1024,
            md5="abc123md5",
            is_normalized=True,
            is_obfuscated=False,
        )

        # Create mock files without calling touch()
        source_apk = setup_config.cur_task_dir / f"{setup_config.cur_task_dir.name}.apk"
        metadata_md = setup_config.cur_task_dir / "release-metadata.md"
        with patch.object(Path, "exists", side_effect=lambda: True):  # Simulate files exist
            # Run the function
            with pytest.raises(BusinessException) as exc_info:
                migrate_test_to_release(task_info)

        # Assertions
        assert exc_info.value.code == 0  # Success exit code
        mock_download.assert_called_once_with(task_info, setup_config.cur_task_dir)
        mock_normalize.assert_called_once_with(source_apk, Path("/app/temp/normalized.apk"))
        mock_sign.assert_called_once_with(Path("/app/temp/normalized.apk"), mock_sign_config, source_apk)
        mock_update_metadata.assert_called_once_with(metadata_md, "abc123md5", 1024, True)
        mock_parse_metadata.assert_called_once_with("metadata_content")
        mock_record_metadata.assert_called_once()
        mock_push.assert_called_once()
        mock_logging_info.assert_any_call("成功复制并更新metadata文件")
        mock_touch.assert_called_once_with()  # Only md5_path.touch() should be called


def test_migrate_test_invalid_sign_config(setup_config, task_info, tmp_path):
    # Mock dependencies
    with (
        patch("auto_assemble.migrate_test.config", setup_config),
        patch("auto_assemble.migrate_test.download_task_resp"),
        patch("auto_assemble.migrate_test.fetch_project_info_by_prod_name") as mock_fetch_project,
        patch("auto_assemble.migrate_test.logging.info") as mock_logging_info,
        patch("pathlib.Path.unlink") as mock_unlink,
    ):
        # Setup mocks
        mock_project_config = MagicMock(spec=ProjectConfig)
        mock_project_config.is_sign_config_valid.return_value = False
        mock_fetch_project.return_value = mock_project_config

        # Create mock files without calling touch()
        with patch.object(Path, "exists", side_effect=lambda: True):  # Simulate files exist
            # Run the function
            with pytest.raises(BusinessException) as exc_info:
                migrate_test_to_release(task_info)

        # Assertions
        assert exc_info.value.code == 12016  # Invalid sign config error
        mock_logging_info.assert_called_with("签名配置无效")
        assert mock_unlink.call_count == 4  # Cleanup called for all files


def test_migrate_test_normalization_failure(setup_config, task_info, tmp_path):
    # Mock dependencies
    with (
        patch("auto_assemble.migrate_test.config", setup_config),
        patch("auto_assemble.migrate_test.download_task_resp"),
        patch("auto_assemble.migrate_test.fetch_project_info_by_prod_name") as mock_fetch_project,
        patch(
            "auto_assemble.migrate_test.exec_normalized_apk",
            side_effect=subprocess.CalledProcessError(1, ["ApkNormalized"]),
        ) as mock_normalize,
        patch("auto_assemble.migrate_test.logging.exception") as mock_logging_exception,
        patch("pathlib.Path.unlink") as mock_unlink,
    ):
        # Setup mocks
        mock_project_config = MagicMock(spec=ProjectConfig)
        mock_project_config.is_sign_config_valid.return_value = True
        mock_sign_config = MagicMock(spec=SignConfig)
        mock_project_config.get_sign_config.return_value = mock_sign_config
        mock_fetch_project.return_value = mock_project_config

        # Create mock files without calling touch()
        with patch.object(Path, "exists", side_effect=lambda: True):  # Simulate files exist
            # Run the function
            with pytest.raises(BusinessException) as exc_info:
                migrate_test_to_release(task_info)

        # Assertions
        assert exc_info.value.code == 12015  # General error code
        mock_normalize.assert_called_once()
        mock_logging_exception.assert_called_once()
        assert mock_unlink.call_count == 4  # Cleanup called for existing files


def test_migrate_test_signing_failure(setup_config, task_info, tmp_path):
    # Mock dependencies
    with (
        patch("auto_assemble.migrate_test.config", setup_config),
        patch("auto_assemble.migrate_test.download_task_resp"),
        patch("auto_assemble.migrate_test.fetch_project_info_by_prod_name") as mock_fetch_project,
        patch("auto_assemble.migrate_test.exec_normalized_apk") as mock_normalize,
        patch("auto_assemble.migrate_test.sign_apk", side_effect=FileNotFoundError("apksigner not found")) as mock_sign,
        patch("auto_assemble.migrate_test.logging.exception") as mock_logging_exception,
        patch("pathlib.Path.unlink") as mock_unlink,
    ):
        # Setup mocks
        mock_project_config = MagicMock(spec=ProjectConfig)
        mock_project_config.is_sign_config_valid.return_value = True
        mock_sign_config = MagicMock(spec=SignConfig)
        mock_project_config.get_sign_config.return_value = mock_sign_config
        mock_fetch_project.return_value = mock_project_config

        # Create mock files without calling touch()
        with patch.object(Path, "exists", side_effect=lambda: True):  # Simulate files exist
            # Run the function
            with pytest.raises(BusinessException) as exc_info:
                migrate_test_to_release(task_info)

        # Assertions
        assert exc_info.value.code == 12015
        mock_normalize.assert_called_once()
        mock_sign.assert_called_once()
        mock_logging_exception.assert_called_once()
        assert mock_unlink.call_count == 5  # Cleanup for source_apk, normalized_apk, metadata_md


def test_migrate_test_push_distribution_failure(setup_config, task_info, tmp_path):
    # Mock dependencies
    with (
        patch("auto_assemble.migrate_test.config", setup_config),
        patch("auto_assemble.migrate_test.download_task_resp"),
        patch("auto_assemble.migrate_test.fetch_project_info_by_prod_name") as mock_fetch_project,
        patch("auto_assemble.migrate_test.exec_normalized_apk"),
        patch("auto_assemble.migrate_test.sign_apk") as mock_sign,
        patch("auto_assemble.migrate_test.update_metadata_md") as mock_update_metadata,
        patch("auto_assemble.migrate_test.parse_metadata") as mock_parse_metadata,
        patch("auto_assemble.migrate_test.record_task_metadata"),
        patch("auto_assemble.migrate_test.push_distribution", return_value=11007) as mock_push,
        patch("auto_assemble.migrate_test.logging.warning") as mock_logging_warning,
        patch("pathlib.Path.unlink"),
        patch("pathlib.Path.touch") as mock_touch,
    ):
        # Setup mocks
        mock_project_config = MagicMock(spec=ProjectConfig)
        mock_project_config.is_sign_config_valid.return_value = True
        mock_sign_config = MagicMock(spec=SignConfig)
        mock_project_config.get_sign_config.return_value = mock_sign_config
        mock_fetch_project.return_value = mock_project_config
        mock_sign.return_value = (setup_config.cur_task_dir / "signed.apk", 1024, "abc123md5")
        mock_update_metadata.return_value = ("new_md5", "metadata_content")
        mock_parse_metadata.return_value = BuildMetadata(
            package_name="com.example.test",
            version_name="1.0.0",
            version_code=1,
            build_type="release",
            flavor="default",
            build_date="20250611",
            file_size=1024,
            md5="abc123md5",
            is_normalized=True,
            is_obfuscated=False,
        )

        # Create mock files without calling touch()
        with patch.object(Path, "exists", side_effect=lambda: True):  # Simulate files exist
            # Run the function
            with pytest.raises(BusinessException) as exc_info:
                migrate_test_to_release(task_info)

        # Assertions
        assert exc_info.value.code == 11007  # Push distribution error code
        mock_push.assert_called_once()
        mock_logging_warning.assert_called_with("push.py执行中断")
        mock_touch.assert_called_once()  # Only md5_path.touch() should be called


def test_migrate_test_missing_files(setup_config, task_info):
    # Mock dependencies
    with (
        patch("auto_assemble.migrate_test.config", setup_config),
        patch("auto_assemble.migrate_test.download_task_resp"),
        patch("auto_assemble.migrate_test.fetch_project_info_by_prod_name") as mock_fetch_project,
        patch("auto_assemble.migrate_test.exec_normalized_apk", side_effect=FileNotFoundError("APK not found")),
        patch("auto_assemble.migrate_test.logging.exception") as mock_logging_exception,
        patch("pathlib.Path.unlink") as mock_unlink,
    ):
        # Setup mocks
        mock_project_config = MagicMock(spec=ProjectConfig)
        mock_project_config.is_sign_config_valid.return_value = True
        mock_sign_config = MagicMock(spec=SignConfig)
        mock_project_config.get_sign_config.return_value = mock_sign_config
        mock_fetch_project.return_value = mock_project_config

        # Simulate no files exist
        with patch.object(Path, "exists", side_effect=lambda: False):  # Simulate no files
            # Run the function
            with pytest.raises(BusinessException) as exc_info:
                migrate_test_to_release(task_info)

        # Assertions
        assert exc_info.value.code == 12015
        mock_logging_exception.assert_called_once()
        mock_unlink.assert_not_called()  # No files exist, so unlink should not be called


def test_migrate_test_invalid_timestamp(setup_config, task_info, tmp_path):
    # Mock dependencies
    with (
        patch("auto_assemble.migrate_test.config", setup_config),
        patch("auto_assemble.migrate_test.download_task_resp"),
        patch("auto_assemble.migrate_test.fetch_project_info_by_prod_name") as mock_fetch_project,
        patch("auto_assemble.migrate_test.exec_normalized_apk"),
        patch("auto_assemble.migrate_test.sign_apk") as mock_sign,
        patch("auto_assemble.migrate_test.update_metadata_md") as mock_update_metadata,
        patch("auto_assemble.migrate_test.parse_metadata") as mock_parse_metadata,
        patch("auto_assemble.migrate_test.record_task_metadata"),
        patch("auto_assemble.migrate_test.push_distribution", return_value=11007) as mock_push,
        patch("auto_assemble.migrate_test.logging.warning") as mock_logging_warning,
        patch("pathlib.Path.unlink"),
        patch("pathlib.Path.touch"),
    ):
        # Setup mocks
        mock_project_config = MagicMock(spec=ProjectConfig)
        mock_project_config.is_sign_config_valid.return_value = True
        mock_sign_config = MagicMock(spec=SignConfig)
        mock_project_config.get_sign_config.return_value = mock_sign_config
        mock_fetch_project.return_value = mock_project_config
        mock_sign.return_value = (setup_config.cur_task_dir / "signed.apk", 1024, "abc123md5")
        mock_update_metadata.return_value = ("new_md5", "metadata_content")
        mock_parse_metadata.return_value = BuildMetadata(
            package_name="com.example.test",
            version_name="1.0.0",
            version_code=1,
            build_type="release",
            flavor="default",
            build_date="20250611",
            file_size=1024,
            md5="abc123md5",
            is_normalized=True,
            is_obfuscated=False,
        )

        # Create mock files with invalid timestamp
        setup_config.cur_task_dir = tmp_path / "invalid_timestamp"
        setup_config.cur_task_dir.mkdir()
        with patch.object(Path, "exists", side_effect=lambda: True):  # Simulate files exist
            # Run the function
            with pytest.raises(BusinessException) as exc_info:
                migrate_test_to_release(task_info)

        # Assertions
        assert exc_info.value.code == 11007  # Invalid timestamp leads to push failure
        mock_push.assert_called_once()
        mock_logging_warning.assert_called_with("push.py执行中断")


def test_migrate_test_api_failure(setup_config, task_info, tmp_path):
    # Mock dependencies
    with (
        patch("auto_assemble.migrate_test.config", setup_config),
        patch("auto_assemble.migrate_test.download_task_resp"),
        patch("auto_assemble.migrate_test.fetch_project_info_by_prod_name", return_value=None),
        patch("auto_assemble.migrate_test.logging.info") as mock_logging_info,
        patch("pathlib.Path.unlink") as mock_unlink,
    ):
        # Create mock files without calling touch()
        with patch.object(Path, "exists", side_effect=lambda: True):  # Simulate files exist
            # Run the function
            with pytest.raises(BusinessException) as exc_info:
                migrate_test_to_release(task_info)

        # Assertions
        assert exc_info.value.code == 12016  # Treated as invalid sign config
        mock_logging_info.assert_called_with("签名配置无效")
        assert mock_unlink.call_count == 4  # Cleanup called for existing files
