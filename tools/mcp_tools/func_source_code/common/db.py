from typing import Any

from pydantic import BaseModel, ConfigDict

from .io_utils import dump_file, load_file


class DB(BaseModel):
    """Lightweight base class for domain databases."""

    model_config = ConfigDict(extra="forbid")

    @classmethod
    def load(cls, path: str) -> "DB":
        data = load_file(path)
        if isinstance(data, str):
            raise ValueError("Expected structured data when loading database")
        return cls.model_validate(data)

    def dump(self, path: str) -> None:
        dump_file(path, self.model_dump())

    def get_json_schema(self) -> dict[str, Any]:
        return self.model_json_schema()