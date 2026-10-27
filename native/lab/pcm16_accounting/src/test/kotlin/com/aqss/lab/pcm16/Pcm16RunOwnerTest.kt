package com.aqss.lab.pcm16

import java.util.ArrayDeque
import kotlin.test.*

class Pcm16RunOwnerTest {
    private fun tick(value: Long, domain: Long = 1) = LabTick(domain, value)
    private fun plan(id: Long = 1, deadline: Long = 100, delay: Long = 5,
                     attempts: Int = 8, capacity: Int = 64) =
        Pcm16RunPlan(id, 2, tick(0), deadline, delay, attempts, 7, capacity)
    private fun admitted() = LabAdmission(true, LabFocus.IMMEDIATE, LabInput.IDLE, 7)
    private fun source() = shortArrayOf(10, 11, 12, 13, 14, 15, 16, 17)

    private class Backend : LabOutputBackend {
        val calls = mutableListOf<LabOperation>()
        val payloads = mutableListOf<List<Short>>()
        val results = ArrayDeque<Int>()
        var failOn: LabOperation? = null
        var fatalOn: LabOperation? = null
        var onCall: ((LabOperation) -> Unit)? = null
        private fun enter(op: LabOperation) {
            calls.add(op)
            onCall?.invoke(op)
            if (op == fatalOn) throw AssertionError("scripted unreported failure")
            if (op == failOn) throw IllegalStateException("scripted observed failure")
        }
        override fun acquire() = enter(LabOperation.ACQUIRE)
        override fun activate() = enter(LabOperation.ACTIVATE)
        override fun write(request: Pcm16WriteRequest): Int {
            enter(LabOperation.WRITE)
            payloads.add(request.copySamples().toList())
            return if (results.isEmpty()) request.span.sampleCount else results.removeFirst()
        }
        override fun quiesce() = enter(LabOperation.QUIESCE)
        override fun discard() = enter(LabOperation.DISCARD)
        override fun release() = enter(LabOperation.RELEASE)
    }

    private fun start(owner: Pcm16RunOwner, backend: Backend, p: Pcm16RunPlan = plan()) =
        assertNotNull(owner.requestStart(p, admitted(), source(), backend))
    private fun advance(owner: Pcm16RunOwner, value: Long? = null): LabTask {
        val task = assertNotNull(owner.pendingTask)
        val now = tick(value ?: task.readyAt)
        assertTrue(owner.execute(task, now))
        assertTrue(owner.record(task, now))
        return task
    }
    private fun activate(owner: Pcm16RunOwner) { advance(owner); advance(owner) }
    private fun drain(owner: Pcm16RunOwner) {
        var steps = 0
        while (owner.pendingTask != null) { check(steps++ < 16); advance(owner) }
    }

    @Test fun unknownDeniedDelayedOrMismatchedAdmissionMakesNoBackendCall() {
        val cases = listOf(LabAdmission(), admitted().copy(foreground = false),
            admitted().copy(focus = LabFocus.UNKNOWN), admitted().copy(focus = LabFocus.DENIED),
            admitted().copy(focus = LabFocus.DELAYED), admitted().copy(input = LabInput.UNKNOWN),
            admitted().copy(input = LabInput.ACTIVE), admitted().copy(input = LabInput.CLOSING),
            admitted().copy(routeRevision = 0), admitted().copy(routeRevision = 8))
        for (context in cases) {
            val owner = Pcm16RunOwner(); val backend = Backend()
            assertNull(owner.requestStart(plan(), context, source(), backend))
            assertTrue(backend.calls.isEmpty())
            assertNull(owner.pendingTask)
            assertFalse(owner.slotOccupied)
            assertEquals(0, owner.historySize)
        }
    }

    @Test fun malformedSourceOrInsufficientTraceReservationRejectsBeforeAcquire() {
        val owner = Pcm16RunOwner(); val backend = Backend()
        for (samples in listOf(ShortArray(0), ShortArray(3), ShortArray(4098))) {
            assertNull(owner.requestStart(plan(), admitted(), samples, backend))
        }
        assertNull(owner.requestStart(plan(capacity = 10), admitted(), source(), backend))
        assertTrue(backend.calls.isEmpty())
        assertEquals(0, owner.historySize)
        assertFalse(owner.slotOccupied)
        start(owner, backend)
    }

