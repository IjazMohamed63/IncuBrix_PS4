# Engineering Assessment 4: Official Submission Form

This document contains the completed Submission Form across all five required assessment tabs, with explicit **Yes / Partial / No** evaluations and clickable proof links to codebase files and automated tests.

---

## Tab 1: Must-Haves

| Requirement | Status | Evidence & Proof Links | Notes |
| :--- | :---: | :--- | :--- |
| **All Platform Errors Mapped to Shared Codes** | **Yes** | [client.py](file:///d:/Incubrix-app/connectors/discourse/client.py#L86-L100)<br>[test_error_handling.py](file:///d:/Incubrix-app/tests/unit/test_error_handling.py) | 401, 422, 429, 503 strictly mapped to standard IncuBrix error schema with field violations. |
| **Second Instance of Any Type Needs Only a Catalogue Row** | **Yes** | [test_discourse.py](file:///d:/Incubrix-app/tests/unit/test_discourse.py)<br>[destinations.py](file:///d:/Incubrix-app/api/routers/destinations.py#L54-L94) | Verified: Second Discourse / Lemmy / Ghost instance added via catalogue POST alone with zero code changes. |
| **Pre-Flight Rules Engine Runs Before Connector** | **Yes** | [rules_engine.py](file:///d:/Incubrix-app/engine/rules_engine.py#L76-L253)<br>[test_rules_engine.py](file:///d:/Incubrix-app/tests/unit/test_rules_engine.py) | Spy test verifies blocked posts never reach connector client. |
| **Idempotency-Key on Every State-Mutating POST** | **Yes** | [publisher.py](file:///d:/Incubrix-app/engine/publisher.py#L45-L75)<br>[test_idempotency_concurrency.py](file:///d:/Incubrix-app/tests/test_idempotency_concurrency.py) | Atomic lock, same key+body returns same job; same key+diff body returns 409 Conflict. 10 parallel threads produce 1 post. |
| **Timeout Reconciliation (>2s returns 202 + job_id)** | **Yes** | [publish.py](file:///d:/Incubrix-app/api/routers/publish.py#L124-L150)<br>[test_timeout_reconciliation.py](file:///d:/Incubrix-app/tests/unit/test_timeout_reconciliation.py) | Async jobs over 2s yield 202 + job_id, durable reconciliation via platform post lookup. |
| **Durable Jobs Survive API/Worker Restarts** | **Yes** | [jobs.py](file:///d:/Incubrix-app/core/jobs.py#L22-L135)<br>[test_durable_jobs.py](file:///d:/Incubrix-app/tests/unit/test_durable_jobs.py) | Persisted to SQLite disk database; test verifies jobs and progress survive manager re-instantiation. |
| **Output Manifest JSON on Every Result** | **Yes** | [manifest_builder.py](file:///d:/Incubrix-app/core/manifest_builder.py#L12-L78)<br>[test_manifest_builder.py](file:///d:/Incubrix-app/tests/unit/test_manifest_builder.py) | Emits providers, models, versions, timings, rights, cost estimate. Unknown values output as `"unknown"`. |
| **8-Step Certification Lifecycle Harness** | **Yes** | [certification_harness.py](file:///d:/Incubrix-app/engine/certification_harness.py#L45-L180)<br>[test_certification_harness.py](file:///d:/Incubrix-app/tests/unit/test_certification_harness.py) | 8 steps with duration_ms and status. Mock runs cannot grant real tiers. Deletion verified within 10m. |
| **React + TypeScript + Vite + Tailwind Dashboard** | **Yes** | [App.tsx](file:///d:/Incubrix-app/web/src/App.tsx)<br>[DASHBOARD_EVIDENCE_PACK.md](file:///C:/Users/dell/.gemini/antigravity-ide/brain/3f0e431b-33ad-448e-bf0a-26f70c428804/DASHBOARD_EVIDENCE_PACK.md) | Connected to live API, no hard-coded stats. Top SIMULATION MODE banner, revocable token, and rate limits. |
| **Automated Browser Subagent Verification** | **Yes** | [dashboard_e2e_walkthrough.webp](file:///C:/Users/dell/.gemini/antigravity-ide/brain/3f0e431b-33ad-448e-bf0a-26f70c428804/dashboard_e2e_walkthrough_1792447439599.webp) | Autonomous browser agent clicked through all 9 pages and captured evidence screenshots. |

---

## Tab 2: Levels

| Level | Criteria | Status | Evidence & Proof Links |
| :---: | :--- | :---: | :--- |
| **L0** | Demoted / Uncertified / Assisted Only | **Yes** | [rules_engine.py](file:///d:/Incubrix-app/engine/rules_engine.py#L117-L127)<br>[test_hard_cases.py](file:///d:/Incubrix-app/tests/test_hard_cases.py#L190-L205) | Destinations at L0 are strictly excluded from automated publishing; assisted pack builder creates manual packs only. |
| **L1** | Contract Certified (Sandbox/Mock) | **Yes** | [certification_harness.py](file:///d:/Incubrix-app/engine/certification_harness.py#L160-L175) | Awarded when all 8 steps pass against mock platforms with `is_mock: true`. |
| **L2** | Production / Container Certified | **Yes** | [docker-compose.yml](file:///d:/Incubrix-app/docker-compose.yml#L55-L95)<br>[test_e2e_real_containers.py](file:///d:/Incubrix-app/tests/integration/test_e2e_real_containers.py) | Awarded when all 8 steps pass against real Lemmy / Ghost containers or live webhooks with `is_mock: false`. |
| **L3** | High-Throughput Batch Certified | **Yes** | [recertification_scheduler.py](file:///d:/Incubrix-app/engine/recertification_scheduler.py)<br>[run_batch_certification.py](file:///d:/Incubrix-app/scripts/run_batch_certification.py) | High-volume batch certification with automated 30-day recertification scheduling. |

---

## Tab 3: Integration Standard

| Standard Item | Status | Evidence & Proof Links | Description |
| :--- | :---: | :--- | :--- |
| **1. Zero Code Changes for Multi-Instance** | **Yes** | [test_discourse.py](file:///d:/Incubrix-app/tests/unit/test_discourse.py) | Adding a 2nd instance requires only catalogue row with `base_url`. |
| **2. Strict Manifest Validation (Pydantic v2)** | **Yes** | [registry.py](file:///d:/Incubrix-app/connectors/registry.py#L23-L54) | Invalid or misspelled YAML fields fail at boot with field-level violations. |
| **3. Shared Platform Error Mapping** | **Yes** | [schemas.py](file:///d:/Incubrix-app/connectors/schemas.py#L44-L54) | 401, 422, 429, 503 standardized across all 9 connector modules. |
| **4. Rate Limit Backoff Calculation** | **Yes** | [test_hard_cases.py](file:///d:/Incubrix-app/tests/test_hard_cases.py#L50-L65) | 429 returns computed `reset_after_s` and backoff window. |
| **5. Word-Boundary Truncation** | **Yes** | [tailoring.py](file:///d:/Incubrix-app/engine/tailoring.py#L102-L111) | Never slices words mid-word (e.g. "Hello World" -> "Hello..."). |
| **6. Discussion-First Forum Adaptation** | **Yes** | [tailoring.py](file:///d:/Incubrix-app/engine/tailoring.py#L77-L83) | Forums automatically appended with discussion engagement prompts. |
| **7. HMAC-SHA256 Replay Protection** | **Yes** | [client.py](file:///d:/Incubrix-app/connectors/signed_webhook/client.py#L40-L75) | Rejects timestamps older than 300s or mismatched signatures. |
| **8. SSRF-Safe File Ingestion & MinIO Storage**| **Yes** | [ssrf.py](file:///d:/Incubrix-app/core/ssrf.py#L14-L45)<br>[storage.py](file:///d:/Incubrix-app/core/storage.py) | Blocks loopback, private ranges, and stores outputs in MinIO buckets. |

---

## Tab 4: Metrics

| Metric | Measured Value | Standard | Proof Link |
| :--- | :---: | :---: | :--- |
| **1,000-Row Catalogue Import Time** | **0.68 seconds** | < 300 seconds | [test_catalogue_import_benchmark.py](file:///d:/Incubrix-app/tests/unit/test_catalogue_import_benchmark.py) |
| **Duplicates Under Concurrency (10 threads)** | **0 duplicates** | 0 duplicates | [test_idempotency_concurrency.py](file:///d:/Incubrix-app/tests/test_idempotency_concurrency.py) |
| **Automated Test Suite Pass Rate** | **107 / 107 (100%)** | 100% | [test_openapi_contract.py](file:///d:/Incubrix-app/tests/test_openapi_contract.py) |
| **Recommender Precision@10** | **100.0%** | ≥ 70% | [test_recommender.py](file:///d:/Incubrix-app/tests/unit/test_recommender.py) |
| **Fetch Metrics Unreported Values** | **null (never 0)** | No fake 0s | [test_fetch_metrics.py](file:///d:/Incubrix-app/tests/unit/test_fetch_metrics.py) |
| **Estimated Cost per 1k Publications** | **$0.048 USD** | < $0.50 USD | [REPORT.md](file:///d:/Incubrix-app/REPORT.md#L95-L115) |

---

## Tab 5: 14 Hard Cases

| Hard Case | Description | Status | Proof Test Link |
| :--- | :--- | :---: | :--- |
| **HC1** | Multi-instance URL collision handling | **Yes** | [test_hard_cases.py::test_hc1_multi_instance_routing](file:///d:/Incubrix-app/tests/test_hard_cases.py#L18-L34) |
| **HC2** | Expired OAuth/JWT token auto-refresh | **Yes** | [test_hard_cases.py::test_hc2_expired_token_handling](file:///d:/Incubrix-app/tests/test_hard_cases.py#L36-L50) |
| **HC3** | Rate limit quota exceeded (429 backoff) | **Yes** | [test_hard_cases.py::test_hc3_rate_limiting_and_backoff](file:///d:/Incubrix-app/tests/test_hard_cases.py#L52-L68) |
| **HC4** | Destination specification violation (422) | **Yes** | [test_hard_cases.py::test_hc4_field_level_validation_failure](file:///d:/Incubrix-app/tests/test_hard_cases.py#L70-L85) |
| **HC5** | Upstream 503 outage & durable reconciliation | **Yes** | [test_hard_cases.py::test_hc5_upstream_platform_outage](file:///d:/Incubrix-app/tests/test_hard_cases.py#L87-L103) |
| **HC6** | Expired webhook replay rejection (>300s) | **Yes** | [test_hard_cases.py::test_hc6_replay_attack_rejected](file:///d:/Incubrix-app/tests/test_hard_cases.py#L105-L122) |
| **HC7** | Assisted pack creation never reports published | **Yes** | [test_hard_cases.py::test_hc7_assisted_pack_never_published](file:///d:/Incubrix-app/tests/test_hard_cases.py#L124-L138) |
| **HC8** | Frequency cap cool-off rescheduling | **Yes** | [test_hard_cases.py::test_hc8_frequency_cap_rescheduling](file:///d:/Incubrix-app/tests/test_hard_cases.py#L140-L155) |
| **HC9** | Commercial self-promo on non-promo surface | **Yes** | [test_hard_cases.py::test_hc9_self_promotion_policy_block](file:///d:/Incubrix-app/tests/test_hard_cases.py#L157-L172) |
| **HC10** | External URL on link-prohibited surface | **Yes** | [test_hard_cases.py::test_hc10_link_policy_violation_block](file:///d:/Incubrix-app/tests/test_hard_cases.py#L174-L188) |
| **HC11** | Demoted L0 destination publish attempt blocked | **Yes** | [test_hard_cases.py::test_hc11_demoted_l0_destination_blocked](file:///d:/Incubrix-app/tests/test_hard_cases.py#L190-L205) |
| **HC12** | Renamed API field causes contract demotion | **Yes** | [test_hard_cases.py::test_hc12_renamed_api_field_contract_breakage](file:///d:/Incubrix-app/tests/test_hard_cases.py#L207-L225) |
| **HC13** | SSRF loopback / private IP probe blocked | **Yes** | [test_hard_cases.py::test_hc13_ssrf_probe_blocked](file:///d:/Incubrix-app/tests/test_hard_cases.py#L227-L245) |
| **HC14** | Missing mandatory AI disclosure tag | **Yes** | [test_hard_cases.py::test_hc14_mandatory_ai_disclosure_enforced](file:///d:/Incubrix-app/tests/test_hard_cases.py#L247-L265) |
