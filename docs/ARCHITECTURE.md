# IncuBrix Long-Tail Distribution Network: Architecture Specification

**Document**: System Architecture & Design Specification  
**Assessment**: IncuBrix Engineering Assessment 4  
**Date**: October 2026  
**Status**: Architecture Baseline  

---

## 1. Architectural Philosophy & Design Principles

The IncuBrix Long-Tail Distribution Network is engineered around five fundamental architectural tenets:

1. **Stateless Connectors, Stateful Runtime**:
   Per Appendix A of the IncuBrix specification, connectors are pure protocol translators. A connector method (`validate`, `publish`, `get_status`, `delete`, `fetch_metrics`, `refresh_auth`, `build_assist_pack`) accepts inputs, communicates over HTTP with the target platform, and returns structured result dictionaries. Connectors **never touch the IncuBrix database**. All state management, audit logging, rate limiting, and persistence are owned exclusively by the central runtime.
2. **One Connector, Many Destinations (Instance Parameterization)**:
   A connector defines the protocol adapter for a platform class (e.g., `discourse`, `lemmy`, `ghost`). Individual destinations (e.g., Discourse Forum A vs Forum B) are represented purely as configuration rows in the catalogue referencing `instance_param` (such as `base_url`). Scaling the long tail requires zero code modifications.
3. **Pre-flight Rules & Zero-Tolerance Safety**:
   No post touches a connector without passing through the deterministic Posting-Rules Engine. Frequency caps, link constraints, self-promotion rules, and mandatory AI-disclosure tags are checked before any network dispatch. Test posts are isolated to local sandboxes and guaranteed deleted within 10 minutes.
4. **Defensive Concurrency & Reconcile-Before-Republish**:
   Every state-altering request requires an `Idempotency-Key`. In the event of a platform timeout where post creation status is ambiguous, the engine reconciles by querying the platform prior to attempting any republish, eliminating duplicate posts.
5. **Fail-Closed Certification & Continuous Verification**:
   No destination is promoted to active publishing status (`L3` / `L4`) without passing an automated end-to-end certification cycle (publish -> verify live -> read status -> delete -> store evidence). Any API contract drift or breaking field rename triggers immediate demotion to `L0`.

---

## 2. System Context & Container Architecture (C4 Model)

The following diagram illustrates the system boundaries, runtime containers, data stores, local test sandboxes, and external integration points.

