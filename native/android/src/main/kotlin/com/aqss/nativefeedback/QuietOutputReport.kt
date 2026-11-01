package com.aqss.nativefeedback

import java.time.Instant
import java.time.format.DateTimeFormatterBuilder

class QuietOutputReportSnapshot private constructor(val text: String, val buildDetails: String) {
    companion object {
        const val NOTICE = "Framework check only. Sound and protection are not verified."
        private val cleanupOperations = setOf(QuietOperation.RETIRE, QuietOperation.PAUSE,
            QuietOperation.FLUSH, QuietOperation.UNWATCH, QuietOperation.RELEASE, QuietOperation.ABANDON)
        fun capture(buildDetails: String, result: QuietOutputResult, reviewedAtMillis: Long): QuietOutputReportSnapshot {
            require(buildDetails.length <= 512)
            val lines = buildDetails.split('\n')
            require(lines.size == 4 && lines[0] == "Audio Bodyguard" && lines[1] == "Platform: Android")
            require(lines[2].startsWith("Version: ") && lines[3].startsWith("Build: "))
            val version = lines[2].removePrefix("Version: ")
            require(version.length in 1..96 && version.isNotBlank() && version.none {
                Character.isISOControl(it) || Character.getType(it) == Character.FORMAT.toInt() || it == '\u2028' || it == '\u2029'
            })
            require(lines[3].removePrefix("Build: ").matches(Regex("[0-9]{1,19}|Unavailable")))
            require(reviewedAtMillis in 0..253402300799999L)
            val utc = DateTimeFormatterBuilder().appendInstant(3).toFormatter().format(Instant.ofEpochMilli(reviewedAtMillis))
            val cleanup = when {
                !result.cleanupSucceeded || result.unreportedCall -> "Unresolved"
                result.trace.none { it.stage == QuietStage.ENTERED && it.operation in cleanupOperations } -> "Not entered"
                else -> "Returned"
            }
            val text = buildString {
                append("Audio Bodyguard quiet output check (v1)\nReviewed at (phone clock, UTC): $utc\n\n$buildDetails\n")
                append("\nRun label (local, not authenticated): ${result.runId}")
                append("\nRequested profile: 48000 Hz, mono, PCM16; 256 zero-valued samples")
                append("\nAdmission budget: 2000 ms; Android calls may take longer to close")
                append("\nApp stream gain requested: 0; accepted: ${result.zeroGainAccepted?.toString() ?: "Not attempted"}")
                append("\nNative track allocation: ${if (result.trackOpened) "Returned" else if (result.allocationEntered) "Entered; outcome unavailable" else "Not entered"}")
                append("\nConstructed stream (framework metadata): ${result.constructed ?: "Unavailable"}")
                append("\nRequested buffer bytes: ${result.requestedBufferBytes ?: "Unavailable"}")
                val routes = result.routes
                append("\nFramework route type codes: ${if (routes?.available == true) routes.types.joinToString().ifEmpty { "None reported" } else "Unavailable"}")
                append("\nRoute query: ${if (routes == null || !routes.available) "Unavailable" else if (routes.multipleQuery) "Plural; ${routes.totalReported} reported, first 16 retained" else "Singular; additional routes unknown"}")
                append("\nKnown accepted samples: ${result.acceptedSamples}\nWrite attempts: ${result.attempts}")
                append("\nEnd reason: ${result.reason}\nResource cleanup calls: $cleanup")
                append("\nCall accounting incomplete: ${result.unreportedCall}")
                append("\nProcess audio exclusion quarantined: ${result.quarantined}")
                append("\nControl clock: elapsed realtime milliseconds (includes sleep)")
                append("\nWorker operations (application observations, not hardware timing):")
                result.trace.forEach { e -> append("\n${e.sequence} ${e.operation} ${e.stage} t=${e.elapsedMs ?: "Unavailable"} raw=${e.rawValue ?: "n/a"} exception=${e.exception} offset=${e.offsetSamples ?: "n/a"} requested=${e.requestedSamples ?: "n/a"} knownAccepted=${e.acceptedSamples}") }
                append("\n\nPhysical output and protection: Not verified")
                append("\nHardware format and acoustic route: Not verified\nCalibration and independent capture: Not recorded")
                append("\nNo acoustic latency, silence or retirement is established.\n\n$NOTICE")
            }
            require(text.length <= 32768 && text.toByteArray(Charsets.UTF_8).size <= 32768)
            return QuietOutputReportSnapshot(text, buildDetails)
        }
    }
}
