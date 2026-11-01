package com.aqss.nativefeedback

import java.time.Instant

/** A bounded historical metadata copy. It is neither an output owner nor
 * physical evidence. The native caller supplies fixed kind/encoding labels,
 * not device names, IDs, addresses, or arbitrary logs. */
class OutputInventoryReportSnapshot private constructor(val text: String, internal val buildDetails: String) {
    companion object {
        const val MAX_CHARACTERS = 24 * 1024
        const val MAX_UTF8_BYTES = 48 * 1024
        private const val MAX_CLOCK = 253_402_300_799_999L

        /** Only this bounded prefix is traversed; truncation remains visible. */
        fun phoneText(value: String): String {
            val prefix = value.take(64).map { if (unsafe(it)) ' ' else it }.joinToString("").trim()
            return prefix.ifBlank { "Unavailable" } + if (value.length > 64) " (truncated)" else ""
        }

        fun capture(
            buildDetails: String,
            manufacturer: String,
            model: String,
            osRelease: String,
            apiLevel: Int,
            observedAtMillis: Long,
            noticesRegistered: Boolean,
            inventory: OutputDeviceInventory,
        ): OutputInventoryReportSnapshot {
            require(buildDetails.length <= 512) { "Bounded installed-build envelope required" }
            val lines = buildDetails.split('\n')
            require(lines.size == 4 && lines[0] == "Audio Bodyguard" && lines[1] == "Platform: Android" &&
                lines[2].startsWith("Version: ") && lines[3].startsWith("Build: ")) { "Installed-build fields only" }
            val version = lines[2].removePrefix("Version: ")
            val build = lines[3].removePrefix("Build: ")
            require(version.isNotBlank() && version.length <= 96 && version.none(::unsafe)) { "Invalid installed version" }
            require(build.matches(Regex("[0-9]{1,19}|Unavailable"))) { "Invalid installed build" }
            require(apiLevel > 0 && observedAtMillis in 0..MAX_CLOCK) { "Unavailable platform or phone clock" }
            // The inventory factory bounds rows and snapshots mutable inputs.
            // Reject malformed presentation fields before building an Intent.
            for (device in inventory.devices) {
                require(device.kind.isNotBlank() && device.kind.length <= 64 && device.kind.none(::unsafe)) { "Invalid output kind" }
                for (field in listOf(device.sampleRatesText, device.channelCountsText, device.encodingsText)) {
                    require(field.isNotBlank() && field.length <= 1024 && field.none(::unsafe)) { "Invalid advertisement field" }
                }
            }
            val text = buildString {
                append("Audio Bodyguard output inventory (v1)\n")
                append("Read finished at (phone clock, UTC): ${Instant.ofEpochMilli(observedAtMillis)}\n\n")
                append(buildDetails)
                append("\n\nPhone: ${phoneText(manufacturer)} ${phoneText(model)}")
                append("\nAndroid: ${phoneText(osRelease)} · API $apiLevel")
                append("\nChange notices during capture: ${if (noticesRegistered) "Registered" else "Unavailable"}\n\n")
                append(inventory.summaryText)
                inventory.devices.forEachIndexed { index, device ->
                    append("\n\n${index + 1}. ${device.kind}")
                    append("\nAdvertised sample rates: ${device.sampleRatesText}")
                    append("\nAdvertised channel counts: ${device.channelCountsText}")
                    append("\nAdvertised encodings: ${device.encodingsText}")
                }
                append("\n\nSelected playback route: Unknown\nNegotiated format: Unknown")
                append("\nIndependent output capture: Not recorded\nCalibration: Not recorded")
                append("\nPhysical output and protection: Not verified")
                append("\n\nSnapshot only. Outputs may have changed.")
                append("\nAdvertised metadata only; not physical output evidence.")
            }
            require(text.length <= MAX_CHARACTERS && text.toByteArray(Charsets.UTF_8).size <= MAX_UTF8_BYTES) { "Report exceeds its text bound" }
            return OutputInventoryReportSnapshot(text, buildDetails)
        }

        private fun unsafe(value: Char) = value.isISOControl() || value == '\u2028' || value == '\u2029' || Character.getType(value) == Character.FORMAT.toInt()
    }
}
