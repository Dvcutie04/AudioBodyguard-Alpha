package com.aqss.nativefeedback

import java.util.concurrent.CountDownLatch
import java.util.concurrent.TimeUnit
import java.util.concurrent.atomic.AtomicInteger
import kotlin.concurrent.thread
import kotlin.test.*

class QuietOutputCheckTest {
    private class Port : QuietOutputBackend, QuietOutputTrack {
        val calls = mutableListOf<QuietOperation>()
        val slices = mutableListOf<Pair<Int, List<Short>>>()
        val returns = java.util.ArrayDeque<Int>()
        var focus = 1
        var minimum = 512
        var gain = 0
        var configured = QuietOutputFormat(true, 48000, 1, true, 256, 256)
        var fail: QuietOperation? = null
        var fatal: QuietOperation? = null
        var hook: ((QuietOperation) -> Unit)? = null
        private var owned: QuietOutputTrack? = null
        override val track: QuietOutputTrack? get() = owned
        private fun enter(op: QuietOperation) {
            calls.add(op); hook?.invoke(op)
            if (fatal == op) throw AssertionError("unreported scripted failure")
            if (fail == op) throw IllegalStateException("scripted API exception")
        }
        override fun minimumBufferBytes(): Int { enter(QuietOperation.MINIMUM); return minimum }
        override fun requestFocus(): Int { enter(QuietOperation.FOCUS); return focus }
        override fun open(bufferBytes: Int) { enter(QuietOperation.OPEN); check(bufferBytes in 512..262144); owned = this }
        override fun retireCallbacks() { enter(QuietOperation.RETIRE) }
        override fun abandonFocus(): Int { enter(QuietOperation.ABANDON); return 1 }
        override fun format(): QuietOutputFormat { enter(QuietOperation.FORMAT); return configured }
        override fun zeroGain(): Int { enter(QuietOperation.ZERO_GAIN); return gain }
        override fun watchRoute() { enter(QuietOperation.WATCH) }
        override fun play() { enter(QuietOperation.PLAY) }
        override fun write(samples: ShortArray, offset: Int, count: Int): Int {
            enter(QuietOperation.WRITE); slices.add(offset to samples.copyOfRange(offset, offset + count).toList())
            return if (returns.isEmpty()) count else returns.removeFirst()
        }
        override fun routes(): QuietOutputRoutes { enter(QuietOperation.ROUTES); return QuietOutputRoutes.from(listOf(2), 1, true) }
        override fun pause() { enter(QuietOperation.PAUSE) }
        override fun flush() { enter(QuietOperation.FLUSH) }
        override fun unwatchRoute() { enter(QuietOperation.UNWATCH) }
        override fun release() { enter(QuietOperation.RELEASE) }
    }
    private fun check(port: Port = Port(), gate: ForegroundAudioExclusion = ForegroundAudioExclusion(),
                      control: QuietOutputControl = QuietOutputControl(), clock: () -> Long = { 100 },
                      foreground: () -> Boolean = { true }, pause: (Long) -> Unit = {}) =
        QuietOutputCheck(gate, control, { port }, clock, foreground, pause)

    @Test fun sharedExclusionRetainsInputAndOutputUntilActualCleanupReturns() {
        val shared = ForegroundAudioExclusion(); val microphone = ForegroundMicrophoneGate(shared)
        val input = assertNotNull(microphone.acquire())
        assertNull(shared.acquire(ForegroundAudioExclusion.Tool.OUTPUT, Any()))
        assertTrue(microphone.release(input, true))
        val output = assertNotNull(shared.acquire(ForegroundAudioExclusion.Tool.OUTPUT, Any()))
        assertNull(microphone.acquire())
        assertTrue(shared.release(output, true))
        assertNotNull(microphone.acquire())
    }

