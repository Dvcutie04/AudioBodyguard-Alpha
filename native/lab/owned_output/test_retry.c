#include "owner.h"
#include "retirement.h"

#include <errno.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define CHECK(condition) do { \
    if (!(condition)) { \
        fprintf(stderr, "%s:%d: FAILED: %s\n", __func__, __LINE__, #condition); \
        exit(EXIT_FAILURE); \
    } \
} while (0)

typedef struct {
    aqss_lab_owner *owner;
    const int16_t *source;
    const ptrdiff_t *returns;
    size_t return_count;
    size_t calls;
    size_t accepted;
    bool invalidate_inside_call;
    int16_t copied[8];
} scripted_backend;

static ptrdiff_t write_script(void *context, const int16_t *frames,
                               size_t frame_count)
{
    scripted_backend *backend = context;
    CHECK(backend->owner->phase == AQSS_LAB_CALL_ENTERED);
    CHECK(backend->calls < backend->return_count);
    CHECK(frames == backend->source + backend->accepted);
    CHECK(frame_count == 8 - backend->accepted);
    ptrdiff_t result = backend->returns[backend->calls++];
    if (result > 0 && (size_t)result <= frame_count) {
        memcpy(backend->copied + backend->accepted, frames,
               (size_t)result * sizeof(*frames));
        backend->accepted += (size_t)result;
    }
    if (backend->invalidate_inside_call) {
        CHECK(aqss_lab_invalidate_runtime(backend->owner, AQSS_LAB_FAULT_XRUN));
        CHECK(!aqss_lab_acknowledge_hold(backend->owner));
        CHECK(!aqss_lab_submit(backend->owner));
        CHECK(!aqss_lab_record_return(backend->owner));
    }
    return result;
}

static void count_body(void *metadata)
{
    ++*(size_t *)metadata;
}

static void test_eagain_and_zero_preserve_suffix_until_explicit_retry(void)
{
    const int16_t frames[8] = {1, -2, 3, -4, 5, -6, 7, -8};
    const ptrdiff_t returns[] = {3, -EAGAIN, 0, 5};
    const size_t accepted[] = {3, 3, 3, 8};
    aqss_lab_owner owner;
    scripted_backend backend = {
        .owner = &owner, .source = frames, .returns = returns, .return_count = 4
    };
    CHECK(aqss_lab_owner_init(&owner, 71, frames, 8, write_script, &backend));
    for (size_t i = 0; i < 4; ++i) {
        CHECK(aqss_lab_submit(&owner));
        CHECK(backend.calls == i + 1); /* No implicit retry loop. */
        CHECK(!aqss_lab_submit(&owner)); /* Still awaiting accounting. */
        CHECK(aqss_lab_record_return(&owner));
        CHECK(!owner.admission_closed);
        CHECK(!owner.invalid_return);
        CHECK(owner.first_fault == AQSS_LAB_FAULT_NONE);
        CHECK(owner.accepted_frames == accepted[i]);
        CHECK(owner.events[i * 3 + 1].returned_frames == returns[i]);
        CHECK(owner.events[i * 3 + 2].returned_frames == returns[i]);
    }
    CHECK(memcmp(backend.copied, frames, sizeof(frames)) == 0);
    CHECK(owner.outcome_unknown);
    CHECK(!aqss_lab_submit(&owner));
    CHECK(backend.calls == 4);
    CHECK(owner.event_count == 12);
}

