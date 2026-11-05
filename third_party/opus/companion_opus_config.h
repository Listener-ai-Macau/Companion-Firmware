/* Minimal config for Companion STM32WB fixed-point Opus encoder. */
#ifndef COMPANION_OPUS_CONFIG_H
#define COMPANION_OPUS_CONFIG_H

#define FIXED_POINT 1
#define OPUS_BUILD 1
#define DISABLE_FLOAT_API 1
#define VAR_ARRAYS 1
/* No runtime CPU detection on bare metal. */
#define OPUS_ARM_ASM 0
#define OPUS_ARM_INLINE_ASM 0
#define OPUS_ARM_NEON_INTR 0
#define OPUS_HAVE_RTCD 0

/* Non-standard malloc: use stack VLA / static only where possible. */
#ifndef USE_ALLOCA
/* Prefer C99 VLAs on arm-none-eabi. */
#endif

#endif /* COMPANION_OPUS_CONFIG_H */
