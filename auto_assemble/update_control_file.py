import logging
import re


def update_control_file(control_file_path: str, uniapp_id: str) -> bool:
    """
    更新 dcloud_control.xml 文件中的 uniapp_id，
    匹配 <app appid="..."> 并修改 appid 的值。

    :param control_file_path: dcloud_control.xml 文件的路径
    :param uniapp_id: 要替换的新的 appid
    :return: 更新成功返回 True，失败返回 False
    """
    try:
        with open(control_file_path, "r", encoding="utf-8") as file:
            content = file.read()

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
