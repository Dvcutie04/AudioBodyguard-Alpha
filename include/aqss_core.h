/**
 * AQSS-36-OMEGA Core Engine C-ABI Header
 * Native FFI Interface for iOS/macOS Swift Bridge
 */

#ifndef AQSS_CORE_H
#define AQSS_CORE_H

#include <stdint.h>
#include <stdbool.h>

#ifdef __cplusplus
extern "C" {
#endif

typedef struct {
    double ambient_db;
    double expectation_z;
    double consensus_trust;
} aqss_telemetry_frame_t;

typedef struct {
    bool is_threat_detected;
    double threat_probability;
    double recommended_attenuation_db;
} aqss_threat_result_t;

/**
 * Evaluates telemetry frame against threat inference engine.
 */
int32_t aqss_evaluate_frame(
    const aqss_telemetry_frame_t* frame,
    aqss_threat_result_t* out_result
);

#ifdef __cplusplus
}
#endif

#endif /* AQSS_CORE_H */
