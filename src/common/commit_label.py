def get_build_req_label(build_mode: str, req_resp: str = "req") -> str:
    """
    获取构建请求标签
    Args:
        req_resp: 请求标识、响应标识
        build_mode (str): 构建模式，可选值：dev、test、release
    Returns:
        str: 构建请求标签
    """
    return f"#{build_mode}_{req_resp}# "