    @Test fun invalidPlanBoundsCannotCreateADeadlineOrAttemptBudget() {
        val valid = plan()
        for (change in listOf<() -> Pcm16RunPlan>(
            { valid.copy(workId = 0) }, { valid.copy(channelCount = 0) },
            { valid.copy(startAt = tick(-1)) }, { valid.copy(startAt = tick(0, 0)) },
            { valid.copy(deadlineExclusive = 0) }, { valid.copy(retryDelay = 0) },
            { valid.copy(retryDelay = -1) }, { valid.copy(maxAttempts = 0) },
            { valid.copy(maxAttempts = 9) }, { valid.copy(traceCapacity = 65) },
            { valid.copy(routeRevision = 0) })) assertFailsWith<IllegalArgumentException> { change() }
    }

    @Test fun stopBeforeAcquireCancelsQueuedWorkWithoutCallingBackend() {
        val owner = Pcm16RunOwner(); val backend = Backend(); val run = start(owner, backend)
        val stale = assertNotNull(owner.pendingTask)
        assertTrue(owner.stop(run))
        assertFalse(owner.execute(stale, tick(0)))
        assertTrue(backend.calls.isEmpty())
        assertNull(owner.pendingTask)
        assertFalse(owner.slotOccupied)
        assertEquals(LabRunState.RELEASED, owner.snapshot(run)?.state)
        assertEquals(false, owner.snapshot(run)?.outcomeUnknown)
    }

    @Test fun stopAfterAcquireReleasesWithoutActivationOrWrite() {
        val owner = Pcm16RunOwner(); val backend = Backend(); val run = start(owner, backend)
        advance(owner)
        val activation = assertNotNull(owner.pendingTask)
        owner.stop(run)
        assertFalse(owner.execute(activation, tick(0)))
        drain(owner)
        assertEquals(listOf(LabOperation.ACQUIRE, LabOperation.RELEASE), backend.calls)
        assertFalse(owner.slotOccupied)
    }

    @Test fun enteredAcquireRetainsTheSlotThroughItsReturnAndAccounting() {
        val owner = Pcm16RunOwner(); val backend = Backend(); val run = start(owner, backend)
        val acquire = assertNotNull(owner.pendingTask)
        backend.onCall = {
            if (it == LabOperation.ACQUIRE) {
                owner.stop(run)
                assertNull(owner.pendingTask)
                assertTrue(owner.slotOccupied)
                assertFalse(owner.record(acquire, tick(0)))
                assertNull(owner.requestStart(plan(id = 2), admitted(), source(), Backend()))
            }
        }
        assertTrue(owner.execute(acquire, tick(0)))
        assertTrue(owner.snapshot(run)!!.awaitingAccounting)
        assertNull(owner.pendingTask)
        assertTrue(owner.record(acquire, tick(0)))
        assertEquals(LabOperation.RELEASE, owner.pendingTask?.operation)
        drain(owner)
        assertEquals(listOf(LabOperation.ACQUIRE, LabOperation.RELEASE), backend.calls)
    }

    @Test fun partialReturnAndZeroScheduleOneDelayedExactSuffix() {
        val owner = Pcm16RunOwner(); val backend = Backend(); val run = start(owner, backend)
        backend.results.addAll(listOf(2, 0, 6))
        activate(owner); advance(owner)
        val retry = assertNotNull(owner.pendingTask)
        assertSame(retry, owner.pendingTask)
        assertEquals(5L, retry.readyAt)
        assertFalse(owner.execute(retry, tick(4)))
        assertSame(retry, owner.pendingTask)
        advance(owner, 5); advance(owner, 10)
        assertEquals(listOf(source().toList(), source().drop(2), source().drop(2)), backend.payloads)
        assertEquals(8, owner.snapshot(run)?.accountedSamples)
        assertEquals(3, owner.snapshot(run)?.attempts)
        assertNull(owner.pendingTask)
        assertTrue(owner.slotOccupied)
    }

