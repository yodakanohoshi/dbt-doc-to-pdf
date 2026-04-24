import json
from pathlib import Path
from typing import Any


def load_manifest(target_dir: Path) -> dict[str, Any]:
    return json.loads((target_dir / "manifest.json").read_text())


def load_catalog(target_dir: Path) -> dict[str, Any]:
    return json.loads((target_dir / "catalog.json").read_text())
