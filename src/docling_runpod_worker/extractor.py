from __future__ import annotations

import gc
import os
import re
import tempfile
import time
from functools import lru_cache
from pathlib import Path

import requests

from docling_runpod_worker.config import CONFIG
from docling_runpod_worker.schema import ExtractionResult, JobRequest
from docling_runpod_worker.staging import stage_doc_docling


def clear_gpu_memory() -> None:
    import torch

    if torch.cuda.is_available():
        torch.cuda.empty_cache()
    gc.collect()


def normalized_lines(markdown: str) -> list[str]:
    markdown = markdown.replace("\r\n", "\n").replace("\r", "\n")
    lines: list[str] = []
    for raw_line in markdown.splitlines():
        cleaned = re.sub(r"^#+\s*", "", raw_line).strip()
        if cleaned.startswith("<!--") and cleaned.endswith("-->"):
            continue
        cleaned = re.sub(r"\s+", " ", cleaned).strip()
        if cleaned:
            lines.append(cleaned)
    return lines


def is_title_candidate(line: str) -> bool:
    lowered = line.lower()
    if lowered in {"abstract", "introduction", "contents", "references", "image"}:
        return False
    if lowered.startswith(("figure ", "table ", "source:", "an early draft of ")):
        return False
    if len(line) < 8 or len(line) > 160:
        return False
    if line.endswith((".", "?", "!")):
        return False
    return True


def infer_title(markdown: str) -> str | None:
    for raw_line in markdown.replace("\r\n", "\n").replace("\r", "\n").splitlines()[:40]:
        stripped = raw_line.strip()
        if not stripped or stripped.startswith("<!--"):
            continue
        if stripped.startswith("#"):
            heading = re.sub(r"^#+\s*", "", stripped).strip()
            if is_title_candidate(heading):
                return heading

    for line in normalized_lines(markdown)[:20]:
        if is_title_candidate(line):
            return line
    return None


@lru_cache(maxsize=1)
def get_converter() -> DocumentConverter:
    from docling.backend.docling_parse_v4_backend import DoclingParseV4DocumentBackend
    from docling.datamodel.accelerator_options import AcceleratorDevice, AcceleratorOptions
    from docling.datamodel.base_models import InputFormat
    from docling.datamodel.pipeline_options import ThreadedPdfPipelineOptions
    from docling.document_converter import DocumentConverter, PdfFormatOption
    from docling.pipeline.threaded_standard_pdf_pipeline import ThreadedStandardPdfPipeline

    os.environ.setdefault("OMP_NUM_THREADS", str(CONFIG.omp_num_threads))

    pipeline_options = ThreadedPdfPipelineOptions(
        do_ocr=False,
        do_table_structure=True,
        do_code_enrichment=False,
        do_formula_enrichment=False,
        do_picture_classification=False,
        ocr_batch_size=16,
        layout_batch_size=CONFIG.layout_batch_size,
        table_batch_size=CONFIG.table_batch_size,
        queue_max_size=CONFIG.queue_size,
        generate_page_images=False,
        images_scale=1.0,
    )
    pipeline_options.accelerator_options = AcceleratorOptions(
        device=AcceleratorDevice.CUDA,
        num_threads=CONFIG.docling_num_threads,
        cuda_use_flash_attention2=True,
    )

    return DocumentConverter(
        format_options={
            InputFormat.PDF: PdfFormatOption(
                backend=DoclingParseV4DocumentBackend,
                pipeline_cls=ThreadedStandardPdfPipeline,
                pipeline_options=pipeline_options,
            )
        }
    )


def download_pdf_bytes(url: str) -> bytes:
    response = requests.get(url, timeout=CONFIG.pdf_download_timeout_seconds)
    response.raise_for_status()
    content_type = response.headers.get("content-type", "").lower()
    if "pdf" not in content_type and not url.lower().endswith(".pdf"):
        raise ValueError(f"url did not return a PDF content-type: {content_type or 'unknown'}")
    return response.content


def extract_from_job(request: JobRequest) -> ExtractionResult:
    started_at = time.perf_counter()
    pdf_bytes = download_pdf_bytes(request.pdf_url)

    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as pdf_handle:
        pdf_handle.write(pdf_bytes)
        pdf_path = Path(pdf_handle.name)

    with tempfile.NamedTemporaryFile(suffix=".md", delete=False) as md_handle:
        markdown_path = Path(md_handle.name)

    try:
        conversion = get_converter().convert(str(pdf_path))
        document = getattr(conversion, "document", conversion)
        page_count = len(document.pages) if hasattr(document, "pages") else 0
        table_count = stage_doc_docling(conversion, str(markdown_path), margin=2.0)
        markdown = markdown_path.read_text(encoding="utf-8").strip()
        text = re.sub(r"(?m)^<!--.*?-->\s*$", "", markdown)
        text = re.sub(r"\n{3,}", "\n\n", text).strip()

        return ExtractionResult(
            text=text,
            title=infer_title(markdown),
            word_count=len(text.split()),
            page_count=page_count,
            table_count=table_count,
            duration_seconds=round(time.perf_counter() - started_at, 3),
            source_url=request.pdf_url,
        )
    finally:
        pdf_path.unlink(missing_ok=True)
        markdown_path.unlink(missing_ok=True)
        clear_gpu_memory()