```mermaid
graph TB
    subgraph Clients["Clients & Users"]
        WebUI["Web Dashboard<br/>(React + Vite + Tailwind)<br/>Port: 5173"]
        CLI["Batch Runner CLI<br/>(scripts/batch_runner.py)"]
        ExternalAPI["External API Consumer /<br/>Webhook Callback Client"]
    end

    subgraph IncuBrixApp["IncuBrix Distribution Engine (Containerized)"]
        subgraph APIGateway["IncuBrix Core API (FastAPI) - Port: 8000"]
            RouterV1["Application Router<br/>/api/v1/*<br/>(Jobs, Destinations, Rules, Certs)"]
            RouterConn["Connector Router<br/>/connector/v1/{connector_key}/{method}<br/>(Stateless Appendix A)"]
            HealthCheck["Health & Readiness<br/>/health & /ready"]
            Middleware["Middleware Pipeline<br/>(X-Correlation-Id, Idempotency, RateLimit)"]
        end

        subgraph CoreEngine["Business Logic & Rules Engine"]
            RulesEngine["Posting-Rules Engine<br/>(Frequency, Self-Promo, AI Tag)"]
            Tailoring["Tailoring Engine<br/>(Discussion hook, Canonical URL, Word limit)"]
            Recommender["Destination Recommender<br/>(Precision@10 evaluation)"]
            Certifier["Certification & Watchdog Engine<br/>(10-minute delete enforcement)"]
        end

        subgraph WorkerService["Asynchronous Worker Service"]
            Worker["Durable Worker Process<br/>(Redis queue / DB-backed polling)"]
            RecertScheduler["30-Day Recertification<br/>Cron Scheduler"]
        end

        subgraph ConnectorsModule["Connector Registry & Adapters"]
            BaseConn["BaseConnector Contract"]
            C_Discourse["Discourse Adapter"]
            C_Lemmy["Lemmy Adapter"]
            C_DevTo["Dev.to Adapter"]
            C_Ghost["Ghost Adapter (JWT)"]
            C_Webhook["Signed Webhook (HMAC)"]
            C_Assisted["Assisted Pack Builder"]
            C_Advanced["Advanced: Hashnode, Slack, MRSS"]
        end
    end

    subgraph DataStorage["Data & Storage Infrastructure"]
        Postgres[("PostgreSQL 16<br/>Durable State & Audit Logs<br/>Port: 5432")]
        RedisQueue[("Redis 7<br/>Queue, Caching, Token Buckets<br/>Port: 6379")]
        MinIOStorage[("MinIO (S3 API)<br/>Media, Artifacts, Evidence Packs<br/>Port: 9000")]
    end

    subgraph Sandboxes["Local Test Instances & Mock Platforms (Docker Compose)"]
        LemmyLocal["Local Lemmy Instance<br/>(Real Container)<br/>Port: 8536"]
        GhostLocal["Local Ghost Blog<br/>(Real Container)<br/>Port: 2368"]
        MockPlatforms["Mock Platforms Service<br/>(Discourse, Dev.to, Webhook Partner, Slack)<br/>Port: 8080"]
    end

    %% Client Interactions
    WebUI -->|HTTP / JSON| APIGateway
    CLI -->|HTTP / JSON| APIGateway
    ExternalAPI -->|HTTP / JSON| APIGateway

    %% API to Internal
    APIGateway --> Middleware
    Middleware --> RouterV1
    Middleware --> RouterConn
    RouterV1 --> CoreEngine
    RouterConn --> ConnectorsModule
    RouterV1 --> Postgres
    RouterV1 --> RedisQueue
    RouterV1 --> MinIOStorage

    %% Worker Interactions
    WorkerService --> CoreEngine
    WorkerService --> ConnectorsModule
    WorkerService --> Postgres
    WorkerService --> RedisQueue
    WorkerService --> MinIOStorage
    Worker -->|Signed Webhook Callbacks| ExternalAPI

    %% Connectors to Targets
    ConnectorsModule -->|REST API| LemmyLocal
    ConnectorsModule -->|Admin API / JWT| GhostLocal
    ConnectorsModule -->|REST / JSON| MockPlatforms
```

---

## 3. Sequence Diagrams

### 3.1 Publish Flow: End-to-End Orchestration
This sequence traces a content publication request from ingestion through tailoring, pre-flight rule validation, asynchronous worker execution, connector invocation, live status check, evidence capture, and manifest generation.

```mermaid
sequenceDiagram
    autonumber
    actor Creator as Client / Creator
    participant API as Core API (/api/v1/publish)
    participant Rules as Rules Engine
    participant DB as PostgreSQL
    participant Redis as Redis Queue
    participant Worker as Background Worker
    participant ConnRouter as /connector/v1/{key}/publish
    participant Platform as Destination Platform (e.g. Lemmy/Ghost/Mock)
    participant Storage as MinIO Storage

    Creator->>API: POST /api/v1/publish<br/>(content, destination_ids, Idempotency-Key)
    activate API
    API->>API: Validate Idempotency-Key & Check Lock

    loop For each destination
        API->>Rules: Evaluate Pre-flight Rules(destination, content)
        activate Rules
        Rules->>DB: Query Destination History (Frequency Cap, Past 7 Days)
        Rules-->>API: Rule Decision (ALLOW | BLOCK | RESCHEDULE)
        deactivate Rules
    end

    alt Rules Rejected or Cap Reached
        API->>DB: Record Rule Audit Failure
        API-->>Creator: 422 Unprocessable Entity or Rescheduled Notice<br/>{"error": {"code": "DEST_RULE_FREQUENCY_CAP"}}
    else Rules Passed
        API->>DB: Insert PublishJob & PublishRecords (Status: QUEUED)
        API->>Redis: Enqueue Job ID
        API-->>Creator: 202 Accepted {"job_id": "job_abc123", "status": "queued"}
    end
    deactivate API

    %% Background Processing
    Worker->>Redis: Dequeue Job ID
    activate Worker
    Worker->>DB: Update Job Status -> RUNNING
    
    loop For each destination record
        Worker->>Worker: Apply Content Tailoring (Format, Links, AI Tag)
        Worker->>ConnRouter: POST /connector/v1/{connector_key}/validate
        ConnRouter-->>Worker: {ok: true, violations: []}

        Worker->>ConnRouter: POST /connector/v1/{connector_key}/publish<br/>(rendition, destination, connection, idempotency_key)
        activate ConnRouter
        ConnRouter->>Platform: Outbound HTTP POST (Create Post)
        Platform-->>ConnRouter: 201 Created {id: "post_999", url: "http://..."}
        ConnRouter-->>Worker: {platform_post_id: "post_999", live_url: "...", status: "published"}
        deactivate ConnRouter

        %% Verify Status
        Worker->>ConnRouter: POST /connector/v1/{connector_key}/get_status
        ConnRouter->>Platform: Outbound HTTP GET (Verify Post Live)
        Platform-->>ConnRouter: 200 OK {status: "active"}
        ConnRouter-->>Worker: {status: "active", live_url: "..."}

        %% Generate Evidence & Manifest
        Worker->>Storage: Store Publish Evidence & Snapshots
        Storage-->>Worker: s3://incubrix-evidence/...
        Worker->>DB: Update PublishRecord (Status: SUCCEEDED, platform_post_id, live_url)
    end

    Worker->>Worker: Generate Output Manifest (Models, Versions, Timings, Rights)
    Worker->>DB: Update PublishJob (Status: SUCCEEDED, manifest_json)
    Worker->>Creator: Optional HMAC-SHA256 Signed Callback (X-IncuBrix-Signature)
    deactivate Worker
```

