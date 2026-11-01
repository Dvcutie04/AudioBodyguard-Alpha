package com.aqss.nativefeedback

import kotlin.test.*

class SetupOutputReportTest {
    private val build = "Audio Bodyguard\nPlatform: Android\nVersion: 0.35-setup-output-live-input\nBuild: 38"
    private val clock = 1_793_116_800_000L
    private fun output(details: String = build, inventory: OutputDeviceInventory = OutputDeviceInventory.from(listOf(
        OutputDeviceAdvertisement("Built-in speaker", listOf(48000), listOf(2), listOf("PCM 16-bit"))))) =
        OutputInventoryReportSnapshot.capture(details, "Maker", "Phone", "16", 36, clock, true, inventory)
    private fun combined(snapshot: OutputInventoryReportSnapshot, notes: Map<TestSetupField, String> = emptyMap()) =
        TestSetupReportSnapshot.capture(build, notes, clock + 120_000, outputReport = snapshot)

    @Test fun combinedReportIncludesTheExactDatedOutputCopyAndSeparateNotesTime() {
        val original = output()
        val text = combined(original, mapOf(TestSetupField.OBSERVER_PHONE to "iPhone")).text
        assertTrue(text.startsWith("Audio Bodyguard test setup (v1)\nNotes reviewed at (phone clock, UTC): 2026-10-27T16:02:00.000Z"))
        assertTrue(text.endsWith("\n\nAttached output snapshot\nSnapshot only. Outputs may have changed.\n\n" + original.text))
        assertTrue(text.contains("Read finished at (phone clock, UTC): 2026-10-27T16:00:00Z"))
        assertTrue(text.contains("Second phone: \"iPhone\""))
        assertTrue(text.contains("Actual playback route: Unknown"))
        assertTrue(text.contains("Selected playback route: Unknown"))
        assertTrue(text.contains("Playback/capture consent: Not collected"))
        assertTrue(text.contains("Physical output and protection: Not verified"))
    }

    @Test fun noAttachmentKeepsTheExistingStandaloneReportAndItsSmallerBounds() {
        val standalone = TestSetupReportSnapshot.capture(build, emptyMap(), clock)
        val explicit = TestSetupReportSnapshot.capture(build, emptyMap(), clock, outputReport = null)
        assertEquals(standalone.text, explicit.text)
        assertFalse(explicit.text.contains("Attached output snapshot"))
        assertTrue(explicit.text.length <= TestSetupReportSnapshot.MAX_CHARACTERS)
    }

    @Test fun anotherInstalledBuildCannotBeAttached() {
        val old = output(build.replace("Build: 38", "Build: 37"))
        assertFailsWith<IllegalArgumentException> { combined(old) }
        val otherVersion = output(build.replace("0.35-setup-output", "0.34-test-setup"))
        assertFailsWith<IllegalArgumentException> { combined(otherVersion) }
    }

    @Test fun draftEditsAndLaterInventoriesCannotRewriteTheCombinedReview() {
        val notes = mutableMapOf(TestSetupField.INTENDED_OUTPUT to "Phone speaker")
        val first = combined(output(), notes); val frozen = first.text
        notes.clear()
        val later = output(inventory = OutputDeviceInventory.from(emptyList()))
        assertEquals(frozen, first.text)
        assertTrue(first.text.contains("1. Built-in speaker"))
        assertFalse(combined(later).text.contains("1. Built-in speaker"))
    }

    @Test fun aLargeValidOutputAndWorstCaseNotesStayInsideCombinedBounds() {
        val dense = OutputDeviceInventory.from(List(16) {
            OutputDeviceAdvertisement("Built-in speaker", listOf(48000), listOf(2), listOf("x".repeat(1024)))
        })
        val original = output(inventory = dense)
        val report = combined(original, TestSetupField.entries.associateWith { "界".repeat(160) })
        assertTrue(report.text.endsWith(original.text))
        assertTrue(report.text.length > TestSetupReportSnapshot.MAX_CHARACTERS)
        assertTrue(report.text.length <= TestSetupReportSnapshot.MAX_COMBINED_CHARACTERS)
        assertTrue(report.text.toByteArray(Charsets.UTF_8).size <= TestSetupReportSnapshot.MAX_COMBINED_UTF8_BYTES)
    }

    @Test fun attachmentCannotBypassTheOriginalNoteAndClockValidation() {
        assertFailsWith<IllegalArgumentException> { combined(output(), mapOf(TestSetupField.PLACEMENT to "x".repeat(161))) }
        assertFailsWith<IllegalArgumentException> { TestSetupReportSnapshot.capture(build, emptyMap(), -1, outputReport = output()) }
        assertFailsWith<IllegalArgumentException> { combined(output(), mapOf(TestSetupField.PLACEMENT to "\uD800")) }
    }

    @Test fun handoffIsOneUseAndReplacementRejectsTheOldTicket() {
        val handoff = SetupOutputReportHandoff()
        val old = output(); val oldTicket = handoff.offer(old)
        val latest = output(inventory = OutputDeviceInventory.from(emptyList()))
        val latestTicket = handoff.offer(latest)
        assertNotEquals(oldTicket, latestTicket)
        assertNull(handoff.take(oldTicket))
        assertSame(latest, handoff.take(latestTicket))
        assertNull(handoff.take(latestTicket))
    }

    @Test fun launchFailureDiscardsOnlyItsOwnHandoff() {
        val handoff = SetupOutputReportHandoff()
        val old = handoff.offer(output()); val current = output(); val latest = handoff.offer(current)
        handoff.discard(old)
        assertSame(current, handoff.take(latest))
        val failed = handoff.offer(output()); handoff.discard(failed)
        assertNull(handoff.take(failed))
    }

    @Test fun aNewProcessOwnerCannotRestoreAnOldAttachmentFromItsTicket() {
        val old = SetupOutputReportHandoff().offer(output())
        val fresh = SetupOutputReportHandoff()
        assertNull(fresh.take(old))
        val current = output(); val currentTicket = fresh.offer(current)
        assertNull(fresh.take(old))
        assertSame(current, fresh.take(currentTicket))
    }
}
