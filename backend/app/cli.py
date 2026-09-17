import argparse
import asyncio
import getpass as getpass
import sys
from collections.abc import Sequence

import app.model_registry  # noqa: F401  все модели: иначе FK users→departments не разрешится
from app.core.db import SessionFactory
from app.core.errors import AppError
from app.modules.users_auth.service import create_first_admin


async def _create_admin(email: str, full_name: str, password: str) -> int:
    async with SessionFactory() as session:
        user = await create_first_admin(
            session, email=email, full_name=full_name, password=password
        )
        return user.id


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m app.cli")
    commands = parser.add_subparsers(dest="command", required=True)
    create_admin = commands.add_parser("create-admin", help="Создать администратора")
    create_admin.add_argument("--email", required=True)
    create_admin.add_argument("--full-name", required=True)
    args = parser.parse_args(argv)

    password = getpass.getpass("Пароль: ")
    if password != getpass.getpass("Повторите пароль: "):
        print("Ошибка: пароли не совпадают", file=sys.stderr)
        return 1
    try:
        user_id = asyncio.run(_create_admin(args.email, args.full_name, password))
    except AppError as exc:
        print(f"Ошибка: {exc.message}", file=sys.stderr)
        return 1
    print(f"Создан администратор id={user_id}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
