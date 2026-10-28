package com.aqss.nativefeedback

import kotlin.test.*
import org.junit.Test

/** Synthetic presentation inputs only; no playback or hardware observations. */
class QuietOutputGuidanceTest {
    private fun result(reason: QuietStop = QuietStop.COMPLETE, cleanup: Boolean = true,
                       quarantined: Boolean = false, unreported: Boolean = false) = QuietOutputResult(
        runId = "synthetic-guidance", reason = reason, acceptedSamples = 0, attempts = 0,
        cleanupSucceeded = cleanup, quarantined = quarantined, allocationEntered = false,
        trackOpened = false, focusGranted = false, zeroGainAccepted = null,
        constructed = null, routes = null, requestedBufferBytes = null,
        unreportedCall = unreported, trace = emptyList())

    @Test fun everyKnownReasonHasDistinctGuidanceWithoutChangingItsResult() {
        val messages = QuietStop.entries.map { reason ->
            val original = result(reason)
            val view = QuietOutputGuidance.from(original, processBlocked = false)
            assertTrue(view.canStart); assertTrue(view.canReview)
            assertTrue(view.message.isNotBlank())
            assertFalse(view.message.contains(reason.name), view.message)
            assertEquals(reason, original.reason)
            assertTrue(original.trace.isEmpty()); assertFalse(original.physicalOutputVerified)
            view.message
        }
        assertEquals(QuietStop.entries.size, messages.toSet().size)
    }

    @Test fun interruptionsExplainTheObservedCauseAndRequireAnExplicitNewCheck() {
        for ((reason, cause) in listOf(QuietStop.USER to "you stopped", QuietStop.INACTIVE to "focus",
            QuietStop.FOCUS_LOSS to "audio focus", QuietStop.ROUTE_CHANGED to "notice",
            QuietStop.WORKER_INTERRUPTED to "interrupted")) {
            val text = QuietOutputGuidance.from(result(reason), false).message.lowercase()
            assertTrue(text.contains(cause), text)
            assertTrue(text.contains("new check"), text)
        }
    }

    @Test fun setupWriteAndLimitProblemsDoNotCollapseIntoOneGenericMessage() {
        for ((reason, clue) in listOf(QuietStop.FOCUS_DENIED to "not grant", QuietStop.BUSY to "wait",
            QuietStop.UNSUPPORTED to "configuration", QuietStop.TIME_LIMIT to "time budget",
            QuietStop.ATTEMPT_LIMIT to "full quiet test", QuietStop.WRITE_FAILED to "write",
            QuietStop.INVALID_RESULT to "unexpected", QuietStop.BACKEND_FAILED to "playback problem")) {
            val text = QuietOutputGuidance.from(result(reason), false).message.lowercase()
            assertTrue(text.contains(clue), text)
        }
    }

    @Test fun controlClockFailureDoesNotTellTheOwnerToChangeTheirCalendarClock() {
        val text = QuietOutputGuidance.from(result(QuietStop.CLOCK_FAULT), false).message.lowercase()
        assertTrue(text.contains("timing")); assertTrue(text.contains("report"))
        assertFalse(text.contains("date")); assertFalse(text.contains("settings"))
    }

    @Test fun unresolvedCleanupOverridesEveryReasonAndPreservesReportBeforeForceStop() {
        for (reason in QuietStop.entries) for (mode in 0..3) {
            val view = QuietOutputGuidance.from(result(reason, cleanup = mode != 0,
                quarantined = mode == 1, unreported = mode == 2), processBlocked = mode == 3)
            assertFalse(view.canStart, "$reason mode=$mode")
            assertTrue(view.canReview, "$reason mode=$mode")
            val text = view.message.lowercase()
            assertTrue(text.contains("unresolved"))
            assertTrue(text.indexOf("review") >= 0 && text.indexOf("review") < text.indexOf("force stop"))
            assertTrue(text.contains("android settings"))
        }
    }

    @Test fun completedFrameworkResultDoesNotBecomeASilenceOrProtectionClaim() {
        val view = QuietOutputGuidance.from(result(), false)
        assertTrue(view.canReview); assertTrue(view.canStart)
        assertTrue(view.message.contains("Android")); assertTrue(view.message.contains("report"))
        for (claim in listOf("silent", "safe", "protected", "verified")) {
            assertFalse(view.message.lowercase().contains(claim))
        }
    }

    @Test fun missingResultDoesNotInventAStartFailureOrOfferANonexistentReport() {
        val view = QuietOutputGuidance.from(null, false)
        assertTrue(view.canStart); assertFalse(view.canReview)
        assertTrue(view.message.contains("No check report is available"))
        assertFalse(view.message.contains("could not start"))
    }

    @Test fun processBlockWithoutAResultStillInhibitsStartWithoutAReviewPrompt() {
        val view = QuietOutputGuidance.from(null, true)
        assertFalse(view.canStart); assertFalse(view.canReview)
        assertTrue(view.message.lowercase().contains("force stop"))
        assertFalse(view.message.lowercase().contains("review"))
    }
}
