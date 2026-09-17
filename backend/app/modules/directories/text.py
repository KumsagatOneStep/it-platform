"""Общая нормализация текстовых полей справочников directories.

Вынесено отдельно, чтобы не дублировать проверку "пусто после strip" в каждой
сущности (см. review round 1 задачи 10: department_name_blank).
"""

from app.core.errors import ValidationFailedError


def normalize_text_field(value: str, *, code: str, message: str) -> str:
    """Убирает пробелы по краям и отклоняет пустое после strip значение (422)."""
    normalized = value.strip()
    if not normalized:
        raise ValidationFailedError(message, code=code)
    return normalized
