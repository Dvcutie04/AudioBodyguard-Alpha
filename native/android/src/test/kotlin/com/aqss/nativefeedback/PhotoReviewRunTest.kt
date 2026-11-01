package com.aqss.nativefeedback

import kotlin.test.*

class PhotoReviewRunTest {
    @Test fun clearBeforeImportRejectsTheLateImage() {
        val run = PhotoReviewRun { 0L }; val token = run.select()
        run.clear()
        assertFalse(run.beginReading(token)); assertFalse(run.complete(token))
    }
    @Test fun replacementRejectsOldImportWithoutClosingTheNewSelection() {
        val run = PhotoReviewRun { 0L }; val old = run.select(); val current = run.select()
        assertFalse(run.beginReading(old)); assertFalse(run.cancel(old)); assertFalse(run.complete(old))
        assertTrue(run.isSelecting(current)); assertTrue(run.beginReading(current)); assertTrue(run.complete(current))
    }
    @Test fun clearDuringRecognitionRejectsTheLateResult() {
        val run = PhotoReviewRun { 0L }; val token = run.select()
        assertTrue(run.beginReading(token)); run.clear()
        assertFalse(run.isReading(token)); assertFalse(run.complete(token))
    }
    @Test fun oneImportAndOneTerminalResultPerSelection() {
        val run = PhotoReviewRun { 0L }; val token = run.select()
        assertFalse(run.complete(token)); assertTrue(run.isSelecting(token))
        assertTrue(run.beginReading(token)); assertFalse(run.beginReading(token))
        assertTrue(run.complete(token)); assertFalse(run.complete(token)); assertFalse(run.beginReading(token))
    }
    @Test fun cancelledSelectionCannotReviveAndAnotherSelectionStillWorks() {
        val run = PhotoReviewRun { 0L }; val token = run.select()
        assertTrue(run.cancel(token)); assertFalse(run.cancel(token)); assertFalse(run.beginReading(token))
        val current = run.select(); assertTrue(run.beginReading(current)); assertTrue(run.complete(current))
    }
    @Test fun foreignOwnerCannotReadCancelOrCompleteAnotherReview() {
        val first = PhotoReviewRun { 0L }; val second = PhotoReviewRun { 0L }
        val foreign = first.select(); val current = second.select()
        assertFalse(second.beginReading(foreign)); assertFalse(second.cancel(foreign)); assertFalse(second.complete(foreign))
        assertTrue(second.beginReading(current)); assertTrue(second.complete(current))
    }
    @Test fun oldRecognitionCannotPublishOrCancelAReplacementInProgress() {
        val run = PhotoReviewRun { 0L }; val old = run.select(); assertTrue(run.beginReading(old))
        val current = run.select(); assertTrue(run.beginReading(current))
        assertFalse(run.complete(old)); assertFalse(run.cancel(old))
        assertTrue(run.isReading(current)); assertTrue(run.complete(current))
    }
    @Test fun resultJustBeforeTheDeadlineCanComplete() {
        var now = 100L; val run = PhotoReviewRun { now }; val token = run.select()
        assertTrue(run.beginReading(token)); now = 30_099
        assertTrue(run.complete(token)); assertFalse(run.complete(token))
    }
    @Test fun readingExpiresAtTheDeadlineAndCannotRevive() {
        var now = 100L; val run = PhotoReviewRun { now }; val token = run.select()
        assertTrue(run.beginReading(token)); now = 30_100
        assertFalse(run.isReading(token)); assertEquals(PhotoReviewRun.EndReason.timeLimit, run.endReason(token)); now = 101
        assertFalse(run.isReading(token)); assertFalse(run.complete(token))
    }
    @Test fun completionChecksTheDeadlineWithoutATimerTick() {
        var now = 100L; val run = PhotoReviewRun { now }; val token = run.select()
        assertTrue(run.beginReading(token)); now = 30_100
        assertFalse(run.complete(token)); now = 100
        assertFalse(run.complete(token))
    }
    @Test fun clockRollbackDuringReadingLatchesTheReviewOff() {
        var now = 100L; val run = PhotoReviewRun { now }; val token = run.select()
        assertTrue(run.beginReading(token)); now = 101; assertTrue(run.isReading(token))
        now = 100; assertFalse(run.isReading(token)); assertEquals(PhotoReviewRun.EndReason.clockInvalid, run.endReason(token)); now = 102
        assertFalse(run.isReading(token)); assertFalse(run.complete(token))
    }
    @Test fun choosingAPictureDoesNotConsumeItsReadingWindow() {
        var now = 100L; val run = PhotoReviewRun { now }; val token = run.select()
        now = 1_000_000; assertTrue(run.isSelecting(token)); assertTrue(run.beginReading(token))
        now = 1_029_999; assertTrue(run.complete(token))
    }
    @Test fun staleCallbacksDoNotSampleTheClockOrExpireTheReplacement() {
        var now = 100L; var samples = 0
        val run = PhotoReviewRun { samples++; now }; val old = run.select(); assertTrue(run.beginReading(old))
        val token = run.select(); now = 200; assertTrue(run.beginReading(token)); val before = samples
        now = 0; assertFalse(run.isReading(old)); assertFalse(run.complete(old)); assertFalse(run.cancel(old))
        assertEquals(before, samples); now = 201; assertTrue(run.complete(token))
    }
    @Test fun invalidReadingStartCannotBeRecoveredByAnotherCallback() {
        var now = -1L; val run = PhotoReviewRun { now }; val token = run.select()
        assertFalse(run.beginReading(token)); now = 0
        assertFalse(run.beginReading(token)); assertFalse(run.complete(token))
    }
    @Test fun anExpiredReviewCanBeReplacedWithoutItsEndReasonLeaking() {
        var now = 0L; val run = PhotoReviewRun { now }; val old = run.select()
        assertTrue(run.beginReading(old)); now = 30_000; assertFalse(run.complete(old))
        assertEquals(PhotoReviewRun.EndReason.timeLimit, run.endReason(old)); assertFalse(run.isSelecting(old))
        val current = run.select(); assertNull(run.endReason(old)); assertNull(run.endReason(current))
        assertTrue(run.beginReading(current)); assertFalse(run.complete(old)); assertTrue(run.complete(current))
        run.clear(); assertNull(run.endReason(current))
    }
}
