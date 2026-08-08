# Coding Standards: gitea_mcp

This document defines the engineering rigor required for all contributions to this project. It is structured in two tiers: **General Standards** (universal engineering baselines) and **Project Standards** (implementation-specific rules).

---

## 1. General Tier (Universal Baselines)
These standards apply to all code regardless of language or framework to ensure long-term maintainability and reliability.

### 1.1 Formal Verification & Testing
No feature is considered "complete" until it has been verified.
- **Peer Review:** All code must undergo a formal examination process (e.g., Pull Request review) to ensure it meets quality bars before merging.
- **Automated Testing:** Every significant change must be accompanied by automated tests to verify correctness and prevent regressions.
- *Source:* [MS&T Standard Document Template | NIST](https://www.nist.gov/document/v1s4-20050301doc)

### 1.2 Design Alignment
Code must be a realization of a design, not an improvised solution.
- **Design Adherence:** Implementation must align with the project's design documents. If a design must change during implementation, the documentation must be updated first.
- *Source:* [Coding Standards and Guidelines | GeeksforGeeks](https://www.geeksforgeeks.org/software-engineering/coding-standards-and-guidelines/)

### 1.3 Maintainability & Complexity
Code should be written for the next developer, not the current one.
- **Complexity Limits:** Developers should strive to minimize cyclomatic complexity. Functions should do one thing and do it well.
- *Source:* [Coding Standards: What Are They and Why Are They Important? | Codacy](https://blog.codacy.com/coding-standards)

---

## 2. Project Tier (Project-Specific Implementation)

### 2.1 Testing Frameworks
- **Unit/Integration Testing:** `pytest`, run against a live Gitea instance (a disposable test repo/org, not a production DMC Labs repo) — not a mocked `_request()` boundary. This is a deliberate choice recorded in the project spec (issue #1): tests validate the actual Gitea API contract, not an approximation of it. No minimum coverage percentage is enforced; every tool must have at least a happy-path test and one test per applicable error class (404, 401/403, 409, 422).
- **No test suite exists yet** as of this document's writing — this defines the standard the first test suite must meet, not a claim that one is present.

### 2.2 Review Process
- **Approval Requirements:** Single-maintainer project. Changes are reviewed by the maintainer via a GitHub Pull Request before merging to `main` — no minimum external-approver count is enforced, but self-merging without opening a PR is discouraged so the diff is visible in review form.

### 2.3 Architectural Constraints
- **Single HTTP boundary:** every Gitea API call must route through the shared `_request()` helper in `gitea_mcp.py` — no tool may call `httpx` directly. This keeps auth, base URL, timeout, and status handling in one place.
- **Centralized error translation:** any exception from `_request()` must be passed through `_handle_api_error()` before being returned to the MCP client — tools must not let raw exceptions propagate or format their own ad hoc error strings.
- **Env-var-only secrets:** `GITEA_TOKEN` and `GITEA_BASE_URL` are read from process environment only. Never hardcode a token, accept one as a tool parameter, log it, or write it to disk.
- **Schema-validated input:** every tool's parameters must be defined as a Pydantic `BaseModel` with `extra="forbid"`, so malformed calls fail before reaching Gitea. Fields with a fixed set of valid values (e.g. `state`) must use `Literal`/enum typing, not an unconstrained `str`.
