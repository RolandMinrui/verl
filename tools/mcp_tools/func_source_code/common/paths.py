from pathlib import Path


def get_database_path(*path_parts: str) -> Path:
    """Return absolute path under tools/database."""
    base_dir = Path(__file__).resolve().parents[3] / "database"
    return base_dir.joinpath(*path_parts)