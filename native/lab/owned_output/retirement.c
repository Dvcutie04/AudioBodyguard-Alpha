#include "retirement.h"

static aqss_lab_retirement_slot *lookup(aqss_lab_retirement_pool *pool,
                                        aqss_lab_retirement_handle handle)
{
    if (pool == NULL || !pool->initialized || handle.pool != pool ||
        handle.slot >= AQSS_LAB_RETIREMENT_SLOTS || handle.runtime_id == 0) {
        return NULL;
    }
    aqss_lab_retirement_slot *slot = &pool->slots[handle.slot];
    return slot->state != AQSS_LAB_SLOT_FREE &&
        slot->runtime_id == handle.runtime_id ? slot : NULL;
}

bool aqss_lab_retirement_init(aqss_lab_retirement_pool *pool,
                              uint64_t endpoint_id, uint64_t resource_id)
{
    if (pool == NULL || endpoint_id == 0 || resource_id == 0) {
        return false;
    }
    *pool = (aqss_lab_retirement_pool){
        .endpoint_id = endpoint_id, .resource_id = resource_id, .initialized = true
    };
    return true;
}

aqss_lab_retirement_handle aqss_lab_reserve_runtime(
    aqss_lab_retirement_pool *pool, uint64_t runtime_id)
{
    const aqss_lab_retirement_handle rejected = {0};
    if (pool == NULL || !pool->initialized || runtime_id == 0 ||
        runtime_id <= pool->last_runtime_id) {
        return rejected;
    }
    size_t available = AQSS_LAB_RETIREMENT_SLOTS;
    for (size_t i = 0; i < AQSS_LAB_RETIREMENT_SLOTS; ++i) {
        if (pool->slots[i].state == AQSS_LAB_SLOT_CURRENT ||
            pool->slots[i].state == AQSS_LAB_SLOT_RESERVED) {
            return rejected;
        }
        if (pool->slots[i].state == AQSS_LAB_SLOT_FREE) {
            available = i;
        }
    }
    if (available == AQSS_LAB_RETIREMENT_SLOTS) {
        return rejected;
    }
    pool->slots[available] = (aqss_lab_retirement_slot){
        .runtime_id = runtime_id, .state = AQSS_LAB_SLOT_RESERVED
    };
    pool->last_runtime_id = runtime_id;
    return (aqss_lab_retirement_handle){pool, available, runtime_id};
}

bool aqss_lab_bind_runtime(aqss_lab_retirement_pool *pool,
                           aqss_lab_retirement_handle handle,
                           aqss_lab_callbacks *callbacks)
{
    aqss_lab_retirement_slot *slot = lookup(pool, handle);
    if (slot == NULL || slot->state != AQSS_LAB_SLOT_RESERVED ||
        callbacks == NULL || !callbacks->initialized || callbacks->metadata == NULL ||
        callbacks->owner->admission_closed || callbacks->owner->call_count != 0 ||
        callbacks->issued != 0 || callbacks->children_issued != 0) {
        return false;
    }
    slot->callbacks = callbacks;
    slot->state = AQSS_LAB_SLOT_CURRENT;
    return true;
}

bool aqss_lab_cancel_reservation(aqss_lab_retirement_pool *pool,
                                 aqss_lab_retirement_handle handle)
{
    aqss_lab_retirement_slot *slot = lookup(pool, handle);
    if (slot == NULL || slot->state != AQSS_LAB_SLOT_RESERVED) {
        return false;
    }
    *slot = (aqss_lab_retirement_slot){0};
    return true;
}

bool aqss_lab_submit_current(aqss_lab_retirement_pool *pool,
                             aqss_lab_retirement_handle handle)
{
    aqss_lab_retirement_slot *slot = lookup(pool, handle);
    return slot != NULL && slot->state == AQSS_LAB_SLOT_CURRENT &&
        aqss_lab_submit(slot->callbacks->owner);
}

bool aqss_lab_retire_runtime(aqss_lab_retirement_pool *pool,
                             aqss_lab_retirement_handle handle)
{
    aqss_lab_retirement_slot *slot = lookup(pool, handle);
    if (slot == NULL || (slot->state != AQSS_LAB_SLOT_CURRENT &&
                         slot->state != AQSS_LAB_SLOT_RETIRING)) {
        return false;
    }
    aqss_lab_request_hold(slot->callbacks->owner);
    slot->state = AQSS_LAB_SLOT_RETIRING;
    return true;
}

void *aqss_lab_take_retired_metadata(aqss_lab_retirement_pool *pool,
                                    aqss_lab_retirement_handle handle)
{
    aqss_lab_retirement_slot *slot = lookup(pool, handle);
    if (slot == NULL || slot->state != AQSS_LAB_SLOT_RETIRING) {
        return NULL;
    }
    void *metadata = aqss_lab_take_callback_metadata(slot->callbacks);
    if (metadata != NULL) {
        *slot = (aqss_lab_retirement_slot){0};
    }
    return metadata;
}
