#ifndef COMP_IMU_SCREEN_AXES_H
#define COMP_IMU_SCREEN_AXES_H
#include <stdbool.h>
#include <stdint.h>
/* Zero means unconfigured. Signed codes1..6 are +X,-X,+Y,-Y,+Z,-Z.
 * The remaining axis supplies screen-front; bit6 carries its sign. Bit7
 * marks an explicit mounting profile, not a sensor bias calibration. */
static inline bool comp_imu_screen_axes_valid(uint8_t packed)
{
    if (packed == 0u) return true;
    const uint8_t right = packed & 7u, up = (packed >> 3u) & 7u;
    return (packed & 0x80u) && right >= 1u && right <= 6u &&
        up >= 1u && up <= 6u && (right - 1u) / 2u != (up - 1u) / 2u;
}
static inline uint8_t comp_imu_screen_axes_pack(uint8_t right, uint8_t up, uint8_t front)
{
    if (right < 1u || right > 6u || up < 1u || up > 6u || front < 1u || front > 6u)
        return 0u;
    const uint8_t ra = (uint8_t)((right - 1u) / 2u),
        ua = (uint8_t)((up - 1u) / 2u), fa = (uint8_t)((front - 1u) / 2u);
    if (ra == ua || ra == fa || ua == fa) return 0u;
    return (uint8_t)(0x80u | right | (up << 3u) | (((front - 1u) & 1u) << 6u));
}
#endif
