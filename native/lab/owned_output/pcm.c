#include "pcm.h"

#include <limits.h>

_Static_assert(CHAR_BIT == 8, "PCM profile requires eight-bit bytes");
_Static_assert(INT16_MIN == -32768 && INT16_MAX == 32767,
               "PCM profile requires signed 16-bit samples");

bool aqss_lab_prepare_pcm(aqss_lab_pcm_block *block, uint64_t work_id,
                          aqss_lab_pcm_format format, uint32_t gain_permille,
                          const uint8_t *source, size_t source_bytes)
{
    if (block == NULL || source == NULL || work_id == 0 ||
        format.sample_rate_hz != AQSS_LAB_PCM_RATE || format.channels != 1 ||
        format.encoding != AQSS_LAB_PCM_S16_LE ||
        gain_permille > AQSS_LAB_PCM_UNITY || source_bytes == 0 ||
        source_bytes % 2 != 0 || source_bytes > 2u * AQSS_LAB_PCM_MAX_FRAMES) {
        return false;
    }
    /* uintptr_t is a required host property of this portable lab build.
     * Subtraction after ordering avoids address-end arithmetic overflow.
     */
    uintptr_t dst = (uintptr_t)block;
    uintptr_t src = (uintptr_t)source;
    if (dst <= src ? src - dst < sizeof(*block) : dst - src < source_bytes) {
        return false;
    }
    aqss_lab_pcm_block candidate = {
        .work_id = work_id, .format = format, .gain_permille = gain_permille,
        .frame_count = source_bytes / 2
    };
    for (size_t i = 0; i < candidate.frame_count; ++i) {
        uint32_t word = (uint32_t)source[2 * i] |
                        ((uint32_t)source[2 * i + 1] << 8);
        int32_t sample = word <= INT16_MAX ? (int32_t)word : (int32_t)word - 65536;
        /* Maximum magnitude 32,768,000 fits int32_t. C11 division truncates
         * toward zero. Attenuation keeps the result representable in int16_t.
         */
        candidate.frames[i] = (int16_t)((sample * (int32_t)gain_permille) / 1000);
    }
    *block = candidate;
    return true;
}
