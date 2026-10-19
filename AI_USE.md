# AI_USE.md: AI Assistant & Tooling Disclosure

This document discloses all AI tools, models, assistants, and automated systems used during the development of the IncuBrix Long-Tail Distribution Network, in compliance with the Engineering Assessment 4 guidelines.

---

## 1. AI Coding Assistants & Environments

| Tool / Assistant | Provider | Version / Model | Scope & Responsibility |
|:-----------------|:---------|:----------------|:-----------------------|
| **Antigravity AI IDE** | Google DeepMind | Gemini 3.8 Flash (High) | Pair programming, architecture document generation, code authoring, automated testing, React dashboard implementation, and browser subagent verification |

---

## 2. Tasks & Workflows Assisted by AI

1. **Architecture & Requirements Analysis (Phase 1)**:
   - Extraction of constraints, must-haves, Integration Standard criteria, and 14 hard cases from `IncuBrix_Assessment4.pdf`.
   - Authoring of Mermaid sequence, state, and C4-style container diagrams.
2. **Scaffold & Contract Schemas (Phase 2)**:
   - Generation of Pydantic v2 validation models conforming to Appendix A connector methods.
   - Authoring of contract test assertions and error-code mapping handlers.
3. **Core & Advanced Connectors (Phase 3 & 6)**:
   - Implementation of HTTP clients for Discourse, Lemmy, Dev.to, Ghost, Webhook, Assisted packs, Hashnode, Slack, and MRSS.
4. **Reliability & Rules Engine (Phase 4)**:
   - Algorithmic implementation of token-bucket rate limiters, backoff window calculations, and pre-flight rules evaluation.
5. **Durable Jobs & 8-Step Certification (Phase 5)**:
   - SQLite disk persistence, HMAC-SHA256 callback signatures, manifest builders, and certification harness.
6. **Web Dashboard & Control Plane (Phase 7)**:
   - React 19 + TypeScript + Vite + Tailwind CSS dashboard with 9 pages, live API stats, simulation mode banner, and revocable demo token security.
7. **Autonomous Browser Verification (Phase 7 & 8)**:
   - Browser subagent automation clicking through end-to-end flows, capturing evidence pack screenshots, and verifying zero console errors.

---

## 3. Human Review & Verification Statement
All architecture, schemas, and application logic produced with AI assistance were critically analyzed, verified for mathematical and logical correctness, tested against real executions, and formatted to ensure complete explainability in a live code review session.
