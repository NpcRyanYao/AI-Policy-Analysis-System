from typing import Any


class AppError(Exception):
    def __init__(self, message: str, *, status_code: int = 400, code: str = "app_error"):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.code = code


class NotFoundError(AppError):
    def __init__(self, message: str = "资源不存在"):
        super().__init__(message, status_code=404, code="not_found")


class ConflictError(AppError):
    def __init__(self, message: str = "资源冲突"):
        super().__init__(message, status_code=409, code="conflict")


class UnauthorizedError(AppError):
    def __init__(self, message: str = "未授权"):
        super().__init__(message, status_code=401, code="unauthorized")


class UpstreamError(AppError):
    def __init__(self, message: str = "上游服务不可用"):
        super().__init__(message, status_code=502, code="upstream_error")


def error_payload(exc: AppError) -> dict[str, Any]:
    return {"error": {"code": exc.code, "message": exc.message}}
