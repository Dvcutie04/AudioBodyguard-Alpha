package com.aqss.nativefeedback

import kotlin.test.*

class OutputDeviceInventoryTest {
    private fun speaker(
        rates: List<Int> = listOf(48000),
        channels: List<Int> = listOf(1, 2),
        encodings: List<String> = listOf("PCM 16-bit"),
    ) = OutputDeviceAdvertisement("Built-in speaker", rates, channels, encodings, OutputDeviceRole.PHONE)

    @Test fun emptyInventoryReportsOnlyTheAbsenceOfAdvertisements() {
        val inventory = OutputDeviceInventory.from(emptyList())
        assertEquals(0, inventory.totalDeviceCount)
        assertTrue(inventory.devices.isEmpty())
        assertFalse(inventory.truncated)
        assertEquals("No available output devices were reported.", inventory.summaryText)
        assertEquals(OutputConnectionGuide.NONE, inventory.connectionGuide)
    }

    @Test fun connectionGuideNamesTheNextCheckWithoutClaimingSelection() {
        fun device(kind: String, role: OutputDeviceRole) = OutputDeviceAdvertisement(
            kind, listOf(48000), listOf(2), listOf("PCM 16-bit"), role,
        )
        assertEquals(OutputConnectionGuide.PHONE,
            OutputDeviceInventory.from(listOf(speaker())).connectionGuide)
        assertEquals(OutputConnectionGuide.WIRELESS,
            OutputDeviceInventory.from(listOf(speaker(), device("Bluetooth media output", OutputDeviceRole.WIRELESS))).connectionGuide)
        assertEquals(OutputConnectionGuide.TV_OR_HOME,
            OutputDeviceInventory.from(listOf(speaker(), device("HDMI", OutputDeviceRole.TV_OR_HOME))).connectionGuide)
        assertEquals(OutputConnectionGuide.WIRED_OR_USB,
            OutputDeviceInventory.from(listOf(speaker(), device("USB audio device", OutputDeviceRole.WIRED_OR_USB))).connectionGuide)
        assertEquals(OutputConnectionGuide.MIXED,
            OutputDeviceInventory.from(listOf(speaker(), device("Other", OutputDeviceRole.UNKNOWN))).connectionGuide)

        val guide = OutputDeviceInventory.from(
            listOf(device("HDMI", OutputDeviceRole.TV_OR_HOME)),
        ).connectionGuide
        assertFalse(guide.title.contains("connected", ignoreCase = true))
        assertFalse(guide.title.contains("selected", ignoreCase = true))
        assertFalse(guide.nextStep.contains("verified", ignoreCase = true))
    }

    @Test fun emptyCapabilitiesKeepAndroidArbitrarySupportMeaning() {
        val row = OutputDeviceInventory.from(listOf(speaker(emptyList(), emptyList(), emptyList()))).devices.single()
        for (text in listOf(row.sampleRatesText, row.channelCountsText, row.encodingsText)) {
            assertEquals("Not enumerated (Android reports arbitrary support)", text)
            assertFalse(text.contains("unsupported", ignoreCase = true))
        }
        assertFalse(row.capabilitiesTruncated)
    }

    @Test fun sameKindDevicesRemainSeparateAdvertisements() {
        val inventory = OutputDeviceInventory.from(listOf(speaker(), speaker()))
        assertEquals(2, inventory.totalDeviceCount)
        assertEquals(2, inventory.devices.size)
        assertEquals(listOf("Built-in speaker", "Built-in speaker"), inventory.devices.map { it.kind })
        assertEquals("2 available output devices reported.", inventory.summaryText)
    }

    @Test fun sourceCountSurvivesAnAlreadyBoundedFrameworkRead() {
        val inventory = OutputDeviceInventory.from(List(16) { speaker() }, totalDeviceCount = 23)
        assertEquals(23, inventory.totalDeviceCount)
        assertEquals(16, inventory.devices.size)
        assertTrue(inventory.truncated)
        assertEquals(OutputConnectionGuide.MIXED, inventory.connectionGuide)
        assertEquals("23 available output devices reported; showing first 16.", inventory.summaryText)
        assertFailsWith<IllegalArgumentException> {
            OutputDeviceInventory.from(listOf(speaker()), totalDeviceCount = 0)
        }
        assertFailsWith<IllegalArgumentException> {
            OutputDeviceInventory.from(emptyList(), totalDeviceCount = -1)
        }
    }

    @Test fun unboundedInputCannotPutMoreThanSixteenRowsInTheSnapshot() {
        val inventory = OutputDeviceInventory.from(List(20) { index ->
            OutputDeviceAdvertisement("Device kind $index", listOf(48000), listOf(2), listOf("PCM 16-bit"))
        })
        assertEquals(20, inventory.totalDeviceCount)
        assertEquals(16, inventory.devices.size)
        assertTrue(inventory.truncated)
        assertEquals("Device kind 15", inventory.devices.last().kind)
    }

    @Test fun eachCapabilityListShowsItsOwnBoundAndKeepsUnrecognizedEncodingLabels() {
        val row = OutputDeviceInventory.from(listOf(speaker(
            rates = (1..20).map { it * 1000 },
            channels = (1..18).toList(),
            encodings = (1..19).map { "Encoding $it" },
        ))).devices.single()
        assertTrue(row.capabilitiesTruncated)
        assertTrue(row.sampleRatesText.endsWith("(showing first 16 of 20)"))
        assertTrue(row.channelCountsText.endsWith("(showing first 16 of 18)"))
        assertTrue(row.encodingsText.endsWith("(showing first 16 of 19)"))
        assertTrue(row.encodingsText.contains("Encoding 16"))
        assertFalse(row.encodingsText.contains("Encoding 17"))
        assertFalse(row.sampleRatesText.contains("17000"))
        assertFalse(row.channelCountsText.contains("17"))
    }

    @Test fun reviewedSnapshotCannotFollowLaterMutableInputChanges() {
        val rates = mutableListOf(44100, 48000)
        val channels = mutableListOf(1, 2)
        val encodings = mutableListOf("PCM 16-bit", "Encoding 999")
        val source = mutableListOf(speaker(rates, channels, encodings))
        val inventory = OutputDeviceInventory.from(source)
        val row = inventory.devices.single()
        rates.clear(); channels.add(8); encodings[0] = "Changed label"; source.clear()
        assertEquals(1, inventory.totalDeviceCount)
        assertEquals("44100, 48000 Hz", row.sampleRatesText)
        assertEquals("1, 2", row.channelCountsText)
        assertEquals("PCM 16-bit, Encoding 999", row.encodingsText)
        assertFalse(row.capabilitiesTruncated)
        @Suppress("UNCHECKED_CAST")
        assertFailsWith<UnsupportedOperationException> {
            (inventory.devices as MutableList<OutputDeviceSummary>).clear()
        }
        assertEquals(1, inventory.devices.size)
    }
}
