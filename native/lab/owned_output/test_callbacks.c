#include "callbacks.h"

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
    size_t body_calls;
    size_t backend_calls;
    uint64_t observed_work_id;
} observations;

typedef struct {
    uint64_t work_id;
    observations *observed;
    aqss_lab_callbacks *callbacks;
    aqss_lab_callback_ticket self;
    bool hold_inside;
} callback_metadata;

static ptrdiff_t accept_prefix(void *context, const int16_t *frames, size_t count)
{
    observations *observed = context;
    CHECK(frames != NULL && count == 8);
    ++observed->backend_calls;
    return 3;
}

static void inspect_metadata(void *context)
{
    callback_metadata *metadata = context;
    if (metadata->hold_inside) {
        aqss_lab_callbacks *callbacks = metadata->callbacks;
        aqss_lab_request_hold(callbacks->owner);
        CHECK(aqss_lab_acknowledge_hold(callbacks->owner));
        CHECK(callbacks->active == 1);
        CHECK(aqss_lab_take_callback_metadata(callbacks) == NULL);
        CHECK(!aqss_lab_deliver_callback(callbacks, metadata->self));
        CHECK(aqss_lab_queue_callback(callbacks).context == NULL);
    }
    /* Access after the attempted nested take catches a premature release. */
    ++metadata->observed->body_calls;
    metadata->observed->observed_work_id = metadata->work_id;
}

static void test_queued_callback_retains_metadata_with_zero_active(void)
{
    const int16_t frames[8] = {1, 2, 3, 4, 5, 6, 7, 8};
    observations observed = {0};
    aqss_lab_owner owner;
    aqss_lab_callbacks callbacks;
    callback_metadata *metadata = malloc(sizeof(*metadata));
    CHECK(metadata != NULL);
    *metadata = (callback_metadata){.work_id = 41, .observed = &observed};
    CHECK(aqss_lab_owner_init(&owner, 41, frames, 8, accept_prefix, &observed));
    CHECK(aqss_lab_callbacks_init(&callbacks, &owner, metadata, inspect_metadata));
    CHECK(aqss_lab_submit(&owner));
    CHECK(aqss_lab_record_return(&owner));
    aqss_lab_callback_ticket ticket = aqss_lab_queue_callback(&callbacks);
    CHECK(ticket.context == &callbacks && ticket.sequence != 0);
    CHECK(callbacks.queued == 1 && callbacks.active == 0);
    aqss_lab_request_hold(&owner);
    CHECK(aqss_lab_acknowledge_hold(&owner));
    CHECK(aqss_lab_take_callback_metadata(&callbacks) == NULL);
    CHECK(callbacks.metadata == metadata);
    CHECK(!aqss_lab_deliver_callback(&callbacks, ticket));
    CHECK(observed.body_calls == 0);
    CHECK(callbacks.queued == 0 && callbacks.active == 0);
    void *released = aqss_lab_take_callback_metadata(&callbacks);
    CHECK(released == metadata);
    free(released);
    /* The context/ticket remain live; the metadata allocation is now freed. */
    CHECK(callbacks.metadata == NULL);
    CHECK(!aqss_lab_deliver_callback(&callbacks, ticket));
    CHECK(aqss_lab_take_callback_metadata(&callbacks) == NULL);
    CHECK(aqss_lab_queue_callback(&callbacks).context == NULL);
    CHECK(observed.body_calls == 0 && observed.backend_calls == 1);
    CHECK(owner.accepted_frames == 3 && owner.outcome_unknown);
}

