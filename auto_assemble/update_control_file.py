import logging
import re


def update_debug_status(content: str) -> str:
    """
    更新 debug 属性的注释状态，确保打包时使用正确的配置

    :param content: XML 文件内容
    :return: 更新后的内容
    """
    # 解开第二行注释，处理可能包含空格的情况
    content = re.sub(r"<!--\s*<hbuilder>\s*-->", "<hbuilder>", content)

    # 检查第四行是否已经被注释，如果没有才添加注释
    if '<!--<hbuilder debug="true" syncDebug="true">-->' not in content:
        content = re.sub(
            r'<hbuilder debug="true" syncDebug="true">',
            '<!--<hbuilder debug="true" syncDebug="true">-->',
            content,
        )
    return content


def update_control_file(control_file_path: str, uniapp_id: str) -> bool:
    """
    更新 dcloud_control.xml 文件中的 uniapp_id 和 debug 状态

    :param control_file_path: dcloud_control.xml 文件的路径
    :param uniapp_id: 要替换的新的 appid
    :return: 更新成功返回 True，失败返回 False
    """
    try:
        with open(control_file_path, "r", encoding="utf-8") as file:
            content = file.read()

        # 更新 debug 状态
        content = update_debug_status(content)

        # 正则匹配 <app appid="..."> 并替换 appid
        new_content, count = re.subn(r'(<app\s+appid=")[^"]+(")', rf"\1{uniapp_id}\2", content)

        # 如果没有匹配到内容，返回 False
        if count == 0:
            print("未找到匹配的 <app appid>，可能文件格式不正确")
            return False

        # 写回文件
        with open(control_file_path, "w", encoding="utf-8") as file:
            file.write(new_content)
        logging.info(f"成功更新 dcloud_control.xml 文件，替换 appid 为: {uniapp_id}")
        return True
    except Exception as e:
        print(f"更新 dcloud_control.xml 文件失败: {e}")
        return False
