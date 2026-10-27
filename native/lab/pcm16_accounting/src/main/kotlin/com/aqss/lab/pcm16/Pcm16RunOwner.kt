package com.aqss.lab.pcm16

import java.util.Collections

data class LabTick(val domain: Long, val value: Long)
enum class LabFocus { UNKNOWN, IMMEDIATE, DELAYED, DENIED }
enum class LabInput { UNKNOWN, IDLE, ACTIVE, CLOSING }
data class LabAdmission(val foreground: Boolean = false, val focus: LabFocus = LabFocus.UNKNOWN,
                        val input: LabInput = LabInput.UNKNOWN, val routeRevision: Long = 0)

/** All values are explicit fixture inputs, not phone configuration or authority. */
data class Pcm16RunPlan(
    val workId: Long,
    val channelCount: Int,
    val startAt: LabTick,
    val deadlineExclusive: Long,
    val retryDelay: Long,
    val maxAttempts: Int,
    val routeRevision: Long,
    val traceCapacity: Int,
) {
    init {
        require(workId > 0 && channelCount > 0 && routeRevision > 0)
        require(startAt.domain > 0 && startAt.value >= 0 && deadlineExclusive > startAt.value)
        require(retryDelay > 0 && maxAttempts in 1..Pcm16WriteAccounting.MAX_CALLS)
        require(traceCapacity in 1..64)
    }
    val requiredTraceEvents: Int get() = 3 * (maxAttempts + 5) + 3
}

enum class LabOperation { ACQUIRE, ACTIVATE, WRITE, QUIESCE, DISCARD, RELEASE }
enum class LabRunState { RESERVED, ACTIVE, CLOSING, RELEASED, QUARANTINED }
enum class LabStopReason { USER_STOP, FOCUS_LOSS, FOREGROUND_LOSS, ROUTE_CHANGE, INPUT_BUSY,
    CLOCK_FAULT, DEADLINE, ATTEMPT_LIMIT, ACQUIRE_ERROR, ACTIVATE_ERROR, WRITE_ERROR,
    INVALID_RETURN, CLEANUP_ERROR, REFERENCE_LIMIT, CALLBACK_ERROR }
enum class LabEvent { FOCUS_LOSS, FOCUS_DUCK, FOREGROUND_LOSS, ROUTE_CHANGE, INPUT_BUSY,
    FOCUS_GAIN, FOREGROUND_RETURN, ROUTE_RETURN }
enum class LabTraceKind { START_RESERVED, CALL_ENTERED, CALL_RETURNED, RETURN_RECORDED,
    ADMISSION_CLOSED, SLOT_RELEASED, QUARANTINED }

/** Scripted operations only. No OS binding or platform cleanup guarantee is supplied. */
interface LabOutputBackend {
    fun acquire()
    fun activate()
    fun write(request: Pcm16WriteRequest): Int
    fun quiesce()
    fun discard()
    fun release()
}

class LabRunToken internal constructor(val ordinal: Int, val workId: Long)
class LabTask internal constructor(val run: LabRunToken, val sequence: Int,
                                  val operation: LabOperation, val readyAt: Long)

data class LabRunTrace(val sequence: Int, val kind: LabTraceKind,
                       val operation: LabOperation?, val taskSequence: Int?,
                       val rawValue: Int?, val exception: Boolean,
                       val accountedSamples: Int, val stopReason: LabStopReason?,
                       val controlObservation: LabTick?)

data class LabRunSnapshot(val plan: Pcm16RunPlan, val state: LabRunState,
                          val admissionOpen: Boolean, val stopReason: LabStopReason?,
                          val inFlight: Boolean, val awaitingAccounting: Boolean,
                          val accountedSamples: Int, val remainingSamples: Int,
                          val attempts: Int, val outcomeUnknown: Boolean,
                          val trace: List<LabRunTrace>, val accountingTrace: List<Pcm16TraceEvent>,
                          val waitingForReferences: Boolean = false,
                          val callbacks: LabCallbackSnapshot? = null)

/**
 * A serial, externally driven run/worker lab. execute() invokes a scripted
 * backend once; record() separately accounts that actual observation. Tokens
 * use exact object identity. This is not a concurrent native output owner.
 */
