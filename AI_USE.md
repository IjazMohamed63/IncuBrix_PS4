# AI_USE.md: AI Assistant & Tooling Disclosure

This document discloses all AI tools, models, assistants, and automated systems used during the development of the IncuBrix Long-Tail Distribution Network, in compliance with the Engineering Assessment 4 guidelines.

---

## 1. AI Coding Assistants & Environments

| Tool / Assistant | Provider | Version / Model | Scope & Responsibility |
|:-----------------|:---------|:----------------|:-----------------------|
| **Antigravity AI IDE** | Google DeepMind | Gemini 3.8 Flash (High) | Pair programming, architecture document generation, code authoring, and test implementation |

---

## 2. Tasks & Workflows Assisted by AI

1. **Architecture & Requirements Analysis (Phase 1)**:
   - Extraction of constraints, must-haves, Integration Standard criteria, and 14 hard cases from `IncuBrix_Assessment4.pdf`.
   - Authoring of Mermaid sequence, state, and C4-style container diagrams.
2. **Scaffold & Contract Schemas (Phase 2)**:
   - Generation of Pydantic v2 validation models conforming to Appendix A connector methods.
   - Authoring of contract test assertions and error-code mapping handlers.
3. **Core & Advanced Connectors (Phase 3 & 6)**:
   - Implementation of HTTP clients for Discourse, Lemmy, Dev.to, Ghost, Webhook, and Assisted packs.
4. **Reliability & Rules Engine (Phase 4)**:
   - Algorithmic implementation of token-bucket rate limiters, backoff window calculations, and pre-flight rules evaluation.
5. **Quality Assurance & Verification**:
   - Automated unit, integration, and contract test suites.

---

## 3. Human Review & Verification Statement
All architecture, schemas, and application logic produced with AI assistance were critically analyzed, verified for mathematical and logical correctness, tested against real executions, and formatted to ensure complete explainability in a live code review session.
