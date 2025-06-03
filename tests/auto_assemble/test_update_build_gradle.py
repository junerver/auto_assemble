import pytest
from pathlib import Path
from unittest.mock import patch
import logging
from common.types import ManifestInfo

# 导入被测试的函数
from auto_assemble.update_build_gradle import update_build_gradle, _process_line, _format_manifest_placeholder

# 测试用的 build.gradle 内容模板
BUILD_GRADLE_TEMPLATE = """\
android {
    defaultConfig {
        versionCode 1
        versionName "1.0"
        ndk {
            abiFilters "armeabi-v7a", "arm64-v8a"
        }
    }
}

dependencies {
    //--------------third party dependencies begin--------------
    implementation(libs.bundles.uni.map.amap.maponly)
    //---------------third party dependencies end---------------
}

manifestPlaceholders = [
    "DCLOUD_APPID"          : "__UNI__882CCF1",
    "DCLOUD_APPKEY"         : "2b78b3e878310b084550b0efd28ab762",
    "DCLOUD_ADID"           : "",
    "DCLOUD_CHANNEL"        : "Official",
    "AMAP_APIKEY"           : "0cce8770e83236802f5fd1babf5685f1",
    "BAIDU_MAP_APIKEY"       : "%百度地图开放平台申请的AppKey%",
    "WX_APPID"              : "wx4d4456070d11a01a",
    "WX_SECRET"             : "b8ad75cd1cd6715de7d27b350e1814a5",
    "GETUI_APPID"           : "dbHI7BqlG677wQgCaWN5Z",
    "JPUSH_APPKEY"          : "2f114c80b8807cb5a222689e"
    "plus.unipush.appid"    : "unipush的appid",
    "plus.unipush.appkey"   : "unipush的key",
    "plus.unipush.appsecret": "unipush的secret",
    "apk.applicationId"     : "io.dcloud.HBuilder",
    "XIAOMI_APP_ID"         : "",
    "XIAOMI_APP_KEY"        : "",
    "MEIZU_APP_ID"          : "",
    "MEIZU_APP_KEY"         : "",
    "HUAWEI_APP_ID"         : "113676289",
    "OPPO_APP_KEY"          : "a2c5a87ccb5541d4b0d031a902b4c880",
    "OPPO_APP_SECRET"       : "082cb6c2c21344c391e02a48355e1f29",
    "VIVO_APP_ID"           : "105876367",
    "VIVO_APP_KEY"          : "8e55630819c7f64b654dd9d6f568a21f",
    "HONOR_APP_ID"          : "104494234",
]

def reqDate = "old_artifact_name"
"""

# 测试用的 version.toml 内容模板
VERSIONS_TOML_TEMPLATE = """\
[versions]
uniSdkVersion = "old_hbx_version"
"""


@pytest.fixture
def setup_files(tmp_path):
    # 创建临时 build.gradle 文件
    build_gradle_path = tmp_path / "build.gradle"
    with open(build_gradle_path, "w", encoding="utf-8") as f:
        f.write(BUILD_GRADLE_TEMPLATE)

    # 创建临时 version.toml 文件
    versions_toml_path = tmp_path / "version.toml"
    with open(versions_toml_path, "w", encoding="utf-8") as f:
        f.write(VERSIONS_TOML_TEMPLATE)

    return build_gradle_path, versions_toml_path


# 测试 _format_manifest_placeholder 函数
class TestFormatManifestPlaceholder:
    def test_basic_formatting(self):
        line = '    DCLOUD_APPID: "old_app_id",'
        result = _format_manifest_placeholder(line, "DCLOUD_APPID", "new_app_id")
        assert result == '    DCLOUD_APPID            : "new_app_id",\n'

    def test_long_key_formatting(self):
        line = '    LONG_KEY_NAME: "old_value",'
        result = _format_manifest_placeholder(line, "LONG_KEY_NAME", "new_value")
        assert result == '    LONG_KEY_NAME           : "new_value",\n'

    def test_short_key_formatting(self):
        line = '    KEY: "old_value",'
        result = _format_manifest_placeholder(line, "KEY", "new_value")
        assert result == '    KEY                     : "new_value",\n'


