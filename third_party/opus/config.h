/* Companion bare-metal fixed-point Opus config (not from autoconf). */
#ifndef CONFIG_H
#define CONFIG_H

#define PACKAGE_VERSION "1.5.2"
#define FIXED_POINT 1
#define OPUS_BUILD 1
#define DISABLE_FLOAT_API 1
#define VAR_ARRAYS 1
#define USE_ALLOCA 1

#define HAVE_STDINT_H 1
#define HAVE_STDLIB_H 1
#define HAVE_STRING_H 1
#define HAVE_STDIO_H 1
#define HAVE_LRINT 1
#define HAVE_LRINTF 1

/* Keep the exact codec configuration from the Aug-03 board-air drops=0
 * baseline.  Enabling Opus' legacy ARMv5E inline macro layer later looked like
 * an optimisation, but on this Cortex-M4/GCC build it increased the measured
 * live frame cost enough to overrun the 20 ms producer while the screen ran. */
/* #undef OPUS_HAVE_RTCD */
/* External ARM assembly objects are not linked in this firmware. */
/* #undef OPUS_ARM_ASM */
/* #undef OPUS_ARM_INLINE_ASM */
/* #undef OPUS_ARM_INLINE_EDSP */
/* #undef OPUS_ARM_INLINE_MEDIA */
/* #undef OPUS_ARM_NEON_INTR */
/* #undef OPUS_ARM_MAY_HAVE_NEON */
/* #undef OPUS_ARM_MAY_HAVE_NEON_INTR */
/* #undef OPUS_ARM_MAY_HAVE_EDSP */
/* #undef OPUS_ARM_PRESUME_NEON */
/* #undef OPUS_ARM_PRESUME_NEON_INTR */
/* #undef OPUS_ARM_PRESUME_EDSP */

/* Keep DRED / Deep PLC / OSCE off for footprint. */
/* #undef ENABLE_DRED */
/* #undef ENABLE_DEEP_PLC */
/* #undef ENABLE_OSCE */
/* #undef ENABLE_LOSSGEN */

#endif /* CONFIG_H */
