#ifndef AQSS_LAB_OWNED_OUTPUT_CALLBACKS_H
#define AQSS_LAB_OWNED_OUTPUT_CALLBACKS_H

#include "owner.h"

/* Scripted, single-thread callback family. The delivery context and its owner
 * outlive every ticket, including rejected replays. Only the borrowed metadata
 * can be taken for reclamation. No native quiescence or child references exist.
 */
#define AQSS_LAB_MAX_CALLBACKS 8u

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
};

/* Fresh context only, bound to one live owner and one borrowed metadata block.
 * Callback bodies must not retain/escape metadata or free it themselves.
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
/* NULL means still retained or already taken. Caller may free a non-NULL result.
 * Taking metadata never clears owner history/uncertainty or releases the context.
 */
void *aqss_lab_take_callback_metadata(aqss_lab_callbacks *callbacks);

#endif
