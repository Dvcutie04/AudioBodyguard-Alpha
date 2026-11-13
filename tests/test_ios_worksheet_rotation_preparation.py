"""Generator contracts, not native iPad or Share qualification."""
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / "tools/prepare_ios_worksheet_rotation_test.py"
spec = importlib.util.spec_from_file_location("rotation_preparation", SCRIPT)
repair = importlib.util.module_from_spec(spec)
spec.loader.exec_module(repair)


class WorksheetRotationPreparationTests(unittest.TestCase):
    def original(self):
        return ("// authored generator fixture before\n" + repair.ANCHOR +
                '        XCTAssertEqual(preview.label, reviewed)\n// after\n').encode()

    def test_repair_only_changes_the_one_preserved_rotation_sequence(self):
        original = self.original()
        patched = repair.transform(original, repair.git_blob_sha(original))
        self.assertEqual(patched.decode().replace(repair.REPLACEMENT, repair.ANCHOR, 1), original.decode())
        self.assertEqual(patched.count(b'reviewAfterRotation.tap()'), 1)
        self.assertIn(b'XCTAssertEqual(preview.label, reviewed)', patched)
        self.assertIn(b'preview.waitForExistence(timeout: 5)', patched)
        self.assertIn(b'timeout: 3', patched)
        self.assertIn(b'button.width >= 44, button.height >= 44', patched)
        self.assertIn(b'now - since >= 0.25', patched)
        self.assertIn(b'lastReadiness', patched)
        self.assertIn(b'readinessSamples', patched)
        self.assertIn(b'last observation:', patched)
        self.assertNotIn(b'sleep(', patched)
        self.assertNotIn(b'XCTSkip', patched)

    def test_unknown_source_and_duplicate_anchor_are_rejected(self):
        original = self.original()
        with self.assertRaises(ValueError):
            repair.transform(original)
        doubled = original + repair.ANCHOR.encode()
        with self.assertRaises(ValueError):
            repair.transform(doubled, repair.git_blob_sha(doubled))

    def test_missing_anchor_is_rejected(self):
        source = b'// different test\n'
        with self.assertRaises(ValueError):
            repair.transform(source, repair.git_blob_sha(source))

    def test_failed_preparation_does_not_change_source_or_write_receipt(self):
        with tempfile.TemporaryDirectory() as temp:
            source, receipt = Path(temp) / 'Tests.swift', Path(temp) / 'receipt.json'
            original = self.original(); source.write_bytes(original)
            with self.assertRaises(ValueError):
                repair.prepare(source, receipt)
            self.assertEqual(source.read_bytes(), original)
            self.assertFalse(receipt.exists())

    def test_compiled_test_identity_is_separate_and_reapplication_fails(self):
        with tempfile.TemporaryDirectory() as temp:
            source, receipt = Path(temp) / 'Tests.swift', Path(temp) / 'receipt.json'
            original = self.original(); source.write_bytes(original)
            repair.prepare(source, receipt, repair.git_blob_sha(original))
            record = json.loads(receipt.read_text())
            self.assertEqual(record['original_test_blob'], repair.git_blob_sha(original))
            self.assertEqual(record['compiled_test_blob'], repair.git_blob_sha(source.read_bytes()))
            self.assertNotEqual(record['original_test_blob'], record['compiled_test_blob'])
            self.assertEqual(record['compiled_test_sha256'], hashlib.sha256(source.read_bytes()).hexdigest())
            self.assertEqual(record['native_execution'], 'UNRUN at source preparation')
            with self.assertRaises(ValueError):
                repair.prepare(source, receipt, repair.git_blob_sha(original))


if __name__ == '__main__':
    unittest.main()