---

### 3.2 Idempotent Retry & Timeout Reconciliation
This sequence illustrates how the system handles a network timeout after a platform accepts a post, reconciling without creating a duplicate.

```mermaid
sequenceDiagram
    autonumber
    actor Client as Client / Worker Retry Loop
    participant Engine as Publish Orchestrator
    participant Conn as Connector Runtime
    participant Platform as Third-Party Platform
    participant DB as PostgreSQL

    Note over Client,Platform: Scenario: First attempt times out after platform accepts post
    Client->>Engine: Publish Request (Idempotency-Key: "idemp_555", Content Hash: "h_abc")
    activate Engine
    Engine->>DB: Check Idempotency Record (Key: "idemp_555")
    DB-->>Engine: Status: "in_progress", Attempt: 1

    Engine->>Conn: publish(rendition, destination, connection, "idemp_555")
    activate Conn
    Conn->>Platform: POST /posts (Create Post)
    activate Platform
    Note over Platform: Platform creates post (ID: 789)<br/>but HTTP connection drops
    Platform-->>Conn: [Network Timeout / Socket Closed]
    deactivate Platform
    Conn-->>Engine: Exception: RequestTimeoutException
    deactivate Conn

    Engine->>DB: Record Timeout, Set State -> "timeout_unreconciled"
    Engine-->>Client: 504 Gateway Timeout or Retry Triggered
    deactivate Engine

    %% Retry Phase
    Note over Client,Platform: Second attempt: Engine reconciles instead of blind re-posting
    Client->>Engine: Retry Publish (Same Idempotency-Key: "idemp_555")
    activate Engine
    Engine->>DB: Check Idempotency Record
    DB-->>Engine: State: "timeout_unreconciled"

    Note over Engine,Conn: Step 1: Reconcile before publishing
    Engine->>Conn: Query existing by Idempotency Tag / Fingerprint
    activate Conn
    Conn->>Platform: GET /posts?reference="idemp_555" (or query by slug/title)
    activate Platform
    Platform-->>Conn: 200 OK Found {id: 789, url: "http://dest/posts/789"}
    deactivate Platform
    Conn-->>Engine: {found: true, platform_post_id: "789", live_url: "..."}
    deactivate Conn

    alt Post Discovered on Platform
        Engine->>DB: Update Record -> SUCCEEDED (platform_post_id: "789", reconciled: true)
        Engine-->>Client: 200 OK {status: "succeeded", platform_post_id: "789", duplicate_prevented: true}
    else Post Not Found on Platform
        Engine->>Conn: publish(rendition, destination, connection, "idemp_555")
        Note over Engine: Safe to republish only after reconciliation confirms absence
    else State Indeterminable
        Engine->>DB: Mark Record -> NEEDS_REVIEW, Trigger Human Alert
        Engine-->>Client: 409 Conflict {"error": {"code": "PLATFORM_UNAVAILABLE", "retryable": false}}
    end
    deactivate Engine
```

---

### 3.3 Certification Run & Automated Demotion
This sequence illustrates the end-to-end certification lifecycle: validation, live test post, status confirmation, mandatory 10-minute deletion, evidence packaging, level assignment, and automated demotion when API drift occurs.