    @Test fun stopCancelsAnIssuedRetryAndNeverReplaysItsSuffix() {
        val owner = Pcm16RunOwner(); val backend = Backend(); val run = start(owner, backend)
        backend.results.add(2)
        activate(owner); advance(owner)
        val retry = assertNotNull(owner.pendingTask)
        owner.stop(run)
        repeat(4) { assertFalse(owner.execute(retry, tick(5))) }
        drain(owner)
        assertEquals(1, backend.payloads.size)
        assertEquals(2, owner.snapshot(run)?.accountedSamples)
        assertEquals(6, owner.snapshot(run)?.remainingSamples)
        assertTrue(owner.snapshot(run)!!.outcomeUnknown)
    }

    @Test fun stopInsideWriteStillAccountsItsPositivePrefixBeforeCleanup() {
        val owner = Pcm16RunOwner(); val backend = Backend(); val run = start(owner, backend)
        backend.results.add(4); activate(owner)
        val write = assertNotNull(owner.pendingTask)
        backend.onCall = {
            if (it == LabOperation.WRITE) {
                owner.stop(run)
                assertNull(owner.pendingTask)
                assertFalse(owner.record(write, tick(0)))
                assertNull(owner.requestStart(plan(id = 2), admitted(), source(), Backend()))
            }
        }
        assertTrue(owner.execute(write, tick(0)))
        assertEquals(0, owner.snapshot(run)?.accountedSamples)
        assertNull(owner.pendingTask)
        assertTrue(owner.record(write, tick(0)))
        assertEquals(4, owner.snapshot(run)?.accountedSamples)
        assertEquals(LabOperation.QUIESCE, owner.pendingTask?.operation)
        drain(owner)
        assertEquals(listOf(LabOperation.ACQUIRE, LabOperation.ACTIVATE, LabOperation.WRITE,
            LabOperation.QUIESCE, LabOperation.DISCARD, LabOperation.RELEASE), backend.calls)
    }

    @Test fun stopBetweenReturnAndAccountingCannotRetireTheSlot() {
        val owner = Pcm16RunOwner(); val backend = Backend(); val run = start(owner, backend)
        backend.results.add(2); activate(owner)
        val write = assertNotNull(owner.pendingTask)
        assertTrue(owner.execute(write, tick(0)))
        owner.stop(run)
        assertNull(owner.pendingTask)
        assertTrue(owner.slotOccupied)
        assertTrue(owner.snapshot(run)!!.awaitingAccounting)
        assertTrue(owner.record(write, tick(0)))
        drain(owner)
        assertEquals(2, owner.snapshot(run)?.accountedSamples)
    }

    @Test fun negativeOrInvalidReturnClosesAdmissionBeforeRecordingAndPreservesHistory() {
        for (raw in listOf(-6, -11, 1, 8)) {
            val owner = Pcm16RunOwner(); val backend = Backend(); val run = start(owner, backend)
            backend.results.addAll(listOf(2, raw)); activate(owner); advance(owner)
            val write = assertNotNull(owner.pendingTask)
            assertTrue(owner.execute(write, tick(5)))
            assertFalse(owner.snapshot(run)!!.admissionOpen)
            assertNull(owner.pendingTask)
            assertEquals(2, owner.snapshot(run)?.accountedSamples)
            assertTrue(owner.record(write, tick(5)))
            drain(owner)
            val snapshot = owner.snapshot(run)!!
            assertEquals(2, snapshot.accountedSamples)
            assertEquals(raw, snapshot.trace.last { it.operation == LabOperation.WRITE &&
                it.kind == LabTraceKind.CALL_RETURNED }.rawValue)
            assertTrue(snapshot.outcomeUnknown)
        }
    }

