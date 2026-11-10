"""Require every current iPhone/iPad UI test to have exactly one reusable-suite assignment.

This test catches newly added native UI cases missed by the hosted software UI
suites; the separate TV-guide workflow may pass even when that inventory drifts.
"""
from tools.prepare_ios_software_ui import suites


def test_every_native_ui_case_is_in_the_software_suite_inventory():
    groups = suites()  # Rejects missing, stale, or duplicate native test assignments.
    assert "AQSSReadOnlyUITests/testSonyLegacyAndHisenseVIDAAKeepTheirOwnPicturesAndBack" in groups["pictures"]
    assert "AQSSReadOnlyUITests/testTVNetworkRejectedReportCancelPreservesClipboard" in groups["tools"]
    assert "AQSSReadOnlyUITests/testTVNetworkRejectedReportCopyMatchesActualReviewedText" in groups["tools"]
