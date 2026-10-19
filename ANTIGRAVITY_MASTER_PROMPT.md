# ANTIGRAVITY MASTER PROMPT: IncuBrix Long-Tail Distribution Network

> How to use: create an empty workspace folder `incubrix-distribution/`. Copy the PDF in as `docs/brief/IncuBrix_Assessment4.pdf` and the form screenshot as `docs/brief/submission_form.png`. Add `docs/brief/` to `.gitignore` (the brief is confidential and must not be published). Open Agent Manager, set mode to Planning, and paste PROMPT 0 first. Paste each later prompt only after you have reviewed and approved the previous phase's artifacts.
> `@` references below point to workspace files and context. If your Antigravity build uses a different mention syntax for MCP servers or tools, keep the intent and adapt the symbol.

---

## PROMPT 0: SYSTEM CONTEXT (paste first, keep pinned)

You are a principal architect and senior full-stack engineer building the **IncuBrix Long-Tail Distribution Network** for Engineering Assessment 4.

Sources of truth, in priority order:
1. @docs/brief/IncuBrix_Assessment4.pdf (every page, including Appendix A)
2. @docs/brief/submission_form.png (final submission checklist)
3. This prompt

Non-negotiable rules:
- Engine first, UI second. The brief says a simple web page or the API docs page is enough; the scoring is on the engine, integration and results. Do not polish the UI before the contract, rules, retries and certification work.
- Honesty over polish. Never claim a connector is certified, a test passed, or a deployment works without evidence from an actual run. Mock results are labelled `mock`, never `real`. Mark unknowns as `unknown`. A false claim disqualifies the submission.
- Never commit secrets or the confidential PDF. `.env.example` has placeholders only.
- Everything must run with no external API keys (simulation mode).
- Commercial-use licences only. No AGPL code in the shipped service. Record every dependency in `SOURCES.md`, and every AI tool use in `AI_USE.md`.
- I must be able to explain and modify all code in a live session. Prefer simple, readable code over clever abstractions.
- Make small commits with meaningful messages throughout. No single giant commit.
- After each phase: summarize what was built, which tests pass, what remains, and the exact command to verify.

Known spec details to respect exactly (do not "improve" them):
- Connector contract: `POST /connector/v1/{connector_key}/{method}`, JSON bodies. Methods: `validate`, `publish`, `get_status`, `delete`, `fetch_metrics` (optional), `refresh_auth` (optional), `build_assist_pack` (assisted tier only). Connectors return results only and never touch the database.
- All other routes live under `/api/v1/`. The `/connector/v1/` path is the one documented exception, plus `/health` and `/ready`.
- Shared error codes: `DEST_SPEC_VIOLATION`, `DEST_RULE_FREQUENCY_CAP`, `CONNECTION_AUTH_EXPIRED`, `PLATFORM_RATE_LIMIT`, `PLATFORM_QUOTA_EXHAUSTED`, `PLATFORM_CONTENT_REJECTED`, `PLATFORM_UNAVAILABLE` (stop after 5 consecutive failures), `CONNECTOR_DISABLED`. Error body: `{"error":{"code","message","retryable","details"}}`.
- Manifest YAML per connector: key, version, tier (native|protocol|bridge|feed|assisted), auth (oauth2|api_key|bot_token|none), surfaces, rate_limits, capabilities, error_map, instance_param.
- Destination record fields: name, url, platform_key, surface, category, audience_tags, language, geo, est_audience, rules_url, frequency_cap, self_promo_allowed, link_policy, disclosure_required, automation_allowed, connector_key, relevance_score (1-5), relevance_reason, level (L0-L4), last_certified_at.
- Test posts go only to my own local instances or sandboxes and are deleted within 10 minutes. No scraping where disallowed. Back off on 429 using the reset time.
- Audience for relevance: AI, video, marketing, SaaS, creators, founders.

Acknowledge these rules in 5 lines, then wait for PROMPT 1.

---

## PROMPT 1: ANALYSIS AND ARCHITECTURE (no application code yet)

Read @docs/brief/IncuBrix_Assessment4.pdf fully and @docs/brief/submission_form.png. Then produce these artifacts for my review:

1. `docs/REQUIREMENTS_ANALYSIS.md`
   - Problem in your own words, in/out of scope.
   - The 9 must-haves, Core/Advanced/Outstanding items, 10 Integration Standard points, 14 hard cases, deliverables.
   - Traceability matrix: Requirement ID | Requirement | Implementation | Test | Evidence | Status (all `Pending`).
   - Ambiguities and the conservative choice you make for each. Include at least: the `/connector/v1/` vs `/api/v1/` routing rule, how "delete within 10 minutes" is enforced, what "agreed sandbox" means for Discourse and Dev.to, how Discourse is tested locally, and the level (L0-L4) assignment rules.
   - The three highest failure risks and mitigations.