    @Test fun repeatedZeroStopsAtTheConfiguredAttemptBudget() {
        val owner = Pcm16RunOwner(); val backend = Backend()
        val run = start(owner, backend, plan(attempts = 3)); backend.results.addAll(listOf(0, 0, 0))
        activate(owner); advance(owner, 0); advance(owner, 5); advance(owner, 10); drain(owner)
        assertEquals(3, backend.payloads.size)
        assertEquals(0, owner.snapshot(run)?.accountedSamples)
        assertEquals(LabStopReason.ATTEMPT_LIMIT, owner.snapshot(run)?.stopReason)
        assertFalse(owner.slotOccupied)
        assertTrue(owner.snapshot(run)!!.outcomeUnknown)
    }

    @Test fun deadlineIsExclusiveAndCheckedBeforeEveryNewBackendEntry() {
        for (stage in listOf(LabOperation.ACQUIRE, LabOperation.ACTIVATE, LabOperation.WRITE)) {
            val owner = Pcm16RunOwner(); val backend = Backend(); val run = start(owner, backend)
            if (stage != LabOperation.ACQUIRE) advance(owner)
            if (stage == LabOperation.WRITE) advance(owner)
            val queued = assertNotNull(owner.pendingTask)
            val before = backend.calls.toList()
            assertFalse(owner.execute(queued, tick(100)))
            assertEquals(before, backend.calls)
            assertEquals(LabStopReason.DEADLINE, owner.snapshot(run)?.stopReason)
            drain(owner)
        }
    }

    @Test fun lateReturnIsAccountedButCannotScheduleMoreOutput() {
        val owner = Pcm16RunOwner(); val backend = Backend(); val run = start(owner, backend)
        backend.results.add(2); activate(owner)
        val write = assertNotNull(owner.pendingTask)
        assertTrue(owner.execute(write, tick(99)))
        assertTrue(owner.record(write, tick(100)))
        assertEquals(2, owner.snapshot(run)?.accountedSamples)
        assertEquals(LabStopReason.DEADLINE, owner.snapshot(run)?.stopReason)
        drain(owner)
        assertEquals(1, backend.payloads.size)
    }

    @Test fun wrongDomainRollbackOrNegativeClockClosesAdmissionWithoutComparingDomains() {
        for (bad in listOf(tick(1, 2), tick(9), tick(-1))) {
            val owner = Pcm16RunOwner(); val backend = Backend(); val run = start(owner, backend)
            activate(owner)
            assertTrue(owner.poll(run, tick(10)))
            val queued = assertNotNull(owner.pendingTask)
            assertFalse(owner.execute(queued, bad))
            assertEquals(LabStopReason.CLOCK_FAULT, owner.snapshot(run)?.stopReason)
            assertFalse(backend.calls.contains(LabOperation.WRITE))
            drain(owner)
        }
    }

    @Test fun badClockAtAccountingPreservesTheReturnedPrefixAndClosesNewWork() {
        val owner = Pcm16RunOwner(); val backend = Backend(); val run = start(owner, backend)
        backend.results.add(2); activate(owner)
        val write = assertNotNull(owner.pendingTask)
        assertTrue(owner.execute(write, tick(5)))
        assertTrue(owner.record(write, tick(4)))
        assertEquals(2, owner.snapshot(run)?.accountedSamples)
        assertEquals(LabStopReason.CLOCK_FAULT, owner.snapshot(run)?.stopReason)
        drain(owner)
    }

    @Test fun retryDelayArithmeticCannotWrapOrExtendTheFixedDeadline() {
        val owner = Pcm16RunOwner(); val backend = Backend()
        val p = plan(deadline = Long.MAX_VALUE, delay = Long.MAX_VALUE)
        val run = start(owner, backend, p); backend.results.add(0)
        activate(owner); advance(owner)
        val task = assertNotNull(owner.pendingTask)
        assertEquals(Long.MAX_VALUE, task.readyAt)
        assertFalse(owner.execute(task, tick(Long.MAX_VALUE)))
        assertEquals(LabStopReason.DEADLINE, owner.snapshot(run)?.stopReason)
        drain(owner)
        assertEquals(1, backend.payloads.size)
    }

