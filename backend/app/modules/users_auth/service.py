"""Публичный интерфейс модуля users_auth. Другие модули импортируют только этот файл и events.py."""

from app.modules.users_auth.models import UserRole
from app.modules.users_auth.users import create_first_admin

__all__ = ["UserRole", "create_first_admin"]
