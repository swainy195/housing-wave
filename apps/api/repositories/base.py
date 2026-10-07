from typing import Any, Protocol


class Repository(Protocol):
    """Small repository boundary shared by JSON and PostgreSQL implementations."""

    @property
    def metadata(self) -> dict[str, Any]: ...

    def all(self, entity: str) -> list[dict[str, Any]]: ...

    def get(self, entity: str, item_id: str) -> dict[str, Any] | None: ...

