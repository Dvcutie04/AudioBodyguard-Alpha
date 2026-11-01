#!/usr/bin/env python3
"""Bind each software UI suite to metadata from its compiled Simulator app.

Capture, permission-change and imported-photo cases retain their dedicated
fixture workflows. A separate native job checks the connected appearance demo.
"""
import argparse
import json
from pathlib import Path
import plistlib
import re
import subprocess


ROOT = Path(__file__).resolve().parents[1]
TESTS = ROOT / "native/ios-app/UITests"


def suites():
    config = json.loads((TESTS / "software-ui-suites.json").read_text())
    actual = set()
    for path in TESTS.glob("*.swift"):
        source = path.read_text()
        name = re.search(r"final class (\w+): XCTestCase", source).group(1)
        actual.update(name + "/" + test for test in re.findall(r"^    func (test\w+)\(", source, re.M))
    assigned = [test for group in config["suites"].values() for test in group]
    assigned += config["dedicated_fixture_tests"]
    if len(assigned) != len(set(assigned)) or set(assigned) != actual:
        raise ValueError(f"UI suite inventory mismatch: missing={actual-set(assigned)}, stale={set(assigned)-actual}")
    return config["suites"]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("products", nargs="?", type=Path)
    parser.add_argument("suite", nargs="?")
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--run", nargs=2, metavar=("SIMULATOR", "RESULT"))
    args = parser.parse_args()
    groups = suites()
    if args.check:
        print(json.dumps({name: len(tests) for name, tests in groups.items()}, sort_keys=True))
        return
    if args.products is None or args.suite not in groups:
        parser.error("Provide a compiled Products directory and a known software UI suite")
    products = args.products
    candidates = list(products.glob("*.xctestrun"))
    if len(candidates) != 1:
        raise ValueError("Require exactly one original compiled test-run file")
    data = plistlib.loads(candidates[0].read_bytes())
    info = plistlib.loads((products / "Release-iphonesimulator/AQSSReadOnly.app/Info.plist").read_bytes())
    targets = [target for target in data.values() if isinstance(target, dict) and target.get("IsUITestBundle")]
    if len(targets) != 1:
        raise ValueError("Require exactly one UI test target")
    target = targets[0]
    environment = target.setdefault("EnvironmentVariables", {})
    environment["AQSS_TEST_APP_VERSION"] = info["CFBundleShortVersionString"]
    environment["AQSS_TEST_APP_BUILD"] = info["CFBundleVersion"]
    destination = products / f"software-{args.suite}.xctestrun"
    destination.write_bytes(plistlib.dumps(data))
    print(f"Prepared {len(groups[args.suite])} {args.suite} tests from compiled app metadata")
    if args.run:
        simulator, result = args.run
        subprocess.run([
            "xcodebuild", "test-without-building", "-xctestrun", str(destination),
            "-destination", f"platform=iOS Simulator,id={simulator}",
            "-parallel-testing-enabled", "NO", "-resultBundlePath", result,
            *("-only-testing:AQSSReadOnlyUITests/" + test for test in groups[args.suite]),
        ], check=True)


if __name__ == "__main__":
    main()
