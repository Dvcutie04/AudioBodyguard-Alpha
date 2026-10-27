package com.aqss.lab.pcm16

import kotlin.test.*

class LabCallbackFamilyTest {
    private class Metadata { var alive = true; var reads = 0; fun read() { check(alive); reads++ } }
    private class Backend : LabOutputBackend {
        val calls = mutableListOf<LabOperation>()
        var failRelease = false
        var onWrite: (() -> Unit)? = null
        override fun acquire() { calls.add(LabOperation.ACQUIRE) }
        override fun activate() { calls.add(LabOperation.ACTIVATE) }
        override fun write(request: Pcm16WriteRequest): Int {
            calls.add(LabOperation.WRITE); onWrite?.invoke(); return 2
        }
        override fun quiesce() { calls.add(LabOperation.QUIESCE) }
        override fun discard() { calls.add(LabOperation.DISCARD) }
        override fun release() {
            calls.add(LabOperation.RELEASE)
            if (failRelease) throw IllegalStateException("scripted release failure")
        }
    }
    private fun plan(id: Long = 1) = Pcm16RunPlan(id, 2, LabTick(1, 0), 100, 5, 8, 7, 42)
    private fun admitted() = LabAdmission(true, LabFocus.IMMEDIATE, LabInput.IDLE, 7)
    private fun start(owner: Pcm16RunOwner, backend: Backend, id: Long = 1) =
        assertNotNull(owner.requestStart(plan(id), admitted(), ShortArray(16) { it.toShort() }, backend))
    private fun advance(owner: Pcm16RunOwner) {
        val task = assertNotNull(owner.pendingTask)
        val now = LabTick(1, task.readyAt)
        assertTrue(owner.execute(task, now)); assertTrue(owner.record(task, now))
    }
    private fun activate(owner: Pcm16RunOwner) { advance(owner); advance(owner) }
    private fun drain(owner: Pcm16RunOwner) {
        var count = 0
        while (owner.pendingTask != null) { check(count++ < 16); advance(owner) }
    }
    private fun attach(owner: Pcm16RunOwner, run: LabRunToken, metadata: Metadata = Metadata()) =
        assertNotNull(owner.attachCallbacks(run, metadata))

    @Test fun queuedCallbackKeepsTheSlotAndMetadataUntilCleanupDeliveryAndExplicitResume() {
        val owner = Pcm16RunOwner(); val backend = Backend(); val run = start(owner, backend)
        val metadata = Metadata(); val family = attach(owner, run, metadata)
        val queued = assertNotNull(family.queue()); activate(owner)
        owner.stop(run); drain(owner)
        assertTrue(owner.slotOccupied)
        assertTrue(owner.snapshot(run)!!.waitingForReferences)
        assertEquals(1, family.snapshot().queued)
        assertEquals(0, family.snapshot().active)
        assertNull(family.takeMetadata())
        assertFalse(owner.resumeCleanup(run))
        assertEquals(LabCallbackDelivery.CLEANUP_ONLY, family.deliver(queued) { error("closed body ran") })
        assertEquals(0, metadata.reads)
        assertNull(owner.pendingTask)
        assertTrue(owner.slotOccupied)
        assertTrue(owner.resumeCleanup(run))
        assertEquals(LabOperation.RELEASE, owner.pendingTask?.operation)
        advance(owner)
        assertSame(metadata, family.takeMetadata())
        metadata.alive = false
        assertEquals(LabCallbackDelivery.REJECTED, family.deliver(queued) { it.read() })
        assertNull(family.takeMetadata())
        assertFalse(owner.slotOccupied)
    }

    @Test fun activeCallbackCanStopAndRunCleanupButCannotReleaseItsOwnMetadataEarly() {
        val owner = Pcm16RunOwner(); val backend = Backend(); val run = start(owner, backend)
        val metadata = Metadata(); val family = attach(owner, run, metadata)
        val ticket = assertNotNull(family.queue()); activate(owner)
        assertEquals(LabCallbackDelivery.DELIVERED, family.deliver(ticket) {
            it.read(); owner.stop(run); drain(owner)
            assertEquals(1, family.snapshot().active)
            assertFalse(owner.resumeCleanup(run))
            assertNull(family.takeMetadata())
            assertEquals(LabCallbackDelivery.REJECTED, family.deliver(ticket) { error("reentrant replay") })
            assertNull(family.queue())
            assertNull(family.retainChild(ticket))
            assertTrue(owner.slotOccupied)
        })
        assertEquals(0, family.snapshot().active)
        assertNull(owner.pendingTask)
        assertTrue(owner.resumeCleanup(run)); drain(owner)
        assertSame(metadata, family.takeMetadata())
        assertEquals(1, metadata.reads)
    }