static void test_live_callback_progress_and_replay(void)
{
    const int16_t frames[8] = {0};
    observations observed = {0};
    aqss_lab_owner owner;
    aqss_lab_callbacks callbacks;
    callback_metadata *metadata = malloc(sizeof(*metadata));
    CHECK(metadata != NULL);
    *metadata = (callback_metadata){.work_id = 42, .observed = &observed};
    CHECK(aqss_lab_owner_init(&owner, 42, frames, 8, accept_prefix, &observed));
    CHECK(aqss_lab_callbacks_init(&callbacks, &owner, metadata, inspect_metadata));
    aqss_lab_callback_ticket ticket = aqss_lab_queue_callback(&callbacks);
    CHECK(aqss_lab_deliver_callback(&callbacks, ticket));
    CHECK(observed.body_calls == 1 && observed.observed_work_id == 42);
    CHECK(callbacks.active == 0 && callbacks.queued == 0);
    CHECK(!aqss_lab_deliver_callback(&callbacks, ticket));
    CHECK(observed.body_calls == 1);
    CHECK(aqss_lab_take_callback_metadata(&callbacks) == NULL);
    aqss_lab_request_hold(&owner);
    CHECK(aqss_lab_take_callback_metadata(&callbacks) == NULL);
    CHECK(aqss_lab_acknowledge_hold(&owner));
    void *released = aqss_lab_take_callback_metadata(&callbacks);
    CHECK(released == metadata);
    free(released);
    CHECK(!aqss_lab_deliver_callback(&callbacks, ticket));
    CHECK(observed.body_calls == 1 && observed.backend_calls == 0);
}

static void test_active_callback_retains_metadata_through_hold(void)
{
    const int16_t frames[8] = {0};
    observations observed = {0};
    aqss_lab_owner owner;
    aqss_lab_callbacks callbacks;
    callback_metadata *metadata = malloc(sizeof(*metadata));
    CHECK(metadata != NULL);
    *metadata = (callback_metadata){
        .work_id = 43, .observed = &observed,
        .callbacks = &callbacks, .hold_inside = true
    };
    CHECK(aqss_lab_owner_init(&owner, 43, frames, 8, accept_prefix, &observed));
    CHECK(aqss_lab_callbacks_init(&callbacks, &owner, metadata, inspect_metadata));
    aqss_lab_callback_ticket ticket = aqss_lab_queue_callback(&callbacks);
    metadata->self = ticket;
    CHECK(aqss_lab_deliver_callback(&callbacks, ticket));
    CHECK(owner.hold_acknowledged);
    CHECK(observed.body_calls == 1 && observed.observed_work_id == 43);
    CHECK(callbacks.active == 0 && callbacks.queued == 0);
    void *released = aqss_lab_take_callback_metadata(&callbacks);
    CHECK(released == metadata);
    free(released);
    CHECK(!aqss_lab_deliver_callback(&callbacks, ticket));
    CHECK(observed.body_calls == 1 && observed.backend_calls == 0);
}

static void test_foreign_and_invalid_tickets_do_not_consume_queued_reference(void)
{
    const int16_t frames[8] = {0};
    observations observed = {0};
    aqss_lab_owner owner;
    aqss_lab_callbacks callbacks;
    aqss_lab_callbacks other_context = {0};
    callback_metadata *metadata = malloc(sizeof(*metadata));
    CHECK(metadata != NULL);
    *metadata = (callback_metadata){.work_id = 44, .observed = &observed};
    CHECK(aqss_lab_owner_init(&owner, 44, frames, 8, accept_prefix, &observed));
    CHECK(aqss_lab_callbacks_init(&callbacks, &owner, metadata, inspect_metadata));
    aqss_lab_callback_ticket ticket = aqss_lab_queue_callback(&callbacks);
    const aqss_lab_callback_ticket invalid[] = {
        {&other_context, ticket.sequence}, {&callbacks, 0},
        {&callbacks, ticket.sequence + 1}, {&callbacks, SIZE_MAX}
    };
    aqss_lab_request_hold(&owner);
    CHECK(aqss_lab_acknowledge_hold(&owner));
    for (size_t i = 0; i < sizeof(invalid) / sizeof(invalid[0]); ++i) {
        CHECK(!aqss_lab_deliver_callback(&callbacks, invalid[i]));
        CHECK(callbacks.queued == 1 && callbacks.active == 0);
        CHECK(aqss_lab_take_callback_metadata(&callbacks) == NULL);
    }
    CHECK(!aqss_lab_deliver_callback(&callbacks, ticket));
    CHECK(callbacks.queued == 0);
    void *released = aqss_lab_take_callback_metadata(&callbacks);
    CHECK(released == metadata);
    free(released);
    CHECK(observed.body_calls == 0 && observed.backend_calls == 0);
}

