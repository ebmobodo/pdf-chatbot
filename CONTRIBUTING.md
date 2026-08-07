# Contributing to PDF Chat Bot

Thanks for your interest in improving PDF Chat Bot! This guide covers the
development workflow, code conventions, and how to get your changes
reviewed and merged.

---

## Development workflow

1. **Fork** the repository and create a feature branch:

   ```bash
   git checkout -b feat/your-feature
   ```

2. **Set up your environment** (see [README.md](./README.md) for full setup):

   ```bash
   python -m venv .venv
   source .venv/bin/activate          # Windows: .venv\Scripts\activate
   pip install -r requirements-dev.txt
   ```

3. **Install pre-commit hooks** (recommended):

   ```bash
   pre-commit install
   ```

   The hooks run Ruff (lint + format), mypy, and whitespace checks before
   every commit.

4. **Make your changes**, keeping the scope of each commit focused and
   described with a clear message.

5. **Run the full quality gate** before pushing:

   ```bash
   ruff check .
   ruff format --check .
   mypy src/
   pytest -v --cov=src
   ```

6. **Push and open a pull request** against the `main` branch using the
   [pull request template](./.github/pull_request_template.md).

---

## Branch naming convention

| Prefix    | Purpose                | Example                  |
| --------- | ---------------------- | ------------------------ |
| `feat/`   | New feature            | `feat/pdf-preview`       |
| `fix/`    | Bug fix                | `fix/ocr-dpi-warning`    |
| `refactor/` | Code restructuring  | `refactor/vector-store`  |
| `docs/`   | Documentation          | `docs/api-keys`          |
| `chore/`  | Tooling / maintenance  | `chore/dependabot`       |

---

## Code style

- **Formatter / linter:** [Ruff](https://docs.astral.sh/ruff/) with the
  ruleset in [`pyproject.toml`](./pyproject.toml) (line length 100,
  double quotes, `E`, `F`, `I`, `UP`, `B`, `SIM`, `C4` selected).
- **Type checking:** mypy against `src/` using the config in
  `pyproject.toml`. New functions should have type annotations.
- **Testing:** pytest with fixtures in `tests/conftest.py`. External
  services (Supabase, NVIDIA, Gemini, Groq, OCR) **must be mocked** in tests —
  never make real network calls.
- **Formatting conventions:**
  - 4-space indentation, UTF-8, LF line endings.
  - Imports sorted (Ruff `I` rule).
  - Docstrings on all public functions and modules.

---

## Testing guidance

- Tests live in `tests/` and mirror the `src/` module layout
  (`test_config.py` ↔ `src/config.py`).
- The autouse `_set_env_vars` fixture in `tests/conftest.py` pins fake
  credentials so tests never touch real secrets.
- Aim to keep coverage on `src/` at **80% or higher**
  (`pytest --cov=src` reports this).
- When you add a new module, add a matching `tests/test_<module>.py`.

---

## Adding or upgrading dependencies

- Runtime dependencies go in [`requirements.txt`](./requirements.txt) and
  should be **pinned** (`==`).
- Development-only tooling goes in
  [`requirements-dev.txt`](./requirements-dev.txt).
- Dependabot is configured to open weekly PRs for both
  (`pip` and `github-actions` ecosystems). Review CI results before merging.
- Keep the runtime image lean — avoid adding dev tools to
  `requirements.txt`.

---

## Commit message style

Follow the [Conventional Commits](https://www.conventionalcommits.org/)
convention:

```
<type>(<scope>): <short summary>

<optional body>
```

Examples:

- `feat(ocr): add multi-language Tesseract support`
- `fix(vector-store): retry embedding batch on timeout`
- `docs: clarify CHUNK_OVERLAP semantics`

---

## Pull request process

1. Fill out the PR template completely.
2. Ensure CI (lint, typecheck, tests, docker build) is green.
3. Reference any related issues with `Closes #123`.
4. A maintainer will review; address feedback in follow-up commits.

---

## Reporting issues

Use the [issue templates](./.github/ISSUE_TEMPLATE/) to report bugs or
request features. For security vulnerabilities, see
[SECURITY.md](./SECURITY.md) — do **not** open a public issue for
security bugs.
