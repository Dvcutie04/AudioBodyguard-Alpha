"""The offline guide must match the catalog and check without rewriting files."""
import os
from pathlib import Path
import subprocess
import sys

import pytest

from tools import export_picture_guide


ROOT = Path(__file__).resolve().parents[1]


def test_stale_offline_guide_fails_check_without_overwriting(tmp_path, monkeypatch):
    (tmp_path / "contracts").mkdir()
    (tmp_path / "docs").mkdir()
    (tmp_path / "contracts/setup_guides_v1.json").write_bytes(
        (ROOT / "contracts/setup_guides_v1.json").read_bytes()
    )
    guide = tmp_path / "docs/picture-guide.html"
    guide.write_bytes(b"stale guide")
    monkeypatch.setattr(export_picture_guide, "ROOT", tmp_path)
    with pytest.raises(SystemExit, match="Regenerate"):
        export_picture_guide.build(check=True)
    assert guide.read_bytes() == b"stale guide"


def test_current_offline_guide_checks_from_cli_without_pythonpath():
    guide = ROOT / "docs/picture-guide.html"
    before = guide.read_bytes()
    result = subprocess.run(
        [sys.executable, str(ROOT / "tools/export_picture_guide.py"), "--check"],
        cwd=ROOT, env={key: value for key, value in os.environ.items() if key != "PYTHONPATH"},
        capture_output=True, text=True, timeout=10,
    )
    assert result.returncode == 0, result.stderr
    assert "OFFLINE_PICTURE_GUIDE_CURRENT" in result.stdout
    assert guide.read_bytes() == before


def test_missing_offline_guide_fails_check_without_creating_file(tmp_path, monkeypatch):
    (tmp_path / "contracts").mkdir()
    (tmp_path / "contracts/setup_guides_v1.json").write_bytes(
        (ROOT / "contracts/setup_guides_v1.json").read_bytes()
    )
    monkeypatch.setattr(export_picture_guide, "ROOT", tmp_path)
    with pytest.raises(SystemExit, match="Regenerate"):
        export_picture_guide.build(check=True)
    assert not (tmp_path / "docs/picture-guide.html").exists()
