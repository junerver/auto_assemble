import pytest
from pathlib import Path
from unittest.mock import patch, Mock
import logging

from auto_assemble.parse_readme import parse_uni_modules, parse_yaml_block, parse_readme

# 测试用的 README.md 内容模板
README_TEMPLATE = """\
# 打包要求

1. 打包使用的 HBuilderX 版本号，必须使用 4.45 以上

   HBuilderX 版本：`4.45`

2. Uniapp 打包后的资源包

3. Uniapp App ID：`__UNI__882CCF1`

4. Uniapp App key：`2b78b3e878310b084550b0efd28ab762`

5. AbiFilters：`"armeabi-v7a", "arm64-v8a"`

6. UrlSchemes：`identifyField`

7. manifest.json 中配置的版本名称 versionName、版本号 versionCode

   版本名称 versionName：`1.2.1`

   版本号 versionCode：`121`

8. 提供 Android 基座需要添加、移除的权限列表，基座默认权限如下：

```xml
<uses-permission android:name="android.permission.INTERNET" />
<uses-permission android:name="android.permission.READ_EXTERNAL_STORAGE" />
<uses-permission android:name="android.permission.WRITE_EXTERNAL_STORAGE" />
<uses-permission android:name="android.permission.READ_PHONE_STATE" />
<uses-permission android:name="android.permission.ACCESS_NETWORK_STATE" />
<uses-permission android:name="android.permission.ACCESS_WIFI_STATE" />
<uses-permission android:name="com.asus.msa.SupplementaryDID.ACCESS" />
<uses-permission android:name="com.huawei.android.launcher.permission.CHANGE_BADGE" />
<uses-permission android:name="android.permission.INSTALL_PACKAGES" />
<uses-permission android:name="android.permission.REQUEST_INSTALL_PACKAGES" />
```

需要额外添加：

```xml
<uses-feature android:name="android.hardware.camera"/>
<uses-feature android:name="android.hardware.camera.autofocus"/>
<uses-permission android:name="android.permission.ACCESS_FINE_LOCATION"/>
<uses-permission android:name="android.permission.ACCESS_NETWORK_STATE"/>
<uses-permission android:name="android.permission.ACCESS_WIFI_STATE"/>
<uses-permission android:name="android.permission.CAMERA"/>
<uses-permission android:name="android.permission.CHANGE_NETWORK_STATE"/>
<uses-permission android:name="android.permission.CHANGE_WIFI_STATE"/>
<uses-permission android:name="android.permission.FLASHLIGHT"/>
<uses-permission android:name="android.permission.INTERNET"/>
<uses-permission android:name="android.permission.MODIFY_AUDIO_SETTINGS"/>
<uses-permission android:name="android.permission.READ_EXTERNAL_STORAGE"/>
<uses-permission android:name="android.permission.READ_PHONE_STATE"/>
<uses-permission android:name="android.permission.VIBRATE"/>
<uses-permission android:name="android.permission.WAKE_LOCK"/>
<uses-permission android:name="android.permission.WRITE_EXTERNAL_STORAGE"/>
```

需要移除：

```xml
<uses-permission android:name="android.permission.RECORD_AUDIO"/>
<uses-permission android:name="android.permission.MOUNT_UNMOUNT_FILESYSTEMS"/>
<uses-permission android:name="android.permission.READ_LOGS"/>
<uses-permission android:name="android.permission.WRITE_SETTINGS"/>
<uses-permission android:name="android.permission.GET_ACCOUNTS"/>
```

9. 模块信息：

    > - Share : weixin
    > - Maps : amap
    > - Payment : weixin
    > - Geolocation : system
    > - Camera
    > - VideoPlayer

10. 第三方平台配置信息：

```yaml
wechat:
  appid: wx4d4456070d11a01a
  secret: b8ad75cd1cd6715de7d27b350e1814a5
amap:
  appkey: 0cce8770e83236802f5fd1babf5685f1
getui:
  appid: dbHI7BqlG677wQgCaWN5Z
jpush:
  appkey: 2f114c80b8807cb5a222689e
oppo:
  appkey: a2c5a87ccb5541d4b0d031a902b4c880
  appid: "32935453"
  secret: 082cb6c2c21344c391e02a48355e1f29
vivo:
  appkey: 8e55630819c7f64b654dd9d6f568a21f
  appid: "105876367"
honor:
  appid: "104494234"
huawei:
  appid: "113676289"
```
"""