static void test_fault_closes_admission_before_return_accounting(void)
{
    const int16_t frames[8] = {11, 12, 13, 14, 15, 16, 17, 18};
    const ptrdiff_t faults[] = {-EPIPE, -EIO, -ENODEV, -EINVAL, PTRDIFF_MIN, 6};
    for (size_t i = 0; i < sizeof(faults) / sizeof(faults[0]); ++i) {
        const ptrdiff_t returns[] = {3, faults[i]};
        aqss_lab_owner owner;
        scripted_backend backend = {
            .owner = &owner, .source = frames, .returns = returns, .return_count = 2
        };
        CHECK(aqss_lab_owner_init(&owner, 72, frames, 8, write_script, &backend));
        size_t body_calls = 0;
        aqss_lab_callbacks callbacks;
        CHECK(aqss_lab_callbacks_init(&callbacks, &owner, &body_calls, count_body));
        aqss_lab_callback_ticket queued = aqss_lab_queue_callback(&callbacks);
        CHECK(queued.sequence != 0);
        CHECK(aqss_lab_submit(&owner));
        CHECK(aqss_lab_record_return(&owner));
        CHECK(aqss_lab_submit(&owner));
        CHECK(owner.admission_closed); /* Fault inhibits before caller cleanup. */
        CHECK(owner.first_fault == AQSS_LAB_FAULT_BACKEND_RESULT);
        CHECK(owner.phase == AQSS_LAB_CALL_RETURNED);
        CHECK(aqss_lab_queue_callback(&callbacks).sequence == 0);
        CHECK(!aqss_lab_deliver_callback(&callbacks, queued));
        CHECK(body_calls == 0);
        CHECK(aqss_lab_take_callback_metadata(&callbacks) == NULL);
        CHECK(!aqss_lab_acknowledge_hold(&owner));
        CHECK(!aqss_lab_submit(&owner));
        CHECK(aqss_lab_record_return(&owner));
        CHECK(owner.invalid_return);
        CHECK(owner.accepted_frames == 3);
        CHECK(owner.outcome_unknown);
        CHECK(aqss_lab_acknowledge_hold(&owner));
        CHECK(aqss_lab_take_callback_metadata(&callbacks) == &body_calls);
        CHECK(!aqss_lab_submit(&owner));
        CHECK(backend.calls == 2);
        CHECK(memcmp(backend.copied, frames, 3 * sizeof(*frames)) == 0);
    }
}

static void test_recovery_cannot_reopen_old_runtime_or_replay_suffix(void)
{
    const int16_t old_frames[8] = {1, 2, 3, 4, 5, 6, 7, 8};
    const ptrdiff_t old_returns[] = {3, -EAGAIN, 5};
    aqss_lab_owner old_owner;
    scripted_backend old_backend = {
        .owner = &old_owner, .source = old_frames,
        .returns = old_returns, .return_count = 3
    };
    CHECK(aqss_lab_owner_init(&old_owner, 73, old_frames, 8,
                              write_script, &old_backend));
    for (size_t i = 0; i < 2; ++i) {
        CHECK(aqss_lab_submit(&old_owner));
        CHECK(aqss_lab_record_return(&old_owner));
    }
    CHECK(aqss_lab_invalidate_runtime(&old_owner, AQSS_LAB_FAULT_ROUTE_CHANGED));
    CHECK(old_owner.first_fault == AQSS_LAB_FAULT_ROUTE_CHANGED);
    CHECK(aqss_lab_acknowledge_hold(&old_owner));
    size_t old_events = old_owner.event_count;
    /* The script could now accept five frames, but a recovered backend cannot
     * make the invalidated owner's old suffix eligible again.
     */
    CHECK(!aqss_lab_submit(&old_owner));

    const int16_t new_frames[8] = {80, 70, 60, 50, 40, 30, 20, 10};
    const ptrdiff_t new_returns[] = {8};
    aqss_lab_owner new_owner;
    scripted_backend new_backend = {
        .owner = &new_owner, .source = new_frames,
        .returns = new_returns, .return_count = 1
    };
    CHECK(aqss_lab_owner_init(&new_owner, 74, new_frames, 8,
                              write_script, &new_backend));
    CHECK(new_backend.calls == 0); /* Recovery itself never dispatched work. */
    CHECK(aqss_lab_submit(&new_owner));
    CHECK(aqss_lab_record_return(&new_owner));
    CHECK(memcmp(new_backend.copied, new_frames, sizeof(new_frames)) == 0);
    CHECK(new_owner.first_fault == AQSS_LAB_FAULT_NONE);
    CHECK(!aqss_lab_submit(&old_owner));
    CHECK(old_backend.calls == 2);
    CHECK(old_owner.accepted_frames == 3);
    CHECK(old_owner.frame_count - old_owner.accepted_frames == 5);
    CHECK(old_owner.event_count == old_events);
    CHECK(old_owner.outcome_unknown);
}