class Pcm16RunOwner {
    private data class Observation(val rawValue: Int? = null, val exception: Boolean = false)
    private class Flight(val task: LabTask, val write: Pcm16WriteRequest?, var result: Observation? = null)
    private class Run(val token: LabRunToken, val plan: Pcm16RunPlan,
                      val ledger: Pcm16WriteAccounting, val backend: LabOutputBackend) {
        var state = LabRunState.RESERVED
        var admissionOpen = true
        var reason: LabStopReason? = null
        var lastTick = plan.startAt.value
        var taskSequence = 0
        var pending: LabTask? = null
        var flight: Flight? = null
        var acquireEntered = false
        var acquired = false
        var activationEntered = false
        var cleanupStarted = false
        var waitingForReferences = false
        var callbacks: LabCallbackFamily<*>? = null
        val trace = ArrayList<LabRunTrace>(plan.traceCapacity)
    }

    private val history = ArrayList<Run>(2)
    private var active: Run? = null
    val pendingTask: LabTask? get() = active?.pending
    val slotOccupied: Boolean get() = active != null
    val historySize: Int get() = history.size

    fun requestStart(plan: Pcm16RunPlan, context: LabAdmission, samples: ShortArray,
                     backend: LabOutputBackend): LabRunToken? {
        if (active != null || history.size == 2) return null
        if (!context.foreground || context.focus != LabFocus.IMMEDIATE || context.input != LabInput.IDLE ||
            context.routeRevision != plan.routeRevision) return null
        if (plan.traceCapacity < plan.requiredTraceEvents) return null
        if (history.lastOrNull()?.plan?.workId?.let { plan.workId <= it } == true) return null
        val ledger = try { Pcm16WriteAccounting.create(plan.workId, plan.channelCount, samples) }
            catch (_: IllegalArgumentException) { return null }
        val run = Run(LabRunToken(history.size + 1, plan.workId), plan, ledger, backend)
        history.add(run)
        active = run
        append(run, LabTraceKind.START_RESERVED, control = plan.startAt)
        queue(run, LabOperation.ACQUIRE, plan.startAt.value)
        return run.token
    }

    fun <M : Any> attachCallbacks(token: LabRunToken, metadata: M): LabCallbackFamily<M>? {
        val run = active?.takeIf { it.token === token && it.admissionOpen && it.callbacks == null }
            ?: return null
        val family = LabCallbackFamily(token, metadata,
            ownerOpen = { active === run && run.admissionOpen },
            ownerReleased = { run.state == LabRunState.RELEASED },
            fault = { close(run, it) })
        run.callbacks = family
        return family
    }

    /** Explicit worker check after reference bookkeeping, never called by releaseChild. */
    fun resumeCleanup(token: LabRunToken): Boolean {
        val run = active?.takeIf { it.token === token } ?: return false
        return resumeFinalRelease(run)
    }

    /** true means one backend call occurred, not that output succeeded. */
    fun execute(task: LabTask, now: LabTick): Boolean {
        val run = active ?: return false
        if (run.token !== task.run || run.pending !== task || run.flight != null) return false
        if (task.operation == LabOperation.RELEASE && run.callbacks?.referencesDrained == false) return false
        val cleanup = isCleanup(task.operation)
        if (!cleanup) {
            if (!run.admissionOpen || !observeClock(run, now)) return false
            if (now.value < task.readyAt) return false
        }
        run.pending = null
        val write = if (task.operation == LabOperation.WRITE) run.ledger.beginWrite() else null
        if (task.operation == LabOperation.WRITE && write == null) {
            close(run, LabStopReason.INVALID_RETURN)
            return false
        }
        val flight = Flight(task, write)
        run.flight = flight
        if (task.operation == LabOperation.ACQUIRE) run.acquireEntered = true
        if (task.operation == LabOperation.ACTIVATE) run.activationEntered = true
        append(run, LabTraceKind.CALL_ENTERED, task, control = now)
        // An unhandled Throwable leaves the entered flight outstanding. It
        // cannot be converted into an observed return or a released slot.
        val result = try {
            val raw = when (task.operation) {
                LabOperation.ACQUIRE -> { run.backend.acquire(); null }
                LabOperation.ACTIVATE -> { run.backend.activate(); null }
                LabOperation.WRITE -> run.backend.write(checkNotNull(write))
                LabOperation.QUIESCE -> { run.backend.quiesce(); null }
                LabOperation.DISCARD -> { run.backend.discard(); null }
                LabOperation.RELEASE -> { run.backend.release(); null }
            }
            Observation(raw)
        } catch (_: Exception) { Observation(exception = true) }

        if (write != null) {
            check(if (result.exception) run.ledger.failed(write)
                else run.ledger.returned(write, checkNotNull(result.rawValue)))
        }
        flight.result = result
        // No return timestamp is invented from the dispatch observation.
        append(run, LabTraceKind.CALL_RETURNED, task, result)
        when {
            result.exception -> close(run, when (task.operation) {
                LabOperation.ACQUIRE -> LabStopReason.ACQUIRE_ERROR
                LabOperation.ACTIVATE -> LabStopReason.ACTIVATE_ERROR
                LabOperation.WRITE -> LabStopReason.WRITE_ERROR
                else -> LabStopReason.CLEANUP_ERROR
            })
            write != null && checkNotNull(result.rawValue) < 0 -> close(run, LabStopReason.WRITE_ERROR)
            write != null && (checkNotNull(result.rawValue) > write.span.sampleCount ||
                checkNotNull(result.rawValue) % run.plan.channelCount != 0) -> close(run, LabStopReason.INVALID_RETURN)
        }
        return true
    }

