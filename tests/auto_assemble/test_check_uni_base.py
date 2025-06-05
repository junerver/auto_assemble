import pytest
from unittest.mock import patch, MagicMock
import logging

from auto_assemble.check_uni_base import check_uni_base
from auto_assemble.types import SignConfig

# 测试用的build.gradle内容模板
BUILD_GRADLE_TEMPLATE = """
android {
    signingConfigs {
        config {
            storeFile file('../keystore/test.keystore')
            storePassword 'test_store_pass'
            keyPassword 'test_key_pass'
            keyAlias 'test_alias'
        }
    }
}
"""

INVALID_BUILD_GRADLE = """
android {
    // 没有签名配置
}
"""


class TestCheckUniBase:
    @pytest.fixture
    def setup_android_project(self, tmp_path):
        """创建模拟的Android项目结构"""
        # 创建必需的目录和文件
        android_dir = tmp_path / "android_project"
        android_dir.mkdir()

        # 创建必需的目录
        (android_dir / "app").mkdir()
        (android_dir / "gradle").mkdir()

        # 创建必需的文件
        (android_dir / "build.gradle").touch()
        (android_dir / "settings.gradle").touch()
        (android_dir / "gradlew").touch()
        (android_dir / "gradlew.bat").touch()

        # 创建app/build.gradle文件
        build_gradle = android_dir / "app" / "build.gradle"
        with open(build_gradle, "w", encoding="utf-8") as f:
            f.write(BUILD_GRADLE_TEMPLATE)

        # 创建keystore目录和文件
        keystore_dir = android_dir / "keystore"
        keystore_dir.mkdir()
        (keystore_dir / "test.keystore").touch()

        return android_dir

    def test_successful_check(self, setup_android_project, caplog):
        """测试成功的基座检查"""
        caplog.set_level(logging.INFO)

        with patch("auto_assemble.check_uni_base.config") as mock_config:
            # 直接设置属性，不使用PropertyMock
            mock_config.ANDROID_UNI_BASE_PATH = str(setup_android_project)

            result = check_uni_base()

            assert isinstance(result, SignConfig)
            assert result.alias == "test_alias"
            assert result.ks_pass == "test_store_pass"
            assert result.key_pass == "test_key_pass"
            assert result.key_store.name == "test.keystore"
            assert "项目结构检查通过" in caplog.text
            assert "签名配置解析成功" in caplog.text

    def test_project_directory_not_exists(self, caplog):
        """测试项目目录不存在"""
        caplog.set_level(logging.ERROR)

        # 创建一个mock Path对象，让exists返回False
        mock_path = MagicMock()
        mock_path.exists = False

        with (
            patch("auto_assemble.check_uni_base.config") as mock_config,
            patch("auto_assemble.check_uni_base.Path") as mock_path_class,
        ):
            # 直接设置属性，不使用PropertyMock
            mock_config.ANDROID_UNI_BASE_PATH = "/path/that/does/not/exist"

            # 让Path构造函数返回我们的mock对象
            mock_path_class.return_value = mock_path

            with pytest.raises(FileNotFoundError) as exc_info:
                check_uni_base()

            assert "项目目录不存在" in str(exc_info.value)
            assert "项目目录不存在" in caplog.text

    def test_missing_required_items(self, tmp_path, caplog):
        """测试缺少必需的项目文件"""
        caplog.set_level(logging.ERROR)

        # 创建不完整的项目目录
        incomplete_dir = tmp_path / "incomplete_project"
        incomplete_dir.mkdir()
        (incomplete_dir / "app").mkdir()  # 只创建app目录

        with patch("auto_assemble.check_uni_base.config") as mock_config:
            # 直接设置属性，不使用PropertyMock
            mock_config.ANDROID_UNI_BASE_PATH = str(incomplete_dir)

            with pytest.raises(FileNotFoundError) as exc_info:
                check_uni_base()

            assert "项目结构不完整" in str(exc_info.value)
            assert "gradle" in str(exc_info.value)
            assert "build.gradle" in str(exc_info.value)

    def test_build_gradle_not_exists(self, setup_android_project, caplog):
        """测试app/build.gradle文件不存在"""
        caplog.set_level(logging.ERROR)

        # 删除build.gradle文件
        (setup_android_project / "app" / "build.gradle").unlink()

        with patch("auto_assemble.check_uni_base.config") as mock_config:
            # 直接设置属性，不使用PropertyMock
            mock_config.ANDROID_UNI_BASE_PATH = str(setup_android_project)

            with pytest.raises(FileNotFoundError) as exc_info:
                check_uni_base()

            assert "app/build.gradle文件不存在" in str(exc_info.value)

    def test_no_signing_config(self, setup_android_project, caplog):
        """测试没有签名配置"""
        caplog.set_level(logging.ERROR)

        # 写入无效的build.gradle内容
        build_gradle = setup_android_project / "app" / "build.gradle"
        with open(build_gradle, "w", encoding="utf-8") as f:
            f.write(INVALID_BUILD_GRADLE)

        with patch("auto_assemble.check_uni_base.config") as mock_config:
            # 直接设置属性，不使用PropertyMock
            mock_config.ANDROID_UNI_BASE_PATH = str(setup_android_project)

            with pytest.raises(ValueError) as exc_info:
                check_uni_base()

            assert "未找到 signingConfigs 区块" in str(exc_info.value)
            assert "解析签名配置失败" in caplog.text

    def test_incomplete_signing_config(self, setup_android_project, caplog):
        """测试不完整的签名配置"""
        caplog.set_level(logging.ERROR)

        # 写入不完整的签名配置
        incomplete_config = """
android {
    signingConfigs {
        config {
            storeFile file('../keystore/test.keystore')
            // 缺少其他配置
        }
    }
}
"""

        build_gradle = setup_android_project / "app" / "build.gradle"
        with open(build_gradle, "w", encoding="utf-8") as f:
            f.write(incomplete_config)

        with patch("auto_assemble.check_uni_base.config") as mock_config:
            # 直接设置属性，不使用PropertyMock
            mock_config.ANDROID_UNI_BASE_PATH = str(setup_android_project)

            with pytest.raises(ValueError) as exc_info:
                check_uni_base()

            assert "未找到签名配置信息" in str(exc_info.value)

    def test_file_read_error(self, setup_android_project, caplog):
        """测试文件读取错误"""
        caplog.set_level(logging.ERROR)

        with (
            patch("auto_assemble.check_uni_base.config") as mock_config,
            patch("builtins.open", side_effect=IOError("File read error")),
        ):
            # 直接设置属性，不使用PropertyMock
            mock_config.ANDROID_UNI_BASE_PATH = str(setup_android_project)

            with pytest.raises(ValueError) as exc_info:
                check_uni_base()

            assert "解析签名配置失败" in str(exc_info.value)
            assert "File read error" in str(exc_info.value)