static void test_hold_after_no_progress_rejects_retry(void)
{
    const int16_t frames[8] = {8, 7, 6, 5, 4, 3, 2, 1};
    const ptrdiff_t no_progress[] = {-EAGAIN, 0};
    for (size_t i = 0; i < 2; ++i) {
        const ptrdiff_t returns[] = {3, no_progress[i], 5};
        aqss_lab_owner owner;
        scripted_backend backend = {
            .owner = &owner, .source = frames, .returns = returns, .return_count = 3
        };
        CHECK(aqss_lab_owner_init(&owner, 75, frames, 8, write_script, &backend));
        for (size_t j = 0; j < 2; ++j) {
            CHECK(aqss_lab_submit(&owner));
            CHECK(aqss_lab_record_return(&owner));
        }
        aqss_lab_request_hold(&owner);
        CHECK(aqss_lab_acknowledge_hold(&owner));
        size_t events = owner.event_count;
        CHECK(!aqss_lab_submit(&owner));
        CHECK(backend.calls == 2);
        CHECK(owner.accepted_frames == 3);
        CHECK(owner.event_count == events);
        CHECK(owner.first_fault == AQSS_LAB_FAULT_NONE); /* A hold is not a fault. */
        CHECK(owner.outcome_unknown);
    }
}

static void test_invalidation_before_dispatch_is_fail_closed(void)
{
    const int16_t frames[8] = {0};
    const ptrdiff_t returns[] = {8};
    const aqss_lab_fault reasons[] = {
        AQSS_LAB_FAULT_BACKEND_RESULT, AQSS_LAB_FAULT_XRUN,
        AQSS_LAB_FAULT_SUSPENDED, AQSS_LAB_FAULT_DISCONNECTED,
        AQSS_LAB_FAULT_ROUTE_CHANGED, AQSS_LAB_FAULT_FORMAT_CHANGED,
        AQSS_LAB_FAULT_UNKNOWN, AQSS_LAB_FAULT_NONE, (aqss_lab_fault)999
    };
    aqss_lab_owner uninitialized = {0};
    CHECK(!aqss_lab_invalidate_runtime(NULL, AQSS_LAB_FAULT_XRUN));
    CHECK(!aqss_lab_invalidate_runtime(&uninitialized, AQSS_LAB_FAULT_XRUN));
    for (size_t i = 0; i < sizeof(reasons) / sizeof(reasons[0]); ++i) {
        aqss_lab_owner owner;
        scripted_backend backend = {
            .owner = &owner, .source = frames, .returns = returns, .return_count = 1
        };
        CHECK(aqss_lab_owner_init(&owner, 76, frames, 8, write_script, &backend));
        CHECK(aqss_lab_invalidate_runtime(&owner, reasons[i]));
        CHECK(owner.first_fault == (i < 7 ? reasons[i] : AQSS_LAB_FAULT_UNKNOWN));
        CHECK(owner.admission_closed);
        CHECK(owner.admission_revision == 2);
        CHECK(aqss_lab_acknowledge_hold(&owner));
        aqss_lab_fault retained = owner.first_fault;
        CHECK(aqss_lab_invalidate_runtime(&owner, AQSS_LAB_FAULT_FORMAT_CHANGED));
        CHECK(owner.first_fault == retained);
        CHECK(!aqss_lab_submit(&owner));
        CHECK(backend.calls == 0); /* This is a pre-dispatch rejection. */
        CHECK(owner.accepted_frames == 0);
        CHECK(!owner.outcome_unknown); /* No invocation, not a physical proof. */
        CHECK(owner.event_count == 2);
    }
}

static void check_fault_window(bool during_call)
{
    const int16_t frames[8] = {11, 22, 33, 44, 55, 66, 77, 88};
    const ptrdiff_t returns[] = {3, 5};
    aqss_lab_owner owner;
    scripted_backend backend = {
        .owner = &owner, .source = frames, .returns = returns, .return_count = 2,
        .invalidate_inside_call = during_call
    };
    CHECK(aqss_lab_owner_init(&owner, 77, frames, 8, write_script, &backend));
    CHECK(aqss_lab_submit(&owner));
    if (!during_call) {
        CHECK(aqss_lab_invalidate_runtime(&owner, AQSS_LAB_FAULT_DISCONNECTED));
    }
    CHECK(owner.admission_closed);
    CHECK(owner.accepted_frames == 0);
    CHECK(backend.accepted == 3);
    CHECK(!aqss_lab_acknowledge_hold(&owner));
    CHECK(!aqss_lab_submit(&owner));
    CHECK(aqss_lab_record_return(&owner));
    CHECK(!owner.invalid_return); /* Fault cannot erase a valid accepted return. */
    CHECK(owner.first_fault == (during_call ? AQSS_LAB_FAULT_XRUN :
                                            AQSS_LAB_FAULT_DISCONNECTED));
    CHECK(owner.accepted_frames == 3);
    CHECK(owner.outcome_unknown);
    CHECK(aqss_lab_acknowledge_hold(&owner));
    CHECK(!aqss_lab_submit(&owner));
    CHECK(backend.calls == 1); /* Earlier work occurred and remains uncertain. */
    CHECK(owner.event_count == 5);
    CHECK(owner.events[3].kind == AQSS_LAB_EVENT_RETURN_RECORDED);
    CHECK(owner.events[4].kind == AQSS_LAB_EVENT_HOLD_ACKNOWLEDGED);
}

