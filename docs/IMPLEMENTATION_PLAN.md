# IncuBrix Long-Tail Distribution Network: Implementation Plan

**Document**: Implementation Plan & Engineering Roadmap  
**Assessment**: IncuBrix Engineering Assessment 4  
**Date**: October 2026  
**Status**: Architecture Baseline  

---

## 1. Technology Stack with Exact Versions

All components are selected to ensure 100% commercial-use compliance (per `SOURCES.md` requirements; zero AGPL dependencies in the distributed application), rock-solid stability, and sub-second developer feedback loops.

### 1.1 Backend Service & Workers
| Technology | Exact Version | Rationale & Responsibility |
|:-----------|:--------------|:---------------------------|
| **Python** | `3.11.8` | Core runtime; leverages modern typing and asynchronous performance optimizations. |
| **FastAPI** | `0.110.0` | High-performance asynchronous REST API framework; native OpenAPI 3.1 generation. |
| **Uvicorn** | `0.28.0` | Production-grade ASGI server with uvloop integration. |
| **Pydantic** | `2.6.4` | High-throughput data validation and settings management (`pydantic-settings 2.2.1`). |
| **SQLAlchemy** | `2.0.28` | Asynchronous ORM utilizing `asyncpg` (`0.29.0`) for PostgreSQL interaction. |
| **Alembic** | `1.13.1` | Deterministic, version-controlled database schema migrations. |
| **HTTPX** | `0.27.0` | Asynchronous HTTP client powering all external platform and connector communications. |
| **PyYAML** | `6.0.1` | Strict YAML parser for connector manifests (`manifest.yaml`). |
| **Cryptography** | `42.0.5` | Cryptographic primitives for HMAC-SHA256 signatures, webhook verification, and Ghost Admin JWTs. |
| **redis-py** | `5.0.3` | Async Redis client for job queueing, distributed locking, and rate limiting. |
| **MinIO Python SDK** | `7.2.5` | S3-compatible client for storing evidence packs, raw CSVs, and media files. |
| **Pytest** | `8.1.1` | Comprehensive test suite runner (`pytest-asyncio 0.23.5`, `pytest-cov 4.1.0`). |

### 1.2 Frontend Dashboard
| Technology | Exact Version | Rationale & Responsibility |
|:-----------|:--------------|:---------------------------|
| **React** | `18.2.0` | Standard UI library for declarative component state. |
| **TypeScript** | `5.3.3` | Type-safe interface definitions mirroring OpenAPI schemas. |
| **Vite** | `5.1.4` | Ultra-fast bundling and local development server. |
| **TailwindCSS** | `3.4.1` | Utility-first styling for clean, responsive, dark-mode dashboard aesthetics. |
| **Lucide-React** | `0.344.0` | Clean, lightweight icon suite for state and navigation indicators. |

### 1.3 Infrastructure & Sandboxes (Docker Compose)
| Container / Service | Image & Version | Port | Purpose |
|:--------------------|:----------------|:-----|:--------|
| **api** | `incubrix-api:latest` (Python 3.11) | `8000` | Core FastAPI application server. |
| **worker** | `incubrix-worker:latest` (Python 3.11) | - | Background job consumer & recertification scheduler. |
| **postgres** | `postgres:16-alpine` | `5432` | Relational database for durable application state. |
| **redis** | `redis:7.2-alpine` | `6379` | Queue broker, token-bucket cache, idempotency locks. |
| **minio** | `minio/minio:RELEASE.2024-03-03T17-50-39Z` | `9000`, `9001` | S3-compatible object store for artifacts and evidence. |
| **ghost-sandbox** | `ghost:5-alpine` | `2368` | Real local Ghost blog instance for native API verification. |
| **lemmy-sandbox** | Custom / Mock Lemmy REST Container | `8536` | Local Lemmy community backend for native federated posting. |
| **mock-platforms** | `incubrix-mock-platforms:latest` | `8080` | High-fidelity mock server for Discourse, Dev.to, Webhooks, Slack, and Hashnode. |

