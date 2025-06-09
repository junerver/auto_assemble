# 错误码映射字典
import sys

ERROR_CODES = {
    # 通过异常跳出执行逻辑
    0: ("成功", 0),
    # 打包服务器错误 (100xx)
    10001: ("项目未在自动打包系统中创建、配置", 1),
    10002: ("打包服务器失败重试超时", 2),
    10003: ("打包服务器主动停止任务", 3),
    10004: ("打包服务器本地环境检查出错", 4),
    10005: ("打包服务器缺少 rar、zip 依赖库", 5),
    # 本地分发仓库错误 (110xx)
    11001: ("本地分发仓库不存在", 11),
    11002: ("打包服务器本地分发仓库同步失败", 12),
    11003: ("本次打包任务所在文件夹已经存在产物", 13),
    11004: ("本次打包任务指向的目录中没有压缩文件", 14),
    11005: ("对UniApp资源包压缩文件内容检查失败", 15),
    11006: ("分发仓库没有任何更新", 16),
    11007: ("分发仓库中需要提交的文件错误", 17),
    11008: ("分发仓库中没有需要提交的apk", 18),
    11009: ("分发仓库执行 git add 失败", 19),
    11010: ("分发仓库中没有待提交文件", 20),
    11011: ("分发仓库待提交文件校验失败", 21),
    11012: ("分发仓库执行 git commit 失败", 22),
    11013: ("用户取消push", 23),
    11014: ("分发仓库执行 git push 失败", 24),
    11015: ("构建模式错误，非构建工具发起的构建请求", 25),
    11016: ("解析readme文件失败", 26),
    # 本机基座工程错误 (120xx)
    12001: ("基座工程分支检查失败", 31),
    12002: ("基座工程资源目录结构检查失败", 32),
    12003: ("基座工程清空资源目录失败", 33),
    12004: ("解压资源文件到基座工程失败", 34),
    12005: ("更新基座工程构建脚本失败", 35),
    12006: ("更新基座工程 dcloud_control.xml 文件失败", 36),
    12007: ("更新 AndroidManifest.xml 文件失败", 37),
    12008: ("基座工程git执行add操作失败", 38),
    12009: ("基座解析依赖失败，请检查依赖配置", 39),
    12010: ("基座工程项目校验失败，工程文件缺失", 40),
    12011: ("基座工程没有待提交的文件，资源文件未更新，终止执行", 41),
    12012: ("基座工程git执行commit操作失败", 42),
    12013: ("基座工程git执行push操作失败", 43),
    12014: ("基座工程git更新失败", 44),
    12015: ("径直归一化出错", 45),
    # 派生任务错误 (130xx)
    13001: ("请求派生任务详情失败", 91),
    13002: ("源任务指向的目录不存在", 92),
    13003: ("源任务指向的目录中缺少必要的资源文件", 93),
    13004: ("派生任务 git add 执行失败", 94),
    13005: ("派生任务 git commit 执行失败", 95),
    13006: ("派生任务 git push 执行失败", 96),
    # 基座工程构建错误 (200xx)
    20001: ("执行 Gradle 构建失败", 51),
    20002: ("复制构建产物失败", 52),
}


def _get_error_message(error_code: int) -> str:
    """根据错误码获取错误信息"""
    if sys.platform == "win32":
        error_info = ERROR_CODES.get(error_code)
        if error_info:
            return error_info[0]
    else:
        unix_error_code = _parse_unix_error_code_to_win32(error_code)
        error_info = ERROR_CODES.get(unix_error_code)
        if error_info:
            return error_info[0]
    return f"未知错误码: {error_code}"


def format_error(error_code: int) -> str:
    """格式化错误信息为 err_code:err_message 格式"""
    return f"{_parse_unix_error_code_to_win32(error_code)}:{_get_error_message(error_code)}"


def unified_error_code(error_code: int) -> int:
    """
    判断操作系统，如果是Windows，则直接返回，否则将错误码格式化为Unix/Linux规则的0-255的错误码
    """
    if sys.platform == "win32":
        return error_code
    else:
        """将错误码格式化为Unix/Linux规则的0-255的错误码"""
        error_info = ERROR_CODES.get(error_code)
        if error_info:
            return error_info[1]
    return 0


def _parse_unix_error_code_to_win32(error_code: int) -> int:
    """将Unix/Linux规则的0-255的错误码转换为Windows规则的错误码"""
    if sys.platform == "win32":
        return error_code
    else:
        for key, value in ERROR_CODES.items():
            if value[1] == error_code:
                return key
    return 0
