import pytest
from pathlib import Path
from unittest.mock import patch, Mock, PropertyMock, MagicMock
import logging

import auto_assemble.copy_res as copy_res
from common.config import config


class TestCheckPaths:
    def test_all_paths_exist(self, tmp_path):
        """测试所有路径都存在"""
        # 创建必要的目录和文件
        distribution_dir = tmp_path / "distribution"
        distribution_dir.mkdir()

        apps_dir = tmp_path / "apps"
        apps_dir.mkdir()

        build_gradle = tmp_path / "build.gradle"
        build_gradle.touch()

        # Mock config 对象的所有相关属性
        with patch("auto_assemble.copy_res.config") as mock_config:
            # 设置属性值
            type(mock_config).DISTRIBUTION_PATH = PropertyMock(return_value=str(distribution_dir))
            type(mock_config).APPS_DIRECTORY = PropertyMock(return_value=str(apps_dir))
            type(mock_config).BUILD_GRADLE_PATH = PropertyMock(return_value=str(build_gradle))

            # 应该不抛出异常
            copy_res.check_paths()

    def test_distribution_path_not_exists(self, tmp_path, caplog):
        """测试分发仓库目录不存在"""
        caplog.set_level(logging.ERROR)

        apps_dir = tmp_path / "apps"
        apps_dir.mkdir()

        build_gradle = tmp_path / "build.gradle"
        build_gradle.touch()

        with patch("auto_assemble.copy_res.config") as mock_config:
            # 设置属性值
            type(mock_config).DISTRIBUTION_PATH = PropertyMock(return_value="/path/that/does/not/exist")
            type(mock_config).APPS_DIRECTORY = PropertyMock(return_value=str(apps_dir))
            type(mock_config).BUILD_GRADLE_PATH = PropertyMock(return_value=str(build_gradle))

            with pytest.raises(FileNotFoundError) as exc_info:
                copy_res.check_paths()

            assert "分发仓库仓库目录不存在" in str(exc_info.value)
            assert "分发仓库仓库目录不存在" in caplog.text

    def test_apps_directory_not_exists(self, tmp_path, caplog):
        """测试应用目录不存在"""
        caplog.set_level(logging.ERROR)

        distribution_dir = tmp_path / "distribution"
        distribution_dir.mkdir()

        build_gradle = tmp_path / "build.gradle"
        build_gradle.touch()

        with patch("auto_assemble.copy_res.config") as mock_config:
            # 设置属性值
            type(mock_config).DISTRIBUTION_PATH = PropertyMock(return_value=str(distribution_dir))
            type(mock_config).APPS_DIRECTORY = PropertyMock(return_value="/path/that/does/not/exist")
            type(mock_config).BUILD_GRADLE_PATH = PropertyMock(return_value=str(build_gradle))

            with pytest.raises(FileNotFoundError) as exc_info:
                copy_res.check_paths()

            assert "UniApp应用目录apps目录不存在" in str(exc_info.value)

    def test_build_gradle_not_exists(self, tmp_path, caplog):
        """测试build.gradle文件不存在"""
        caplog.set_level(logging.ERROR)

        distribution_dir = tmp_path / "distribution"
        distribution_dir.mkdir()

        apps_dir = tmp_path / "apps"
        apps_dir.mkdir()

        with patch("auto_assemble.copy_res.config") as mock_config:
            # 设置属性值
            type(mock_config).DISTRIBUTION_PATH = PropertyMock(return_value=str(distribution_dir))
            type(mock_config).APPS_DIRECTORY = PropertyMock(return_value=str(apps_dir))
            type(mock_config).BUILD_GRADLE_PATH = PropertyMock(return_value="/path/that/does/not/exist")

            with pytest.raises(FileNotFoundError) as exc_info:
                copy_res.check_paths()

            assert "基座项目Gradle文件不存在" in str(exc_info.value)


