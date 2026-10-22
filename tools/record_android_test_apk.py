#!/usr/bin/env python3
"""Verify the built live-input APK and retain its source/byte identity in CI."""
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import zipfile


def main():
    apk = Path("native/android/app/build/outputs/apk/liveInput/app-liveInput.apk")
    output = Path("artifacts/ui/android-live-input")
    output.mkdir(parents=True, exist_ok=True)
    sdk = Path(os.environ["ANDROID_HOME"])
    candidates = list((sdk / "build-tools").glob("*/apksigner"))
    if not candidates:
        raise RuntimeError("No installed Android APK signature verifier")
    signer = max(candidates, key=lambda p: tuple(int(v) for v in re.findall(r"\d+", p.parent.name)))
    verified = subprocess.run([str(signer), "verify", "--verbose", "--print-certs", str(apk)],
                              check=True, capture_output=True, text=True)
    (output / "apk-signature.txt").write_text(verified.stdout + verified.stderr)
    badging = subprocess.check_output([str(signer.parent / "aapt"), "dump", "badging", str(apk)], text=True)
    (output / "apk-badging.txt").write_text(badging)
    package = re.search(r"package: name='([^']+)' versionCode='([^']+)' versionName='([^']+)'", badging)
    if package is None or package[1] != "com.aqss.bodyguard.prototype.liveinput":
        raise RuntimeError("APK identity is not the separate live-input test app")
    fixture_names = {path.name for path in Path("native/ios/Tests/AQSSNativeFeedbackTests/Fixtures").glob("tv-photo-*.png")}
    if not fixture_names:
        raise RuntimeError("Synthetic photo fixture inventory is unavailable")
    with zipfile.ZipFile(apk) as archive:
        poster = archive.read("res/drawable-nodpi-v4/startup_artwork.jpg")
        for name in archive.namelist():
            if name.endswith(".dex") and b"Lcom/aqss/bodyguard/uiprobe/" in archive.read(name):
                raise RuntimeError("Test observer code was packaged into the delivered APK")
            if name.rsplit("/", 1)[-1] in fixture_names:
                raise RuntimeError("Synthetic photo fixture was packaged into the delivered APK")
    poster_sha = hashlib.sha256(poster).hexdigest()
    if poster_sha != "8f15b1e42a9cf067a7458973edbe43aa9a975b82f728d5ccc47d180bcb50307c":
        raise RuntimeError("Packaged opening poster differs from the approved original")
    with apk.open("rb") as source:
        digest = hashlib.file_digest(source, "sha256").hexdigest()
    record = {
        "source_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
        "workflow_run_id": os.environ["GITHUB_RUN_ID"],
        "application_id": package[1], "version_code": int(package[2]), "version_name": package[3],
        "size_bytes": apk.stat().st_size, "sha256": digest,
        "opening_poster_sha256": poster_sha,
        "signature_verified": True,
        "test_observer_excluded": True,
        "scope": "CI-built test APK and emulator checks; no physical input/output qualification",
    }
    (output / "apk-provenance.json").write_text(json.dumps(record, indent=2) + "\n")
    print("LIVE_TEST_APK_VERIFIED " + json.dumps(record, sort_keys=True))


if __name__ == "__main__":
    main()
