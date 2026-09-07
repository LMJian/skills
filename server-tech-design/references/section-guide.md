# Section Guide — Server-Side Technical Design

The catalog of sections a server-side design can contain. For each: **what it's for → what a
reviewer checks → common traps**. Read this before choosing the section set, then include only the
sections this change actually needs (say when you drop one).

Guiding rule throughout: **open each section with the conclusion, then support it. Use a table or
diagram wherever it beats prose.**

---

## Header / Meta
- **Purpose**: make the review auditable — Owner, main reviewer, co-reviewers, and a change-log table
  (event / what changed / who / when).
- **Reviewer checks**: is there an Owner and a reviewer assigned? Is the change log kept up to date so
  a second-round reviewer can see what moved?

## 1. Background & Goals

### Background
- **Purpose**: give the reader the context to understand *what problem this solves*, business and
  technical. Link the PRD if the work comes from a product requirement.
- **Reviewer checks**: could someone **not on this project** understand the situation after reading
  this? Is the pain/current-state stated before the solution?
- **Traps**: diving straight into implementation detail or internal jargon so cross-team reviewers are
  lost. Introduce terms where they first appear.

### Goals
- **Purpose**: state what success looks like and how it's measured.
- **Reviewer checks**: are business and technical goals separated? Are they **quantified** (P99, QPS,
  error rate, coverage) rather than "improve performance / experience"?

## 2. Detailed Design

> General rule: for a sub-section that doesn't apply, write "not applicable because …" — don't leave a
> blank the reviewer has to interpret.

### Key terms
- Define the terms/acronyms/internal codenames needed to read the rest. A cheap, high-value readability
  aid — over-include rather than let a reviewer stall on an acronym.

### Design options & chosen design
- **Purpose**: show what the solution looks like and *why this one*.
- **Reviewer checks**: is there an **architecture/flow/sequence diagram**? At least one **alternative
  compared** (reasoning / pros / cons)? An **explicit decision** with rationale? For refactors: is
  **traffic diff** covered (scope + method)? **L0 links and security-path links must have traffic
  diff.**
- **Traps**: presenting only the chosen option with no rejected alternatives, so reviewers can't judge
  whether the trade-off was sound. Lead with the decision, then the reasoning.

### Interfaces
- **Purpose**: define the contract and its safety for new/changed interfaces.
- **Reviewer checks**: communication method + payload (IDL / field definition); **signature &
  parameter validation**; **upper bound on repeated / LIST fields**; interface authz; **idempotency**;
  sensitive HTTP field naming (e.g. `bank_card` → `safe_bank_card`). Use a table when there are many
  interfaces (name / in / out / notes).

### Storage & Cache
- **Purpose**: how data is stored/cached and kept consistent and safe.
- **Reviewer checks**: storage selection compared against alternatives; data-entity relationships (ER
  diagram when several relate); **L4 fields encrypted at rest**; for caches, a **data-link diagram**,
  **consistency** strategy, and **authz**; MySQL impact on link latency assessed.

### MG (multi-region) design
- **Purpose**: correctness and performance across regions.
- **Reviewer checks**: does it apply? MG call path mapped; degradation bounded (**cross ≤ 2, target
  ≤ 400ms, hard cap 800ms**); no wrong-destination routing; **downstream MG support & routing strategy
  confirmed**. If it doesn't apply, say why.

### Exception handling
- **Purpose**: how each failure point is handled so nothing is unbounded in production.
- **Reviewer checks**: a handling strategy per failure point (timeout, failure, consistency);
  **multi-level transactions and strong/weak dependencies** called out. A "failure point → trigger →
  handling" table reads well here.

### Sensitive data & handling
- **Purpose**: prevent leakage.
- **Reviewer checks**: does any interface carry sensitive data; encryption/masking; **L4 (UGC, PII)**;
  encrypted at rest; **no sensitive data landing in logs**.

### Security design
Three parts, each gated by "does it apply":
- **Business authz** — new interfaces / changed interface logic / non-interface logic (scripts, MQ);
  for interface changes fill the "authz point" items (cross-tenant risk, authz-type functions, security
  products, logical authz, OAPI generic authz).
- **Encryption & security items** — sensitive field storage/exposure; key storage (never in the code
  repo; prefer encrypted TCC); exposed-struct scope validation; XSS/CSRF; black-industry abuse (rate
  limiting); compliance audit; new third-party packages.
- **Security discussion & conclusion** — a table of scenario / conclusion / notes.
- **Reviewer checks**: a per-item "applies? → conclusion" table so the security surface is visible at a
  glance.

### Monitoring
- **Purpose**: make the rollout observable and anomalies catchable.
- **Reviewer checks**: metrics + grafana dashboard; new P0&P1 services added to the stability
  dashboard; monitoring is **effective** — it reflects whether the rollout meets expectations and
  exposes anomalies (don't list argos default-injected metrics).
- **Example**: add a rate limiter → monitor passed vs throttled traffic; add authz → monitor
  pass/reject/fail QPS.
- **Trap**: "we added monitoring" without naming the specific metric.

### 私有互通 (private interop) design
- Does the change / its new dependencies support private interop; how to stay compatible with
  lower-version interop requests when a new downstream isn't deployed. Say why if not applicable.

### Capacity planning
- Estimate per-day increments to MySQL/Abase/Redis/TOS storage, gateway QPS, new TCE resources, and DB
  selection/pressure for new tables.
- **Thresholds needing a sign-off meeting**: MySQL > 10M rows/day, Abase/TOS > 100G/day, Redis
  persistent > 100M/day, gateway new QPS avg > 500/s, TCE expansion / new cluster.

### New call-chain traffic assessment
- For any new call chain, align **QPS and rate-limit config with the business owner**; confirm whether
  related interfaces already have limits and whether they need adjusting. Present as a table:
  service PSM / interface / estimated traffic / rate-limit config / scenario.

### Risk control (kill-switch)
- Changes on **L0–L3 links or security-related changes must have an FG kill-switch** for one-click
  rollback; describe the FG and its strategy; check whether a product lab switch conflicts with the FG.

### Compatibility with upstream
- Could this break upstream? If so: blast-radius assessment, upstream notified, upstream changes &
  schedule, temporary mitigation.

### Performance impact
- Does it add meaningful cost or affect critical-path latency; MG cases follow the MG thresholds;
  otherwise estimate added latency (**focus on RPC and I/O, especially I/O inside loops**).

## 3. Automated test-case design
- **Single tests are the baseline**; keep unit & automated tests in sync with the change; never ship
  before tests pass; **attach the test link**.
- Core-flow cases (query→create→update…) covering tenant / role / permission; exception cases (KA
  private deployment, FG states, PSM merge, Pre/Online and cn/va/sg data inconsistency during rollout).

## 4. Plan checklist
- Structured pre-review self-check; tick each item (see `review-checklist.md`).

## 5. Effort & Milestones
- Break down by milestone with effort and rough dates; for large projects, phase it with per-phase
  goals and dates.

## 6. Testing notes
- QA resources booked in advance; sufficient self-testing.

## 7. Rollout plan (required)
- Confirm with PM/FE/client for complex changes — no unplanned rollout; fully specify **gray release
  and rollback**; when multiple services depend on each other, **state the rollout order**.

## 8. Review records
- Record first-round (conclusion + TODO) and second-round reviews; **re-review when the built solution
  diverges from the design by > 1 person-day**, and sync the relevant people.
