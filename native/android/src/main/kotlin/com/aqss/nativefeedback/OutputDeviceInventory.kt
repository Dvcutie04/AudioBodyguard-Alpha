package com.aqss.nativefeedback

import java.util.Collections

/** Available-device metadata only. Callers supply fixed kind/encoding labels,
 * never device names, addresses or identifiers. These are advertisements, not
 * a selected playback route, negotiated format or independent observation.
 */
data class OutputDeviceAdvertisement(
    val kind: String,
    val sampleRates: List<Int>,
    val channelCounts: List<Int>,
    val encodings: List<String>,
)

/** Immutable text for one separately reported device, even if kinds repeat. */
data class OutputDeviceSummary(
    val kind: String,
    val sampleRatesText: String,
    val channelCountsText: String,
    val encodingsText: String,
    val capabilitiesTruncated: Boolean,
)

/** Bounded, immutable presentation snapshot. The Android caller bounds the
 * devices it inspects and the values it renders; framework getters may return
 * full arrays. Pass the complete getDevices() count when reading only a prefix.
 */
class OutputDeviceInventory private constructor(
    val totalDeviceCount: Int,
    val devices: List<OutputDeviceSummary>,
) {
    val truncated: Boolean get() = totalDeviceCount > devices.size

    val summaryText: String get() = when {
        totalDeviceCount == 0 -> "No available output devices were reported."
        truncated -> "$totalDeviceCount available output devices reported; showing first ${devices.size}."
        totalDeviceCount == 1 -> "1 available output device reported."
        else -> "$totalDeviceCount available output devices reported."
    }

    companion object {
        const val MAX_DEVICES = 16
        const val MAX_CAPABILITIES = 16
        private const val ARBITRARY_SUPPORT = "Not enumerated (Android reports arbitrary support)"

        fun from(
            devices: List<OutputDeviceAdvertisement>,
            totalDeviceCount: Int = devices.size,
        ): OutputDeviceInventory {
            require(totalDeviceCount >= devices.size) { "Reported count cannot omit supplied advertisements" }
            val rows = devices.take(MAX_DEVICES).map { device ->
                OutputDeviceSummary(
                    kind = device.kind,
                    sampleRatesText = capabilityText(device.sampleRates, " Hz"),
                    channelCountsText = capabilityText(device.channelCounts),
                    encodingsText = capabilityText(device.encodings),
                    capabilitiesTruncated = listOf(
                        device.sampleRates.size, device.channelCounts.size, device.encodings.size,
                    ).any { it > MAX_CAPABILITIES },
                )
            }
            return OutputDeviceInventory(totalDeviceCount, Collections.unmodifiableList(rows))
        }

        private fun capabilityText(values: List<*>, suffix: String = ""): String {
            if (values.isEmpty()) return ARBITRARY_SUPPORT
            val text = values.take(MAX_CAPABILITIES).joinToString(", ") + suffix
            return if (values.size > MAX_CAPABILITIES) {
                "$text (showing first $MAX_CAPABILITIES of ${values.size})"
            } else text
        }
    }
}