    fun record(task: LabTask, now: LabTick): Boolean {
        val run = active ?: return false
        val flight = run.flight ?: return false
        if (run.token !== task.run || flight.task !== task) return false
        val result = flight.result ?: return false
        // Clock failure closes fresh admission but must not erase an actual
        // returned prefix or prevent existing cleanup accounting.
        if (!isCleanup(task.operation) && run.admissionOpen) observeClock(run, now)
        if (flight.write != null) check(run.ledger.recordReturn(flight.write))
        append(run, LabTraceKind.RETURN_RECORDED, task, result, now)
        run.flight = null

        if (result.exception && (task.operation == LabOperation.ACQUIRE || isCleanup(task.operation))) {
            quarantine(run)
            return true
        }
        when (task.operation) {
            LabOperation.ACQUIRE -> {
                run.acquired = true
                if (run.admissionOpen) {
                    run.state = LabRunState.ACTIVE
                    queue(run, LabOperation.ACTIVATE, run.lastTick)
                } else continueCleanup(run)
            }
            LabOperation.ACTIVATE -> {
                if (run.admissionOpen) queue(run, LabOperation.WRITE, run.lastTick)
                else continueCleanup(run)
            }
            LabOperation.WRITE -> {
                when {
                    !run.admissionOpen -> continueCleanup(run)
                    run.ledger.remainingSamples == 0 -> Unit // Local acceptance is not presentation or release.
                    run.ledger.callsStarted >= run.plan.maxAttempts -> close(run, LabStopReason.ATTEMPT_LIMIT)
                    else -> {
                        val remainingTicks = run.plan.deadlineExclusive - run.lastTick
                        val ready = if (run.plan.retryDelay >= remainingTicks) run.plan.deadlineExclusive
                            else run.lastTick + run.plan.retryDelay
                        queue(run, LabOperation.WRITE, ready)
                    }
                }
            }
            LabOperation.QUIESCE -> queue(run, LabOperation.DISCARD, run.lastTick)
            LabOperation.DISCARD -> waitForFinalRelease(run)
            LabOperation.RELEASE -> releaseSlot(run)
        }
        return true
    }

    fun stop(token: LabRunToken): Boolean {
        val run = active?.takeIf { it.token === token } ?: return false
        close(run, LabStopReason.USER_STOP)
        return true
    }

    fun notify(token: LabRunToken, event: LabEvent): Boolean {
        val run = active?.takeIf { it.token === token } ?: return false
        val reason = when (event) {
            LabEvent.FOCUS_LOSS, LabEvent.FOCUS_DUCK -> LabStopReason.FOCUS_LOSS
            LabEvent.FOREGROUND_LOSS -> LabStopReason.FOREGROUND_LOSS
            LabEvent.ROUTE_CHANGE -> LabStopReason.ROUTE_CHANGE
            LabEvent.INPUT_BUSY -> LabStopReason.INPUT_BUSY
            else -> return false
        }
        close(run, reason)
        return true
    }

