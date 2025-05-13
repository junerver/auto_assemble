from typing import TypedDict


class Commit(TypedDict):
    # 提交的hash值
    id: str
    # 提交的消息
    message: str
    # 提交的标题
    title: str
    # 提交的日期
    timestamp: str
    # 提交的URL
    url: str
    # 提交的作者
    author: dict
    # 添加的文件
    added: list[str]
    # 删除的文件
    removed: list[str]
    # 修改的文件
    modified: list[str]
