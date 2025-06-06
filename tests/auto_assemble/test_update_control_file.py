import pytest
from pathlib import Path
from unittest.mock import patch
import logging


from auto_assemble.update_control_file import update_debug_status, update_control_file

# 测试用的 XML 内容模板(正式，非debug)
VALID_XML_TEMPLATE = """<!-- 正式发布时必须使用这个 -->
<hbuilder>
<!-- 生成自定义运行基座时修改为下面的内容 -->
<!--<hbuilder debug="true" syncDebug="true">-->
    <apps>
        <!-- todo: 1. 修改uni应用id -->
        <app appid="__UNI__882CCF1" appver="" />
    </apps>
</hbuilder>
"""


# 测试 update_debug_status 函数
class TestUpdateDebugStatus:
    @pytest.mark.parametrize(
        "debug_mode, expected_second_line, expected_fourth_line",
        [
            # 非 debug 模式
            (False, "<hbuilder>", '<!--<hbuilder debug="true" syncDebug="true">-->'),
            # debug 模式
            (True, "<!--<hbuilder>-->", '<hbuilder debug="true" syncDebug="true">'),
        ],
    )
    def test_update_debug_status(self, debug_mode, expected_second_line, expected_fourth_line):
        """测试更新 debug 属性的注释状态"""
        # 准备测试数据
        content = VALID_XML_TEMPLATE

        # 执行函数
        result = update_debug_status(content, debug_mode)

        # 分割结果行
        lines = result.splitlines()

        # 验证第二行
        assert lines[1].strip() == expected_second_line
        # 验证第四行
        assert lines[3].strip() == expected_fourth_line

    def test_no_changes_when_already_correct_non_debug(self):
        """测试当已经是非 debug 模式时，不会进行任何更改"""
        # 准备已经是非 debug 模式的 XML
        content = """<!-- 正式发布时必须使用这个 -->
<hbuilder>
<!-- 生成自定义运行基座时修改为下面的内容 -->
<!--<hbuilder debug="true" syncDebug="true">-->
    <apps>
        <!-- todo: 1. 修改uni应用id -->
        <app appid="__UNI__882CCF1" appver="" />
    </apps>
</hbuilder>"""

        # 执行函数
        result = update_debug_status(content, False)

        # 验证内容未改变
        assert result == content

    def test_no_changes_when_already_correct_debug(self):
        """测试当已经是 debug 模式时，不会进行任何更改"""
        # 准备已经是 debug 模式的 XML
        content = """<!-- 正式发布时必须使用这个 -->
<!--<hbuilder>-->
<!-- 生成自定义运行基座时修改为下面的内容 -->
<hbuilder debug="true" syncDebug="true">
    <apps>
        <!-- todo: 1. 修改uni应用id -->
        <app appid="__UNI__882CCF1" appver="" />
    </apps>
</hbuilder>"""

        # 执行函数
        result = update_debug_status(content, True)

        # 验证内容未改变
        assert result == content

    @pytest.mark.parametrize("debug_mode", [False, True])
    def test_handles_whitespace_variations(self, debug_mode):
        """测试切换到 debug 模式和非 debug 模式时，处理可能包含空格的情况"""
        # 准备带有额外空格的 XML
        content = """<!-- 正式发布时必须使用这个 -->
<hbuilder>
<!-- 生成自定义运行基座时修改为下面的内容 -->
<!--<hbuilder debug="true" syncDebug="true">-->
    <apps>
        <!-- todo: 1. 修改uni应用id -->
        <app appid="__UNI__882CCF1" appver="" />
    </apps>
</hbuilder>"""

        # 执行函数
        result = update_debug_status(content, debug_mode)

        # 分割结果行
        lines = result.splitlines()

        if not debug_mode:
            # 非 debug 模式：第二行应解开注释，第四行应添加注释
            assert "<hbuilder>" in lines[1]
            assert "<!--" not in lines[1]
            assert '<!--<hbuilder debug="true" syncDebug="true">-->' in lines[3]
        else:
            # debug 模式：第二行应添加注释，第四行应解开注释
            assert "<!--<hbuilder>-->" in lines[1]
            assert '<hbuilder debug="true" syncDebug="true">' in lines[3]
            assert "<!--" not in lines[3]


