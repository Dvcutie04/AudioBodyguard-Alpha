#include "hold.h"

#include <stdio.h>
#include <stdlib.h>

#define CHECK(condition) do { \
    if (!(condition)) { \
        fprintf(stderr, "%s:%d: FAILED: %s\n", __func__, __LINE__, #condition); \
        exit(EXIT_FAILURE); \
    } \
} while (0)

static ptrdiff_t accept_prefix(void *context, const int16_t *frames, size_t count)
{
    size_t *calls = context;
    CHECK(frames != NULL && count == 8);
    ++*calls;
    return 3;
}

static void initialize(aqss_lab_owner *owner, size_t *calls)
{
    static const int16_t frames[8] = {1, 2, 3, 4, 5, 6, 7, 8};
    *calls = 0;
    CHECK(aqss_lab_owner_init(owner, 61, frames, 8, accept_prefix, calls));
}

static void test_old_request_and_runtime_cannot_satisfy_current_cut(void)
{
    aqss_lab_owner owner;
    size_t calls;
    initialize(&owner, &calls);
    aqss_lab_hold_control current = {0};
    const aqss_lab_hold_identity identity = {1, 2, 30, 40};
    CHECK(aqss_lab_begin_hold(&current, &owner, identity, 5, 100, 200));
    aqss_lab_hold_ack valid;
    CHECK(aqss_lab_produce_hold_ack(&current, &valid));
    aqss_lab_hold_ack old = valid;
    old.identity.request_id = 39;
    CHECK(!aqss_lab_match_hold_ack(&current, &old, 5, 101));
    old = valid;
    old.identity.runtime_id = 29;
    CHECK(!aqss_lab_match_hold_ack(&current, &old, 5, 102));
    CHECK(aqss_lab_match_hold_ack(&current, &valid, 5, 103));
    CHECK(calls == 0 && owner.admission_closed);
}

static void test_complete_scope_and_status_match_without_refresh(void)
{
    aqss_lab_owner owner;
    size_t calls;
    initialize(&owner, &calls);
    aqss_lab_hold_control current = {0};
    const aqss_lab_hold_identity identity = {1, 2, 30, 40};
    CHECK(aqss_lab_begin_hold(&current, &owner, identity, 5, 100, 200));
    aqss_lab_hold_ack valid;
    CHECK(aqss_lab_produce_hold_ack(&current, &valid));
    CHECK(valid.admission_revision == 2);
    aqss_lab_hold_ack other[4] = {valid, valid, valid, valid};
    other[0].identity.endpoint_id = 9;
    other[1].identity.resource_id = 9;
    other[2].admission_revision = 1;
    other[3].status = AQSS_LAB_HOLD_PENDING;
    const size_t events = owner.event_count;
    for (size_t i = 0; i < 4; ++i) {
        CHECK(!aqss_lab_match_hold_ack(&current, &other[i], 5, 101 + i));
    }
    CHECK(!aqss_lab_match_hold_ack(&current, NULL, 5, 105));
    /* An unrelated clock cannot be interpreted as this deadline's clock. */
    CHECK(!aqss_lab_match_hold_ack(&current, &valid, 6, UINT64_MAX));
    CHECK(!current.time_invalid && current.last_tick == 105);
    CHECK(aqss_lab_match_hold_ack(&current, &valid, 5, 106));
    CHECK(aqss_lab_match_hold_ack(&current, &valid, 5, 106));
    CHECK(current.deadline == 200 && owner.event_count == events);
    CHECK(!aqss_lab_submit(&owner) && calls == 0);
}

static void test_acknowledgement_waits_for_recorded_return(void)
{
    aqss_lab_owner owner;
    size_t calls;
    initialize(&owner, &calls);
    CHECK(aqss_lab_submit(&owner));
    aqss_lab_hold_control control = {0};
    const aqss_lab_hold_identity identity = {1, 2, 30, 40};
    CHECK(aqss_lab_begin_hold(&control, &owner, identity, 5, 100, 200));
    aqss_lab_hold_ack ack = {0};
    CHECK(!aqss_lab_produce_hold_ack(&control, &ack));
    CHECK(ack.identity.request_id == 0);
    ack = (aqss_lab_hold_ack){identity, 2, AQSS_LAB_HOLD_ACCOUNTED};
    CHECK(!aqss_lab_match_hold_ack(&control, &ack, 5, 101));
    CHECK(aqss_lab_record_return(&owner));
    CHECK(aqss_lab_produce_hold_ack(&control, &ack));
    CHECK(aqss_lab_match_hold_ack(&control, &ack, 5, 102));
    CHECK(owner.accepted_frames == 3 && owner.outcome_unknown);
    CHECK(!aqss_lab_submit(&owner) && calls == 1);
}

