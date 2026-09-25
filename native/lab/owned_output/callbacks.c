#include "callbacks.h"

bool aqss_lab_callbacks_init(aqss_lab_callbacks *callbacks,
                             aqss_lab_owner *owner, void *metadata,
                             aqss_lab_callback_body body)
{
    if (callbacks == NULL || owner == NULL || !owner->initialized ||
        owner->admission_closed || metadata == NULL || body == NULL) {
        return false;
    }
    *callbacks = (aqss_lab_callbacks){
        .owner = owner, .metadata = metadata, .body = body, .initialized = true
    };
    return true;
}

aqss_lab_callback_ticket aqss_lab_queue_callback(aqss_lab_callbacks *callbacks)
{
    const aqss_lab_callback_ticket rejected = {0};
    if (callbacks == NULL || !callbacks->initialized ||
        callbacks->owner->admission_closed || callbacks->metadata == NULL) {
        return rejected;
    }
    if (callbacks->issued == AQSS_LAB_MAX_CALLBACKS) {
        callbacks->capacity_exhausted = true;
        aqss_lab_request_hold(callbacks->owner);
        return rejected;
    }
    callbacks->slots[callbacks->issued] = AQSS_LAB_CALLBACK_QUEUED;
    ++callbacks->issued;
    ++callbacks->queued;
    return (aqss_lab_callback_ticket){callbacks, callbacks->issued};
}

bool aqss_lab_deliver_callback(aqss_lab_callbacks *callbacks,
                               aqss_lab_callback_ticket ticket)
{
    /* Validate the stable context/ticket before touching borrowed metadata. */
    if (callbacks == NULL || !callbacks->initialized ||
        ticket.context != callbacks || ticket.sequence == 0 ||
        ticket.sequence > callbacks->issued ||
        callbacks->slots[ticket.sequence - 1] != AQSS_LAB_CALLBACK_QUEUED) {
        return false;
    }
    size_t slot = ticket.sequence - 1;
    --callbacks->queued;
    if (callbacks->owner->admission_closed) {
        callbacks->slots[slot] = AQSS_LAB_CALLBACK_CONSUMED;
        return false;
    }
    callbacks->slots[slot] = AQSS_LAB_CALLBACK_ACTIVE;
    ++callbacks->active;
    callbacks->body(callbacks->metadata);
    --callbacks->active;
    callbacks->slots[slot] = AQSS_LAB_CALLBACK_CONSUMED;
    return true;
}

aqss_lab_child_reference aqss_lab_retain_child(
    aqss_lab_callbacks *callbacks, aqss_lab_callback_ticket parent)
{
    const aqss_lab_child_reference rejected = {0};
    if (callbacks == NULL || !callbacks->initialized ||
        callbacks->owner->admission_closed || callbacks->metadata == NULL ||
        parent.context != callbacks || parent.sequence == 0 ||
        parent.sequence > callbacks->issued ||
        callbacks->slots[parent.sequence - 1] != AQSS_LAB_CALLBACK_ACTIVE) {
        return rejected;
    }
    if (callbacks->children_issued == AQSS_LAB_MAX_CHILD_REFERENCES) {
        callbacks->child_capacity_exhausted = true;
        aqss_lab_request_hold(callbacks->owner);
        return rejected;
    }
    callbacks->children[callbacks->children_issued] = (aqss_lab_child_slot){
        .parent_sequence = parent.sequence, .retained = true
    };
    ++callbacks->children_issued;
    ++callbacks->children_retained;
    return (aqss_lab_child_reference){
        callbacks, callbacks->children_issued, parent.sequence
    };
}

bool aqss_lab_release_child(aqss_lab_callbacks *callbacks,
                             aqss_lab_child_reference reference)
{
    /* Use only the stable registry, including after the metadata was freed. */
    if (callbacks == NULL || !callbacks->initialized ||
        reference.context != callbacks || reference.sequence == 0 ||
        reference.sequence > callbacks->children_issued) {
        return false;
    }
    aqss_lab_child_slot *child = &callbacks->children[reference.sequence - 1];
    if (!child->retained || child->parent_sequence != reference.parent_sequence) {
        return false;
    }
    child->retained = false;
    --callbacks->children_retained;
    return true;
}

void *aqss_lab_take_callback_metadata(aqss_lab_callbacks *callbacks)
{
    if (callbacks == NULL || !callbacks->initialized ||
        !callbacks->owner->hold_acknowledged || callbacks->queued != 0 ||
        callbacks->active != 0 || callbacks->children_retained != 0) {
        return NULL;
    }
    void *metadata = callbacks->metadata;
    callbacks->metadata = NULL;
    return metadata;
}
