"""Импорт всех ORM-моделей, чтобы Base.metadata знала все таблицы.

Нужен точкам входа, которые не импортируют app.main: Alembic (migrations/env.py)
и CLI (app/cli.py). Без него внешние ключи между модулями (например,
users.department_id → common.departments) не разрешаются при flush.
"""

from app.core import audit  # noqa: F401
from app.modules.directories import models as directories_models  # noqa: F401
from app.modules.users_auth import models as users_auth_models  # noqa: F401
