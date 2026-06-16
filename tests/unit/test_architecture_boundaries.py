from pathlib import Path


def test_trading_core_does_not_import_adapters() -> None:
    root = Path("packages/trading_core")
    offenders: list[str] = []

    for path in root.rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        if "from adapters" in text or "import adapters" in text:
            offenders.append(str(path))

    assert offenders == []
