"""Нормализация текстовых полей: strip и запрет пустого значения.

Общая для всех модулей, чтобы "пусто после strip" проверялось одинаково
(названия справочников, ФИО пользователя).
"""

from app.core.errors import ValidationFailedError


def normalize_text_field(value: str, *, code: str, message: str) -> str:
    """Убирает пробелы по краям и отклоняет пустое после strip значение (422)."""
    normalized = value.strip()
    if not normalized:
        raise ValidationFailedError(message, code=code)
    return normalized
