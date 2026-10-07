from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any, Protocol


@dataclass(slots=True)
class IngestBatch:
    """Normalized boundary for future agency adapters; no external connector is active yet."""

    source_id: str
    reference_date: date | None
    collected_at: datetime
    records: dict[str, list[dict[str, Any]]] = field(default_factory=dict)


class SourceAdapter(Protocol):
    """Future MOLIT/LH/SH/GH/iH adapters normalize data into an IngestBatch."""

    source_id: str

    def collect(self) -> IngestBatch: ...

