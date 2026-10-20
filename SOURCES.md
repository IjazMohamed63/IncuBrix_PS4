# SOURCES.md: Dependency & License Declarations

This document declares all third-party libraries, datasets, and runtime dependencies utilized by the IncuBrix Long-Tail Distribution Network, confirming commercial-use licensing compliance (no AGPL, no non-commercial CC BY-NC in application runtime).

---

## 1. Backend Runtime Dependencies (Python)

| Dependency | Version | License | Commercial Permitted? | Purpose in Project |
|:-----------|:--------|:--------|:----------------------|:-------------------|
| `fastapi` | 0.110.0 | MIT | Yes | High-performance asynchronous HTTP API framework |
| `uvicorn` | 0.28.0 | BSD-3-Clause | Yes | Production ASGI web server |
| `pydantic` | 2.6.4 | MIT | Yes | Data validation and settings management |
| `pydantic-settings` | 2.2.1 | MIT | Yes | Environment variable configuration loading |
| `sqlalchemy` | 2.0.28 | MIT | Yes | Asynchronous ORM and SQL toolkit |
| `asyncpg` | 0.29.0 | Apache-2.0 | Yes | High-performance PostgreSQL asynchronous driver |
| `alembic` | 1.13.1 | MIT | Yes | Relational database schema migrations |
| `redis` | 5.0.3 | MIT | Yes | Redis client for caching, rate-limiting, and queueing |
| `httpx` | 0.27.0 | BSD-3-Clause | Yes | Asynchronous HTTP client for platform connectors |
| `pyyaml` | 6.0.1 | MIT | Yes | Manifest YAML parsing |
| `cryptography` | 42.0.5 | Apache-2.0 / BSD | Yes | Cryptographic HMAC-SHA256 signatures and JWT generation |
| `minio` | 7.2.5 | Apache-2.0 | Yes | S3-compatible object storage SDK |
| `python-multipart` | 0.0.9 | Apache-2.0 | Yes | Multipart form-data parser for CSV imports |
| `pytest` | 8.1.1 | MIT | Yes | Test framework |
| `pytest-asyncio` | 0.23.5 | Apache-2.0 | Yes | Asynchronous test execution runner |
| `pytest-cov` | 4.1.0 | MIT | Yes | Test coverage reporting |
| `aiosqlite` | 0.22.1 | MIT | Yes | Asynchronous SQLite driver for zero-dependency cloud deployments |


---

## 2. Infrastructure Containers (Docker Compose)

| Image | Version / Tag | License | Purpose |
|:------|:--------------|:--------|:--------|
| `postgres` | 16-alpine | PostgreSQL License (BSD-like) | Relational database engine |
| `redis` | alpine | BSD-3-Clause | Memory broker, rate-limit cache, distributed locks |
| `cleanstart/minio` | latest | GNU AGPLv3 (Local Container Only) | Local object store service; local development container only, **NOT** distributed or bundled into proprietary code. |
| `ghost` | 5-alpine | MIT | Local sandbox instance for Ghost blog connector validation |
| `dessalines/lemmy` | 0.19.5 | AGPLv3 (Local Container Only) | Local development sandbox instance for Lemmy federated community validation; local container only, **NOT** distributed or bundled into proprietary code. |

---

## 3. Frontend Dashboard Dependencies (Web)

| Dependency | Version | License | Commercial Permitted? | Purpose |
|:-----------|:--------|:--------|:----------------------|:--------|
| `react` | 19.3.1 | MIT | Yes | Modern declarative UI component model |
| `react-dom` | 19.3.1 | MIT | Yes | DOM renderer for React |
| `typescript` | 5.8.0 | Apache-2.0 | Yes | Type-safe contract verification |
| `vite` | 8.3.4 | MIT | Yes | Next-generation frontend bundler and dev server |
| `tailwindcss` | 3.4.17 | MIT | Yes | Utility-first CSS styling engine |
| `postcss` | 8.5.3 | MIT | Yes | CSS transformation pipeline |
| `autoprefixer` | 10.4.21 | MIT | Yes | Vendor prefix injection |
| `lucide-react` | 1.16.0 | ISC | Yes | Iconography library |

---

## 4. Verification Statement
All dependencies have been reviewed and verified for commercial use. No AGPL-licensed code is compiled, linked, or distributed in the IncuBrix application binary or runtime package.
