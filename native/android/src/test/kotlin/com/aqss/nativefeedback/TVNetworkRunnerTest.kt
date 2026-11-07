package com.aqss.nativefeedback

import java.io.IOException
import java.util.concurrent.CountDownLatch
import java.util.concurrent.TimeUnit
import java.util.concurrent.atomic.AtomicInteger
import kotlin.test.*

class TVNetworkRunnerTest {
    private val target = LocalTVTarget.parse("192.168.1.105")!!

    @Test fun oneHostTwoPortsAndNoExtraRetry() {
        val runner = TVNetworkRunner()
        val attempts = mutableListOf<Pair<Int, Int>>()
        val done = CountDownLatch(1)
        var result: TVNetworkResult? = null
        runner.start(target, { object : TVProbeSocket {
            override fun connect(target: LocalTVTarget, port: Int, timeoutMillis: Int) {
                assertEquals("192.168.1.105", target.address)
                attempts.add(port to timeoutMillis); throw IOException()
            }
            override fun close() {}
        } }) { _, value -> result = value; done.countDown() }
        assertTrue(done.await(3, TimeUnit.SECONDS))
        assertEquals(listOf(7345 to 4000, 9000 to 4000), attempts)
        assertEquals(TVNetworkOutcome.NOT_REACHED, result?.outcome)
    }

    @Test fun anAnswerClosesTheSocketAndStopsFallback() {
        val runner = TVNetworkRunner()
        val done = CountDownLatch(1)
        var closes = 0
        var allocations = 0
        var result: TVNetworkResult? = null
        runner.start(target, { allocations++; object : TVProbeSocket {
            override fun connect(target: LocalTVTarget, port: Int, timeoutMillis: Int) {}
            override fun close() { closes++ }
        } }) { _, value -> result = value; done.countDown() }
        assertTrue(done.await(3, TimeUnit.SECONDS))
        assertEquals(TVNetworkResult(TVNetworkOutcome.REACHABLE, 7345), result)
        assertEquals(1, allocations); assertEquals(1, closes)
    }

    @Test fun cancelRetainsEnteredWorkAndSuppressesLateSuccessAndFallback() {
        val runner = TVNetworkRunner()
        val entered = CountDownLatch(1); val release = CountDownLatch(1); val done = CountDownLatch(1)
        var allocations = 0
        var result: TVNetworkResult? = null
        val id = assertNotNull(runner.start(target, { allocations++; object : TVProbeSocket {
            override fun connect(target: LocalTVTarget, port: Int, timeoutMillis: Int) {
                entered.countDown(); assertTrue(release.await(3, TimeUnit.SECONDS))
            }
            override fun close() {} // Scripted native call has not returned yet.
        } }) { _, value -> result = value; done.countDown() })
        assertTrue(entered.await(3, TimeUnit.SECONDS)); runner.cancel(id)
        assertNull(runner.start(target, { error("Must not allocate") }) { _, _ -> })
        release.countDown(); assertTrue(done.await(3, TimeUnit.SECONDS))
        assertEquals(TVNetworkOutcome.STOPPED, result?.outcome); assertEquals(1, allocations)
        val fresh = CountDownLatch(1)
        val freshEntered = CountDownLatch(1); val freshRelease = CountDownLatch(1)
        var freshResult: TVNetworkResult? = null
        assertNotNull(runner.start(target, { object : TVProbeSocket {
            override fun connect(target: LocalTVTarget, port: Int, timeoutMillis: Int) {
                freshEntered.countDown(); assertTrue(freshRelease.await(3, TimeUnit.SECONDS))
            }
            override fun close() {}
        } }) { _, value -> freshResult = value; fresh.countDown() })
        assertTrue(freshEntered.await(3, TimeUnit.SECONDS))
        runner.cancel(id) // A retired token cannot stop its successor.
        freshRelease.countDown()
        assertTrue(fresh.await(3, TimeUnit.SECONDS))
        assertEquals(TVNetworkOutcome.REACHABLE, freshResult?.outcome)
    }

    @Test fun cleanupFailureKeepsTheOwnerQuarantined() {
        val runner = TVNetworkRunner(); val done = CountDownLatch(1)
        var result: TVNetworkResult? = null
        runner.start(target, { object : TVProbeSocket {
            override fun connect(target: LocalTVTarget, port: Int, timeoutMillis: Int) {}
            override fun close() { throw IOException() }
        } }) { _, value -> result = value; done.countDown() }
        assertTrue(done.await(3, TimeUnit.SECONDS))
        assertEquals(TVNetworkOutcome.CLEANUP_UNRESOLVED, result?.outcome)
        assertNull(runner.start(target, { error("Quarantined") }) { _, _ -> })
    }

