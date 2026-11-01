package com.aqss.nativefeedback

import java.util.UUID

/** Main-thread-only transfer of at most one already bounded, typed snapshot.
 * Tickets are process-local, single-use and never carry report text. They are
 * not authentication, durable identities or permission to open an output. */
class SetupOutputReportHandoff {
    private data class Pending(val ticket: String, val report: OutputInventoryReportSnapshot)
    private var pending: Pending? = null

    fun offer(report: OutputInventoryReportSnapshot): String {
        // Fresh opaque labels avoid matching a restored ticket with a new
        // process's first pending snapshot. They are not authorization tokens.
        val ticket = UUID.randomUUID().toString()
        pending = Pending(ticket, report)
        return ticket
    }

    fun take(ticket: String?): OutputInventoryReportSnapshot? {
        val current = pending ?: return null
        if (current.ticket != ticket) return null
        pending = null
        return current.report
    }

    fun discard(ticket: String) {
        if (pending?.ticket == ticket) pending = null
    }
}
