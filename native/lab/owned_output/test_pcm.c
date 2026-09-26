#include "pcm.h"
#include "owner.h"

#include <errno.h>
#include <limits.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define CHECK(condition) do { \
    if (!(condition)) { \
        fprintf(stderr, "%s:%d: FAILED: %s\n", __func__, __LINE__, #condition); \
        exit(EXIT_FAILURE); \
    } \
} while (0)

static const aqss_lab_pcm_format format = {
    AQSS_LAB_PCM_RATE, 1, AQSS_LAB_PCM_S16_LE
};

static void test_exact_rounding_and_source_immutability(void)
{
    const uint8_t source[] = {
        0x00, 0x80, 0xff, 0x7f, 0xfd, 0xff, 0x03, 0x00,
        0xff, 0xff, 0x01, 0x00, 0x00, 0x00, 0x34, 0x12
    };
    uint8_t before[sizeof source];
    memcpy(before, source, sizeof source);
    aqss_lab_pcm_block block;
    const int16_t expected[] = {-16384, 16383, -1, 1, 0, 0, 0, 2330};
    CHECK(aqss_lab_prepare_pcm(&block, 71, format, 500, source, sizeof source));
    CHECK(block.work_id == 71 && block.gain_permille == 500);
    CHECK(block.frame_count == 8);
    CHECK(block.format.sample_rate_hz == 48000 && block.format.channels == 1);
    CHECK(memcmp(block.frames, expected, sizeof expected) == 0);
    CHECK(memcmp(source, before, sizeof source) == 0);
}

static void test_entire_sample_and_gain_domain(void)
{
    uint8_t source[2 * AQSS_LAB_PCM_MAX_FRAMES];
    aqss_lab_pcm_block block;
    for (uint32_t gain = 0; gain <= 1000; ++gain) {
        for (int32_t base = INT16_MIN; base <= INT16_MAX; base += 256) {
            for (size_t i = 0; i < 256; ++i) {
                uint16_t bits = (uint16_t)(base + (int32_t)i);
                source[2 * i] = (uint8_t)bits;
                source[2 * i + 1] = (uint8_t)(bits >> 8);
            }
            CHECK(aqss_lab_prepare_pcm(&block, 72, format, gain, source, sizeof source));
            for (size_t i = 0; i < 256; ++i) {
                int32_t sample = base + (int32_t)i;
                /* Unsigned-magnitude oracle avoids the implementation's
                 * signed division; also assert never amplifying/sign-flipping.
                 */
                uint64_t magnitude = (uint64_t)(sample < 0 ? -sample : sample);
                int32_t scaled = (int32_t)(magnitude * gain / 1000);
                int32_t expected = sample < 0 ? -scaled : scaled;
                CHECK(block.frames[i] == expected);
                CHECK(sample < 0 ? block.frames[i] <= 0 && block.frames[i] >= sample :
                                   block.frames[i] >= 0 && block.frames[i] <= sample);
            }
        }
    }
}

static void test_invalid_format_and_gain_leave_destination_intact(void)
{
    const uint8_t source[] = {1, 0};
    aqss_lab_pcm_block block;
    memset(&block, 0xa5, sizeof block);
    uint8_t before[sizeof block];
    memcpy(before, &block, sizeof block);
    const aqss_lab_pcm_format invalid[] = {
        {0, 1, AQSS_LAB_PCM_S16_LE}, {44100, 1, AQSS_LAB_PCM_S16_LE},
        {48000, 0, AQSS_LAB_PCM_S16_LE}, {48000, 2, AQSS_LAB_PCM_S16_LE},
        {48000, 1, (aqss_lab_pcm_encoding)0},
        {48000, 1, (aqss_lab_pcm_encoding)999}
    };
    for (size_t i = 0; i < sizeof invalid / sizeof invalid[0]; ++i) {
        CHECK(!aqss_lab_prepare_pcm(&block, 73, invalid[i], 500, source, sizeof source));
        CHECK(memcmp(before, &block, sizeof block) == 0);
    }
    CHECK(!aqss_lab_prepare_pcm(&block, 73, format, 1001, source, sizeof source));
    CHECK(!aqss_lab_prepare_pcm(&block, 73, format, UINT32_MAX, source, sizeof source));
    CHECK(memcmp(before, &block, sizeof block) == 0);
}

