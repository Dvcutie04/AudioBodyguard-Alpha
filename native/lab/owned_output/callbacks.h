#ifndef AQSS_LAB_OWNED_OUTPUT_CALLBACKS_H
#define AQSS_LAB_OWNED_OUTPUT_CALLBACKS_H

#include "owner.h"

/* Scripted, single-thread callback family. The delivery context and its owner
 * outlive every ticket and child reference, including rejected replays. Only
 * borrowed metadata can be reclaimed. No native quiescence is established here.
 */
#define AQSS_LAB_MAX_CALLBACKS 8u
#define AQSS_LAB_MAX_CHILD_REFERENCES 8u

typedef enum {
    AQSS_LAB_CALLBACK_UNUSED,
    AQSS_LAB_CALLBACK_QUEUED,
    AQSS_LAB_CALLBACK_ACTIVE,
    AQSS_LAB_CALLBACK_CONSUMED
} aqss_lab_callback_state;

typedef struct aqss_lab_callbacks aqss_lab_callbacks;

/* Value ticket; never a pointer into reclaimable metadata. Not authority. */
typedef struct {
    const aqss_lab_callbacks *context;
    size_t sequence;
} aqss_lab_callback_ticket;

/* One retained metadata reference, with the issuing callback's lineage.
 * Only an active callback can acquire it while owner admission is open.
 */
typedef struct {
    const aqss_lab_callbacks *context;
    size_t sequence;
    size_t parent_sequence;
} aqss_lab_child_reference;

typedef struct {
    size_t parent_sequence;
    bool retained;
} aqss_lab_child_slot;

typedef void (*aqss_lab_callback_body)(void *metadata);

struct aqss_lab_callbacks {
    aqss_lab_owner *owner;
    void *metadata;
    aqss_lab_callback_body body;
    size_t issued;
    size_t queued;
    size_t active;
    bool initialized;
    bool capacity_exhausted;
    aqss_lab_callback_state slots[AQSS_LAB_MAX_CALLBACKS];
    size_t children_issued;
    size_t children_retained;
    bool child_capacity_exhausted;
    aqss_lab_child_slot children[AQSS_LAB_MAX_CHILD_REFERENCES];
};

/* Fresh context only, bound to one live owner and one borrowed metadata block.
 * Metadata may outlive a body only under an explicit retained child reference.
 * Each child must stop using the pointer before releasing its reference.
 * No untracked references or direct frees by bodies/children are permitted.
 * Every scripted delivery must first acquire a ticket through this context.
 */
bool aqss_lab_callbacks_init(aqss_lab_callbacks *callbacks,
                             aqss_lab_owner *owner, void *metadata,
                             aqss_lab_callback_body body);
/* A zero/context-null ticket means acquisition was rejected. Slots never reuse. */
aqss_lab_callback_ticket aqss_lab_queue_callback(aqss_lab_callbacks *callbacks);
/* True means the body ran; no physical-success or settlement meaning.
 * A held queued delivery is consumed for cleanup without accessing metadata.
 */
bool aqss_lab_deliver_callback(aqss_lab_callbacks *callbacks,
                               aqss_lab_callback_ticket ticket);
/* Register before handing metadata to a child. Rejected acquisition returns a
 * zero/context-null value. These slots never reuse; this is not an executor.
 */
aqss_lab_child_reference aqss_lab_retain_child(
    aqss_lab_callbacks *callbacks, aqss_lab_callback_ticket parent);
/* Release after the child's last access, including during closed admission.
 * Invalid/replayed releases return false and consume no other reference.
 * This performs bookkeeping only; it cannot dispatch, enqueue, or reactivate.
 */
bool aqss_lab_release_child(aqss_lab_callbacks *callbacks,
                             aqss_lab_child_reference reference);
/* NULL means still retained or already taken. Caller may free a non-NULL result.
 * Taking metadata never clears owner history/uncertainty or releases the context.
 */
void *aqss_lab_take_callback_metadata(aqss_lab_callbacks *callbacks);

#endif