    @Test fun retainedChildOutlivesItsParentAndReleasePerformsBookkeepingOnly() {
        val owner = Pcm16RunOwner(); val backend = Backend(); val run = start(owner, backend)
        val metadata = Metadata(); val family = attach(owner, run, metadata)
        val parent = assertNotNull(family.queue()); var child: LabChildTicket? = null
        family.deliver(parent) { child = assertNotNull(family.retainChild(parent)); it.read() }
        assertNull(family.retainChild(parent))
        activate(owner); advance(owner); owner.stop(run); drain(owner)
        val reference = assertNotNull(child)
        assertEquals(1, family.snapshot().retainedChildren)
        assertSame(metadata, family.metadataFor(reference))
        family.metadataFor(reference)!!.read()
        assertNull(family.takeMetadata())
        val calls = backend.calls.toList()
        assertTrue(family.releaseChild(reference))
        assertEquals(calls, backend.calls)
        assertNull(owner.pendingTask)
        assertTrue(owner.slotOccupied)
        assertNull(family.metadataFor(reference))
        assertFalse(family.releaseChild(reference))
        assertTrue(owner.resumeCleanup(run)); drain(owner)
        assertSame(metadata, family.takeMetadata())
        assertEquals(2, owner.snapshot(run)?.accountedSamples)
        assertTrue(owner.snapshot(run)!!.outcomeUnknown)
    }

    @Test fun onlyAnActiveCurrentParentCanRetainAChild() {
        val owner = Pcm16RunOwner(); val run = start(owner, Backend()); val family = attach(owner, run)
        val parent = assertNotNull(family.queue())
        assertNull(family.retainChild(parent))
        val forged = LabCallbackTicket(run, parent.sequence)
        family.deliver(parent) {
            assertNull(family.retainChild(forged))
            assertNotNull(family.retainChild(parent))
        }
        assertNull(family.retainChild(parent))
        assertEquals(1, family.snapshot().retainedChildren)
    }

    @Test fun foreignAndForgedTicketsCannotConsumeAQueuedReference() {
        val owner = Pcm16RunOwner(); val run = start(owner, Backend()); val family = attach(owner, run)
        val other = Pcm16RunOwner(); val foreignRun = start(other, Backend()); val foreign = attach(other, foreignRun)
        val ticket = assertNotNull(family.queue()); val peer = assertNotNull(foreign.queue())
        for (bad in listOf(peer, LabCallbackTicket(run, ticket.sequence), LabCallbackTicket(run, 0),
            LabCallbackTicket(run, Int.MAX_VALUE))) {
            assertEquals(LabCallbackDelivery.REJECTED, family.deliver(bad) { error("invalid body") })
        }
        assertEquals(1, family.snapshot().queued)
        assertEquals(1, foreign.snapshot().queued)
        assertEquals(LabCallbackDelivery.DELIVERED, family.deliver(ticket) { it.read() })
        assertEquals(0, family.snapshot().queued)
    }

    @Test fun foreignForgedAndRepeatedChildReleasesCannotConsumeAnotherReference() {
        val owner = Pcm16RunOwner(); val run = start(owner, Backend()); val family = attach(owner, run)
        val parent = assertNotNull(family.queue()); val children = mutableListOf<LabChildTicket>()
        family.deliver(parent) { repeat(2) { children.add(assertNotNull(family.retainChild(parent))) } }
        val wrong = LabChildTicket(run, children[0].sequence, parent)
        assertFalse(family.releaseChild(wrong))
        assertNull(family.metadataFor(wrong))
        assertFalse(family.releaseChild(LabChildTicket(run, 0, parent)))
        assertFalse(family.releaseChild(LabChildTicket(run, Int.MAX_VALUE, parent)))
        val other = Pcm16RunOwner(); val otherRun = start(other, Backend()); val foreign = attach(other, otherRun)
        val otherParent = assertNotNull(foreign.queue()); var foreignChild: LabChildTicket? = null
        foreign.deliver(otherParent) { foreignChild = assertNotNull(foreign.retainChild(otherParent)) }
        assertFalse(family.releaseChild(foreignChild!!))
        assertNull(family.metadataFor(foreignChild!!))
        assertEquals(1, foreign.snapshot().retainedChildren)
        assertTrue(family.releaseChild(children[0]))
        assertFalse(family.releaseChild(children[0]))
        assertEquals(1, family.snapshot().retainedChildren)
        assertNotNull(family.metadataFor(children[1]))
        assertTrue(family.releaseChild(children[1]))
    }

