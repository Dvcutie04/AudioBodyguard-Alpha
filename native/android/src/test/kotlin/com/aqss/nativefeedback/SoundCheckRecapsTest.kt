package com.aqss.nativefeedback

import kotlin.test.*

class SoundCheckRecapsTest {
    @Test fun excludedRecapsShareOnlyTheExactInstalledMetadata() {
        val metadata = "Audio Bodyguard\nPlatform: Android\nVersion: test-version\nBuild: 20"
        val report = PrivateSupportReportSnapshot(metadata, listOf(
            SoundCheckRecap(true, SoundCheckEnd.STOPPED_BY_USER),
            SoundCheckRecap(false, SoundCheckEnd.PERMISSION_CHANGED),
        ))
        assertEquals(metadata, report.text(includeRecentChecks = false))
    }

    @Test fun supportReportKeepsNewestFirstAndDoesNotCallMissingInputSilence() {
        val text = soundCheckSupportReportSection(listOf(
            SoundCheckRecap(true, SoundCheckEnd.STOPPED_BY_USER),
            SoundCheckRecap(false, SoundCheckEnd.NO_SAMPLES),
        ))
        assertEquals("Recent sound checks (this app session)\nCheck 1: Input samples observed\nStopped by you\n\nCheck 2: No input samples observed\nNo current input samples\n\nInput observations only; not proof of sound safety, protection or TV control.", text)
    }

    @Test fun supportReportDefensivelyExcludesASixthCompletedRow() {
        val rows = listOf(SoundCheckEnd.STOPPED_BY_USER, SoundCheckEnd.TIME_LIMIT,
            SoundCheckEnd.PERMISSION_CHANGED, SoundCheckEnd.INPUT_BLOCKED,
            SoundCheckEnd.CLEANUP_FAILED, SoundCheckEnd.CLOSED).map { SoundCheckRecap(false, it) }
        val text = soundCheckSupportReportSection(rows)
        assertEquals(5, Regex("^Check [1-5]:", RegexOption.MULTILINE).findAll(text).count())
        assertFalse(text.contains("Check 6"))
        assertFalse(text.contains("Sound check closed"))
        assertTrue(text.contains("Input cleanup failed; restart the app before retrying"))
    }

    @Test fun aNewReportAfterClearIsEmptyWhileTheReviewedSnapshotStaysFixed() {
        val store = SoundCheckRecaps()
        val run = assertNotNull(store.begin()); store.observe(run); store.finish(run, SoundCheckEnd.STOPPED_BY_USER)
        val snapshot = store.snapshot()
        val reviewed = soundCheckSupportReportSection(snapshot)
        store.clear()
        assertTrue(reviewed.contains("Check 1: Input samples observed\nStopped by you"))
        assertEquals(reviewed, soundCheckSupportReportSection(snapshot))
        assertTrue(soundCheckSupportReportSection(store.snapshot()).contains("No completed sound checks in this app session."))
    }

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
