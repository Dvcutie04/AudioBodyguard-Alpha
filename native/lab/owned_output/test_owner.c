#include "owner.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

/* Checks must stay active even if a caller compiles with NDEBUG. */
#define CHECK(condition) do { \
    if (!(condition)) { \
        fprintf(stderr, "%s:%d: FAILED: %s\n", __func__, __LINE__, #condition); \
        exit(EXIT_FAILURE); \
    } \
} while (0)

typedef struct {
    aqss_lab_owner *owner;
    const int16_t *source;
    size_t source_count;
    size_t calls;
    size_t accepted;
    bool request_hold_inside_call;
    ptrdiff_t invalid_suffix_return;
    int16_t copied[8];
} scripted_backend;

static ptrdiff_t accept_prefix_then_suffix(void *context, const int16_t *frames,
                                          size_t frame_count)
{
    scripted_backend *backend = context;
    CHECK(backend->owner->phase == AQSS_LAB_CALL_ENTERED);
    if (backend->request_hold_inside_call) {
        aqss_lab_request_hold(backend->owner);
        CHECK(!aqss_lab_acknowledge_hold(backend->owner));
        CHECK(!aqss_lab_submit(backend->owner));
        CHECK(!aqss_lab_record_return(backend->owner));
    }
    CHECK(backend->calls < 2);
    CHECK(frames == backend->source + backend->accepted);
    CHECK(frame_count == backend->source_count - backend->accepted);
    if (backend->calls == 1 && backend->invalid_suffix_return != 0) {
        ++backend->calls;
        return backend->invalid_suffix_return;
    }
    size_t accepted = backend->calls == 0 ? 3 : frame_count;
    CHECK(backend->accepted + accepted <= 8);
    memcpy(backend->copied + backend->accepted, frames,
           accepted * sizeof(*frames));
    backend->accepted += accepted;
    ++backend->calls;
    return (ptrdiff_t)accepted;
}

static void test_partial_write_hold_rejects_suffix(void)
{
    const int16_t frames[8] = {11, -22, 33, -44, 55, -66, 77, -88};
    aqss_lab_owner owner;
    scripted_backend backend = {
        .owner = &owner, .source = frames, .source_count = 8
    };
    CHECK(aqss_lab_owner_init(&owner, 17, frames, 8,
                              accept_prefix_then_suffix, &backend));
    CHECK(aqss_lab_submit(&owner));
    CHECK(owner.phase == AQSS_LAB_CALL_RETURNED);
    CHECK(owner.accepted_frames == 0); /* Return not yet accounted for. */
    CHECK(owner.returned_frames == 3);
    CHECK(aqss_lab_record_return(&owner));
    CHECK(owner.phase == AQSS_LAB_RETURN_RECORDED);
    CHECK(owner.accepted_frames == 3);

    aqss_lab_request_hold(&owner);
    CHECK(aqss_lab_acknowledge_hold(&owner));
    size_t events_at_cut = owner.event_count;
    bool retry_dispatched = aqss_lab_submit(&owner);
    CHECK(backend.calls == 1); /* The prior call happened; only retry is blocked. */
    CHECK(!retry_dispatched);
    CHECK(owner.event_count == events_at_cut);
    CHECK(owner.accepted_frames == 3);
    CHECK(owner.frame_count - owner.accepted_frames == 5);
    CHECK(owner.outcome_unknown);
    CHECK(backend.accepted == 3);
    CHECK(memcmp(backend.copied, frames, 3 * sizeof(*frames)) == 0);
    /* Those copied frames survive the cut; no cancellation or settlement. */
    CHECK(owner.event_count == 5);
    const aqss_lab_event_kind expected[] = {
        AQSS_LAB_EVENT_CALL_ENTERED, AQSS_LAB_EVENT_CALL_RETURNED,
        AQSS_LAB_EVENT_RETURN_RECORDED, AQSS_LAB_EVENT_HOLD_REQUESTED,
        AQSS_LAB_EVENT_HOLD_ACKNOWLEDGED
    };
    for (size_t i = 0; i < owner.event_count; ++i) {
        CHECK(owner.events[i].kind == expected[i]);
        CHECK(owner.events[i].work_id == 17);
    }
    aqss_lab_request_hold(&owner);
    CHECK(aqss_lab_acknowledge_hold(&owner));
    CHECK(!aqss_lab_record_return(&owner));
    CHECK(owner.event_count == events_at_cut);
}

