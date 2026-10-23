"""Application boundaries only: no H-MEM/Nightshift integration is claimed."""
from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class ReviewedCorrection:
    investigation_id: str
    text: str
    evidence_ids: tuple[str, ...]
    reviewer: str
    reviewed_at: str


class InvestigationMemory(Protocol):
    def recall(self, company_cik: str, evidence_ids: tuple[str, ...]) -> list[ReviewedCorrection]: ...
    def remember(self, correction: ReviewedCorrection) -> None: ...


class InvestigationRuntime(Protocol):
    def discover(self) -> dict: ...
    def chat(self, text: str, model: str) -> str: ...