    @Test fun cancelReturnsWhileSocketCloseIsStillRunning() {
        val runner = TVNetworkRunner()
        val connected = CountDownLatch(1)
        val releaseConnect = CountDownLatch(1)
        val closing = CountDownLatch(1)
        val releaseClose = CountDownLatch(1)
        val cancelReturned = CountDownLatch(1)
        val done = CountDownLatch(1)
        val id = assertNotNull(runner.start(target, { object : TVProbeSocket {
            override fun connect(target: LocalTVTarget, port: Int, timeoutMillis: Int) {
                connected.countDown()
                check(releaseConnect.await(10, TimeUnit.SECONDS))
            }
            override fun close() {
                closing.countDown()
                check(releaseClose.await(10, TimeUnit.SECONDS))
            }
        } }) { _, _ -> done.countDown() })
        assertTrue(connected.await(3, TimeUnit.SECONDS))
        val caller = Thread({
            runner.cancel(id)
            cancelReturned.countDown()
        }, "test-network-cancel-caller").apply { isDaemon = true; start() }
        try {
            assertTrue(closing.await(3, TimeUnit.SECONDS))
            assertTrue(cancelReturned.await(1, TimeUnit.SECONDS), "Stop must return while native close is blocked")
            assertNull(runner.start(target, { error("Close still owns the check") }) { _, _ -> })
        } finally {
            releaseClose.countDown()
            releaseConnect.countDown()
            caller.join(3000)
        }
        assertTrue(done.await(3, TimeUnit.SECONDS))
    }

    @Test fun workerReturnCannotReleaseAnEnteredCancellationClose() {
        verifyCancellationCleanup(closeFails = false)
    }

    @Test fun lateCancellationCloseFailureQuarantinesTheOwner() {
        verifyCancellationCleanup(closeFails = true)
    }

    private fun verifyCancellationCleanup(closeFails: Boolean) {
        val runner = TVNetworkRunner()
        val connected = CountDownLatch(1)
        val releaseConnect = CountDownLatch(1)
        val cancellationClose = CountDownLatch(1)
        val releaseClose = CountDownLatch(1)
        val workerClose = CountDownLatch(1)
        val closeCalls = AtomicInteger()
        val done = CountDownLatch(1)
        var result: TVNetworkResult? = null
        val id = assertNotNull(runner.start(target, { object : TVProbeSocket {
            override fun connect(target: LocalTVTarget, port: Int, timeoutMillis: Int) {
                connected.countDown()
                check(releaseConnect.await(10, TimeUnit.SECONDS))
            }
            override fun close() {
                if (closeCalls.incrementAndGet() == 1) {
                    cancellationClose.countDown()
                    check(releaseClose.await(10, TimeUnit.SECONDS))
                    if (closeFails) throw IOException()
                } else {
                    workerClose.countDown()
                }
            }
        } }) { _, value -> result = value; done.countDown() })
        assertTrue(connected.await(3, TimeUnit.SECONDS))
        val caller = Thread({ repeat(3) { runner.cancel(id) } }, "test-network-cancel-caller")
            .apply { isDaemon = true; start() }
        try {
            assertTrue(cancellationClose.await(3, TimeUnit.SECONDS))
            releaseConnect.countDown()
            assertTrue(workerClose.await(3, TimeUnit.SECONDS))
            assertFalse(done.await(1, TimeUnit.SECONDS), "A result must wait for every entered close to return")
            assertNull(runner.start(target, { error("Cancellation close is still entered") }) { _, _ -> })
        } finally {
            releaseClose.countDown()
            releaseConnect.countDown()
            caller.join(3000)
        }
        assertTrue(done.await(3, TimeUnit.SECONDS))
        assertEquals(if (closeFails) TVNetworkOutcome.CLEANUP_UNRESOLVED else TVNetworkOutcome.STOPPED, result?.outcome)
        assertEquals(2, closeCalls.get())
        if (closeFails) {
            assertNull(runner.start(target, { error("Late close failure must keep quarantine") }) { _, _ -> })
        }
    }
}