static void test_partial_write_progress_preserves_exact_suffix(void)
{
    const int16_t frames[8] = {1, -2, 3, -4, 5, -6, 7, -8};
    aqss_lab_owner owner;
    scripted_backend backend = {
        .owner = &owner, .source = frames, .source_count = 8
    };
    CHECK(aqss_lab_owner_init(&owner, 18, frames, 8,
                              accept_prefix_then_suffix, &backend));
    CHECK(!aqss_lab_acknowledge_hold(&owner));
    for (size_t i = 0; i < 2; ++i) {
        CHECK(aqss_lab_submit(&owner));
        CHECK(owner.phase == AQSS_LAB_CALL_RETURNED);
        CHECK(aqss_lab_record_return(&owner));
    }
    CHECK(backend.calls == 2);
    CHECK(owner.accepted_frames == 8);
    CHECK(memcmp(backend.copied, frames, sizeof(frames)) == 0);
    CHECK(!aqss_lab_submit(&owner));
    CHECK(owner.event_count == 6);
    CHECK(owner.events[3].offset == 3);
    CHECK(owner.events[3].requested_frames == 5);
    CHECK(owner.outcome_unknown); /* Complete transfer is not observed output. */
    CHECK(!owner.hold_acknowledged);
}

static void check_hold_waits_for_accounting(bool during_call)
{
    const int16_t frames[8] = {10, 20, 30, 40, 50, 60, 70, 80};
    aqss_lab_owner owner;
    scripted_backend backend = {
        .owner = &owner, .source = frames, .source_count = 8,
        .request_hold_inside_call = during_call
    };
    CHECK(aqss_lab_owner_init(&owner, 19, frames, 8,
                              accept_prefix_then_suffix, &backend));
    CHECK(aqss_lab_submit(&owner));
    CHECK(owner.phase == AQSS_LAB_CALL_RETURNED);
    if (!during_call) {
        aqss_lab_request_hold(&owner);
    }
    CHECK(owner.admission_closed);
    CHECK(!aqss_lab_acknowledge_hold(&owner));
    CHECK(!aqss_lab_submit(&owner));
    CHECK(owner.accepted_frames == 0);
    CHECK(owner.outcome_unknown);
    CHECK(backend.accepted == 3); /* Transfer already occurred in either case. */
    CHECK(owner.event_count == 3);
    CHECK(owner.events[1].kind == (during_call ?
          AQSS_LAB_EVENT_HOLD_REQUESTED : AQSS_LAB_EVENT_CALL_RETURNED));
    CHECK(owner.events[2].kind == (during_call ?
          AQSS_LAB_EVENT_CALL_RETURNED : AQSS_LAB_EVENT_HOLD_REQUESTED));
    CHECK(aqss_lab_record_return(&owner));
    CHECK(aqss_lab_acknowledge_hold(&owner));
    CHECK(owner.events[3].kind == AQSS_LAB_EVENT_RETURN_RECORDED);
    CHECK(owner.events[4].kind == AQSS_LAB_EVENT_HOLD_ACKNOWLEDGED);
    CHECK(owner.accepted_frames == 3);
    CHECK(owner.outcome_unknown);
    CHECK(!aqss_lab_submit(&owner));
    CHECK(backend.calls == 1);
}

static void test_inflight_hold_waits_for_recorded_return(void)
{
    check_hold_waits_for_accounting(true);
}

static void test_returned_call_cannot_ack_before_recording(void)
{
    check_hold_waits_for_accounting(false);
}