```mermaid
sequenceDiagram
    autonumber
    actor Admin as Certifier Scheduler / Admin
    participant CertEngine as Certification Engine
    participant Conn as Connector Runtime
    participant Platform as Platform / Sandbox
    participant MinIO as MinIO Storage
    participant DB as PostgreSQL
    participant Watchdog as 10-Minute Deletion Watchdog

    Admin->>CertEngine: Run Certification (destination_id: "dest_lemmy_1")
    activate CertEngine
    CertEngine->>DB: Create CertificationRun (Status: RUNNING, Step: PREREQUISITES)

    %% Step 1: Validate
    CertEngine->>Conn: validate(rendition, destination, connection)
    Conn-->>CertEngine: {ok: true, violations: []}
    CertEngine->>DB: Log Step: VALIDATE_SUCCESS

    %% Step 2: Publish Test Post
    CertEngine->>Conn: publish(test_rendition, destination, connection, cert_idemp_key)
    activate Conn
    Conn->>Platform: POST /api/v3/post (Create Test Post)
    Platform-->>Conn: 200 OK {post_view: {post: {id: 456, name: "Test Post"}}}
    Conn-->>CertEngine: {platform_post_id: "456", live_url: "http://lemmy/post/456", status: "published"}
    deactivate Conn
    CertEngine->>DB: Log Step: PUBLISH_SUCCESS (post_id: "456")
    CertEngine->>Watchdog: Register Deletion Deadline (post_id: "456", TTL: 600s)

    %% Step 3: Confirm Live & Get Status
    CertEngine->>Conn: get_status("456", connection)
    activate Conn
    Conn->>Platform: GET /api/v3/post?id=456
    Platform-->>Conn: 200 OK {status: "active"}
    Conn-->>CertEngine: {status: "active", live_url: "http://lemmy/post/456"}
    deactivate Conn
    CertEngine->>DB: Log Step: GET_STATUS_SUCCESS

    %% Step 4: Immediate Deletion
    CertEngine->>Conn: delete("456", connection)
    activate Conn
    Conn->>Platform: POST /api/v3/post/delete {post_id: 456, deleted: true}
    Platform-->>Conn: 200 OK {deleted: true}
    Conn-->>CertEngine: {deleted: true}
    deactivate Conn
    CertEngine->>DB: Log Step: DELETE_SUCCESS
    CertEngine->>Watchdog: Cancel Deletion Deadline (post_id: "456")

    %% Step 5: Store Evidence Pack & Update Level
    CertEngine->>MinIO: Upload Evidence Pack (HTTP logs, payloads, timestamps)
    MinIO-->>CertEngine: s3://incubrix-evidence/cert_lemmy_1.json
    CertEngine->>DB: Update Destination (level: L3, last_certified_at: now())
    CertEngine->>DB: Update CertificationRun (Status: SUCCEEDED)
    CertEngine-->>Admin: Certification Passed (Level L3 Granted)
    deactivate CertEngine

    %% Alternative: API Drift / Renamed Field Scenario
    Note over Admin,DB: Failure Scenario: Platform renames API field
    Admin->>CertEngine: Run Recertification (destination_id: "dest_broken")
    activate CertEngine
    CertEngine->>Conn: publish(test_rendition, ...)
    Conn->>Platform: POST /api/v1/posts
    Platform-->>Conn: 200 OK {"renamed_identifier": "post_777"}
    Note over Conn: Pydantic Validation Error:<br/>Missing required field 'id'
    Conn-->>CertEngine: Exception: SchemaViolationException
    CertEngine->>DB: Update Destination (level: L0, status: DEGRADED)
    CertEngine->>DB: Insert Alert Ticket (Reason: "API Schema Drift: Missing id")
    CertEngine->>MinIO: Store Failure Evidence
    CertEngine-->>Admin: Certification Failed -> Demoted to L0
    deactivate CertEngine
```

---

## 4. State Diagrams

### 4.1 Job State Machine
Represents the lifecycle of asynchronous publishing operations managed by the job engine.

