package com.aqss.nativefeedback

import kotlin.test.*

class SoundCheckRecapsTest {
    @Test fun supportReportDoesNotInventCompletedChecksFromAnActiveDraft() {
        val store = SoundCheckRecaps()
        store.observe(assertNotNull(store.begin()))
        assertEquals(
            "Recent sound checks (this app session)\nNo completed sound checks in this app session.\n\nInput observations only; not proof of sound safety, protection or TV control.",
            soundCheckSupportReportSection(store.snapshot()),
        )
    }

    @Test fun onlyFinishedChecksAppearAndZeroInputIsNotSilence() {
        val store = SoundCheckRecaps()
        val run = assertNotNull(store.begin())
        assertTrue(store.snapshot().isEmpty())
        assertTrue(store.finish(run, SoundCheckEnd.NO_SAMPLES))
        assertEquals(listOf(SoundCheckRecap(false, SoundCheckEnd.NO_SAMPLES)), store.snapshot())
        assertFalse(store.finish(run, SoundCheckEnd.STOPPED_BY_USER))
    }

    @Test fun lateObservationsAndFinishesCannotChangeANewerCheck() {
        val store = SoundCheckRecaps()
        val old = assertNotNull(store.begin())
        assertNull(store.begin())
        assertTrue(store.observe(old))
        assertTrue(store.finish(old, SoundCheckEnd.LEFT_SCREEN))
        val current = assertNotNull(store.begin())
        assertFalse(store.observe(old))
        assertFalse(store.finish(old, SoundCheckEnd.TIME_LIMIT))
        assertTrue(store.finish(current, SoundCheckEnd.COULD_NOT_START))
        assertEquals(false, store.snapshot()[0].inputObserved)
        assertEquals(true, store.snapshot()[1].inputObserved)
    }

    @Test fun onlyTheFiveNewestSummariesSurviveAndSnapshotsAreIndependent() {
        val store = SoundCheckRecaps()
        val ends = SoundCheckEnd.entries.take(6)
        for (end in ends) store.finish(assertNotNull(store.begin()), end)
        val before = store.snapshot()
        assertEquals(ends.drop(1).reversed(), before.map { it.end })
        store.clear()
        assertEquals(5, before.size)
        assertTrue(store.snapshot().isEmpty())
        assertTrue(SoundCheckRecaps().snapshot().isEmpty())
    }

    @Test fun clearDiscardsAnUnfinishedCheckAndRejectsItsLatePublication() {
        val store = SoundCheckRecaps()
        val old = assertNotNull(store.begin())
        store.observe(old)
        store.clear()
        val current = assertNotNull(store.begin())
        assertFalse(store.observe(old))
        assertFalse(store.finish(old, SoundCheckEnd.CLEANUP_FAILED))
        assertTrue(store.finish(current, SoundCheckEnd.TIME_LIMIT))
        assertEquals(listOf(SoundCheckRecap(false, SoundCheckEnd.TIME_LIMIT)), store.snapshot())
    }

    @Test fun clearingRecapsCannotUnlockMicrophoneCleanupFailure() {
        val gate = ForegroundMicrophoneGate()
        val owner = assertNotNull(gate.acquire())
        gate.release(owner, cleanupSucceeded = false)
        SoundCheckRecaps.process.clear()
        assertTrue(gate.blocked)
        assertNull(gate.acquire())
    }
}
