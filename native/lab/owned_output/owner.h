#ifndef AQSS_LAB_OWNED_OUTPUT_OWNER_H
#define AQSS_LAB_OWNED_OUTPUT_OWNER_H

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

/* Test-only C11 owner: one borrowed mono S16 block, one hold, one thread.
 * No native API, physical observation, durable history, or authority exists.
 * Keep the owner, frames, and scripted backend context alive for the whole test.
 * Fields are exposed for stack allocation, not a security/isolation boundary.
 */
#define AQSS_LAB_MAX_CALLS 8u
#define AQSS_LAB_MAX_EVENTS (3u * AQSS_LAB_MAX_CALLS + 2u)

typedef enum {
    AQSS_LAB_IDLE,
    AQSS_LAB_CALL_ENTERED,
    AQSS_LAB_CALL_RETURNED,
    AQSS_LAB_RETURN_RECORDED
} aqss_lab_phase;

typedef enum {
    AQSS_LAB_EVENT_CALL_ENTERED,
    AQSS_LAB_EVENT_CALL_RETURNED,
    AQSS_LAB_EVENT_RETURN_RECORDED,
    AQSS_LAB_EVENT_HOLD_REQUESTED,
    AQSS_LAB_EVENT_HOLD_ACKNOWLEDGED
} aqss_lab_event_kind;

typedef struct {
    aqss_lab_event_kind kind;
    uint64_t work_id;
    size_t offset;
    size_t requested_frames;
    /* Meaningful only for CALL_RETURNED and RETURN_RECORDED. */
    ptrdiff_t returned_frames;
} aqss_lab_event;

/* Returns the accepted prefix length. Other results retain uncertainty and
 * close admission; OS-specific error/EAGAIN handling is a later increment.
 */
typedef ptrdiff_t (*aqss_lab_scripted_write)(
    void *context, const int16_t *frames, size_t frame_count);

typedef struct {
    uint64_t work_id;
    const int16_t *frames;
    uint64_t admission_revision;
    size_t frame_count;
    aqss_lab_scripted_write write;
    void *context;
    bool initialized;
    bool admission_closed;
    bool hold_acknowledged;
    bool hold_control_bound;
    bool outcome_unknown;
    bool invalid_return;
    bool trace_exhausted;
    aqss_lab_phase phase;
    size_t accepted_frames;
    size_t call_count;
    size_t call_offset;
    size_t call_frames;
    ptrdiff_t returned_frames;
    size_t event_count;
    aqss_lab_event events[AQSS_LAB_MAX_EVENTS];
} aqss_lab_owner;

/* Initialize fresh storage only; never reset a live owner to discard history. */
bool aqss_lab_owner_init(aqss_lab_owner *owner, uint64_t work_id,
                         const int16_t *frames, size_t frame_count,
                         aqss_lab_scripted_write write, void *context);

/* True means the scripted backend was called, not that frames applied.
 * A returned result must be recorded explicitly before any subsequent call.
 */
bool aqss_lab_submit(aqss_lab_owner *owner);
bool aqss_lab_record_return(aqss_lab_owner *owner);
void aqss_lab_request_hold(aqss_lab_owner *owner);
/* An owner cut only: never physical silence, NOT_APPLIED, or readiness. */
bool aqss_lab_acknowledge_hold(aqss_lab_owner *owner);

#endif
