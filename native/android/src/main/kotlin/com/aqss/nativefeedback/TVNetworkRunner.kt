package com.aqss.nativefeedback

/** Narrow native boundary: no payload, discovery, DNS, authentication or control. */
interface TVProbeSocket {
    fun connect(target: LocalTVTarget, port: Int, timeoutMillis: Int)
    fun close()
}

enum class TVNetworkOutcome { REACHABLE, NOT_REACHED, STOPPED, CLEANUP_UNRESOLVED }
data class TVNetworkResult(val outcome: TVNetworkOutcome, val port: Int? = null)

/** One bounded worker; cancellation cannot release an entered call or replay it. */
class TVNetworkRunner {
    private enum class CancellationClose { NOT_REQUESTED, PENDING, RETURNED }
    private class Run(val id: Long, val completed: (Long, TVNetworkResult) -> Unit) {
        var cancelled = false
        var cleanupFailed = false
        var socket: TVProbeSocket? = null
        var cancellationClose = CancellationClose.NOT_REQUESTED
        var returnedResult: TVNetworkResult? = null
        var published = false
    }
    private val lock = Any()
    private var active: Run? = null
    private var nextId = 0L

    fun start(target: LocalTVTarget, factory: () -> TVProbeSocket,
              completed: (Long, TVNetworkResult) -> Unit): Long? {
        val run = synchronized(lock) {
            if (active != null || nextId == Long.MAX_VALUE) return null
            Run(++nextId, completed).also { active = it }
        }
        val worker = Thread({
            var result = TVNetworkResult(TVNetworkOutcome.NOT_REACHED)
            for (port in LocalTVTarget.PORTS) {
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
        try { worker.start() } catch (_: RuntimeException) {
            synchronized(lock) { if (active === run) active = null }
            return null
        }
        return run.id
    }

    fun cancel(id: Long) {
        val close = synchronized(lock) {
            val run = active?.takeIf { it.id == id && !it.published } ?: return@synchronized null
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
        val result = synchronized(lock) {
            if (active !== run || run.published || run.cancellationClose == CancellationClose.PENDING) {
                return@synchronized null
            }
            val returned = run.returnedResult ?: return@synchronized null
            run.published = true
            when {
                run.cleanupFailed -> TVNetworkResult(TVNetworkOutcome.CLEANUP_UNRESOLVED)
                run.cancelled -> TVNetworkResult(TVNetworkOutcome.STOPPED)
                else -> returned
            }.also { if (!run.cleanupFailed) active = null }
        }
        if (result != null) run.completed(run.id, result)
    }
}