2. `docs/ARCHITECTURE.md` with **Mermaid diagrams** (render-check them):
   - C4-style system context and container diagram: Web UI, API (FastAPI), Worker, Postgres, Redis, MinIO, local Lemmy, local Ghost, mock-platforms service (Discourse, Dev.to, signed-webhook partner, Slack/Hashnode/etc.).
   - Sequence diagram: publish flow (content, tailoring, rules engine, connector validate, job, connector publish, status check, evidence, manifest).
   - Sequence diagram: idempotent retry after a timeout-after-accept (reconcile instead of re-publish).
   - Sequence diagram: certification run (validate, publish, confirm live, get_status, delete, evidence, level update, demotion on failure).
   - State diagrams: job states (queued, running, succeeded, failed) and destination level transitions.
   - ER diagram of the database.

3. `docs/IMPLEMENTATION_PLAN.md`: stack with exact versions (Python 3.11+, FastAPI, Pydantic v2, SQLAlchemy 2, Alembic, Postgres, httpx, pytest; React + TypeScript + Vite + Tailwind; Redis worker or DB-backed durable queue), repo structure, API route plan, milestone list with acceptance criteria, and risk register.

Do not write application code. Stop and ask me to approve the architecture diagram and plan.

---

## PROMPT 2: FOUNDATION AND CONNECTOR CONTRACT (Day 1-2)

Implement per the approved @docs/ARCHITECTURE.md and @docs/IMPLEMENTATION_PLAN.md:

1. Repo scaffold, `docker-compose.yml` (api, worker, postgres, redis, minio, mock-platforms), `.env.example`, `.gitignore`, Alembic baseline, structured JSON logging with `X-Correlation-Id` propagation, `GET /health` and `GET /ready` (ready checks DB, storage, queue).
2. Manifest loader and validator run at startup; reject invalid manifests with a clear error.
3. Connector registry and the exact `POST /connector/v1/{connector_key}/{method}` router with Pydantic schemas matching Appendix A.
4. Shared error codes, error-map normalization, and a global exception handler producing the standard error body. Respect `CONNECTOR_DISABLED` kill switch.
5. Contract tests that run against every connector method and schema. Write them before the connectors.

Done when: `docker compose up` is healthy and `pytest tests/contract` passes against a stub connector. Report results.

---

## PROMPT 3: SIX CORE CONNECTORS (Day 3-4)

Using the registry from Prompt 2, implement six independent modules under `connectors/`, each with `manifest.yaml`, implementation, config example, unit, contract and certification tests:

1. `discourse` (multi-instance via `base_url`; mock Discourse server in mock-platforms)
2. `lemmy` (multi-instance; **real local Lemmy container** in compose)
3. `devto` (mock server; never label mock as real)
4. `ghost` (multi-instance; **real local Ghost container** in compose, Admin API with JWT)
5. `signed_webhook` (HMAC-SHA256, timestamp plus replay protection, partner mock verifies signature, secrets never logged)
6. `assisted` (`build_assist_pack` only: files, caption, deep_link, checklist; package creation is never reported as "published")

Requirements: all platform errors mapped to shared codes (401 expired token, 429 with reset time, 422 rejected, 5xx unavailable); validation returns field-level violations; adding a second instance of any type must need only a catalogue row. Prove it with a test that adds a new Discourse destination via the API and publishes to it with zero code changes.

Done when: all six pass contract tests and each publishes, reads status and deletes against its local or mock target. Show the output.

---

## PROMPT 4: RULES, RELIABILITY, SIMULATION (Day 5)

1. **Rules engine** (runs before every publish): frequency cap with computed next-allowed time, self-promotion policy, link policy, AI-disclosure requirement, format limits, content type, automation permission, connector/certification eligibility. Output a structured decision (allow|block|reschedule, rule, reason, retry_at, required_human_action, warnings) and store an audit record. A blocked post must provably never reach the connector (test with a spy).
2. **Idempotency**: `Idempotency-Key` on every POST that does work. Persisted records, atomic insert/lock, same key + same body returns the same job, same key + different body returns a conflict error. Concurrency test with parallel requests must create exactly one job and one post.
3. **Timeout reconciliation**: if a publish times out after the platform accepted it, do not re-publish. Reconcile via a platform request id or lookup; if undeterminable, mark `needs_review` and surface it.
4. **Rate limiting and backoff**: per-connector and per-destination. On 429 parse reset time, persist the block until then, make no calls during the window. Circuit-break after 5 consecutive failures.
5. **Simulation mode**: all mock platforms support scripted scenarios: success, timeout-before, timeout-after-accept, 429 with reset, expired token, rejected content, unsupported media, renamed API field, revoked permission, unavailable, delete failure.
6. Redact secrets from logs everywhere. Add a test that greps logs and repo for known test secrets.

Done when the 14 hard cases each have a dedicated test in `tests/hard_cases/` with recorded results. Keep failures; do not delete them.

---

## PROMPT 5: JOBS, CERTIFICATION, MANIFESTS, BATCH RUNNER (Day 6)

