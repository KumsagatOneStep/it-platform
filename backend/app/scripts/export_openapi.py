import json
import sys
from pathlib import Path

from fastapi import FastAPI

from app.main import create_app


def render_openapi(app: FastAPI) -> str:
    return json.dumps(app.openapi(), ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def main() -> None:
    target = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("openapi.json")
    target.write_text(render_openapi(create_app()), encoding="utf-8")
    print(f"OpenAPI-схема записана в {target}")


if __name__ == "__main__":
    main()
