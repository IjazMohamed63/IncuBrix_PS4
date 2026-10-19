# IncuBrix Long-Tail Distribution Network

Containerized distribution connector engine, pre-flight rules compliance system, 8-step automated certification harness, and live React control plane built for IncuBrix Engineering Assessment 4.

---

## 1. System Architecture

```mermaid
flowchart TD
    Client["Clients / Dashboard / API Consumers"]
    API["FastAPI Control Plane (:8000)"]
    MW["Security & Correlation Middleware"]
    RulesEngine["Pre-Flight Posting Rules Engine"]
    Tailor["Content Tailoring Engine"]
    IdempLock["Atomic Idempotency & Replay Store"]
    JobMgr["Durable Background Job Manager (:SQLite/Redis)"]
    Registry["Connector Manifest Registry (9 Connectors)"]
    CertHarness["8-Step Automated Certification Harness"]
    Storage["S3 / MinIO Artifact Storage (:9000)"]

    %% Connectors
    Discourse["discourse (Multi-Instance)"]
    Lemmy["lemmy (Federated Container)"]
    DevTo["devto (Developer Hub)"]
    Ghost["ghost (Admin JWT Container)"]
    Webhook["signed_webhook (HMAC-SHA256)"]
    Assisted["assisted (Manual Pack)"]
    Hashnode["hashnode (Engineering Blog)"]
    Slack["slack (Webhook Syndication)"]
    MRSS["mrss_feed (XML Syndication)"]

    Client -->|X-IncuBrix-Token| API
    API --> MW
    MW --> IdempLock
    IdempLock --> RulesEngine
    RulesEngine -->|ALLOW| Tailor
    RulesEngine -->|BLOCK / RESCHEDULE| API
    Tailor --> JobMgr
    JobMgr --> Registry
    Registry --> Discourse & Lemmy & DevTo & Ghost & Webhook & Assisted & Hashnode & Slack & MRSS
    CertHarness -->|8 Steps| Registry
    CertHarness --> Storage
    JobMgr --> Storage
```

---

## 2. Quickstart Setup (Under 10 Commands)

To run the entire platform locally from a clean clone:

```bash
# 1. Clone repository
git clone https://github.com/incubrix-candidate/incubrix-distribution.git
cd incubrix-distribution

# 2. Setup environment variables
cp .env.example .env

# 3. Create virtual environment & activate
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# 4. Install backend dependencies
pip install -r requirements.txt

# 5. Start infrastructure containers (Postgres, Redis, MinIO, Lemmy, Ghost)
docker compose up -d

# 6. Apply database migrations
alembic upgrade head

# 7. Run full automated test suite (107 tests passing)
pytest

# 8. Start FastAPI backend server
uvicorn api.main:app --host 0.0.0.0 --port 8000

# 9. (Optional) Start React + Vite Web Dashboard
cd web && npm install && npm run dev
```

---

## 3. Environment Variables Reference

| Variable | Default Value | Description |
| :--- | :--- | :--- |
| `APP_ENV` | `development` | Runtime environment (`development`, `production`, `test`) |
| `APP_PORT` | `8000` | FastAPI server listening port |
| `SIMULATION_MODE` | `true` | When true, mock platform sandboxes are enabled and mock runs cannot grant real tiers |
| `DATABASE_URL` | `postgresql+asyncpg://incubrix_user:...@localhost:5432/incubrix_db` | Asynchronous PostgreSQL connection string |
| `REDIS_URL` | `redis://localhost:6379/0` | Redis connection URL for distributed locking and queues |
| `S3_ENDPOINT` | `localhost:9000` | MinIO / S3 object storage host endpoint |
| `S3_ACCESS_KEY` | `incubrix_minio_admin` | S3 administrative access key |
| `S3_SECRET_KEY` | `incubrix_minio_secret_key...` | S3 administrative secret key |
| `S3_BUCKET_NAME` | `incubrix-artifacts` | Storage bucket for certification evidence packs and output manifests |
| `WEBHOOK_SIGNING_SECRET` | `whsec_dev_placeholder_signing_key_32chars` | Secret key used to generate `X-IncuBrix-Signature` HMAC-SHA256 headers |
| `API_ACCESS_TOKEN` | `incubrix_demo_reviewer_token_2026` | Revocable reviewer authentication token |

---

## 4. Automated Testing Suite

The repository contains 107 automated unit, contract, certification, and reliability tests:

```bash
# Run all tests
pytest -q

# Run contract verification tests across all 9 connectors
pytest tests/contract/

# Run pre-flight posting rules and 14 hard cases
pytest tests/unit/test_rules_engine.py tests/test_hard_cases.py

# Run durable background jobs & idempotency concurrency tests
pytest tests/unit/test_durable_jobs.py tests/test_idempotency_concurrency.py

# Run OpenAPI 3.1 specification drift test
pytest tests/test_openapi_contract.py
```

---

## 5. Batch Certification Runner CLI

Run the automated 8-step certification runner across the destination catalogue:

```bash
# Run batch certification with mock platform sandboxes
python -m scripts.run_batch_certification --input data/seed_catalogue.csv --mock

# Run against real local containers (Ghost on :2368, Lemmy on :8536)
python -m scripts.run_batch_certification --input data/seed_catalogue.csv --real

# Custom output directory
python -m scripts.run_batch_certification --input data/seed_catalogue.csv --output-dir batch_run_output
```

---

## 6. Standard IncuBrix Error Codes & Mapping

All platform-specific connector exceptions are mapped to standard IncuBrix shared codes:

| Error Code | HTTP Status | Retryable? | Description |
| :--- | :---: | :---: | :--- |
| `UNAUTHORIZED` | 401 | No | Token invalid, revoked, or expired; re-authentication required |
| `FORBIDDEN` | 403 | No | Insufficient permissions on the target platform surface |
| `NOT_FOUND` | 404 | No | Destination, connector, job, or resource does not exist |
| `DEST_SPEC_VIOLATION` | 422 | No | Rendition violates surface limits (e.g. title too long, body missing) |
| `RATE_LIMITED` | 429 | Yes | Platform or connector quota exceeded; includes computed `reset_after_s` |
| `TIMEOUT` | 504 | Yes | Platform took longer than 2.0s; reconciled via durable background job |
| `DOWNSTREAM_UNAVAILABLE` | 503 | Yes | Upstream target platform offline or 5xx server error |
| `INTERNAL_ERROR` | 500 | No | Unhandled internal exception |

---

## 7. Simulation Mode Specification

- **Flag**: Configured via `SIMULATION_MODE=true` or dynamically toggled in `/api/v1/security/simulation-mode`.
- **Top Banner**: Clear, persistent warning banner displayed across the top of the React dashboard.
- **Contract Guarantee**: Certification runs executed in mock mode are strictly labeled `"mock"` in output manifests and can **never** grant a real-certified level (`L2` / `L3`).
- **Isolation**: Prevents side-effects against public external platforms while validating end-to-end pipeline compliance.
