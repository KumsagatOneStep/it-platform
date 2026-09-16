import itertools
from functools import cache

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.users_auth.models import User, UserRole
from app.modules.users_auth.passwords import hash_password

DEFAULT_PASSWORD = "Pa55word-Test"

_counter = itertools.count(1)


@cache
def _default_password_hash() -> str:
    return hash_password(DEFAULT_PASSWORD)


async def make_user(
    session: AsyncSession,
    *,
    email: str | None = None,
    full_name: str = "Иванов Иван Иванович",
    role: UserRole = UserRole.EMPLOYEE,
    department_id: int | None = None,
    password: str = DEFAULT_PASSWORD,
    must_change_password: bool = False,
    is_active: bool = True,
) -> User:
    password_hash = (
        _default_password_hash() if password == DEFAULT_PASSWORD else hash_password(password)
    )
    user = User(
        email=email or f"user{next(_counter)}@company.ru",
        full_name=full_name,
        password_hash=password_hash,
        role=role,
        department_id=department_id,
        must_change_password=must_change_password,
        is_active=is_active,
    )
    session.add(user)
    await session.flush()
    return user


async def login(
    client: AsyncClient, email: str, password: str = DEFAULT_PASSWORD
) -> dict[str, str]:
    response = await client.post("/api/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}