# 测试 update_control_file 函数
class TestUpdateControlFile:
    @pytest.fixture
    def setup_files(self, tmp_path):
        # 创建临时文件
        file_path = tmp_path / "dcloud_control.xml"
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(VALID_XML_TEMPLATE)
        return file_path

    def test_successful_update(self, setup_files, caplog):
        """测试成功更新 dcloud_control.xml 文件"""
        # 设置日志捕获
        caplog.set_level(logging.INFO)

        # 执行函数
        result = update_control_file(setup_files, "NEW_APP_ID", False)

        # 验证返回 True
        assert result is True

        # 验证日志记录
        assert "成功更新 dcloud_control.xml 文件，替换 appid 为: NEW_APP_ID" in caplog.text

        # 读取更新后的内容
        with open(setup_files, "r", encoding="utf-8") as f:
            content = f.read()

        # 验证 appid 被替换
        assert '<app appid="NEW_APP_ID"' in content

        # 验证 debug 状态被更新（非 debug 模式）
        lines = content.splitlines()
        assert lines[1].strip() == "<hbuilder>"
        assert lines[3].strip() == '<!--<hbuilder debug="true" syncDebug="true">-->'

    def test_appid_not_found(self, tmp_path, capsys):
        """测试未找到匹配的 <app appid> 时的处理"""
        # 创建没有 app 标签的文件
        file_path = tmp_path / "invalid.xml"
        with open(file_path, "w", encoding="utf-8") as f:
            f.write("""<?xml version="1.0" encoding="UTF-8"?>
<apps>
    <no-app-here>
</apps>""")

        # 执行函数
        result = update_control_file(file_path, "NEW_APP_ID", False)

        # 验证返回 False
        assert result is False

        # 验证输出消息
        captured = capsys.readouterr()
        assert "未找到匹配的 <app appid>，可能文件格式不正确" in captured.out

    def test_debug_mode_update(self, setup_files):
        """测试在 debug 模式下更新 dcloud_control.xml 文件"""
        # 执行函数 (debug 模式)
        result = update_control_file(setup_files, "NEW_APP_ID", True)

        # 验证返回 True
        assert result is True

        # 读取更新后的内容
        with open(setup_files, "r", encoding="utf-8") as f:
            content = f.read()

        # 验证 debug 状态被更新（debug 模式）
        lines = content.splitlines()
        assert lines[1].strip() == "<!--<hbuilder>-->"
        assert lines[3].strip() == '<hbuilder debug="true" syncDebug="true">'

    def test_file_not_found(self, caplog):
        """测试文件不存在时的处理"""
        # 设置日志捕获
        caplog.set_level(logging.ERROR)

        # 使用不存在的文件路径
        non_existent_file = Path("/path/that/does/not/exist.xml")

        # 执行函数
        result = update_control_file(non_existent_file, "NEW_APP_ID", False)

        # 验证返回 False
        assert result is False

        # 验证错误消息 - 修复：使用 caplog 而不是 capsys
        assert "更新 dcloud_control.xml 文件失败" in caplog.text

    @patch("builtins.open", side_effect=PermissionError("No write permission"))
    def test_write_permission_error(self, mock_open, caplog):
        # 设置日志捕获
        caplog.set_level(logging.ERROR)

        # 创建临时文件路径
        file_path = Path("/fake/path/dcloud_control.xml")

        # 执行函数
        result = update_control_file(file_path, "NEW_APP_ID", False)

        # 验证返回 False
        assert result is False

        # 验证错误消息 - 修复：使用 caplog 而不是 capsys
        assert "更新 dcloud_control.xml 文件失败" in caplog.text
        assert "No write permission" in caplog.text

    @patch("auto_assemble.update_control_file.update_debug_status", return_value=VALID_XML_TEMPLATE)
    def test_appid_replacement_only(self, mock_update, setup_files):
        # 执行函数
        result = update_control_file(setup_files, "NEW_APP_ID", False)

        # 验证返回 True
        assert result is True

        # 读取更新后的内容
        with open(setup_files, "r", encoding="utf-8") as f:
            content = f.read()

        # 验证 appid 被替换
        assert '<app appid="NEW_APP_ID"' in content

        # 验证 debug 状态未被改变（因为模拟返回了原始内容）
        lines = content.splitlines()
        assert "<hbuilder>" in lines[1]
        assert '<!--<hbuilder debug="true" syncDebug="true">-->' in lines[3]

    @pytest.mark.parametrize(
        "original_appid",
        ["APP_ID_WITH-HYPHEN", "APP_ID_WITH_UNDERSCORE", "APP_ID_WITH.NUMBERS123", "com.example.long.app.id"],
    )
    def test_various_appid_formats(self, setup_files, original_appid):
        # 修改原始 XML 中的 appid
        modified_xml = VALID_XML_TEMPLATE.replace("OLD_APP_ID", original_appid)
        with open(setup_files, "w", encoding="utf-8") as f:
            f.write(modified_xml)

        # 执行函数
        new_appid = "REPLACED_APP_ID"
        result = update_control_file(setup_files, new_appid, False)

        # 验证返回 True
        assert result is True

        # 读取更新后的内容
        with open(setup_files, "r", encoding="utf-8") as f:
            content = f.read()

        # 验证 appid 被替换
        assert f'<app appid="{new_appid}"' in content