---

## 2. Repository Directory Structure

```text
Incubrix-app/
├── .env.example                       # Documented environment variables with placeholders
├── .gitignore                          # Excludes .env, docs/brief, __pycache__, node_modules
├── Makefile                            # One-command orchestration: make up, make test, make batch
├── README.md                           # Quickstart (<10 commands), architecture, settings, error codes
├── REPORT.md                           # Analytical report (2-4 pages): numbers, trade-offs, unit costs
├── SOURCES.md                          # Licensing declaration for all libraries, datasets, and models
├── AI_USE.md                           # Disclosure of AI tools, assistants, and code generations
├── docker-compose.yml                  # Service orchestration (API, worker, db, redis, minio, sandboxes)
├── openapi.yaml                        # OpenAPI 3.1 specification exported from FastAPI
│
├── api/                                # Core FastAPI HTTP Service
│   ├── main.py                         # Application factory, middleware registration, router mounting
│   ├── dependencies.py                 # Dependency injection (DB session, Redis, Auth, Storage)
│   ├── middleware/
│   │   ├── correlation.py              # Injects and propagates X-Correlation-Id
│   │   ├── idempotency.py              # Idempotency-Key validation and distributed locking
│   │   ├── rate_limit.py               # Token bucket rate limiting middleware
│   │   └── error_handler.py            # Global exception handler producing standardized JSON error schema
│   └── routers/
│       ├── health.py                   # GET /health and GET /ready endpoints
│       ├── connectors.py               # POST /connector/v1/{connector_key}/{method} (Appendix A)
│       ├── publish.py                  # POST /api/v1/publish (Content ingestion & job creation)
│       ├── jobs.py                     # GET /api/v1/jobs/{job_id} & cancellation
│       ├── destinations.py             # CRUD /api/v1/destinations and CSV import
│       ├── rules.py                    # GET/POST /api/v1/rules, AI rule capture & confirmation
│       ├── certifications.py           # POST /api/v1/destinations/{id}/certify & run logs
│       ├── recommendations.py          # POST /api/v1/recommendations
│       └── metrics.py                  # GET /api/v1/metrics/*
│
├── connectors/                         # Connector Implementations (One folder per connector)
│   ├── base.py                         # Abstract BaseConnector contract & schema validators
│   ├── registry.py                     # Manifest loader, schema validation, connector registry
│   ├── discourse/
│   │   ├── manifest.yaml               # Discourse connector specification
│   │   ├── client.py                   # Discourse REST API implementation (multi-instance base_url)
│   │   └── error_map.py                # Platform error translation
│   ├── lemmy/
│   │   ├── manifest.yaml
│   │   ├── client.py
│   │   └── error_map.py
│   ├── devto/
│   │   ├── manifest.yaml
│   │   ├── client.py
│   │   └── error_map.py
│   ├── ghost/
│   │   ├── manifest.yaml
│   │   ├── client.py                   # Admin API with short-lived JWT generation
│   │   └── error_map.py
│   ├── signed_webhook/
│   │   ├── manifest.yaml
│   │   ├── client.py                   # HMAC-SHA256 signature generator & dispatcher
│   │   └── error_map.py
│   ├── assisted/
│   │   ├── manifest.yaml
│   │   └── client.py                   # build_assist_pack implementation
│   ├── hashnode/                       # Advanced Connector: GraphQL developer publishing
│   ├── slack/                          # Advanced Connector: Slack Bot/Webhook
│   └── mrss/                           # Advanced Connector: Syndicated Media RSS Feed
│
├── core/                               # Central System Kernel & Infrastructure
│   ├── config.py                       # Pydantic BaseSettings loading .env
│   ├── database.py                     # Async SQLAlchemy engine & session factory
│   ├── storage.py                      # MinIO S3 wrapper for evidence and artifact uploads
│   ├── logging.py                      # Structured JSON logger with secret redaction filters
│   ├── errors.py                       # Standard error codes & AppBaseException
│   └── rate_limiter.py                 # Redis token bucket & backoff window manager
│
├── engine/                             # Core Business Intelligence & Orchestration
│   ├── rules_engine.py                 # Pre-flight posting rule evaluation
│   ├── publisher.py                    # Publish execution & timeout reconciliation logic
│   ├── certifier.py                    # Automated certification runner & watchdog coordinator
│   ├── tailoring.py                    # Format adaptation (discussion hook, canonical URL, AI tags)
│   ├── catalogue_importer.py           # High-performance CSV import, normalization, de-duplication
│   ├── rule_capture.py                 # AI community rules extraction adapter
│   ├── recommender.py                  # Destination ranking & precision evaluation engine
│   └── manifest_generator.py           # Output JSON manifest constructor
│
├── models/                             # SQLAlchemy Relational Models
│   ├── base.py                         # Base declarative class with timestamps
│   ├── destination.py                  # Destination entity matching 20 spec fields
│   ├── connection.py                   # Auth credentials & base_url parameters
│   ├── rule.py                         # Posting rules & rule decision audit logs
│   ├── job.py                          # Asynchronous jobs & publish records
│   ├── certification.py                # Certification runs & deletion watchdog records
│   └── metrics.py                      # Normalized metric snapshots
│
├── worker/                             # Asynchronous Job Execution Service
│   ├── worker.py                       # Async worker loop listening to Redis queue
│   ├── tasks/
│   │   ├── publish_task.py             # Asynchronous publish execution & status poll
│   │   ├── certification_task.py       # Certification workflow execution
│   │   ├── recertification_cron.py     # 30-day recurring recertification scheduler
│   │   └── cleanup_watchdog_task.py    # 10-minute deletion enforcer
│
├── mock_platforms/                     # Simulation Environment & Mock Servers
│   ├── main.py                         # Mock HTTP server exposing Discourse, Dev.to, Webhook receiver
│   ├── state.py                        # In-memory post store with 10-minute auto-expiry
│   └── scenarios.py                    # Scripted failure scenarios (429, timeout, rename field)
│
├── scripts/                            # Operational & Test Automation Utilities
│   ├── batch_runner.py                 # CLI tool running test inputs, writing all results to folder
│   ├── export_openapi.py               # Generates openapi.yaml directly from FastAPI schema
│   ├── seed_catalogue.py               # Populates database with initial 150 real destinations
│   └── benchmark_import.py             # Benchmarks 1,000-row CSV import timing
│
├── tests/                              # Comprehensive Test Suite
│   ├── conftest.py                     # Test fixtures, mock clients, test DB setup
│   ├── contract/                       # Strict connector contract & OpenAPI drift tests
│   ├── unit/                           # Unit tests (rules, tailoring, secrets, error mapping)
│   ├── integration/                    # Integration tests (DB, Redis, MinIO, Connectors)
│   ├── hard_cases/                     # Dedicated test scripts for all 14 Hard Cases
│   ├── evaluation/                     # Precision@10 evaluator for Recommender
│   └── e2e/                            # Full end-to-end publish and certification flows
│
└── web/                                # React Dashboard Application
    ├── package.json
    ├── vite.config.ts
    ├── tailwind.config.js
    └── src/
        ├── App.tsx
        ├── pages/                      # Overview, Destinations, Connectors, Publish, Certs, Jobs
        └── components/                 # SimulationModeBanner, EvidenceViewer, StatusBadge
```