    @Test fun eachNegativeLifecycleEventClosesTheRunAndPositiveEventsCannotRestartIt() {
        for (event in listOf(LabEvent.FOCUS_LOSS, LabEvent.FOCUS_DUCK, LabEvent.FOREGROUND_LOSS,
            LabEvent.ROUTE_CHANGE, LabEvent.INPUT_BUSY)) {
            val owner = Pcm16RunOwner(); val backend = Backend(); val run = start(owner, backend)
            activate(owner)
            val stale = assertNotNull(owner.pendingTask)
            assertTrue(owner.notify(run, event))
            for (positive in listOf(LabEvent.FOCUS_GAIN, LabEvent.FOREGROUND_RETURN, LabEvent.ROUTE_RETURN)) {
                assertFalse(owner.notify(run, positive))
            }
            assertFalse(owner.execute(stale, tick(0)))
            drain(owner)
            assertFalse(backend.calls.contains(LabOperation.WRITE))
            assertEquals(LabRunState.RELEASED, owner.snapshot(run)?.state)
        }
    }

    @Test fun foreignAndStaleTasksOrCallbacksCannotChangeTheCurrentRun() {
        val owner = Pcm16RunOwner(); val backend = Backend(); val first = start(owner, backend)
        val oldTask = assertNotNull(owner.pendingTask)
        owner.stop(first)
        val second = start(owner, Backend(), plan(id = 2))
        val current = assertNotNull(owner.pendingTask)
        val foreignOwner = Pcm16RunOwner(); val foreign = start(foreignOwner, Backend())
        assertFalse(owner.execute(oldTask, tick(-1, 9)))
        assertFalse(owner.record(oldTask, tick(0)))
        assertFalse(owner.notify(first, LabEvent.ROUTE_CHANGE))
        assertFalse(owner.notify(foreign, LabEvent.FOCUS_LOSS))
        assertFalse(owner.execute(foreignOwner.pendingTask!!, tick(0)))
        assertFalse(owner.record(foreignOwner.pendingTask!!, tick(0)))
        assertSame(current, owner.pendingTask)
        assertTrue(owner.snapshot(second)!!.admissionOpen)
        assertNull(owner.snapshot(foreign))
    }

    @Test fun acquireExceptionQuarantinesAnUnresolvedAllocationAndBlocksSuccessors() {
        val owner = Pcm16RunOwner(); val backend = Backend(); val run = start(owner, backend)
        backend.failOn = LabOperation.ACQUIRE
        advance(owner)
        assertEquals(LabRunState.QUARANTINED, owner.snapshot(run)?.state)
        assertTrue(owner.slotOccupied)
        assertNull(owner.pendingTask)
        assertNull(owner.requestStart(plan(id = 2), admitted(), source(), Backend()))
        owner.poll(run, tick(1000)); owner.stop(run)
        assertTrue(owner.slotOccupied)
        assertEquals(listOf(LabOperation.ACQUIRE), backend.calls)
    }

    @Test fun activationExceptionStillRequiresCleanupBeforeAnotherRun() {
        val owner = Pcm16RunOwner(); val backend = Backend(); val run = start(owner, backend)
        backend.failOn = LabOperation.ACTIVATE
        activate(owner)
        assertTrue(owner.slotOccupied)
        assertNull(owner.requestStart(plan(id = 2), admitted(), source(), Backend()))
        drain(owner)
        assertEquals(listOf(LabOperation.ACQUIRE, LabOperation.ACTIVATE, LabOperation.QUIESCE,
            LabOperation.DISCARD, LabOperation.RELEASE), backend.calls)
        assertFalse(owner.slotOccupied)
        assertEquals(LabStopReason.ACTIVATE_ERROR, owner.snapshot(run)?.stopReason)
    }

    @Test fun writeExceptionRetainsItsPrefixAndRequiresCleanup() {
        val owner = Pcm16RunOwner(); val backend = Backend(); val run = start(owner, backend)
        backend.results.add(2); activate(owner); advance(owner)
        backend.failOn = LabOperation.WRITE
        advance(owner, 5)
        assertTrue(owner.slotOccupied)
        assertEquals(2, owner.snapshot(run)?.accountedSamples)
        drain(owner)
        assertEquals(LabStopReason.WRITE_ERROR, owner.snapshot(run)?.stopReason)
        assertTrue(owner.snapshot(run)!!.outcomeUnknown)
    }

