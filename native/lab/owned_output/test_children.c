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

typedef struct fixture fixture;

typedef struct {
    uint64_t work_id;
    fixture *test;
} child_metadata;

struct fixture {
    aqss_lab_owner owner;
    aqss_lab_callbacks callbacks;
    aqss_lab_callbacks foreign_context;
    aqss_lab_callback_ticket parent;
    aqss_lab_callback_ticket peer;
    aqss_lab_child_reference children[AQSS_LAB_MAX_CHILD_REFERENCES];
    child_metadata *metadata;
    const child_metadata *borrowed;
    size_t body_calls;
    size_t backend_calls;
    bool zero_progress;
};

static ptrdiff_t scripted_write(void *context, const int16_t *frames, size_t count)
{
    fixture *test = context;
    CHECK(frames != NULL && count == 8);
    ++test->backend_calls;
    return test->zero_progress ? 0 : 3;
}

static void initialize(fixture *test, aqss_lab_callback_body body)
{
    static const int16_t frames[8] = {1, 2, 3, 4, 5, 6, 7, 8};
    *test = (fixture){0};
    test->metadata = malloc(sizeof(*test->metadata));
    CHECK(test->metadata != NULL);
    *test->metadata = (child_metadata){.work_id = 51, .test = test};
    CHECK(aqss_lab_owner_init(&test->owner, 51, frames, 8, scripted_write, test));
    CHECK(aqss_lab_callbacks_init(&test->callbacks, &test->owner,
                                 test->metadata, body));
}

static void reclaim_metadata(fixture *test)
{
    void *released = aqss_lab_take_callback_metadata(&test->callbacks);
    CHECK(released != NULL && released == test->metadata);
    free(released);
    test->metadata = NULL;
    test->borrowed = NULL;
    CHECK(test->callbacks.metadata == NULL);
}

static void retain_one_child(void *context)
{
    child_metadata *metadata = context;
    fixture *test = metadata->test;
    ++test->body_calls;
    test->children[0] = aqss_lab_retain_child(&test->callbacks, test->parent);
    CHECK(test->children[0].context == &test->callbacks);
    CHECK(test->children[0].parent_sequence == test->parent.sequence);
    test->borrowed = metadata; /* Hand off only after retention succeeds. */
}

static void test_child_retains_metadata_after_parent_returns(void)
{
    fixture test;
    initialize(&test, retain_one_child);
    CHECK(aqss_lab_submit(&test.owner));
    CHECK(aqss_lab_record_return(&test.owner));
    test.parent = aqss_lab_queue_callback(&test.callbacks);
    CHECK(aqss_lab_deliver_callback(&test.callbacks, test.parent));
    CHECK(test.callbacks.queued == 0 && test.callbacks.active == 0);
    CHECK(test.callbacks.children_retained == 1);
    CHECK(test.body_calls == 1 && test.borrowed->work_id == 51);
    CHECK(aqss_lab_retain_child(&test.callbacks, test.parent).context == NULL);
    aqss_lab_request_hold(&test.owner);
    CHECK(aqss_lab_acknowledge_hold(&test.owner));
    CHECK(aqss_lab_take_callback_metadata(&test.callbacks) == NULL);
    CHECK(test.borrowed->work_id == 51); /* Existing child still has live data. */
    aqss_lab_event retained[AQSS_LAB_MAX_EVENTS];
    memcpy(retained, test.owner.events, sizeof(retained));
    CHECK(aqss_lab_release_child(&test.callbacks, test.children[0]));
    CHECK(test.callbacks.children_retained == 0);
    CHECK(!aqss_lab_submit(&test.owner));
    CHECK(aqss_lab_queue_callback(&test.callbacks).context == NULL);
    CHECK(memcmp(retained, test.owner.events, sizeof(retained)) == 0);
    CHECK(test.backend_calls == 1);
    CHECK(test.owner.accepted_frames == 3 && test.owner.outcome_unknown);
    reclaim_metadata(&test);
    /* Stable value references remain safe to reject after the actual free. */
    CHECK(!aqss_lab_release_child(&test.callbacks, test.children[0]));
    CHECK(!aqss_lab_deliver_callback(&test.callbacks, test.parent));
    CHECK(aqss_lab_take_callback_metadata(&test.callbacks) == NULL);
}