---

## 3. API Route Plan

### 3.1 Connector Contract Routes (Appendix A Exception)
*Pure protocol bridges; stateless, return results only, never touch IncuBrix database.*

| Method | Route Path | Request Body | Response Payload | Description |
|:-------|:-----------|:-------------|:-----------------|:------------|
| `POST` | `/connector/v1/{connector_key}/validate` | `{rendition, destination, connection}` | `{"ok": bool, "violations": []}` | Pre-validates content against platform spec. |
| `POST` | `/connector/v1/{connector_key}/publish` | `{rendition, destination, connection, idempotency_key}` | `{"platform_post_id": str, "live_url": str, "status": str}` | Publishes content to destination. |
| `POST` | `/connector/v1/{connector_key}/get_status` | `{"platform_post_id": str, "connection": {...}}` | `{"status": str, "live_url": str}` | Verifies live availability of published post. |
| `POST` | `/connector/v1/{connector_key}/delete` | `{"platform_post_id": str, "connection": {...}}` | `{"deleted": bool}` | Deletes post from destination. |
| `POST` | `/connector/v1/{connector_key}/fetch_metrics` | `{"platform_post_id": str, "connection": {...}, "since": str}` | `{"views", "likes", "comments", "shares", "saves", "watch_time_s", "clicks"}` | Fetches normalized engagement metrics. |
| `POST` | `/connector/v1/{connector_key}/refresh_auth` | `{"connection": {...}}` | `{"expires_at": str}` | Refreshes expiring authentication tokens. |
| `POST` | `/connector/v1/{connector_key}/build_assist_pack` | `{rendition, destination}` | `{"files": [], "caption": str, "deep_link": str, "checklist": []}` | Builds ready-to-post package (Assisted tier). |

