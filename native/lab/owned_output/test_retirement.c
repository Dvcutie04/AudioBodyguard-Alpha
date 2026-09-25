#include "retirement.h"
#include "hold.h"

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
    aqss_lab_owner owner;
    aqss_lab_callbacks callbacks;
    aqss_lab_callback_ticket parent;
    aqss_lab_child_reference child;
    size_t calls;
    size_t bodies;
} runtime;

static ptrdiff_t accept_prefix(void *context, const int16_t *frames, size_t count)
{
    runtime *run = context;
    CHECK(frames != NULL && count == 8);
    ++run->calls;
    return 3;
}

static void retain_child(void *context)
{
    runtime *run = *(runtime **)context;
    ++run->bodies;
    run->child = aqss_lab_retain_child(&run->callbacks, run->parent);
    CHECK(run->child.context == &run->callbacks);
}

static void initialize(runtime *run)
{
    static const int16_t frames[8] = {1, 2, 3, 4, 5, 6, 7, 8};
    *run = (runtime){0};
    runtime **metadata = malloc(sizeof(*metadata));
    CHECK(metadata != NULL);
    *metadata = run;
    CHECK(aqss_lab_owner_init(&run->owner, 71, frames, 8, accept_prefix, run));
    CHECK(aqss_lab_callbacks_init(&run->callbacks, &run->owner, metadata, retain_child));
}

static void release_metadata(aqss_lab_retirement_pool *pool,
                              aqss_lab_retirement_handle handle, runtime *run)
{
    void *original = run->callbacks.metadata;
    CHECK(original != NULL);
    void *metadata = aqss_lab_take_retired_metadata(pool, handle);
    CHECK(metadata == original);
    free(metadata);
    CHECK(run->callbacks.metadata == NULL);
}

static void test_retirement_capacity_preserves_outstanding_references(void)
{
    aqss_lab_retirement_pool pool;
    CHECK(aqss_lab_retirement_init(&pool, 1, 2));
    runtime runs[AQSS_LAB_RETIREMENT_SLOTS];
    aqss_lab_retirement_handle handles[AQSS_LAB_RETIREMENT_SLOTS];
    for (size_t i = 0; i < AQSS_LAB_RETIREMENT_SLOTS; ++i) {
        handles[i] = aqss_lab_reserve_runtime(&pool, i + 1);
        CHECK(handles[i].pool == &pool); /* Reserve before allocation/dispatch. */
        initialize(&runs[i]);
        CHECK(aqss_lab_bind_runtime(&pool, handles[i], &runs[i].callbacks));
        CHECK(aqss_lab_submit_current(&pool, handles[i]));
        CHECK(aqss_lab_record_return(&runs[i].owner));
        runs[i].parent = aqss_lab_queue_callback(&runs[i].callbacks);
        CHECK(aqss_lab_deliver_callback(&runs[i].callbacks, runs[i].parent));
        CHECK(aqss_lab_retire_runtime(&pool, handles[i]));
        CHECK(aqss_lab_acknowledge_hold(&runs[i].owner));
        CHECK(aqss_lab_take_retired_metadata(&pool, handles[i]) == NULL);
    }
    aqss_lab_retirement_slot retained[AQSS_LAB_RETIREMENT_SLOTS];
    memcpy(retained, pool.slots, sizeof(retained));
    aqss_lab_retirement_handle denied = aqss_lab_reserve_runtime(&pool, 3);
    CHECK(denied.pool == NULL);
    CHECK(!aqss_lab_submit_current(&pool, denied));
    CHECK(memcmp(retained, pool.slots, sizeof(retained)) == 0);
    for (size_t i = 0; i < AQSS_LAB_RETIREMENT_SLOTS; ++i) {
        CHECK(runs[i].callbacks.children_retained == 1);
        CHECK(runs[i].calls == 1 && runs[i].owner.accepted_frames == 3);
        CHECK(runs[i].owner.outcome_unknown);
        CHECK(aqss_lab_release_child(&runs[i].callbacks, runs[i].child));
        release_metadata(&pool, handles[i], &runs[i]);
    }
}

