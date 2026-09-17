"""Импорт всех ORM-моделей для Alembic. Код приложения этот файл не импортирует."""

from app.core import audit  # noqa: F401
from app.modules.directories import models as directories_models  # noqa: F401
from app.modules.users_auth import models as users_auth_models  # noqa: F401
