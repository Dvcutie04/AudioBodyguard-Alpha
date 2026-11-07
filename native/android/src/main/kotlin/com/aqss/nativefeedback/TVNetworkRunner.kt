package com.aqss.nativefeedback

import java.net.Socket
import java.util.concurrent.ScheduledFuture
import java.util.concurrent.ScheduledThreadPoolExecutor
import java.util.concurrent.TimeUnit
import java.util.concurrent.atomic.AtomicReference

/** Narrow native boundary for reachability and untrusted certificate observation. */
interface TVProbeSocket {
    fun connect(target: LocalTVTarget, port: Int, timeoutMillis: Int)
    fun close()
}

enum class TVNetworkOutcome { REACHABLE, NOT_REACHED, STOPPED, CLEANUP_UNRESOLVED }
data class TVNetworkResult(val outcome: TVNetworkOutcome, val port: Int? = null,
                           val certificateSha256: String? = null)

/** One bounded worker; cancellation cannot release an entered call or replay it. */
class TVNetworkRunner {
    private enum class CancellationClose { NOT_REQUESTED, PENDING, RETURNED }
    private class Run(val id: Long, val deadline: Long?, completed: (Long, TVNetworkResult) -> Unit) {
        var completion: ((Long, TVNetworkResult) -> Unit)? = completed
        var cancelled = false
        var cleanupFailed = false
        var socket: TVProbeSocket? = null
        var cancellationClose = CancellationClose.NOT_REQUESTED
        var returnedResult: TVNetworkResult? = null
        var timeout: ScheduledFuture<*>? = null
    }
    private val lock = Any()
    private var active: Run? = null
    private var nextId = 0L
    private val deadlines by lazy {
        ScheduledThreadPoolExecutor(1) { task ->
            Thread(task, "aqss-tv-network-deadline").apply { isDaemon = true }
        }.apply { removeOnCancelPolicy = true }
    }

    fun start(target: LocalTVTarget, factory: () -> TVProbeSocket,
              completed: (Long, TVNetworkResult) -> Unit): Long? =
        start(target, LocalTVTarget.PORTS, null, factory, completed)

    fun readCertificate(target: LocalTVTarget, reachedPort: Int, bindSocket: (Socket) -> Unit,
                        completed: (Long, TVNetworkResult) -> Unit): Long? {
        if (reachedPort !in LocalTVTarget.PORTS) return null
        val fingerprint = AtomicReference<String>()
        return start(target, listOf(reachedPort), LocalTVTarget.TIMEOUT_MILLIS,
            { TVCertificateSocket(bindSocket, fingerprint) }) { id, result ->
            val observed = fingerprint.getAndSet(null)
            completed(id, result.copy(certificateSha256 = observed.takeIf { result.outcome == TVNetworkOutcome.REACHABLE }))
        }
    }

    private fun start(target: LocalTVTarget, ports: List<Int>, timeoutMillis: Int?,
                      factory: () -> TVProbeSocket, completed: (Long, TVNetworkResult) -> Unit): Long? {
        val run = synchronized(lock) {
            if (active != null || nextId == Long.MAX_VALUE) return null
            val deadline = timeoutMillis?.let { System.nanoTime() + TimeUnit.MILLISECONDS.toNanos(it.toLong()) }
            Run(++nextId, deadline, completed).also { active = it }
        }
        val worker = Thread({
            var result = TVNetworkResult(TVNetworkOutcome.NOT_REACHED)
            for (port in ports) {
                if (synchronized(lock) { run.cancelled }) break
                var socket: TVProbeSocket? = null
                try {
                    val current = factory()
                    socket = current
                    val admitted = synchronized(lock) {
                        if (run.cancelled) false else { run.socket = current; true }
                    }
                    if (admitted) {
                        current.connect(target, port, LocalTVTarget.TIMEOUT_MILLIS)
                        result = TVNetworkResult(TVNetworkOutcome.REACHABLE, port)
                    }
                } catch (_: Exception) {
                    // Native errors are deliberately not exported with host information.
                    result = TVNetworkResult(TVNetworkOutcome.NOT_REACHED)
                } finally {
                    try { socket?.close() } catch (_: Exception) {
                        synchronized(lock) { run.cleanupFailed = true }
                    }
                    synchronized(lock) { if (!run.cleanupFailed) run.socket = null }
                }
                if (synchronized(lock) { run.cancelled || run.cleanupFailed } ||
                    result.outcome == TVNetworkOutcome.REACHABLE) break
            }
            synchronized(lock) { run.returnedResult = result }
            finishIfReturned(run)
        }, "aqss-tv-network-check").apply { isDaemon = true }
        try {
            synchronized(lock) {
                if (run.deadline != null) {
                    val remaining = (run.deadline - System.nanoTime()).coerceAtLeast(0)
                    run.timeout = deadlines.schedule({ cancel(run.id) }, remaining, TimeUnit.NANOSECONDS)
                }
                worker.start()
            }
        } catch (_: RuntimeException) {
            synchronized(lock) {
                run.timeout?.cancel(false)
                if (active === run) active = null
            }
            return null
        }
        return run.id
    }

    fun cancel(id: Long) {
        val close = synchronized(lock) {
            val run = active?.takeIf { it.id == id && it.completion != null } ?: return@synchronized null
            run.cancelled = true
            val socket = run.socket ?: return@synchronized null
            if (run.cancellationClose != CancellationClose.NOT_REQUESTED) return@synchronized null
            run.cancellationClose = CancellationClose.PENDING
            run to socket
        } ?: return
        val (run, socket) = close
        try {
            Thread({
                try { socket.close() } catch (_: Exception) {
                    synchronized(lock) { run.cleanupFailed = true }
                } finally {
                    synchronized(lock) { run.cancellationClose = CancellationClose.RETURNED }
                    finishIfReturned(run)
                }
            }, "aqss-tv-network-close").apply { isDaemon = true; start() }
        } catch (_: RuntimeException) {
            // No close entered. The original worker still owns connection and cleanup.
            synchronized(lock) { run.cancellationClose = CancellationClose.RETURNED }
            finishIfReturned(run)
        }
    }

    private fun finishIfReturned(run: Run) {
        val completion = synchronized(lock) {
            if (active !== run || run.cancellationClose == CancellationClose.PENDING) {
                return@synchronized null
            }
            val returned = run.returnedResult ?: return@synchronized null
            val callback = run.completion ?: return@synchronized null
            run.completion = null
            run.timeout?.cancel(false)
            val deadlinePassed = run.deadline?.let { System.nanoTime() - it >= 0 } == true
            val result = when {
                run.cleanupFailed -> TVNetworkResult(TVNetworkOutcome.CLEANUP_UNRESOLVED)
                run.cancelled || deadlinePassed -> TVNetworkResult(TVNetworkOutcome.STOPPED)
                else -> returned
            }
            if (!run.cleanupFailed) active = null
            callback to result
        }
        completion?.let { (callback, result) -> callback(run.id, result) }
    }
}
