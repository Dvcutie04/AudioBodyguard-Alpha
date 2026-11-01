package com.aqss.lab.pcm16

import java.util.Collections

class LabCallbackTicket internal constructor(val run: LabRunToken, val sequence: Int)
class LabChildTicket internal constructor(val run: LabRunToken, val sequence: Int, val parent: LabCallbackTicket)
enum class LabCallbackDelivery { DELIVERED, CLEANUP_ONLY, REJECTED }
enum class LabCallbackEvent { ATTACHED, QUEUED, ENTERED, RETURNED, CLEANUP_CONSUMED,
    CHILD_RETAINED, CHILD_RELEASED, METADATA_TAKEN }
data class LabCallbackTrace(val sequence: Int, val kind: LabCallbackEvent,
                            val callbackSequence: Int?, val childSequence: Int?,
                            val queued: Int, val active: Int, val retainedChildren: Int,
                            val exception: Boolean)
data class LabCallbackSnapshot(val callbacksIssued: Int, val childrenIssued: Int,
                               val queued: Int, val active: Int, val retainedChildren: Int,
                               val metadataRetained: Boolean, val trace: List<LabCallbackTrace>)

/**
 * One stable, serial fixture context. Producers register before queueing; child
 * users release only after their last metadata access. This is not an executor,
 * native producer registry, synchronized ownership boundary or quiescence proof.
 */
class LabCallbackFamily<M : Any> internal constructor(
    private val run: LabRunToken,
    metadata: M,
    private val ownerOpen: () -> Boolean,
    private val ownerReleased: () -> Boolean,
    private val fault: (LabStopReason) -> Unit,
) {
    companion object {
        const val MAX_CALLBACKS = 8
        const val MAX_CHILDREN = 8
        const val MAX_EVENTS = 42
    }
    private enum class State { QUEUED, ACTIVE, CONSUMED }
    private class CallbackSlot(val ticket: LabCallbackTicket, var state: State = State.QUEUED)
    private class ChildSlot(val ticket: LabChildTicket, var retained: Boolean = true)
    private var metadata: M? = metadata
    private val callbacks = ArrayList<CallbackSlot>(MAX_CALLBACKS)
    private val children = ArrayList<ChildSlot>(MAX_CHILDREN)
    private val events = ArrayList<LabCallbackTrace>(MAX_EVENTS)
    private var queued = 0
    private var active = 0
    private var retained = 0
    val referencesDrained: Boolean get() = queued == 0 && active == 0 && retained == 0

    init { append(LabCallbackEvent.ATTACHED) }

    fun queue(): LabCallbackTicket? {
        if (!ownerOpen() || metadata == null) return null
        if (callbacks.size == MAX_CALLBACKS) {
            fault(LabStopReason.REFERENCE_LIMIT)
            return null
        }
        val ticket = LabCallbackTicket(run, callbacks.size + 1)
        callbacks.add(CallbackSlot(ticket)); queued++
        append(LabCallbackEvent.QUEUED, ticket)
        return ticket
    }

    fun deliver(ticket: LabCallbackTicket, body: (M) -> Unit): LabCallbackDelivery {
        val slot = callbackSlot(ticket)?.takeIf { it.state == State.QUEUED }
            ?: return LabCallbackDelivery.REJECTED
        queued--
        if (!ownerOpen()) {
            slot.state = State.CONSUMED
            append(LabCallbackEvent.CLEANUP_CONSUMED, ticket)
            return LabCallbackDelivery.CLEANUP_ONLY
        }
        val value = checkNotNull(metadata)
        slot.state = State.ACTIVE; active++
        append(LabCallbackEvent.ENTERED, ticket)
        var completed = false
        try {
            body(value)
            completed = true
            return LabCallbackDelivery.DELIVERED
        } finally {
            // Preserve the active reference while the owner records the fault.
            // Re-throwing a body failure does not invent a successful return.
            try { if (!completed) fault(LabStopReason.CALLBACK_ERROR) }
            finally {
                active--; slot.state = State.CONSUMED
                append(LabCallbackEvent.RETURNED, ticket, exception = !completed)
            }
        }
    }

    fun retainChild(parent: LabCallbackTicket): LabChildTicket? {
        if (!ownerOpen() || metadata == null || callbackSlot(parent)?.state != State.ACTIVE) return null
        if (children.size == MAX_CHILDREN) {
            fault(LabStopReason.REFERENCE_LIMIT)
            return null
        }
        val child = LabChildTicket(run, children.size + 1, parent)
        children.add(ChildSlot(child)); retained++
        append(LabCallbackEvent.CHILD_RETAINED, parent, child)
        return child
    }

    /** Borrowed data: the driver must finish every last use before releaseChild. */
    fun metadataFor(child: LabChildTicket): M? =
        if (childSlot(child)?.retained == true) metadata else null

    /** Bookkeeping only. No backend call, task queueing or owner reactivation. */
    fun releaseChild(child: LabChildTicket): Boolean {
        val slot = childSlot(child)?.takeIf { it.retained } ?: return false
        slot.retained = false; retained--
        append(LabCallbackEvent.CHILD_RELEASED, child.parent, child)
        return true
    }

    fun takeMetadata(): M? {
        if (!referencesDrained || !ownerReleased()) return null
        val value = metadata ?: return null
        metadata = null
        append(LabCallbackEvent.METADATA_TAKEN)
        return value
    }

    fun snapshot() = LabCallbackSnapshot(callbacks.size, children.size, queued, active,
        retained, metadata != null, Collections.unmodifiableList(ArrayList(events)))

    private fun callbackSlot(ticket: LabCallbackTicket): CallbackSlot? {
        if (ticket.run !== run || ticket.sequence <= 0 || ticket.sequence > callbacks.size) return null
        return callbacks[ticket.sequence - 1].takeIf { it.ticket === ticket }
    }

    private fun childSlot(ticket: LabChildTicket): ChildSlot? {
        if (ticket.run !== run || ticket.sequence <= 0 || ticket.sequence > children.size) return null
        return children[ticket.sequence - 1].takeIf { it.ticket === ticket }
    }

    private fun append(kind: LabCallbackEvent, parent: LabCallbackTicket? = null,
                       child: LabChildTicket? = null, exception: Boolean = false) {
        check(events.size < MAX_EVENTS)
        events.add(LabCallbackTrace(events.size + 1, kind, parent?.sequence, child?.sequence,
            queued, active, retained, exception))
    }
}