static void retain_around_hold(void *context)
{
    child_metadata *metadata = context;
    fixture *test = metadata->test;
    ++test->body_calls;
    const aqss_lab_callback_ticket rejected[] = {
        {&test->foreign_context, test->parent.sequence},
        {&test->callbacks, 0},
        {&test->callbacks, SIZE_MAX},
        {&test->callbacks, test->callbacks.issued + 1},
        test->peer
    };
    for (size_t i = 0; i < sizeof(rejected) / sizeof(rejected[0]); ++i) {
        CHECK(aqss_lab_retain_child(&test->callbacks, rejected[i]).context == NULL);
    }
    CHECK(test->callbacks.children_issued == 0);
    test->children[0] = aqss_lab_retain_child(&test->callbacks, test->parent);
    CHECK(test->children[0].context == &test->callbacks);
    test->borrowed = metadata;
    aqss_lab_request_hold(&test->owner);
    CHECK(aqss_lab_acknowledge_hold(&test->owner));
    CHECK(test->callbacks.active == 1);
    CHECK(aqss_lab_retain_child(&test->callbacks, test->parent).context == NULL);
    CHECK(aqss_lab_queue_callback(&test->callbacks).context == NULL);
    CHECK(!aqss_lab_submit(&test->owner));
    CHECK(aqss_lab_take_callback_metadata(&test->callbacks) == NULL);
}

static void test_child_acquisition_requires_active_parent_and_open_admission(void)
{
    fixture test;
    initialize(&test, retain_around_hold);
    test.parent = aqss_lab_queue_callback(&test.callbacks);
    test.peer = aqss_lab_queue_callback(&test.callbacks);
    CHECK(aqss_lab_retain_child(&test.callbacks, test.parent).context == NULL);
    CHECK(aqss_lab_deliver_callback(&test.callbacks, test.parent));
    CHECK(test.callbacks.children_retained == 1 && test.callbacks.active == 0);
    CHECK(test.callbacks.queued == 1);
    CHECK(test.borrowed->work_id == 51);
    CHECK(aqss_lab_release_child(&test.callbacks, test.children[0]));
    CHECK(aqss_lab_take_callback_metadata(&test.callbacks) == NULL);
    /* The remaining queued peer keeps metadata alive after the child releases. */
    CHECK(!aqss_lab_deliver_callback(&test.callbacks, test.peer));
    CHECK(test.callbacks.queued == 0 && test.body_calls == 1);
    CHECK(test.backend_calls == 0);
    reclaim_metadata(&test);
}

static void retain_two_children(void *context)
{
    retain_one_child(context);
    child_metadata *metadata = context;
    fixture *test = metadata->test;
    test->children[1] = aqss_lab_retain_child(&test->callbacks, test->parent);
    CHECK(test->children[1].context == &test->callbacks);
    CHECK(test->children[1].sequence != test->children[0].sequence);
}

static void test_invalid_and_duplicate_releases_preserve_other_children(void)
{
    fixture test;
    initialize(&test, retain_two_children);
    test.parent = aqss_lab_queue_callback(&test.callbacks);
    CHECK(aqss_lab_deliver_callback(&test.callbacks, test.parent));
    aqss_lab_request_hold(&test.owner);
    CHECK(aqss_lab_acknowledge_hold(&test.owner));
    const aqss_lab_child_reference valid = test.children[0];
    const aqss_lab_child_reference rejected[] = {
        {&test.foreign_context, valid.sequence, valid.parent_sequence},
        {&test.callbacks, 0, valid.parent_sequence},
        {&test.callbacks, SIZE_MAX, valid.parent_sequence},
        {&test.callbacks, test.callbacks.children_issued + 1, valid.parent_sequence},
        {&test.callbacks, valid.sequence, valid.parent_sequence + 1}
    };
    for (size_t i = 0; i < sizeof(rejected) / sizeof(rejected[0]); ++i) {
        CHECK(!aqss_lab_release_child(&test.callbacks, rejected[i]));
        CHECK(test.callbacks.children_retained == 2);
        CHECK(aqss_lab_take_callback_metadata(&test.callbacks) == NULL);
    }
    CHECK(aqss_lab_release_child(&test.callbacks, valid));
    CHECK(!aqss_lab_release_child(&test.callbacks, valid));
    CHECK(test.callbacks.children_retained == 1);
    CHECK(aqss_lab_take_callback_metadata(&test.callbacks) == NULL);
    CHECK(test.borrowed->work_id == 51); /* The second child still holds it. */
    CHECK(aqss_lab_release_child(&test.callbacks, test.children[1]));
    reclaim_metadata(&test);
    CHECK(!aqss_lab_release_child(&test.callbacks, test.children[1]));
    CHECK(!aqss_lab_release_child(&test.callbacks, valid));
    CHECK(test.body_calls == 1 && test.backend_calls == 0);
}