static void test_reclaimed_slot_reuse_rejects_old_handles_and_acknowledgements(void)
{
    aqss_lab_retirement_pool pool;
    CHECK(aqss_lab_retirement_init(&pool, 1, 2));
    aqss_lab_retirement_handle old = aqss_lab_reserve_runtime(&pool, 10);
    runtime first;
    initialize(&first);
    CHECK(aqss_lab_bind_runtime(&pool, old, &first.callbacks));
    CHECK(aqss_lab_submit_current(&pool, old));
    CHECK(aqss_lab_record_return(&first.owner));
    first.parent = aqss_lab_queue_callback(&first.callbacks);
    CHECK(aqss_lab_retire_runtime(&pool, old));
    aqss_lab_hold_control first_cut = {0};
    CHECK(aqss_lab_begin_hold(&first_cut, &first.owner,
          (aqss_lab_hold_identity){1, 2, 10, 100}, 5, 100, 200));
    aqss_lab_hold_ack old_ack;
    CHECK(aqss_lab_produce_hold_ack(&first_cut, &old_ack));
    CHECK(aqss_lab_take_retired_metadata(&pool, old) == NULL);
    CHECK(!aqss_lab_deliver_callback(&first.callbacks, first.parent));
    release_metadata(&pool, old, &first);
    const size_t first_events = first.owner.event_count;
    aqss_lab_retirement_handle next = aqss_lab_reserve_runtime(&pool, 11);
    CHECK(next.pool == &pool && next.slot == old.slot);
    runtime second;
    initialize(&second);
    CHECK(aqss_lab_bind_runtime(&pool, next, &second.callbacks));
    CHECK(!aqss_lab_submit_current(&pool, old));
    CHECK(!aqss_lab_retire_runtime(&pool, old));
    CHECK(!aqss_lab_cancel_reservation(&pool, old));
    CHECK(aqss_lab_take_retired_metadata(&pool, old) == NULL);
    CHECK(!aqss_lab_deliver_callback(&first.callbacks, first.parent));
    CHECK(!second.owner.admission_closed && second.calls == 0);
    CHECK(aqss_lab_submit_current(&pool, next));
    CHECK(aqss_lab_record_return(&second.owner));
    CHECK(aqss_lab_retire_runtime(&pool, next));
    aqss_lab_hold_control next_cut = {0};
    CHECK(aqss_lab_begin_hold(&next_cut, &second.owner,
          (aqss_lab_hold_identity){1, 2, 11, 101}, 5, 100, 200));
    aqss_lab_hold_ack new_ack;
    CHECK(aqss_lab_produce_hold_ack(&next_cut, &new_ack));
    CHECK(!aqss_lab_match_hold_ack(&next_cut, &old_ack, 5, 101));
    CHECK(aqss_lab_match_hold_ack(&next_cut, &new_ack, 5, 102));
    release_metadata(&pool, next, &second);
    CHECK(first.owner.accepted_frames == 3 && first.owner.outcome_unknown);
    CHECK(first.calls == 1 && first.owner.event_count == first_events);
    CHECK(second.calls == 1 && second.owner.outcome_unknown);
}

static void test_retirement_waits_for_return_accounting(void)
{
    aqss_lab_retirement_pool pool;
    CHECK(aqss_lab_retirement_init(&pool, 1, 2));
    aqss_lab_retirement_handle handle = aqss_lab_reserve_runtime(&pool, 1);
    runtime run;
    initialize(&run);
    CHECK(aqss_lab_bind_runtime(&pool, handle, &run.callbacks));
    CHECK(aqss_lab_submit_current(&pool, handle));
    CHECK(aqss_lab_retire_runtime(&pool, handle));
    CHECK(!aqss_lab_acknowledge_hold(&run.owner));
    CHECK(aqss_lab_take_retired_metadata(&pool, handle) == NULL);
    CHECK(!aqss_lab_submit_current(&pool, handle) && run.calls == 1);
    CHECK(aqss_lab_record_return(&run.owner));
    CHECK(aqss_lab_acknowledge_hold(&run.owner));
    release_metadata(&pool, handle, &run);
    CHECK(run.owner.accepted_frames == 3 && run.owner.outcome_unknown);
}

