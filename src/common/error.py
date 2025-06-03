from common.err_code import ERROR_CODES


class BusinessException(Exception):
    def __init__(self, code):
        self.code = code
        self.message = ERROR_CODES[code][0]
        super().__init__(f"[{code}] {self.message}")
