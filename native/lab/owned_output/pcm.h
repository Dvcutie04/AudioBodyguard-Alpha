#ifndef AQSS_LAB_OWNED_OUTPUT_PCM_H
#define AQSS_LAB_OWNED_OUTPUT_PCM_H

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

/* Synthetic lab profile, not device negotiation: 48 kHz, mono, S16LE bytes.
 * Prepare before owner initialization. Caller keeps the block unchanged and
 * alive while borrowed by an owner/backend; this public struct does not
 * enforce immutability. No live gain change or audio API is provided.
 */
#define AQSS_LAB_PCM_MAX_FRAMES 256u
#define AQSS_LAB_PCM_RATE 48000u
#define AQSS_LAB_PCM_UNITY 1000u

typedef enum { AQSS_LAB_PCM_S16_LE = 1 } aqss_lab_pcm_encoding;
typedef struct {
    uint32_t sample_rate_hz;
    uint16_t channels;
    aqss_lab_pcm_encoding encoding;
} aqss_lab_pcm_format;

typedef struct {
    uint64_t work_id;
    aqss_lab_pcm_format format;
    uint32_t gain_permille;
    size_t frame_count;
    int16_t frames[AQSS_LAB_PCM_MAX_FRAMES];
} aqss_lab_pcm_block;

/* Exact rule: signed sample * gain in int32_t, divided by 1000 toward zero.
 * Caller supplies valid readable/writable objects. Their storage must not
 * overlap. All validation precedes writes; failure leaves destination intact.
 * This is a preparation function, not safe reinitialization of live work.
 */
bool aqss_lab_prepare_pcm(aqss_lab_pcm_block *block, uint64_t work_id,
                          aqss_lab_pcm_format format, uint32_t gain_permille,
                          const uint8_t *source, size_t source_bytes);

#endif
