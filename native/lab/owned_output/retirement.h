#ifndef AQSS_LAB_OWNED_OUTPUT_RETIREMENT_H
#define AQSS_LAB_OWNED_OUTPUT_RETIREMENT_H

#include "callbacks.h"

/* Two metadata reservations for one scripted endpoint/resource. The pool,
 * owners and callback contexts stay alive through all stale handle replays.
 * This bounds registered metadata blocks, not their byte size or OS resources.
 */
#define AQSS_LAB_RETIREMENT_SLOTS 2u

typedef enum {
    AQSS_LAB_SLOT_FREE,
    AQSS_LAB_SLOT_RESERVED,
    AQSS_LAB_SLOT_CURRENT,
    AQSS_LAB_SLOT_RETIRING
} aqss_lab_retirement_state;

typedef struct {
    uint64_t runtime_id;
    aqss_lab_callbacks *callbacks;
    aqss_lab_retirement_state state;
} aqss_lab_retirement_slot;

typedef struct aqss_lab_retirement_pool {
    uint64_t endpoint_id;
    uint64_t resource_id;
    uint64_t last_runtime_id;
    bool initialized;
    aqss_lab_retirement_slot slots[AQSS_LAB_RETIREMENT_SLOTS];
} aqss_lab_retirement_pool;

typedef struct {
    const aqss_lab_retirement_pool *pool;
    size_t slot;
    uint64_t runtime_id;
} aqss_lab_retirement_handle;

bool aqss_lab_retirement_init(aqss_lab_retirement_pool *pool,
                              uint64_t endpoint_id, uint64_t resource_id);
/* Reserve BEFORE allocating a new metadata block or entering its backend.
 * Only one reserved/current incarnation is allowed. Runtime IDs must strictly
 * increase; the high-water mark survives cancellation/reclamation. Never reset
 * a live pool, recycle its external contexts, or submit outside the pool API.
 */
aqss_lab_retirement_handle aqss_lab_reserve_runtime(
    aqss_lab_retirement_pool *pool, uint64_t runtime_id);
bool aqss_lab_bind_runtime(aqss_lab_retirement_pool *pool,
                           aqss_lab_retirement_handle handle,
                           aqss_lab_callbacks *callbacks);
bool aqss_lab_cancel_reservation(aqss_lab_retirement_pool *pool,
                                 aqss_lab_retirement_handle handle);
bool aqss_lab_submit_current(aqss_lab_retirement_pool *pool,
                             aqss_lab_retirement_handle handle);
bool aqss_lab_retire_runtime(aqss_lab_retirement_pool *pool,
                             aqss_lab_retirement_handle handle);
/* Releases a slot only when the existing metadata lifetime gate permits it.
 * Caller may free the returned block. Physical history stays in the live owner;
 * neither a free slot nor a new reservation is successor readiness/authority.
 */
void *aqss_lab_take_retired_metadata(aqss_lab_retirement_pool *pool,
                                    aqss_lab_retirement_handle handle);

#endif
