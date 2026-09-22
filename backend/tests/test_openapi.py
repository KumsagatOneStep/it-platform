import json

from app.main import create_app
from app.scripts.export_openapi import render_openapi
from tests.db_utils import BACKEND_DIR


def test_committed_openapi_schema_is_up_to_date() -> None:
    committed = (BACKEND_DIR / "openapi.json").read_text(encoding="utf-8")

    assert committed == render_openapi(create_app()), (
        "openapi.json устарел: выполните `make openapi` и закоммитьте результат"
    )


def test_openapi_contains_core_paths() -> None:
    paths = json.loads(render_openapi(create_app()))["paths"]

    for path in (
        "/api/auth/login",
        "/api/admin/users",
        "/api/departments",
        "/api/directories/locations",
        "/api/assets",
        "/api/assets/{asset_id}/operations",
    ):
        assert path in paths
