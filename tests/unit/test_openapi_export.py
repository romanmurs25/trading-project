import json
from pathlib import Path

from scripts.export_openapi import export_openapi


def test_export_openapi_writes_schema_with_live_data_paths(tmp_path: Path) -> None:
    output_path = tmp_path / "openapi.json"

    written_path = export_openapi(output_path)

    schema = json.loads(written_path.read_text(encoding="utf-8"))
    assert written_path == output_path
    assert "/api/live-data/state" in schema["paths"]
    assert "/api/live-data/replay-demo" in schema["paths"]
    assert "/api/live-data/poll/moex-once" in schema["paths"]
