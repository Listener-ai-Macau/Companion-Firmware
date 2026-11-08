/* Real newly created365: six used sectors at an absolute12KiB skew.
 * Rounding to the second boundary makes five4K plus one32K command,
 * replacing just ONE needed4K erase with a slower full block. */
#define COMP_PREFIX_TEST_BASE (65536+12288)
#include "test_companion_short_unaligned_tail.c"