    @Test fun failedCleanupQuarantinesBothToolsAndStaleLeaseCannotClearIt() {
        val shared = ForegroundAudioExclusion(); val microphone = ForegroundMicrophoneGate(shared)
        val old = assertNotNull(shared.acquire(ForegroundAudioExclusion.Tool.OUTPUT, Any()))
        assertTrue(shared.release(old, true))
        val current = assertNotNull(shared.acquire(ForegroundAudioExclusion.Tool.OUTPUT, Any()))
        assertFalse(shared.release(old, false)); assertFalse(shared.blocked)
        assertFalse(shared.release(current, false)); assertTrue(shared.blocked)
        assertTrue(microphone.blocked); assertNull(microphone.acquire())
        assertFalse(shared.release(current, true))
    }

    @Test fun simultaneousInputAndOutputReservationsHaveOnlyOneWinner() {
        val gate = ForegroundAudioExclusion(); val go = CountDownLatch(1); val ready = CountDownLatch(2)
        val wins = AtomicInteger()
        val jobs = ForegroundAudioExclusion.Tool.entries.map { kind -> thread {
            ready.countDown(); go.await()
            if (gate.acquire(kind, Any()) != null) wins.incrementAndGet()
        } }
        assertTrue(ready.await(5, TimeUnit.SECONDS)); go.countDown()
        jobs.forEach { it.join(5000); assertFalse(it.isAlive) }
        assertEquals(1, wins.get())
    }

    @Test fun stoppedInactiveOrBusyAdmissionCallsNoBackendFactory() {
        for (mode in 0..2) {
            val gate = ForegroundAudioExclusion(); val control = QuietOutputControl(); var constructed = 0
            if (mode == 0) control.stop(QuietStop.USER)
            if (mode == 2) gate.acquire(ForegroundAudioExclusion.Tool.INPUT, Any())
            val run = QuietOutputCheck(gate, control, { constructed++; Port() }, { 100 }, { mode != 1 }, {})
            val result = run.execute()
            assertEquals(0, constructed)
            assertEquals(0, result.acceptedSamples)
            assertTrue(result.trace.isEmpty())
        }
    }

    @Test fun deniedFocusCannotAllocateOrPlayAndNeverStartsLater() {
        val port = Port().apply { focus = 0 }; val control = QuietOutputControl()
        val result = check(port, control = control).execute()
        assertEquals(QuietStop.FOCUS_DENIED, result.reason)
        assertFalse(port.calls.contains(QuietOperation.OPEN))
        assertFalse(port.calls.contains(QuietOperation.PLAY))
        assertTrue(port.calls.contains(QuietOperation.ABANDON))
        assertEquals(0, result.acceptedSamples)
        assertEquals(QuietStop.FOCUS_DENIED, control.reason)
    }

    @Test fun unsupportedBufferRejectsBeforeFocusOrNativeAllocation() {
        for (minimum in listOf(-2, 0, 262145, Int.MAX_VALUE)) {
            val port = Port().apply { this.minimum = minimum }
            val result = check(port).execute()
            assertEquals(QuietStop.UNSUPPORTED, result.reason)
            assertFalse(port.calls.contains(QuietOperation.FOCUS))
            assertFalse(port.calls.contains(QuietOperation.OPEN))
        }
    }

    @Test fun constructedMismatchOrZeroGainErrorNeverPlaysOrWrites() {
        for (case in 0..3) {
            val port = Port()
            when (case) {
                0 -> port.configured = port.configured.copy(initialized = false)
                1 -> port.configured = port.configured.copy(sampleRate = 44100)
                2 -> port.configured = port.configured.copy(pcm16 = false)
                else -> port.gain = -3
            }
            val result = check(port).execute()
            assertFalse(port.calls.contains(QuietOperation.PLAY))
            assertFalse(port.calls.contains(QuietOperation.WRITE))
            assertTrue(port.calls.contains(QuietOperation.RELEASE))
            assertTrue(result.cleanupSucceeded)
        }
    }

    @Test fun actualQuietProfileMutesBeforePlayAndOnlySubmitsZeros() {
        val port = Port(); val result = check(port).execute()
        assertTrue(port.calls.indexOf(QuietOperation.ZERO_GAIN) < port.calls.indexOf(QuietOperation.PLAY))
        assertEquals(256, result.acceptedSamples); assertEquals(1, result.attempts)
        assertTrue(port.slices.single().second.all { it == 0.toShort() })
        assertEquals(QuietStop.COMPLETE, result.reason)
        assertTrue(result.cleanupSucceeded); assertFalse(result.physicalOutputVerified)
        assertEquals(listOf(QuietOperation.PAUSE, QuietOperation.FLUSH, QuietOperation.UNWATCH,
            QuietOperation.RELEASE, QuietOperation.ABANDON), port.calls.filter {
                it in listOf(QuietOperation.PAUSE, QuietOperation.FLUSH, QuietOperation.UNWATCH,
                    QuietOperation.RELEASE, QuietOperation.ABANDON) })
    }

