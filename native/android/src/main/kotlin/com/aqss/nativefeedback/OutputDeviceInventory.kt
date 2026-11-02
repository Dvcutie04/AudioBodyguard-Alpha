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
    val role: OutputDeviceRole = OutputDeviceRole.UNKNOWN,
)

/** Coarse presentation role only. It deliberately excludes names, addresses,
 * IDs and any claim that an available output is the selected playback route. */
enum class OutputDeviceRole { PHONE, WIRED_OR_USB, WIRELESS, TV_OR_HOME, UNKNOWN }

enum class OutputConnectionGuide(val title: String, val nextStep: String) {
    PHONE(
        "Only this phone’s audio is listed",
        "Turn on the TV or home device, open Android’s media output control, then refresh.",
    ),
    WIRED_OR_USB(
        "A wired or USB audio option is available",
        "Confirm the cable or accessory leads to the intended TV or home-audio device.",
    ),
    WIRELESS(
        "A wireless audio option is available",
        "Open Android’s media output control and select the name that matches your TV or home device.",
    ),
    TV_OR_HOME(
        "A TV or home-audio option is available",
        "Open Android’s media output control, select the matching name, then confirm it on the TV.",
    ),
    MIXED(
        "Several output options need confirmation",
        "Use Android’s media output control to choose one output, then return and refresh.",
    ),
    NONE(
        "No output option was reported",
        "Turn on the TV or home device, check Wi-Fi or Bluetooth, then refresh.",
    ),
}

/** Immutable text for one separately reported device, even if kinds repeat. */
data class OutputDeviceSummary(
    val kind: String,
    val sampleRatesText: String,
    val channelCountsText: String,
    val encodingsText: String,
    val capabilitiesTruncated: Boolean,
    val role: OutputDeviceRole,
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

    val connectionGuide: OutputConnectionGuide get() {
        if (totalDeviceCount == 0 || devices.isEmpty()) return OutputConnectionGuide.NONE
        if (truncated) return OutputConnectionGuide.MIXED
        val roles = devices.map { it.role }.toSet()
        return when {
            OutputDeviceRole.TV_OR_HOME in roles -> OutputConnectionGuide.TV_OR_HOME
            OutputDeviceRole.WIRELESS in roles -> OutputConnectionGuide.WIRELESS
            roles == setOf(OutputDeviceRole.PHONE) -> OutputConnectionGuide.PHONE
            OutputDeviceRole.WIRED_OR_USB in roles -> OutputConnectionGuide.WIRED_OR_USB
            else -> OutputConnectionGuide.MIXED
        }
    }

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
                    role = device.role,
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
