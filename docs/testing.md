# Reproducible checks

Use Python 3.12, Node.js 22.12+ and Docker Compose 2.24.4+. Install backend runtime pins before development tools: `python -m pip install -r backend/requirements.lock`, then `python -m pip install -e "backend[dev]"`. From `frontend`, run `npm ci`.

## Backend

From `backend`, run `python -m pytest -q` and `ruff check . ../scripts`. Every application fixture runs Alembic migrations; SQLite is the default. To exercise PostgreSQL, set `TEST_DATABASE_URL` to a disposable database whose name starts with `casetrace_test`. Each fixture creates a unique schema and removes only that schema afterward. Existing case databases are rejected as test targets.

Set `RUN_OCR_TESTS=1` when Tesseract with `eng` and `hin` and Poppler are available. This enables both image and scanned-PDF fixtures. Skipped OCR tests are not a runtime pass. `python scripts/verify_runtime.py --ocr --models` additionally checks real inference, finite 768-dimensional embeddings and PostgreSQL cosine distance; run it only against the synthetic training installation with the models installed.

The 20-question citation set checks the primary expected section identifier, not legal applicability or model accuracy on unseen cases. Full PDF ingestion tests verify page extraction, provenance, replacement behavior and preservation of a previous index when invalid bytes are supplied.

## Browser

From the frontend environment, run `npx playwright install chromium`, then `npx playwright test workspace.spec.ts`. The configuration starts a new temporary synthetic API database and Vite server. Ensure the backend Python environment is active so the `python` command resolves to it. The browser suite covers evidence uploads, checklist generation, React Flow interaction, reminder clearing, separate supervisor approval, activity records, account onboarding and mobile overflow.

For an already running isolated stack, set `CASETRACE_EXTERNAL_SERVER=1`, `CASETRACE_BASE_URL` and the synthetic `CASETRACE_TEST_PASSWORD`. `CASETRACE_CHROME_CHANNEL=chrome` uses an installed Chrome. Video recording also needs Playwright's FFmpeg component. Production verification uses `CASETRACE_PRODUCTION_TEST_URL=https://localhost:18443` and `production.spec.ts`; it must target a fresh synthetic production-check installation, with its verification administrator provisioned. The browser probe accepts the local test CA, while the separate HTTPS probe verifies that CA and hostname normally.

## Dependencies and containers

Run `npm audit --audit-level=low` from frontend, and `python -m pip_audit --local --skip-editable` in a clean backend environment. Backend pins can be regenerated with `scripts/lock_backend.py` after reviewing upgrades; then rebuild and test both platforms. An empty advisory report is evidence at the check date, not a guarantee about future disclosures.

For disposable Compose checks, combine `docker-compose.yml` and `compose.verify.yml` under a unique `casetrace-check-*` project and a protected test environment file. This uses loopback ports 15173, 18000 and 15432 and the `casetrace_test` database. Verify startup, Alembic consistency, full workflows, database outage/recovery and encrypted restore. Stop only the verification project afterward; never remove an operational volume.

## Demo

`node demo.cjs --discover`, then `node demo.cjs --rehearse`, then `node demo.cjs` records the actual synthetic workflow to `docs/demo.webm`. Run from frontend against the isolated training installation and set its URL/password as above. The recorder uses a visible cursor, captions and human-readable pacing, and fails if a required control is unavailable. No bank, telecom or CCTNS interaction is demonstrated or implied.
