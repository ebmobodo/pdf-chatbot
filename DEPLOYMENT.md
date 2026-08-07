# Deployment Playbook — Render (Docker Web Service)

This guide walks through deploying the **PDF Chat Bot** to Render as a
Docker web service. Render builds the image from the repository's
`Dockerfile` and runs `scripts/start.sh`, which binds Streamlit to host
`0.0.0.0` on the port from the `PORT` environment variable (default
**10000**, matching Render's default web-service port).

---

## 1. Prerequisites

- A Render account: <https://dashboard.render.com>
- The repository hosted on GitHub (Render builds from it).
- Docker (optional) to test the image locally before deploying.
- The four required credentials for this app:

  | Variable            | Where to get it |
  | ------------------- | --------------- |
  | `GOOGLE_API_KEY`    | <https://aistudio.google.com/apikey> |
  | `NVIDIA_API_KEY`    | <https://build.nvidia.com> → API keys |
  | `SUPABASE_URL`      | Supabase project → Settings → API |
  | `SUPABASE_SERVICE_KEY` | Supabase project → Settings → API → `service_role` key |

  Plus one optional (recommended) fallback credential:

  | Variable         | Where to get it |
  | ---------------- | --------------- |
  | `GROQ_API_KEY`   | <https://console.groq.com/keys> — used only if the Gemini call fails |

---

## 2. Deploy with the Blueprint (`render.yaml`)

`render.yaml` defines the whole service. The recommended path is to push
it to your GitHub repo and let Render pick it up:

1. Push this repository to GitHub (make sure `render.yaml` is included).
2. In the Render dashboard, go to **New → Blueprint** and select the repo.
3. Render creates the web service from `render.yaml`:
   - runtime: **docker**
   - `PORT=10000` (Render's default web-service port; `scripts/start.sh`
     binds to whatever `$PORT` resolves to on host `0.0.0.0`)
   - `healthCheckPath=/_stcore/health`
   - plan: **free**
4. Render will create the service but it **will not start yet** — the four
   required API keys are marked `sync: false` and must be added manually
   (step 3).

### Manual alternative (Dashboard)

1. Render dashboard → **New → Web Service** → connect your GitHub repo.
2. **Runtime**: Docker.
3. **Health Check Path**: `/_stcore/health`.
4. Set **Start Command** to `bash scripts/start.sh` (the Dockerfile already
   sets this; leave it if using the Dockerfile's `CMD`).
5. Create the service, then set env vars (step 3).

---

## 3. Set the required environment variables

The API keys have `sync: false` in `render.yaml` — they are intentionally
**not** committed to the repo. Set them in the Render dashboard:

1. Open the service → **Environment** tab.
2. Add each variable (as a secret so it is not shown in plain text):

   | Name                 | Value                            |
   | -------------------- | -------------------------------- |
   | `GOOGLE_API_KEY`     | your Gemini key                  |
   | `NVIDIA_API_KEY`     | your NVIDIA NIM key              |
   | `SUPABASE_URL`       | e.g. `https://xyz.supabase.co`   |
   | `SUPABASE_SERVICE_KEY` | your `service_role` key        |

3. Optional tuning variables (same names/defaults as `.env.example`):

   | Name | Example |
   | ---- | ------- |
   | `LLM_MODEL` | `gemini-2.5-flash` |
   | `LLM_TEMPERATURE` | `0.3` |
   | `GROQ_API_KEY` | your Groq key (enables the fallback LLM) |
   | `FALLBACK_LLM_MODEL` | `llama-3.3-70b-versatile` |
   | `EMBED_MODEL` | `nvidia/nv-embedqa-e5-v5` |
   | `CHUNK_SIZE` | `1000` |
   | `CHUNK_OVERLAP` | `200` |
   | `OCR_ENABLED` | `true` |

> **Fallback behavior:** `src/llm_chain.py` always calls the primary Gemini
> model first. If that call raises (rate limit, bad key, downtime), the
> request automatically retries on Groq when `GROQ_API_KEY` is set. Without a
> Groq key the app logs a warning at startup and runs Gemini-only.

> **OCR caveat:** the Dockerfile installs `poppler-utils` + `tesseract-ocr`,
> so OCR for scanned PDFs works out of the box in production. Set
> `OCR_ENABLED=true` to enable it (blank pages are OCR'd automatically;
> text-based PDFs still use the fast `pypdf` path).

---

## 4. Test the image locally (optional but recommended)

```bash
docker build -t pdf-chatbot .
docker run --rm -p 10000:10000 \
  -e PORT=10000 \
  -e GOOGLE_API_KEY=... \
  -e NVIDIA_API_KEY=... \
  -e SUPABASE_URL=... \
  -e SUPABASE_SERVICE_KEY=... \
  pdf-chatbot
```

Open <http://localhost:10000>, upload a PDF, and confirm the chat works
before deploying. Verify the health endpoint too:
`curl http://localhost:10000/_stcore/health`.

---

## 5. Deploy & trigger builds

- **Auto-deploy:** after the service is created, every push to the
  connected branch triggers a new build and release.
- **Manual deploy:** service → **Manual Deploy → Deploy latest commit**.
- Watch the build in the service **Events** tab. First build takes a few
  minutes (apt + pip install of the LangChain/Streamlit stack); later
  builds are faster thanks to Docker layer caching.

The app is live at `https://<service-name>.onrender.com`.

---

## 6. Rolling out updates

```bash
git add .
git commit -m "Describe the change"
git push origin main
```

Auto-deploy builds and swaps the running service. To hard-restart:
service → **Manual Deploy** or the **Restart** button in the service menu.

---

## 7. Scaling & hardening notes

- **Sleep / cold start:** the free tier sleeps after 15 minutes of
  inactivity; the next request wakes it (takes ~30–60 s). A `cron-job.org`
  ping to `/_stcore/health` every ~10 minutes keeps it warm.
- **Upgrade:** the free instance is 512 MB RAM / 0.1 CPU; PDF-heavy loads
  benefit from a paid plan (1 GB+ / 0.5 CPU).
- **Keep secrets out of the image:** `.dockerignore` already excludes
  `.env`; always pass credentials via Render env vars / secrets.
- **Pin dependencies:** `requirements.txt` is locked; bump deliberately.
- **Health check:** `/_stcore/health` is used by Render; keep it reachable
  (Streamlit exposes it by default). The `Dockerfile` healthcheck probes the
  same endpoint on the port from `$PORT`, so it stays correct even if the
  injected `PORT` differs from the default.

---

## 8. Troubleshooting

| Symptom | Likely cause | Fix |
| ------- | ------------ | --- |
| Deploy fails / container crashes | Missing env vars | App crashes at startup if the 4 required vars are absent; set them in **Environment** |
| `Missing required environment variable(s)` | Vars not set or not redeployed | Add vars, then **Manual Deploy → Clear build cache & deploy** |
| `httpx.ConnectError: getaddrinfo failed` | Supabase URL hostname unreachable / typo | Confirm `SUPABASE_URL`, check network egress |
| `401 Invalid API key` | Wrong/rotated key | Rotate the key, update the env var, redeploy |
| Health check failing | Port mismatch | The Docker healthcheck and Render both probe `$PORT`; ensure the app actually bound `0.0.0.0:$PORT` (check logs for the `Starting Streamlit on 0.0.0.0:...` line). Do not hardcode another port |
| Empty answers / "no context" | Nothing embedded yet, or OCR disabled on scanned PDFs | Process a PDF first; enable `OCR_ENABLED=true` |
| OCR returns empty on scanned pages | `OCR_ENABLED` not set, or OCR skipped for that page | Set `OCR_ENABLED=true` and redeploy; the image ships `poppler-utils` + `tesseract-ocr` |
| Port already in use (local) | Another process on 10000 | Run with `-e PORT=10001 -p 10001:10001` |

---

## Related: Supabase MCP (developer tooling)

For AI-assisted development against your Supabase project, the MCP server
is configured in `opencode.json`:

```json
{
  "mcp": {
    "supabase": {
      "type": "remote",
      "url": "https://mcp.supabase.com/mcp?project_ref=YOUR_PROJECT_REF",
      "enabled": true
    }
  }
}
```

Authenticate once with `opencode mcp auth supabase`, which opens a browser
OAuth flow. This is developer tooling only — it is not required for the
Render deployment.
