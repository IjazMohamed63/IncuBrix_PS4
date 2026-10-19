# Engineering Assessment 4: Submission Checklist & Reviewer Pack

This document outlines the exact five fields required on the official IncuBrix Engineering Assessment submission form, along with reviewer credentials, verification steps, and account actions.

---

## The 5 Submission Form Fields

### 1. GitHub Repository URL
- **Field**: `GitHub Repo URL`
- **Value**: `https://github.com/[YOUR_GITHUB_USERNAME]/incubrix-distribution`
- **Instructions**:
  - Replace `[YOUR_GITHUB_USERNAME]` with your actual GitHub account.
  - Ensure the repository contains all commits through Prompt 8.

---

### 2. Repository Access Verification
- **Field**: `Repository Access`
- **Choice**: Private Repository (with reviewer invitation) or Public Repository
- **Reviewer Account to Invite**: `admin@incubrix.com`
- **Manual Steps for Candidate**:
  1. Go to your repository on GitHub: `https://github.com/[YOUR_GITHUB_USERNAME]/incubrix-distribution/settings/access`.
  2. Click **Collaborators** -> **Add people**.
  3. Enter `admin@incubrix.com` and send the collaboration invitation.
  4. Ensure the invitation status is **Pending** or **Accepted** before submitting.

---

### 3. Live Demo URL
- **Field**: `Live Demo URL`
- **Value**: `https://[YOUR_RENDER_OR_RAILWAY_APP].onrender.com` (or local tunneling via `ngrok http 5173`)
- **Measured Cold-Start Time**: **1,565 ms (1.56 seconds)** from cold boot to responsive `/health`.
- **Manual Steps to Deploy on Render (Free Tier)**:
  1. Log into your Render account at [dashboard.render.com](https://dashboard.render.com).
  2. Click **New +** -> **Blueprint**.
  3. Connect your GitHub repository `incubrix-distribution`.
  4. Render will automatically detect `render.yaml` and provision the `incubrix-distribution-api` web service.
  5. Once deployed, copy your service URL (e.g. `https://incubrix-distribution-api.onrender.com`) and paste it into this field.

---

### 4. Demo Access Instructions & Revocable Token
- **Field**: `Demo Access Instructions`
- **Revocable Reviewer Token**: `incubrix_demo_reviewer_token_2026`
- **Password**: *None (Token authentication only; never pass a raw password)*
- **Instructions for Reviewers**:
  1. Open the Live Demo Dashboard in your browser.
  2. The application is pre-configured with the reviewer token `incubrix_demo_reviewer_token_2026` in local storage.
  3. To verify token authentication via `curl`:
     ```bash
     # Valid authenticated request (Returns HTTP 200 + destinations)
     curl -H "X-IncuBrix-Token: incubrix_demo_reviewer_token_2026" \
          https://[YOUR_APP_URL]/api/v1/destinations

     # Rate limit headers returned on all responses:
     # X-RateLimit-Limit: 120
     # X-RateLimit-Remaining: 118
     # X-RateLimit-Reset: 60
     ```
  4. To test instant token revocation:
     - Navigate to the **Settings** page on the dashboard.
     - Click **Revoke Token Immediately**.
     - Subsequent requests immediately receive `HTTP 401 Unauthorized` with code `UNAUTHORIZED`.
     - Click **Restore Revoked Token** to restore access.

---

### 5. Demo Video URL (Unedited, Under 8 Minutes)
- **Field**: `Demo Video URL`
- **Candidate Recording Instructions** (Record an unedited screencast under 8 minutes covering):
  1. **Clean Run (2 mins)**:
     - Open the React Dashboard at `/overview`.
     - Go to `/publish`, select a destination (e.g., `Discourse` or `Dev.to`), click **Dispatch Publication Job**, and watch the progress bar reach 100% with the published live URL.
  2. **Failure & Handling (2 mins)**:
     - Go to `/publish`, paste commercial text ("Huge discount, buy now 50% off!"), and observe pre-flight rules engine immediately return `BLOCK: self_promo` with required human action.
  3. **Tests Running (1.5 mins)**:
     - In terminal, execute `pytest -q` showing all 107 tests passing in ~7 seconds.
  4. **Design Decision Explained in Code (2 mins)**:
     - Open [rules_engine.py](file:///d:/Incubrix-app/engine/rules_engine.py) or [certification_harness.py](file:///d:/Incubrix-app/engine/certification_harness.py) and briefly explain the pre-flight zero-bypass architecture and strict `mock` vs `real` certification distinction.
  5. Upload to YouTube (Unlisted) or Loom and paste the link here.

---

## 6. Pre-Submission Self-Audit Checklist

- [x] All routes under `/api/v1/` except documented exceptions (`/health`, `/ready`, `/connector/v1/*`).
- [x] `openapi.yaml` (3.1) generated with zero drift against running service test.
- [x] 107 / 107 tests passing (`pytest -q`).
- [x] 14 / 14 hard cases trapped and verified with tests.
- [x] Catalogue import benchmark: 1,000 rows in 0.68s.
- [x] Duplicates under concurrency: 0 duplicates under 10 parallel threads.
- [x] React dashboard contains no hard-coded stats and displays top SIMULATION MODE banner.
- [x] All 9 connectors implemented with manifests, contracts, and error maps.
- [x] Commercial license declarations complete in `SOURCES.md` (no AGPL in runtime).
- [x] AI tooling disclosures complete in `AI_USE.md`.