# 测试 parse_uni_modules 函数
class TestParseUniModules:
    def test_successful_parsing(self):
        """测试成功解析模块信息"""
        result = parse_uni_modules(README_TEMPLATE)
        expected = [
            "Share : weixin",
            "Maps : amap",
            "Payment : weixin",
            "Geolocation : system",
            "Camera",
            "VideoPlayer",
        ]
        assert result == expected

    def test_no_modules_section(self):
        """测试未找到模块信息部分"""
        content = "# 打包要求\n没有模块信息部分"
        result = parse_uni_modules(content)
        assert result == []

    def test_empty_modules(self):
        """测试空模块列表"""
        content = """# 打包要求
9. 模块信息：

    > - 
"""
        result = parse_uni_modules(content)
        assert result == [""]

    def test_parsing_error(self):
        """测试解析错误处理"""
        # 使用无效的正则表达式模式来模拟解析错误
        with patch("re.search", side_effect=Exception("Regex error")):
            result = parse_uni_modules(README_TEMPLATE)
            assert result == []


# 测试 parse_yaml_block 函数
class TestParseYamlBlock:
    def test_successful_parsing(self):
        """测试成功解析 YAML 代码块"""
        result = parse_yaml_block(README_TEMPLATE)
        expected = {
            "wechat": {"appid": "wx4d4456070d11a01a", "secret": "b8ad75cd1cd6715de7d27b350e1814a5"},
            "amap": {"appkey": "0cce8770e83236802f5fd1babf5685f1"},
            "getui": {"appid": "dbHI7BqlG677wQgCaWN5Z"},
            "jpush": {"appkey": "2f114c80b8807cb5a222689e"},
            "oppo": {
                "appkey": "a2c5a87ccb5541d4b0d031a902b4c880",
                "appid": "32935453",
                "secret": "082cb6c2c21344c391e02a48355e1f29",
            },
            "vivo": {"appkey": "8e55630819c7f64b654dd9d6f568a21f", "appid": "105876367"},
            "honor": {"appid": "104494234"},
            "huawei": {"appid": "113676289"},
        }
        assert result == expected

    def test_no_yaml_block(self):
        """测试未找到 YAML 代码块"""
        content = "# 打包要求\n没有 YAML 代码块"
        result = parse_yaml_block(content)
        assert result == {}

    def test_invalid_yaml(self):
        """测试无效的 YAML 内容"""
        content = """# 打包要求
```yaml
invalid: yaml: content
```
"""
        result = parse_yaml_block(content)
        assert result == {}

    def test_special_characters(self):
        """测试特殊字符处理，不是需要解析的内容，返回值是空字典"""
        content = """# 打包要求
```yaml
key1: "%value1%"
key2: "value2"
key3: "%value3%"
```
"""
        result = parse_yaml_block(content)
        assert result == {}


