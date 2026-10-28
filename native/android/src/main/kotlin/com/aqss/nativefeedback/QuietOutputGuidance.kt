package com.aqss.nativefeedback

/** Presentation only. Native admission and resource ownership remain with the worker and exclusion gate. */
class QuietOutputGuidance private constructor(
    val message: String,
    val canStart: Boolean,
    val canReview: Boolean,
) {
    companion object {
        fun from(result: QuietOutputResult?, processBlocked: Boolean): QuietOutputGuidance {
            val reviewable = result != null
            val unresolved = processBlocked || result?.quarantined == true ||
                result?.cleanupSucceeded == false || result?.unreportedCall == true
            if (unresolved) {
                val keepReport = if (reviewable) "Review or share any report you want to keep, then force stop" else "Force stop"
                return QuietOutputGuidance(
                    "Audio tools are blocked by unresolved cleanup. $keepReport this app in Android Settings before starting a new check.",
                    canStart = false, canReview = reviewable)
            }
            val message = when (result?.reason) {
                null -> "No check report is available. Tap Start to try a new check."
                QuietStop.COMPLETE -> "Quiet check ended. Review the report for Android's observations."
                QuietStop.USER -> "You stopped this check. Tap Start only when you want a new check."
                QuietStop.INACTIVE -> "This check stopped when the screen lost focus. Tap Start only when you are ready for a new check."
                QuietStop.FOCUS_DENIED -> "Android did not grant audio focus for this check. Check other audio use before tapping Start for a new check."
                QuietStop.FOCUS_LOSS -> "Android changed the audio focus. Check other audio use, then tap Start for a new check."
                QuietStop.ROUTE_CHANGED -> "An output-change notice stopped this check. Check your intended output, then tap Start for a new check."
                QuietStop.BUSY -> "Another audio tool is running or closing. Stop it and wait for it to close before tapping Start."
                QuietStop.UNSUPPORTED -> "This quiet-check configuration is unavailable here. Review the report for details."
                QuietStop.TIME_LIMIT -> "This check reached its time budget. Review the report before choosing Start for a new check."
                QuietStop.CLOCK_FAULT -> "This check stopped because its timing information was unavailable or inconsistent. Review the report before trying a new check."
                QuietStop.ATTEMPT_LIMIT -> "The check stopped before Android accepted the full quiet test. Review the report before trying a new check."
                QuietStop.WRITE_FAILED -> "A playback write reported a problem. Review or share the report before trying a new check."
                QuietStop.INVALID_RESULT -> "The check received an unexpected playback result. Review or share the report before trying a new check."
                QuietStop.BACKEND_FAILED -> "The check encountered a playback problem. Review or share the report before trying a new check."
                QuietStop.WORKER_INTERRUPTED -> "The check was interrupted before it finished. Review the report before trying a new check."
            }
            return QuietOutputGuidance(message, canStart = true, canReview = reviewable)
        }
    }
}