static ptrdiff_t accept_no_frames(void *context, const int16_t *frames,
                                 size_t frame_count)
{
    scripted_backend *backend = context;
    CHECK(backend->owner->phase == AQSS_LAB_CALL_ENTERED);
    CHECK(frames == backend->source);
    CHECK(frame_count == backend->source_count);
    ++backend->calls;
    return 0;
}

static void test_trace_capacity_reserves_hold_and_preserves_history(void)
{
    const int16_t frames[1] = {123};
    aqss_lab_owner owner;
    scripted_backend backend = {
        .owner = &owner, .source = frames, .source_count = 1
    };
    CHECK(aqss_lab_owner_init(&owner, 20, frames, 1, accept_no_frames, &backend));
    for (size_t i = 0; i < AQSS_LAB_MAX_CALLS; ++i) {
        CHECK(aqss_lab_submit(&owner));
        CHECK(aqss_lab_record_return(&owner));
    }
    aqss_lab_event retained[3u * AQSS_LAB_MAX_CALLS];
    memcpy(retained, owner.events, sizeof(retained));
    CHECK(!aqss_lab_submit(&owner));
    CHECK(backend.calls == AQSS_LAB_MAX_CALLS);
    CHECK(owner.trace_exhausted);
    CHECK(owner.admission_closed);
    CHECK(aqss_lab_acknowledge_hold(&owner));
    CHECK(owner.event_count == AQSS_LAB_MAX_EVENTS);
    CHECK(memcmp(retained, owner.events, sizeof(retained)) == 0);
    CHECK(owner.events[AQSS_LAB_MAX_EVENTS - 2].kind ==
          AQSS_LAB_EVENT_HOLD_REQUESTED);
    CHECK(owner.events[AQSS_LAB_MAX_EVENTS - 1].kind ==
          AQSS_LAB_EVENT_HOLD_ACKNOWLEDGED);
    CHECK(!aqss_lab_submit(&owner));
    aqss_lab_request_hold(&owner);
    CHECK(aqss_lab_acknowledge_hold(&owner));
    CHECK(owner.event_count == AQSS_LAB_MAX_EVENTS);
    CHECK(owner.accepted_frames == 0);
    CHECK(owner.outcome_unknown); /* Zero accepted is still not a finality proof. */
}

static void test_invalid_return_preserves_prefix_and_inhibits_retry(void)
{
    const int16_t frames[8] = {9, 8, 7, 6, 5, 4, 3, 2};
    const ptrdiff_t invalid_results[] = {-1, 6}; /* Remaining suffix has 5 frames. */
    for (size_t i = 0; i < 2; ++i) {
        aqss_lab_owner owner;
        scripted_backend backend = {
            .owner = &owner, .source = frames, .source_count = 8,
            .invalid_suffix_return = invalid_results[i]
        };
        CHECK(aqss_lab_owner_init(&owner, 21, frames, 8,
                                  accept_prefix_then_suffix, &backend));
        CHECK(aqss_lab_submit(&owner));
        CHECK(aqss_lab_record_return(&owner));
        CHECK(aqss_lab_submit(&owner));
        CHECK(aqss_lab_record_return(&owner));
        CHECK(owner.invalid_return);
        CHECK(owner.admission_closed);
        CHECK(owner.accepted_frames == 3);
        CHECK(owner.outcome_unknown);
        CHECK(aqss_lab_acknowledge_hold(&owner));
        CHECK(!aqss_lab_submit(&owner));
        CHECK(backend.calls == 2);
        CHECK(memcmp(backend.copied, frames, 3 * sizeof(*frames)) == 0);
    }
}

int main(void)
{
    test_partial_write_hold_rejects_suffix();
    test_partial_write_progress_preserves_exact_suffix();
    test_inflight_hold_waits_for_recorded_return();
    test_returned_call_cannot_ack_before_recording();
    test_trace_capacity_reserves_hold_and_preserves_history();
    test_invalid_return_preserves_prefix_and_inhibits_retry();
    puts("AQSS_NATIVE_LAB_PASS: 6 deterministic C cases; physical output unqualified");
    return EXIT_SUCCESS;
}
