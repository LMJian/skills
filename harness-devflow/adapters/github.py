#!/usr/bin/env python3
"""Optional GitHub CLI adapter for PR creation/reuse and one-shot observation.

Uses explicit repository/head/base and --body-file. It never merges or sends comments.
The core workflow has no dependency on this adapter or on GitHub CLI.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import subprocess
import sys


def call(repo, *args, json_output=True):
    result = subprocess.run(["gh", *args, "--repo", repo], capture_output=True, text=True,
                            stdin=subprocess.DEVNULL, timeout=90)
    if result.returncode:
        raise RuntimeError(result.stderr.strip() or "GitHub CLI failed")
    return json.loads(result.stdout) if json_output else result.stdout.strip()


def process(request, args):
    stage = request["stage"]
    if stage == "pr":
        if not args.base or not args.body_file or not args.title_file:
            raise ValueError("PR creation needs explicit --base, --title-file and --body-file")
        prs = call(args.repo, "pr", "list", "--head", request["branch"], "--base", args.base,
                   "--state", "open", "--json", "number,url,headRefOid", "--limit", "100")
        if len(prs) > 1:
            raise ValueError("Multiple matching PRs; select/reconcile the intended PR explicitly")
        if prs:
            pr = prs[0]
            if pr["headRefOid"] != request["head"]:
                raise ValueError("Existing PR head does not match reviewed local HEAD; reconcile push first")
        else:
            title = Path(args.title_file).read_text().strip()
            body_path = Path(args.body_file).resolve()
            if not title or not body_path.read_text().strip():
                raise ValueError("PR title and body must be concrete and nonempty")
            url = call(args.repo, "pr", "create", "--head", request["branch"], "--base", args.base,
                       "--title", title, "--body-file", str(body_path), json_output=False)
            pr = call(args.repo, "pr", "view", url, "--json", "number,url,headRefOid")
            if pr["headRefOid"] != request["head"]:
                raise ValueError("Created PR head differs from reviewed HEAD; reconcile before continuing")
        return {"schema_version": 1, "status": "pass", "summary": "PR exists for the reviewed branch",
                "external_id": str(pr["number"]), "url": pr["url"], "head": pr["headRefOid"]}
    if stage != "monitor":
        raise ValueError("GitHub adapter supports only pr and monitor")
    prior = [r for r in request["prior_results"] if r and r.get("external_id") and r.get("url")]
    if not prior:
        raise ValueError("No recorded PR receipt; create or reconcile the PR first")
    pr = call(args.repo, "pr", "view", prior[-1]["external_id"], "--json",
              "number,url,state,headRefOid,reviewDecision,statusCheckRollup,comments,reviews")
    state = pr["state"].lower()
    if pr["headRefOid"] != request["head"]:
        raise ValueError("Remote PR head changed; inspect and review the actual branch before proceeding")
    return {"schema_version": 1, "status": "pass" if state == "merged" else "pending",
            "summary": f"PR is {state}", "state": state, "external_id": str(pr["number"]),
            "url": pr["url"], "head": pr["headRefOid"], "signals": pr}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", required=True, help="[HOST/]OWNER/REPO")
    parser.add_argument("--base")
    parser.add_argument("--title-file")
    parser.add_argument("--body-file")
    args = parser.parse_args()
    request = json.loads(Path(os.environ["HARNESS_REQUEST"]).read_text())
    print(json.dumps(process(request, args)))


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, KeyError, RuntimeError, subprocess.SubprocessError) as error:
        print(json.dumps({"schema_version": 1, "status": "fail", "summary": str(error)}))
        sys.exit(1)
