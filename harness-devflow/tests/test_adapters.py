"""Command boundary tests. Remote service behavior is explicitly simulated."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
from unittest.mock import patch

from adapters import github
from harness import runner
from harness.model import HarnessError
from harness.storage import atomic_json, read_json
from test_workflow import RepoCase


class AdapterTests(RepoCase):
    def set_adapter(self, code, effect="read", timeout=5, stage="interfaces", extra=None):
        config_path = self.root / ".harness/project.json"
        config = read_json(config_path)
        config["adapters"][stage] = {"argv": [sys.executable, "-c", code, *(extra or [])],
                                     "effect": effect, "timeout_seconds": timeout}
        atomic_json(config_path, config)
        self.commit("Configure adapter")
        self.flow.sync_config("Configure test adapter before design")

    def at_interfaces(self):
        self.to_approval()
        self.flow.approve("design_approval", "fixture-user", "Approve test design")
        self.flow.enter("interfaces")

    def test_external_command_requires_authorization_before_it_can_execute(self):
        self.set_adapter('print("executed")', effect="external")
        self.at_interfaces()
        before = len(self.flow.load()["runs"])
        with self.assertRaisesRegex(HarnessError, "authorization"):
            runner.run(self.flow, "adapter", "interfaces")
        self.assertEqual(len(self.flow.load()["runs"]), before)

    def test_malformed_or_missing_adapter_output_cannot_pass(self):
        self.set_adapter('print("not-json")')
        self.at_interfaces()
        receipt = runner.run(self.flow, "adapter", "interfaces")
        self.assertEqual(receipt["status"], "failed")
        with self.assertRaises(HarnessError):
            self.flow.complete("interfaces", str(self.report("interfaces", adapter_run=receipt["id"])))

    def test_timeout_is_real_failure_with_recorded_logs(self):
        self.set_adapter('import time; print("starting", flush=True); time.sleep(30)', timeout=1)
        self.at_interfaces()
        receipt = runner.run(self.flow, "adapter", "interfaces")
        self.assertTrue(receipt["timed_out"])
        self.assertEqual(receipt["status"], "unresolved")
        self.assertIn("starting", Path(receipt["stdout"]).read_text())
        self.assertLess(receipt["duration_seconds"], 10)

    def test_argv_metacharacters_are_literal_and_idempotency_key_is_stable(self):
        payload = '$(touch unwanted); `touch other`'
        code = 'import json,sys; print(json.dumps({"schema_version":1,"status":"pass","summary":sys.argv[1]}))'
        self.set_adapter(code, extra=[payload])
        self.at_interfaces()
        one = runner.run(self.flow, "adapter", "interfaces")
        two = runner.run(self.flow, "adapter", "interfaces")
        self.assertEqual(one["response"]["summary"], payload)
        self.assertEqual(one["idempotency_key"], two["idempotency_key"])
        self.assertFalse((self.root / "unwanted").exists())

    def test_failed_commands_hit_bounded_retry_limit(self):
        self.set_adapter('import sys; sys.exit(9)')
        self.at_interfaces()
        for _ in range(3):
            receipt = runner.run(self.flow, "adapter", "interfaces")
            self.assertEqual(receipt["exit_code"], 9)
        with self.assertRaisesRegex(HarnessError, "budget"):
            runner.run(self.flow, "adapter", "interfaces")

    def test_command_that_mutates_tested_code_fails_receipt(self):
        config_path = self.root / ".harness/project.json"
        config = read_json(config_path)
        config["checks"]["mutator"] = {"argv": [sys.executable, "-c", 'open("base.py","w").write("changed = True")']}
        config["stage_checks"]["integration"] = ["mutator"]
        atomic_json(config_path, config)
        self.commit("Configure mutation fixture")
        self.flow.sync_config("Set mutation test before design")
        self.finish_review()
        self.flow.enter("integration")
        result = runner.run(self.flow, "check", "mutator")
        self.assertEqual(result["status"], "failed")
        self.assertIn("Code changed", result["error"])

    def test_monitor_pending_then_merged_and_release_gate(self):
        marker = self.root / ".harness/runs/example/remote-state"
        marker.write_text("open")
        pr_code = 'import json; print(json.dumps({"schema_version":1,"status":"pass","summary":"Simulated PR","external_id":"7","url":"https://example.test/pr/7"}))'
        self.set_adapter(pr_code, effect="external", stage="pr")
        mon_code = ('import json; from pathlib import Path; state=Path(' + repr(str(marker)) + ').read_text(); '
                    'print(json.dumps({"schema_version":1,"status":"pass" if state=="merged" else "pending",'
                    '"summary":"Simulated observation","state":state}))')
        self.set_adapter(mon_code, stage="monitor")
        push_code = 'import json; print(json.dumps({"schema_version":1,"status":"pass","summary":"Simulated push"}))'
        self.set_adapter(push_code, stage="push")
        self.flow.configure_flow({"target": "deployed"}, "Exercise remote release lifecycle")
        self.finish_review()
        self.flow.enter("integration")
        receipt = runner.run(self.flow, "check", "unit")
        self.flow.complete("integration", str(self.report("integration", checks=[receipt["id"]])))
        self.flow.enter("push")
        receipt = runner.run(self.flow, "adapter", "push")
        self.flow.complete("push", str(self.report("push", adapter_run=receipt["id"])))
        self.flow.enter("pr")
        receipt = runner.run(self.flow, "adapter", "pr", authorization="Fixture explicitly permits simulated creation")
        self.flow.complete("pr", str(self.report("pr", adapter_run=receipt["id"])))
        with self.assertRaises(HarnessError):
            self.flow.skip("monitor", "Bypass merge observation")
        self.flow.enter("monitor")
        receipt = runner.run(self.flow, "adapter", "monitor")
        self.assertEqual(receipt["status"], "pending")
        with self.assertRaises(HarnessError):
            self.flow.complete("monitor", str(self.report("monitor", adapter_run=receipt["id"])))
        marker.write_text("merged")
        receipt = runner.run(self.flow, "adapter", "monitor")
        result = self.flow.complete("monitor", str(self.report("monitor", adapter_run=receipt["id"])))
        self.assertEqual(result["current_stage"], "release")

    def test_git_push_adapter_updates_real_local_remote(self):
        plugin = Path(__file__).resolve().parent.parent
        remote = self.root / ".harness/runs/remote.git"
        subprocess.run(["git", "init", "--bare", str(remote)], check=True, capture_output=True)
        self.git("remote", "add", "fixture", str(remote))
        path = self.root / ".harness/project.json"
        config = read_json(path)
        config["adapters"]["push"] = {"argv": [sys.executable, "{plugin_root}/adapters/git_push.py", "--remote", "fixture"], "effect": "external"}
        atomic_json(path, config)
        self.commit("Configure local remote push")
        self.flow.sync_config("Configure fixture before design")
        self.flow.configure_flow({"target": "pr", "stages": {"integration": False}}, "Push fixture for PR delivery")
        self.finish_review()
        self.flow.enter("push")
        receipt = runner.run(self.flow, "adapter", "push", authorization="Push fixture to temporary bare repo")
        self.assertEqual(receipt["status"], "passed", receipt)
        self.assertEqual(self.git("rev-parse", "refs/heads/feature/example", root=remote), self.git("rev-parse", "HEAD"))


class GitHubContractTests(RepoCase):
    def test_existing_pr_is_reused_without_create(self):
        request = {"stage": "pr", "branch": "feature/example", "head": "abc"}
        args = argparse.Namespace(repo="owner/repo", base="main", body_file="unused", title_file="unused")
        with patch.object(github, "call", return_value=[{"number": 7, "url": "https://example.test/pr/7", "headRefOid": "abc"}]) as api:
            result = github.process(request, args)
        self.assertEqual(result["external_id"], "7")
        self.assertEqual(api.call_count, 1)
        self.assertNotIn("create", api.call_args.args)

    def test_remote_head_mismatch_is_not_silently_accepted(self):
        request = {"stage": "pr", "branch": "feature/example", "head": "abc"}
        args = argparse.Namespace(repo="owner/repo", base="main", body_file="unused", title_file="unused")
        with patch.object(github, "call", return_value=[{"number": 7, "url": "url", "headRefOid": "other"}]), self.assertRaisesRegex(ValueError, "head does not match"):
            github.process(request, args)
