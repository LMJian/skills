# Template — Server-Side Technical Design (ready to fill)

Copy this skeleton as a starting point. It is aligned with the internal 技术方案 template. Delete
sections that don't apply (and note you deleted them); replace prompts in _italics_ with real content;
mark decisions needing a human as **【待填写】 / TODO**.

---

**Project Owner**: _name_ · **Main reviewer**: _name_ · **Co-reviewers**: _names_

**Change log**

| Event | What changed | Who | When |
|---|---|---|---|
| Created | Initial draft | | |

---

# 1. Background & Goals

## Background
_Business + technical context. What problem does this solve? Link the PRD. Written so someone **not on
this project** can understand the context. Define terms on first use._

## Goals
### Business goals
_What outcome, measured how — quantify._
### Technical goals
_e.g. P99 800ms → 300ms; +200 QPS; error rate < 0.01%._

# 2. Detailed Design
_Delete sub-sections that don't apply; write "not applicable because …" where a required one is out of
scope._

## 2.0 Key terms
_Acronyms / codenames the reader needs._

## 2.1 Design options & chosen design
_Architecture / flow / sequence diagram here._

**Decision: _Option X_** — _why in one line._

| Option | Approach | Pros | Cons | Chosen |
|---|---|---|---|---|
| A | | | | |
| B | | | | ✅ |

_Refactor only: traffic-diff scope + method (L0 / security-path links require it)._

## 2.2 Interfaces
_Communication method + payload (IDL/fields). Signature & param validation; repeated/LIST upper bound;
authz; idempotency; PR-sensitive naming (bank_card → safe_bank_card)._

| Interface | In | Out | Notes |
|---|---|---|---|

## 2.3 Storage & Cache (required)
_Selection + comparison; data-entity relationships (ER); L4 fields encrypted at rest; cache data-link
diagram + consistency + authz; MySQL latency impact._

## 2.4 MG design (required)
_Applies? Call path; cross ≤ 2, ≤ 400ms (cap 800ms); no wrong-destination routing; downstream MG
support + routing strategy. — or "not applicable because …"._

## 2.5 Exception handling (required)
| Failure point | Trigger | Handling |
|---|---|---|

_Call out multi-level transactions and strong/weak dependencies._

## 2.6 Sensitive data & handling (required)
_L4 (UGC/PII)? Encryption/masking; encrypted at rest; not logged._

## 2.7 Security design (required)
### Business authz
_New interface / changed interface logic / non-interface logic. Fill authz points if interfaces change._
### Encryption & security items
_Sensitive field storage/exposure; key storage (TCC, not in repo); exposed-struct scope; XSS/CSRF;
abuse & rate limiting; compliance audit; new third-party packages._
### Security discussion & conclusion
| Scenario | Conclusion | Notes |
|---|---|---|

## 2.8 Monitoring (required)
_Effective metrics that reflect rollout success and expose anomalies (not argos defaults). Name the
specific metrics + dashboard; add P0&P1 services to the stability dashboard._

## 2.9 Private interop (required)
_Supported? New dependencies supported? Low-version compatibility when a new downstream isn't deployed._

## 2.10 Capacity planning
_Per-day increments: MySQL/Abase/Redis/TOS, gateway QPS, TCE resources, new-table DB selection. Flag
over-threshold items + sign-off owner._

## 2.11 New call-chain traffic assessment (required)
| Service PSM | Interface | Est. traffic | Rate-limit | Scenario |
|---|---|---|---|---|

_Aligned with business owner._

## 2.12 Risk control (required)
_FG kill-switch for L0–L3 / security changes; FG name + strategy; no conflict with product lab switch._

## 2.13 Compatibility with upstream (required)
_Any incompatible change? Blast radius; upstream notified; upstream changes + schedule; mitigation._

## 2.14 Performance impact (required)
_Latency delta; MG thresholds if applicable; RPC and in-loop I/O scrutinized._

# 3. Automated test-case design
_Single tests are the baseline. Attach the test link._
## 3.1 Core-flow cases
_query→create→update, covering tenant / role / permission._
## 3.2 Exception cases
_KA private deployment, FG states, PSM merge, Pre/Online & cn/va/sg data inconsistency._

# 4. Plan checklist
_See review-checklist.md._

# 5. Effort & Milestones
_Milestone breakdown, effort, dates; phase large projects._

# 6. Testing notes
_QA booked; self-testing done._

# 7. Rollout plan (required)
_Gray release + rollback. Multi-service dependency order._

# 8. Review records
## First round
### Conclusion
### TODO
## Second round
_Re-review if the built solution diverges from the design by > 1 person-day._
