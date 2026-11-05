#ifndef COMPANION_GATT_MSVC_COMPAT_H
#define COMPANION_GATT_MSVC_COMPAT_H
#define __CMSIS_COMPILER_H
#define __COMPILER_BARRIER() ((void)0)
#define __NO_RETURN __declspec(noreturn)
#define __DMB() ((void)0)
#define __DSB() ((void)0)
#define __ISB() ((void)0)
#define __NOP() ((void)0)
#define __CLZ(value) 0u
#define __RBIT(value) (value)
#define __STATIC_INLINE static inline
#define __STATIC_FORCEINLINE static __forceinline
#define __INLINE inline
#define __USED
#define __WEAK
#define __PACKED
#define __ALIGNED(x) __declspec(align(x))
#define __RESTRICT restrict

/* Host-only bridge for STM32Cube generated packed declarations. */
#define COMPILER_H__
#define __GNUC__ 1
#define __attribute__(x)
#define __PACKED_STRUCT struct
#define __PACKED_UNION union
#define PACKED(decl) decl
#define PACKED__
#define PACKED_STRUCT struct

#endif
