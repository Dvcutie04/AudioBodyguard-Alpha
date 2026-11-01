package com.aqss.lab.pcm16

import kotlin.test.*

class Pcm16WriteAccountingTest {
    private fun ledger(channels: Int = 2, count: Int = 16, id: Long = 1) =
        Pcm16WriteAccounting.create(id, channels, ShortArray(count) { (it + 10).toShort() })

    private fun complete(ledger: Pcm16WriteAccounting, raw: Int): Pcm16WriteRequest {
        val request = assertNotNull(ledger.beginWrite())
        assertTrue(ledger.returned(request, raw))
        assertTrue(ledger.recordReturn(request))
        return request
    }

    @Test fun checkedSpanKeepsSamplesFramesAndBytesDistinct() {
        val span = Pcm16Span.checked(24, 6, 12, 3)
        assertEquals(6, span.offsetSamples)
        assertEquals(12, span.sampleCount)
        assertEquals(2, span.offsetFrames)
        assertEquals(4, span.frameCount)
        assertEquals(12L, span.offsetBytes)
        assertEquals(24L, span.byteCount)
        val large = Pcm16Span.checked(Int.MAX_VALUE - 1, 0, Int.MAX_VALUE - 1, 2)
        assertEquals(4294967292L, large.byteCount)
    }

    @Test fun malformedBoundsAlignmentAndOverflowRejectBeforeDispatch() {
        val invalid = listOf(
            intArrayOf(-1, 0, 2, 2), intArrayOf(8, -2, 2, 2),
            intArrayOf(8, 0, -2, 2), intArrayOf(8, 0, 0, 2),
            intArrayOf(8, 0, 2, 0), intArrayOf(8, 0, 2, -1),
            intArrayOf(8, 1, 2, 2), intArrayOf(8, 0, 3, 2),
            intArrayOf(7, 0, 2, 2), intArrayOf(8, 8, 2, 2),
            intArrayOf(Int.MAX_VALUE, Int.MAX_VALUE, Int.MAX_VALUE, 1),
        )
        var dispatched = 0
        for (args in invalid) {
            assertFailsWith<IllegalArgumentException> {
                Pcm16Span.checked(args[0], args[1], args[2], args[3])
                dispatched++
            }
        }
        assertEquals(0, dispatched)
    }

    @Test fun sourceAndRequestsCannotMutateTheRetainedSuffix() {
        val source = shortArrayOf(10, 11, 12, 13, 14, 15, 16, 17)
        val owner = Pcm16WriteAccounting.create(9, 2, source)
        source.fill(99)
        val first = assertNotNull(owner.beginWrite())
        first.copySamples().fill(88)
        assertContentEquals(shortArrayOf(10, 11, 12, 13, 14, 15, 16, 17), first.copySamples())
        assertTrue(owner.returned(first, 2))
        assertTrue(owner.recordReturn(first))
        val next = assertNotNull(owner.beginWrite())
        assertEquals(2, next.span.offsetSamples)
        assertContentEquals(shortArrayOf(12, 13, 14, 15, 16, 17), next.copySamples())
    }

    @Test fun partialStereoReturnAdvancesExactlyOneAcceptedPrefix() {
        val owner = ledger(count = 8)
        complete(owner, 2)
        assertEquals(2, owner.accountedSamples)
        assertEquals(1, owner.accountedFrames)
        assertEquals(4L, owner.accountedBytes)
        val suffix = complete(owner, 6)
        assertEquals(2, suffix.span.offsetSamples)
        assertEquals(6, suffix.span.sampleCount)
        assertEquals(8, owner.accountedSamples)
        assertEquals(0, owner.remainingSamples)
        assertNull(owner.beginWrite())
        assertTrue(owner.outcomeUnknown)
    }

    @Test fun zeroPreservesTheSuffixAndRequiresExplicitAccountingAndAnotherAttempt() {
        val owner = ledger(count = 8)
        complete(owner, 2)
        val zero = assertNotNull(owner.beginWrite())
        assertTrue(owner.returned(zero, 0))
        assertNull(owner.beginWrite())
        assertEquals(Pcm16ResultKind.ZERO, owner.trace.last().resultKind)
        assertEquals(0, owner.trace.last().rawValue)
        assertTrue(owner.recordReturn(zero))
        assertEquals(2, owner.accountedSamples)
        assertEquals(2, owner.callsStarted)
        val later = complete(owner, 6)
        assertEquals(zero.span.offsetSamples, later.span.offsetSamples)
        assertContentEquals(zero.copySamples(), later.copySamples())
    }

