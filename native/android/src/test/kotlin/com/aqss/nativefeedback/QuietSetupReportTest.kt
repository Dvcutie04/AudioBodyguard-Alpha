package com.aqss.nativefeedback

import kotlin.test.*

class QuietSetupReportTest {
    private val build = "Audio Bodyguard\nPlatform: Android\nVersion: 0.37-quiet-setup-live-input\nBuild: 40"
    private val clock = 1_793_116_800_000L
    private fun result(label: String = "00000000-0000-4000-8000-000000000001") = QuietOutputResult(
        runId = label, reason = QuietStop.COMPLETE, acceptedSamples = 256, attempts = 1,
        cleanupSucceeded = true, quarantined = false, allocationEntered = true, trackOpened = true,
        focusGranted = true, zeroGainAccepted = true,
        constructed = QuietOutputFormat(true, 48000, 1, true, 256, 256),
        routes = QuietOutputRoutes.from(listOf(2), 1, true), requestedBufferBytes = 512,
        unreportedCall = false, trace = emptyList(),
    )
    private fun quiet(details: String = build, label: String = "00000000-0000-4000-8000-000000000001") =
        QuietOutputReportSnapshot.capture(details, result(label), clock)
    private fun inventory() = OutputInventoryReportSnapshot.capture(build, "Maker", "Phone", "16", 36,
        clock, true, OutputDeviceInventory.from(emptyList()))
    private fun combined(source: QuietOutputReportSnapshot, notes: Map<TestSetupField, String> = emptyMap()) =
        TestSetupReportSnapshot.capture(build, notes, clock + 120_000, quietReport = source)

    @Test fun exactQuietReportAndItsOriginalReviewTimeAreRetainedOnce() {
        val original = quiet()
        val text = combined(original, mapOf(TestSetupField.INTENDED_OUTPUT to "Phone speaker")).text
        assertTrue(text.startsWith("Audio Bodyguard test setup (v2)\nNotes reviewed at (phone clock, UTC): 2026-10-27T16:02:00.000Z"))
        assertTrue(text.endsWith(original.text)); assertEquals(2, text.split(original.text).size)
        assertTrue(text.contains("Attached quiet check report"))
        assertTrue(text.contains("Reviewed at (phone clock, UTC): 2026-10-27T16:00:00.000Z"))
        assertTrue(text.contains("Intended output: \"Phone speaker\""))
        assertEquals(build, original.buildDetails)
    }

    @Test fun frameworkCountsNeverResolveThePhysicalAndConsentUnknowns() {
        val text = combined(quiet()).text
        for (line in listOf("Known accepted samples: 256", "Physical output and protection: Not verified",
            "Actual playback route: Unknown", "Negotiated format: Unknown", "Independent capture: Not recorded",
            "Playback/capture consent: Not collected", QuietOutputReportSnapshot.NOTICE)) assertTrue(text.contains(line), line)
    }

    @Test fun theTwoReportKindsCannotBeMixedInOneAttachmentSlot() {
        assertFailsWith<IllegalArgumentException> {
            TestSetupReportSnapshot.capture(build, emptyMap(), clock, outputReport = inventory(), quietReport = quiet())
        }
    }

    @Test fun mismatchedInstalledBuildOrVersionIsRejected() {
        for (details in listOf(build.replace("Build: 40", "Build: 39"), build.replace("0.37", "0.36"))) {
            assertFailsWith<IllegalArgumentException> { combined(quiet(details)) }
        }
    }

    @Test fun oldStandaloneAndInventoryReportsKeepTheirOriginalEnvelopes() {
        val plain = TestSetupReportSnapshot.capture(build, emptyMap(), clock)
        val explicit = TestSetupReportSnapshot.capture(build, emptyMap(), clock, quietReport = null)
        assertEquals(plain.text, explicit.text); assertTrue(plain.text.startsWith("Audio Bodyguard test setup (v1)"))
        val source = inventory()
        val attached = TestSetupReportSnapshot.capture(build, emptyMap(), clock, outputReport = source)
        assertTrue(attached.text.startsWith("Audio Bodyguard test setup (v1)")); assertTrue(attached.text.endsWith(source.text))
        assertFalse(attached.text.contains("Attached quiet check report"))
    }

