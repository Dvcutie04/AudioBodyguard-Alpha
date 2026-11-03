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
    private class Run(val id: Long) {
        var cancelled = false
        var cleanupFailed = false
        var socket: TVProbeSocket? = null
    }
    private val lock = Any()
    private var active: Run? = null
    private var nextId = 0L

    fun start(target: LocalTVTarget, factory: () -> TVProbeSocket,
              completed: (Long, TVNetworkResult) -> Unit): Long? {
        val run = synchronized(lock) {
            if (active != null || nextId == Long.MAX_VALUE) return null
            Run(++nextId).also { active = it }
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
            val finalResult = synchronized(lock) {
                when {
                    run.cleanupFailed -> TVNetworkResult(TVNetworkOutcome.CLEANUP_UNRESOLVED)
                    run.cancelled -> TVNetworkResult(TVNetworkOutcome.STOPPED)
                    else -> result
                }.also { if (!run.cleanupFailed && active === run) active = null }
            }
            completed(run.id, finalResult)
        }, "aqss-tv-network-check").apply { isDaemon = true }
        try { worker.start() } catch (_: RuntimeException) {
            synchronized(lock) { if (active === run) active = null }
            return null
        }
        return run.id
    }

    fun cancel(id: Long) {
        val run = synchronized(lock) {
            active?.takeIf { it.id == id }?.also { it.cancelled = true }
        } ?: return
        val socket = synchronized(lock) { run.socket }
        try { socket?.close() } catch (_: Exception) {
            synchronized(lock) { run.cleanupFailed = true }
        }
        // Only the worker's actual return and cleanup may release the occupied slot.
    }
}