    @Test fun eachCleanupExceptionQuarantinesWithoutTryingLaterStepsOrFreeingTheSlot() {
        for (op in listOf(LabOperation.QUIESCE, LabOperation.DISCARD, LabOperation.RELEASE)) {
            val owner = Pcm16RunOwner(); val backend = Backend(); val run = start(owner, backend)
            activate(owner); owner.stop(run); backend.failOn = op
            drain(owner)
            val snapshot = owner.snapshot(run)!!
            assertEquals(op, backend.calls.last())
            assertEquals(LabRunState.QUARANTINED, snapshot.state)
            assertTrue(owner.slotOccupied)
            assertNull(owner.pendingTask)
            assertNull(owner.requestStart(plan(id = 2), admitted(), source(), Backend()))
            assertTrue(snapshot.trace.any { it.operation == op && it.kind == LabTraceKind.CALL_RETURNED && it.exception })
            assertTrue(snapshot.trace.any { it.operation == op && it.kind == LabTraceKind.RETURN_RECORDED })
        }
    }

    @Test fun delayedCleanupCannotBeReplacedByTimeoutOrDuplicateDelivery() {
        val owner = Pcm16RunOwner(); val backend = Backend(); val run = start(owner, backend)
        activate(owner); owner.stop(run)
        val quiesce = assertNotNull(owner.pendingTask)
        backend.onCall = {
            if (it == LabOperation.QUIESCE) {
                owner.poll(run, tick(1000))
                assertTrue(owner.slotOccupied)
                assertNull(owner.pendingTask)
                assertFalse(owner.execute(quiesce, tick(1000)))
                assertFalse(owner.record(quiesce, tick(1000)))
                assertNull(owner.requestStart(plan(id = 2), admitted(), source(), Backend()))
            }
        }
        assertTrue(owner.execute(quiesce, tick(0)))
        owner.poll(run, tick(2000))
        assertTrue(owner.slotOccupied)
        assertNull(owner.pendingTask)
        assertTrue(owner.record(quiesce, tick(0)))
        assertFalse(owner.record(quiesce, tick(0)))
        drain(owner)
        assertFalse(owner.slotOccupied)
    }

    @Test fun cleanupContinuesWhenItsClockIsUnavailableOrWrongDomain() {
        val owner = Pcm16RunOwner(); val backend = Backend(); val run = start(owner, backend)
        activate(owner); owner.stop(run)
        repeat(3) {
            val task = assertNotNull(owner.pendingTask)
            assertTrue(owner.execute(task, tick(-1, 0)))
            assertTrue(owner.record(task, tick(-1, 0)))
        }
        assertFalse(owner.slotOccupied)
        assertEquals(LabRunState.RELEASED, owner.snapshot(run)?.state)
    }

    @Test fun slotIsNotReleasedInsideReleaseOrBeforeItsReturnIsRecorded() {
        val owner = Pcm16RunOwner(); val backend = Backend(); val run = start(owner, backend)
        activate(owner); owner.stop(run); advance(owner); advance(owner)
        val release = assertNotNull(owner.pendingTask)
        backend.onCall = {
            if (it == LabOperation.RELEASE) {
                assertTrue(owner.slotOccupied)
                assertNull(owner.requestStart(plan(id = 2), admitted(), source(), Backend()))
            }
        }
        assertTrue(owner.execute(release, tick(0)))
        assertTrue(owner.slotOccupied)
        assertTrue(owner.record(release, tick(0)))
        assertFalse(owner.slotOccupied)
        assertNotNull(owner.requestStart(plan(id = 2), admitted(), source(), Backend()))
        assertEquals(LabRunState.RELEASED, owner.snapshot(run)?.state)
    }

