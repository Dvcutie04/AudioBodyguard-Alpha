package com.aqss.nativefeedback

import kotlin.test.*

class OwnedVoiceSkipGateTest {
    private fun player(intro: Boolean = true, recap: Boolean = true, generation: Int = 7,
                       content: String = "episode-1"): OwnedSkipSnapshot =
        OwnedSkipSnapshot("owned", "session-1", content, generation, intro, intro, recap, recap)

    @Test fun exactFinalPhrasesAndRejections() {
        assertEquals(OwnedSkipAction.SKIP_INTRO, OwnedVoiceSkipGate.parse("Audio Bodyguard, skip intro", true))
        assertEquals(OwnedSkipAction.SKIP_RECAP, OwnedVoiceSkipGate.parse(" AUDIO BODYGUARD SKIP RECAP. ", true))
        assertNull(OwnedVoiceSkipGate.parse("Audio Bodyguard skip recap", false))
        for (text in listOf("skip intro", "Audio Bodyguard don't skip intro", "Audio Bodyguard skip next",
                            "Audio Bodyguard skip intro please",\n                            "Audio Bodyguard\\nskip intro", "Audio Bodyguard\\tskip recap",\n                            "\\nAudio Bodyguard skip intro\\n", "Audio Bodyguard skip intro\\r", "Audio Bodyguard skip intro and recap",
                            "\u00A0Audio Bodyguard skip intro", "Audio Bodyguard skip recap\u00A0")) {
            assertNull(OwnedVoiceSkipGate.parse(text, true))
        }
    }

    @Test fun eachCommandCallsCorrectOwnedButtonOnce() {
        for ((text, expected) in listOf("Audio Bodyguard skip intro" to OwnedSkipAction.SKIP_INTRO,
                                        "Audio Bodyguard skip recap" to OwnedSkipAction.SKIP_RECAP)) {
            val gate = OwnedVoiceSkipGate()
            val state = player()
            val calls = mutableListOf<OwnedSkipAction>()
            assertTrue(gate.start("listen-1", state))
            val proposal = assertNotNull(gate.propose(text, true, "listen-1", state))
            assertEquals(expected, proposal.action)
            val press: (OwnedSkipAction) -> Boolean = { calls.add(it); true }
            assertEquals(OwnedSkipDecision.REQUESTED,
                gate.request(proposal, "listen-1", state, true, true, press))
            assertEquals(OwnedSkipDecision.UNAVAILABLE,
                gate.request(proposal, "listen-1", state, true, true, press))
            assertEquals(listOf(expected), calls)
        }
    }

    @Test fun changedAffordanceSessionStopAndPermissionAreRefused() {
        val gate = OwnedVoiceSkipGate()
        val state = player()
        var calls = 0
        assertTrue(gate.start("listen-1", state))
        assertNull(gate.propose("Audio Bodyguard skip intro", false, "listen-1", state))
        val proposal = assertNotNull(gate.propose("Audio Bodyguard skip intro", true, "listen-1", state))
        for (different in listOf(player(intro = false), player(generation = 8), player(content = "episode-2"))) {
            assertEquals(OwnedSkipDecision.UNAVAILABLE, gate.request(proposal, "listen-1", different, true, true) { calls++; true })
        }
        assertEquals(OwnedSkipDecision.UNAVAILABLE, gate.request(proposal, "listen-1", state, false, true) { calls++; true })
        assertEquals(OwnedSkipDecision.UNAVAILABLE, gate.request(proposal, "listen-1", state, true, false) { calls++; true })
        gate.stop()
        assertEquals(OwnedSkipDecision.UNAVAILABLE, gate.request(proposal, "listen-1", state, true, true) { calls++; true })
        assertFalse(gate.start("listen-1", state))
        assertTrue(gate.start("listen-2", state))
        assertNull(gate.propose("Audio Bodyguard skip recap", true, "listen-1", state))
        assertEquals(0, calls)
    }

    @Test fun unsupportedControlAndFailedOwnedButtonCannotBeRetried() {
        val gate = OwnedVoiceSkipGate()
        val state = player(intro = false)
        assertTrue(gate.start("listen-1", state))
        assertNull(gate.propose("Audio Bodyguard skip intro", true, "listen-1", state))
        val proposal = assertNotNull(gate.propose("Audio Bodyguard skip recap", true, "listen-1", state))
        var calls = 0
        assertEquals(OwnedSkipDecision.CALL_FAILED,
            gate.request(proposal, "listen-1", state, true, true) { calls++; false })
        assertEquals(OwnedSkipDecision.UNAVAILABLE,
            gate.request(proposal, "listen-1", state, true, true) { calls++; false })
        assertEquals(1, calls)
    }

    @Test fun lostPermissionOrForegroundInvalidatesPendingFinalResult() {
        for ((permitted, foreground) in listOf(false to true, true to false)) {
            val gate = OwnedVoiceSkipGate()
            val state = player()
            var calls = 0
            assertTrue(gate.start("listen-1", state))
            val proposal = assertNotNull(gate.propose("Audio Bodyguard skip intro", true, "listen-1", state))
            val action: (OwnedSkipAction) -> Boolean = { calls++; true }
            assertEquals(OwnedSkipDecision.UNAVAILABLE,
                gate.request(proposal, "listen-1", state, permitted, foreground, action))
            assertEquals(OwnedSkipDecision.UNAVAILABLE,
                gate.request(proposal, "listen-1", state, true, true, action))
            assertNull(gate.propose("Audio Bodyguard skip recap", true, "listen-1", state))
            assertFalse(gate.start("listen-1", state))
            assertTrue(gate.start("listen-2", state))
            assertEquals(0, calls)
        }
    }
    @Test fun nativeFinalResultEntryPointMatchesOnceAndRejectsConsentLoss() {
        for ((text, expected) in listOf("Audio Bodyguard skip intro" to OwnedSkipAction.SKIP_INTRO,
                                        "Audio Bodyguard skip recap" to OwnedSkipAction.SKIP_RECAP)) {
            val gate = OwnedVoiceSkipGate()
            val state = player()
            val calls = mutableListOf<OwnedSkipAction>()
            val press: (OwnedSkipAction) -> Boolean = { calls.add(it); true }
            assertTrue(gate.start("voice-1", state))
            assertEquals(OwnedSkipDecision.REQUESTED, gate.requestFinal(text, "voice-1", state, true, true, press))
            assertEquals(OwnedSkipDecision.UNAVAILABLE, gate.requestFinal(text, "voice-1", state, true, true, press))
            assertEquals(listOf(expected), calls)
        }
        for ((permission, foreground) in listOf(false to true, true to false)) {
            val gate = OwnedVoiceSkipGate()
            val state = player()
            var calls = 0
            val press: (OwnedSkipAction) -> Boolean = { calls++; true }
            assertTrue(gate.start("voice-1", state))
            assertEquals(OwnedSkipDecision.UNAVAILABLE,
                gate.requestFinal("Audio Bodyguard skip intro", "voice-1", state, permission, foreground, press))
            assertEquals(OwnedSkipDecision.UNAVAILABLE,
                gate.requestFinal("Audio Bodyguard skip intro", "voice-1", state, true, true, press))
            assertEquals(0, calls)
        }
    }

}