### 3.2 System & Core Application Routes (`/api/v1/` and Root)

| Method | Route Path | Headers / Params | Response | Description |
|:-------|:-----------|:-----------------|:---------|:------------|
| `GET` | `/health` | None | `{"status": "pass"}` | Instant liveness check. |
| `GET` | `/ready` | None | `{"status": "ready", "checks": {"database": "up", "redis": "up", "storage": "up"}}` | Deep readiness verifying all dependencies. |
| `POST` | `/api/v1/publish` | `Idempotency-Key` (req) | `202 Accepted {"job_id": "...", "status": "queued"}` | Main content publish entrypoint. |
| `GET` | `/api/v1/jobs/{job_id}` | None | `{"job_id", "status", "progress", "results": [], "manifest": {...}}` | Background job progress & status polling. |
| `POST` | `/api/v1/jobs/{job_id}/cancel` | None | `{"job_id", "status": "cancelled"}` | Cancels an active or queued job. |
| `GET` | `/api/v1/destinations` | `query, category, level, limit, offset` | `{"items": [...], "total": int}` | Lists and filters catalogue destinations. |
| `POST` | `/api/v1/destinations` | Destination JSON | `201 Created` Destination Record | Adds a new destination (1 configuration row). |
| `GET` | `/api/v1/destinations/{id}` | None | Destination Record Details | Retrieves full destination details and rules. |
| `PUT` | `/api/v1/destinations/{id}` | Destination Update JSON | Updated Destination Record | Updates destination metadata or rules. |
| `DELETE` | `/api/v1/destinations/{id}` | None | `204 No Content` | Removes destination from catalogue. |
| `POST` | `/api/v1/destinations/import` | `multipart/form-data` (CSV) | `202 Accepted {"job_id": "..."}` | High-speed CSV import process. |
| `GET` | `/api/v1/destinations/import/{job_id}/report`| None | CSV / JSON error report | Downloads row-by-row import failure report. |
| `POST` | `/api/v1/destinations/{id}/certify` | `{"is_mock": bool}` | `202 Accepted {"job_id": "..."}` | Triggers certification run for destination. |
| `GET` | `/api/v1/certifications` | `destination_id, limit` | `{"runs": [...]}` | Lists historical certification records. |
| `GET` | `/api/v1/certifications/{id}` | None | Certification Run & Evidence Pack | Fetches step-by-step logs and proof links. |
| `GET` | `/api/v1/rules` | `destination_id` | `{"rules": [...]}` | Lists active rules for destinations. |
| `POST` | `/api/v1/rules/propose` | `{"rules_url": str, "community_text": str}` | Proposed Rules JSON | AI-assisted rule extraction proposal. |
| `POST` | `/api/v1/rules/{id}/confirm` | `{"confirmed": bool}` | Updated Rule Record | Human confirmation activating a proposed rule. |
| `POST` | `/api/v1/recommendations` | `{content: {...}, limit: 10}` | `{"recommendations": [{"destination_id", "score", "reasons": [...]}]}` | Recommender ranking candidate destinations. |
| `GET` | `/api/v1/connectors` | None | `{"connectors": [...]}` | Lists registered manifests, versions, and tiers. |
| `POST` | `/api/v1/connectors/{key}/toggle` | `{"enabled": bool}` | `{"connector_key": str, "enabled": bool}` | Kill-switch toggling `CONNECTOR_DISABLED`. |