1. Durable background jobs: anything over 2 seconds returns 202 + `job_id`; `GET /api/v1/jobs/{job_id}` returns status, progress 0-100 and result links; optional callback URL signed with HMAC-SHA256 in `X-IncuBrix-Signature`. Jobs survive an API/worker restart (test it).
2. Files in/out: accept upload or URL (SSRF-safe validation, size limits); store outputs in MinIO and return download links.
3. Output manifest JSON on every result: providers/models and versions, settings, seed, timings, cost estimate, warnings, licence/rights, AI-generated flag. Unknown values are `unknown`.
4. **Certification harness**: steps prerequisites, validate, publish test post, confirm live, get_status, delete (verify cleanup within 10 minutes), store evidence, set level. Each step has timestamps and status. Mock runs are labelled `mock` and cannot grant a real-certified level. A renamed API field must fail certification and demote the destination, excluded from publishing and recommendations, with an alert record and prior evidence preserved.
5. **Batch runner CLI** `scripts/batch_runner.py <file-or-folder> --out <dir>`: writes inputs, outputs, failures, logs, summary and links between results and test cases.
6. One command runs all tests with no API keys: `make test` (unit, contract, integration, at least one e2e).

Done when: e2e publish and e2e certification pass, and a batch run produces a complete output folder.

---

## PROMPT 6: CATALOGUE AND ADVANCED FEATURES (Day 7-8)

1. Destination catalogue API and CSV import: validation, URL normalization, duplicate detection on normalized URL + platform, invalid URL report, safe reachability check, enrichment, mixed-language rows, row-level error report (downloadable), progress via job. Benchmark 1,000 rows and record the real time; do not claim under 5 minutes until measured.
2. Relevance scoring 1-5 with a short explanation (AI, video, marketing, SaaS, creators, founders), explainable and configurable.
3. Rule capture: an adapter-based AI step (real provider behind config, mock adapter default) proposes rules from a rules page; a human must confirm before activation.
4. Content tailoring: discussion-first for forums, canonical URL for articles, word-boundary truncation, hashtag/mention style, AI disclosure text, non-English handling. Re-validate after tailoring.
5. Three more connectors, chosen for testability (suggest: Hashnode, Slack, MRSS feed; justify the choice).

Outstanding only if everything above is verified: recommender with precision@10 on a labelled set, `fetch_metrics` on 3 connectors (unavailable is `null`, never 0), 30-day recertification scheduler with demotion plus alert, and a researched real catalogue (catalogue only, nothing posted, no invented numbers).

---

## PROMPT 7: WEB DASHBOARD (Day 7-8, after the engine works)

Build a React + TypeScript + Vite + Tailwind dashboard against the real API, no hard-coded stats. Pages: Overview, Destinations (search/filter/detail), Connectors (manifest, health, errors), Publish (content, tailored renditions, validation, rule decisions, blocked reasons, job tracking), Rules, Certification Center (step timeline pending/running/succeeded/failed, mock vs real label, evidence links), Catalogue Import, Jobs & Logs (idempotency status, retry history, correlation id), Settings, link to `/docs`. Show a clear SIMULATION MODE banner. Protect the live demo with a revocable token and rate limits. Use a browser agent to click through the main flow and capture screenshots for the evidence pack.

---

## PROMPT 8: HARDENING, DOCS, DEPLOYMENT, SUBMISSION (Day 9-10)

1. Generate `openapi.yaml` (3.1) and a test that diffs it against the running service. All routes under `/api/v1/` except the documented exceptions.
2. Write `README.md` (Mermaid architecture, setup under 10 commands, env vars, tests, batch runner, error code list, simulation mode), `REPORT.md` (2-4 pages, measured numbers only: certification counts and time per connector, success rate, duplicates under retry = 0, rule violations caught vs missed, import time, cost per 1,000 publications), `SOURCES.md`, `AI_USE.md`.
3. Build the **test pack** (inputs, outputs including failures, logs, evidence index linking each claim to a file) and **certification pack** (run record, live URL or API response, screenshot, deletion confirmation per certified destination).
4. Fill the Submission Form tabs (must-haves, levels, Integration Standard with proof links, Metrics, Hard cases) with Yes/Partial/No and evidence links. Mark anything unverified as Partial/No.
5. Deployment config for a free host (Render/Fly/Railway), with cold-start time measured, token auth and rate limiting. Verify from an external request; tell me the manual steps that need my accounts. Never invent URLs or tokens.
6. `docs/SUBMISSION_CHECKLIST.md` for the five form fields: GitHub repo URL; repository access (private repo with reviewer access to **admin@incubrix.com**, or public, only after I verify the setting); live demo URL; demo access instructions or a revocable token (never a password); demo video URL (unedited, 8 minutes max: one clean run, one failure and its handling, tests running, one design decision explained in code).
7. Clean-machine check: fresh clone, `cp .env.example .env`, `docker compose up`, `make test`. Report the outcome honestly.

---

## RECOVERY PROMPTS (use when needed)

- "Re-read @docs/REQUIREMENTS_ANALYSIS.md and list every row still `Pending` or `Partial`, with the next action for each."
- "Test X failed. Find the root cause from logs and code, fix it properly (no workaround), add a regression test, and rerun the relevant suites."
- "Audit the repo for secrets, hard-coded paths, mock results labelled as real, and unverified claims in the README/REPORT. List every finding."
- "Simulate the live session: ask me to trace one output field from request to final file, then give me a surprise input and make me predict the result."