# 测试 parse_readme 函数
class TestParseReadme:
    @pytest.fixture
    def setup_readme(self, tmp_path):
        """创建临时 README.md 文件"""
        readme_path = tmp_path / "README.md"
        with open(readme_path, "w", encoding="utf-8") as f:
            f.write(README_TEMPLATE)
        return readme_path

    @pytest.fixture(autouse=True)
    def setup_config(self):
        """设置测试配置"""
        from common.config import config

        config._prod_name = "test_project"
        yield
        config._prod_name = None

    def test_successful_parsing(self, setup_readme, caplog):
        """测试成功解析 README.md 文件"""
        # 设置日志捕获
        caplog.set_level(logging.INFO)

        # 模拟服务器响应
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "third_party_configs": [
                {
                    "provider": "wechat",
                    "description": "微信开放平台申请的appid",
                    "dict_key": "WX_APPID",
                    "dict_value": "appid",
                    "config_value": "wx4d4456070d11a01a",
                },
                {
                    "provider": "wechat",
                    "description": "微信开放平台申请的secret",
                    "dict_key": "WX_SECRET",
                    "dict_value": "secret",
                    "config_value": "b8ad75cd1cd6715de7d27b350e1814a5",
                },
                {
                    "provider": "amap",
                    "description": "高德开放平台申请的appkey",
                    "dict_key": "AMAP_APIKEY",
                    "dict_value": "appkey",
                    "config_value": "0cce8770e83236802f5fd1babf5685f1",
                },
                {
                    "provider": "getui",
                    "description": "个推平台申请的appid",
                    "dict_key": "GETUI_APPID",
                    "dict_value": "appid",
                    "config_value": "dbHI7BqlG677wQgCaWN5Z",
                },
                {
                    "provider": "jpush",
                    "description": "极光推送申请的appkey",
                    "dict_key": "JPUSH_APPKEY",
                    "dict_value": "appkey",
                    "config_value": "2f114c80b8807cb5a222689e",
                },
                {
                    "provider": "oppo",
                    "description": "oppo推送的appkey",
                    "dict_key": "OPPO_APPKEY",
                    "dict_value": "appkey",
                    "config_value": "a2c5a87ccb5541d4b0d031a902b4c880",
                },
                {
                    "provider": "oppo",
                    "description": "oppo推送的appid",
                    "dict_key": "OPPO_APPID",
                    "dict_value": "appid",
                    "config_value": "32935453",
                },
                {
                    "provider": "oppo",
                    "description": "oppo推送的appsecret",
                    "dict_key": "OPPO_APPSECRET",
                    "dict_value": "secret",
                    "config_value": "082cb6c2c21344c391e02a48355e1f29",
                },
                {
                    "provider": "vivo",
                    "description": "vivo推送的appkey",
                    "dict_key": "VIVO_APPKEY",
                    "dict_value": "appkey",
                    "config_value": "8e55630819c7f64b654dd9d6f568a21f",
                },
                {
                    "provider": "vivo",
                    "description": "vivo推送的appid",
                    "dict_key": "VIVO_APPID",
                    "dict_value": "appid",
                    "config_value": "105876367",
                },
                {
                    "provider": "honor",
                    "description": "honor推送的appid",
                    "dict_key": "HONOR_APP_ID",
                    "dict_value": "appid",
                    "config_value": "104494234",
                },
                {
                    "provider": "huawei",
                    "description": "华为推送的appid",
                    "dict_key": "HUAWEI_APP_ID",
                    "dict_value": "appid",
                    "config_value": "113676289",
                },
            ]
        }

        with patch("requests.get", return_value=mock_response):
            result = parse_readme(setup_readme)

        # 验证返回结果
        assert isinstance(result, dict)
        assert result["hbx_version"] == "4.45"
        assert result["version_name"] == "1.2.1"
        assert result["version_code"] == "121"
        assert result["uniapp_id"] == "__UNI__882CCF1"
        assert result["uniapp_key"] == "2b78b3e878310b084550b0efd28ab762"
        assert result["abi_filters"] == '"armeabi-v7a", "arm64-v8a"'
        assert result["schemes"] == "identifyField"
        assert result["modules"] == [
            "Share : weixin",
            "Maps : amap",
            "Payment : weixin",
            "Geolocation : system",
            "Camera",
            "VideoPlayer",
        ]
        assert result["third_party_config"] == {
            "wechat": {
                "appid": "wx4d4456070d11a01a",
                "secret": "b8ad75cd1cd6715de7d27b350e1814a5",
            },
            "amap": {"appkey": "0cce8770e83236802f5fd1babf5685f1"},
            "getui": {"appid": "dbHI7BqlG677wQgCaWN5Z"},
            "jpush": {"appkey": "2f114c80b8807cb5a222689e"},
            "oppo": {
                "appkey": "a2c5a87ccb5541d4b0d031a902b4c880",
                "appid": "32935453",
                "secret": "082cb6c2c21344c391e02a48355e1f29",
            },
            "vivo": {"appkey": "8e55630819c7f64b654dd9d6f568a21f", "appid": "105876367"},
            "honor": {"appid": "104494234"},
            "huawei": {"appid": "113676289"},
        }

    def test_file_not_found(self, caplog):
        """测试文件不存在的情况"""
        result = parse_readme(Path("/path/that/does/not/exist/README.md"))
        assert result is None
        assert "README.md 文件不存在" in caplog.text

    def test_server_request_failure(self, setup_readme, caplog):
        """测试服务器请求失败时使用本地解析"""
        # 设置日志捕获
        caplog.set_level(logging.INFO)

        # 模拟服务器请求失败
        mock_response = Mock()
        mock_response.status_code = 404

        with patch("requests.get", return_value=mock_response):
            result = parse_readme(setup_readme)

        # 验证返回结果
        assert isinstance(result, dict)
        assert result["hbx_version"] == "4.45"
        assert result["version_name"] == "1.2.1"
        assert result["version_code"] == "121"
        assert result["uniapp_id"] == "__UNI__882CCF1"
        assert result["uniapp_key"] == "2b78b3e878310b084550b0efd28ab762"
        assert result["abi_filters"] == '"armeabi-v7a", "arm64-v8a"'
        assert result["schemes"] == "identifyField"
        assert result["modules"] == [
            "Share : weixin",
            "Maps : amap",
            "Payment : weixin",
            "Geolocation : system",
            "Camera",
            "VideoPlayer",
        ]
        assert result["third_party_config"] == {
            "wechat": {
                "appid": "wx4d4456070d11a01a",
                "secret": "b8ad75cd1cd6715de7d27b350e1814a5",
            },
            "amap": {"appkey": "0cce8770e83236802f5fd1babf5685f1"},
            "getui": {"appid": "dbHI7BqlG677wQgCaWN5Z"},
            "jpush": {"appkey": "2f114c80b8807cb5a222689e"},
            "oppo": {
                "appkey": "a2c5a87ccb5541d4b0d031a902b4c880",
                "appid": "32935453",
                "secret": "082cb6c2c21344c391e02a48355e1f29",
            },
            "vivo": {"appkey": "8e55630819c7f64b654dd9d6f568a21f", "appid": "105876367"},
            "honor": {"appid": "104494234"},
            "huawei": {"appid": "113676289"},
        }

    def test_identify_field_project(self, setup_readme, caplog):
        """测试识田间项目的特殊处理"""
        # 设置日志捕获
        caplog.set_level(logging.INFO)

        # 设置项目名称为识田间
        from common.config import config

        config._prod_name = "identify_field"

        # 模拟服务器请求失败
        mock_response = Mock()
        mock_response.status_code = 404

        with patch("requests.get", return_value=mock_response):
            result = parse_readme(setup_readme)

        # 验证返回结果
        assert isinstance(result, dict)
        assert result["third_party_config"]["wechat"] == {
            "appid": "wx4d4456070d11a01a",
            "secret": "b8ad75cd1cd6715de7d27b350e1814a5",
        }
        assert "识田间项目使用正式微信配置" in caplog.text

    def test_partial_information(self, tmp_path, caplog):
        """测试部分信息缺失的情况"""
        # 创建只有部分信息的 README.md
        partial_readme = tmp_path / "README.md"
        with open(partial_readme, "w", encoding="utf-8") as f:
            f.write(
                """# 打包要求
1. 打包使用的 HBuilderX 版本号，必须使用 4.45 以上

   HBuilderX 版本：`4.45`
"""
            )

        # 模拟服务器响应
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"third_party_configs": {}}

        with patch("requests.get", return_value=mock_response):
            result = parse_readme(partial_readme)

        # 验证返回结果
        assert isinstance(result, dict)
        assert result["hbx_version"] == "4.45"
        assert result["version_name"] == ""
        assert result["version_code"] == ""
        assert result["uniapp_id"] == ""
        assert result["uniapp_key"] == ""
        assert result["abi_filters"] == '"armeabi-v7a", "arm64-v8a"'
        assert result["schemes"] == ""
        assert result["modules"] == []

        # 验证日志记录
        assert "未能完整解析README.md信息" in caplog.text