static void test_expiry_and_clock_rollback_are_terminal(void)
{
    for (size_t expired = 0; expired < 2; ++expired) {
        aqss_lab_owner owner;
        size_t calls;
        initialize(&owner, &calls);
        aqss_lab_hold_control control = {0};
        const aqss_lab_hold_identity identity = {1, 2, 30, 40};
        CHECK(aqss_lab_begin_hold(&control, &owner, identity, 5, 100, 200));
        CHECK(!aqss_lab_match_hold_ack(&control, NULL, 5, 150));
        CHECK(!aqss_lab_match_hold_ack(&control, NULL, 5, expired ? 200 : 149));
        CHECK(control.time_invalid);
        aqss_lab_hold_ack late;
        /* Owner accounting/cleanup is possible even after the wait expires. */
        CHECK(aqss_lab_produce_hold_ack(&control, &late));
        CHECK(!aqss_lab_match_hold_ack(&control, &late, 5, 199));
        CHECK(control.deadline == 200 && owner.hold_acknowledged);
        CHECK(!aqss_lab_submit(&owner) && calls == 0);
    }
}

static void test_invalid_request_does_not_replace_control_or_close_owner(void)
{
    aqss_lab_owner owner;
    size_t calls;
    initialize(&owner, &calls);
    aqss_lab_hold_control control = {0};
    const aqss_lab_hold_identity invalid[] = {
        {0, 2, 3, 4}, {1, 0, 3, 4}, {1, 2, 0, 4}, {1, 2, 3, 0}
    };
    for (size_t i = 0; i < 4; ++i) {
        CHECK(!aqss_lab_begin_hold(&control, &owner, invalid[i], 5, 100, 200));
    }
    const aqss_lab_hold_identity valid = {1, 2, 3, 4};
    CHECK(!aqss_lab_begin_hold(&control, &owner, valid, 0, 100, 200));
    CHECK(!aqss_lab_begin_hold(&control, &owner, valid, 5, 200, 200));
    CHECK(!aqss_lab_begin_hold(&control, &owner, valid, 5, 201, 200));
    CHECK(!control.initialized && !owner.admission_closed);
    CHECK(owner.admission_revision == 1 && owner.event_count == 0 && calls == 0);
}

static void test_same_cut_cannot_rebind_or_refresh_deadline(void)
{
    aqss_lab_owner owner;
    size_t calls;
    initialize(&owner, &calls);
    aqss_lab_hold_control original = {0}, replacement = {0};
    const aqss_lab_hold_identity identity = {1, 2, 30, 40};
    CHECK(aqss_lab_begin_hold(&original, &owner, identity, 5, 100, 200));
    CHECK(!aqss_lab_match_hold_ack(&original, NULL, 5, 200));
    CHECK(!aqss_lab_begin_hold(&original, &owner, identity, 5, 201, 400));
    CHECK(!aqss_lab_begin_hold(&replacement, &owner, identity, 5, 201, 400));
    CHECK(original.deadline == 200 && original.time_invalid);
    CHECK(!replacement.initialized);
    aqss_lab_hold_ack late;
    CHECK(aqss_lab_produce_hold_ack(&original, &late));
    CHECK(!aqss_lab_match_hold_ack(&original, &late, 5, 202));
    CHECK(owner.hold_acknowledged && calls == 0);
}

int main(void)
{
    test_old_request_and_runtime_cannot_satisfy_current_cut();
    test_complete_scope_and_status_match_without_refresh();
    test_acknowledgement_waits_for_recorded_return();
    test_expiry_and_clock_rollback_are_terminal();
    test_invalid_request_does_not_replace_control_or_close_owner();
    test_same_cut_cannot_rebind_or_refresh_deadline();
    puts("AQSS_HOLD_LAB_PASS: 6 deterministic C cases; acknowledgement is not finality");
    return EXIT_SUCCESS;
}
