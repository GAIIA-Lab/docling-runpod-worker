# Docling RunPod Worker

Reusable GPU-backed PDF extraction worker for RunPod Serverless.

[![Licence: Apache 2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)
[![Publish image](https://github.com/GAIIA-Lab/docling-runpod-worker/actions/workflows/publish.yml/badge.svg)](https://github.com/GAIIA-Lab/docling-runpod-worker/actions/workflows/publish.yml)

This repository is a small service boundary around Docling: give it a publicly
reachable PDF URL, and it returns normalized markdown/text plus extraction
metadata. It can be used by any product, pipeline, or internal tool that needs
PDF-to-text extraction without embedding Docling directly in the main
application.

## What it does

- Accepts one PDF extraction job at a time.
- Downloads the PDF from a public URL.
- Runs Docling with CUDA acceleration.
- Returns extracted text, title, page count, table count, word count, source URL,
  and duration.
- Optionally POSTs the same result to a callback URL.

## What it does not do

- It does not classify, summarize, tag, or score documents.
- It does not write to your database.
- It does not know about your app's tables, projects, users, or workflows.
- It does not require any specific application platform.

Keep product-specific logic in the caller. This worker should remain a generic
PDF extraction component.

## Request contract

RunPod sends jobs as an event object. The worker accepts the job fields inside
`input`:

```json
{
  "input": {
    "job_id": "job-123",
    "pdf_url": "https://example.com/report.pdf",
    "callback_url": "https://example.com/api/pdf-extraction-callback",
    "callback_secret": "shared-secret",
    "metadata": {
      "source": "annual-report-import",
      "tenant_id": "customer-1"
    }
  }
}
```

Required fields:

| Field | Purpose |
| --- | --- |
| `job_id` | Caller-defined identifier used to correlate the response. |
| `pdf_url` | Publicly reachable PDF URL. |

Optional fields:

| Field | Purpose |
| --- | --- |
| `callback_url` | URL to POST the result to after completion or failure. |
| `callback_secret` | Shared secret sent with callback requests. |
| `metadata` | Caller-owned object for correlation or routing. The worker validates that it is an object but does not interpret it. |
| `document_id` | Optional caller document identifier. Included in callback payloads when provided. |
| `file_name` | Optional original file name. Included in callback payloads when provided. |

`source_url` is accepted as a compatibility alias for `pdf_url`:

```json
{
  "input": {
    "job_id": "job-123",
    "source_url": "https://example.com/report.pdf",
    "document_id": "doc-1",
    "file_name": "report.pdf",
    "callback_url": "https://example.com/api/pdf-extraction-callback",
    "callback_secret": "shared-secret"
  }
}
```

Put caller-specific correlation identifiers in `metadata`.

## Response contract

Success response:

```json
{
  "ok": true,
  "job_id": "job-123",
  "status": "completed",
  "result": {
    "text": "...",
    "title": "Report title",
    "word_count": 1234,
    "page_count": 42,
    "table_count": 3,
    "duration_seconds": 18.4,
    "source_url": "https://example.com/report.pdf"
  }
}
```

Failure response:

```json
{
  "ok": false,
  "job_id": "job-123",
  "status": "failed",
  "error": {
    "code": "EXTRACTION_FAILED",
    "message": "..."
  }
}
```

Bad requests return the same failure shape with `error.code` set to
`BAD_REQUEST`.

## Callback behaviour

If `callback_url` is provided, the worker POSTs a JSON payload after the job
finishes. The callback payload starts with the normal response payload and adds
callback-friendly fields:

- `stage`: `completed` or `failed`
- `progress`: `100` for success, `0` for failure
- `extractor_version`
- caller-provided `metadata`, when present
- `status`: `succeeded` on success, `failed` on failure
- flattened success fields: `extracted_text`, `title`, `word_count`,
  `page_count`, `table_count`, `duration_seconds`, `source_url`
- flattened failure fields: `error_code`, `error_message`

When `callback_secret` is provided, the callback request includes both headers:

```text
Authorization: Bearer <callback_secret>
x-callback-secret: <callback_secret>
```

Your callback endpoint should verify at least one of those headers.

## Repository layout

```text
.
├── Dockerfile
├── handler.py
├── local_test.py
├── requirements.txt
├── src/docling_runpod_worker/
│   ├── callbacks.py
│   ├── config.py
│   ├── extractor.py
│   ├── schema.py
│   └── staging.py
└── tests/sample_event.json
```

Important files:

| File | Purpose |
| --- | --- |
| `handler.py` | RunPod entrypoint. |
| `src/docling_runpod_worker/schema.py` | Request and response schema parsing. |
| `src/docling_runpod_worker/extractor.py` | Docling download and extraction core. |
| `src/docling_runpod_worker/staging.py` | Markdown staging and table handling. |
| `src/docling_runpod_worker/callbacks.py` | Callback payload and POST helper. |
| `local_test.py` | Direct local invocation without RunPod. |
| `tests/sample_event.json` | Minimal sample event payload. |

## Environment variables

See `.env.example`.

| Variable | Default | Purpose |
| --- | --- | --- |
| `MODE_TO_RUN` | `pod` | Use `serverless` in RunPod Serverless. Use `pod` or leave unset for local tests. |
| `DOCLING_NUM_THREADS` | `8` | Thread count passed to Docling accelerator options. |
| `OMP_NUM_THREADS` | `8` | OpenMP thread count. |
| `DOCLING_LAYOUT_BATCH_SIZE` | `512` | Layout model batch size. |
| `DOCLING_TABLE_BATCH_SIZE` | `64` | Table model batch size. |
| `DOCLING_QUEUE_SIZE` | `256` | Docling pipeline queue size. |
| `PDF_DOWNLOAD_TIMEOUT_SECONDS` | `120` | Timeout for downloading the source PDF. |
| `CALLBACK_TIMEOUT_SECONDS` | `20` | Timeout for callback POST requests. |
| `EXTRACTOR_VERSION` | `docling-runpod-worker/0.1` | Version string included in callback payloads. |

## Quick start on RunPod

This worker uses a queue-based Serverless endpoint. You can deploy the published
image without cloning the repository:

1. In RunPod Serverless, select **New Endpoint** → **Import from Docker Registry**.
2. Use `ghcr.io/gaiia-lab/docling-runpod-worker:latest` as the container image.
3. Select a CUDA 12.8-compatible GPU and set `MODE_TO_RUN=serverless`.
4. Deploy the endpoint, then submit a synchronous test:

```bash
curl --request POST \
  --url "https://api.runpod.ai/v2/<endpoint-id>/runsync" \
  --header "Authorization: Bearer <runpod-api-key>" \
  --header "Content-Type: application/json" \
  --data '{"input":{"job_id":"test-1","pdf_url":"https://example.com/report.pdf"}}'
```

Use a version tag or image digest instead of `latest` for production so a
deployment can be reproduced and rolled back.

## Local development

Create a virtual environment and install dependencies:

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
```

Run a direct local extraction:

```bash
python local_test.py \
  --pdf-url "https://example.com/report.pdf" \
  --job-id "local-test-1"
```

Run the RunPod SDK local server:

```bash
MODE_TO_RUN=serverless python handler.py --rp_serve_api
```

## Build and publish your own image

Fork this repository and enable GitHub Actions. Pushes to your fork's `main`
branch publish an image to:

```text
ghcr.io/<your-github-owner>/docling-runpod-worker:latest
```

The workflow also publishes immutable `sha-*` tags and version tags for Git
tags matching `v*`. Make the resulting package public if RunPod should pull it
without registry credentials.

To build locally instead:

```bash
docker build --platform linux/amd64 \
  --tag ghcr.io/<your-github-owner>/docling-runpod-worker:latest .
```

The container entrypoint is:

```bash
python -u handler.py
```

See RunPod's [worker deployment guide](https://docs.runpod.io/serverless/workers/deploy)
for endpoint configuration and registry alternatives.

## Security notes

- Treat the RunPod API key and `callback_secret` as secrets; never commit them.
- Only submit URLs you trust. The worker makes outbound requests to `pdf_url`
  and `callback_url`, so exposing the endpoint to untrusted callers creates a
  server-side request forgery risk.
- Set RunPod execution timeouts and spending limits appropriate to your use
  case. PDF size and complexity directly affect GPU time and memory use.
- Pin a version tag or digest in production instead of using `latest`.

## Integration pattern

The recommended application architecture is:

1. Your app uploads or stores a PDF somewhere the worker can fetch.
2. Your app submits a RunPod job with `job_id`, `pdf_url`, and optional callback
   fields.
3. This worker extracts the PDF and returns or POSTs the result.
4. Your app owns persistence, retries, user-facing status, downstream analysis,
   and any domain-specific processing.

This keeps the extraction layer replaceable. If you later move from RunPod to
another GPU provider, or from Docling to another extractor, your main
application only needs to preserve the request/response contract.

## Contributing and licence

Contributions are welcome; see [CONTRIBUTING.md](CONTRIBUTING.md). This project
is licensed under the [Apache License 2.0](LICENSE).
