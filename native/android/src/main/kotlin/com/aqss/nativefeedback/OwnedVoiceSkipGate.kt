package com.aqss.nativefeedback

/** Owned-fixture action, not a TV command, transport or playback authority. */
enum class OwnedSkipAction { SKIP_INTRO, SKIP_RECAP }
enum class OwnedSkipDecision { UNAVAILABLE, REQUESTED, CALL_FAILED }

data class OwnedSkipSnapshot(
    val playerId: String,
    val playbackSessionId: String,
    val contentId: String,
    val generation: Int,
    val introVisible: Boolean,
    val introEnabled: Boolean,
    val recapVisible: Boolean,
    val recapEnabled: Boolean,
) {
    internal fun valid(): Boolean = generation >= 0 && listOf(playerId, playbackSessionId, contentId).all { id ->
        id.length in 1..96 && id.all { ch -> ch in 'a'..'z' || ch in 'A'..'Z' || ch in '0'..'9' || ch in "._:-" }
    }
    internal fun offers(action: OwnedSkipAction): Boolean = when (action) {
        OwnedSkipAction.SKIP_INTRO -> introVisible && introEnabled
        OwnedSkipAction.SKIP_RECAP -> recapVisible && recapEnabled
    }
}

class OwnedSkipProposal internal constructor(
    val action: OwnedSkipAction,
    internal val runId: String,
    internal val snapshot: OwnedSkipSnapshot,
    internal val nonce: Any,
)

/** Must be used on the Android main thread, as the native SpeechRecognizer is. */
class OwnedVoiceSkipGate {
    companion object {
        const val GRAMMAR_VERSION = "voice-skip-v1"
        private val phrase = Regex("^audio\\s+bodyguard\\s*,?\\s*skip\\s+(intro|recap)[.!?]?$", RegexOption.IGNORE_CASE)
        fun parse(text: String?, final: Boolean): OwnedSkipAction? {
            if (!final || text == null || text.length !in 1..96 || !text.all { it.code in 0..127 }) return null
            return when (phrase.matchEntire(text.trim())?.groupValues?.get(1)?.lowercase()) {
                "intro" -> OwnedSkipAction.SKIP_INTRO
                "recap" -> OwnedSkipAction.SKIP_RECAP
                else -> null
            }
        }
    }
    private var runId: String? = null
    private var lastRunId: String? = null
    private var selected: OwnedSkipSnapshot? = null
    private var pending: OwnedSkipProposal? = null
    private var used = false

    fun start(runId: String, player: OwnedSkipSnapshot): Boolean {
        if (this.runId != null || runId == lastRunId || runId.length !in 1..96 ||
            !runId.all { it.isLetterOrDigit() && it.code < 128 || it in "._:-" } || !player.valid()) return false
        this.runId = runId; lastRunId = runId; selected = player; pending = null; used = false
        return true
    }
    fun stop() { runId = null; selected = null; pending = null; used = false }
    fun propose(text: String?, final: Boolean, runId: String,
                observed: OwnedSkipSnapshot): OwnedSkipProposal? {
        if (this.runId != runId || used || pending != null || selected != observed) return null
        val action = parse(text, final) ?: return null
        if (!observed.offers(action)) return null
        return OwnedSkipProposal(action, runId, observed, Any()).also { pending = it }
    }
    fun request(proposal: OwnedSkipProposal?, runId: String, observed: OwnedSkipSnapshot,
                permitted: Boolean, foreground: Boolean,
                pressOwnedButton: (OwnedSkipAction) -> Boolean): OwnedSkipDecision {
        if (proposal == null || this.runId != runId || used ||
            proposal.runId != runId || proposal !== pending || selected != observed ||
            proposal.snapshot != observed || !observed.offers(proposal.action)) return OwnedSkipDecision.UNAVAILABLE
        // Once session permission or foreground ownership is lost, require fresh Start.
        if (!permitted || !foreground) { stop(); return OwnedSkipDecision.UNAVAILABLE }
        used = true; pending = null
        return try {
            if (pressOwnedButton(proposal.action)) OwnedSkipDecision.REQUESTED else OwnedSkipDecision.CALL_FAILED
        } catch (_: RuntimeException) { OwnedSkipDecision.CALL_FAILED }
    }
    /** Final recognition requests an owned button only; never physical verification. */
    fun requestFinal(text: String?, runId: String, observed: OwnedSkipSnapshot,
                     permitted: Boolean, foreground: Boolean,
                     pressOwnedButton: (OwnedSkipAction) -> Boolean): OwnedSkipDecision {
        if (!permitted || !foreground) { stop(); return OwnedSkipDecision.UNAVAILABLE }
        val proposal = propose(text, true, runId, observed) ?: return OwnedSkipDecision.UNAVAILABLE
        return request(proposal, runId, observed, permitted, foreground, pressOwnedButton)
    }

}