    @Test fun clearNotesKeepsQuietDataAndRemovingQuietDataKeepsNotes() {
        val original = quiet()
        val cleared = combined(original)
        assertTrue(cleared.text.endsWith(original.text)); assertTrue(cleared.text.contains("Intended output: Unknown"))
        val removed = TestSetupReportSnapshot.capture(build, mapOf(TestSetupField.INTENDED_OUTPUT to "Phone speaker"), clock)
        assertTrue(removed.text.contains("Intended output: \"Phone speaker\"")); assertFalse(removed.text.contains(original.text))
    }

    @Test fun laterNoteEditsCannotRewriteTheReviewedCombination() {
        val notes = mutableMapOf(TestSetupField.CONSTRAINTS to "No calibration")
        val report = combined(quiet(), notes); val frozen = report.text; notes.clear()
        assertEquals(frozen, report.text); assertTrue(report.text.contains("Setup constraints: \"No calibration\""))
    }

    @Test fun anAttachmentCannotBypassNoteOrClockValidation() {
        assertFailsWith<IllegalArgumentException> { combined(quiet(), mapOf(TestSetupField.PLACEMENT to "x".repeat(161))) }
        assertFailsWith<IllegalArgumentException> { combined(quiet(), mapOf(TestSetupField.PLACEMENT to "\uD800")) }
        assertFailsWith<IllegalArgumentException> { TestSetupReportSnapshot.capture(build, emptyMap(), -1, quietReport = quiet()) }
    }

    @Test fun aSyntheticNearCapacityReportAndWorstCaseNotesFitTheExplicitCombinedBound() {
        // Synthetic renderer fixture, not a worker's UUID or a physical observation.
        val original = quiet(label = "x".repeat(28_000))
        val text = combined(original, TestSetupField.entries.associateWith { "界".repeat(160) }).text
        assertTrue(text.endsWith(original.text))
        assertTrue(text.length <= TestSetupReportSnapshot.MAX_QUIET_COMBINED_CHARACTERS)
        assertTrue(text.toByteArray(Charsets.UTF_8).size <= TestSetupReportSnapshot.MAX_QUIET_COMBINED_UTF8_BYTES)
    }

    @Test fun typedHandoffIsSingleUseAndRejectsMissingOrForeignTickets() {
        val handoff = SetupReportHandoff(); val attachment = SetupReportAttachment.Quiet(quiet())
        val ticket = handoff.offer(attachment)
        assertNull(handoff.take(null)); assertNull(handoff.take("foreign"))
        assertSame(attachment, handoff.take(ticket)); assertNull(handoff.take(ticket))
    }

    @Test fun replacingAnInventoryWithAQuietReportRetiresTheOldTicket() {
        val handoff = SetupReportHandoff()
        val old = handoff.offer(SetupReportAttachment.Inventory(inventory()))
        val current = SetupReportAttachment.Quiet(quiet()); val ticket = handoff.offer(current)
        assertNotEquals(old, ticket); assertNull(handoff.take(old)); assertSame(current, handoff.take(ticket))
    }

    @Test fun staleDiscardCannotEraseTheCurrentTypedAttachment() {
        val handoff = SetupReportHandoff()
        val old = handoff.offer(SetupReportAttachment.Quiet(quiet()))
        val current = SetupReportAttachment.Inventory(inventory()); val ticket = handoff.offer(current)
        handoff.discard(old); assertSame(current, handoff.take(ticket))
    }

    @Test fun aFreshProcessOrExplicitDiscardCannotRestoreAnOldReport() {
        val old = SetupReportHandoff(); val ticket = old.offer(SetupReportAttachment.Quiet(quiet()))
        assertNull(SetupReportHandoff().take(ticket))
        old.discard(ticket); assertNull(old.take(ticket))
    }
}