    @Test fun everyNegativeReturnIsTerminalAndNeverTreatedAsPosixWouldBlock() {
        for (raw in listOf(-1, -2, -3, -6, -11, Int.MIN_VALUE)) {
            val owner = ledger(count = 8)
            complete(owner, 2)
            val request = assertNotNull(owner.beginWrite())
            assertTrue(owner.returned(request, raw))
            assertFalse(owner.admissionOpen)
            assertEquals(Pcm16InhibitReason.NATIVE_ERROR, owner.inhibitReason)
            val event = owner.trace.single { it.callId == request.callId && it.kind == Pcm16EventKind.CALL_RETURNED }
            assertEquals(raw, event.rawValue)
            assertEquals(Pcm16ResultKind.NATIVE_ERROR, event.resultKind)
            assertNull(event.acceptedByCall)
            assertFalse(owner.acknowledgeHold())
            assertTrue(owner.recordReturn(request))
            assertEquals(2, owner.accountedSamples)
            assertNull(owner.beginWrite())
            assertTrue(owner.acknowledgeHold())
            assertTrue(owner.outcomeUnknown)
        }
    }

    @Test fun oversizedAndUnalignedReturnsInhibitWithoutInventingAnAcceptedCount() {
        for (raw in listOf(1, 7, 8, Int.MAX_VALUE)) {
            val owner = ledger(count = 8)
            complete(owner, 2)
            val request = assertNotNull(owner.beginWrite())
            assertTrue(owner.returned(request, raw))
            assertFalse(owner.admissionOpen)
            assertEquals(Pcm16InhibitReason.INVALID_RETURN, owner.inhibitReason)
            val event = owner.trace.first { it.callId == request.callId && it.kind == Pcm16EventKind.CALL_RETURNED }
            assertEquals(Pcm16ResultKind.INVALID_RETURN, event.resultKind)
            assertEquals(raw, event.rawValue)
            assertNull(event.acceptedByCall)
            assertTrue(owner.recordReturn(request))
            assertEquals(2, owner.accountedSamples)
        }
    }

    @Test fun holdBeforeEntryMakesNoScriptedBackendCallAndAcknowledgementIsIdempotent() {
        val owner = ledger()
        owner.hold()
        var backendCalls = 0
        owner.beginWrite()?.let { backendCalls++ }
        assertEquals(0, backendCalls)
        assertFalse(owner.outcomeUnknown)
        assertTrue(owner.acknowledgeHold())
        val trace = owner.trace
        owner.hold()
        assertTrue(owner.acknowledgeHold())
        assertEquals(trace, owner.trace)
        assertEquals(Pcm16InhibitReason.USER_HOLD, owner.inhibitReason)
    }

    @Test fun holdDuringAnEnteredCallRetainsItsActualPositiveReturn() {
        val owner = ledger(count = 8)
        val request = assertNotNull(owner.beginWrite())
        owner.hold()
        assertFalse(owner.acknowledgeHold())
        assertFalse(owner.recordReturn(request))
        assertNull(owner.beginWrite())
        assertTrue(owner.returned(request, 4))
        assertFalse(owner.acknowledgeHold())
        assertEquals(0, owner.accountedSamples)
        assertTrue(owner.recordReturn(request))
        assertEquals(4, owner.accountedSamples)
        assertEquals(4, owner.remainingSamples)
        assertTrue(owner.acknowledgeHold())
        assertNull(owner.beginWrite())
        assertEquals(Pcm16InhibitReason.USER_HOLD, owner.inhibitReason)
        assertEquals(listOf(Pcm16EventKind.CALL_ENTERED, Pcm16EventKind.HOLD_REQUESTED,
            Pcm16EventKind.CALL_RETURNED, Pcm16EventKind.RETURN_RECORDED,
            Pcm16EventKind.HOLD_ACKNOWLEDGED), owner.trace.map { it.kind })
        assertTrue(owner.outcomeUnknown)
    }

    @Test fun holdAfterReturnStillWaitsForAccounting() {
        val owner = ledger()
        val request = assertNotNull(owner.beginWrite())
        assertTrue(owner.returned(request, 4))
        owner.hold()
        assertFalse(owner.acknowledgeHold())
        assertTrue(owner.recordReturn(request))
        assertTrue(owner.acknowledgeHold())
        assertEquals(4, owner.accountedSamples)
    }

    @Test fun oldOrForeignTicketsCannotReturnOrAccountAnotherCall() {
        val owner = ledger()
        val other = ledger()
        val request = assertNotNull(owner.beginWrite())
        val foreign = assertNotNull(other.beginWrite())
        assertEquals(request.callId, foreign.callId)
        assertEquals(request.workId, foreign.workId)
        assertFalse(owner.returned(foreign, 4))
        assertFalse(owner.recordReturn(foreign))
        assertFalse(owner.failed(foreign))
        assertTrue(owner.returned(request, 4))
        assertFalse(owner.returned(request, 4))
        assertTrue(owner.recordReturn(request))
        assertFalse(owner.recordReturn(request))
        val later = assertNotNull(owner.beginWrite())
        assertFalse(owner.returned(request, 4))
        assertFalse(owner.recordReturn(request))
        assertTrue(owner.returned(later, 2))
        assertTrue(owner.recordReturn(later))
        assertEquals(6, owner.accountedSamples)
        assertEquals(0, other.accountedSamples)
    }

