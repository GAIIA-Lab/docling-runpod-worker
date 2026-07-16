from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(frozen=True)
class JobRequest:
    job_id: str
    pdf_url: str
    callback_url: str | None = None
    callback_secret: str | None = None
    document_id: str | None = None
    file_name: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ExtractionResult:
    text: str
    title: str | None
    word_count: int
    page_count: int
    table_count: int
    duration_seconds: float
    source_url: str


@dataclass(frozen=True)
class ErrorInfo:
    code: str
    message: str


@dataclass(frozen=True)
class JobResponse:
    ok: bool
    job_id: str | None
    status: str
    result: ExtractionResult | None = None
    error: ErrorInfo | None = None

    @classmethod
    def success(cls, job_id: str, result: ExtractionResult) -> "JobResponse":
        return cls(ok=True, job_id=job_id, status="completed", result=result)

    @classmethod
    def failure(cls, job_id: str | None, error: ErrorInfo) -> "JobResponse":
        return cls(ok=False, job_id=job_id, status="failed", error=error)

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "ok": self.ok,
            "job_id": self.job_id,
            "status": self.status,
        }
        if self.result is not None:
            payload["result"] = asdict(self.result)
        if self.error is not None:
            payload["error"] = asdict(self.error)
        return payload


def parse_request(event: dict[str, Any]) -> JobRequest:
    if not isinstance(event, dict):
        raise ValueError("event must be an object")

    raw = event.get("input", event)
    if not isinstance(raw, dict):
        raise ValueError("input must be an object")

    job_id = str(raw.get("job_id", "")).strip()
    pdf_url = str(raw.get("pdf_url", "") or raw.get("source_url", "")).strip()
    callback_url = str(raw.get("callback_url", "")).strip() or None
    callback_secret = str(raw.get("callback_secret", "")).strip() or None
    document_id = str(raw.get("document_id", "")).strip() or None
    file_name = str(raw.get("file_name", "")).strip() or None
    metadata = raw.get("metadata") or {}

    if not job_id:
        raise ValueError("job_id is required")
    if not pdf_url:
        raise ValueError("pdf_url is required")
    if not isinstance(metadata, dict):
        raise ValueError("metadata must be an object")

    return JobRequest(
        job_id=job_id,
        pdf_url=pdf_url,
        callback_url=callback_url,
        callback_secret=callback_secret,
        document_id=document_id,
        file_name=file_name,
        metadata=metadata,
    )
