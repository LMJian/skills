# Search Playbook

## Purpose

Use this playbook after the deterministic inventory identifies candidate files. The goal is to reconstruct behavior, not to enumerate the repository.

## Evidence hierarchy

Use this order when sources disagree:

1. Executed runtime or integration evidence.
2. Source code on the relevant deployed/released revision.
3. IDL, schema, protocol definitions, and wire fixtures.
4. Tests that assert externally visible behavior.
5. Configuration defaults and rollout controls.
6. Accepted design decisions and owner documentation.
7. Knowledge-base pages with confidence and staleness caveats.
8. Commit messages, comments, and naming clues.

Generated code proves what a consumer compiled against, but its source IDL and generation owner remain the contract authority.

## Concept expansion

For each user term, build a small search set:

| User concept | Search forms |
| --- | --- |
| Business action | domain verb, RPC method, handler, event/topic name |
| Data object | public type, IDL struct, DB model, serialized job |
| Failure | error constant, result code, retry callback, abort metric |
| Runtime control | config key, TCC/FG key, default constant, option function |
| Compatibility | old entrypoint, adapter, deprecated field, version prefix |

Prefer exact fixed-string `rg -F` searches first. Use regex only after learning local naming.

## End-to-end trace

Trace in both directions:

```text
caller -> public API -> validation -> core branches -> serialization/RPC/storage
       <- result/error <- response mapping <- retry/compensation <- downstream
```

For each edge, capture:

- input/output types and optionality;
- default and exceptional behavior;
- identity, tenant, event, and version fields;
- idempotency and retry unit;
- ordering and partial-success semantics;
- hard limits versus tunable capacity controls;
- owner and change mechanism.

## Git archaeology

Start from the current implementation, then answer focused questions:

- When did this behavior appear?
- What did the immediately previous implementation do?
- Which commit changed the wire shape or failure semantics?
- Did tests change in the same commit?
- Is a compatibility adapter preserving the old behavior?

Use `git log -S` for exact literals or symbol names and `git log -G` for structural patterns. Avoid broad full-history reads without a hypothesis.

## Cross-repository contracts

If all repositories are locally available, inspect both producer and consumer revisions. Otherwise:

- verify the local mirror and generated client;
- record the claimed external owner;
- identify the required remote IDL/commit/version;
- mark the contract `unverified_external`;
- treat field IDs, requiredness, event naming, result codes, partial success, and retry semantics as blocking until confirmed.

## Confidence labels

- `high`: runtime evidence or matching source + contract + test.
- `medium`: source plus one corroborating source, with no conflict.
- `low`: documentation, comments, commit message, or one-sided contract only.
- `unknown`: no reliable local evidence.

Never convert a low-confidence statement into a design constraint without an owner question.

## Common failure patterns

- Reading only new code and missing the old adapter or caller.
- Treating generated code as the editable owner.
- Confusing full business names with transport parent/sub-type fields.
- Treating a TCC default as a server hard limit.
- Testing accepted counts without testing exact failed identities.
- Assuming “library has no deployment” means integration testing is unnecessary.
- Updating code after design approval without invalidating design and test artifacts.
- Searching the knowledge base but failing to record an empty-recall gap.