    @Test fun callbackCapacityClosesAdmissionWithoutDroppingAnyQueuedReferences() {
        val owner = Pcm16RunOwner(); val backend = Backend(); val run = start(owner, backend)
        val family = attach(owner, run); val tickets = List(8) { assertNotNull(family.queue()) }
        activate(owner)
        assertNull(family.queue())
        assertEquals(LabStopReason.REFERENCE_LIMIT, owner.snapshot(run)?.stopReason)
        assertEquals(8, family.snapshot().queued)
        drain(owner)
        assertFalse(backend.calls.contains(LabOperation.RELEASE))
        for (ticket in tickets) assertEquals(LabCallbackDelivery.CLEANUP_ONLY,
            family.deliver(ticket) { error("capacity must keep bodies inhibited") })
        assertNull(owner.pendingTask)
        assertTrue(owner.resumeCleanup(run)); drain(owner)
        assertNotNull(family.takeMetadata())
        assertEquals(8, family.snapshot().callbacksIssued)
        assertNull(family.queue())
    }

    @Test fun childCapacityClosesAdmissionWhileAllRetainedChildrenCanStillDrain() {
        val owner = Pcm16RunOwner(); val backend = Backend(); val run = start(owner, backend)
        val family = attach(owner, run); val parent = assertNotNull(family.queue())
        val children = mutableListOf<LabChildTicket>(); activate(owner)
        family.deliver(parent) {
            repeat(8) { children.add(assertNotNull(family.retainChild(parent))) }
            assertNull(family.retainChild(parent))
            assertEquals(LabStopReason.REFERENCE_LIMIT, owner.snapshot(run)?.stopReason)
        }
        drain(owner)
        assertTrue(owner.slotOccupied)
        for (child in children) { assertNotNull(family.metadataFor(child)); assertTrue(family.releaseChild(child)) }
        assertNull(owner.pendingTask)
        assertTrue(owner.resumeCleanup(run)); drain(owner)
        assertNotNull(family.takeMetadata())
        assertEquals(8, family.snapshot().childrenIssued)
    }

    @Test fun stopBeforeAcquireWaitsForQueuedReferencesWithoutAnyBackendCall() {
        val owner = Pcm16RunOwner(); val backend = Backend(); val run = start(owner, backend)
        val metadata = Metadata(); val family = attach(owner, run, metadata); val ticket = assertNotNull(family.queue())
        owner.stop(run)
        assertTrue(owner.slotOccupied)
        assertNull(owner.pendingTask)
        assertNull(family.takeMetadata())
        assertNull(owner.requestStart(plan(2), admitted(), ShortArray(8), Backend()))
        family.deliver(ticket) { error("closed") }
        assertTrue(backend.calls.isEmpty())
        assertNull(owner.pendingTask)
        assertTrue(owner.resumeCleanup(run))
        assertTrue(backend.calls.isEmpty())
        assertFalse(owner.slotOccupied)
        assertSame(metadata, family.takeMetadata())
    }

    @Test fun liveDeliveryRunsOnceButMetadataStillWaitsForOwnerCleanupAccounting() {
        val owner = Pcm16RunOwner(); val backend = Backend(); val run = start(owner, backend)
        val metadata = Metadata(); val family = attach(owner, run, metadata); val ticket = assertNotNull(family.queue())
        assertEquals(LabCallbackDelivery.DELIVERED, family.deliver(ticket) { it.read() })
        assertEquals(LabCallbackDelivery.REJECTED, family.deliver(ticket) { it.read() })
        assertNull(family.takeMetadata())
        activate(owner); owner.stop(run); advance(owner); advance(owner)
        val release = assertNotNull(owner.pendingTask)
        assertTrue(owner.execute(release, LabTick(1, 0)))
        assertNull(family.takeMetadata())
        assertTrue(owner.record(release, LabTick(1, 0)))
        assertSame(metadata, family.takeMetadata())
        assertEquals(1, metadata.reads)
    }

