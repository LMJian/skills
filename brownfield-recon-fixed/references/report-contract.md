# Report Contract

## Artifact layout

Write these files under the selected artifact directory:

```text
brownfield-recon/
├── evidence.json
├── report.md
├── contract-matrix.md
└── open-questions.md
```

## `report.md`

Use the following sections:

1. **Readiness** — `READY`, `READY_WITH_GAPS`, or `BLOCKED`, with a one-paragraph reason.
2. **Scope and evidence** — repository, branch/base, keywords, inspected modules, unavailable dependencies, KB result.
3. **System map** — entrypoints, main flow, downstreams, persistence, configuration, and generated-code boundaries.
4. **Existing behavior** — externally visible current behavior with `path:line` evidence.
5. **Historical behavior** — legacy behavior, introducing/changing commits, retained compatibility adapters.
6. **Compatibility invariants** — behaviors that must not change silently.
7. **Failure, retry, and idempotency** — partial success, retry unit, persisted unit, abort/compensation, ordering.
8. **Configuration and capacity** — defaults, TCC/FG, runtime knobs, hard limits, owner.
9. **Risks and contradictions** — code/docs/test/IDL conflicts, severity, affected consumers.
10. **Design inputs** — constraints, recommended contract tests, and explicit non-goals.

For important claims, use a table:

| Topic | Fact | Evidence | Confidence | Design impact |
| --- | --- | --- | --- | --- |

Label inferred statements with `Inference:` and explain the supporting facts.

## `contract-matrix.md`

Use one row per high-impact field or behavior:

| Contract | Producer | Consumer | Owner | Wire/type semantics | Failure/retry semantics | Evidence | Status |
| --- | --- | --- | --- | --- | --- | --- | --- |

Allowed status values:

- `verified`
- `verified_local_only`
- `unverified_external`
- `conflict`
- `pending_owner`

Field IDs, requiredness, enum values, identity composition, parent/sub-type rules, error codes, partial success, batch cardinality, idempotency keys, and versioning deserve separate rows.

## `open-questions.md`

Use questions that an owner can answer decisively:

| Priority | Question | Why blocking | Evidence already checked | Required owner | Decision deadline |
| --- | --- | --- | --- | --- | --- |

Priorities:

- `P0`: unsafe to design or implement without an answer.
- `P1`: implementation can start only behind an explicit boundary or temporary adapter.
- `P2`: non-blocking documentation or future evolution.

Do not use vague questions such as “请确认方案是否合理”. Ask for a concrete field, limit, owner, or behavior choice.
