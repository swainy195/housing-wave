from enum import StrEnum


class Stage(StrEnum):
    POLICY = "POLICY"
    BUSINESS = "BUSINESS"
    PERMIT = "PERMIT"
    CONSTRUCTION = "CONSTRUCTION"
    SUPPLY = "SUPPLY"
    MOVE_IN = "MOVE_IN"


STAGE_ORDER = [
    Stage.POLICY,
    Stage.BUSINESS,
    Stage.PERMIT,
    Stage.CONSTRUCTION,
    Stage.SUPPLY,
    Stage.MOVE_IN,
]


class DataStatus(StrEnum):
    AVAILABLE = "AVAILABLE"
    PARTIAL = "PARTIAL"
    NOT_CONNECTED = "NOT_CONNECTED"
    NOT_AVAILABLE = "NOT_AVAILABLE"


class LinkType(StrEnum):
    OFFICIAL = "OFFICIAL"
    VERIFIED = "VERIFIED"
    CANDIDATE = "CANDIDATE"


class ProgressStatus(StrEnum):
    NORMAL = "NORMAL"
    WARNING = "WARNING"
    DELAYED = "DELAYED"
    DATA_CHECK = "DATA_CHECK"


def progress_status(gap: float | None) -> ProgressStatus:
    """PoC temporary threshold; replace with an approved policy rule in production."""
    if gap is None:
        return ProgressStatus.DATA_CHECK
    if gap < -15:
        return ProgressStatus.DELAYED
    if gap < -5:
        return ProgressStatus.WARNING
    return ProgressStatus.NORMAL

