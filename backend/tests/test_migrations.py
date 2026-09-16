from alembic import command
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import SCHEMAS
from tests.db_utils import alembic_config


def test_migrations_downgrade_to_base_and_upgrade_again() -> None:
    config = alembic_config()

    command.downgrade(config, "base")
    command.upgrade(config, "head")


async def test_all_schemas_exist(db_session: AsyncSession) -> None:
    rows = await db_session.execute(text("SELECT schema_name FROM information_schema.schemata"))

    assert set(SCHEMAS) <= {row[0] for row in rows}