---

## 4. Milestone List & Acceptance Criteria

### Milestone 1: Analysis & Architecture (Prompt 1) - Current
- **Acceptance Criteria**:
  - `docs/REQUIREMENTS_ANALYSIS.md` completed (problem, must-haves, levels, IS points, 14 hard cases, traceability matrix, ambiguities, risks).
  - `docs/ARCHITECTURE.md` completed with 5 valid Mermaid diagrams (C4 container, 3 sequence diagrams, 2 state machines, ER diagram).
  - `docs/IMPLEMENTATION_PLAN.md` completed with exact versions, repo structure, API route plan, milestones, and risk register.
  - Zero application code written before explicit approval.

### Milestone 2: Foundation & Connector Contract (Prompt 2)
- **Acceptance Criteria**:
  - `docker-compose.yml`, `.env.example`, `.gitignore`, structured logging with `X-Correlation-Id` and secret redaction.
  - `GET /health` and deep `GET /ready` functional.
  - Manifest loader and validator validating Appendix A YAML schemas on startup.
  - Connector registry and `POST /connector/v1/{connector_key}/{method}` router operational.
  - Standard error codes and global error handler active.
  - `pytest tests/contract` passes against a contract stub.

### Milestone 3: Six Core Connectors (Prompt 3)
- **Acceptance Criteria**:
  - Six functional connectors: Discourse, Lemmy, Dev.to, Ghost, Signed Webhook, Assisted.
  - Docker Compose spins up real Lemmy and real Ghost instances, plus mock platforms.
  - All 6 connectors pass validation, publish, status check, and deletion.
  - Multi-instance capability proven: adding a second Discourse forum requires only 1 catalogue row, zero code changes.

### Milestone 4: Rules Engine, Reliability & 14 Hard Cases (Prompt 4)
- **Acceptance Criteria**:
  - Posting-rules engine operational (frequency cap, self-promo ban, link policy, AI disclosure).
  - Blocked posts provably never hit connectors (verified with spy tests).
  - `Idempotency-Key` concurrency protection (parallel requests produce exactly 1 post).
  - Timeout reconciliation logic prevents duplicate publishing.
  - 429 rate limit backoff and circuit-breaker active.
  - All 14 Hard Cases have dedicated automated tests in `tests/hard_cases/` with recorded results.

### Milestone 5: Jobs, Certification, Manifests & Batch Runner (Prompt 5)
- **Acceptance Criteria**:
  - Background jobs return 202 + `job_id`, progress 0–100, signed webhook callbacks.
  - MinIO file in/out storage operational with presigned download links.
  - Output manifest JSON generated on every result.
  - End-to-end certification harness with 10-minute deletion watchdog and automated demotion on API drift.
  - Standalone batch runner CLI `scripts/batch_runner.py` executes test inputs and dumps full output folder.
  - `make test` runs all tests with zero external API keys.

### Milestone 6: Catalogue & Advanced Features (Prompt 6)
- **Acceptance Criteria**:
  - CSV import with deduplication, normalization, reachability, and row-level error logs.
  - Benchmark 1,000-row CSV import and record actual execution time.
  - AI rule capture adapter with human confirmation flow.
  - Content tailoring engine (discussion hooks, canonical URLs, word-boundary truncation, hashtags).
  - Three advanced connectors implemented: Hashnode, Slack, MRSS.
  - Recommender with measured precision@10 on labeled benchmark set.
  - Metrics fetching normalized across 3 connectors (`null` when unsupported).
  - 30-day recertification scheduler with automated demotion alerts.
  - Real catalogue of >=150 verified destinations.

