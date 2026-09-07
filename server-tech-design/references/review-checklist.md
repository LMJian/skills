# Review Checklist — Server-Side Technical Design

Run this before handing off a draft. It's the same lens a reviewer applies, so passing it means fewer
review round-trips. Also usable standalone to critique an existing draft. For anything that doesn't
apply, the correct state is "**not applicable because …**", not a blank.

## Structure & completeness
- [ ] Header has Owner / main reviewer / co-reviewers and a change-log table.
- [ ] Linked the related PRD (if the work comes from a product requirement).
- [ ] Key terms defined before they're used.
- [ ] Every mandatory-by-default section has real content or an explicit "not applicable because …":
      Interfaces, Storage, Exception handling, Security, Monitoring, Risk control (kill-switch),
      Rollout.

## Design quality
- [ ] Detailed design has an architecture/flow/sequence **diagram**.
- [ ] At least one **alternative** compared (reasoning / pros / cons) with an **explicit decision**.
- [ ] Refactor: **traffic diff** covered; L0 / security-path links have traffic diff.
- [ ] Interfaces: payload/IDL, signature & param validation, repeated/LIST field upper bound,
      idempotency, PR-sensitive field naming.
- [ ] Storage: L4 fields encrypted at rest; cache consistency + authz described; MySQL latency impact
      assessed.
- [ ] Exception handling covers timeout / failure / consistency; strong-weak dependencies stated.
- [ ] MG: applies? cross ≤ 2, ≤ 400ms (cap 800ms), downstream MG support confirmed — or "n/a because".

## Safety, capacity, risk
- [ ] Sensitive data: L4 (UGC/PII) identified, encrypted at rest, not logged.
- [ ] Security: per-item "applies? → conclusion" for authz / encryption / XSS-CSRF / abuse / compliance
      / third-party packages.
- [ ] Monitoring is **effective** — reflects rollout success and exposes anomalies; specific metrics
      named (not just "added monitoring", not argos defaults).
- [ ] Capacity: storage/QPS/resource increments estimated; over-threshold items have a sign-off owner.
- [ ] New call-chain traffic aligned with the business owner (QPS + rate-limit config).
- [ ] Risk control: FG kill-switch present for L0–L3 / security changes, with strategy; no conflict
      with product lab switch.
- [ ] Compatibility: upstream breaks assessed, notified, scheduled, with a mitigation.
- [ ] Performance: latency delta estimated; RPC / in-loop I/O scrutinized.

## Testing & rollout
- [ ] Core-flow cases + exception cases; **test link attached**.
- [ ] Rollout plan has **gray release + rollback**; multi-service dependencies have a stated **order**.

## Readability (the differentiator)
- [ ] **Background is understandable by someone not on the project** — no undefined jargon.
- [ ] **Decisions lead** — conclusion before reasoning; the reader never guesses which option won.
- [ ] **Diagrams where they help** — flows/architecture/state drawn, not described in prose.
- [ ] **Layered** — headings/lists/tables; no >5–6 line text blocks without a break.
- [ ] **Comparisons are tables** (≥3 items, ≥2 dimensions).
- [ ] **Quantified** — goals, capacity, traffic, performance carry numbers.
- [ ] **Open questions are visible** as 【待填写】 / TODO, not hidden.
- [ ] **Scannable** — a reviewer can grasp the main plan from headings + bold sentences in 1–2 minutes.
