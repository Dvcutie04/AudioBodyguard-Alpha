#ifndef AQSS_LAB_OWNED_OUTPUT_HOLD_H
#define AQSS_LAB_OWNED_OUTPUT_HOLD_H

#include "owner.h"

/* Internal, single-thread lab matching. IDs are trusted nonzero fixture values,
 * never authentication. Zero-initialize a fresh control for one owner cut;
 * do not reuse request IDs within an endpoint/resource/runtime domain or reset
 * live objects.
 */
typedef struct {
    uint64_t endpoint_id;
    uint64_t resource_id;
    uint64_t runtime_id;
    uint64_t request_id;
} aqss_lab_hold_identity;

typedef enum {
    AQSS_LAB_HOLD_PENDING,
    AQSS_LAB_HOLD_ACCOUNTED
} aqss_lab_hold_status;

typedef struct {
    aqss_lab_hold_identity identity;
    uint64_t admission_revision;
    aqss_lab_hold_status status;
} aqss_lab_hold_ack;

typedef struct {
    aqss_lab_owner *owner;
    aqss_lab_hold_identity identity;
    uint64_t admission_revision;
    uint64_t clock_domain;
    uint64_t deadline;
    uint64_t last_tick;
    bool initialized;
    bool time_invalid;
} aqss_lab_hold_control;

/* Fixed, exclusive deadline in one explicitly injected monotonic clock domain.
 * A control and an owner can each be bound once; begin never refreshes a wait.
 * The fixture supplies unique IDs and valid lifetimes; no clock is read here.
 */
bool aqss_lab_begin_hold(aqss_lab_hold_control *control, aqss_lab_owner *owner,
                         aqss_lab_hold_identity identity, uint64_t clock_domain,
                         uint64_t now, uint64_t deadline);
/* Produce only after the owner accounts for its entered call. This may happen
 * after a wait expires; cleanup and acceptance within a deadline are distinct.
 */
bool aqss_lab_produce_hold_ack(aqss_lab_hold_control *control,
                              aqss_lab_hold_ack *ack);
/* Unrelated notifications/mismatches stay false. Expiry or clock rollback is
 * terminal for this control. Matching never refreshes a deadline or dispatches.
 */
bool aqss_lab_match_hold_ack(aqss_lab_hold_control *control,
                            const aqss_lab_hold_ack *ack,
                            uint64_t clock_domain, uint64_t now);

#endif