static void exhaust_child_capacity(void *context)
{
    child_metadata *metadata = context;
    fixture *test = metadata->test;
    ++test->body_calls;
    for (size_t i = 0; i < AQSS_LAB_MAX_CHILD_REFERENCES; ++i) {
        test->children[i] = aqss_lab_retain_child(&test->callbacks, test->parent);
        CHECK(test->children[i].context == &test->callbacks);
    }
    test->borrowed = metadata;
    CHECK(aqss_lab_retain_child(&test->callbacks, test->parent).context == NULL);
    CHECK(test->callbacks.child_capacity_exhausted);
    CHECK(test->owner.admission_closed);
    CHECK(aqss_lab_acknowledge_hold(&test->owner));
    CHECK(aqss_lab_take_callback_metadata(&test->callbacks) == NULL);
}

static void test_child_cleanup_remains_available_at_capacity(void)
{
    fixture test;
    initialize(&test, exhaust_child_capacity);
    test.zero_progress = true;
    for (size_t i = 0; i < AQSS_LAB_MAX_CALLS; ++i) {
        CHECK(aqss_lab_submit(&test.owner));
        CHECK(aqss_lab_record_return(&test.owner));
    }
    test.parent = aqss_lab_queue_callback(&test.callbacks);
    CHECK(aqss_lab_deliver_callback(&test.callbacks, test.parent));
    CHECK(test.owner.event_count == AQSS_LAB_MAX_EVENTS);
    CHECK(test.callbacks.children_retained == AQSS_LAB_MAX_CHILD_REFERENCES);
    CHECK(test.callbacks.queued == 0 && test.callbacks.active == 0);
    aqss_lab_event retained[AQSS_LAB_MAX_EVENTS];
    memcpy(retained, test.owner.events, sizeof(retained));
    for (size_t i = 0; i < AQSS_LAB_MAX_CHILD_REFERENCES; ++i) {
        CHECK(aqss_lab_take_callback_metadata(&test.callbacks) == NULL);
        CHECK(test.borrowed->work_id == 51);
        CHECK(aqss_lab_release_child(&test.callbacks, test.children[i]));
        CHECK(!aqss_lab_release_child(&test.callbacks, test.children[i]));
    }
    CHECK(test.callbacks.children_retained == 0);
    CHECK(!aqss_lab_submit(&test.owner));
    CHECK(aqss_lab_queue_callback(&test.callbacks).context == NULL);
    CHECK(memcmp(retained, test.owner.events, sizeof(retained)) == 0);
    CHECK(test.owner.event_count == AQSS_LAB_MAX_EVENTS);
    CHECK(test.backend_calls == AQSS_LAB_MAX_CALLS && test.body_calls == 1);
    CHECK(test.owner.accepted_frames == 0 && test.owner.outcome_unknown);
    reclaim_metadata(&test);
    CHECK(!aqss_lab_release_child(&test.callbacks, test.children[0]));
}

int main(void)
{
    test_child_retains_metadata_after_parent_returns();
    test_child_acquisition_requires_active_parent_and_open_admission();
    test_invalid_and_duplicate_releases_preserve_other_children();
    test_child_cleanup_remains_available_at_capacity();
    puts("AQSS_CHILD_LAB_PASS: 4 deterministic C cases; physical output unqualified");
    return EXIT_SUCCESS;
}
