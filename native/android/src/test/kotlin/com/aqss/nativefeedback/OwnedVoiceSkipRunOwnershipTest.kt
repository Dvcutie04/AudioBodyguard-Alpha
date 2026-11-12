package com.aqss.nativefeedback

import kotlin.test.*

class OwnedVoiceSkipRunOwnershipTest {
    private fun player(generation: Int = 1) =
        OwnedSkipSnapshot("owned", "episode-session", "episode", generation, true, true, true, true)

    @Test fun oldFinalDenialCannotStopNewListeningRun() {
        for ((permitted, foreground) in listOf(false to true, true to false)) {
            for ((phrase, expected) in listOf("Audio Bodyguard, skip intro" to OwnedSkipAction.SKIP_INTRO,
                                             "Audio Bodyguard, skip recap" to OwnedSkipAction.SKIP_RECAP)) {
                val gate = OwnedVoiceSkipGate()
                val state = player()
                val calls = mutableListOf<OwnedSkipAction>()
                val press: (OwnedSkipAction) -> Boolean = { calls.add(it); true }
                assertTrue(gate.start("old", state))
                gate.stop()
                assertTrue(gate.start("new", state))
                assertEquals(OwnedSkipDecision.UNAVAILABLE,
                    gate.requestFinal(phrase, "old", state, permitted, foreground, press))
                assertEquals(emptyList(), calls)
                assertEquals(OwnedSkipDecision.REQUESTED,
                    gate.requestFinal(phrase, "new", state, true, true, press))
                assertEquals(listOf(expected), calls)
                assertEquals(OwnedSkipDecision.UNAVAILABLE,
                    gate.requestFinal(phrase, "new", state, true, true, press))
                assertEquals(listOf(expected), calls)
            }
        }
    }

    @Test fun currentDenialInvalidatesRunBeforeOtherRejections() {
        for ((permitted, foreground) in listOf(false to true, true to false)) {
            for (missing in listOf(true, false)) {
                val gate = OwnedVoiceSkipGate()
                val state = player()
                val calls = mutableListOf<OwnedSkipAction>()
                val press: (OwnedSkipAction) -> Boolean = { calls.add(it); true }
                assertTrue(gate.start("current", state))
                val proposal = assertNotNull(gate.propose("Audio Bodyguard, skip intro", true, "current", state))
                assertEquals(OwnedSkipDecision.UNAVAILABLE,
                    gate.request(if (missing) null else proposal, "current",
                        if (missing) state else player(2), permitted, foreground, press))
                assertEquals(emptyList(), calls)
                // Restored permission and state cannot revive a revoked proposal.
                assertEquals(OwnedSkipDecision.UNAVAILABLE,
                    gate.request(proposal, "current", state, true, true, press))
                assertEquals(emptyList(), calls)
                assertFalse(gate.start("current", state))
                assertTrue(gate.start("fresh", state))
                assertEquals(OwnedSkipDecision.REQUESTED,
                    gate.requestFinal("Audio Bodyguard, skip intro", "fresh", state, true, true, press))
                assertEquals(listOf(OwnedSkipAction.SKIP_INTRO), calls)
            }
        }
    }

    @Test fun oldSplitRequestCannotStopNewPendingProposal() {
        for ((permitted, foreground) in listOf(false to true, true to false)) {
            val gate = OwnedVoiceSkipGate()
            val state = player()
            val calls = mutableListOf<OwnedSkipAction>()
            val press: (OwnedSkipAction) -> Boolean = { calls.add(it); true }
            assertTrue(gate.start("old", state))
            val old = assertNotNull(gate.propose("Audio Bodyguard, skip intro", true, "old", state))
            gate.stop()
            assertTrue(gate.start("new", state))
            val new = assertNotNull(gate.propose("Audio Bodyguard, skip recap", true, "new", state))
            assertEquals(OwnedSkipDecision.UNAVAILABLE,
                gate.request(old, "old", state, permitted, foreground, press))
            assertEquals(emptyList(), calls)
            assertEquals(OwnedSkipDecision.REQUESTED,
                gate.request(new, "new", state, true, true, press))
            assertEquals(listOf(OwnedSkipAction.SKIP_RECAP), calls)
        }
    }
}
