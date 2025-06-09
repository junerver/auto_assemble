def normalize_bool_fields(data: dict, fields: list[str]) -> dict:
    """对 Optional[bool] 做归一化处理，None -> False"""
    for field in fields:
        data[field] = bool(data.get(field) or False)
    return data
