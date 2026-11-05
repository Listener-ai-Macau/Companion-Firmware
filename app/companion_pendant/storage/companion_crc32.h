#ifndef COMPANION_CRC32_H
#define COMPANION_CRC32_H

#include <stdint.h>
#include <stddef.h>

/* Reflected IEEE CRC-32, with the existing finalized seed convention. Two
 * nibble lookups replace eight bit steps per byte. The 64-byte const table
 * stays in internal Flash; no shared hardware CRC ownership or RAM buffer. */
static inline uint32_t companion_crc32(
    uint32_t seed, const uint8_t *data, size_t length)
{
    static const uint32_t table[16] = {
        UINT32_C(0x00000000), UINT32_C(0x1DB71064), UINT32_C(0x3B6E20C8), UINT32_C(0x26D930AC),
        UINT32_C(0x76DC4190), UINT32_C(0x6B6B51F4), UINT32_C(0x4DB26158), UINT32_C(0x5005713C),
        UINT32_C(0xEDB88320), UINT32_C(0xF00F9344), UINT32_C(0xD6D6A3E8), UINT32_C(0xCB61B38C),
        UINT32_C(0x9B64C2B0), UINT32_C(0x86D3D2D4), UINT32_C(0xA00AE278), UINT32_C(0xBDBDF21C),
    };
    uint32_t crc = seed ^ UINT32_C(0xFFFFFFFF);
    for (size_t i = 0u; i < length; ++i) {
        crc ^= data[i];
        crc = (crc >> 4u) ^ table[crc & 15u];
        crc = (crc >> 4u) ^ table[crc & 15u];
    }
    return crc ^ UINT32_C(0xFFFFFFFF);
}

#endif /* COMPANION_CRC32_H */