# 测试 _process_line 函数
class TestProcessLine:
    @pytest.mark.parametrize("debug_mode", [False, True])
    def test_reqDate_replacement(self, debug_mode, monkeypatch):
        # 模拟配置
        monkeypatch.setattr("common.config.config.build_mode", "dev" if debug_mode else "prod")

        line = 'def reqDate = "old_artifact_name"'
        artifact_name = "new_artifact_name"
        version_info = {}

        result = _process_line(line, artifact_name, version_info)

        expected_suffix = "_debug" if debug_mode else ""
        expected = f'def reqDate = "new_artifact_name{expected_suffix}"'
        assert expected in result

    def test_abiFilters_replacement(self):
        line = '            abiFilters "armeabi-v7a", "arm64-v8a"'
        artifact_name = "artifact"
        version_info = {"abi_filters": '"x86", "x86_64"'}

        result = _process_line(line, artifact_name, version_info)
        assert 'abiFilters "x86", "x86_64"' in result

    def test_versionName_replacement(self):
        line = '        versionName "1.0"'
        artifact_name = "artifact"
        version_info = {"version_name": "2.0"}

        result = _process_line(line, artifact_name, version_info)
        assert 'versionName "2.0"' in result

    def test_versionCode_replacement(self):
        line = "        versionCode 1"
        artifact_name = "artifact"
        version_info = {"version_code": "2"}

        result = _process_line(line, artifact_name, version_info)
        assert "versionCode 2" in result

    @pytest.mark.parametrize(
        "placeholder, value, config_path",
        [
            # 微信配置
            ('"WX_APPID"', "new_wx_appid", ("wechat", "appid")),
            ('"WX_SECRET"', "new_wx_secret", ("wechat", "secret")),
            # 高德地图配置
            ('"AMAP_APIKEY"', "new_amap_apikey", ("amap", "appkey")),
            # 百度地图配置
            ('"BAIDU_MAP_APIKEY"', "new_baidu_apikey", ("baidu", "appkey")),
            # 个推配置
            ('"GETUI_APPID"', "new_getui_appid", ("getui", "appid")),
            ('"JPUSH_APPKEY"', "new_jpush_appkey", ("jpush", "appkey")),
            # 小米配置
            ('"XIAOMI_APP_ID"', "new_xiaomi_app_id", ("xiaomi", "appid")),
            ('"XIAOMI_APP_KEY"', "new_xiaomi_app_key", ("xiaomi", "appkey")),
            # 魅族配置
            ('"MEIZU_APP_ID"', "new_meizu_app_id", ("meizu", "appid")),
            ('"MEIZU_APP_KEY"', "new_meizu_app_key", ("meizu", "appkey")),
            # 华为配置
            ('"HUAWEI_APP_ID"', "new_huawei_app_id", ("huawei", "appid")),
            # OPPO配置
            ('"OPPO_APP_KEY"', "new_oppo_app_key", ("oppo", "appkey")),
            ('"OPPO_APP_SECRET"', "new_oppo_secret", ("oppo", "secret")),
            # VIVO配置
            ('"VIVO_APP_ID"', "new_vivo_app_id", ("vivo", "appid")),
            ('"VIVO_APP_KEY"', "new_vivo_app_key", ("vivo", "appkey")),
            # 荣耀配置
            ('"HONOR_APP_ID"', "new_honor_app_id", ("honor", "appid")),
        ],
    )
    def test_manifest_placeholder_replacement(self, placeholder, value, config_path):
        # 确保输入行格式与代码期望一致
        line = f'    {placeholder}  : "old_value",'
        artifact_name = "artifact"

        # 构建正确的嵌套配置结构
        third_party_config = {}
        current = third_party_config
        for key in config_path[:-1]:
            current[key] = {}
            current = current[key]
        current[config_path[-1]] = value

        version_info = {"third_party_config": third_party_config}

        result = _process_line(line, artifact_name, version_info)

        # 计算正确的对齐空格
        expected_spaces = " " * (24 - len(placeholder))
        expected_line = f'    {placeholder}{expected_spaces}: "{value}",\n'
        print(expected_line)
        print(result)
        assert result == expected_line

    def test_no_change_when_no_replacement(self):
        line = '        applicationId "com.example.app"'
        artifact_name = "artifact"
        version_info = {}

        result = _process_line(line, artifact_name, version_info)
        assert result == line


