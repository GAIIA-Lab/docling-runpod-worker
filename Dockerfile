FROM runpod/pytorch:1.0.2-cu1281-torch280-ubuntu2404

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    MODE_TO_RUN=serverless \
    PYTHONPATH=/app/src

WORKDIR /app

COPY requirements.txt /app/requirements.txt

RUN python -c "import torch; assert torch.__version__.startswith('2.8.'), torch.__version__"

RUN pip install --no-cache-dir -r /app/requirements.txt

RUN rm -f /usr/local/bin/filebrowser

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