static ptrdiff_t accept_zero(void *context, const int16_t *frames, size_t count)
{
    observations *observed = context;
    CHECK(frames != NULL && count == 8);
    ++observed->backend_calls;
    return 0;
}

static void test_capacity_keeps_cleanup_available_with_full_owner_trace(void)
{
    const int16_t frames[8] = {0};
    observations observed = {0};
    aqss_lab_owner owner;
    aqss_lab_callbacks callbacks;
    callback_metadata *metadata = malloc(sizeof(*metadata));
    CHECK(metadata != NULL);
    *metadata = (callback_metadata){.work_id = 45, .observed = &observed};
    CHECK(aqss_lab_owner_init(&owner, 45, frames, 8, accept_zero, &observed));
    CHECK(aqss_lab_callbacks_init(&callbacks, &owner, metadata, inspect_metadata));
    for (size_t i = 0; i < AQSS_LAB_MAX_CALLS; ++i) {
        CHECK(aqss_lab_submit(&owner));
        CHECK(aqss_lab_record_return(&owner));
    }
    aqss_lab_callback_ticket tickets[AQSS_LAB_MAX_CALLBACKS];
    for (size_t i = 0; i < AQSS_LAB_MAX_CALLBACKS; ++i) {
        tickets[i] = aqss_lab_queue_callback(&callbacks);
        CHECK(tickets[i].sequence == i + 1);
    }
    CHECK(aqss_lab_queue_callback(&callbacks).context == NULL);
    CHECK(callbacks.capacity_exhausted && owner.admission_closed);
    CHECK(callbacks.queued == AQSS_LAB_MAX_CALLBACKS);
    CHECK(aqss_lab_acknowledge_hold(&owner));
    CHECK(owner.event_count == AQSS_LAB_MAX_EVENTS);
    aqss_lab_event retained[AQSS_LAB_MAX_EVENTS];
    memcpy(retained, owner.events, sizeof(retained));
    for (size_t i = 0; i < AQSS_LAB_MAX_CALLBACKS; ++i) {
        CHECK(aqss_lab_take_callback_metadata(&callbacks) == NULL);
        CHECK(!aqss_lab_deliver_callback(&callbacks, tickets[i]));
        CHECK(callbacks.queued == AQSS_LAB_MAX_CALLBACKS - i - 1);
        CHECK(!aqss_lab_deliver_callback(&callbacks, tickets[i]));
        CHECK(callbacks.queued == AQSS_LAB_MAX_CALLBACKS - i - 1);
    }
    CHECK(memcmp(retained, owner.events, sizeof(retained)) == 0);
    CHECK(owner.event_count == AQSS_LAB_MAX_EVENTS && owner.outcome_unknown);
    CHECK(observed.body_calls == 0 && observed.backend_calls == AQSS_LAB_MAX_CALLS);
    void *released = aqss_lab_take_callback_metadata(&callbacks);
    CHECK(released == metadata);
    free(released);
    for (size_t i = 0; i < AQSS_LAB_MAX_CALLBACKS; ++i) {
        CHECK(!aqss_lab_deliver_callback(&callbacks, tickets[i]));
    }
}

int main(void)
{
    test_queued_callback_retains_metadata_with_zero_active();
    test_live_callback_progress_and_replay();
    test_active_callback_retains_metadata_through_hold();
    test_foreign_and_invalid_tickets_do_not_consume_queued_reference();
    test_capacity_keeps_cleanup_available_with_full_owner_trace();
    puts("AQSS_CALLBACK_LAB_PASS: 5 deterministic C cases; native quiescence unqualified");
    return EXIT_SUCCESS;
}
