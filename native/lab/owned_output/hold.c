#include "hold.h"

bool aqss_lab_begin_hold(aqss_lab_hold_control *control, aqss_lab_owner *owner,
                         aqss_lab_hold_identity identity, uint64_t clock_domain,
                         uint64_t now, uint64_t deadline)
{
    if (control == NULL || control->initialized || owner == NULL ||
        !owner->initialized || owner->hold_control_bound ||
        identity.endpoint_id == 0 || identity.resource_id == 0 ||
        identity.runtime_id == 0 || identity.request_id == 0 ||
        clock_domain == 0 || now >= deadline) {
        return false;
    }
    aqss_lab_request_hold(owner);
    owner->hold_control_bound = true;
    *control = (aqss_lab_hold_control){
        .owner = owner, .identity = identity,
        .admission_revision = owner->admission_revision,
        .clock_domain = clock_domain, .deadline = deadline, .last_tick = now,
        .initialized = true
    };
    return true;
}

bool aqss_lab_produce_hold_ack(aqss_lab_hold_control *control,
                              aqss_lab_hold_ack *ack)
{
    if (control == NULL || !control->initialized || ack == NULL ||
        control->owner->admission_revision != control->admission_revision ||
        !aqss_lab_acknowledge_hold(control->owner)) {
        return false;
    }
    *ack = (aqss_lab_hold_ack){control->identity, control->admission_revision,
                              AQSS_LAB_HOLD_ACCOUNTED};
    return true;
}

bool aqss_lab_match_hold_ack(aqss_lab_hold_control *control,
                            const aqss_lab_hold_ack *ack,
                            uint64_t clock_domain, uint64_t now)
{
    if (control == NULL || !control->initialized || control->time_invalid ||
        clock_domain != control->clock_domain) {
        return false;
    }
    if (now < control->last_tick || now >= control->deadline) {
        control->time_invalid = true;
        return false;
    }
    control->last_tick = now;
    return ack != NULL && ack->status == AQSS_LAB_HOLD_ACCOUNTED &&
        control->owner->hold_acknowledged && control->owner->admission_closed &&
        control->owner->admission_revision == control->admission_revision &&
        ack->admission_revision == control->admission_revision &&
        ack->identity.endpoint_id == control->identity.endpoint_id &&
        ack->identity.resource_id == control->identity.resource_id &&
        ack->identity.runtime_id == control->identity.runtime_id &&
        ack->identity.request_id == control->identity.request_id;
}
