#include "owner.h"

static void append_event(aqss_lab_owner *owner, aqss_lab_event_kind kind,
                         ptrdiff_t returned_frames)
{
    /* Admission reserves three entries per call; the two hold entries are
     * independent of ordinary capacity. No record is overwritten or evicted.
     */
    owner->events[owner->event_count++] = (aqss_lab_event){
        .kind = kind,
        .work_id = owner->work_id,
        .offset = owner->call_offset,
        .requested_frames = owner->call_frames,
        .returned_frames = returned_frames
    };
}

bool aqss_lab_owner_init(aqss_lab_owner *owner, uint64_t work_id,
                         const int16_t *frames, size_t frame_count,
                         aqss_lab_scripted_write write, void *context)
{
    if (owner == NULL || work_id == 0 || frames == NULL || write == NULL ||
        frame_count == 0 || frame_count > (size_t)PTRDIFF_MAX) {
        return false;
    }
    *owner = (aqss_lab_owner){
        .work_id = work_id,
        .frames = frames,
        .frame_count = frame_count,
        .write = write,
        .context = context,
        .initialized = true,
        .phase = AQSS_LAB_IDLE
    };
    return true;
}

bool aqss_lab_submit(aqss_lab_owner *owner)
{
    if (owner == NULL || !owner->initialized || owner->admission_closed ||
        owner->phase == AQSS_LAB_CALL_ENTERED ||
        owner->phase == AQSS_LAB_CALL_RETURNED ||
        owner->accepted_frames == owner->frame_count) {
        return false;
    }
    if (owner->call_count == AQSS_LAB_MAX_CALLS) {
        owner->trace_exhausted = true;
        aqss_lab_request_hold(owner);
        return false;
    }
    ++owner->call_count; /* Reserve the entire call's trace before dispatch. */
    owner->call_offset = owner->accepted_frames;
    owner->call_frames = owner->frame_count - owner->call_offset;
    owner->phase = AQSS_LAB_CALL_ENTERED;
    owner->outcome_unknown = true;
    append_event(owner, AQSS_LAB_EVENT_CALL_ENTERED, 0);
    owner->returned_frames = owner->write(
        owner->context, owner->frames + owner->call_offset, owner->call_frames);
    owner->phase = AQSS_LAB_CALL_RETURNED;
    append_event(owner, AQSS_LAB_EVENT_CALL_RETURNED, owner->returned_frames);
    return true;
}

bool aqss_lab_record_return(aqss_lab_owner *owner)
{
    if (owner == NULL || !owner->initialized ||
        owner->phase != AQSS_LAB_CALL_RETURNED) {
        return false;
    }
    owner->invalid_return = owner->returned_frames < 0 ||
        (size_t)owner->returned_frames > owner->call_frames;
    if (!owner->invalid_return) {
        owner->accepted_frames += (size_t)owner->returned_frames;
    }
    owner->phase = AQSS_LAB_RETURN_RECORDED;
    append_event(owner, AQSS_LAB_EVENT_RETURN_RECORDED, owner->returned_frames);
    if (owner->invalid_return) {
        aqss_lab_request_hold(owner);
    }
    return true;
}

void aqss_lab_request_hold(aqss_lab_owner *owner)
{
    if (owner != NULL && owner->initialized && !owner->admission_closed) {
        owner->admission_closed = true;
        append_event(owner, AQSS_LAB_EVENT_HOLD_REQUESTED, 0);
    }
}

bool aqss_lab_acknowledge_hold(aqss_lab_owner *owner)
{
    if (owner == NULL || !owner->initialized || !owner->admission_closed ||
        owner->phase == AQSS_LAB_CALL_ENTERED ||
        owner->phase == AQSS_LAB_CALL_RETURNED) {
        return false;
    }
    if (!owner->hold_acknowledged) {
        owner->hold_acknowledged = true;
        append_event(owner, AQSS_LAB_EVENT_HOLD_ACKNOWLEDGED, 0);
    }
    return true;
}