static void test_inflight_fault_waits_for_return_accounting(void)
{
    check_fault_window(true);
}

static void test_returned_fault_waits_for_return_accounting(void)
{
    check_fault_window(false);
}

static void test_fault_at_full_trace_preserves_history(void)
{
    const int16_t frames[8] = {0};
    const ptrdiff_t returns[AQSS_LAB_MAX_CALLS] = {
        -EAGAIN, 0, -EAGAIN, 0, -EAGAIN, 0, -EAGAIN, 0
    };
    aqss_lab_owner owner;
    scripted_backend backend = {
        .owner = &owner, .source = frames, .returns = returns,
        .return_count = AQSS_LAB_MAX_CALLS
    };
    CHECK(aqss_lab_owner_init(&owner, 78, frames, 8, write_script, &backend));
    for (size_t i = 0; i < AQSS_LAB_MAX_CALLS; ++i) {
        CHECK(aqss_lab_submit(&owner));
        CHECK(aqss_lab_record_return(&owner));
    }
    aqss_lab_event history[3u * AQSS_LAB_MAX_CALLS];
    memcpy(history, owner.events, sizeof(history));
    CHECK(!aqss_lab_submit(&owner));
    CHECK(owner.trace_exhausted);
    CHECK(aqss_lab_acknowledge_hold(&owner));
    CHECK(owner.event_count == AQSS_LAB_MAX_EVENTS);
    CHECK(aqss_lab_invalidate_runtime(&owner, AQSS_LAB_FAULT_SUSPENDED));
    CHECK(owner.first_fault == AQSS_LAB_FAULT_SUSPENDED);
    CHECK(aqss_lab_invalidate_runtime(&owner, AQSS_LAB_FAULT_XRUN));
    CHECK(owner.first_fault == AQSS_LAB_FAULT_SUSPENDED);
    CHECK(owner.event_count == AQSS_LAB_MAX_EVENTS);
    CHECK(memcmp(history, owner.events, sizeof(history)) == 0);
    CHECK(!aqss_lab_submit(&owner));
    CHECK(backend.calls == AQSS_LAB_MAX_CALLS);
    CHECK(owner.accepted_frames == 0);
    CHECK(owner.outcome_unknown);
}

typedef struct {
    aqss_lab_callbacks *callbacks;
    aqss_lab_callback_ticket parent;
    aqss_lab_child_reference child;
    size_t body_calls;
} callback_metadata;

static void retain_child_body(void *raw)
{
    callback_metadata *metadata = raw;
    ++metadata->body_calls;
    metadata->child = aqss_lab_retain_child(metadata->callbacks, metadata->parent);
    CHECK(metadata->child.sequence != 0);
}

