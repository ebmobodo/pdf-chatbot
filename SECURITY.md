# Security Policy

## Supported versions

| Version | Supported          |
| ------- | ------------------ |
| latest  | ✅ Supported       |
| < latest | ❌ Not supported  |

This project is under active development; only the latest commit on `main`
and the most recent tagged release receive security fixes.

## Reporting a vulnerability

**Please do not open a public GitHub issue for security vulnerabilities.**

Instead, report them privately by emailing the maintainers at:

```
security@example.com
```

When reporting, include:

- A description of the vulnerability and its impact.
- The affected component (e.g. `src/document_processor.py`).
- Steps to reproduce, if possible.
- Any suggested remediation.

You will receive an acknowledgment within **48 hours**, and a detailed
response with a fix timeline (typically within 7 days). If the issue is
confirmed, a fix will be released as soon as possible and coordinated with
the reporter before public disclosure.

## Security considerations for this application

- **Secrets:** All credentials (`GOOGLE_API_KEY`, `NVIDIA_API_KEY`,
  `SUPABASE_URL`, `SUPABASE_SERVICE_KEY`) are read from environment
  variables / secrets. Never commit a real `.env`; it is git-ignored and
  `.dockerignore`d.
- **Service-role key:** The Supabase `service_role` key bypasses RLS. Keep
  it out of any client-facing code and rotate it immediately if exposed.
- **Untrusted PDFs:** Uploaded PDFs are parsed server-side by `pypdf` and
  (optionally) OCR'd with `pdf2image` + `pytesseract`. Keep them and their
  dependencies up to date (Dependabot + `pip-audit` in CI) to mitigate parser
  vulnerabilities.
- **Dependency scanning:** CI runs `pip-audit`, bandit, and GitHub CodeQL
  on every push to `main` and on pull requests.

## Dependency security automation

Dependabot is configured (`.github/dependabot.yml`) to open weekly PRs for
Python (`pip`) and `github-actions` ecosystems. Apply dependency updates
promptly, especially security-patched versions.