### Milestone 7: Web Dashboard (Prompt 7)
- **Acceptance Criteria**:
  - React + TypeScript + Vite + Tailwind dashboard connected to live API.
  - Clear `SIMULATION MODE` banner.
  - Pages: Overview, Destinations, Connectors, Publish, Rules, Certification Center, Jobs & Logs.
  - Evidence viewer with direct links to MinIO artifacts.
  - Public demo protection with revocable demo access token and rate limiting.

### Milestone 8: Hardening, Submission Pack & Final Verification (Prompt 8)
- **Acceptance Criteria**:
  - `openapi.yaml` exported and tested for zero drift against live endpoints.
  - `README.md`, `REPORT.md` (2–4 pages with empirical data), `SOURCES.md`, `AI_USE.md`.
  - Complete Test Pack and Certification Pack assembled.
  - Submission Form fully completed with links to evidence.
  - Clean machine check passed: fresh clone, `cp .env.example .env`, `docker compose up`, `make test`.

---

## 5. Comprehensive Risk Register

| Risk ID | Description | Severity | Likelihood | Detection Mechanism | Mitigation Strategy |
|:--------|:------------|:---------|:-----------|:--------------------|:--------------------|
| **RSK-01** | Duplicate post dispatched after network timeout during publish. | Critical | High | Idempotency integration tests; mock platform receive counter. | Implement Reconcile-Before-Republish: query destination for post fingerprint prior to re-attempting `publish()`. Mark `needs_review` if indeterminable. |
| **RSK-02** | Test posts not cleaned up within 10 minutes on external or sandbox platforms. | High | Medium | Deletion watchdog table audit; automated cleanup unit tests. | Dual cleanup architecture: immediate synchronous `delete()` followed by Redis delay queue watchdog with a strict 600s TTL. Auto-demote destination if deletion fails. |
| **RSK-03** | Third-party platform renames response fields (API drift), breaking parsing. | High | Medium | Pydantic response validation; certification test harness. | Strict Pydantic models reject mismatched schemas; 30-day recertification demotes destination to `L0` and generates an alert ticket. |
| **RSK-04** | Accidental leakage of test credentials or auth tokens into Git or logs. | Critical | Low | CI regex grep script scanning Git commits and output log files. | Custom JSON logging formatter redacts tokens via regex pattern matching; `.env` strictly gitignored; automated test in `tests/unit/test_secret_redaction.py`. |
| **RSK-05** | Rate-limit cascading lockouts (429 spamming). | High | High | Mock platform 429 scenario tests; rate limit audit logs. | Parse `Retry-After` headers and persist destination backoff window in Redis; block all outbound traffic until window elapses; trip circuit breaker after 5 consecutive failures. |
| **RSK-06** | 1,000-row CSV import exceeds the 5-minute performance threshold. | Medium | Medium | Automated performance benchmark script (`scripts/benchmark_import.py`). | Asynchronous streaming CSV parser, batch database insertions (`bulk_insert_mappings`), and concurrent async URL reachability probes via `asyncio.gather` with a semaphore. |
| **RSK-07** | Docker Compose startup failure or resource exhaustion on reviewer's machine. | High | Medium | Clean-machine verification run on an isolated container / environment. | Lightweight Alpine container bases; mock-platforms server handles heavy platforms (Discourse) so memory footprint stays well under 2GB. |
| **RSK-08** | Inadvertent inclusion of AGPL or non-commercial open-source code. | High | Low | Automated dependency license audit in `tests/test_licenses.py`. | Every dependency vetted for MIT/Apache-2.0/BSD; documented in `SOURCES.md`. |

---

## 6. Execution Command Summary
- Launch Development Environment: `docker compose up -d`
- Run Full Test Suite: `make test` (or `pytest`)
- Run Contract Suite: `pytest tests/contract`
- Run Hard Cases Suite: `pytest tests/hard_cases`
- Run Batch Runner: `python scripts/batch_runner.py tests/data/batch_sample.json --out output/batch_results`
