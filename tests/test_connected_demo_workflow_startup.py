"""Shell-orchestration regressions; these mocks do not qualify a native Simulator.

The real XCUITest and artifact checks remain in read-only-ui-smoke.yml. These
unit tests prove boot failures and XCTest failures cannot become shell success.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import textwrap
import unittest


WORKFLOW = Path(__file__).resolve().parents[1] / ".github/workflows/read-only-ui-smoke.yml"
STEP_NAME = "Test connected appearance without changing physical readiness"
TEST_SELECTOR = (
    "-only-testing:AQSSReadOnlyUITests/AQSSReadOnlyUITests/"
    "testConnectedDemoAppearanceKeepsPhysicalReadinessUnverified"
)


def connected_job() -> str:
    text = WORKFLOW.read_text(encoding="utf-8")
    return text.split("  ios-connected-demo:\n", 1)[1].split("\n  android-emulator:", 1)[0]


def extract_test_script() -> str:
    step = connected_job().split("      - name: " + STEP_NAME + "\n", 1)[1]
    step = step.split("\n      - name:", 1)[0]
    return textwrap.dedent(step.split("        run: |\n", 1)[1])


class ConnectedDemoWorkflowStartupTests(unittest.TestCase):
    def run_script(self, boot_exit: int = 0, xcode_exit: int = 0):
        with tempfile.TemporaryDirectory(prefix="aqss-workflow-unit-") as temp:
            root = Path(temp)
            binary = root / "bin"
            binary.mkdir()
            commands = root / "commands.jsonl"
            stub = "#!" + sys.executable + "\n" + textwrap.dedent("""\
                import json, os, pathlib, sys
                name = pathlib.Path(sys.argv[0]).name
                args = sys.argv[1:]
                with open(os.environ["COMMAND_LOG"], "a", encoding="utf-8") as log:
                    log.write(json.dumps([name] + args) + "\\n")
                if name == "xcrun" and args == ["simctl", "list", "devices", "available", "-j"]:
                    print(json.dumps({"devices": {"fixture-runtime": [
                        {"name": "iPhone fixture", "udid": "fixture-udid", "isAvailable": True}
                    ]}}))
                elif name == "xcrun" and args == ["simctl", "bootstatus", "fixture-udid", "-b"]:
                    raise SystemExit(int(os.environ["BOOT_EXIT"]))
                elif name == "xcodebuild":
                    print("mock XCTest output: orchestration only")
                    raise SystemExit(int(os.environ["XCODE_EXIT"]))
                else:
                    raise SystemExit("Unexpected command: " + repr([name] + args))
                """)
            for name in ("xcrun", "xcodebuild"):
                path = binary / name
                path.write_text(stub, encoding="utf-8")
                path.chmod(0o700)
            env = dict(os.environ, PATH=str(binary) + os.pathsep + os.environ["PATH"],
                       RUNNER_TEMP=str(root), COMMAND_LOG=str(commands),
                       BOOT_EXIT=str(boot_exit), XCODE_EXIT=str(xcode_exit))
            result = subprocess.run(["bash", "-c", extract_test_script()], env=env,
                                    text=True, capture_output=True, timeout=10)
            calls = [json.loads(line) for line in commands.read_text().splitlines()]
            saved = root / "aqss-connected-demo-xcodebuild.log"
            return result, calls, saved.read_text() if saved.exists() else None

    def test_boot_readiness_precedes_the_unchanged_native_test(self):
        result, calls, _ = self.run_script()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(calls[1], ["xcrun", "simctl", "bootstatus", "fixture-udid", "-b"])
        self.assertEqual(calls[2][0], "xcodebuild")
        self.assertIn(TEST_SELECTOR, calls[2])
        self.assertIn("platform=iOS Simulator,id=fixture-udid", calls[2])
        parallel = calls[2].index("-parallel-testing-enabled")
        self.assertEqual(calls[2][parallel + 1], "NO")
        self.assertIn("CODE_SIGNING_ALLOWED=NO", calls[2])

    def test_boot_failure_prevents_xctest(self):
        result, calls, _ = self.run_script(boot_exit=23)
        self.assertEqual(result.returncode, 23, result.stdout + result.stderr)
        self.assertFalse(any(call[0] == "xcodebuild" for call in calls))

    def test_xctest_failure_survives_log_capture(self):
        result, _, saved = self.run_script(xcode_exit=65)
        self.assertEqual(result.returncode, 65, result.stdout + result.stderr)
        self.assertIsNotNone(saved)
        self.assertIn("mock XCTest output", saved)

    def test_existing_timeout_and_source_gate_are_preserved(self):
        job = connected_job()
        self.assertIn("    timeout-minutes: 20\n", job)
        self.assertIn("          persist-credentials: false\n", job)
        self.assertIn("          ref: ${{ inputs.source_revision || '' }}\n", job)
        self.assertNotIn("continue-on-error", job)
        self.assertNotIn("-retry-tests-on-failure", job)
        self.assertEqual(job.count(TEST_SELECTOR), 1)

    def test_native_result_and_startup_log_are_retained_on_failure(self):
        job = connected_job()
        header = "      - name: Keep connected-demo native results and startup log\n"
        self.assertIn(header, job)
        retention = job.split(header, 1)[1]
        retention = retention.split("\n      - name:", 1)[0]
        self.assertIn("        if: always()\n", retention)
        self.assertIn("${{ runner.temp }}/aqss-connected-demo.xcresult", retention)
        self.assertIn("${{ runner.temp }}/aqss-connected-demo-xcodebuild.log", retention)
        self.assertIn("          if-no-files-found: error\n", retention)


if __name__ == "__main__":
    unittest.main()
