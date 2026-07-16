FROM runpod/pytorch:2.4.0-py3.11-cuda12.4.1-devel-ubuntu22.04

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    MODE_TO_RUN=serverless \
    PYTHONPATH=/app/src

WORKDIR /app

COPY requirements.txt /app/requirements.txt

RUN pip install --no-cache-dir -r /app/requirements.txt

COPY handler.py /app/handler.py
COPY local_test.py /app/local_test.py
COPY src /app/src

RUN python -c "\
from docling.datamodel.pipeline_options import ThreadedPdfPipelineOptions; \
from docling.datamodel.base_models import InputFormat; \
from docling.document_converter import DocumentConverter, PdfFormatOption; \
from docling.pipeline.threaded_standard_pdf_pipeline import ThreadedStandardPdfPipeline; \
from docling.backend.docling_parse_v4_backend import DoclingParseV4DocumentBackend; \
opts = ThreadedPdfPipelineOptions(do_ocr=False, do_table_structure=True); \
converter = DocumentConverter(format_options={InputFormat.PDF: PdfFormatOption(backend=DoclingParseV4DocumentBackend, pipeline_cls=ThreadedStandardPdfPipeline, pipeline_options=opts)}); \
print('Models downloaded and cached successfully') \
"

CMD ["python", "-u", "handler.py"]