    @Test fun partialAndZeroKeepTheSameSuffixWithoutReplayingAPrefix() {
        val port = Port().apply { returns.addAll(listOf(2, 0, 254)) }
        val result = check(port).execute()
        assertEquals(listOf(0, 2, 2), port.slices.map { it.first })
        assertEquals(listOf(256, 254, 254), port.slices.map { it.second.size })
        assertTrue(port.slices.all { it.second.all { sample -> sample == 0.toShort() } })
        assertEquals(256, result.acceptedSamples); assertEquals(3, result.attempts)
    }

    @Test fun zeroAttemptsAreFiniteAndNeverBusySpin() {
        val port = Port().apply { returns.addAll(List(8) { 0 }) }; val delays = mutableListOf<Long>()
        val result = check(port, pause = { delays.add(it) }).execute()
        assertEquals(8, result.attempts); assertEquals(0, result.acceptedSamples)
        assertEquals(List(7) { 10L }, delays)
        assertEquals(QuietStop.ATTEMPT_LIMIT, result.reason)
    }

    @Test fun negativeOrOversizedReturnsPreserveEarlierAcceptanceAndCloseNewWrites() {
        for (raw in listOf(-6, -11, 255, Int.MAX_VALUE)) {
            val port = Port().apply { returns.addAll(listOf(2, raw)) }
            val result = check(port).execute()
            assertEquals(2, result.acceptedSamples); assertEquals(2, result.attempts)
            assertEquals(raw, result.trace.last { it.operation == QuietOperation.WRITE && it.stage == QuietStage.RETURNED }.rawValue)
            assertFalse(result.physicalOutputVerified)
        }
    }

    @Test fun stopDuringEnteredWriteStillRecordsItsActualAcceptedPrefix() {
        val control = QuietOutputControl(); val port = Port().apply { returns.add(2) }
        port.hook = { if (it == QuietOperation.WRITE) control.stop(QuietStop.USER) }
        val result = check(port, control = control).execute()
        assertEquals(2, result.acceptedSamples); assertEquals(1, result.attempts)
        assertEquals(QuietStop.USER, result.reason)
        assertTrue(result.cleanupSucceeded)
    }

    @Test fun controlCutDoesNotWaitBehindABlockedWorkerOrReleaseItsLease() {
        val gate = ForegroundAudioExclusion(); val control = QuietOutputControl(); val port = Port()
        val entered = CountDownLatch(1); val leave = CountDownLatch(1)
        port.returns.add(2)
        port.hook = { if (it == QuietOperation.WRITE) { entered.countDown(); kotlin.check(leave.await(5, TimeUnit.SECONDS)) } }
        val run = check(port, gate, control)
        val job = thread { run.execute() }
        try {
            assertTrue(entered.await(5, TimeUnit.SECONDS))
            control.stop(QuietStop.INACTIVE)
            assertEquals(QuietStop.INACTIVE, control.reason)
            assertNull(gate.acquire(ForegroundAudioExclusion.Tool.INPUT, Any()))
            assertFalse(port.calls.contains(QuietOperation.RELEASE))
        } finally { leave.countDown(); job.join(5000) }
        assertFalse(job.isAlive)
        assertEquals(2, run.result!!.acceptedSamples)
        assertNotNull(gate.acquire(ForegroundAudioExclusion.Tool.INPUT, Any()))
    }

