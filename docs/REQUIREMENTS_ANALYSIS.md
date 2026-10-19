# IncuBrix Long-Tail Distribution Network: Requirements Analysis

**Project**: IncuBrix Engineering Assessment 4  
**Role**: Principal Architect & Senior Full-Stack Engineer  
**Status**: Architecture & Analysis Phase (Prompt 1)  
**Date**: October 2026  

---

## 1. Problem Statement & Scope Definition

### 1.1 The Problem in Our Own Words
IncuBrix currently automates content distribution to 15 Tier-1 social and media platforms (YouTube, Instagram, Facebook, LinkedIn, TikTok, X, Threads, Pinterest, Bluesky, Mastodon, Reddit, Vimeo, WordPress, Telegram, Discord) and outbound RSS feeds. While these major platforms offer broad reach, high-intent audience growth and engagement are increasingly concentrated in the **"long tail"**: niche forums (Discourse), federated communities (Lemmy), developer publishing networks (Dev.to, Hashnode), independent blogs (Ghost), newsletters (Kit, Mailchimp), partner websites, private Slack/Discord communities, MRSS video syndication feeds, and high-trust communities where automated posting is banned and a human must publish manually.

The core engineering challenge is **"one connector, many destinations"** backed by strict **safety, rule compliance, and certification**. A single connector engine must handle hundreds of instances (for example, forum #41 on Discourse must be a single configuration row in a catalogue, requiring zero new application code). Because communities enforce strict, distinct formatting rules, link constraints, self-promotion limits, and AI disclosure mandates, a single careless automated post risks permanent community bans and domain blacklisting. Every destination must be certified (validated, test-posted, confirmed live, and cleaned up within 10 minutes) before it is trusted.

### 1.2 Scope Boundaries

#### In-Scope
1. **Connector Architecture**: Unified connector interface implementing `POST /connector/v1/{connector_key}/{method}` (`validate`, `publish`, `get_status`, `delete`, `fetch_metrics`, `refresh_auth`, `build_assist_pack`), backed by per-connector YAML manifests and shared error code mapping.
2. **Six Core Connectors**:
   - `discourse`: Multi-instance forum posting via REST API (`base_url` instance parameter).
   - `lemmy`: Multi-instance federated community posting via Lemmy HTTP API.
   - `devto`: Developer article publishing via Forem API.
   - `ghost`: Independent blog publication via Ghost Admin API with JWT authentication.
   - `signed_webhook`: Secure JSON payload delivery signed with HMAC-SHA256, timestamp replay prevention, and signature headers.
   - `assisted`: Specialized workflow generating a ready-to-post assist package (bundled media, tailored text, deep link, rules checklist) for communities where automated bot posting is forbidden.
3. **Advanced Connectors (3 additional)**:
   - `hashnode`: GraphQL-based developer blog publication.
   - `slack`: Bot/Webhook structured message distribution.
   - `mrss`: Media RSS feed generation and syndicate updates.
4. **Pre-flight Posting-Rules Engine**: Comprehensive validation executing prior to any connector invocation, verifying frequency caps, self-promotion policies, link rules, and AI disclosure requirements.
5. **Certification & Recertification Harness**: Automated lifecycle runner (validate -> publish test post -> verify live status -> delete within 10 minutes -> record evidence pack -> assign destination level L0–L4; periodic 30-day recertification with automated demotion and alerting).
6. **Destination Catalogue Engine**: CSV ingestion with normalization, deduplication, URL reachability verification, enrichment, row-by-row error reporting, and relevance scoring (1–5) across IncuBrix target verticals.
7. **Content Tailoring & Recommendation**: Automated rendition tailoring (discussion-first forum hooks, canonical URL tagging for articles, word-boundary truncation, hashtags/mentions) and fit-based destination recommendation.
8. **IncuBrix Integration Standard (10 Points)**: Containerized architecture, OpenAPI 3.1 documentation, asynchronous job queue (202 Accepted + polling/HMAC callbacks), idempotent POST execution (`Idempotency-Key`), standardized JSON error payloads, S3/MinIO file storage, structured JSON logging with correlation IDs, JSON output manifests, and a batch runner CLI.
9. **Simulation Mode & Local Sandbox**: Complete, zero-external-API-key local test environment via Docker Compose (including local Lemmy, local Ghost, and high-fidelity mock platforms).

#### Out-of-Scope
- The 15 existing Tier-1 platforms (YouTube, Instagram, Facebook, LinkedIn, TikTok, X, Threads, Pinterest, Bluesky, Mastodon, Reddit, Vimeo, WordPress, Telegram, Discord) and basic outbound RSS.
- Paid boosting, paid ad campaigns, PPC management.
- Outbound cold email outreach and B2B lead generation sequences.
- Customer billing, subscriptions, invoicing, and payment gateways.

---

## 2. Core Specifications & Deliverable Breakdown

### 2.1 The 9 Must-Haves (Pass/Fail Gate)
Every must-have is non-negotiable. A single failure disqualifies the submission.

| # | Must-Have Requirement | Verification Method | Acceptance Criteria |
|---|----------------------|--------------------|---------------------|
| **MH1** | **Exact connector contract** | Contract test suite (`pytest tests/contract`) | Exposes `POST /connector/v1/{connector_key}/{method}` for all required methods; matches Appendix A schemas, manifests, and shared error codes. |
| **MH2** | **Six Core connectors certified** | Certification harness + evidence logs | Discourse, Lemmy, Dev.to, Ghost, Signed Webhook, and Assisted connector certified with verifiable run records. |
| **MH3** | **Configuration, not code** | API/Catalogue test | Adding an additional destination (e.g., Discourse forum #41) requires only 1 database/catalogue row; zero code changes. |
| **MH4** | **Rules checked before every post** | Rule engine test suite (`tests/unit/test_rules.py`) | Pre-flight check evaluates frequency cap, self-promo, link policy, AI disclosure. Violating posts blocked or rescheduled with explicit reasons; zero requests reach the connector. |
| **MH5** | **Never spam, never cheat** | Audit logs, network inspect, cleanup tests | Test posts target only local instances/sandboxes; all test posts deleted within 10 minutes; platform rate limits respected (exponential backoff on 429 reset time). |
| **MH6** | **Safe retries** | Concurrency & idempotency tests | Duplicate requests with identical `Idempotency-Key` never create duplicate posts; timeouts trigger reconciliation rather than blind republishing. |
| **MH7** | **Secrets protected & simulation mode** | Repo scan, log audit, simulation test run | Zero secrets in repo/logs; full end-to-end execution functional in simulation mode with mock platforms and no real API keys. |
| **MH8** | **Local test instances** | `docker compose up` verification on clean host | Single command boots API, worker, Postgres, Redis, MinIO, Lemmy, Ghost, and mock platform services. |
| **MH9** | **Integration Standard followed & live demo** | Review against 10 Integration Standard points | All 10 points fulfilled; publicly accessible demo URL active throughout review window. |

---

### 2.2 Grading Levels

#### Core Level (15 Marks - Required)
1. Pass all 9 Must-Haves.
2. Complete certification runs for all six Core connectors (publish, verify live URL, status check, delete) with stored evidence.
3. Full platform error mapping to shared error codes (`DEST_SPEC_VIOLATION`, `DEST_RULE_FREQUENCY_CAP`, `CONNECTION_AUTH_EXPIRED`, `PLATFORM_RATE_LIMIT`, `PLATFORM_QUOTA_EXHAUSTED`, `PLATFORM_CONTENT_REJECTED`, `PLATFORM_UNAVAILABLE`, `CONNECTOR_DISABLED`).

#### Advanced Level (15 Marks)
1. **Catalogue Import Engine**: Validates, normalizes, deduplicates (normalized URL + platform key), verifies reachability, and enriches CSV records; imports 1,000 rows in <5 minutes with row-by-row error logs.
2. **Rules Capture**: AI-assisted rule extraction analyzing community guideline pages, producing structured rule proposals requiring human confirmation prior to activation.
3. **Relevance Scoring**: Deterministic scoring (1–5) evaluating fit for IncuBrix target audiences (AI, video, marketing, SaaS, creators, founders) with human-readable rationales.
4. **Content Tailoring**: Automatic per-destination adaptation (discussion-first framing for forums, canonical URLs for blogs, word-boundary truncation, platform-specific hashtags/mentions, AI disclosure tags).
5. **Three Additional Connectors**: Implementation and testing of `hashnode`, `slack`, and `mrss`.

#### Outstanding Level (10 Marks)
1. **Intelligent Recommender**: Ranks candidate destinations for given content based on audience fit, active rules, and past performance; precision@10 evaluated on a benchmark labeled dataset.
2. **Metrics Ingestion**: Standardized `fetch_metrics` across at least three connectors, normalizing views, likes, comments, shares, saves, watch time, and clicks (`null` when unsupported, never `0`).
3. **Automated Recertification**: Background scheduler executing 30-day health checks; automated demotion to L0 and ticket/alert generation upon failure.
4. **Real-World Catalogue**: Curated dataset of >=150 real, verified destinations researched with accurate rules, relevance scores, and connector keys (catalogue only; zero unauthorized posting).

---

### 2.3 The 10 Integration Standard Requirements

| # | Standard | Implementation Specification |
|---|----------|------------------------------|
| **IS1** | **One-command start & test** | `docker compose up -d` boots entire infrastructure; `make test` runs unit, contract, integration, and e2e suites without external API keys; `.env.example` documents all keys. |
| **IS2** | **Documented HTTP API** | Auto-generated `openapi.yaml` conforming strictly to OpenAPI 3.1; all standard endpoints under `/api/v1/` (with documented exceptions: `/connector/v1/...`, `/health`, `/ready`). |
| **IS3** | **Background jobs** | Operations taking >2 seconds return `202 Accepted` with `{"job_id": "..."}`; `GET /api/v1/jobs/{job_id}` returns status (`queued`, `running`, `succeeded`, `failed`), progress `0-100`, and result links; optional webhook callback signed with HMAC-SHA256 (`X-IncuBrix-Signature`). |
| **IS4** | **Safe retries** | Mandatory `Idempotency-Key` header on all state-altering POST requests; cache/lock guarantees identical response and zero duplicate work. |
| **IS5** | **Clear errors** | Uniform error schema: `{"error": {"code": "UPPER_SNAKE_CASE", "message": "...", "retryable": boolean, "details": {...}}}`. |
| **IS6** | **Configuration** | Pydantic `BaseSettings` reading environment variables; zero hard-coded paths, tokens, or credentials. |
| **IS7** | **Files in, files out** | Media ingested via multipart upload or validated URL; generated artifacts/evidence stored in S3/MinIO and exposed via pre-signed/download URLs. |
| **IS8** | **Logs and health** | Structured JSON logs containing `timestamp`, `level`, `job_id`, `X-Correlation-Id`, and `module`; endpoints `GET /health` (liveness) and `GET /ready` (readiness checking DB, Redis, MinIO). |
| **IS9** | **Output manifest** | Every operation yields a JSON manifest detailing models/providers, versions, runtime parameters, seed, timings, cost estimates, warnings, copyright/license metadata, and AI-generation flags. |
| **IS10** | **Batch runner** | Standalone CLI `python scripts/batch_runner.py <input-folder-or-file> --out <output-dir>` executing batch inputs and generating consolidated output reports. |

---

### 2.4 The 14 Hard Cases to Test

| # | Hard Case Scenario | Expected System Behavior |
|---|--------------------|--------------------------|
| **HC1** | Publish call times out and is retried with identical `Idempotency-Key`. | Reconcile first. Query platform status; if accepted, return existing post ID; never create a duplicate post. |
| **HC2** | Platform returns HTTP 429 with `Retry-After` / reset timestamp. | Map to `PLATFORM_RATE_LIMIT`, extract reset epoch, persist backoff window, reject subsequent requests until window elapses. |
| **HC3** | Authentication token expired or revoked (HTTP 401). | Map to `CONNECTION_AUTH_EXPIRED`, mark connection status `degraded`, pause destination, emit alert requiring reconnection. |
| **HC4** | Content rejected by platform rules/moderation (HTTP 422). | Map to `PLATFORM_CONTENT_REJECTED`, extract platform rejection message, fail job with non-retryable error, preserve log. |
| **HC5** | Title or body exceeds platform character limits. | Pre-flight validation fails with `DEST_SPEC_VIOLATION`, listing field-level length violations; request never sent to platform. |
| **HC6** | Media attachment format or file size unsupported by destination. | Pre-flight validation fails with `DEST_SPEC_VIOLATION` detailing unsupported MIME type or exceeding size limit. |
| **HC7** | Second post submitted within destination's frequency cap window. | Pre-flight rules engine blocks immediate post with `DEST_RULE_FREQUENCY_CAP`, calculating exact `reschedule_at` timestamp. |
| **HC8** | Promotional post submitted to community with `self_promo_allowed: false`. | Rules engine rejects post with rule violation; marks required human review or blocks delivery entirely. |
| **HC9** | Platform renames an API response field during runtime. | Connector fails schema validation; certification harness catches failure, demotes destination to `L0`, alerts admin. |
| **HC10** | CSV import contains duplicate destination entries (same URL + platform). | Deduplication engine flags subsequent rows as duplicates, keeps primary, records duplicate count in import report. |
| **HC11** | CSV import contains malformed URLs, missing required fields, syntax errors. | Validation isolates invalid rows, continues processing valid rows, generates downloadable row-by-row error report. |
| **HC12** | CSV import contains mixed languages across global communities. | Ingestion preserves language metadata; content tailoring engine flags language mismatches or triggers localized renditions. |
| **HC13** | Partner revokes webhook signing secret or endpoint returns 403/500. | Webhook connector detects signature/handshake failure, maps to `PLATFORM_UNAVAILABLE` or `CONNECTION_AUTH_EXPIRED`, ceases transmission. |
| **HC14** | Destination enforces mandatory AI-content disclosure tag. | Tailoring engine verifies presence of AI disclosure; if missing, appends compliant disclosure statement or flags for user confirmation. |

---

### 2.5 Required Submission Deliverables
1. **Submission Form**: Completed spreadsheet / checklist with proof links for all must-haves, levels, Integration Standard items, metrics, and hard cases.
2. **Live Demo URL**: Public deployment protected by revocable demo token and rate limiting.
3. **Repository**: Clean Git history with semantic commits; reviewer access granted to `admin@incubrix.com`.
4. **`README.md`**: Architecture overview, quickstart under 10 commands, test instructions, batch runner usage, error code reference.
5. **`openapi.yaml`**: Complete OpenAPI 3.1 specification.
6. **`REPORT.md`**: 2–4 page analytical report covering architectural trade-offs, empirical metrics, unit costs, and future work.
7. **`SOURCES.md` & `AI_USE.md`**: Full disclosure of third-party libraries, datasets, licenses, AI tools, and usage breakdown.
8. **Test Pack**: Comprehensive test artifacts, execution logs, failure runs, and evidence index.
9. **Demo Video**: Unedited screen recording (<=8 minutes) covering happy path, failure handling, test suite run, and code walkthrough.
10. **Certification Pack**: Structured evidence per certified destination (run logs, live URLs, API payloads, screenshots, deletion receipts).
11. **Catalogue Files**: Raw CSVs, import validation reports, and labeled recommender evaluation benchmark.

---

## 3. Traceability Matrix

Every requirement is mapped from specification through implementation, testing, and evidence collection. Initial status is set to `Pending`.

| Req ID | Requirement Description | Implementation Component | Test Case / Suite | Evidence Artifact | Status |
|:-------|:------------------------|:-------------------------|:------------------|:------------------|:-------|
| **REQ-MH1** | Exact connector contract (`/connector/v1/`) | `api/routers/connectors.py`, `connectors/base.py` | `tests/contract/test_connector_contract.py` | OpenAPI diff & contract test run logs | `Pending` |
| **REQ-MH2** | Six Core connectors certified | `connectors/{discourse,lemmy,devto,ghost,signed_webhook,assisted}` | `tests/integration/test_core_certification.py` | `certification_pack/core/*.json` | `Pending` |
| **REQ-MH3** | Configuration, not code for new instances | `engine/catalogue.py`, `models/destination.py` | `tests/integration/test_dynamic_destination.py` | Run log adding Discourse instance #41 | `Pending` |
| **REQ-MH4** | Pre-flight posting rules engine | `engine/rules_engine.py` | `tests/unit/test_rules_engine.py` | Spy verification logs (connector never called) | `Pending` |
| **REQ-MH5** | Never spam / delete within 10 min / 429 backoff | `engine/certifier.py`, `core/rate_limiter.py` | `tests/integration/test_cleanup_watchdog.py` | Deletion audit records & rate-limit logs | `Pending` |
| **REQ-MH6** | Safe retries & timeout reconciliation | `middleware/idempotency.py`, `engine/publisher.py` | `tests/integration/test_idempotency_retry.py` | Zero-duplicate database audit logs | `Pending` |
| **REQ-MH7** | Secrets protection & simulation mode | `core/logging.py`, `mock_platforms/` | `tests/unit/test_secret_redaction.py`, simulation suite | Clean log grep report & simulation run logs | `Pending` |
| **REQ-MH8** | Local test instances via Docker Compose | `docker-compose.yml`, Dockerfiles | Clean machine launch script | Compose startup health logs | `Pending` |
| **REQ-MH9** | Integration standard followed & demo online | All components & live deployment | `tests/e2e/test_end_to_end.py` | Live demo health ping & checklist | `Pending` |
| **REQ-COR1** | All must-haves passing | Complete test suite | `make test` | Full pytest terminal output report | `Pending` |
| **REQ-COR2** | Core connectors full certification run | `engine/certifier.py` | `tests/e2e/test_certification_e2e.py` | JSON run records & live URL verifications | `Pending` |
| **REQ-COR3** | Platform errors mapped to shared codes | `connectors/*/error_mapper.py` | `tests/unit/test_error_mapping.py` | Error translation matrix test results | `Pending` |
| **REQ-ADV1** | Catalogue CSV import (<5m for 1k rows) | `engine/catalogue_importer.py` | `tests/performance/test_import_benchmark.py` | Benchmark benchmark_1000_import.json | `Pending` |
| **REQ-ADV2** | AI community rules capture with human review | `engine/rule_capture.py` | `tests/unit/test_rule_capture.py` | Generated proposal vs confirmed rule diff | `Pending` |
| **REQ-ADV3** | Relevance scoring 1-5 against target audience | `engine/relevance.py` | `tests/unit/test_relevance_scoring.py` | Score distribution & rationale sample | `Pending` |
| **REQ-ADV4** | Content tailoring engine | `engine/tailoring.py` | `tests/unit/test_tailoring.py` | Input vs tailored renditions JSON | `Pending` |
| **REQ-ADV5** | Three advanced connectors (Hashnode, Slack, MRSS) | `connectors/{hashnode,slack,mrss}` | `tests/integration/test_advanced_connectors.py` | Certification records for advanced connectors | `Pending` |
| **REQ-OUT1** | Recommender ranking with precision@10 metric | `engine/recommender.py` | `tests/evaluation/test_recommender.py` | Precision evaluation report on labeled set | `Pending` |
| **REQ-OUT2** | Standardized `fetch_metrics` on 3 connectors | `connectors/{lemmy,ghost,hashnode}/client.py` | `tests/integration/test_metrics_fetching.py` | Normalized metrics JSON payloads | `Pending` |
| **REQ-OUT3** | 30-day recertification scheduler & demotion | `worker/tasks/recertification.py` | `tests/integration/test_recertification.py` | Demotion event log & alert notification | `Pending` |
| **REQ-OUT4** | Curated real catalogue of >=150 destinations | `data/catalogue_150.csv` | `tests/data/test_catalogue_validity.py` | Validated CSV export & stats breakdown | `Pending` |
| **REQ-IS1** | One-command start and test (`make test`) | `Makefile`, `docker-compose.yml` | Root CI execution script | Makefile run trace | `Pending` |
| **REQ-IS2** | Documented OpenAPI 3.1 specification | `api/main.py` -> `scripts/export_openapi.py` | `tests/contract/test_openapi_drift.py` | `openapi.yaml` diff validation | `Pending` |
| **REQ-IS3** | Background jobs (202, progress, callback) | `worker/job_manager.py`, `api/routers/jobs.py` | `tests/integration/test_background_jobs.py` | Polling trace & signed callback receipt | `Pending` |
| **REQ-IS4** | Idempotency-Key on POST endpoints | `middleware/idempotency.py` | `tests/integration/test_idempotency.py` | Parallel request race condition logs | `Pending` |
| **REQ-IS5** | Standardized error payload structure | `core/errors.py`, `core/exceptions.py` | `tests/unit/test_error_schemas.py` | Formatted error response snapshots | `Pending` |
| **REQ-IS6** | Environment-driven configuration | `core/config.py` (`Pydantic BaseSettings`) | `tests/unit/test_config.py` | `.env.example` validation check | `Pending` |
| **REQ-IS7** | S3/MinIO input/output handling | `core/storage.py` | `tests/integration/test_storage.py` | MinIO upload/download presigned URL tests | `Pending` |
| **REQ-IS8** | Structured JSON logging & correlation IDs | `core/logging.py`, `middleware/correlation.py` | `tests/unit/test_logging.py` | JSON log sample with X-Correlation-Id | `Pending` |
| **REQ-IS9** | Output manifest with timings, cost, rights | `engine/manifest_generator.py` | `tests/unit/test_manifest_generator.py` | Sample manifest.json artifacts | `Pending` |
| **REQ-IS10** | Batch runner CLI (`scripts/batch_runner.py`) | `scripts/batch_runner.py` | `tests/integration/test_batch_runner.py` | Batch run output directory tree & report | `Pending` |
| **REQ-HC1** | HC1: Publish timeout + idempotency retry | `engine/publisher.py`, `connectors/base.py` | `tests/hard_cases/test_hc01_timeout_retry.py` | Hard case test report HC01 | `Pending` |
| **REQ-HC2** | HC2: 429 rate limit backoff | `core/rate_limiter.py` | `tests/hard_cases/test_hc02_rate_limit_backoff.py` | Hard case test report HC02 | `Pending` |
| **REQ-HC3** | HC3: Token expiration (401) handling | `connectors/base.py`, `engine/publisher.py` | `tests/hard_cases/test_hc03_auth_expired.py` | Hard case test report HC03 | `Pending` |
| **REQ-HC4** | HC4: Platform content rejection (422) | `connectors/base.py`, `engine/publisher.py` | `tests/hard_cases/test_hc04_content_rejected.py` | Hard case test report HC04 | `Pending` |
| **REQ-HC5** | HC5: Title/body character limit violation | `engine/rules_engine.py` | `tests/hard_cases/test_hc05_length_violation.py` | Hard case test report HC05 | `Pending` |
| **REQ-HC6** | HC6: Unsupported media type/size | `engine/rules_engine.py` | `tests/hard_cases/test_hc06_media_unsupported.py` | Hard case test report HC06 | `Pending` |
| **REQ-HC7** | HC7: Frequency cap breach | `engine/rules_engine.py` | `tests/hard_cases/test_hc07_frequency_cap.py` | Hard case test report HC07 | `Pending` |
| **REQ-HC8** | HC8: Self-promotion violation | `engine/rules_engine.py` | `tests/hard_cases/test_hc08_self_promo_ban.py` | Hard case test report HC08 | `Pending` |
| **REQ-HC9** | HC9: Platform API field renaming demotion | `engine/certifier.py` | `tests/hard_cases/test_hc09_api_drift_demote.py` | Hard case test report HC09 | `Pending` |
| **REQ-HC10** | HC10: CSV duplicate detection & deduplication | `engine/catalogue_importer.py` | `tests/hard_cases/test_hc10_csv_duplicates.py` | Hard case test report HC10 | `Pending` |
| **REQ-HC11** | HC11: CSV malformed URLs and errors | `engine/catalogue_importer.py` | `tests/hard_cases/test_hc11_csv_bad_urls.py` | Hard case test report HC11 | `Pending` |
| **REQ-HC12** | HC12: Mixed languages in destinations | `engine/tailoring.py` | `tests/hard_cases/test_hc12_mixed_languages.py` | Hard case test report HC12 | `Pending` |
| **REQ-HC13** | HC13: Partner webhook revocation / secret rot | `connectors/signed_webhook/client.py` | `tests/hard_cases/test_hc13_revoked_webhook.py` | Hard case test report HC13 | `Pending` |
| **REQ-HC14** | HC14: Mandatory AI-content disclosure tag | `engine/tailoring.py`, `engine/rules_engine.py` | `tests/hard_cases/test_hc14_ai_disclosure.py` | Hard case test report HC14 | `Pending` |

---

## 4. Critical Ambiguities & Conservative Architectural Choices

### 4.1 Ambiguity 1: The `/connector/v1/` vs `/api/v1/` Routing Rule
- **The Ambiguity**: The brief states in Appendix A that connectors are exposed over HTTP at `POST /connector/v1/{connector_key}/{method}`, yet Integration Standard Point 2 states that all routes must reside under `/api/v1/`.
- **Conservative Architectural Choice**:
  - We strictly honor the explicit specification: `POST /connector/v1/{connector_key}/{method}` is treated as the **only documented connector-specific route prefix**.
  - `/connector/v1/` routes are implemented as pure, stateless protocol bridges. They accept renditions and credentials, execute network interactions against destination platforms, and return structured payloads. They **never read from or write to the IncuBrix database**.
  - All higher-level platform orchestration routes (content submission, job tracking, catalogue management, certification requests, rules administration, and analytics) reside strictly under `/api/v1/`.
  - Health checks `/health` and `/ready` sit at the root level.
  - Both route families are fully documented in the unified OpenAPI 3.1 schema.

### 4.2 Ambiguity 2: Enforcement of "Delete within 10 Minutes"
- **The Ambiguity**: Must-have 5 requires test posts to be deleted within 10 minutes. Relying on an inline synchronous call risks leaving orphaned posts if the process crashes or network fails between publish and delete.
- **Conservative Architectural Choice**:
  - **Two-tier cleanup guarantee**:
    1. *Immediate Synchronous Cleanup*: The certification harness verifies the live status of the post and immediately invokes `delete(platform_post_id, connection)`.
    2. *Durable Asynchronous Watchdog*: Whenever a test post is created during certification, an expirable record is inserted into Postgres and a Redis delay queue task is scheduled with a maximum TTL of 10 minutes (600s).
    3. If the post is not confirmed deleted within 10 minutes, the worker fires a hard cleanup task with exponential retries. If deletion still fails, the destination is automatically demoted to `L0`, an alert is generated, and the failure is recorded in the audit trail.
  - In simulation/mock platforms, an automated in-memory TTL purges any post older than 10 minutes regardless.

### 4.3 Ambiguity 3: "Agreed Sandbox" for Discourse and Dev.to
- **The Ambiguity**: Brief mentions posting only to "own test instances or agreed sandbox areas". Discourse and Dev.to are public production ecosystems; creating test accounts on live community forums can violate community guidelines and terms of service.
- **Conservative Architectural Choice**:
  - We **never** perform automated test posts against public third-party production forums or public Dev.to user feeds.
  - For Discourse, our primary integration target is a containerized Mock Discourse Server running in Docker Compose that mirrors the official Discourse REST API (`/posts.json`, `/t/{id}.json`) with configurable scenarios. For real instance validation, we support user-configured private self-hosted Discourse instances via `base_url`.
  - For Dev.to, we run a containerized mock service implementing the Forem API (`/api/articles`). When configured with a real developer API key, it posts exclusively in `published: false` (draft mode) or to an isolated test tag, verified and immediately deleted.
  - In all test packs and reports, mock runs are explicitly marked `mock` and never misrepresented as `real`.

### 4.4 Ambiguity 4: How Discourse is Tested Locally
- **The Ambiguity**: Running a full native Discourse instance in Docker Compose requires a Ruby on Rails stack, PostgreSQL, Redis, and a custom bootstrap script requiring >2GB RAM and 15+ minutes initialization time.
- **Conservative Architectural Choice**:
  - For Docker Compose (`docker compose up`), we run our lightweight, high-fidelity `mock-platforms` service. It implements the exact Discourse API endpoints, header validation, authentication formats (`Api-Key`, `Api-Username`), rate limiting with `Retry-After`, and field-level validation errors.
  - Lemmy and Ghost run as real, lightweight Docker containers directly in Docker Compose.
  - Our Discourse connector client is completely agnostic to whether it is speaking to the mock server or a live self-hosted Discourse instance because both implement the exact identical HTTP contract.

### 4.5 Ambiguity 5: Level (L0–L4) Assignment Rules
- **The Ambiguity**: Page 9 defines levels L0–L4. How are destinations categorized and promoted/demoted?
- **Conservative Architectural Choice**:
  - **L0 (Catalogued Only)**: The destination is recorded, normalized, and validated for schema and reachability, but has not completed end-to-end API certification.
  - **L1 (Assisted)**: The destination prohibits bot automation or lacks an open API. Content distribution is supported via `build_assist_pack` (downloadable asset package with tailored caption, link, and rules checklist for human manual posting).
  - **L2 (Bridged or Feed)**: Distribution occurs via RSS/MRSS syndicated feeds or signed outbound webhooks.
  - **L3 (Native API)**: Fully automated connector with end-to-end verified `validate`, `publish`, `get_status`, and `delete` methods against live or sandbox targets.
  - **L4 (Native API plus Metrics)**: Fulfills all L3 criteria AND implements verified `fetch_metrics` returning normalized engagement metrics (views, likes, comments, shares, clicks).
  - **Demotion Policy**: Any API failure, token expiration, schema violation, or failed 30-day recertification run immediately drops the destination back to `L0`. A mock certification can verify code readiness in tests but cannot promote a production destination to L3/L4.

---

## 5. The Three Highest Failure Risks & Mitigations

### 5.1 Risk 1: Silent Duplicate Posting After Timeout-After-Accept
- **The Risk**: A publish call is dispatched to a third-party platform. The platform processes the post and creates it, but a network drop, gateway timeout, or client timeout occurs before the HTTP response is returned. If the retry worker blindly re-executes `publish()`, a duplicate post is created. On forums and developer blogs, duplicate posts trigger automated spam filters and community account bans.
- **Root Cause**: Network unreliability paired with non-idempotent remote publishing endpoints.
- **Architectural Mitigation**:
  - Implement a **Reconcile-Before-Republish** pattern in the publish orchestration engine.
  - On retry of a timed-out job, the connector first executes an entity lookup:
    1. If the connector supports client-supplied idempotency tags (or client-side reference tracking), query the platform for existing posts created with that reference.
    2. Alternatively, invoke `get_status` or search by canonical content fingerprint/slug created within the preceding 15-minute window.
    3. If an existing post matching the fingerprint is found, adopt its `platform_post_id`, mark the publish step as successful, and skip the outbound `publish()` call entirely.
    4. If the state is indeterminable, halt the job, set status to `needs_review`, and alert the operator rather than risking a duplicate post.

### 5.2 Risk 2: Cascading Account Bans from Rate Limit Abuse and Unchecked Violations
- **The Risk**: Sending automated posts without respecting community frequency caps or blasting requests into HTTP 429 rate limit responses will burn API keys, get IP addresses blocklisted, and cause community moderators to ban IncuBrix across multiple destinations.
- **Root Cause**: Independent uncoordinated workers firing concurrent requests without shared token-bucket rate limiters or global destination locks.
- **Architectural Mitigation**:
  - Distributed Redis-backed Token Bucket and Sliding Window Rate Limiter tracking requests per-destination and per-connector.
  - Dynamic Backoff on HTTP 429: Parse `Retry-After` or `X-RateLimit-Reset` headers; immediately persist a lock on the destination and connector in Redis; block all outbound traffic until the reset window expires.
  - Circuit Breaker: Automatically trip a circuit breaker after 5 consecutive failures (`PLATFORM_UNAVAILABLE`), switching connector status to `degraded` and preventing thundering herds.
  - Hard Pre-Flight Rules Gate: The rules engine runs synchronously before any job is handed to a connector; a post that breaches frequency caps is automatically rescheduled to `now() + window` rather than being discarded or repeatedly attempted.

### 5.3 Risk 3: Connector Drift and Silent Schema Corruption from Renamed Platform Fields
- **The Risk**: Long-tail platforms and open-source software (Lemmy, Ghost, Discourse, Dev.to) continuously release updates that alter API payloads, rename response attributes, or change authentication schemes. Unnoticed drift leads to silent publish failures or corrupt data.
- **Root Cause**: External API volatility outside our control.
- **Architectural Mitigation**:
  - Strict Pydantic v2 validation contracts for all connector inputs and outputs. Any payload missing expected fields or containing mismatched types fails fast.
  - Automated 30-Day Recertification Engine: A scheduled background runner periodically executes an end-to-end certification cycle against every active destination.
  - If a platform renames a critical response field, the certification run fails immediately, demotes the destination from L3/L4 to L0, excludes it from the recommender and publishing pipelines, and raises a structured alert ticket.

---

## 6. Verification & Sign-off Criteria
This analysis represents the complete baseline requirements specification. All implementation and architectural artifacts will trace directly back to this document. Application code implementation will commence only upon explicit architectural approval.
