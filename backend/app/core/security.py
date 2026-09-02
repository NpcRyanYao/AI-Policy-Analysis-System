from fastapi import Header

from app.config import get_settings
from app.core.exceptions import UnauthorizedError


def require_admin(x_admin_token: str | None = Header(default=None, alias="X-Admin-Token")) -> None:
    settings = get_settings()
    if settings.write_guard_relaxed:
        return
    expected = settings.admin_token
    if not expected:
        raise UnauthorizedError("生产环境必须配置 ADMIN_TOKEN")
    if x_admin_token != expected:
        raise UnauthorizedError("管理员令牌无效")
