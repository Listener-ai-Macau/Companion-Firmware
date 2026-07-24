#ifndef COMPANION_HOST_CMSIS_COMPILER_H
#define COMPANION_HOST_CMSIS_COMPILER_H

#define __STATIC_INLINE static inline
#define __INLINE inline
#define __get_PRIMASK() 0u
#define __disable_irq() ((void)0)
#define __set_PRIMASK(value) ((void)(value))

#endif
