# AGENTS.md — pdf-chatbot

Python RAG chatbot: upload a PDF, ask questions, get answers grounded in the document.
Stack: Streamlit + LangChain + Supabase (pgvector) + NVIDIA NIM embeddings + Google Gemini
(primary LLM with automatic Groq fallback), with an optional OCR fallback. Deployed to
**Render** (Docker Web Service).

## Quick start
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env   # fill in keys
streamlit run app.py   # or: bash scripts/start.sh
```

## Quality gate (run in this order before pushing)
```bash
ruff check .
ruff format --check .
mypy src/                          # type-checks src/ only; tests excluded
pytest -v --cov=src                # coverage >= 80% is enforced (fail_under=80)
```
CI runs all four for Python 3.12 (`lint`, `typecheck`, `test`, `build`) in
`.github/workflows/ci.yml`; tests also run against 3.11.

## Environment / secrets
- 4 required vars — the app **crashes at startup** if missing (config validation in `src/config.py`):
  `SUPABASE_URL`, `SUPABASE_SERVICE_KEY`, `GOOGLE_API_KEY`, `NVIDIA_API_KEY`.
- 1 optional var: `GROQ_API_KEY` (enables the Groq fallback LLM in `src/llm_chain.py`; without it the
  app logs a warning and runs Gemini-only). Tunables: `LLM_MODEL`, `LLM_TEMPERATURE`,
  `FALLBACK_LLM_MODEL`, `EMBED_MODEL`, `EMBED_BASE_URL`, chunking, OCR, `POSTGREST_TIMEOUT`.
- Local dev: set in `.env` (loaded via `python-dotenv` in `src/config.py`).
- Tests pin fake credentials via the autouse `_set_env_vars` fixture in `tests/conftest.py`.
  Never make real network calls — mock Supabase / NVIDIA / Gemini / Groq / OCR.

## Testing
- `tests/` mirrors `src/` layout (`test_config.py` ↔ `src/config.py`). Add a matching
  `tests/test_<module>.py` for any new `src/` module.
- Fixtures available in `tests/conftest.py`: `sample_chunks` (list[Document]) and `fake_pdf_bytes`.
- Run one file: `pytest tests/test_config.py -v`

## Architecture (execution flow)
PDF upload → `app.py` (Streamlit UI) → `src/document_processor.py` (pypdf text + optional OCR
in `src/ocr.py`) → `src/vector_store.py` (NVIDIA NIM embeddings + Supabase pgvector
`match_documents`) → `src/llm_chain.py` (Gemini RAG with Groq fallback) → chat UI. Config is
centralized in `src/config.py`.

## Code style
- Ruff: line-length 100, double-quote strings, rules `E,F,I,UP,B,SIM,C4` (see `pyproject.toml`).
- 4-space indent, LF line endings, UTF-8. Imports sorted (Ruff `I`).
- mypy: `disallow_untyped_defs=true` for `src/` — new functions need type annotations.

## Dependencies
- `requirements.txt`: **pinned** (`==`), runtime only — keep the Docker image lean; never add dev tools here.
- `requirements-dev.txt`: test/lint tooling (pytest, ruff). Not shipped in the image.
- Dependabot opens weekly PRs for both files (pip + github-actions ecosystems).

## Branching / commits
- Branch names: `feat/`, `fix/`, `refactor/`, `docs/`, `chore/` (see CONTRIBUTING.md).
- Commits: Conventional Commits, e.g. `feat(ocr): add multi-language Tesseract support`.

## Docker / Deploy (Render — NOT Hugging Face Spaces)
- Production entrypoint: `scripts/start.sh` — reads `$PORT` (default **10000**, Render's default
  web-service port), binds host `0.0.0.0`, and logs the bound address for debugging.
- Deployment is via **Render** `render.yaml` (Docker web service): sets `PORT=10000`,
  `healthCheckPath=/_stcore/health`, free tier. API keys have `sync: false` — set them in the
  Render dashboard, not in this file.
- The `Dockerfile` is the Render image source. Its healthcheck probes `/_stcore/health` on
  `$PORT` (not a hardcoded port), so it stays correct when Render injects a different `PORT`.
  `EXPOSE 10000` is informational only.
- Local image run: `docker build -t pdf-chatbot .` then
  `docker run --rm -p 10000:10000 -e PORT=10000 -e GOOGLE_API_KEY=... -e NVIDIA_API_KEY=... -e SUPABASE_URL=... -e SUPABASE_SERVICE_KEY=... pdf-chatbot`.
- OCR: `poppler-utils` + `tesseract-ocr` are installed by the Dockerfile;
  enable via `OCR_ENABLED=true` (blank pages are OCR'd, text pages use pypdf).

## Known technical debt
- `langchain-community` (used for `SupabaseVectorStore`) is sunset; migrate `src/vector_store.py`
  to the standalone `langchain-supabase` package when it stabilizes.