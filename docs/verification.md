# Verification

Executed on 23–24 November 2026 with Python 3.12, Node.js 26, Chrome, Docker Compose, PostgreSQL 17 and pgvector. These are local verification results; GitHub Actions provides additional checks on the actual pull request and release revision.

| Check | Observed result |
| --- | --- |
| Windows SQLite suite | 25 passed; 2 live OCR checks skipped because native OCR tools were unavailable. |
| Linux PostgreSQL suite | All 27 passed, including both real OCR checks. Every application fixture used Alembic migrations and an isolated test schema. |
| Schema consistency | PostgreSQL `alembic check` reported no new upgrade operations. |
| Browser training workflow | Four passed: evidence/checklist/React Flow/reminders, separate supervisor approval and activity, officer provisioning/password change, and mobile overflow. |
| Browser production configuration | One passed over local HTTPS: individual officer onboarding, evidence upload, separate approval, externally recorded dispatch reference/proof and audit event. |
| HTTPS and database permissions | The local CA and hostname were validated without disabling certificate checks. The runtime identity was `casetrace_app`; audit mutation was denied. |
| Dependencies | Frontend `npm audit` and backend `pip-audit` reported no known vulnerabilities after the reviewed upgrades. Runtime pins are included. |
| Full statutory PDFs | All pages indexed into both SQLite and PostgreSQL: BNSS 249, BNS 102, BSA 54, IT Act 36; total 441. URLs, file hashes and source manifests were retained. |
| Local models | Real `qwen2.5:0.5b` and the originally documented `qwen2.5:3b` returned suggestions. `nomic-embed-text` produced finite 768-dimensional vectors; 14 curated sections were stored and a PostgreSQL nearest-vector check passed. |
| Hindi scanned evidence | Both PNG and image-only PDF produced the expected account, amount and date. OCR-inserted account spacing was reproduced and covered by a regression test. |
| Encrypted recovery | A synthetic PostgreSQL dump was streamed into an AES-GCM archive and authenticated before restoration into a new verification database. Tampered ciphertext is rejected by the regression test. |
| Recorded demonstration | [Actual synthetic workflow](demo.webm), 3 minutes 1 second, 1280×720; discovery and rehearsal completed before recording. |

The browser checks discovered and fixed the previous Evidence-tab `/evidence` versus API `/documents` mismatch. Clearing optional reminder dates now removes obsolete records. Production requires an officer-confirmed progress-update anchor, blocks simulated sending and refuses known seeded training users/cases at startup.

The 20-question legal set checks expected primary section identifiers. It does not establish legal applicability, amendment coverage or model performance on unseen questions. Full-text results are labeled as original-document search results. The OCR results establish the controlled fixtures, not general handwriting or scan accuracy.

Both Compose configurations have been run locally using synthetic data. A local operational configuration is not an approved agency installation. No public host, organizational identity provider/MFA, institutional retention policy or authorized bank/telecom/CCTNS integration has been supplied. Those rollout decisions and real-agency acceptance remain open; see [the runbook](production.md).