```mermaid
stateDiagram-v2
    [*] --> QUEUED: Client initiates publish (202 Accepted)
    QUEUED --> RUNNING: Worker dequeues job
    
    RUNNING --> PRE_FLIGHT_CHECK: Evaluate destination rules
    PRE_FLIGHT_CHECK --> RESCHEDULED: Frequency cap reached (wait window)
    RESCHEDULED --> QUEUED: Scheduled window expires
    PRE_FLIGHT_CHECK --> FAILED: Hard rule violation (self-promo/banned)

    RUNNING --> EXECUTING_CONNECTOR: Rules passed, calling connector
    EXECUTING_CONNECTOR --> TIMEOUT_DETECTED: Socket timeout / platform lag
    TIMEOUT_DETECTED --> RECONCILING: Idempotency recovery check
    
    RECONCILING --> SUCCEEDED: Post discovered on target platform
    RECONCILING --> NEEDS_REVIEW: Ambiguous status / human alert
    
    EXECUTING_CONNECTOR --> SUCCEEDED: Publish & live verification confirmed
    EXECUTING_CONNECTOR --> FAILED: Platform rejects content (422) or fatal error
    EXECUTING_CONNECTOR --> RETRY_DELAY: Platform 429 / 5xx (backoff active)
    RETRY_DELAY --> QUEUED: Backoff timer elapses (<5 attempts)
    RETRY_DELAY --> FAILED: Max retry limit reached (>=5 failures)

    SUCCEEDED --> [*]
    FAILED --> [*]
    NEEDS_REVIEW --> [*]
```

---

### 4.2 Destination Level Transitions (L0–L4)
Represents the trust and capability maturity levels defined in Appendix A and Page 9 of the specification.

```mermaid
stateDiagram-v2
    [*] --> L0_Catalogued: Destination imported / created

    state L0_Catalogued {
        [*] --> Inactive: Uncertified
        Inactive --> ReachabilityChecked: Verified URL & Schema
    }

    L0_Catalogued --> L1_Assisted: Flagged as automation_allowed=false
    L0_Catalogued --> L2_Bridged: Configured as RSS / MRSS / Webhook
    L0_Catalogued --> L3_Native: Passes full Certification Harness<br/>(validate, publish, status, delete)

    L3_Native --> L4_Native_Metrics: Passes fetch_metrics certification<br/>(views, likes, comments, clicks)
    L4_Native_Metrics --> L3_Native: Metrics endpoint fails / uninstalled

    %% Demotion transitions
    L3_Native --> L0_Catalogued: Certification fails / API field rename / Auth expired
    L4_Native_Metrics --> L0_Catalogued: Certification fails / Token revoked / Hard error
    L2_Bridged --> L0_Catalogued: Feed endpoint dead / Webhook secret revoked
    L1_Assisted --> L0_Catalogued: Destination deactivated / Rules changed

    note right of L0_Catalogued
        L0 destinations are strictly excluded
        from automated publishing and
        recommender ranking.
    end note
```

---

## 5. Entity-Relationship (ER) Diagram

The relational data model implemented in PostgreSQL via SQLAlchemy 2 and managed with Alembic.