static void test_fault_retirement_waits_for_callbacks_and_children(void)
{
    const int16_t frames[8] = {1, 2, 3, 4, 5, 6, 7, 8};
    const ptrdiff_t returns[] = {3, -EAGAIN, 5};
    aqss_lab_owner owner;
    scripted_backend backend = {
        .owner = &owner, .source = frames, .returns = returns, .return_count = 3
    };
    aqss_lab_retirement_pool pool;
    CHECK(aqss_lab_retirement_init(&pool, 1, 2));
    aqss_lab_retirement_handle old = aqss_lab_reserve_runtime(&pool, 1);
    CHECK(old.pool == &pool); /* Reserve before allocation/dispatch. */
    callback_metadata *metadata = calloc(1, sizeof(*metadata));
    CHECK(metadata != NULL);
    aqss_lab_callbacks callbacks;
    CHECK(aqss_lab_owner_init(&owner, 79, frames, 8, write_script, &backend));
    CHECK(aqss_lab_callbacks_init(&callbacks, &owner, metadata, retain_child_body));
    CHECK(aqss_lab_bind_runtime(&pool, old, &callbacks));
    metadata->callbacks = &callbacks;
    metadata->parent = aqss_lab_queue_callback(&callbacks);
    CHECK(aqss_lab_deliver_callback(&callbacks, metadata->parent));
    aqss_lab_child_reference child = metadata->child;
    aqss_lab_callback_ticket queued = aqss_lab_queue_callback(&callbacks);
    CHECK(queued.sequence != 0);
    for (size_t i = 0; i < 2; ++i) {
        CHECK(aqss_lab_submit_current(&pool, old));
        CHECK(aqss_lab_record_return(&owner));
    }
    CHECK(aqss_lab_invalidate_runtime(&owner, AQSS_LAB_FAULT_ROUTE_CHANGED));
    CHECK(!aqss_lab_submit_current(&pool, old));
    CHECK(aqss_lab_reserve_runtime(&pool, 2).pool == NULL);
    CHECK(aqss_lab_retire_runtime(&pool, old));
    CHECK(aqss_lab_acknowledge_hold(&owner));
    CHECK(aqss_lab_take_retired_metadata(&pool, old) == NULL);
    CHECK(!aqss_lab_deliver_callback(&callbacks, queued));
    CHECK(metadata->body_calls == 1);
    CHECK(aqss_lab_take_retired_metadata(&pool, old) == NULL);
    CHECK(aqss_lab_release_child(&callbacks, child));
    CHECK(aqss_lab_take_retired_metadata(&pool, old) == metadata);
    free(metadata);
    CHECK(!aqss_lab_deliver_callback(&callbacks, queued));
    CHECK(!aqss_lab_release_child(&callbacks, child));

    const int16_t new_frames[8] = {42, 42, 42, 42, 42, 42, 42, 42};
    const ptrdiff_t new_returns[] = {8};
    aqss_lab_owner new_owner;
    scripted_backend new_backend = {
        .owner = &new_owner, .source = new_frames,
        .returns = new_returns, .return_count = 1
    };
    aqss_lab_retirement_handle next = aqss_lab_reserve_runtime(&pool, 2);
    CHECK(next.pool == &pool && next.slot == old.slot);
    size_t body_calls = 0;
    aqss_lab_callbacks new_callbacks;
    CHECK(aqss_lab_owner_init(&new_owner, 80, new_frames, 8, write_script, &new_backend));
    CHECK(aqss_lab_callbacks_init(&new_callbacks, &new_owner, &body_calls, count_body));
    CHECK(aqss_lab_bind_runtime(&pool, next, &new_callbacks));
    CHECK(!aqss_lab_submit_current(&pool, old));
    CHECK(aqss_lab_submit_current(&pool, next));
    CHECK(aqss_lab_record_return(&new_owner));
    CHECK(new_owner.accepted_frames == 8);
    CHECK(owner.accepted_frames == 3 && backend.calls == 2);
    CHECK(owner.outcome_unknown);
    CHECK(owner.first_fault == AQSS_LAB_FAULT_ROUTE_CHANGED);
    CHECK(aqss_lab_retire_runtime(&pool, next));
    CHECK(aqss_lab_acknowledge_hold(&new_owner));
    CHECK(aqss_lab_take_retired_metadata(&pool, next) == &body_calls);
}

int main(void)
{
    test_eagain_and_zero_preserve_suffix_until_explicit_retry();
    test_fault_closes_admission_before_return_accounting();
    test_recovery_cannot_reopen_old_runtime_or_replay_suffix();
    test_hold_after_no_progress_rejects_retry();
    test_invalidation_before_dispatch_is_fail_closed();
    test_inflight_fault_waits_for_return_accounting();
    test_returned_fault_waits_for_return_accounting();
    test_fault_at_full_trace_preserves_history();
    test_fault_retirement_waits_for_callbacks_and_children();
    puts("AQSS_NATIVE_RETRY_PASS: 9 deterministic C cases; physical output unqualified");
    return EXIT_SUCCESS;
}