    @Test fun nestedCallbacksKeepBothActiveReferencesUntilTheirActualReturns() {
        val owner = Pcm16RunOwner(); val backend = Backend(); val run = start(owner, backend)
        val family = attach(owner, run); val first = assertNotNull(family.queue()); val second = assertNotNull(family.queue())
        activate(owner)
        family.deliver(first) {
            family.deliver(second) {
                assertEquals(2, family.snapshot().active)
                owner.stop(run); drain(owner)
                assertFalse(owner.resumeCleanup(run))
                assertNull(family.takeMetadata())
            }
            assertEquals(1, family.snapshot().active)
            assertFalse(owner.resumeCleanup(run))
        }
        assertEquals(0, family.snapshot().active)
        assertTrue(owner.resumeCleanup(run)); drain(owner)
        assertNotNull(family.takeMetadata())
    }

    @Test fun callbackExceptionClosesAdmissionAndRecordsTheActualBodyReturn() {
        val owner = Pcm16RunOwner(); val backend = Backend(); val run = start(owner, backend)
        val family = attach(owner, run); val ticket = assertNotNull(family.queue()); activate(owner)
        assertFailsWith<IllegalArgumentException> {
            family.deliver(ticket) { throw IllegalArgumentException("scripted body failure") }
        }
        assertEquals(LabStopReason.CALLBACK_ERROR, owner.snapshot(run)?.stopReason)
        assertEquals(0, family.snapshot().active)
        assertTrue(family.snapshot().trace.last().exception)
        assertNull(family.queue())
        drain(owner)
        assertFalse(owner.slotOccupied)
        assertNotNull(family.takeMetadata())
    }

    @Test fun callbackFailureCannotDiscardAChildThatOutlivesTheFailedBody() {
        val owner = Pcm16RunOwner(); val backend = Backend(); val run = start(owner, backend)
        val family = attach(owner, run); val parent = assertNotNull(family.queue())
        var child: LabChildTicket? = null; activate(owner)
        assertFailsWith<AssertionError> {
            family.deliver(parent) {
                child = assertNotNull(family.retainChild(parent))
                throw AssertionError("scripted callback failure")
            }
        }
        drain(owner)
        assertTrue(owner.slotOccupied)
        assertNotNull(family.metadataFor(assertNotNull(child)))
        assertTrue(family.releaseChild(child!!))
        assertNull(owner.pendingTask)
        assertTrue(owner.resumeCleanup(run)); drain(owner)
        assertNotNull(family.takeMetadata())
    }

    @Test fun drainingReferencesCannotReleaseAQuarantinedResource() {
        val owner = Pcm16RunOwner(); val backend = Backend(); val run = start(owner, backend)
        val family = attach(owner, run); val parent = assertNotNull(family.queue()); var child: LabChildTicket? = null
        family.deliver(parent) { child = assertNotNull(family.retainChild(parent)) }
        activate(owner); owner.stop(run); drain(owner)
        family.releaseChild(child!!); assertTrue(owner.resumeCleanup(run))
        backend.failRelease = true; drain(owner)
        assertEquals(LabRunState.QUARANTINED, owner.snapshot(run)?.state)
        assertTrue(owner.slotOccupied)
        assertNull(family.takeMetadata())
        assertFalse(owner.resumeCleanup(run))
        assertNull(owner.pendingTask)
    }

    @Test fun timeoutAndPositiveCallbacksDoNotDrainAQueuedReference() {
        val owner = Pcm16RunOwner(); val backend = Backend(); val run = start(owner, backend)
        val family = attach(owner, run); val ticket = assertNotNull(family.queue()); activate(owner)
        owner.stop(run); drain(owner)
        owner.poll(run, LabTick(1, 1000))
        owner.notify(run, LabEvent.FOCUS_GAIN)
        assertEquals(1, family.snapshot().queued)
        assertFalse(owner.resumeCleanup(run))
        assertNull(family.takeMetadata())
        family.deliver(ticket) { error("cleanup only") }
        assertTrue(owner.resumeCleanup(run)); drain(owner)
    }

