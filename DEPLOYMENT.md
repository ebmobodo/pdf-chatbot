# Deployment Playbook — Hugging Face Spaces (Docker SDK)

This guide walks through deploying the **PDF Chat Bot** to a Hugging Face
Space, under either a personal account or an organization. The Space uses
the **Docker SDK** and runs the image built from the repository's
`Dockerfile` (Streamlit on port `7860`).

---

## 1. Prerequisites

- A Hugging Face account. If you deploy under an organization, create (or
  have access to) the organization: <https://huggingface.co/organizations/new>
- Git installed and configured (`git config --global user.name/email`).
- Docker (optional) to test the image locally before pushing.
- The four required credentials for this app:

  | Secret                | Where to get it |
  | --------------------- | --------------- |
  | `GOOGLE_API_KEY`      | <https://aistudio.google.com/apikey> |
  | `NVIDIA_API_KEY`      | <https://build.nvidia.com> → API keys |
  | `SUPABASE_URL`        | Supabase project → Settings → API |
  | `SUPABASE_SERVICE_KEY`| Supabase project → Settings → API → `service_role` key |

---

## 2. Create a Hugging Face User Access Token (write)

The token is used to push the Space code. A token with **write** access on
the target account/org is required.

1. Go to <https://huggingface.co/settings/tokens>.
2. Click **Create new token**.
3. Give it a name (e.g. `pdf-chatbot-deploy`).
4. Role: **Write** (for the account that owns the Space).
5. If deploying under an organization, create the token **inside the
   organization's settings** (org → Settings → Tokens) so it has write
   access to the org Space.
6. **Copy the token immediately** — it is only shown once. Treat it as a
   secret: store it in your OS keychain / a password manager. Never commit
   it to Git.

---

## 3. Create the Space (Docker SDK / Blank)

### Option A — Web UI (simplest)

1. Go to <https://huggingface.co/new-space>.
2. **Owner**: choose your username or the organization.
3. **Space name**: e.g. `pdf-chatbot`.
4. **License**: pick MIT (matches this repo).
5. **Select the Space SDK**: **Docker**.
6. **Docker template**: **Blank**.
7. **Hardware**: start with the free **CPU basic** tier.
8. Click **Create Space**.

### Option B — CLI

```bash
pip install huggingface_hub
huggingface-cli login                    # paste your write token

# Personal space
huggingface-cli repo create pdf-chatbot --type space --space_sdk docker

# Organization space
huggingface-cli repo create pdf-chatbot \
  --type space --space_sdk docker --organization YOUR_ORG_NAME
```

> The Space will initially fail to start (no Dockerfile yet). That is
> expected — we push the code in step 5.

---

## 4. Configure Space Secrets (Repository Secrets)

HF Space **secrets** become environment variables inside the container at
runtime. They are the production equivalent of the local `.env` file.

1. Open the Space you just created.
2. Go to **Settings** → **Variables and secrets**.
3. Under **Secrets**, add each of these (click *Add a secret* per row):

   | Name                 | Value                                        |
   | -------------------- | -------------------------------------------- |
   | `GOOGLE_API_KEY`     | your Gemini key                              |
   | `NVIDIA_API_KEY`     | your NVIDIA NIM key                          |
   | `SUPABASE_URL`       | e.g. `https://xyz.supabase.co`               |
   | `SUPABASE_SERVICE_KEY` | your `service_role` key                    |

4. Optional tuning secrets (same values as `.env.example`):

   | Name | Example |
   | ---- | ------- |
   | `LLM_MODEL` | `gemini-1.5-flash` |
   | `LLM_TEMPERATURE` | `0.3` |
   | `EMBED_MODEL` | `nvidia/nv-embedqa-e5-v5` |
   | `CHUNK_SIZE` | `1000` |
   | `CHUNK_OVERLAP` | `200` |
   | `OCR_ENABLED` | `true` (requires the OCR system deps already in the Dockerfile) |

5. Optionally, under **Variables**, you can add non-secret env overrides.

> The Dockerfile ships `poppler-utils` + `tesseract-ocr`, so
> `OCR_ENABLED=true` works out of the box in the Space.

---

## 5. Test the image locally (optional but recommended)

```bash
cd pdf-chatbot

docker build -t pdf-chatbot .
docker run --rm -p 7860:7860 \
  -e GOOGLE_API_KEY=... \
  -e NVIDIA_API_KEY=... \
  -e SUPABASE_URL=... \
  -e SUPABASE_SERVICE_KEY=... \
  pdf-chatbot
```

Open <http://localhost:7860>, upload a PDF, and confirm the chat works
before deploying.

---

## 6. Deploy by pushing to Hugging Face

1. **Add the Space as a remote** (replace `YOUR_ORG_NAME`/`SPACE_NAME`):

   ```bash
   cd pdf-chatbot

   # If this directory is not yet a Git repo:
   git init
   git add .
   git commit -m "Initial release"

   # Personal space
   git remote add hf https://huggingface.co/spaces/USERNAME/pdf-chatbot

   # Organization space
   git remote add hf https://huggingface.co/spaces/YOUR_ORG_NAME/pdf-chatbot
   ```

2. **Push** (you may be prompted for the write token):

   ```bash
   git push hf main
   ```

3. Hugging Face detects the commit and automatically builds the Docker
   image. Watch progress under the Space's **Runtime** tab or in
   **Settings → Builds**.

4. When the build finishes, the app is live at:

   ```
   https://huggingface.co/spaces/YOUR_ORG_NAME/pdf-chatbot
   ```

> First build takes a few minutes (apt packages + pip install of the
> LangChain/Streamlit stack). Subsequent builds are much faster thanks to
> Docker layer caching.

---

## 7. Rolling out updates

```bash
git add .
git commit -m "Describe the change"
git push hf main
```

HF rebuilds and hot-swaps the running Space. To hard-restart after a
deployment: **Settings → Danger Zone → Restart space**.

---

## 8. Scaling & hardening notes

- **Sleep / cold start:** free and `cpu-basic` Spaces sleep after
  inactivity; the app restarts on the next visit (takes ~10–20 s).
- **Upgrade hardware:** Settings → Hardware → `cpu-upgrade` (2 vCPU) for
  faster PDF processing, or GPU tiers if you later run local models.
- **Keep secrets out of the image:** `.dockerignore` already excludes
  `.env`; always pass credentials via Space secrets.
- **Pin dependencies:** `requirements.txt` is locked; bump deliberately.
- **Rotate the HF token** if it is ever exposed, and use the
  **organization** for team collaboration (members get their own tokens).

---

## 9. Troubleshooting

| Symptom | Likely cause | Fix |
| ------- | ------------ | --- |
| Space build fails | Syntax error or missing package | Check **Settings → Builds** logs; run `docker build` locally |
| `httpx.ConnectError: getaddrinfo failed` | Supabase URL hostname unreachable / typo | Confirm `SUPABASE_URL` secret, check network egress |
| `Missing required environment variable(s)` | Secrets not set | Re-check **Settings → Variables and secrets** |
| `401 Invalid API key` | Wrong/rotated key | Rotate the key, update the secret, restart the Space |
| Empty answers / "no context" | Nothing embedded yet, or OCR disabled on scanned PDFs | Process a PDF first; set `OCR_ENABLED=true` |
| OCR returns empty on scanned pages | `poppler-utils`/`tesseract-ocr` missing in image | Already installed in `Dockerfile`; verify the image was rebuilt |
| Port already in use (local) | Another process on 7860 | Run with `--server.port=8501` locally |

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
Space deployment.
