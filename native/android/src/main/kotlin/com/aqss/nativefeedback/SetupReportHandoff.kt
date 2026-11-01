package com.aqss.nativefeedback

import java.util.UUID

/** One bounded report kind, never an audio handle or permission to start work. */
sealed class SetupReportAttachment {
    class Inventory(val report: OutputInventoryReportSnapshot) : SetupReportAttachment()
    class Quiet(val report: QuietOutputReportSnapshot) : SetupReportAttachment()
}

/** Main-thread-only, process-local, single-use transfer. A replacement retires
 * the preceding ticket even when the report kind changes. Labels carry no text
 * and are neither authentication nor durable identities. */
class SetupReportHandoff {
    private data class Pending(val ticket: String, val attachment: SetupReportAttachment)
    private var pending: Pending? = null
    fun offer(attachment: SetupReportAttachment): String = UUID.randomUUID().toString().also {
        pending = Pending(it, attachment)
    }
    fun take(ticket: String?): SetupReportAttachment? {
        val current = pending ?: return null
        if (current.ticket != ticket) return null
        pending = null; return current.attachment
    }
    fun discard(ticket: String) { if (pending?.ticket == ticket) pending = null }
}
