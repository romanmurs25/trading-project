from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from apps.api.main import create_app  # noqa: E402

DEFAULT_OUTPUT = Path("apps/web/src/api/openapi.json")


def export_openapi(output_path: Path = DEFAULT_OUTPUT) -> Path:
    schema: dict[str, Any] = create_app().openapi()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(schema, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return output_path


if __name__ == "__main__":
    print(export_openapi())
