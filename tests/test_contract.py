from __future__ import annotations

import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from docling_runpod_worker.callbacks import build_callback_payload
from docling_runpod_worker.schema import ExtractionResult, JobResponse, parse_request


class RequestContractTests(unittest.TestCase):
    def test_source_url_alias_and_metadata(self) -> None:
        request = parse_request({
            "input": {
                "job_id": "job-1",
                "source_url": "https://example.com/report.pdf",
                "metadata": {"correlation_id": "run-1"},
            }
        })

        self.assertEqual(request.pdf_url, "https://example.com/report.pdf")
        self.assertEqual(request.metadata, {"correlation_id": "run-1"})

    def test_callback_payload_is_generic(self) -> None:
        request = parse_request({
            "input": {
                "job_id": "job-1",
                "pdf_url": "https://example.com/report.pdf",
                "document_id": "doc-1",
                "file_name": "report.pdf",
                "metadata": {"correlation_id": "run-1"},
            }
        })
        result = ExtractionResult(
            text="Report text",
            title="Report",
            word_count=2,
            page_count=1,
            table_count=0,
            duration_seconds=0.5,
            source_url=request.pdf_url,
        )

        payload = build_callback_payload(request, JobResponse.success(request.job_id, result))

        self.assertEqual(payload["document_id"], "doc-1")
        self.assertEqual(payload["file_name"], "report.pdf")
        self.assertEqual(payload["metadata"], {"correlation_id": "run-1"})


if __name__ == "__main__":
    unittest.main()