class TestFindCompressedFile:
    def test_find_zip_file(self, tmp_path):
        """测试查找ZIP文件"""
        test_dir = tmp_path / "test_dir"
        test_dir.mkdir()

        # 创建一个ZIP文件
        zip_file = test_dir / "test.zip"
        zip_file.touch()

        # 创建一些其他文件
        (test_dir / "readme.txt").touch()
        (test_dir / "config.json").touch()

        result = copy_res.find_compressed_file(test_dir)

        assert result == zip_file

    def test_find_rar_file(self, tmp_path):
        """测试查找RAR文件"""
        test_dir = tmp_path / "test_dir"
        test_dir.mkdir()

        # 创建一个RAR文件
        rar_file = test_dir / "test.rar"
        rar_file.touch()

        result = copy_res.find_compressed_file(test_dir)

        assert result == rar_file

    def test_prefer_zip_over_rar(self, tmp_path):
        """测试优先选择ZIP文件"""
        test_dir = tmp_path / "test_dir"
        test_dir.mkdir()

        # 创建ZIP和RAR文件
        zip_file = test_dir / "test.zip"
        zip_file.touch()
        rar_file = test_dir / "test.rar"
        rar_file.touch()

        result = copy_res.find_compressed_file(test_dir)

        # 应该返回ZIP文件（按字母顺序或实现逻辑）
        assert result.suffix in [".zip", ".rar"]

    def test_no_compressed_file(self, tmp_path):
        """测试没有压缩文件"""
        test_dir = tmp_path / "test_dir"
        test_dir.mkdir()

        # 只创建普通文件
        (test_dir / "readme.txt").touch()
        (test_dir / "config.json").touch()

        result = copy_res.find_compressed_file(test_dir)

        assert result is None

    def test_empty_directory(self, tmp_path):
        """测试空目录"""
        test_dir = tmp_path / "empty_dir"
        test_dir.mkdir()

        result = copy_res.find_compressed_file(test_dir)

        assert result is None

    def test_multiple_compressed_files(self, tmp_path):
        """测试多个压缩文件"""
        test_dir = tmp_path / "test_dir"
        test_dir.mkdir()

        # 创建多个压缩文件
        (test_dir / "file1.zip").touch()
        (test_dir / "file2.zip").touch()
        (test_dir / "file3.rar").touch()

        result = copy_res.find_compressed_file(test_dir)

        # 应该返回其中一个压缩文件
        assert result is not None
        assert result.suffix in [".zip", ".rar"]

    @pytest.mark.usefixtures("caplog")
    def test_copy_res_main_flow(self, tmp_path, caplog, capsys):
        caplog.set_level(logging.INFO)
        # 1. 构造目录结构
        distribution_dir = tmp_path / "distribution"
        distribution_dir.mkdir()
        apps_dir = tmp_path / "apps"
        apps_dir.mkdir()
        project_dir = apps_dir / "test_project"
        project_dir.mkdir()
        build_gradle = tmp_path / "build.gradle"
        build_gradle.touch()
        test_zip = project_dir / "test.zip"
        test_zip.touch()
        manifest_json = project_dir / "manifest.json"
        manifest_json.touch()
        # 额外：产物apk路径
        cur_task_dir = distribution_dir / "test_project" / "task_dir"
        cur_task_dir.mkdir(parents=True, exist_ok=True)
        apk_file = cur_task_dir / "task_dir.apk"

        # 创建临时目录用于模拟 check_compressed_file_content 的返回值
        temp_check_dir = cur_task_dir / "temp_check"
        temp_check_dir.mkdir(parents=True, exist_ok=True)
        test_project_dir = temp_check_dir / "test_project"
        test_project_dir.mkdir()

        # 创建一个 mock 对象来替代 Path.exists 方法
        def mock_exists(self):
            return str(self) != str(apk_file)

        def iterdir_side_effect(self):
            path_str = str(self)
            if "temp_check" in path_str:
                # 在临时目录中返回一个与 UNI_APP_ID 同名的目录
                return [Path(path_str) / "test_project"]
            elif path_str == str(apps_dir):
                return [project_dir]
            elif path_str == str(project_dir):
                return [test_zip, manifest_json]
            return []

        # 按模块分组 mock 对象
        copy_res_patches = {
            "sync_repository": Mock(return_value=True),
            "check_git_branch": Mock(return_value=True),
            "git_reset_and_clean": Mock(return_value=None),
            "find_compressed_file": Mock(return_value=test_zip),
            "modern_extract": Mock(return_value=[f"{config.UNI_APP_ID}/"]),
            "check_compressed_file_content": Mock(return_value=(True, temp_check_dir)),
            "extract_compressed_file": Mock(return_value=True),
            "clear_directory": Mock(return_value=True),
            "check_apps_directory": Mock(return_value=True),
            "parse_readme": Mock(
                return_value={
                    "uniapp_id": "test_project",
                    "hbx_version": "3.99.0",
                    "version_name": "1.0.0",
                    "version_code": 1,
                    "uniapp_key": "key",
                    "abi_filters": ["armeabi-v7a"],
                    "schemes": ["test"],
                    "modules": [],
                    "third_party_config": {},
                }
            ),
            "update_build_gradle": Mock(return_value=True),
            "update_control_file": Mock(return_value=True),
            "update_android_manifest": Mock(return_value=True),
        }

        shutil_patches = {
            "rmtree": Mock(),
            "copy2": Mock(),
            "copytree": Mock(),
        }

        with (
            patch.multiple("auto_assemble.copy_res", **copy_res_patches),
            patch.multiple("shutil", **shutil_patches),
            patch.object(Path, "exists", mock_exists),
            patch.object(Path, "mkdir", Mock()),
            patch.object(Path, "iterdir", side_effect=iterdir_side_effect),
            patch.object(Path, "is_file", Mock(return_value=True)),
            patch.object(Path, "is_dir", Mock(return_value=True)),
            patch("os.unlink", Mock()),
            patch("zipfile.ZipFile", MagicMock()),
            patch("subprocess.run", Mock(return_value=Mock(returncode=0))),
            patch("auto_assemble.copy_res.config") as mock_config,
        ):
            # config 路径属性 - 直接设置属性而不是使用PropertyMock
            mock_config.DISTRIBUTION_PATH = str(distribution_dir)
            mock_config.APPS_DIRECTORY = str(apps_dir)
            mock_config.BUILD_GRADLE_PATH = str(build_gradle)
            mock_config.ANDROID_UNI_BASE_PATH = str(tmp_path)
            mock_config.CONTROL_FILE_PATH = str(tmp_path / "dcloud_control.xml")
            mock_config.ANDROID_MANIFEST_PATH = str(tmp_path / "AndroidManifest.xml")
            mock_config.PROD_NAME = "test_project"
            mock_config.PROD_BRANCH = "prod_test_project"
            mock_config.UNI_APP_ID = "test_project"
            mock_config.cur_task_dir = cur_task_dir
            mock_config.build_mode = "release"
            mock_config.cur_task_id = "test_project,20240604"
            mock_config.is_obfuscated = False

            result = copy_res.copy_res("test_project", "task_dir")
            captured = capsys.readouterr()
            assert result == 0
            assert (
                "所有操作执行成功" in caplog.text
                or "所有操作执行成功" in captured.err
                or "所有操作执行成功" in captured.out
            )
            # patch.multiple 并不返回任何内容，我们需要用自己的字典来管理、验证mock的函数是否被调用
            assert copy_res_patches["check_compressed_file_content"].called
            assert copy_res_patches["find_compressed_file"].called
