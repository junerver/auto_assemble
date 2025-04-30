from typing import TypedDict, NotRequired


class BuildMetadata(TypedDict):
    """
    构建任务产物元数据
    """

    package_name: NotRequired[str]
    version_name: NotRequired[str]
    version_code: NotRequired[int]
    build_type: NotRequired[str]
    flavor: NotRequired[str]
    build_date: NotRequired[str]
    file_size: NotRequired[int]
    md5: NotRequired[str]