    @Test fun deadlineClockRollbackAndOverflowNeverCreateFurtherNativeWork() {
        for (mode in 0..2) {
            val port = Port(); var now = if (mode == 2) Long.MAX_VALUE else 100L
            if (mode < 2) port.hook = { if (it == QuietOperation.ZERO_GAIN) now = if (mode == 0) 2100 else 99 }
            val result = check(port, clock = { now }).execute()
            assertFalse(port.calls.contains(QuietOperation.PLAY))
            assertFalse(port.calls.contains(QuietOperation.WRITE))
            assertTrue(result.reason in listOf(QuietStop.TIME_LIMIT, QuietStop.CLOCK_FAULT))
        }
    }

    @Test fun allocationExceptionQuarantinesTheUnknownOwnerWithoutReplay() {
        val gate = ForegroundAudioExclusion(); val port = Port().apply { fail = QuietOperation.OPEN }
        val result = check(port, gate).execute()
        assertTrue(gate.blocked); assertFalse(result.cleanupSucceeded)
        assertFalse(port.calls.contains(QuietOperation.PLAY))
        assertNull(gate.acquire(ForegroundAudioExclusion.Tool.INPUT, Any()))
    }

    @Test fun pauseFailureSkipsFlushButStillAttemptsReleaseAndFocusAbandon() {
        val gate = ForegroundAudioExclusion(); val port = Port().apply { fail = QuietOperation.PAUSE }
        val result = check(port, gate).execute()
        assertFalse(port.calls.contains(QuietOperation.FLUSH))
        assertTrue(port.calls.contains(QuietOperation.RELEASE))
        assertTrue(port.calls.contains(QuietOperation.ABANDON))
        assertFalse(result.cleanupSucceeded); assertTrue(gate.blocked)
    }

    @Test fun cleanupFailuresCannotReopenEitherAudioTool() {
        for (op in listOf(QuietOperation.FLUSH, QuietOperation.UNWATCH, QuietOperation.RELEASE, QuietOperation.ABANDON)) {
            val gate = ForegroundAudioExclusion(); val port = Port().apply { fail = op }
            val result = check(port, gate).execute()
            assertFalse(result.cleanupSucceeded); assertTrue(gate.blocked)
            assertNull(ForegroundMicrophoneGate(gate).acquire())
            assertTrue(result.trace.any { it.operation == op && it.exception })
        }
    }

    @Test fun unreportedThrowableKeepsTheOwnerRetainedAndDoesNotInventCleanup() {
        val gate = ForegroundAudioExclusion(); val port = Port().apply { fatal = QuietOperation.WRITE }
        val run = check(port, gate)
        assertFailsWith<AssertionError> { run.execute() }
        assertTrue(gate.blocked); assertFalse(run.result!!.cleanupSucceeded)
        assertFalse(port.calls.contains(QuietOperation.RELEASE))
        assertNull(gate.acquire(ForegroundAudioExclusion.Tool.INPUT, Any()))
    }

    @Test fun resultsAndTraceStayBoundedAndCannotClaimPhysicalProtection() {
        val port = Port().apply { returns.addAll(List(8) { 0 }) }
        val result = check(port).execute()
        assertTrue(result.trace.size <= 96)
        assertEquals((1..result.trace.size).toList(), result.trace.map { it.sequence })
        @Suppress("UNCHECKED_CAST")
        assertFailsWith<UnsupportedOperationException> { (result.trace as MutableList<QuietTraceEvent>).clear() }
        val report = QuietOutputReportSnapshot.capture("Audio Bodyguard\nPlatform: Android\nVersion: 0.36-quiet-output-live-input\nBuild: 39", result, 0)
        assertTrue(report.text.contains("Physical output and protection: Not verified"))
        assertTrue(report.text.contains("Control clock: elapsed realtime milliseconds (includes sleep)"))
        assertTrue(report.text.toByteArray(Charsets.UTF_8).size <= 32768)
    }

    @Test fun routesRemainFrameworkSnapshotsAndBoundUntrustedResultLists() {
        val source = MutableList(20) { it }
        val routes = QuietOutputRoutes.from(source, 20, true)
        source.clear()
        assertEquals(16, routes.types.size); assertEquals(20, routes.totalReported)
        assertTrue(routes.multipleQuery)
        @Suppress("UNCHECKED_CAST")
        assertFailsWith<UnsupportedOperationException> { (routes.types as MutableList<Int>).clear() }
    }
}
