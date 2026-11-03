package com.aqss.nativefeedback

import java.io.IOException
import java.util.concurrent.CountDownLatch
import java.util.concurrent.TimeUnit
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
}
