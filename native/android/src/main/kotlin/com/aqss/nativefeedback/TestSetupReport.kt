package com.aqss.nativefeedback

import java.time.Instant
import java.time.format.DateTimeFormatterBuilder

enum class TestSetupField(val title: String, val hint: String) {
    PLAYBACK_PHONE("Playback phone", "Model and OS version"),
    INTENDED_OUTPUT("Intended output", "For example: phone speaker. Your plan, not a detected route."),
    OBSERVER_PHONE("Second phone", "Model and OS, or unavailable"),
    RECORDING_APP("Recording app and mode", "App name and the mode you can check"),
    PLACEMENT("Phone placement", "Where each phone would be placed"),
    CONSTRAINTS("Setup constraints", "Missing equipment or anything you cannot check"),
}

/** Immutable user notes, never measured output or authorization. */
class TestSetupReportSnapshot private constructor(val text: String) {
    companion object {
        const val MAX_FIELD_UNITS = 160
        const val MAX_CHARACTERS = 4 * 1024
        const val MAX_UTF8_BYTES = 8 * 1024
        const val MAX_COMBINED_CHARACTERS = 32 * 1024
        const val MAX_COMBINED_UTF8_BYTES = 64 * 1024
        const val NOTICE = "Setup notes only. Nothing is verified."
        const val OUTPUT_NOTICE = "Snapshot only. Outputs may have changed."
        private const val MAX_CLOCK = 253_402_300_799_999L
        private val utc = DateTimeFormatterBuilder().appendInstant(3).toFormatter()

        fun limitInput(value: String): String {
            val prefix = value.take(MAX_FIELD_UNITS)
            return if (prefix.lastOrNull()?.isHighSurrogate() == true) prefix.dropLast(1) else prefix
        }

        fun capture(buildDetails: String, notes: Map<TestSetupField, String>, reviewedAtMillis: Long,
                    outputReport: OutputInventoryReportSnapshot? = null): TestSetupReportSnapshot {
            require(buildDetails.length <= 512) { "Bounded installed-build envelope required" }
            val lines = buildDetails.split('\n')
            require(lines.size == 4 && lines[0] == "Audio Bodyguard" && lines[1] == "Platform: Android" &&
                lines[2].startsWith("Version: ") && lines[3].startsWith("Build: ")) { "Installed-build fields only" }
            val version = lines[2].removePrefix("Version: ")
            val build = lines[3].removePrefix("Build: ")
            require(version.length in 1..96 && version.isNotBlank() && normalized(version) == version) { "Invalid installed version" }
            require(build.matches(Regex("[0-9]{1,19}|Unavailable"))) { "Invalid installed build" }
            require(reviewedAtMillis in 0..MAX_CLOCK) { "Unavailable phone clock" }
            require(outputReport == null || outputReport.buildDetails == buildDetails) { "Output snapshot must match the installed build" }
            val text = buildString {
                append("Audio Bodyguard test setup (v1)\n")
                append("Notes reviewed at (phone clock, UTC): ${utc.format(Instant.ofEpochMilli(reviewedAtMillis))}\n\n")
                append(buildDetails); append("\n\nYour notes (not verified)")
                for (field in TestSetupField.entries) {
                    val value = normalized(notes[field] ?: "")
                    val quoted = if (value.isEmpty()) "Unknown" else "\"" + value.replace("\\", "\\\\").replace("\"", "\\\"") + "\""
                    append("\n${field.title}: $quoted")
                }
                append("\n\nActual playback route: Unknown\nNegotiated format: Unknown")
                append("\nBackend and ownership review: Pending\nIndependent capture: Not recorded")
                append("\nCalibration and clock mapping: Unknown\nPlayback/capture consent: Not collected")
                append("\nPhysical output and protection: Not verified")
                append("\n\n$NOTICE\nThis worksheet does not authorize playback or recording.")
            }
            require(text.length <= MAX_CHARACTERS && text.toByteArray(Charsets.UTF_8).size <= MAX_UTF8_BYTES) { "Setup report exceeds its text bound" }
            val combined = if (outputReport == null) text else text +
                "\n\nAttached output snapshot\n$OUTPUT_NOTICE\n\n" + outputReport.text
            require(combined.length <= MAX_COMBINED_CHARACTERS && combined.toByteArray(Charsets.UTF_8).size <= MAX_COMBINED_UTF8_BYTES) { "Combined report exceeds its text bound" }
            return TestSetupReportSnapshot(combined)
        }

        private fun normalized(value: String): String {
            require(value.length <= MAX_FIELD_UNITS) { "Keep each answer brief" }
            return buildString {
                var index = 0
                while (index < value.length) {
                    val point = Character.codePointAt(value, index)
                    require(point !in 0xD800..0xDFFF) { "Invalid note text" }
                    index += Character.charCount(point)
                    val unsafe = Character.isISOControl(point) || point == 0x2028 || point == 0x2029 ||
                        Character.getType(point) == Character.FORMAT.toInt()
                    if (unsafe) append(' ') else appendCodePoint(point)
                }
            }.trim()
        }
    }
}
