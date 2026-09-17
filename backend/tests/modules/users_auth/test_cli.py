import asyncio
import os
import subprocess
import sys

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.pool import NullPool

from app import cli
from app.core.config import get_settings
from tests.db_utils import BACKEND_DIR


def test_create_admin_rejects_mismatched_passwords(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    answers = iter(["First-Password-1", "Second-Password-2"])
    monkeypatch.setattr(cli.getpass, "getpass", lambda prompt="": next(answers))

    exit_code = cli.main(["create-admin", "--email", "a@company.ru", "--full-name", "Админ"])

    assert exit_code == 1
    assert "не совпадают" in capsys.readouterr().err


def _run_cli_in_fresh_process(email: str, password: str) -> subprocess.CompletedProcess[str]:
    """Запуск как в реальности: новый интерпретатор без импорта app.main.

    start_new_session отвязывает процесс от терминала, и getpass читает пароль из stdin.
    """
    env = {
        **os.environ,
        "APP_ENV": "test",
        "DATABASE_URL": get_settings().database_url,
        "PYTHONWARNINGS": "ignore::getpass.GetPassWarning",
    }
    return subprocess.run(
        [sys.executable, "-m", "app.cli", "create-admin", "--email", email, "--full-name", "Админ"],
        input=f"{password}\n{password}\n",
        capture_output=True,
        text=True,
        cwd=BACKEND_DIR,
        env=env,
        timeout=60,
        start_new_session=True,
        check=False,
    )


async def _delete_user(email: str) -> None:
    engine = create_async_engine(get_settings().database_url, poolclass=NullPool)
    try:
        async with engine.begin() as connection:
            user_id = await connection.scalar(
                text("SELECT id FROM common.users WHERE email = :email"), {"email": email}
            )
            if user_id is not None:
                await connection.execute(
                    text(
                        "DELETE FROM common.audit_log "
                        "WHERE entity_type = 'user' AND entity_id = :id"
                    ),
                    {"id": str(user_id)},
                )
                await connection.execute(
                    text("DELETE FROM common.users WHERE id = :id"), {"id": user_id}
                )
    finally:
        await engine.dispose()


async def _user_role(email: str) -> str | None:
    engine = create_async_engine(get_settings().database_url, poolclass=NullPool)
    try:
        async with engine.connect() as connection:
            role: str | None = await connection.scalar(
                text("SELECT role FROM common.users WHERE email = :email"), {"email": email}
            )
            return role
    finally:
        await engine.dispose()


async def test_create_admin_in_fresh_process_creates_admin_and_rejects_duplicate() -> None:
    email = "cli-fresh-process@company.ru"
    await _delete_user(email)
    try:
        created = await asyncio.to_thread(_run_cli_in_fresh_process, email, "Strong-Pass-123")
        assert created.returncode == 0, created.stderr
        assert "Создан администратор id=" in created.stdout
        assert await _user_role(email) == "admin"

        duplicate = await asyncio.to_thread(_run_cli_in_fresh_process, email, "Strong-Pass-123")
        assert duplicate.returncode == 1, duplicate.stderr
        assert "Ошибка: Пользователь с таким email уже существует" in duplicate.stderr
    finally:
        await _delete_user(email)