    @Test fun traceCapacityPreservesAllCallsAndReservesHoldAndAcknowledgementSpace() {
        val owner = ledger(channels = 1, count = 16)
        repeat(8) { complete(owner, 1) }
        val first = owner.trace
        assertEquals(24, first.size)
        assertNull(owner.beginWrite())
        assertEquals(Pcm16InhibitReason.TRACE_FULL, owner.inhibitReason)
        assertTrue(owner.acknowledgeHold())
        assertEquals(26, owner.trace.size)
        assertEquals(first, owner.trace.take(24))
        assertEquals((1..26).toList(), owner.trace.map { it.sequence })
        assertEquals(8, owner.accountedSamples)
        assertEquals(8, owner.remainingSamples)
        assertEquals(24, first.size)
        @Suppress("UNCHECKED_CAST")
        assertFailsWith<UnsupportedOperationException> { (owner.trace as MutableList<Pcm16TraceEvent>).clear() }
    }

    @Test fun observedExceptionKeepsOwnershipPendingUntilItIsRecorded() {
        val owner = ledger()
        complete(owner, 2)
        val request = assertNotNull(owner.beginWrite())
        assertTrue(owner.failed(request))
        assertFalse(owner.admissionOpen)
        assertFalse(owner.acknowledgeHold())
        val event = owner.trace.first { it.callId == request.callId && it.kind == Pcm16EventKind.CALL_RETURNED }
        assertEquals(Pcm16ResultKind.EXCEPTION, event.resultKind)
        assertNull(event.rawValue)
        assertNull(event.acceptedByCall)
        assertTrue(owner.recordReturn(request))
        assertEquals(2, owner.accountedSamples)
        assertTrue(owner.acknowledgeHold())
        assertTrue(owner.outcomeUnknown)
    }

    @Test fun firstInhibitionReasonSurvivesLaterFailureAndRepeatedHold() {
        val owner = ledger()
        val request = assertNotNull(owner.beginWrite())
        owner.hold()
        assertTrue(owner.returned(request, -6))
        assertTrue(owner.recordReturn(request))
        owner.hold()
        assertEquals(Pcm16InhibitReason.USER_HOLD, owner.inhibitReason)
        assertEquals(1, owner.trace.count { it.kind == Pcm16EventKind.HOLD_REQUESTED })
        assertEquals(Pcm16ResultKind.NATIVE_ERROR, owner.trace.first { it.kind == Pcm16EventKind.CALL_RETURNED }.resultKind)
    }

    @Test fun holdAfterZeroNeverResubmitsTheOldSuffix() {
        val owner = ledger(count = 8)
        complete(owner, 2)
        val zero = complete(owner, 0)
        owner.hold()
        assertTrue(owner.acknowledgeHold())
        repeat(10) { assertNull(owner.beginWrite()) }
        assertEquals(2, owner.callsStarted)
        assertEquals(2, owner.accountedSamples)
        assertEquals(6, owner.remainingSamples)
        assertEquals(2, zero.span.offsetSamples)
        assertTrue(owner.outcomeUnknown)
    }

    @Test fun repeatedZeroReturnsReachAFiniteLimitWithoutAutomaticRetries() {
        val owner = ledger()
        repeat(8) { complete(owner, 0) }
        assertEquals(8, owner.callsStarted)
        assertEquals(0, owner.accountedSamples)
        assertEquals(16, owner.remainingSamples)
        assertNull(owner.beginWrite())
        assertEquals(Pcm16InhibitReason.TRACE_FULL, owner.inhibitReason)
        assertTrue(owner.acknowledgeHold())
        assertTrue(owner.outcomeUnknown)
    }

    @Test fun invalidSourceIdentityOrCapacityCannotCreateAnOwner() {
        for (id in listOf(0L, -1L)) assertFailsWith<IllegalArgumentException> {
            Pcm16WriteAccounting.create(id, 2, ShortArray(4))
        }
        for ((channels, count) in listOf(0 to 4, -1 to 4, 2 to 3, 2 to 0, 1 to 4097)) {
            assertFailsWith<IllegalArgumentException> { ledger(channels, count) }
        }
    }

    @Test fun monoStereoAndOtherChannelCountsKeepExactInterleavedSuffixes() {
        for (channels in listOf(1, 2, 3, 8)) {
            val owner = ledger(channels, channels * 5)
            val copied = mutableListOf<Short>()
            for (frames in listOf(1, 2, 2)) {
                val request = assertNotNull(owner.beginWrite())
                val accepted = frames * channels
                copied.addAll(request.copySamples().take(accepted))
                assertTrue(owner.returned(request, accepted))
                assertTrue(owner.recordReturn(request))
            }
            assertEquals(List(channels * 5) { (it + 10).toShort() }, copied)
            assertEquals(5, owner.accountedFrames)
            assertEquals(channels * 10L, owner.accountedBytes)
            assertTrue(owner.outcomeUnknown)
        }
    }
}
