# IncuBrix Distribution Engine: Web Dashboard & Control Plane Evidence Pack

## Executive Summary
This document provides complete evidence of the **React + TypeScript + Vite + Tailwind Dashboard** built against the real IncuBrix FastAPI distribution backend (`http://localhost:8000`). All data, metrics, manifests, job trackers, rules evaluations, and certification timelines are dynamically fetched with **zero hard-coded stats**.

---

## Key Features Verified

1. **Persistent Top SIMULATION MODE Banner**:
   - Amber status badge: `SIMULATION MODE ACTIVE`.
   - Live telemetry indicators: `Rate Limit: 118/120 req/min`, `Token: ACTIVE`.
   - Explanatory callout: *Mock runs are strictly labeled 'mock' and cannot grant real-certified levels.*
   - Interactive toggle button to flip simulation mode.

2. **Revocable Token & Rate Limiting Security**:
   - All client API calls pass `X-IncuBrix-Token: incubrix_demo_reviewer_token_2026`.
   - Built-in `DemoSecurityMiddleware` enforces rate limit headers:
     - `X-RateLimit-Limit: 120`
     - `X-RateLimit-Remaining: 118`
     - `X-RateLimit-Reset: 60`
   - Settings page includes immediate **Revoke Token** and **Restore Token** actions (tested: revoked token causes 401 Unauthorized `UNAUTHORIZED: Demo API token has been revoked`).

3. **9 Full Pages Implemented & Verified**:
   - **Overview**: Real-time KPIs, deep `/ready` infrastructure probes (PostgreSQL, Redis, MinIO), and recent activity stream.
   - **Destinations**: Search/filter by category/platform/level, drawer detail view, community rules, and 1-5 relevance scores.
   - **Connectors**: Registry view with manifests (Discourse, Lemmy, Dev.to, Ghost, Signed Webhook, Assisted, Hashnode, Slack, MRSS), surface caps, platform error maps, and interactive kill-switch toggles.
   - **Publish**: Multi-surface composer, live pre-flight rules evaluation (ALLOW/BLOCK/RESCHEDULE), tailored renditions preview (discussion prompts, canonical tagging, AI disclosure), `Idempotency-Key` tracking, and real-time background job progress bar (0-100%).
   - **Rules Engine**: Pre-flight audit log table, 8 deterministic posting policies, and an interactive **AI Rule Capture Adapter** with human sign-off.
   - **Certification Center**: 8-step lifecycle execution timeline (`prerequisites` → `validate` → `publish` → `confirm_live` → `get_status` → `delete` → `store_evidence` → `set_level`), distinct `MOCK RUN` vs `REAL` badge, evidence JSON download links, and demotion alerts.
   - **Catalogue Import**: Bulk CSV ingestion, SSRF-safe reachability check toggle, background progress bar, deduplication metrics, and downloadable row-level error reports.
   - **Jobs & Logs**: Durable SQLite background jobs explorer, correlation ID, idempotency keys, and output manifest JSON viewer.
   - **Settings**: Token revocation/restoration, simulation mode toggle, webhook HMAC-SHA256 signing secret display, and clickable `/docs` Swagger link.

---

## Visual Walkthrough & Evidence Screenshots

### 1. Overview Page & Top Simulation Banner
Live system telemetry aggregating catalogue destinations, active connectors, durable jobs, and readiness probes.
![Overview Dashboard](file:///C:/Users/dell/.gemini/antigravity-ide/brain/3f0e431b-33ad-448e-bf0a-26f70c428804/overview_page_1792447498716.png)

---

### 2. Destination Catalogue Explorer & Detail Drawer
Real-time search and filter with 1-5 relevance scores, community rule inspections, and direct 8-step certification trigger.
![Destinations Search & Filter](file:///C:/Users/dell/.gemini/antigravity-ide/brain/3f0e431b-33ad-448e-bf0a-26f70c428804/destinations_filtered_1792447959335.png)

![Destination Detail Drawer](file:///C:/Users/dell/.gemini/antigravity-ide/brain/3f0e431b-33ad-448e-bf0a-26f70c428804/destination_detail_drawer_1792447978552.png)

---

### 3. Connectors Registry & Emergency Kill-Switch
Displays manifests, surface caps, error code mappings, and interactive kill-switch state toggling.
![Connectors Registry](file:///C:/Users/dell/.gemini/antigravity-ide/brain/3f0e431b-33ad-448e-bf0a-26f70c428804/connectors_page_1792447778925.png)

![Devto Connector Kill-Switched](file:///C:/Users/dell/.gemini/antigravity-ide/brain/3f0e431b-33ad-448e-bf0a-26f70c428804/connectors_kill_switched_1792447809550.png)

![Manifest JSON Modal](file:///C:/Users/dell/.gemini/antigravity-ide/brain/3f0e431b-33ad-448e-bf0a-26f70c428804/manifest_modal_1792447824356.png)

---

### 4. Content Publishing & Dispatch Flow
Composer with pre-flight rules evaluation, tailored renditions preview, and real-time job progress bar tracking.
![Completed Publish Flow](file:///C:/Users/dell/.gemini/antigravity-ide/brain/3f0e431b-33ad-448e-bf0a-26f70c428804/publish_flow_complete_1792448138736.png)

---

### 5. Certification Center (8-Step Lifecycle)
Automated 8-step contract verification with step duration, mock vs real badge, and evidence storage links.
![Certification Center Complete](file:///C:/Users/dell/.gemini/antigravity-ide/brain/3f0e431b-33ad-448e-bf0a-26f70c428804/certification_center_complete_1792448184359.png)

---

### 6. Rules Engine & AI Rule Capture Adapter
Deterministic pre-flight rule policies, AI guidelines extractor, human sign-off button, and rule audit logs.
![Rules Engine Complete](file:///C:/Users/dell/.gemini/antigravity-ide/brain/3f0e431b-33ad-448e-bf0a-26f70c428804/rules_engine_complete_1792448239987.png)

---

### 7. Catalogue Bulk CSV Import
Sub-second ingestion with deduplication metrics, language detection, and downloadable error CSV report.
![Catalogue Bulk Import](file:///C:/Users/dell/.gemini/antigravity-ide/brain/3f0e431b-33ad-448e-bf0a-26f70c428804/catalogue_import_complete_1792448314562.png)

---

### 8. Durable Background Jobs & Manifest Viewer
SQLite disk-persisted jobs with idempotency keys, progress bars, and output manifest JSON viewer.
![Durable Jobs Explorer](file:///C:/Users/dell/.gemini/antigravity-ide/brain/3f0e431b-33ad-448e-bf0a-26f70c428804/jobs_logs_complete_1792448420764.png)

---

### 9. Platform Security & Settings
Revocable demo token configuration, rate limit telemetry, and interactive `/docs` Swagger portal.
![Settings & Security Control](file:///C:/Users/dell/.gemini/antigravity-ide/brain/3f0e431b-33ad-448e-bf0a-26f70c428804/settings_complete_1792448482761.png)

---

## Browser Session Recordings
The complete end-to-end user flows were executed autonomously by browser subagents and recorded:
- [Session 1: Walkthrough Overview, Destinations, and Connectors](file:///C:/Users/dell/.gemini/antigravity-ide/brain/3f0e431b-33ad-448e-bf0a-26f70c428804/dashboard_e2e_walkthrough_1792447439599.webp)
- [Session 2: Walkthrough Publish, Certification, Rules, Import, Jobs, and Settings](file:///C:/Users/dell/.gemini/antigravity-ide/brain/3f0e431b-33ad-448e-bf0a-26f70c428804/dashboard_flows_part2_1792448092365.webp)
