#include "owner.h"

#include <errno.h>
#include <stdio.h>
#include <stdlib.h>

#define CHECK(condition) do { \
    if (!(condition)) { \
        fprintf(stderr, "%s:%d: FAILED: %s\n", __func__, __LINE__, #condition); \
        exit(EXIT_FAILURE); \
    } \
} while (0)

typedef struct {
    aqss_lab_owner *owner;
    const ptrdiff_t *results;
    size_t index;
    bool hold_inside;
} script;

static ptrdiff_t write_result(void *context, const int16_t *frames, size_t count)
{
    script *s = context;
    (void)frames;
    (void)count;
    if (s->hold_inside) aqss_lab_request_hold(s->owner);
    return s->results[s->index++];
}

static void check_sequence(const aqss_lab_owner *owner)
{
    for (size_t i = 0; i < owner->event_count; ++i) {
        CHECK(owner->events[i].schema_version == 2);
        CHECK(owner->events[i].sequence == i + 1);
        CHECK(owner->events[i].work_id == owner->work_id);
    }
}

static void test_trace_distinguishes_prefix_zero_and_would_block(void)
{
    const int16_t frames[5] = {1, 2, 3, 4, 5};
    const ptrdiff_t returns[] = {3, 0, -EAGAIN, 2};
    const aqss_lab_return_kind kinds[] = {
        AQSS_LAB_RETURN_PREFIX, AQSS_LAB_RETURN_ZERO,
        AQSS_LAB_RETURN_WOULD_BLOCK, AQSS_LAB_RETURN_PREFIX
    };
    aqss_lab_owner owner;
    script s = {.owner = &owner, .results = returns};
    CHECK(aqss_lab_owner_init(&owner, 301, frames, 5, write_result, &s));
    for (size_t i = 0; i < 4; ++i) {
        size_t before = owner.accepted_frames;
        CHECK(aqss_lab_submit(&owner));
        const aqss_lab_event *entry = &owner.events[3 * i];
        const aqss_lab_event *returned = entry + 1;
        CHECK(entry->call_index == i + 1 && entry->admission_revision == 1);
        CHECK(entry->accepted_frames == before && entry->offset == before);
        CHECK(entry->return_kind == AQSS_LAB_RETURN_NONE);
        CHECK(returned->return_kind == kinds[i]);
        CHECK(returned->returned_frames == returns[i]);
        CHECK(returned->accepted_frames == before);
        CHECK(aqss_lab_record_return(&owner));
        CHECK(owner.events[3 * i + 2].accepted_frames == owner.accepted_frames);
        CHECK(owner.events[3 * i + 2].return_kind == kinds[i]);
    }
    CHECK(owner.accepted_frames == 5);
    aqss_lab_request_hold(&owner);
    CHECK(aqss_lab_acknowledge_hold(&owner));
    CHECK(owner.events[12].admission_revision == 2);
    CHECK(owner.events[13].accepted_frames == 5);
    check_sequence(&owner);
}

static void test_invalid_return_keeps_accounting_and_cut_separate(void)
{
    const int16_t frames[5] = {1, 2, 3, 4, 5};
    const ptrdiff_t returns[] = {3, -EIO};
    aqss_lab_owner owner;
    script s = {.owner = &owner, .results = returns};
    CHECK(aqss_lab_owner_init(&owner, 302, frames, 5, write_result, &s));
    CHECK(aqss_lab_submit(&owner) && aqss_lab_record_return(&owner));
    CHECK(aqss_lab_submit(&owner));
    CHECK(owner.events[4].return_kind == AQSS_LAB_RETURN_INVALID);
    CHECK(owner.events[4].accepted_frames == 3);
    CHECK(owner.events[4].admission_revision == 1);
    CHECK(owner.events[5].kind == AQSS_LAB_EVENT_HOLD_REQUESTED);
    CHECK(owner.events[5].admission_revision == 2);
    CHECK(!aqss_lab_acknowledge_hold(&owner));
    CHECK(aqss_lab_record_return(&owner));
    CHECK(owner.events[6].return_kind == AQSS_LAB_RETURN_INVALID);
    CHECK(owner.events[6].accepted_frames == 3);
    CHECK(aqss_lab_acknowledge_hold(&owner));
    CHECK(owner.outcome_unknown && owner.first_fault == AQSS_LAB_FAULT_BACKEND_RESULT);
    check_sequence(&owner);
}

static void test_inflight_hold_revision_does_not_rewrite_entry(void)
{
    const int16_t frames[5] = {1, 2, 3, 4, 5};
    const ptrdiff_t returns[] = {3};
    aqss_lab_owner owner;
    script s = {.owner = &owner, .results = returns, .hold_inside = true};
    CHECK(aqss_lab_owner_init(&owner, 303, frames, 5, write_result, &s));
    CHECK(aqss_lab_submit(&owner));
    CHECK(owner.events[0].kind == AQSS_LAB_EVENT_CALL_ENTERED);
    CHECK(owner.events[0].admission_revision == 1);
    CHECK(owner.events[1].kind == AQSS_LAB_EVENT_HOLD_REQUESTED);
    CHECK(owner.events[1].admission_revision == 2);
    CHECK(owner.events[2].kind == AQSS_LAB_EVENT_CALL_RETURNED);
    CHECK(owner.events[2].accepted_frames == 0);
    CHECK(aqss_lab_record_return(&owner));
    CHECK(owner.events[3].accepted_frames == 3);
    CHECK(aqss_lab_acknowledge_hold(&owner));
    CHECK(owner.events[4].return_kind == AQSS_LAB_RETURN_NONE);
    CHECK(!aqss_lab_submit(&owner) && s.index == 1);
    check_sequence(&owner);
}

static void test_full_trace_retains_contiguous_sequences_and_reserved_cut(void)
{
    const int16_t frames[1] = {1};
    const ptrdiff_t returns[AQSS_LAB_MAX_CALLS] = {0};
    aqss_lab_owner owner;
    script s = {.owner = &owner, .results = returns};
    CHECK(aqss_lab_owner_init(&owner, 304, frames, 1, write_result, &s));
    for (size_t i = 0; i < AQSS_LAB_MAX_CALLS; ++i) {
        CHECK(aqss_lab_submit(&owner) && aqss_lab_record_return(&owner));
    }
    CHECK(!aqss_lab_submit(&owner));
    CHECK(aqss_lab_acknowledge_hold(&owner));
    CHECK(owner.event_count == AQSS_LAB_MAX_EVENTS);
    CHECK(owner.events[24].kind == AQSS_LAB_EVENT_HOLD_REQUESTED);
    CHECK(owner.events[25].kind == AQSS_LAB_EVENT_HOLD_ACKNOWLEDGED);
    CHECK(owner.events[25].call_index == 8 && owner.events[25].accepted_frames == 0);
    CHECK(owner.trace_exhausted && owner.outcome_unknown);
    check_sequence(&owner);
}

int main(void)
{
    test_trace_distinguishes_prefix_zero_and_would_block();
    test_invalid_return_keeps_accounting_and_cut_separate();
    test_inflight_hold_revision_does_not_rewrite_entry();
    test_full_trace_retains_contiguous_sequences_and_reserved_cut();
    puts("AQSS_LAB_TRACE_TESTS_PASSED 4");
    return 0;
}
