package com.aqss.nativefeedback

import java.util.Collections
import java.time.Instant
import java.time.format.DateTimeFormatterBuilder

/** One explicitly entered private IPv4 host; never a discovered or verified TV. */
class LocalTVTarget private constructor(val address: String, private val values: List<Int>) {
    fun addressBytes(): ByteArray = values.map { it.toByte() }.toByteArray()

    companion object {
        val PORTS: List<Int> = Collections.unmodifiableList(listOf(7345, 9000))
        const val TIMEOUT_MILLIS = 4000
        const val BOUNDARY = "TV identity, pairing and audio protection are not verified."
        const val INVALID_ADDRESS = "Enter the private IPv4 address shown in your TV’s network settings."

        fun parse(input: String): LocalTVTarget? {
            if (input.length > 64) return null
            val value = input.trim()
            if (value.isEmpty() || value.length > 15) return null
            val parts = value.split('.')
            if (parts.size != 4) return null
            val bytes = parts.map { part ->
                if (part.isEmpty() || part.any { it !in '0'..'9' } ||
                    (part.length > 1 && part.first() == '0')) return null
                part.toIntOrNull()?.takeIf { it in 0..255 } ?: return null
            }
            val privateRange = bytes[0] == 10 || (bytes[0] == 172 && bytes[1] in 16..31) ||
                (bytes[0] == 192 && bytes[1] == 168)
            if (!privateRange || bytes[3] !in 1..254) return null
            return LocalTVTarget(value, bytes)
        }
    }
}

enum class TVTrialFollowUp { ADDRESS_PICTURES, PHONE_WIFI, REVIEW }

enum class TVTrialOutcome {
    ADDRESS_REJECTED, WIFI_REQUIRED, CHECK_UNAVAILABLE, SERVICE_ANSWERED_UNVERIFIED,
    NO_SERVICE_RESPONSE, CHECK_STOPPED, CLEANUP_UNRESOLVED;

    val followUp: TVTrialFollowUp?
        get() = when (this) {
            ADDRESS_REJECTED -> TVTrialFollowUp.ADDRESS_PICTURES
            WIFI_REQUIRED, NO_SERVICE_RESPONSE -> TVTrialFollowUp.PHONE_WIFI
            SERVICE_ANSWERED_UNVERIFIED -> TVTrialFollowUp.REVIEW
            CHECK_UNAVAILABLE, CHECK_STOPPED, CLEANUP_UNRESOLVED -> null
        }
}

/** Historical description only; no host, user notes, device ID or authority. */
class TVTrialReport private constructor(val text: String) {
    companion object {
        const val NOTICE = "Historical check only. TV identity, pairing and protection are not verified."
        const val BETA_SCOPE = "Friends can try the setup pictures and phone sound/voice checks. The in-app network check tests VIZIO candidate services only. Other TV brands use their official app guides. TV control and audio protection are not available in this beta."
        fun capture(buildDetails: String, outcome: TVTrialOutcome, reviewedAtMillis: Long): TVTrialReport {
            TestSetupReportSnapshot.capture(buildDetails, emptyMap(), reviewedAtMillis)
            val utc = DateTimeFormatterBuilder().appendInstant(3).toFormatter()
            val result = when (outcome) {
                TVTrialOutcome.ADDRESS_REJECTED -> "No native check started: the entered address was rejected."
                TVTrialOutcome.WIFI_REQUIRED -> "No native check started: a suitable Wi-Fi path was unavailable."
                TVTrialOutcome.CHECK_UNAVAILABLE -> "No new native check started: previous work was closing or unavailable."
                TVTrialOutcome.SERVICE_ANSWERED_UNVERIFIED -> "A TCP service answered at that moment. Its identity is not authenticated."
                TVTrialOutcome.NO_SERVICE_RESPONSE -> "The check ended without establishing a service response. The cause is unknown."
                TVTrialOutcome.CHECK_STOPPED -> "The check stopped. This is not a successful connection result."
                TVTrialOutcome.CLEANUP_UNRESOLVED -> "Cleanup was not confirmed. Another check must remain blocked."
            }
            return TVTrialReport(listOf("Audio Bodyguard connection trial (v1)",
                "Reviewed at (phone clock, UTC): ${utc.format(Instant.ofEpochMilli(reviewedAtMillis))}",
                "", buildDetails, "", "Selected test: VIZIO candidate TCP services (not a verified TV model)",
                "Outcome: ${outcome.name}", result, "", "No TV command or audio was sent by this check.",
                "TV identity: Not verified", "TV pairing: Not verified", "Audio protection: Not verified", "",
                NOTICE, "No TV address, Wi-Fi name, password, audio or photo is included.",
                "Reviewing or sharing this text does not authorize a device action.").joinToString("\n"))
        }
    }
}
