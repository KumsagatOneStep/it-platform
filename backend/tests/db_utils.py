from pathlib import Path

from alembic.config import Config

BACKEND_DIR = Path(__file__).resolve().parents[1]


def alembic_config() -> Config:
    config = Config(str(BACKEND_DIR / "alembic.ini"))
    config.attributes["skip_logging"] = True
    return config