    /** An externally delivered observation, not a timer or a physical deadline guarantee. */
    fun poll(token: LabRunToken, now: LabTick): Boolean {
        val run = active?.takeIf { it.token === token } ?: return false
        if (run.admissionOpen) observeClock(run, now)
        return true
    }

    fun snapshot(token: LabRunToken): LabRunSnapshot? {
        val run = history.firstOrNull { it.token === token } ?: return null
        return LabRunSnapshot(run.plan, run.state, run.admissionOpen, run.reason,
            run.flight != null, run.flight?.result != null, run.ledger.accountedSamples,
            run.ledger.remainingSamples, run.ledger.callsStarted, run.ledger.outcomeUnknown,
            Collections.unmodifiableList(ArrayList(run.trace)), run.ledger.trace,
            run.waitingForReferences, run.callbacks?.snapshot())
    }

    private fun observeClock(run: Run, now: LabTick): Boolean {
        if (now.domain != run.plan.startAt.domain || now.value < 0 || now.value < run.lastTick) {
            close(run, LabStopReason.CLOCK_FAULT)
            return false
        }
        run.lastTick = now.value
        if (now.value >= run.plan.deadlineExclusive) {
            close(run, LabStopReason.DEADLINE)
            return false
        }
        return true
    }

    private fun close(run: Run, reason: LabStopReason) {
        if (!run.admissionOpen) return
        run.admissionOpen = false
        run.reason = reason
        run.state = LabRunState.CLOSING
        run.pending = null
        run.ledger.hold()
        append(run, LabTraceKind.ADMISSION_CLOSED)
        if (run.flight == null) continueCleanup(run)
    }

    private fun continueCleanup(run: Run) {
        if (run.cleanupStarted || run.flight != null) return
        check(run.ledger.acknowledgeHold())
        run.cleanupStarted = true
        if (!run.acquireEntered) { waitForFinalRelease(run); return }
        if (!run.acquired) { quarantine(run); return }
        if (run.activationEntered) queue(run, LabOperation.QUIESCE, run.lastTick)
        else waitForFinalRelease(run)
    }

    private fun waitForFinalRelease(run: Run) {
        check(run.pending == null && run.flight == null)
        run.waitingForReferences = true
        resumeFinalRelease(run)
    }

    private fun resumeFinalRelease(run: Run): Boolean {
        if (!run.waitingForReferences || run.state != LabRunState.CLOSING ||
            run.admissionOpen || run.flight != null || run.pending != null ||
            run.callbacks?.referencesDrained == false) return false
        run.waitingForReferences = false
        if (!run.acquireEntered) releaseSlot(run)
        else queue(run, LabOperation.RELEASE, run.lastTick)
        return true
    }

    private fun releaseSlot(run: Run) {
        check(run.flight == null && !run.admissionOpen && run.callbacks?.referencesDrained != false)
        run.pending = null
        run.state = LabRunState.RELEASED
        append(run, LabTraceKind.SLOT_RELEASED)
        active = null
    }

    private fun quarantine(run: Run) {
        run.pending = null
        run.waitingForReferences = false
        run.state = LabRunState.QUARANTINED
        append(run, LabTraceKind.QUARANTINED)
        // Keep the current slot occupied. There is no timeout/reset/recovery API.
    }

    private fun queue(run: Run, operation: LabOperation, readyAt: Long) {
        check(run.pending == null && run.flight == null)
        run.taskSequence++
        run.pending = LabTask(run.token, run.taskSequence, operation, readyAt)
    }

    private fun isCleanup(operation: LabOperation) = when (operation) {
        LabOperation.QUIESCE, LabOperation.DISCARD, LabOperation.RELEASE -> true
        else -> false
    }

    private fun append(run: Run, kind: LabTraceKind, task: LabTask? = null,
                       result: Observation? = null, control: LabTick? = null) {
        check(run.trace.size < run.plan.traceCapacity)
        run.trace.add(LabRunTrace(run.trace.size + 1, kind, task?.operation, task?.sequence,
            result?.rawValue, result?.exception ?: false, run.ledger.accountedSamples, run.reason, control))
    }
}