static void test_invalid_buffer_size_identity_and_overlap(void)
{
    const uint8_t source[514] = {0};
    aqss_lab_pcm_block block = {0};
    uint8_t before[sizeof block];
    memcpy(before, &block, sizeof block);
    const size_t bad_sizes[] = {0, 1, 3, 513, 514, SIZE_MAX};
    for (size_t i = 0; i < sizeof bad_sizes / sizeof bad_sizes[0]; ++i) {
        CHECK(!aqss_lab_prepare_pcm(&block, 74, format, 1, source, bad_sizes[i]));
    }
    CHECK(!aqss_lab_prepare_pcm(NULL, 74, format, 1, source, 2));
    CHECK(!aqss_lab_prepare_pcm(&block, 74, format, 1, NULL, 2));
    CHECK(!aqss_lab_prepare_pcm(&block, 0, format, 1, source, 2));
    CHECK(!aqss_lab_prepare_pcm(&block, 74, format, 1, (const uint8_t *)&block, 2));
    CHECK(!aqss_lab_prepare_pcm(&block, 74, format, 1, (const uint8_t *)block.frames, 2));
    CHECK(memcmp(before, &block, sizeof block) == 0);
}

static void test_exact_capacity_and_unaligned_little_endian_input(void)
{
    uint8_t storage[513] = {0};
    for (size_t i = 0; i < 256; ++i) {
        storage[1 + 2 * i] = 0x34;
        storage[2 + 2 * i] = 0x12;
    }
    aqss_lab_pcm_block block;
    CHECK(aqss_lab_prepare_pcm(&block, 75, format, 1000, storage + 1, 512));
    CHECK(block.frame_count == 256);
    for (size_t i = 0; i < 256; ++i) CHECK(block.frames[i] == 0x1234);
}

typedef struct {
    const aqss_lab_pcm_block *block;
    size_t calls;
    size_t accepted;
    int16_t copied[8];
} backend;

static ptrdiff_t copy_script(void *context, const int16_t *frames, size_t count)
{
    backend *b = context;
    CHECK(frames == b->block->frames + b->accepted);
    CHECK(count == b->block->frame_count - b->accepted);
    size_t call = b->calls++;
    if (call == 1) return -EAGAIN;
    size_t accepted = call == 0 ? 3 : count;
    CHECK(b->accepted + accepted <= 8);
    memcpy(b->copied + b->accepted, frames, accepted * sizeof(*frames));
    b->accepted += accepted;
    return (ptrdiff_t)accepted;
}

static void test_gain_context_survives_partial_retry_and_later_preparation(void)
{
    const uint8_t source[] = {0, 128, 255, 127, 253, 255, 3, 0,
                              255, 255, 1, 0, 0, 0, 52, 18};
    aqss_lab_pcm_block old_block, later_block;
    CHECK(aqss_lab_prepare_pcm(&old_block, 76, format, 500, source, sizeof source));
    backend b = {.block = &old_block};
    aqss_lab_owner owner;
    CHECK(aqss_lab_owner_init(&owner, old_block.work_id, old_block.frames,
                              old_block.frame_count, copy_script, &b));
    CHECK(aqss_lab_submit(&owner) && aqss_lab_record_return(&owner));
    CHECK(owner.accepted_frames == 3);
    CHECK(aqss_lab_prepare_pcm(&later_block, 77, format, 0, source, sizeof source));
    CHECK(aqss_lab_submit(&owner) && aqss_lab_record_return(&owner));
    CHECK(owner.accepted_frames == 3);
    CHECK(aqss_lab_submit(&owner) && aqss_lab_record_return(&owner));
    CHECK(b.calls == 3 && b.accepted == 8);
    CHECK(memcmp(b.copied, old_block.frames, sizeof b.copied) == 0);
    CHECK(old_block.gain_permille == 500 && later_block.gain_permille == 0);
    CHECK(owner.work_id == 76 && owner.outcome_unknown);
    aqss_lab_request_hold(&owner);
    CHECK(aqss_lab_acknowledge_hold(&owner));
    CHECK(!aqss_lab_submit(&owner) && b.calls == 3);
}

int main(void)
{
    test_exact_rounding_and_source_immutability();
    test_entire_sample_and_gain_domain();
    test_invalid_format_and_gain_leave_destination_intact();
    test_invalid_buffer_size_identity_and_overlap();
    test_exact_capacity_and_unaligned_little_endian_input();
    test_gain_context_survives_partial_retry_and_later_preparation();
    puts("AQSS_LAB_PCM_TESTS_PASSED 6");
    return 0;
}
