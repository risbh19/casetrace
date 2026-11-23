# Operational deployment and acceptance

CaseTrace has an operational software configuration and a synthetic training configuration. The release candidate has been exercised locally using synthetic data, including HTTPS, restricted database access, officer onboarding and recorded notice dispatch. It has not been deployed for an agency or approved for live investigations.

## Required rollout decisions

Before live data is introduced, the installation owner must supply the authorized department/stations, deployment domain and host, officer identity policy, retention and legal-hold requirements, backup custody and recovery targets, approved legal corpus and agency acceptance. If an institutional identity provider or MFA is required, integrate and validate it before rollout; this release supplies local officer accounts. Bank, telecom and CCTNS APIs are not implemented and must not be represented as connected.

No department, hosting account, identity provider, retention policy or official integration access has been provided for this project. These are open deployment prerequisites, rather than completed features or fabricated connections.

## Install a separate operational instance

1. Provision a host with Docker Compose 2.24.4 or later, encrypted storage, restricted operator access and a DNS name you control. Only the HTTPS gateway publishes network ports; the database and API remain internal.
2. Copy `deploy/production.env.example` to a protected `.env.production` file. Set `CASETRACE_DOMAIN` to the actual host name. Generate independent URL-safe database owner and application passwords of at least 24 random characters, and a signing key of at least 48 random characters. Store and rotate these through the installation's approved secret-management process. Never commit this file.
3. Start `docker compose --env-file .env.production -p casetrace -f compose.production.yml up -d --build`. Check that the migration job exits successfully and API health becomes healthy. Caddy obtains a certificate for the configured domain; DNS and inbound HTTPS must be ready.
4. Create the first station administrator with `docker compose --env-file .env.production -p casetrace -f compose.production.yml run --rm migrate python -m app.manage operator.name --name "Officer Name" --station "Authorized Station"`. Enter the password at the prompt. The operator command creates no sample cases or demo users.
5. Sign in over HTTPS. Use **Officer accounts** to provision individual officers in that station. New officers must change their temporary password before viewing case records. Deactivation, role changes and password resets invalidate their existing sessions. Supervisors assign active investigating officers to cases.
6. Review the reference catalog and index approved original documents using the migration-owner service: `docker compose --env-file .env.production -p casetrace -f compose.production.yml run --rm migrate python -m app.ingest_statutes --directory /tmp/law_sources`. This downloads the configured official snapshots; retain their provenance and verify amendments separately. Production defaults do not enable local model inference.

The migration owner is separate from `casetrace_app`. The runtime account cannot update or delete stored original evidence or audit events. Database triggers enforce immutability as well. A database superuser or host operator remains a trusted administrative boundary; preserve off-host backups and operator audit records according to the approved policy.

## Notices and dates

Production blocks the simulated-send endpoint. A separate authorized supervisor approves a draft. After an officer uses the approved external channel, the supervisor records the channel, external reference and an original proof document already uploaded to the same case. The event records an assertion of external dispatch; CaseTrace does not transmit the notice or independently confirm third-party receipt.

Production progress reminders require a reviewed anchor date. Custody date and reviewed offence band must be supplied together. The displayed calculations and source references require officer and agency legal review; no universal legal deadline or automated investigative authority is implied.

## Encrypted backups and restore verification

Use the backend Python environment to run `scripts/backup.py`. Generate a protected, independent 32-byte random key file and retain it separately from the encrypted backups. The archive uses streaming AES-GCM authenticated encryption; no plaintext backup is written to disk.

```text
python scripts/backup.py backup /approved/path/casetrace.enc --key-file /protected/path/backup.key --env-file .env.production
python scripts/backup.py restore-check /approved/path/casetrace.enc --key-file /protected/path/backup.key --env-file .env.production --database casetrace_restore_acceptance
```

Run from the repository root. A previous archive is never overwritten. Restore authenticates a private ciphertext copy before executing SQL, and requires a new `casetrace_restore_*` database; it never drops or overwrites the live database. Compare restored counts, original-file hashes and required workflow records. An actual disaster recovery or retention deletion needs the installation owner's approved procedure. This release does not perform automatic deletion.

## Monitor and recover

Monitor HTTPS `/health` for database readiness and the Compose service state. A failed database connection returns 503; reconnection is checked on subsequent requests. Alert delivery and monitoring ownership must be configured by the installation owner. Original downloads verify their stored SHA-256 before returning bytes, and record access. Application SQL errors hide bound data; operational HTTP access logs are disabled to reduce request-data exposure.

Before deployment changes, create and verify a backup, record the image/source revision, test migrations against a restored copy and retain the previous release. If a schema migration changes stored data, use the reviewed recovery procedure rather than blindly downgrading a live database. Do not remove database volumes during upgrades.

## Local acceptance environment

`compose.production.verify.yml` publishes HTTPS only on `127.0.0.1:18443` and uses the `localhost` certificate issued by Caddy's local CA. Use a new `casetrace-prod-check-*` project, independent environment file and synthetic verification accounts. Never apply this override to a real installation. The production browser probe is explicitly opt-in and restricted to loopback hosts. The automated release gate checks the training browser suite and both database backends; real agency acceptance remains separate.