    @Test fun fullyAcceptedDataDoesNotMeanPresentationOrResourceRetirement() {
        val owner = Pcm16RunOwner(); val backend = Backend(); val run = start(owner, backend)
        activate(owner); advance(owner)
        assertEquals(8, owner.snapshot(run)?.accountedSamples)
        assertTrue(owner.snapshot(run)!!.outcomeUnknown)
        assertTrue(owner.slotOccupied)
        assertNull(owner.pendingTask)
        assertTrue(owner.poll(run, tick(99)))
        assertTrue(owner.slotOccupied)
        assertTrue(owner.poll(run, tick(100)))
        drain(owner)
        assertEquals(LabStopReason.DEADLINE, owner.snapshot(run)?.stopReason)
        assertTrue(owner.snapshot(run)!!.outcomeUnknown)
    }

    @Test fun historyAndWorkIdentityAreBoundedAndAnExplicitStartIsRequired() {
        val owner = Pcm16RunOwner(); val backend = Backend(); val first = start(owner, backend)
        activate(owner); advance(owner); owner.stop(first); drain(owner)
        assertNull(owner.requestStart(plan(), admitted(), source(), Backend()))
        assertNull(owner.pendingTask)
        val second = start(owner, Backend(), plan(id = 2))
        owner.stop(second)
        assertEquals(2, owner.historySize)
        assertNull(owner.requestStart(plan(id = 3), admitted(), source(), Backend()))
        assertTrue(owner.snapshot(first)!!.outcomeUnknown)
        assertEquals(8, owner.snapshot(first)?.accountedSamples)
    }

    @Test fun traceReservationCoversMaximumWritesAndAllCleanupWithoutEviction() {
        val p = plan(attempts = 8, capacity = 42)
        val owner = Pcm16RunOwner(); val backend = Backend(); val run = start(owner, backend, p)
        backend.results.addAll(List(8) { 0 })
        activate(owner); repeat(8) { advance(owner, it * 5L) }; drain(owner)
        val snapshot = owner.snapshot(run)!!
        assertEquals(42, snapshot.trace.size)
        assertEquals((1..42).toList(), snapshot.trace.map { it.sequence })
        assertEquals(13, snapshot.trace.count { it.kind == LabTraceKind.CALL_ENTERED })
        assertEquals(13, snapshot.trace.count { it.kind == LabTraceKind.CALL_RETURNED })
        assertEquals(13, snapshot.trace.count { it.kind == LabTraceKind.RETURN_RECORDED })
        val frozen = snapshot.trace
        owner.stop(run)
        assertEquals(frozen, owner.snapshot(run)?.trace)
        @Suppress("UNCHECKED_CAST")
        assertFailsWith<UnsupportedOperationException> { (frozen as MutableList<LabRunTrace>).clear() }
    }

    @Test fun firstStopReasonSurvivesLaterFaultButTheFaultReturnIsStillRecorded() {
        val owner = Pcm16RunOwner(); val backend = Backend(); val run = start(owner, backend)
        activate(owner); backend.results.add(-6)
        backend.onCall = { if (it == LabOperation.WRITE) owner.stop(run) }
        advance(owner); drain(owner)
        val snapshot = owner.snapshot(run)!!
        assertEquals(LabStopReason.USER_STOP, snapshot.stopReason)
        assertEquals(1, snapshot.trace.count { it.kind == LabTraceKind.ADMISSION_CLOSED })
        assertEquals(-6, snapshot.trace.first { it.operation == LabOperation.WRITE &&
            it.kind == LabTraceKind.CALL_RETURNED }.rawValue)
    }

    @Test fun unreportedFailureCannotMakeTheSlotAvailableOrInventReturnAccounting() {
        val owner = Pcm16RunOwner(); val backend = Backend(); val run = start(owner, backend)
        backend.fatalOn = LabOperation.ACQUIRE
        val task = assertNotNull(owner.pendingTask)
        assertFailsWith<AssertionError> { owner.execute(task, tick(0)) }
        owner.stop(run); owner.poll(run, tick(1000))
        assertFalse(owner.record(task, tick(1000)))
        assertNull(owner.pendingTask)
        assertTrue(owner.slotOccupied)
        assertNull(owner.requestStart(plan(id = 2), admitted(), source(), Backend()))
        assertFalse(owner.snapshot(run)!!.trace.any { it.kind == LabTraceKind.CALL_RETURNED })
    }
}
