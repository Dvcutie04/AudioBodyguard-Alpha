"""Host verification keeps exact native bytes and exports Xcode legacy objects."""
import contextlib
import importlib
import io
import json
from pathlib import Path
import plistlib
import subprocess
import tempfile
import unittest
from unittest.mock import patch


class TestReviewedClipboard(unittest.TestCase):
    def check_script(self, kind, *, mismatch=False, export_failure=False, duplicate=False, changed_original=False):
        module = importlib.import_module('tools.check_ios_' + kind + '_clipboard')
        metadata = 'Audio Bodyguard\nPlatform: iPhone/iPad\nVersion: 0.38.0\nBuild: 1\n'
        boundary = 'Actual playback route: Unknown\nPhysical output and protection: Not verified\n'
        original = ('Audio Bodyguard iPhone output details (v1)\n' + metadata + boundary).encode()
        payload = original if kind == 'output_details' else (
            ('Audio Bodyguard test setup (' + ('v2' if kind == 'combined_setup' else 'v1') + ')\n' + metadata + boundary).encode()
            + (original if kind == 'combined_setup' else b''))
        names = {'test_setup': 'Test setup reviewed text', 'output_details': 'Output details reviewed text',
                 'combined_setup': 'Combined setup reviewed text'}
        attachments = [{'name': {'_value': names[kind]}, 'payloadRef': {'id': {'_value': 'review'}}}]
        if kind == 'combined_setup':
            attachments.append({'name': {'_value': 'Included output details reviewed text'}, 'payloadRef': {'id': {'_value': 'original'}}})
        if duplicate:
            attachments.append({'name': {'_value': names[kind]}, 'payloadRef': {'id': {'_value': 'ambiguous'}}})
        exports = []

        def run(command, **kwargs):
            if command[:3] == ['xcrun', 'xcresulttool', 'get']:
                return subprocess.CompletedProcess(command, 0, json.dumps(attachments))
            self.assertEqual(command[:3], ['xcrun', 'xcresulttool', 'export'])
            self.assertIn('--legacy', command, 'Xcode 26 requires explicit legacy object export')
            self.assertEqual(command[command.index('--type') + 1], 'file')
            exports.append(command)
            if export_failure:
                raise subprocess.CalledProcessError(64, command)
            data = (original + (b'changed' if changed_original else b'')) if command[command.index('--id') + 1] == 'original' else payload
            Path(command[command.index('--output-path') + 1]).write_bytes(data)
            return subprocess.CompletedProcess(command, 0)

        def output(command, **kwargs):
            if command[:3] == ['xcrun', 'simctl', 'pbpaste']:
                return payload + (b'changed' if mismatch else b'')
            self.assertEqual(command, ['git', 'rev-parse', 'HEAD'])
            return 'a' * 40

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            info = root / 'Info.plist'
            info.write_bytes(plistlib.dumps({'CFBundleShortVersionString': '0.38.0', 'CFBundleVersion': '1'}))
            destination = root / 'output'
            with contextlib.ExitStack() as stack:
                stack.enter_context(patch('sys.argv', ['check', 'isolated-simulator', str(root / 'test.xcresult'), str(info), str(destination)]))
                stack.enter_context(patch.object(module.subprocess, 'run', side_effect=run))
                stack.enter_context(patch.object(module.subprocess, 'check_output', side_effect=output))
                stack.enter_context(contextlib.redirect_stdout(io.StringIO()))
                if kind == 'combined_setup':
                    stack.enter_context(patch.object(module, 'verify_native_setup_intake', return_value={'qualified': False}))
                if mismatch or duplicate or changed_original:
                    with self.assertRaisesRegex(AssertionError, 'Native clipboard differs|Require one|Combined report did not retain'):
                        module.main()
                elif export_failure:
                    with self.assertRaises(subprocess.CalledProcessError):
                        module.main()
                else:
                    module.main()
            receipts = list(destination.glob('*receipt.json'))
            if mismatch or export_failure or duplicate or changed_original:
                self.assertEqual(receipts, [], 'Never issue a receipt when independent verification fails')
            else:
                self.assertEqual(len(receipts), 1)
                receipt = json.loads(receipts[0].read_text())
                self.assertTrue(receipt['exact_preview_match'])
                self.assertEqual(receipt['bytes'], len(payload))
                self.assertEqual(len(exports), 2 if kind == 'combined_setup' else 1)

    def test_exact_native_payloads_export_with_legacy_flag(self):
        for kind in ('test_setup', 'output_details', 'combined_setup'):
            with self.subTest(kind=kind):
                self.check_script(kind)

    def test_changed_native_clipboard_never_passes(self):
        for kind in ('test_setup', 'output_details', 'combined_setup'):
            with self.subTest(kind=kind):
                self.check_script(kind, mismatch=True)

    def test_export_failure_never_passes(self):
        for kind in ('test_setup', 'output_details', 'combined_setup'):
            with self.subTest(kind=kind):
                self.check_script(kind, export_failure=True)

    def test_ambiguous_review_never_passes(self):
        for kind in ('test_setup', 'output_details', 'combined_setup'):
            with self.subTest(kind=kind):
                self.check_script(kind, duplicate=True)

    def test_changed_original_snapshot_never_passes(self):
        self.check_script('combined_setup', changed_original=True)
