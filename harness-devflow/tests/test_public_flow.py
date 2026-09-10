"""Public CLI professional handoff: actual recon collection, design inputs and guided delivery."""
from pathlib import Path

from harness.storage import atomic_json, read_json
import test_host_execution as support
from test_workflow import RepoCase


# Reuse fixture utilities without inheriting the parent's test methods.
class PublicProfessionalFlowTests(RepoCase):
    cli = support.PortableExecutionTests.cli
    body = support.PortableExecutionTests.body
    checkpoint = support.PortableExecutionTests.checkpoint

    def test_public_standard_backend_flow_reuses_recon_and_finishes_guided_implementation(self):
        self.flow.configure_flow({"profile": "standard", "domain": "backend", "assistance": "guided", "isolation": "checkout",
                                  "stages": {"design_approval": False, "interfaces": False, "integration": False}},
                                 "Standard backend workflow with bundled methods")
        self.cli("next")
        recon = self.cli("use-skill", "recon", "--reason", "Read the existing value contract")
        collected = self.cli("collect-recon", "--scope", ".", "--keyword", "value")
        self.assertEqual(collected["status"], "passed")
        baseline = Path(recon["output_directory"]) / "report.md"
        baseline.write_text("# Existing value contract\nbase.value returns 1; tests/test_base.py asserts it.\nThe new feature must preserve base.value.\n")
        result_path = self.root / ".harness/runs/example/artifacts/recon-result.json"
        atomic_json(result_path, {"status": "pass", "summary": "Read and checked the existing contract", "artifacts": [str(baseline)],
                                  "details": {"phase": "design", "readiness": "READY"}, "tool_runs": [collected["id"]]})
        self.cli("record-skill", "recon", "--result", str(result_path))
        intake = self.body("intake", artifacts=[str(baseline)], details={"acceptance": ["AC-1"], "modules": [{"id": "core", "acceptance": ["AC-1"]}]})
        self.cli("submit", "--result", str(intake))
        self.cli("next")
        design = self.cli("use-skill", "design", "--reason", "Design the feature while preserving the baseline")
        request = read_json(Path(design["request"]))
        self.assertIn(str(baseline), request["input_artifacts"])
        self.assertTrue(request["input_reports"])
        document = Path(design["output_directory"]) / "design.md"
        document.write_text(f"# Feature design\nKeep base.value returning 1. Add feature_core.value returning 2.\nRead baseline: {baseline}\nVerify both contracts with unit tests.\n")
        design_result = self.root / ".harness/runs/example/artifacts/design-result.json"
        atomic_json(design_result, {"status": "pass", "summary": "Defined the feature and regression boundary", "artifacts": [str(document)]})
        self.cli("record-skill", "design", "--result", str(design_result))
        self.cli("submit", "--result", str(self.body("design", artifacts=[str(document)], details={"designs": {"core": str(document)}})))
        self.cli("next")
        audit = self.cli("use-skill", "design_audit", "--reason", "Check the baseline and acceptance coverage")
        audit_doc = Path(audit["output_directory"]) / "audit.md"
        audit_doc.write_text("# Audit\nChecked the unchanged base contract and the new feature expectation; unit tests cover both.\n")
        audit_result = self.root / ".harness/runs/example/artifacts/audit-result.json"
        atomic_json(audit_result, {"status": "pass", "summary": "Checked design coverage", "artifacts": [str(audit_doc)], "findings": []})
        self.cli("record-skill", "design_audit", "--result", str(audit_result))
        self.cli("submit", "--result", str(self.body("design_audit", artifacts=[str(audit_doc)])))
        self.cli("submit", "--result", str(self.body("test_design", details={"scenarios": [{"id": "S-1", "acceptance": ["AC-1"]}]})))
        tasks = self.root / ".harness/runs/example/artifacts/tasks.json"
        atomic_json(tasks, {"core": [{"id": "build", "summary": "Implement feature_core without changing base", "acceptance": ["AC-1"], "verification": "Run the base and feature unit tests"}]})
        self.cli("plan", "--tasks", str(tasks))
        self.cli("next")
        _, receipt = self.implement_module()
        self.checkpoint(receipt)
        module = self.body("implement", completed_tasks=["build"], acceptance=["AC-1"], checks=[receipt["id"]])
        self.cli("submit-module", "core", "--result", str(module))
        self.cli("submit", "--result", str(self.body("implement")))
        self.cli("next")
        self.cli("run-check", "unit")
        final = self.cli("submit", "--result", str(self.body("review")))
        self.assertEqual(final["status"], "complete")
        self.assertEqual(len(self.flow.load()["capability_uses"]), 3)
        self.assertEqual((self.root / "base.py").read_text(), "def value():\n    return 1\n")
