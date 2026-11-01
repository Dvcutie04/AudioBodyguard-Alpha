package com.aqss.nativefeedback

import java.util.Collections
import java.util.concurrent.CountDownLatch
import kotlin.test.*

class PhotoWorkSlotTest {
    @Test fun onlyTheRealOwnerReturnNotifiesAvailability() {
        val slot = PhotoWorkSlot(); var calls = 0
        val observer = slot.observe { calls++ }
        val work = assertNotNull(slot.acquire()); val foreign = assertNotNull(PhotoWorkSlot().acquire())
        assertEquals(0, calls); assertFalse(slot.release(foreign)); assertEquals(0, calls)
        assertTrue(slot.release(work)); assertEquals(1, calls)
        assertFalse(slot.release(work)); assertEquals(1, calls)
        val next = assertNotNull(slot.acquire()); assertEquals(1, calls)
        assertTrue(slot.release(next)); assertEquals(2, calls); observer.close()
    }
    @Test fun detachedViewsDoNotReceiveLaterAvailabilitySignals() {
        val slot = PhotoWorkSlot(); var closedCalls = 0; var liveCalls = 0
        val closed = slot.observe { closedCalls++ }; val live = slot.observe { liveCalls++ }
        closed.close(); closed.close()
        assertTrue(slot.release(assertNotNull(slot.acquire())))
        assertEquals(0, closedCalls); assertEquals(1, liveCalls)
        live.close(); assertTrue(slot.release(assertNotNull(slot.acquire()))); assertEquals(1, liveCalls)
    }
    @Test fun availabilityCallbacksRunOutsideTheSlotLock() {
        val slot = PhotoWorkSlot(); var called = false
        val observer = slot.observe {
            called = true
            val available = java.util.concurrent.atomic.AtomicBoolean(false)
            val query = Thread { available.set(!slot.occupied) }.apply { start() }
            query.join(5000); assertFalse(query.isAlive); assertTrue(available.get())
        }
        assertTrue(slot.release(assertNotNull(slot.acquire()))); assertTrue(called); observer.close()
    }
    @Test fun aBrokenViewCannotPreventCleanupOrOtherNotifications() {
        val slot = PhotoWorkSlot(); var calls = 0
        val broken = slot.observe { throw IllegalStateException("View unavailable") }
        val live = slot.observe { calls++ }
        assertTrue(slot.release(assertNotNull(slot.acquire()))); assertFalse(slot.occupied); assertEquals(1, calls)
        broken.close(); live.close()
    }
    @Test fun oneReadOwnsCapacityUntilItsActualReturn() {
        val slot = PhotoWorkSlot(); assertFalse(slot.occupied)
        val work = assertNotNull(slot.acquire()); assertTrue(slot.occupied)
        repeat(100) { assertNull(slot.acquire()) }
        assertTrue(slot.release(work)); assertFalse(slot.occupied)
        assertNotNull(slot.acquire())
    }
    @Test fun aForeignLeaseCannotFreeTheOccupiedSlot() {
        val slot = PhotoWorkSlot(); val work = assertNotNull(slot.acquire())
        val foreign = assertNotNull(PhotoWorkSlot().acquire())
        assertFalse(slot.release(foreign)); assertTrue(slot.occupied); assertNull(slot.acquire())
        assertTrue(slot.release(work))
    }
    @Test fun duplicateReturnCannotFreeTheNextRead() {
        val slot = PhotoWorkSlot(); val old = assertNotNull(slot.acquire())
        assertTrue(slot.release(old)); assertFalse(slot.release(old))
        val current = assertNotNull(slot.acquire()); assertNotSame(old, current)
        assertFalse(slot.release(old)); assertNull(slot.acquire()); assertTrue(slot.release(current))
    }
    @Test fun clearingAnExpiredReviewDoesNotSettleItsRead() {
        val slot = PhotoWorkSlot(); var now = 0L
        val oldView = PhotoReviewRun { now }; val token = oldView.select()
        val work = assertNotNull(slot.acquire()); assertTrue(oldView.beginReading(token))
        now = 30_000; assertFalse(oldView.complete(token)); oldView.clear()
        val newView = PhotoReviewRun { now }; val next = newView.select()
        assertTrue(newView.isSelecting(next)); assertTrue(slot.occupied); assertNull(slot.acquire())
        assertTrue(slot.release(work)); assertFalse(oldView.complete(token))
        val current = assertNotNull(slot.acquire()); assertTrue(newView.beginReading(next))
        assertTrue(newView.complete(next)); assertTrue(slot.release(current))
    }
    @Test fun publishingAResultDoesNotSettleItsCleanup() {
        val slot = PhotoWorkSlot(); val run = PhotoReviewRun { 0L }; val token = run.select()
        val work = assertNotNull(slot.acquire()); assertTrue(run.beginReading(token)); assertTrue(run.complete(token))
        run.clear(); assertNull(slot.acquire()); assertTrue(slot.release(work)); assertNotNull(slot.acquire())
    }
    @Test fun closingASelectingViewDoesNotOwnOrReleaseAnotherRead() {
        val slot = PhotoWorkSlot(); val work = assertNotNull(slot.acquire())
        val chooser = PhotoReviewRun { 0L }; val token = chooser.select()
        assertTrue(chooser.cancel(token)); chooser.clear()
        assertNull(slot.acquire()); assertTrue(slot.release(work))
    }
    @Test fun simultaneousCallersAdmitExactlyOneRead() {
        val slot = PhotoWorkSlot(); val start = CountDownLatch(1)
        val admitted = Collections.synchronizedList(mutableListOf<PhotoWorkSlot.Lease>())
        val callers = List(16) { Thread { start.await(); slot.acquire()?.let { admitted.add(it) } }.apply { start() } }
        start.countDown(); callers.forEach { it.join(5000); assertFalse(it.isAlive) }
        assertEquals(1, admitted.size); assertTrue(slot.occupied)
        assertTrue(slot.release(admitted.single())); assertFalse(slot.occupied)
    }
}
