package com.aqss.nativefeedback

import java.util.Collections
import java.util.concurrent.CountDownLatch
import kotlin.test.*

class PhotoWorkSlotTest {
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
