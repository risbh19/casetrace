CaseTrace 1.0 release candidate completes the documented workspace features and adds a separate operational deployment configuration.

- Interactive React Flow money trails with pan, zoom, account selection and transfer tables.
- Full official-PDF page ingestion with original URLs, page numbers, retrieval dates and SHA-256 provenance; curated section summaries remain separate from original-text search results.
- Supervisor overview, permission-scoped related-case identifiers and audited officer reassignment.
- Individual officer provisioning, forced temporary-password changes, account deactivation, revocable sessions and persisted sign-in throttling.
- Immutable original evidence and audit records, integrity-checked downloads, and restricted PostgreSQL application permissions.
- Production notice dispatch records require separate approval, an external reference and uploaded proof. CaseTrace does not transmit notices to banks or telecom providers.
- Explicit progress-update anchors in production, corrected optional-reminder clearing, and repaired evidence-screen API routing.
- HTTPS deployment, encrypted streaming backups, isolated restore verification, pinned runtime dependencies, dependency audits and browser/SQLite/PostgreSQL/OCR checks.

This is a release candidate for deployment acceptance. No real agency, public host, officer identity provider, retention policy, bank/telecom API or CCTNS connection has been supplied or approved. Those rollout requirements remain open. A local production-configuration check with synthetic data is not agency approval for live investigations. See `docs/production.md` and `docs/verification.md` for evidence and remaining acceptance work.
