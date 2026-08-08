# PDF Chat Bot

A production-ready **Retrieval-Augmented Generation (RAG)** application that
lets users upload a PDF, ask natural-language questions about it, and get
answer grounded strictly in the document's content.

Built with **Streamlit**, **LangChain**, **Supabase (pgvector)**, **NVIDIA
NIM embeddings**, and **Google Gemini** (primary LLM, with an automatic
**Groq fallback**), plus an optional **OCR fallback** for scanned
documents. Containerized for deployment to **Render** (Docker Web Service).

---

## Architecture

```
                 ┌────────────────────────────────────────────┐
 Uploaded PDF ──►│  Streamlit UI (app.py)                     │
                 │                                             │
                 │  ┌─────────────────────────────────────┐    │
                 │  │ src.document_processor.py           │    │
                 │  │  text extraction (pypdf)            │    │
                 │  │  optional OCR fallback (src.ocr.py) │    │
                 │  └─────────────────────────────────────┘    │
                 └──────────────┬──────────────────────────────┘
                                │ chunks
                                ▼
              ┌─────────────────────────────────────────────┐
              │ src.vector_store.py                         │
              │  NVIDIA NIM embeddings + Supabase pgvector  │
              └─────────────────────┬───────────────────────┘
                                    │ retrieval (match_documents)
                                    ▼
               ┌─────────────────────────────────────────────┐
               │ src.llm_chain.py  (Gemini RAG chain)        │
               │  Gemini primary → Groq fallback on failure  │
               │  context + question ──► grounded answer     │
               └─────────────────────────┬───────────────────┘
                                        ▼
                               Streamlit chat UI
```

### Project layout

```
pdf-chatbot/
├── app.py                     # Streamlit entry point
├── src/
│   ├── config.py              # Centralized, validated environment config
│   ├── document_processor.py  # PDF ingestion + chunking
│   ├── ocr.py                 # Optional OCR pipeline (scanned pages)
│   ├── vector_store.py        # Supabase + NVIDIA embeddings integration
│   └── llm_chain.py           # Gemini RAG chain w/ Groq fallback
├── tests/                     # pytest suite (mocked external services)
├── scripts/
│   └── start.sh               # Entrypoint: reads $PORT, binds 0.0.0.0
├── Dockerfile                 # Render-optimized production image
├── .dockerignore
├── requirements.txt           # Locked runtime dependencies
├── requirements-dev.txt       # Test / quality tooling
├── pyproject.toml             # pytest + ruff configuration
├── .env.example               # Template for environment variables
└── DEPLOYMENT.md              # Render deployment playbook
```

---

## Prerequisites

- Python 3.11+ (3.13 recommended for local dev)
- Accounts / API keys:
  - **Google** (`GOOGLE_API_KEY`) — Gemini LLM (primary)
  - **NVIDIA** (`NVIDIA_API_KEY`) — embeddings
  - **Supabase** project (`SUPABASE_URL`, `SUPABASE_SERVICE_KEY`) with the
    `documents` table and `match_documents` pgvector function
  - **Groq** (`GROQ_API_KEY`) — optional fallback LLM used when Gemini is
    rate-limited or unavailable
- Optional for OCR: `poppler-utils` and `tesseract-ocr` system packages

## Local development

```bash
# 1. Create a virtual environment and install dependencies
python -m venv .venv
.venv\Scripts\activate            # Windows
pip install -r requirements.txt

# 2. Configure environment
copy .env.example .env            # Windows
# then fill in your keys

# 3. Run the app
streamlit run app.py

# 4. Run tests and lint
pip install -r requirements-dev.txt
pytest -v
ruff check .
```

> **OCR for scanned PDFs:** set `OCR_ENABLED=true`. The OCR fallback
> renders pages with no text layer and runs Tesseract (see
> `src/ocr.py`). This pattern is inspired by OCR pipelines such as
> Baidu's [Unlimited-OCR](https://github.com/baidu/Unlimited-OCR). Without
> `poppler-utils`/`tesseract-ocr` installed, OCR degrades gracefully.

## Configuration reference

| Variable                | Required | Default                          | Description                          |
| ----------------------- | :------: | -------------------------------- | ------------------------------------ |
| `GOOGLE_API_KEY`        |   yes    | —                                | Gemini API key                       |
| `NVIDIA_API_KEY`        |   yes    | —                                | NVIDIA NIM API key                   |
| `SUPABASE_URL`          |   yes    | —                                | Supabase project URL                 |
| `SUPABASE_SERVICE_KEY`  |   yes    | —                                | Supabase service-role key            |
| `LLM_MODEL`             |   no     | `gemini-2.5-flash`               | Primary Gemini model                |
| `LLM_TEMPERATURE`       |   no     | `0.3`                            | LLM sampling temperature             |
| `GROQ_API_KEY`          |   no     | —                                | Groq API key (enables fallback)      |
| `FALLBACK_LLM_MODEL`    |   no     | `llama-3.3-70b-versatile`        | Groq model used when Gemini fails    |
| `EMBED_MODEL`           |   no     | `nvidia/nemotron-3-embed-1b`     | NVIDIA embedding model               |
| `EMBED_BASE_URL`        |   no     | `https://integrate.api.nvidia.com/v1` | NVIDIA NIM endpoint             |
| `CHUNK_SIZE`            |   no     | `1000`                           | Text splitter chunk size             |
| `CHUNK_OVERLAP`         |   no     | `200`                            | Text splitter chunk overlap          |
| `OCR_ENABLED`           |   no     | `false`                          | Enable OCR fallback for scanned pages |
| `OCR_DPI`               |   no     | `300`                            | OCR render resolution                |
| `OCR_LANGUAGE`          |   no     | `eng`                            | Tesseract language pack              |
| `POSTGREST_TIMEOUT`     |   no     | `60`                             | Supabase PostgREST timeout (seconds) |

## Docker

```bash
docker build -t pdf-chatbot .
docker run --rm -p 10000:10000 \
  -e PORT=10000 \
  -e GOOGLE_API_KEY=... \
  -e NVIDIA_API_KEY=... \
  -e SUPABASE_URL=... \
  -e SUPABASE_SERVICE_KEY=... \
  pdf-chatbot
# open http://localhost:10000
```

See [DEPLOYMENT.md](./DEPLOYMENT.md) for the full Render setup.

## Known technical debt

- `langchain-community` (used for `SupabaseVectorStore`) is being sunset;
  when the standalone `langchain-supabase` integration stabilizes, migrate
  `src/vector_store.py` to it to drop the deprecation warning.
- OCR ships with English (`eng`) only by default; install additional
  `tesseract-ocr-*` language packs to extend support.

## License & third-party licenses

Application code in this repository is provided under the MIT License.
Key dependencies and their licenses: pdf2image (MIT), pytesseract
(Apache-2.0), pypdf (BSD-3-Clause), Streamlit (Apache-2.0), LangChain
(MIT), Supabase (MIT).
