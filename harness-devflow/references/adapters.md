# Platform adapters

The core depends on Python 3.10+ and Git. A project can use any language, documentation
format, test runner, code host or deployment target. Checks consume an exit code; adapters
add a small JSON response. Nothing contacts an external platform until its configured
command is actually invoked.

## Project configuration

`checks` and `adapters` are maps in `.harness/project.json`. A check has `argv` and optional
`timeout_seconds`; an adapter also declares `effect: read | local | external`. The effect is
an operator-authored declaration, not a sandbox. Treat project command configuration as
executable code. The runtime records existing authorization for external adapters; it does
not grant new permission or replace the host's sandbox.

Available adapter slots: `interfaces`, `push`, `pr`, `monitor`, `deploy`.
The core doesn't require a document-publishing adapter: local artifacts are the review packet,
and a user-authorized connector can publish them and add a URL to the packet.

```json
{
  "push": {
    "argv": ["python3", "{plugin_root}/adapters/git_push.py", "--remote", "origin"],
    "effect": "external",
    "timeout_seconds": 240
  },
  "pr": {
    "argv": ["python3", "{plugin_root}/adapters/github.py", "--repo", "OWNER/REPOSITORY", "--base", "main",
             "--title-file", "{artifact_dir}/pr-title.txt", "--body-file", "{artifact_dir}/pr-body.md"],
    "effect": "external",
    "timeout_seconds": 300
  },
  "monitor": {
    "argv": ["python3", "{plugin_root}/adapters/github.py", "--repo", "OWNER/REPOSITORY"],
    "effect": "read",
    "timeout_seconds": 120
  }
}
```

This is an example `adapters` value, not a usable configuration until the repository and
base branch are replaced with verified values. `origin` is an example; select the intended
remote. GitHub CLI is optional and must already be installed/authenticated if selected.
The GitHub adapter reconciles an existing open request on the same head/base, checks its
head SHA, creates a request using explicit title/body files, or observes the recorded PR.
It never merges or posts comments. Closed-unmerged requests stay non-complete.

GitHub flags/fields were checked against the primary CLI manuals:
[create](https://cli.github.com/manual/gh_pr_create),
[list](https://cli.github.com/manual/gh_pr_list),
[view](https://cli.github.com/manual/gh_pr_view).
Provider tests use a fake executable for contract/error cases; live GitHub authorization is
not part of the core test suite.

## Request

The subprocess receives `HARNESS_REQUEST`, an absolute path to a JSON file, plus
`HARNESS_TASK`, `HARNESS_STAGE`, `HARNESS_IDEMPOTENCY_KEY`. It inherits the existing process
environment; no tokens are written into project configuration by the plugin.

The request contains:

- `schema_version`, `task`, `goal`, `stage`;
- `repository`, `branch`, reviewed `head`, `base_ref`, `base_sha`;
- `artifact_directory`, `idempotency_key`;
- `prior_results`: successful adapter responses, useful for locating an already-created PR.

Relative command paths and arguments resolve from the consumer working directory. Placeholder
substitution is limited to documented tokens in argv. Do not interpolate a shell string.
The timeout covers the subprocess; on POSIX its process group is terminated on timeout.
Diagnostics belong on stderr; adapter stdout is limited to one JSON response of at most 1 MiB.

## Response

```json
{
  "schema_version": 1,
  "status": "pass",
  "summary": "Describe the observed successful operation"
}
```

`status` is `pass`, `pending` or `fail`. Only a successful command exit plus `pass` can
complete a stage. Additional required result fields:

| Adapter | Successful result |
| --- | --- |
| interfaces | Summary of generated contracts and dependency updates; artifacts in stage report |
| push | Summary of actual push; recommended remote and head fields |
| pr | Nonempty `external_id` and `url` |
| monitor | `state: open | merged | closed`; only `merged` allows stage completion |
| deploy | Nonempty `deployment_id`; return pass after actual completion/health verification |

The core checks the response contract, not the external service itself. A custom adapter must
implement honest observation, version pinning, timeout handling and reconciliation. Returning
`pass` after merely scheduling a deployment is incorrect.

## Implement a new adapter

Use a small project-owned script. Read the request, use the project's authenticated API/CLI,
reconcile previous outcomes using the idempotency key, and return the JSON contract. A GitLab,
Azure DevOps or self-hosted service uses the same `pr`/`monitor` contract; no changes to core
state transitions are necessary. A container, CI or cloud deployment uses the `deploy` slot.

For uncertain results, inspect the remote object before retrying. Failed or timed-out processes
can already have produced an external effect. Global uniqueness cannot be guaranteed by a local
lock across separate machines; the provider adapter must supply any required server-side
idempotency. Cross-repository schema updates should wait for real generation/publishing results
and record both upstream and consumer dependency evidence.

## Scheduler boundary

The runtime records a real scheduler's provider/handle via `record-monitor`; it does not run a
persistent daemon. The monitor skill uses an available host automation or explicitly configured
CI/webhook scheduler only when monitoring has been requested. A handle is bookkeeping, not a
scheduler implementation. Aborting/closing a task requires cancelling the actual job too.
