package com.aqss.nativefeedback

import kotlin.test.*

class OutputInventoryReportTest {
    private val build = "Audio Bodyguard\nPlatform: Android\nVersion: 0.33-output-report-live-input\nBuild: 36"
    private val clock = 1_793_116_800_000L // 2026-10-27T16:00:00Z; phone clock only.
    private fun inventory() = OutputDeviceInventory.from(listOf(
        OutputDeviceAdvertisement("Built-in speaker", listOf(48000), listOf(2), listOf("PCM 16-bit"))))
    private fun report(inventory: OutputDeviceInventory = inventory(), details: String = build,
                       manufacturer: String = "Maker", model: String = "Phone",
                       release: String = "16", api: Int = 36, captured: Long = clock,
                       notices: Boolean = true) = OutputInventoryReportSnapshot.capture(
        details, manufacturer, model, release, api, captured, notices, inventory)

    @Test fun capturedTextContainsOnlyTheReviewedMetadataAndExplicitUnknowns() {
        val text = report().text
        assertTrue(text.startsWith("Audio Bodyguard output inventory (v1)\nCaptured at (phone clock, UTC): 2026-10-27T16:00:00Z\n\n$build"))
        assertTrue(text.contains("Phone: Maker Phone\nAndroid: 16 · API 36"))
        assertTrue(text.contains("1 available output device reported.\n\n1. Built-in speaker\nAdvertised sample rates: 48000 Hz\nAdvertised channel counts: 2\nAdvertised encodings: PCM 16-bit"))
        for (line in listOf("Selected playback route: Unknown", "Negotiated format: Unknown",
                "Independent output capture: Not recorded", "Calibration: Not recorded",
                "Physical output and protection: Not verified", "Snapshot only. Outputs may have changed.")) {
            assertTrue(text.contains(line), line)
        }
        assertFalse(text.contains("Recent sound checks"))
        assertFalse(text.contains("192.168."))
        assertTrue(text.length <= OutputInventoryReportSnapshot.MAX_CHARACTERS)
        assertTrue(text.toByteArray(Charsets.UTF_8).size <= OutputInventoryReportSnapshot.MAX_UTF8_BYTES)
    }

    @Test fun zeroDevicesAndEmptyCapabilitiesRetainTheirDifferentMeanings() {
        val empty = report(OutputDeviceInventory.from(emptyList())).text
        assertTrue(empty.contains("No available output devices were reported."))
        assertFalse(empty.contains("1. "))
        val arbitrary = report(OutputDeviceInventory.from(listOf(
            OutputDeviceAdvertisement("Built-in speaker", emptyList(), emptyList(), emptyList())))).text
        assertEquals(3, Regex(Regex.escape("Not enumerated (Android reports arbitrary support)")).findAll(arbitrary).count())
        assertFalse(arbitrary.contains("unsupported", ignoreCase = true))
        assertTrue(arbitrary.contains("Negotiated format: Unknown"))
    }

    @Test fun captureKeepsSeparateRowsAndTruncationWithoutChoosingAFormat() {
        val rows = List(16) { OutputDeviceAdvertisement("Built-in speaker", (1..20).map { it * 1000 },
            listOf(1, 2), listOf("PCM float", "Other encoding (999)")) }
        val text = report(OutputDeviceInventory.from(rows, 23), notices = false).text
        assertTrue(text.contains("23 available output devices reported; showing first 16."))
        assertTrue(text.contains("16. Built-in speaker")); assertFalse(text.contains("17. Built-in speaker"))
        assertTrue(text.contains("(showing first 16 of 20)")); assertFalse(text.contains("17000"))
        assertTrue(text.contains("Other encoding (999)"))
        assertTrue(text.contains("Change notices during capture: Unavailable"))
    }

    @Test fun laterMutableInputsCannotRewriteTheReviewedString() {
        val rates = mutableListOf(44100); val encodings = mutableListOf("PCM 16-bit")
        val rows = mutableListOf(OutputDeviceAdvertisement("Built-in speaker", rates, listOf(2), encodings))
        val captured = report(OutputDeviceInventory.from(rows))
        val original = captured.text
        rates[0] = 96000; encodings[0] = "Changed"; rows.clear()
        assertEquals(original, captured.text)
        assertTrue(captured.text.contains("44100 Hz")); assertFalse(captured.text.contains("96000"))
    }

    @Test fun boundedPhoneTextCannotInjectReportLinesOrHideTruncation() {
        val text = report(manufacturer = "Maker\nPrivate:", model = "X".repeat(100), release = "\t").text
        assertTrue(text.contains("Phone: Maker Private: " + "X".repeat(64) + " (truncated)"))
        assertTrue(text.contains("Android: Unavailable · API 36"))
        assertFalse(text.contains("\nPrivate:"))
        assertFalse(text.contains("X".repeat(65)))
    }

    @Test fun buildEnvelopeClockAndAdvertisementControlsFailClosed() {
        for (details in listOf(build + "\nSecret: hidden", build.replace("Platform: Android", "Platform: Unknown"),
                build.replace("Build: 36", "Build: 36\u0000"), build.replace("Version: 0.33-output-report-live-input", "Version: " + "v".repeat(97)))) {
            assertFailsWith<IllegalArgumentException> { report(details = details) }
        }
        assertFailsWith<IllegalArgumentException> { report(api = 0) }
        assertFailsWith<IllegalArgumentException> { report(captured = -1) }
        assertFailsWith<IllegalArgumentException> { report(captured = Long.MAX_VALUE) }
        for (label in listOf("Built-in speaker\nSecret: hidden", "x".repeat(65))) {
            assertFailsWith<IllegalArgumentException> { report(OutputDeviceInventory.from(listOf(
                OutputDeviceAdvertisement(label, listOf(48000), listOf(2), listOf("PCM 16-bit"))))) }
        }
    }

    @Test fun oversizedOrNonAsciiCapabilityTextCannotCreateAnUnboundedPayload() {
        assertFailsWith<IllegalArgumentException> { report(OutputDeviceInventory.from(listOf(
            OutputDeviceAdvertisement("Built-in speaker", listOf(48000), listOf(2), listOf("x".repeat(1025)))))) }
        val dense = OutputDeviceInventory.from(List(16) { OutputDeviceAdvertisement("界".repeat(64),
            (1..16).map { Int.MAX_VALUE }, (1..16).map { Int.MAX_VALUE }, listOf("界".repeat(1024))) })
        assertFailsWith<IllegalArgumentException> { report(dense) }
    }
}
