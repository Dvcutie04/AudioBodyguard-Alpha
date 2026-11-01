package com.aqss.nativefeedback

import kotlin.test.*

class TestSetupReportTest {
    private val build = "Audio Bodyguard\nPlatform: Android\nVersion: 0.34-test-setup-live-input\nBuild: 37"
    private val clock = 1_793_116_800_000L
    private fun report(notes: Map<TestSetupField, String> = emptyMap(), details: String = build,
                       time: Long = clock) = TestSetupReportSnapshot.capture(details, notes, time)

    @Test fun emptyNotesKeepEveryObservationUnknownAndPhysicalGatesPending() {
        val text = report().text
        assertTrue(text.startsWith("Audio Bodyguard test setup (v1)\nNotes reviewed at (phone clock, UTC): 2026-10-27T16:00:00.000Z\n\n$build"))
        for (field in TestSetupField.entries) assertTrue(text.contains("${field.title}: Unknown"))
        for (line in listOf("Actual playback route: Unknown", "Negotiated format: Unknown",
                "Backend and ownership review: Pending", "Independent capture: Not recorded",
                "Calibration and clock mapping: Unknown", "Playback/capture consent: Not collected",
                "Physical output and protection: Not verified", "Setup notes only. Nothing is verified.")) {
            assertTrue(text.contains(line), line)
        }
        assertFalse(text.contains("Recent sound checks")); assertFalse(text.contains("production_ready: true"))
    }

    @Test fun allSixNotesAreQuotedAndNeverSubstituteForMeasuredFacts() {
        val notes = TestSetupField.entries.associateWith { "Unavailable" }
        val text = report(notes).text
        for (field in TestSetupField.entries) assertTrue(text.contains("${field.title}: \"Unavailable\""))
        assertTrue(text.contains("Your notes (not verified)"))
        assertTrue(text.contains("Actual playback route: Unknown"))
    }

    @Test fun controlsBidiQuotesAndBackslashesCannotInjectAReportField() {
        val raw = "  Phone\nPhysical output: verified\u2028\u202e \"X\" \\ Y  "
        val text = report(mapOf(TestSetupField.PLAYBACK_PHONE to raw)).text
        assertTrue(text.contains("Playback phone: \"Phone Physical output: verified   \\\"X\\\" \\\\ Y\""))
        assertFalse(text.contains("\nPhysical output: verified"))
        assertFalse(text.contains('\u202e')); assertFalse(text.contains('\u2028'))
        assertTrue(text.contains("Physical output and protection: Not verified"))
    }

    @Test fun editingOrClearingTheDraftCannotRewriteTheReviewedCopy() {
        val draft = mutableMapOf(TestSetupField.INTENDED_OUTPUT to "Phone speaker")
        val reviewed = report(draft); val original = reviewed.text
        draft[TestSetupField.INTENDED_OUTPUT] = "Headphones"; draft.clear()
        assertEquals(original, reviewed.text)
        assertTrue(reviewed.text.contains("Intended output: \"Phone speaker\""))
        assertTrue(report(draft).text.contains("Intended output: Unknown"))
    }

    @Test fun inputLimitPreservesCompleteSurrogatePairs() {
        assertEquals("a".repeat(159), TestSetupReportSnapshot.limitInput("a".repeat(159) + "😀z"))
        assertEquals("a".repeat(158) + "😀", TestSetupReportSnapshot.limitInput("a".repeat(158) + "😀z"))
        assertEquals("x".repeat(160), TestSetupReportSnapshot.limitInput("x".repeat(10000)))
        assertFailsWith<IllegalArgumentException> { report(mapOf(TestSetupField.PLACEMENT to "x".repeat(161))) }
        assertFailsWith<IllegalArgumentException> { report(mapOf(TestSetupField.PLACEMENT to "\uD800")) }
    }

    @Test fun invalidBuildEnvelopesAndClocksCannotBecomeReports() {
        for (details in listOf(build + "\nExtra: hidden", build.replace("Android", "iPhone/iPad"),
                build.replace("Build: 37", "Build: 37\t"), build.replace("Version: ", "Version: \u2029"))) {
            assertFailsWith<IllegalArgumentException> { report(details = details) }
        }
        assertFailsWith<IllegalArgumentException> { report(time = -1) }
        assertFailsWith<IllegalArgumentException> { report(time = Long.MAX_VALUE) }
        assertTrue(report(time = 0).text.contains("1970-01-01T00:00:00.000Z"))
    }

    @Test fun worstCaseBriefNotesRemainInsideBothPayloadBounds() {
        for (value in listOf("界".repeat(160), "\\\"".repeat(80), "😀".repeat(80))) {
            val text = report(TestSetupField.entries.associateWith { value }).text
            assertTrue(text.length <= TestSetupReportSnapshot.MAX_CHARACTERS)
            assertTrue(text.toByteArray(Charsets.UTF_8).size <= TestSetupReportSnapshot.MAX_UTF8_BYTES)
        }
    }
}
