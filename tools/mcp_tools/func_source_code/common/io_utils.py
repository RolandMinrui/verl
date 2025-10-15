import json
from pathlib import Path
from typing import Any

import toml
import yaml


def load_file(path: str | Path) -> dict[str, Any] | str:
    """Load structured data or text from disk based on extension."""
    path = Path(path)
    if path.suffix == ".json":
        return json.loads(path.read_text())
    if path.suffix in (".yaml", ".yml"):
        return yaml.safe_load(path.read_text())
    if path.suffix == ".toml":
        return toml.loads(path.read_text())
    if path.suffix in (".txt", ".md"):
        return path.read_text()
    raise ValueError(f"Unsupported file extension: {path.suffix}")


def dump_file(path: str | Path, data: dict[str, Any] | str) -> None:
    """Persist structured data or text to disk based on extension."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    if path.suffix == ".json":
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2))
        return
    if path.suffix in (".yaml", ".yml"):
        path.write_text(yaml.safe_dump(data))
        return
    if path.suffix == ".toml":
        # toml library cannot handle enums directly, convert via json round-trip
        path.write_text(toml.dumps(json.loads(json.dumps(data))))
        return
    if path.suffix in (".txt", ".md"):
        if not isinstance(data, str):
            raise TypeError("Text files require string content")
        path.write_text(data)
        return
    raise ValueError(f"Unsupported file extension: {path.suffix}")