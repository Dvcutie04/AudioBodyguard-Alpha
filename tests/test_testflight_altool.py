import pytest
import os
from pathlib import Path
import subprocess
import sys

from tools.testflight_altool import require_success


@pytest.mark.parametrize(('operation', 'output'), [
    ('validate', "No errors validating archive at '/tmp/app.ipa'.\n"),
    ('validate', 'VERIFY SUCCEEDED with no errors\n'),
    ('upload', "No errors uploading archive at '/tmp/app.ipa'.\n"),
    ('upload', 'UPLOAD SUCCEEDED with no errors\nDelivery UUID: example\n'),
])
def test_explicit_acceptance(operation, output):
    require_success(operation, 0, output)


@pytest.mark.parametrize('operation', ['validate', 'upload'])
@pytest.mark.parametrize('output', [
    '',
    "Running altool at path '/Applications/Xcode.app/.../altool'...",
    'VERIFY FAILED with 1 error\nValidation failed (409) Invalid bundle. No orientations were specified.',
    'UPLOAD FAILED with 1 error\nFailed to upload package.',
    'ERROR: [ContentDelivery.Uploader] Validation failed (409)',
    'UPLOAD SUCCEEDED with no errors\nERROR: contradictory rejection',
    'No errors validating archive at /tmp/app.ipa\nValidation failed (409)',
])
def test_zero_exit_without_unambiguous_acceptance_fails(operation, output):
    with pytest.raises(ValueError):
        require_success(operation, 0, output)


def test_validation_success_does_not_prove_upload():
    with pytest.raises(ValueError):
        require_success('upload', 0, 'No errors validating archive at /tmp/app.ipa')


def test_nonzero_exit_always_fails():
    with pytest.raises(ValueError):
        require_success('upload', 1, 'UPLOAD SUCCEEDED with no errors')


@pytest.mark.parametrize(('output', 'expected'), [
    ('UPLOAD FAILED with 1 error', 1),
    ('UPLOAD SUCCEEDED with no errors', 0),
])
def test_cli_propagates_apple_result_even_when_altool_exits_zero(tmp_path, output, expected):
    fake_xcrun = tmp_path / 'xcrun'
    fake_xcrun.write_text('#!/bin/sh\nprintf "%s\\n" "$FAKE_APPLE_OUTPUT"\nexit 0\n')
    fake_xcrun.chmod(0o755)
    env = dict(os.environ, PATH=str(tmp_path)+os.pathsep+os.environ['PATH'],
               ASC_KEY_ID='synthetic', ASC_ISSUER_ID='synthetic', FAKE_APPLE_OUTPUT=output)
    script = Path(__file__).resolve().parents[1] / 'tools/testflight_altool.py'
    result = subprocess.run([sys.executable, str(script), 'upload', '--ipa', '/tmp/test.ipa'],
                            env=env, capture_output=True, text=True)
    assert result.returncode == expected
    assert ('acceptance explicitly confirmed' in result.stdout) == (expected == 0)
