from __future__ import annotations

import requests

from docling_runpod_worker.config import CONFIG
from docling_runpod_worker.schema import JobRequest, JobResponse


def build_callback_payload(request: JobRequest, response: JobResponse) -> dict:
    payload = response.to_dict()
    payload["stage"] = "completed" if response.ok else "failed"
    payload["progress"] = 100 if response.ok else 0
    payload["extractor_version"] = CONFIG.extractor_version
    if request.metadata:
        payload["metadata"] = request.metadata

    if request.document_id:
        payload["document_id"] = request.document_id
    if request.file_name:
        payload["file_name"] = request.file_name

    if response.ok and response.result is not None:
        payload["status"] = "succeeded"
        payload["source_url"] = response.result.source_url
        payload["extracted_text"] = response.result.text
        payload["title"] = response.result.title
        payload["word_count"] = response.result.word_count
        payload["page_count"] = response.result.page_count
        payload["table_count"] = response.result.table_count
        payload["duration_seconds"] = response.result.duration_seconds
    elif response.error is not None:
        payload["error_code"] = response.error.code
        payload["error_message"] = response.error.message

    return payload


def post_callback(request: JobRequest, response: JobResponse) -> None:
    if not request.callback_url:
        return

    headers = {"Content-Type": "application/json"}
    if request.callback_secret:
        headers["Authorization"] = f"Bearer {request.callback_secret}"
        headers["x-callback-secret"] = request.callback_secret

    callback_response = requests.post(
        request.callback_url,
        json=build_callback_payload(request, response),
        headers=headers,
        timeout=CONFIG.callback_timeout_seconds,
    )
    callback_response.raise_for_status()