static void test_reservation_cancellation_does_not_reuse_runtime_ids(void)
{
    aqss_lab_retirement_pool pool;
    CHECK(aqss_lab_retirement_init(&pool, 1, 2));
    CHECK(aqss_lab_reserve_runtime(&pool, 0).pool == NULL);
    aqss_lab_retirement_handle first = aqss_lab_reserve_runtime(&pool, 1);
    CHECK(first.pool == &pool);
    CHECK(!aqss_lab_bind_runtime(&pool, first, NULL));
    CHECK(!aqss_lab_retire_runtime(&pool, first));
    CHECK(!aqss_lab_submit_current(&pool, first));
    CHECK(aqss_lab_reserve_runtime(&pool, 2).pool == NULL);
    CHECK(aqss_lab_cancel_reservation(&pool, first));
    CHECK(!aqss_lab_cancel_reservation(&pool, first));
    CHECK(aqss_lab_reserve_runtime(&pool, 1).pool == NULL);
    aqss_lab_retirement_handle last = aqss_lab_reserve_runtime(&pool, UINT64_MAX);
    CHECK(last.pool == &pool);
    CHECK(aqss_lab_cancel_reservation(&pool, last));
    CHECK(pool.last_runtime_id == UINT64_MAX);
    CHECK(aqss_lab_reserve_runtime(&pool, 1).pool == NULL);
    CHECK(aqss_lab_reserve_runtime(&pool, UINT64_MAX).pool == NULL);
}

static void test_invalid_handles_cannot_retire_or_replace_current_runtime(void)
{
    aqss_lab_retirement_pool pool, foreign;
    CHECK(aqss_lab_retirement_init(&pool, 1, 2));
    CHECK(aqss_lab_retirement_init(&foreign, 1, 3));
    aqss_lab_retirement_handle handle = aqss_lab_reserve_runtime(&pool, 1);
    runtime run;
    initialize(&run);
    CHECK(aqss_lab_bind_runtime(&pool, handle, &run.callbacks));
    CHECK(!aqss_lab_bind_runtime(&pool, handle, &run.callbacks));
    const aqss_lab_retirement_handle bad[] = {
        {&foreign, handle.slot, 1}, {&pool, SIZE_MAX, 1},
        {&pool, handle.slot, 0}, {&pool, handle.slot, 2}
    };
    for (size_t i = 0; i < 4; ++i) {
        CHECK(!aqss_lab_retire_runtime(&pool, bad[i]));
        CHECK(!aqss_lab_submit_current(&pool, bad[i]));
        CHECK(!aqss_lab_cancel_reservation(&pool, bad[i]));
        CHECK(aqss_lab_take_retired_metadata(&pool, bad[i]) == NULL);
    }
    CHECK(aqss_lab_take_retired_metadata(&pool, handle) == NULL);
    CHECK(!aqss_lab_cancel_reservation(&pool, handle));
    CHECK(aqss_lab_reserve_runtime(&pool, 2).pool == NULL);
    CHECK(!run.owner.admission_closed && run.calls == 0);
    CHECK(aqss_lab_retire_runtime(&pool, handle));
    CHECK(aqss_lab_retire_runtime(&pool, handle));
    CHECK(run.owner.event_count == 1);
    CHECK(aqss_lab_acknowledge_hold(&run.owner));
    release_metadata(&pool, handle, &run);
    CHECK(aqss_lab_take_retired_metadata(&pool, handle) == NULL);
}

int main(void)
{
    test_retirement_capacity_preserves_outstanding_references();
    test_reclaimed_slot_reuse_rejects_old_handles_and_acknowledgements();
    test_retirement_waits_for_return_accounting();
    test_reservation_cancellation_does_not_reuse_runtime_ids();
    test_invalid_handles_cannot_retire_or_replace_current_runtime();
    puts("AQSS_RETIREMENT_LAB_PASS: 5 deterministic C cases; metadata only");
    return EXIT_SUCCESS;
}