```mermaid
erDiagram
    DESTINATION {
        uuid id PK
        string name
        string url
        string platform_key
        string surface
        string category
        jsonb audience_tags
        string language
        string geo
        int est_audience
        string rules_url
        int frequency_cap
        boolean self_promo_allowed
        string link_policy
        boolean disclosure_required
        boolean automation_allowed
        string connector_key
        int relevance_score
        text relevance_reason
        string level
        timestamp last_certified_at
        timestamp created_at
        timestamp updated_at
    }

    CONNECTION {
        uuid id PK
        uuid destination_id FK
        string auth_type
        text encrypted_credentials
        string base_url
        timestamp expires_at
        string status
        timestamp created_at
        timestamp updated_at
    }

    CONNECTOR_MANIFEST {
        string key PK
        string version
        string tier
        string auth_type
        jsonb surfaces
        jsonb rate_limits
        jsonb capabilities
        jsonb error_map
        string instance_param
        boolean is_active
        timestamp loaded_at
    }

    POSTING_RULE {
        uuid id PK
        uuid destination_id FK
        string rule_type
        jsonb parameters
        boolean is_enforced
        boolean is_human_confirmed
        timestamp created_at
    }

    RULE_DECISION_AUDIT {
        uuid id PK
        uuid job_id FK
        uuid destination_id FK
        string decision
        string rule_violated
        text rationale
        timestamp next_allowed_at
        boolean human_action_required
        timestamp evaluated_at
    }

    PUBLISH_JOB {
        uuid id PK
        string idempotency_key UK
        string status
        int progress
        string callback_url
        string correlation_id
        jsonb manifest_json
        text error_message
        timestamp created_at
        timestamp updated_at
    }

    PUBLISH_RECORD {
        uuid id PK
        uuid job_id FK
        uuid destination_id FK
        string status
        string platform_post_id
        string live_url
        jsonb tailored_rendition
        string evidence_s3_url
        int retry_count
        timestamp published_at
        timestamp verified_at
        timestamp deleted_at
    }

    CERTIFICATION_RUN {
        uuid id PK
        uuid destination_id FK
        string connector_key
        boolean is_mock
        string status
        string target_level
        string assigned_level
        jsonb step_results
        string evidence_s3_url
        timestamp started_at
        timestamp completed_at
    }

    DELETION_WATCHDOG {
        uuid id PK
        uuid certification_run_id FK
        string platform_post_id
        uuid destination_id FK
        timestamp expires_at
        boolean is_deleted
        timestamp deleted_at
        int attempt_count
    }

    METRICS_SNAPSHOT {
        uuid id PK
        uuid destination_id FK
        string platform_post_id
        bigint views
        bigint likes
        bigint comments
        bigint shares
        bigint saves
        bigint watch_time_s
        bigint clicks
        timestamp recorded_at
    }

    DESTINATION ||--o{ CONNECTION : "has"
    DESTINATION ||--o{ POSTING_RULE : "governed by"
    DESTINATION ||--o{ PUBLISH_RECORD : "receives"
    DESTINATION ||--o{ CERTIFICATION_RUN : "undergoes"
    DESTINATION ||--o{ METRICS_SNAPSHOT : "tracks"
    PUBLISH_JOB ||--o{ PUBLISH_RECORD : "contains"
    PUBLISH_JOB ||--o{ RULE_DECISION_AUDIT : "generates"
    CERTIFICATION_RUN ||--o{ DELETION_WATCHDOG : "monitored by"
```

---

## 6. Security, Secrets Protection & Error Handling Architecture

### 6.1 Secrets Protection & Redaction Pipeline
1. **Zero Secret Persistence in Repos**:
   All tokens, API keys, and webhook signing secrets are injected purely via environment variables or loaded encrypted into PostgreSQL.
2. **Streaming Log Redaction**:
   The custom JSON logging formatter intercepts log records and matches against compiled regex patterns for API keys, bearer tokens, JWT signatures, and hex secrets (`Bearer [A-Za-z0-9_\-\.]+`, `Api-Key [A-Za-z0-9]+`, `whsec_[A-Za-z0-9]+`), replacing them with `[REDACTED]` prior to emission.
3. **Signed Webhooks & Signature Verification**:
   - Outbound partner webhooks are signed using HMAC-SHA256 (`X-IncuBrix-Signature`) calculated over `timestamp + "." + raw_body`, protecting against replay attacks via a 5-minute timestamp validity window.
   - Background job callback payloads use identical cryptographic signing.

### 6.2 Standardized Error Architecture
Every error across `/api/v1/` and `/connector/v1/` returns HTTP status codes mapped to the standardized error schema:

```json
{
  "error": {
    "code": "PLATFORM_RATE_LIMIT",
    "message": "Target community rate limit reached. Reset in 320 seconds.",
    "retryable": true,
    "details": {
      "reset_epoch": 1776543200,
      "retry_after_seconds": 320,
      "destination_id": "8a72b14e-0c9f-431e-b81b-53c842b10a22"
    }
  }
}
```

The error mapping engine enforces the following translation matrix across all connectors:
- HTTP 400 -> `DEST_SPEC_VIOLATION` (Retry: No)
- HTTP 401 / 403 -> `CONNECTION_AUTH_EXPIRED` (Retry: After Reconnect)
- HTTP 422 -> `PLATFORM_CONTENT_REJECTED` (Retry: No)
- HTTP 429 -> `PLATFORM_RATE_LIMIT` (Retry: Yes, after backoff)
- HTTP 500 / 502 / 503 / 504 -> `PLATFORM_UNAVAILABLE` (Retry: Yes, max 5 consecutive)
- Disabled Flag -> `CONNECTOR_DISABLED` (Retry: No)

---

## 7. Architecture Verification Summary
All sequence flows, state machines, and relational schemas directly fulfill the IncuBrix Assessment 4 brief and master prompt rules. The engine prioritizes reliability, rules verification, and idempotent recovery over cosmetic features.
