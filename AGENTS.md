# AGENTS.md

## Purpose
- Working rules for `docling-runpod-worker`.

## Positioning
- This project is a standalone PDF extraction worker.
- Keep it reusable across products and pipelines.
- Do not couple it to any caller-specific platform, database, or schema.

## Scope
- Accept one extraction job.
- Fetch one PDF.
- Run Docling on GPU.
- Return normalized extraction output.
- Optionally callback the caller.

## Non-Goals
- No app-specific business logic.
- No topic classification.
- No database writes.
- No orchestration tables.

## Execution Style
- Prefer small, testable changes.
- Preserve a stable external request/response contract.
- Keep deployment artifacts explicit: `Dockerfile`, `requirements.txt`, `.env.example`.
