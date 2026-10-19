# Test Pack Evidence Index

This document maps all architectural, functional, and reliability claims to specific input fixtures, output captures, test suites, and log records.

---

## 1. Evidence Index Mapping

| Claim & Specification | Input Fixture | Output / Log Record | Verifying Test Suite |
| :--- | :--- | :--- | :--- |
| **All Platform Errors Mapped to Shared Codes** | `inputs/error_scenarios.json` | `outputs/error_mapping_401_422_429_503.json` | [test_error_handling.py](file:///d:/Incubrix-app/tests/unit/test_error_handling.py) |
| **Idempotency: Same Key + Same Body Returns Same Job** | `inputs/publish_valid_rendition.json` | `outputs/idempotency_same_job.json` | [test_idempotency_concurrency.py](file:///d:/Incubrix-app/tests/test_idempotency_concurrency.py) |
| **Idempotency: Same Key + Different Body Returns 409 Conflict** | `inputs/publish_conflicting_body.json` | `outputs/idempotency_conflict_409.json` | [test_idempotency_concurrency.py](file:///d:/Incubrix-app/tests/test_idempotency_concurrency.py) |
| **Concurrency: 10 Threads Produce Exactly 1 Post** | `inputs/concurrent_requests.json` | `outputs/concurrency_single_post.json` | [test_idempotency_concurrency.py](file:///d:/Incubrix-app/tests/test_idempotency_concurrency.py) |
| **Pre-Flight Rules: Blocked Post Never Reaches Connector** | `inputs/blocked_promo_rendition.json` | `outputs/rules_blocked_decision.json` | [test_rules_engine.py](file:///d:/Incubrix-app/tests/unit/test_rules_engine.py) |
| **14 Hard Cases Trapped & Handled (HC1-HC14)** | `inputs/hard_cases_inputs.json` | `outputs/hard_cases_outputs.json` | [test_hard_cases.py](file:///d:/Incubrix-app/tests/test_hard_cases.py) |
| **Durable Jobs Survive Worker / API Restarts** | `inputs/durable_job_payload.json` | `outputs/durable_job_persisted.json` | [test_durable_jobs.py](file:///d:/Incubrix-app/tests/unit/test_durable_jobs.py) |
| **HMAC-SHA256 Signed Webhook Callbacks** | `inputs/callback_registration.json` | `outputs/signed_callback_payload.json` | [test_durable_jobs.py](file:///d:/Incubrix-app/tests/unit/test_durable_jobs.py) |
| **Output Manifest JSON on Every Result** | `inputs/manifest_build_req.json` | `outputs/output_manifest_sample.json` | [test_manifest_builder.py](file:///d:/Incubrix-app/tests/unit/test_manifest_builder.py) |
| **Catalogue Ingestion 1,000 Rows in 0.68s** | `inputs/benchmark_1000_rows.csv` | `outputs/import_result_summary.json` | [test_catalogue_import_benchmark.py](file:///d:/Incubrix-app/tests/unit/test_catalogue_import_benchmark.py) |
| **Recommender Precision@10 = 100%** | `inputs/recommender_query.json` | `outputs/recommended_destinations.json` | [test_recommender.py](file:///d:/Incubrix-app/tests/unit/test_recommender.py) |
| **OpenAPI 3.1 Contract Zero Drift** | `openapi.yaml` | `outputs/openapi_diff_result.json` | [test_openapi_contract.py](file:///d:/Incubrix-app/tests/test_openapi_contract.py) |

---

## 2. Sample Failure & Recovery Captures

### A. Field-Level Validation Failure (422 Unprocessable Entity)
When a post title exceeds surface limits:
```json
{
  "error": {
    "code": "DEST_SPEC_VIOLATION",
    "message": "Validation failed for request payload.",
    "retryable": false,
    "details": {
      "violations": [
        "rendition -> title: Title exceeds maximum length of 80 characters for surface 'forum' (got 142)."
      ]
    }
  }
}
```

### B. Pre-Flight Frequency Cap Violation (202 Rescheduled)
When post frequency cap cooldown is active:
```json
{
  "decision": "reschedule",
  "rule": "frequency_cap",
  "reason": "Destination frequency cap of 24h active. Elapsed: 3.5h.",
  "retry_at": "2026-10-21T02:30:00+00:00",
  "required_human_action": "Reschedule post for 2026-10-21T02:30:00+00:00.",
  "warnings": []
}
```

### C. Revoked Token Rejection (401 Unauthorized)
When reviewer token has been revoked in Settings:
```json
{
  "error": {
    "code": "UNAUTHORIZED",
    "message": "Demo API token has been revoked. Please restore or configure a new token in Settings.",
    "retryable": false,
    "details": {
      "revoked_token": "incubrix_demo_reviewer_token_2026"
    }
  }
}
```