# 测试 update_build_gradle 函数
class TestUpdateBuildGradle:
    def test_successful_update(self, setup_files, caplog):
        build_gradle_path, versions_toml_path = setup_files

        # 设置日志捕获级别
        caplog.set_level(logging.INFO)  # 确保捕获 INFO 级别日志
        # 模拟配置
        with patch("common.config.config._versions_toml_path", versions_toml_path):
            # 准备版本信息
            version_info = ManifestInfo(
                version_name="2.0",
                version_code=2,
                uniapp_id="new_app_id",
                uniapp_key="new_app_key",
                hbx_version="new_hbx_version",
                abi_filters='"x86", "x86_64"',
                third_party_config={
                    "wechat": {"appid": "new_wx_appid", "secret": "new_wx_secret"},
                    "amap": {"appkey": "new_amap_apikey"},
                    "baidu": {"appkey": "new_baidu_apikey"},
                    "getui": {"appid": "new_getui_appid"},
                    "jpush": {"appkey": "new_jpush_appkey"},
                },
                modules=["Share : weixin", "Maps : amap", "Geolocation : amap"],
            )

            # 执行函数
            result = update_build_gradle(build_gradle_path, "new_artifact_name", version_info)

            # 验证返回 True
            assert result is True

            # 验证日志记录
            assert "成功更新build.gradle文件" in caplog.text
            assert "更新 hbx_version 为: new_hbx_version" in caplog.text
            assert "更新 versionName 为: 2.0" in caplog.text
            assert "更新 versionCode 为: 2" in caplog.text
            assert "更新 uniapp_id 为: new_app_id" in caplog.text
            assert "更新 uniapp_key 为: new_app_key" in caplog.text

            # 验证 build.gradle 内容
            with open(build_gradle_path, "r", encoding="utf-8") as f:
                content = f.read()

            # 验证基本替换
            assert 'def reqDate = "new_artifact_name"' in content
            assert 'versionName "2.0"' in content
            assert "versionCode 2" in content
            assert 'abiFilters "x86", "x86_64"' in content

            # 验证 manifestPlaceholders
            assert '"DCLOUD_APPKEY"         : "new_app_key"' in content
            assert '"DCLOUD_APPKEY"         : "new_app_key"' in content
            assert '"WX_APPID"              : "new_wx_appid"' in content
            assert '"WX_SECRET"             : "new_wx_secret"' in content
            assert '"AMAP_APIKEY"           : "new_amap_apikey"' in content
            assert '"BAIDU_MAP_APIKEY"      : "new_baidu_apikey"' in content
            assert '"GETUI_APPID"           : "new_getui_appid"' in content
            assert '"JPUSH_APPKEY"          : "new_jpush_appkey"' in content

            # 验证第三方依赖
            assert "//--------------third party dependencies begin--------------" in content
            assert "implementation(libs.bundles.uni.share.wechat)" in content
            assert "implementation(libs.bundles.uni.amap.map.location)" in content
            assert "//---------------third party dependencies end---------------" in content

            # 验证 version.toml 更新
            with open(versions_toml_path, "r", encoding="utf-8") as f:
                versions_content = f.read()
            assert 'uniSdkVersion = "new_hbx_version"' in versions_content

    def test_module_dependency_mapping(self, setup_files):
        build_gradle_path, versions_toml_path = setup_files

        # 准备版本信息
        version_info = ManifestInfo(modules=["Maps : amap", "Geolocation : amap"])

        # 执行函数
        with patch("common.config.config._versions_toml_path", versions_toml_path):
            result = update_build_gradle(build_gradle_path, "artifact", version_info)

        # 验证返回 True
        assert result is True

        # 验证 build.gradle 内容
        with open(build_gradle_path, "r", encoding="utf-8") as f:
            content = f.read()

        # 验证合并后的依赖
        assert "implementation(libs.bundles.uni.amap.map.location)" in content
        assert "implementation(libs.bundles.uni.map.amap.maponly)" not in content
        assert "implementation(libs.bundles.uni.location.amap.locationonly)" not in content

    def test_module_not_found(self, setup_files, caplog):
        build_gradle_path, versions_toml_path = setup_files
        # 设置日志捕获级别
        caplog.set_level(logging.INFO)  # 确保捕获 INFO 级别日志
        # 准备版本信息
        version_info = ManifestInfo(modules=["Invalid : module"])

        # 执行函数并期望抛出异常
        with patch("common.config.config._versions_toml_path", versions_toml_path):
            with pytest.raises(KeyError) as exc_info:
                update_build_gradle(build_gradle_path, "artifact", version_info)

        # 验证错误日志
        assert "模块 'Invalid : module' 未找到在MODULE_DEPENDENCY_MAP中" in caplog.text
        assert "Module 'Invalid : module' not found in MODULE_DEPENDENCY_MAP" in str(exc_info.value)

    def test_no_hbx_version(self, setup_files, caplog):
        build_gradle_path, versions_toml_path = setup_files

        # 准备版本信息（不包含 hbx_version）
        version_info = ManifestInfo(version_name="2.0", modules=["Share : weixin"])

        # 执行函数
        with patch("common.config.config._versions_toml_path", versions_toml_path):
            result = update_build_gradle(build_gradle_path, "artifact", version_info)

        # 验证返回 True
        assert result is True

        # 验证 version.toml 未修改
        with open(versions_toml_path, "r", encoding="utf-8") as f:
            versions_content = f.read()
        assert 'uniSdkVersion = "old_hbx_version"' in versions_content

        # 验证日志中没有 hbx_version 更新记录
        assert "更新 hbx_version" not in caplog.text

    def test_no_modules(self, setup_files, caplog):
        build_gradle_path, versions_toml_path = setup_files

        # 准备版本信息（不包含 modules）
        version_info = ManifestInfo(
            version_name="2.0",
        )

        # 执行函数
        with patch("common.config.config._versions_toml_path", versions_toml_path):
            result = update_build_gradle(build_gradle_path, "artifact", version_info)

        # 验证返回 True
        assert result is True

        # 验证 build.gradle 内容
        with open(build_gradle_path, "r", encoding="utf-8") as f:
            content = f.read()

        # 验证第三方依赖区域保持不变
        assert "implementation(libs.bundles.uni.map.amap.maponly)" in content

    def test_file_not_found(self, caplog):
        # 使用不存在的文件路径
        non_existent_file = Path("/path/that/does/not/exist.gradle")

        # 执行函数
        result = update_build_gradle(non_existent_file, "artifact", ManifestInfo())

        # 验证返回 False
        assert result is False

        # 验证错误日志
        assert "更新build.gradle文件时发生错误" in caplog.text

    @patch("builtins.open", side_effect=PermissionError("No write permission"))
    def test_write_permission_error(self, mock_open, caplog):
        # 创建临时文件路径
        file_path = Path("/fake/path/build.gradle")

        # 执行函数
        result = update_build_gradle(file_path, "artifact", ManifestInfo())

        # 验证返回 False
        assert result is False

        # 验证错误日志
        assert "更新build.gradle文件时发生错误" in caplog.text
        assert "No write permission" in caplog.text


# 测试模块依赖映射
def test_module_dependency_map():
    # 导入被测试的映射字典
    from auto_assemble.update_build_gradle import MODULE_DEPENDENCY_MAP

    # 验证关键映射
    assert MODULE_DEPENDENCY_MAP["Share : weixin"] == "implementation(libs.bundles.uni.share.wechat)"
    assert MODULE_DEPENDENCY_MAP["Maps : amap"] == "implementation(libs.bundles.uni.map.amap.maponly)"
    assert (
        MODULE_DEPENDENCY_MAP["Maps : amap & Geolocation : amap"]
        == "implementation(libs.bundles.uni.amap.map.location)"
    )
    assert MODULE_DEPENDENCY_MAP["Geolocation : system"] is None
    assert MODULE_DEPENDENCY_MAP["VideoPlayer"] == "implementation(libs.bundles.uni.videoplayer)"
