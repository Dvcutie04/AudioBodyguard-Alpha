package com.aqss.bodyguard.prototype

/** Presentation only; these messages cannot admit capture or clear cleanup quarantine. */
internal object MicrophoneAvailabilityGuidance {
    const val BUSY = "Another audio tool is running or closing. Stop it and wait for it to close before tapping Start."
    const val BLOCKED = "Audio tools are blocked by unresolved cleanup. Review or share any reports you want to keep, then force stop this app in Android Settings before starting a new check."
}