    @Test fun fullOwnerAndFamilyTracesPreserveCleanupAndMetadataTransferCapacity() {
        val owner = Pcm16RunOwner(); val backend = Backend(); val run = start(owner, backend)
        val metadata = Metadata(); val family = attach(owner, run, metadata)
        val tickets = List(8) { assertNotNull(family.queue()) }; val children = mutableListOf<LabChildTicket>()
        family.deliver(tickets[0]) { repeat(8) { children.add(assertNotNull(family.retainChild(tickets[0]))) } }
        tickets.drop(1).forEach { ticket -> family.deliver(ticket) { it.read() } }
        activate(owner)
        repeat(7) { advance(owner) }
        // Eighth write is also a positive prefix in this scripted profile and
        // consumes the whole 16-sample source; an explicit Stop still follows.
        advance(owner); owner.stop(run); drain(owner)
        assertEquals(38, owner.snapshot(run)?.trace?.size)
        val before = backend.calls.toList()
        children.forEach { assertTrue(family.releaseChild(it)) }
        assertEquals(before, backend.calls)
        assertNull(owner.pendingTask)
        assertTrue(owner.resumeCleanup(run)); drain(owner)
        assertSame(metadata, family.takeMetadata())
        val callbackTrace = family.snapshot().trace
        assertEquals(42, callbackTrace.size)
        assertEquals((1..42).toList(), callbackTrace.map { it.sequence })
        assertEquals(42, owner.snapshot(run)?.trace?.size)
        @Suppress("UNCHECKED_CAST")
        assertFailsWith<UnsupportedOperationException> { (callbackTrace as MutableList<LabCallbackTrace>).clear() }
        assertTrue(owner.snapshot(run)!!.outcomeUnknown)
    }

    @Test fun metadataTransferAndOldTicketsCannotAffectAnExplicitSuccessor() {
        val owner = Pcm16RunOwner(); val backend = Backend(); val first = start(owner, backend)
        val oldMetadata = Metadata(); val old = attach(owner, first, oldMetadata)
        val ticket = assertNotNull(old.queue()); owner.stop(first)
        old.deliver(ticket) { error("closed") }; assertTrue(owner.resumeCleanup(first))
        assertSame(oldMetadata, old.takeMetadata()); oldMetadata.alive = false
        val second = start(owner, Backend(), 2); val current = attach(owner, second)
        val pending = assertNotNull(owner.pendingTask)
        assertEquals(LabCallbackDelivery.REJECTED, old.deliver(ticket) { it.read() })
        assertEquals(LabCallbackDelivery.REJECTED, current.deliver(ticket) { error("foreign") })
        assertNull(old.queue()); assertNull(old.takeMetadata())
        assertFalse(owner.resumeCleanup(first))
        assertSame(pending, owner.pendingTask)
        assertTrue(owner.snapshot(second)!!.admissionOpen)
    }

    @Test fun callbackAttachmentCannotReplaceALiveFamilyOrAttachToClosedOrForeignRun() {
        val owner = Pcm16RunOwner(); val backend = Backend(); val run = start(owner, backend)
        val metadata = Metadata(); val family = attach(owner, run, metadata)
        assertNull(owner.attachCallbacks(run, Metadata()))
        val foreignOwner = Pcm16RunOwner(); val foreign = start(foreignOwner, Backend())
        assertNull(owner.attachCallbacks(foreign, Metadata()))
        owner.stop(run)
        assertNull(owner.attachCallbacks(run, Metadata()))
        assertSame(metadata, family.takeMetadata())
        assertNull(owner.snapshot(foreign))
    }

    @Test fun drainedCallbackReferencesCannotBypassAnEnteredWritesReturnAccounting() {
        val owner = Pcm16RunOwner(); val backend = Backend(); val run = start(owner, backend)
        val metadata = Metadata(); val family = attach(owner, run, metadata)
        val parent = assertNotNull(family.queue()); var child: LabChildTicket? = null
        activate(owner)
        backend.onWrite = {
            family.deliver(parent) {
                child = assertNotNull(family.retainChild(parent))
                owner.stop(run)
                assertNull(owner.pendingTask)
                assertFalse(owner.resumeCleanup(run))
                assertNull(family.takeMetadata())
            }
        }
        val write = assertNotNull(owner.pendingTask)
        assertTrue(owner.execute(write, LabTick(1, 0)))
        assertTrue(family.releaseChild(assertNotNull(child)))
        assertTrue(family.referencesDrained)
        assertEquals(0, owner.snapshot(run)?.accountedSamples)
        assertFalse(owner.resumeCleanup(run))
        assertNull(owner.pendingTask)
        assertNull(family.takeMetadata())
        assertTrue(owner.record(write, LabTick(1, 0)))
        drain(owner)
        assertEquals(2, owner.snapshot(run)?.accountedSamples)
        assertTrue(owner.snapshot(run)!!.outcomeUnknown)
        assertSame(metadata, family.takeMetadata())
    }
}
