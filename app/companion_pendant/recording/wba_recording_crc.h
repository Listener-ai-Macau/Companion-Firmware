#ifndef COMPANION_WBA_RECORDING_CRC_H
#define COMPANION_WBA_RECORDING_CRC_H
#include "../storage/companion_crc32.h"
/* Existing finalized-seed API; one shared IEEE implementation. */
static inline uint32_t comp_wba_recording_crc32(uint32_t seed,const uint8_t *data,uint32_t length)
{return companion_crc32(seed,data,length);}
#endif
