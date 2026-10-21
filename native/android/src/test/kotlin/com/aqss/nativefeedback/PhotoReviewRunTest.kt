package com.aqss.nativefeedback

import kotlin.test.*

class PhotoReviewRunTest {
    @Test fun clearBeforeImportRejectsTheLateImage() {
        val run = PhotoReviewRun(); val token = run.select()
        run.clear()
        assertFalse(run.beginReading(token)); assertFalse(run.complete(token))
    }
    @Test fun replacementRejectsOldImportWithoutClosingTheNewSelection() {
        val run = PhotoReviewRun(); val old = run.select(); val current = run.select()
        assertFalse(run.beginReading(old)); assertFalse(run.cancel(old)); assertFalse(run.complete(old))
        assertTrue(run.isSelecting(current)); assertTrue(run.beginReading(current)); assertTrue(run.complete(current))
    }
    @Test fun clearDuringRecognitionRejectsTheLateResult() {
        val run = PhotoReviewRun(); val token = run.select()
        assertTrue(run.beginReading(token)); run.clear()
        assertFalse(run.isReading(token)); assertFalse(run.complete(token))
    }
    @Test fun oneImportAndOneTerminalResultPerSelection() {
        val run = PhotoReviewRun(); val token = run.select()
        assertFalse(run.complete(token)); assertTrue(run.isSelecting(token))
        assertTrue(run.beginReading(token)); assertFalse(run.beginReading(token))
        assertTrue(run.complete(token)); assertFalse(run.complete(token)); assertFalse(run.beginReading(token))
    }
    @Test fun cancelledSelectionCannotReviveAndAnotherSelectionStillWorks() {
        val run = PhotoReviewRun(); val token = run.select()
        assertTrue(run.cancel(token)); assertFalse(run.cancel(token)); assertFalse(run.beginReading(token))
        val current = run.select(); assertTrue(run.beginReading(current)); assertTrue(run.complete(current))
    }
    @Test fun foreignOwnerCannotReadCancelOrCompleteAnotherReview() {
        val first = PhotoReviewRun(); val second = PhotoReviewRun()
        val foreign = first.select(); val current = second.select()
        assertFalse(second.beginReading(foreign)); assertFalse(second.cancel(foreign)); assertFalse(second.complete(foreign))
        assertTrue(second.beginReading(current)); assertTrue(second.complete(current))
    }
    @Test fun oldRecognitionCannotPublishOrCancelAReplacementInProgress() {
        val run = PhotoReviewRun(); val old = run.select(); assertTrue(run.beginReading(old))
        val current = run.select(); assertTrue(run.beginReading(current))
        assertFalse(run.complete(old)); assertFalse(run.cancel(old))
        assertTrue(run.isReading(current)); assertTrue(run.complete(current))
    }
}
