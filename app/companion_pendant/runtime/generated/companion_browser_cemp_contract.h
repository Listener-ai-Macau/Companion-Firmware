#ifndef COMPANION_BROWSER_CEMP_CONTRACT_H
#define COMPANION_BROWSER_CEMP_CONTRACT_H

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
#include "emote_player.h"

/* Generated from the browser-authored CEMP. Do not edit. */
#define COMPANION_BROWSER_CEMP_PACK_NAME "comp_req_638_browser_epaper_external_nor"
#define COMPANION_BROWSER_CEMP_PACK_REVISION 638u
#define COMPANION_BROWSER_CEMP_CLIP_COUNT 1294u
#define COMPANION_BROWSER_CEMP_FRAME_COUNT 2084u
#define COMPANION_BROWSER_CEMP_STRING_BYTES 17594u
#define COMPANION_BROWSER_CEMP_TOTAL_BYTES 1436691u
#define COMPANION_BROWSER_CEMP_CANONICAL_FRAME_CLIP_COUNT 1073u
#define COMPANION_BROWSER_CEMP_STATE_MAP_COUNT 2581u
#define COMPANION_BROWSER_CEMP_FUNCTION_CLIP_TIMING_COUNT 3u
#define COMPANION_BROWSER_LIFE_FAMILY_MASK 0x0000028Fu
#define COMPANION_BROWSER_LIFE_EPISODE_LIMIT 32u
#define COMPANION_BROWSER_PAGE_SHA256 "AA5235193309CAA9B42F467DA1CE2D75BF96EB2197F26410D22356A45ABC6857"
#define COMPANION_BROWSER_CEMP_SHA256 "9C1761C134A7FE75703A3197140D239BC71FED5AA83EC5B5DC887921A02254F7"

static const uint8_t companion_browser_cemp_strings[
    COMPANION_BROWSER_CEMP_STRING_BYTES] = {
  0x63u, 0x6Fu, 0x6Du, 0x70u, 0x5Fu, 0x72u, 0x65u, 0x71u, 0x5Fu, 0x36u, 0x33u, 0x38u, 0x5Fu, 0x62u, 0x72u, 0x6Fu,
  0x77u, 0x73u, 0x65u, 0x72u, 0x5Fu, 0x65u, 0x70u, 0x61u, 0x70u, 0x65u, 0x72u, 0x5Fu, 0x65u, 0x78u, 0x74u, 0x65u,
  0x72u, 0x6Eu, 0x61u, 0x6Cu, 0x5Fu, 0x6Eu, 0x6Fu, 0x72u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u,
  0x30u, 0x30u, 0x30u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x30u, 0x30u, 0x31u, 0x00u, 0x66u,
  0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x30u, 0x30u, 0x32u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu,
  0x30u, 0x30u, 0x30u, 0x33u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x30u, 0x30u, 0x34u, 0x00u,
  0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x30u, 0x30u, 0x35u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u,
  0x5Fu, 0x30u, 0x30u, 0x30u, 0x36u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x30u, 0x30u, 0x37u,
  0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x30u, 0x30u, 0x38u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du,
  0x65u, 0x5Fu, 0x30u, 0x30u, 0x30u, 0x39u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x30u, 0x31u,
  0x30u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x30u, 0x31u, 0x31u, 0x00u, 0x66u, 0x72u, 0x61u,
  0x6Du, 0x65u, 0x5Fu, 0x30u, 0x30u, 0x31u, 0x32u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x30u,
  0x31u, 0x33u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x30u, 0x31u, 0x34u, 0x00u, 0x66u, 0x72u,
  0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x30u, 0x31u, 0x35u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u,
  0x30u, 0x31u, 0x36u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x30u, 0x31u, 0x37u, 0x00u, 0x66u,
  0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x30u, 0x31u, 0x38u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu,
  0x30u, 0x30u, 0x31u, 0x39u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x30u, 0x32u, 0x30u, 0x00u,
  0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x30u, 0x32u, 0x31u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u,
  0x5Fu, 0x30u, 0x30u, 0x32u, 0x32u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x30u, 0x32u, 0x33u,
  0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x30u, 0x32u, 0x34u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du,
  0x65u, 0x5Fu, 0x30u, 0x30u, 0x32u, 0x35u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x30u, 0x32u,
  0x36u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x30u, 0x32u, 0x37u, 0x00u, 0x66u, 0x72u, 0x61u,
  0x6Du, 0x65u, 0x5Fu, 0x30u, 0x30u, 0x32u, 0x38u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x30u,
  0x32u, 0x39u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x30u, 0x33u, 0x30u, 0x00u, 0x66u, 0x72u,
  0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x30u, 0x33u, 0x31u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u,
  0x30u, 0x33u, 0x32u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x30u, 0x33u, 0x33u, 0x00u, 0x66u,
  0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x30u, 0x33u, 0x34u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu,
  0x30u, 0x30u, 0x33u, 0x35u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x30u, 0x33u, 0x36u, 0x00u,
  0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x30u, 0x33u, 0x37u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u,
  0x5Fu, 0x30u, 0x30u, 0x33u, 0x38u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x30u, 0x33u, 0x39u,
  0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x30u, 0x34u, 0x30u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du,
  0x65u, 0x5Fu, 0x30u, 0x30u, 0x34u, 0x31u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x30u, 0x34u,
  0x32u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x30u, 0x34u, 0x33u, 0x00u, 0x66u, 0x72u, 0x61u,
  0x6Du, 0x65u, 0x5Fu, 0x30u, 0x30u, 0x34u, 0x34u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x30u,
  0x34u, 0x35u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x30u, 0x34u, 0x36u, 0x00u, 0x66u, 0x72u,
  0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x30u, 0x34u, 0x37u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u,
  0x30u, 0x34u, 0x38u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x30u, 0x34u, 0x39u, 0x00u, 0x66u,
  0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x30u, 0x35u, 0x30u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu,
  0x30u, 0x30u, 0x35u, 0x31u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x30u, 0x35u, 0x32u, 0x00u,
  0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x30u, 0x35u, 0x33u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u,
  0x5Fu, 0x30u, 0x30u, 0x35u, 0x34u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x30u, 0x35u, 0x35u,
  0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x30u, 0x35u, 0x36u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du,
  0x65u, 0x5Fu, 0x30u, 0x30u, 0x35u, 0x37u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x30u, 0x35u,
  0x38u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x30u, 0x35u, 0x39u, 0x00u, 0x66u, 0x72u, 0x61u,
  0x6Du, 0x65u, 0x5Fu, 0x30u, 0x30u, 0x36u, 0x30u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x30u,
  0x36u, 0x31u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x30u, 0x36u, 0x32u, 0x00u, 0x66u, 0x72u,
  0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x30u, 0x36u, 0x33u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u,
  0x30u, 0x36u, 0x34u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x30u, 0x36u, 0x35u, 0x00u, 0x66u,
  0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x30u, 0x36u, 0x36u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu,
  0x30u, 0x30u, 0x36u, 0x37u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x30u, 0x36u, 0x38u, 0x00u,
  0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x30u, 0x36u, 0x39u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u,
  0x5Fu, 0x30u, 0x30u, 0x37u, 0x30u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x30u, 0x37u, 0x31u,
  0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x30u, 0x37u, 0x32u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du,
  0x65u, 0x5Fu, 0x30u, 0x30u, 0x37u, 0x33u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x30u, 0x37u,
  0x34u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x30u, 0x37u, 0x35u, 0x00u, 0x66u, 0x72u, 0x61u,
  0x6Du, 0x65u, 0x5Fu, 0x30u, 0x30u, 0x37u, 0x36u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x30u,
  0x37u, 0x37u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x30u, 0x37u, 0x38u, 0x00u, 0x66u, 0x72u,
  0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x30u, 0x37u, 0x39u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u,
  0x30u, 0x38u, 0x30u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x30u, 0x38u, 0x31u, 0x00u, 0x66u,
  0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x30u, 0x38u, 0x32u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu,
  0x30u, 0x30u, 0x38u, 0x33u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x30u, 0x38u, 0x34u, 0x00u,
  0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x30u, 0x38u, 0x35u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u,
  0x5Fu, 0x30u, 0x30u, 0x38u, 0x36u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x30u, 0x38u, 0x37u,
  0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x30u, 0x38u, 0x38u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du,
  0x65u, 0x5Fu, 0x30u, 0x30u, 0x38u, 0x39u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x30u, 0x39u,
  0x30u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x30u, 0x39u, 0x31u, 0x00u, 0x66u, 0x72u, 0x61u,
  0x6Du, 0x65u, 0x5Fu, 0x30u, 0x30u, 0x39u, 0x32u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x30u,
  0x39u, 0x33u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x30u, 0x39u, 0x34u, 0x00u, 0x66u, 0x72u,
  0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x30u, 0x39u, 0x35u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u,
  0x30u, 0x39u, 0x36u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x30u, 0x39u, 0x37u, 0x00u, 0x66u,
  0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x30u, 0x39u, 0x38u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu,
  0x30u, 0x30u, 0x39u, 0x39u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x31u, 0x30u, 0x30u, 0x00u,
  0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x31u, 0x30u, 0x31u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u,
  0x5Fu, 0x30u, 0x31u, 0x30u, 0x32u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x31u, 0x30u, 0x33u,
  0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x31u, 0x30u, 0x34u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du,
  0x65u, 0x5Fu, 0x30u, 0x31u, 0x30u, 0x35u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x31u, 0x30u,
  0x36u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x31u, 0x30u, 0x37u, 0x00u, 0x66u, 0x72u, 0x61u,
  0x6Du, 0x65u, 0x5Fu, 0x30u, 0x31u, 0x30u, 0x38u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x31u,
  0x30u, 0x39u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x31u, 0x31u, 0x30u, 0x00u, 0x66u, 0x72u,
  0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x31u, 0x31u, 0x31u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u,
  0x31u, 0x31u, 0x32u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x31u, 0x31u, 0x33u, 0x00u, 0x66u,
  0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x31u, 0x31u, 0x34u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu,
  0x30u, 0x31u, 0x31u, 0x35u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x31u, 0x31u, 0x36u, 0x00u,
  0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x31u, 0x31u, 0x37u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u,
  0x5Fu, 0x30u, 0x31u, 0x31u, 0x38u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x31u, 0x31u, 0x39u,
  0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x31u, 0x32u, 0x30u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du,
  0x65u, 0x5Fu, 0x30u, 0x31u, 0x32u, 0x31u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x31u, 0x32u,
  0x32u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x31u, 0x32u, 0x33u, 0x00u, 0x66u, 0x72u, 0x61u,
  0x6Du, 0x65u, 0x5Fu, 0x30u, 0x31u, 0x32u, 0x34u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x31u,
  0x32u, 0x35u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x31u, 0x32u, 0x36u, 0x00u, 0x66u, 0x72u,
  0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x31u, 0x32u, 0x37u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u,
  0x31u, 0x32u, 0x38u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x31u, 0x32u, 0x39u, 0x00u, 0x66u,
  0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x31u, 0x33u, 0x30u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu,
  0x30u, 0x31u, 0x33u, 0x31u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x31u, 0x33u, 0x32u, 0x00u,
  0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x31u, 0x33u, 0x33u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u,
  0x5Fu, 0x30u, 0x31u, 0x33u, 0x34u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x31u, 0x33u, 0x35u,
  0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x31u, 0x33u, 0x36u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du,
  0x65u, 0x5Fu, 0x30u, 0x31u, 0x33u, 0x37u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x31u, 0x33u,
  0x38u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x31u, 0x33u, 0x39u, 0x00u, 0x66u, 0x72u, 0x61u,
  0x6Du, 0x65u, 0x5Fu, 0x30u, 0x31u, 0x34u, 0x30u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x31u,
  0x34u, 0x31u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x31u, 0x34u, 0x32u, 0x00u, 0x66u, 0x72u,
  0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x31u, 0x34u, 0x33u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u,
  0x31u, 0x34u, 0x34u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x31u, 0x34u, 0x35u, 0x00u, 0x66u,
  0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x31u, 0x34u, 0x36u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu,
  0x30u, 0x31u, 0x34u, 0x37u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x31u, 0x34u, 0x38u, 0x00u,
  0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x31u, 0x34u, 0x39u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u,
  0x5Fu, 0x30u, 0x31u, 0x35u, 0x30u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x31u, 0x35u, 0x31u,
  0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x31u, 0x35u, 0x32u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du,
  0x65u, 0x5Fu, 0x30u, 0x31u, 0x35u, 0x33u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x31u, 0x35u,
  0x34u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x31u, 0x35u, 0x35u, 0x00u, 0x66u, 0x72u, 0x61u,
  0x6Du, 0x65u, 0x5Fu, 0x30u, 0x31u, 0x35u, 0x36u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x31u,
  0x35u, 0x37u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x31u, 0x35u, 0x38u, 0x00u, 0x66u, 0x72u,
  0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x31u, 0x35u, 0x39u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u,
  0x31u, 0x36u, 0x30u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x31u, 0x36u, 0x31u, 0x00u, 0x66u,
  0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x31u, 0x36u, 0x32u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu,
  0x30u, 0x31u, 0x36u, 0x33u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x31u, 0x36u, 0x34u, 0x00u,
  0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x31u, 0x36u, 0x35u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u,
  0x5Fu, 0x30u, 0x31u, 0x36u, 0x36u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x31u, 0x36u, 0x37u,
  0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x31u, 0x36u, 0x38u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du,
  0x65u, 0x5Fu, 0x30u, 0x31u, 0x36u, 0x39u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x31u, 0x37u,
  0x30u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x31u, 0x37u, 0x31u, 0x00u, 0x66u, 0x72u, 0x61u,
  0x6Du, 0x65u, 0x5Fu, 0x30u, 0x31u, 0x37u, 0x32u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x31u,
  0x37u, 0x33u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x31u, 0x37u, 0x34u, 0x00u, 0x66u, 0x72u,
  0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x31u, 0x37u, 0x35u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u,
  0x31u, 0x37u, 0x36u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x31u, 0x37u, 0x37u, 0x00u, 0x66u,
  0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x31u, 0x37u, 0x38u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu,
  0x30u, 0x31u, 0x37u, 0x39u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x31u, 0x38u, 0x30u, 0x00u,
  0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x31u, 0x38u, 0x31u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u,
  0x5Fu, 0x30u, 0x31u, 0x38u, 0x32u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x31u, 0x38u, 0x33u,
  0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x31u, 0x38u, 0x34u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du,
  0x65u, 0x5Fu, 0x30u, 0x31u, 0x38u, 0x35u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x31u, 0x38u,
  0x36u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x31u, 0x38u, 0x37u, 0x00u, 0x66u, 0x72u, 0x61u,
  0x6Du, 0x65u, 0x5Fu, 0x30u, 0x31u, 0x38u, 0x38u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x31u,
  0x38u, 0x39u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x31u, 0x39u, 0x30u, 0x00u, 0x66u, 0x72u,
  0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x31u, 0x39u, 0x31u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u,
  0x31u, 0x39u, 0x32u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x31u, 0x39u, 0x33u, 0x00u, 0x66u,
  0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x31u, 0x39u, 0x34u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu,
  0x30u, 0x31u, 0x39u, 0x35u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x31u, 0x39u, 0x36u, 0x00u,
  0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x31u, 0x39u, 0x37u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u,
  0x5Fu, 0x30u, 0x31u, 0x39u, 0x38u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x31u, 0x39u, 0x39u,
  0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x32u, 0x30u, 0x30u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du,
  0x65u, 0x5Fu, 0x30u, 0x32u, 0x30u, 0x31u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x32u, 0x30u,
  0x32u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x32u, 0x30u, 0x33u, 0x00u, 0x66u, 0x72u, 0x61u,
  0x6Du, 0x65u, 0x5Fu, 0x30u, 0x32u, 0x30u, 0x34u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x32u,
  0x30u, 0x35u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x32u, 0x30u, 0x36u, 0x00u, 0x66u, 0x72u,
  0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x32u, 0x30u, 0x37u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u,
  0x32u, 0x30u, 0x38u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x32u, 0x30u, 0x39u, 0x00u, 0x66u,
  0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x32u, 0x31u, 0x30u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu,
  0x30u, 0x32u, 0x31u, 0x31u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x32u, 0x31u, 0x32u, 0x00u,
  0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x32u, 0x31u, 0x33u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u,
  0x5Fu, 0x30u, 0x32u, 0x31u, 0x34u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x32u, 0x31u, 0x35u,
  0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x32u, 0x31u, 0x36u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du,
  0x65u, 0x5Fu, 0x30u, 0x32u, 0x31u, 0x37u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x32u, 0x31u,
  0x38u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x32u, 0x31u, 0x39u, 0x00u, 0x66u, 0x72u, 0x61u,
  0x6Du, 0x65u, 0x5Fu, 0x30u, 0x32u, 0x32u, 0x30u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x32u,
  0x32u, 0x31u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x32u, 0x32u, 0x32u, 0x00u, 0x66u, 0x72u,
  0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x32u, 0x32u, 0x33u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u,
  0x32u, 0x32u, 0x34u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x32u, 0x32u, 0x35u, 0x00u, 0x66u,
  0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x32u, 0x32u, 0x36u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu,
  0x30u, 0x32u, 0x32u, 0x37u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x32u, 0x32u, 0x38u, 0x00u,
  0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x32u, 0x32u, 0x39u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u,
  0x5Fu, 0x30u, 0x32u, 0x33u, 0x30u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x32u, 0x33u, 0x31u,
  0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x32u, 0x33u, 0x32u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du,
  0x65u, 0x5Fu, 0x30u, 0x32u, 0x33u, 0x33u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x32u, 0x33u,
  0x34u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x32u, 0x33u, 0x35u, 0x00u, 0x66u, 0x72u, 0x61u,
  0x6Du, 0x65u, 0x5Fu, 0x30u, 0x32u, 0x33u, 0x36u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x32u,
  0x33u, 0x37u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x32u, 0x33u, 0x38u, 0x00u, 0x66u, 0x72u,
  0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x32u, 0x33u, 0x39u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u,
  0x32u, 0x34u, 0x30u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x32u, 0x34u, 0x31u, 0x00u, 0x66u,
  0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x32u, 0x34u, 0x32u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu,
  0x30u, 0x32u, 0x34u, 0x33u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x32u, 0x34u, 0x34u, 0x00u,
  0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x32u, 0x34u, 0x35u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u,
  0x5Fu, 0x30u, 0x32u, 0x34u, 0x36u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x32u, 0x34u, 0x37u,
  0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x32u, 0x34u, 0x38u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du,
  0x65u, 0x5Fu, 0x30u, 0x32u, 0x34u, 0x39u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x32u, 0x35u,
  0x30u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x32u, 0x35u, 0x31u, 0x00u, 0x66u, 0x72u, 0x61u,
  0x6Du, 0x65u, 0x5Fu, 0x30u, 0x32u, 0x35u, 0x32u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x32u,
  0x35u, 0x33u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x32u, 0x35u, 0x34u, 0x00u, 0x66u, 0x72u,
  0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x32u, 0x35u, 0x35u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u,
  0x32u, 0x35u, 0x36u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x32u, 0x35u, 0x37u, 0x00u, 0x66u,
  0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x32u, 0x35u, 0x38u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu,
  0x30u, 0x32u, 0x35u, 0x39u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x32u, 0x36u, 0x30u, 0x00u,
  0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x32u, 0x36u, 0x31u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u,
  0x5Fu, 0x30u, 0x32u, 0x36u, 0x32u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x32u, 0x36u, 0x33u,
  0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x32u, 0x36u, 0x34u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du,
  0x65u, 0x5Fu, 0x30u, 0x32u, 0x36u, 0x35u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x32u, 0x36u,
  0x36u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x32u, 0x36u, 0x37u, 0x00u, 0x66u, 0x72u, 0x61u,
  0x6Du, 0x65u, 0x5Fu, 0x30u, 0x32u, 0x36u, 0x38u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x32u,
  0x36u, 0x39u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x32u, 0x37u, 0x30u, 0x00u, 0x66u, 0x72u,
  0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x32u, 0x37u, 0x31u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u,
  0x32u, 0x37u, 0x32u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x32u, 0x37u, 0x33u, 0x00u, 0x66u,
  0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x32u, 0x37u, 0x34u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu,
  0x30u, 0x32u, 0x37u, 0x35u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x32u, 0x37u, 0x36u, 0x00u,
  0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x32u, 0x37u, 0x37u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u,
  0x5Fu, 0x30u, 0x32u, 0x37u, 0x38u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x32u, 0x37u, 0x39u,
  0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x32u, 0x38u, 0x30u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du,
  0x65u, 0x5Fu, 0x30u, 0x32u, 0x38u, 0x31u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x32u, 0x38u,
  0x32u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x32u, 0x38u, 0x33u, 0x00u, 0x66u, 0x72u, 0x61u,
  0x6Du, 0x65u, 0x5Fu, 0x30u, 0x32u, 0x38u, 0x34u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x32u,
  0x38u, 0x35u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x32u, 0x38u, 0x36u, 0x00u, 0x66u, 0x72u,
  0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x32u, 0x38u, 0x37u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u,
  0x32u, 0x38u, 0x38u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x32u, 0x38u, 0x39u, 0x00u, 0x66u,
  0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x32u, 0x39u, 0x30u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu,
  0x30u, 0x32u, 0x39u, 0x31u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x32u, 0x39u, 0x32u, 0x00u,
  0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x32u, 0x39u, 0x33u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u,
  0x5Fu, 0x30u, 0x32u, 0x39u, 0x34u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x32u, 0x39u, 0x35u,
  0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x32u, 0x39u, 0x36u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du,
  0x65u, 0x5Fu, 0x30u, 0x32u, 0x39u, 0x37u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x32u, 0x39u,
  0x38u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x32u, 0x39u, 0x39u, 0x00u, 0x66u, 0x72u, 0x61u,
  0x6Du, 0x65u, 0x5Fu, 0x30u, 0x33u, 0x30u, 0x30u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x33u,
  0x30u, 0x31u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x33u, 0x30u, 0x32u, 0x00u, 0x66u, 0x72u,
  0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x33u, 0x30u, 0x33u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u,
  0x33u, 0x30u, 0x34u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x33u, 0x30u, 0x35u, 0x00u, 0x66u,
  0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x33u, 0x30u, 0x36u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu,
  0x30u, 0x33u, 0x30u, 0x37u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x33u, 0x30u, 0x38u, 0x00u,
  0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x33u, 0x30u, 0x39u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u,
  0x5Fu, 0x30u, 0x33u, 0x31u, 0x30u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x33u, 0x31u, 0x31u,
  0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x33u, 0x31u, 0x32u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du,
  0x65u, 0x5Fu, 0x30u, 0x33u, 0x31u, 0x33u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x33u, 0x31u,
  0x34u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x33u, 0x31u, 0x35u, 0x00u, 0x66u, 0x72u, 0x61u,
  0x6Du, 0x65u, 0x5Fu, 0x30u, 0x33u, 0x31u, 0x36u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x33u,
  0x31u, 0x37u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x33u, 0x31u, 0x38u, 0x00u, 0x66u, 0x72u,
  0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x33u, 0x31u, 0x39u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u,
  0x33u, 0x32u, 0x30u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x33u, 0x32u, 0x31u, 0x00u, 0x66u,
  0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x33u, 0x32u, 0x32u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu,
  0x30u, 0x33u, 0x32u, 0x33u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x33u, 0x32u, 0x34u, 0x00u,
  0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x33u, 0x32u, 0x35u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u,
  0x5Fu, 0x30u, 0x33u, 0x32u, 0x36u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x33u, 0x32u, 0x37u,
  0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x33u, 0x32u, 0x38u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du,
  0x65u, 0x5Fu, 0x30u, 0x33u, 0x32u, 0x39u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x33u, 0x33u,
  0x30u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x33u, 0x33u, 0x31u, 0x00u, 0x66u, 0x72u, 0x61u,
  0x6Du, 0x65u, 0x5Fu, 0x30u, 0x33u, 0x33u, 0x32u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x33u,
  0x33u, 0x33u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x33u, 0x33u, 0x34u, 0x00u, 0x66u, 0x72u,
  0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x33u, 0x33u, 0x35u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u,
  0x33u, 0x33u, 0x36u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x33u, 0x33u, 0x37u, 0x00u, 0x66u,
  0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x33u, 0x33u, 0x38u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu,
  0x30u, 0x33u, 0x33u, 0x39u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x33u, 0x34u, 0x30u, 0x00u,
  0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x33u, 0x34u, 0x31u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u,
  0x5Fu, 0x30u, 0x33u, 0x34u, 0x32u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x33u, 0x34u, 0x33u,
  0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x33u, 0x34u, 0x34u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du,
  0x65u, 0x5Fu, 0x30u, 0x33u, 0x34u, 0x35u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x33u, 0x34u,
  0x36u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x33u, 0x34u, 0x37u, 0x00u, 0x66u, 0x72u, 0x61u,
  0x6Du, 0x65u, 0x5Fu, 0x30u, 0x33u, 0x34u, 0x38u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x33u,
  0x34u, 0x39u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x33u, 0x35u, 0x30u, 0x00u, 0x66u, 0x72u,
  0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x33u, 0x35u, 0x31u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u,
  0x33u, 0x35u, 0x32u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x33u, 0x35u, 0x33u, 0x00u, 0x66u,
  0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x33u, 0x35u, 0x34u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu,
  0x30u, 0x33u, 0x35u, 0x35u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x33u, 0x35u, 0x36u, 0x00u,
  0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x33u, 0x35u, 0x37u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u,
  0x5Fu, 0x30u, 0x33u, 0x35u, 0x38u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x33u, 0x35u, 0x39u,
  0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x33u, 0x36u, 0x30u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du,
  0x65u, 0x5Fu, 0x30u, 0x33u, 0x36u, 0x31u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x33u, 0x36u,
  0x32u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x33u, 0x36u, 0x33u, 0x00u, 0x66u, 0x72u, 0x61u,
  0x6Du, 0x65u, 0x5Fu, 0x30u, 0x33u, 0x36u, 0x34u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x33u,
  0x36u, 0x35u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x33u, 0x36u, 0x36u, 0x00u, 0x66u, 0x72u,
  0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x33u, 0x36u, 0x37u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u,
  0x33u, 0x36u, 0x38u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x33u, 0x36u, 0x39u, 0x00u, 0x66u,
  0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x33u, 0x37u, 0x30u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu,
  0x30u, 0x33u, 0x37u, 0x31u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x33u, 0x37u, 0x32u, 0x00u,
  0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x33u, 0x37u, 0x33u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u,
  0x5Fu, 0x30u, 0x33u, 0x37u, 0x34u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x33u, 0x37u, 0x35u,
  0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x33u, 0x37u, 0x36u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du,
  0x65u, 0x5Fu, 0x30u, 0x33u, 0x37u, 0x37u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x33u, 0x37u,
  0x38u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x33u, 0x37u, 0x39u, 0x00u, 0x66u, 0x72u, 0x61u,
  0x6Du, 0x65u, 0x5Fu, 0x30u, 0x33u, 0x38u, 0x30u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x33u,
  0x38u, 0x31u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x33u, 0x38u, 0x32u, 0x00u, 0x66u, 0x72u,
  0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x33u, 0x38u, 0x33u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u,
  0x33u, 0x38u, 0x34u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x33u, 0x38u, 0x35u, 0x00u, 0x66u,
  0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x33u, 0x38u, 0x36u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu,
  0x30u, 0x33u, 0x38u, 0x37u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x33u, 0x38u, 0x38u, 0x00u,
  0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x33u, 0x38u, 0x39u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u,
  0x5Fu, 0x30u, 0x33u, 0x39u, 0x30u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x33u, 0x39u, 0x31u,
  0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x33u, 0x39u, 0x32u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du,
  0x65u, 0x5Fu, 0x30u, 0x33u, 0x39u, 0x33u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x33u, 0x39u,
  0x34u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x33u, 0x39u, 0x35u, 0x00u, 0x66u, 0x72u, 0x61u,
  0x6Du, 0x65u, 0x5Fu, 0x30u, 0x33u, 0x39u, 0x36u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x33u,
  0x39u, 0x37u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x33u, 0x39u, 0x38u, 0x00u, 0x66u, 0x72u,
  0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x33u, 0x39u, 0x39u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u,
  0x34u, 0x30u, 0x30u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x34u, 0x30u, 0x31u, 0x00u, 0x66u,
  0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x34u, 0x30u, 0x32u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu,
  0x30u, 0x34u, 0x30u, 0x33u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x34u, 0x30u, 0x34u, 0x00u,
  0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x34u, 0x30u, 0x35u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u,
  0x5Fu, 0x30u, 0x34u, 0x30u, 0x36u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x34u, 0x30u, 0x37u,
  0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x34u, 0x30u, 0x38u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du,
  0x65u, 0x5Fu, 0x30u, 0x34u, 0x30u, 0x39u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x34u, 0x31u,
  0x30u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x34u, 0x31u, 0x31u, 0x00u, 0x66u, 0x72u, 0x61u,
  0x6Du, 0x65u, 0x5Fu, 0x30u, 0x34u, 0x31u, 0x32u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x34u,
  0x31u, 0x33u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x34u, 0x31u, 0x34u, 0x00u, 0x66u, 0x72u,
  0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x34u, 0x31u, 0x35u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u,
  0x34u, 0x31u, 0x36u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x34u, 0x31u, 0x37u, 0x00u, 0x66u,
  0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x34u, 0x31u, 0x38u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu,
  0x30u, 0x34u, 0x31u, 0x39u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x34u, 0x32u, 0x30u, 0x00u,
  0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x34u, 0x32u, 0x31u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u,
  0x5Fu, 0x30u, 0x34u, 0x32u, 0x32u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x34u, 0x32u, 0x33u,
  0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x34u, 0x32u, 0x34u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du,
  0x65u, 0x5Fu, 0x30u, 0x34u, 0x32u, 0x35u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x34u, 0x32u,
  0x36u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x34u, 0x32u, 0x37u, 0x00u, 0x66u, 0x72u, 0x61u,
  0x6Du, 0x65u, 0x5Fu, 0x30u, 0x34u, 0x32u, 0x38u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x34u,
  0x32u, 0x39u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x34u, 0x33u, 0x30u, 0x00u, 0x66u, 0x72u,
  0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x34u, 0x33u, 0x31u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u,
  0x34u, 0x33u, 0x32u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x34u, 0x33u, 0x33u, 0x00u, 0x66u,
  0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x34u, 0x33u, 0x34u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu,
  0x30u, 0x34u, 0x33u, 0x35u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x34u, 0x33u, 0x36u, 0x00u,
  0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x34u, 0x33u, 0x37u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u,
  0x5Fu, 0x30u, 0x34u, 0x33u, 0x38u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x34u, 0x33u, 0x39u,
  0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x34u, 0x34u, 0x30u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du,
  0x65u, 0x5Fu, 0x30u, 0x34u, 0x34u, 0x31u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x34u, 0x34u,
  0x32u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x34u, 0x34u, 0x33u, 0x00u, 0x66u, 0x72u, 0x61u,
  0x6Du, 0x65u, 0x5Fu, 0x30u, 0x34u, 0x34u, 0x34u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x34u,
  0x34u, 0x35u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x34u, 0x34u, 0x36u, 0x00u, 0x66u, 0x72u,
  0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x34u, 0x34u, 0x37u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u,
  0x34u, 0x34u, 0x38u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x34u, 0x34u, 0x39u, 0x00u, 0x66u,
  0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x34u, 0x35u, 0x30u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu,
  0x30u, 0x34u, 0x35u, 0x31u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x34u, 0x35u, 0x32u, 0x00u,
  0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x34u, 0x35u, 0x33u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u,
  0x5Fu, 0x30u, 0x34u, 0x35u, 0x34u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x34u, 0x35u, 0x35u,
  0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x34u, 0x35u, 0x36u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du,
  0x65u, 0x5Fu, 0x30u, 0x34u, 0x35u, 0x37u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x34u, 0x35u,
  0x38u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x34u, 0x35u, 0x39u, 0x00u, 0x66u, 0x72u, 0x61u,
  0x6Du, 0x65u, 0x5Fu, 0x30u, 0x34u, 0x36u, 0x30u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x34u,
  0x36u, 0x31u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x34u, 0x36u, 0x32u, 0x00u, 0x66u, 0x72u,
  0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x34u, 0x36u, 0x33u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u,
  0x34u, 0x36u, 0x34u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x34u, 0x36u, 0x35u, 0x00u, 0x66u,
  0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x34u, 0x36u, 0x36u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu,
  0x30u, 0x34u, 0x36u, 0x37u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x34u, 0x36u, 0x38u, 0x00u,
  0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x34u, 0x36u, 0x39u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u,
  0x5Fu, 0x30u, 0x34u, 0x37u, 0x30u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x34u, 0x37u, 0x31u,
  0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x34u, 0x37u, 0x32u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du,
  0x65u, 0x5Fu, 0x30u, 0x34u, 0x37u, 0x33u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x34u, 0x37u,
  0x34u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x34u, 0x37u, 0x35u, 0x00u, 0x66u, 0x72u, 0x61u,
  0x6Du, 0x65u, 0x5Fu, 0x30u, 0x34u, 0x37u, 0x36u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x34u,
  0x37u, 0x37u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x34u, 0x37u, 0x38u, 0x00u, 0x66u, 0x72u,
  0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x34u, 0x37u, 0x39u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u,
  0x34u, 0x38u, 0x30u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x34u, 0x38u, 0x31u, 0x00u, 0x66u,
  0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x34u, 0x38u, 0x32u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu,
  0x30u, 0x34u, 0x38u, 0x33u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x34u, 0x38u, 0x34u, 0x00u,
  0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x34u, 0x38u, 0x35u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u,
  0x5Fu, 0x30u, 0x34u, 0x38u, 0x36u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x34u, 0x38u, 0x37u,
  0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x34u, 0x38u, 0x38u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du,
  0x65u, 0x5Fu, 0x30u, 0x34u, 0x38u, 0x39u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x34u, 0x39u,
  0x30u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x34u, 0x39u, 0x31u, 0x00u, 0x66u, 0x72u, 0x61u,
  0x6Du, 0x65u, 0x5Fu, 0x30u, 0x34u, 0x39u, 0x32u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x34u,
  0x39u, 0x33u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x34u, 0x39u, 0x34u, 0x00u, 0x66u, 0x72u,
  0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x34u, 0x39u, 0x35u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u,
  0x34u, 0x39u, 0x36u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x34u, 0x39u, 0x37u, 0x00u, 0x66u,
  0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x34u, 0x39u, 0x38u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu,
  0x30u, 0x34u, 0x39u, 0x39u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x35u, 0x30u, 0x30u, 0x00u,
  0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x35u, 0x30u, 0x31u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u,
  0x5Fu, 0x30u, 0x35u, 0x30u, 0x32u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x35u, 0x30u, 0x33u,
  0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x35u, 0x30u, 0x34u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du,
  0x65u, 0x5Fu, 0x30u, 0x35u, 0x30u, 0x35u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x35u, 0x30u,
  0x36u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x35u, 0x30u, 0x37u, 0x00u, 0x66u, 0x72u, 0x61u,
  0x6Du, 0x65u, 0x5Fu, 0x30u, 0x35u, 0x30u, 0x38u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x35u,
  0x30u, 0x39u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x35u, 0x31u, 0x30u, 0x00u, 0x66u, 0x72u,
  0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x35u, 0x31u, 0x31u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u,
  0x35u, 0x31u, 0x32u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x35u, 0x31u, 0x33u, 0x00u, 0x66u,
  0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x35u, 0x31u, 0x34u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu,
  0x30u, 0x35u, 0x31u, 0x35u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x35u, 0x31u, 0x36u, 0x00u,
  0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x35u, 0x31u, 0x37u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u,
  0x5Fu, 0x30u, 0x35u, 0x31u, 0x38u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x35u, 0x31u, 0x39u,
  0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x35u, 0x32u, 0x30u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du,
  0x65u, 0x5Fu, 0x30u, 0x35u, 0x32u, 0x31u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x35u, 0x32u,
  0x32u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x35u, 0x32u, 0x33u, 0x00u, 0x66u, 0x72u, 0x61u,
  0x6Du, 0x65u, 0x5Fu, 0x30u, 0x35u, 0x32u, 0x34u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x35u,
  0x32u, 0x35u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x35u, 0x32u, 0x36u, 0x00u, 0x66u, 0x72u,
  0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x35u, 0x32u, 0x37u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u,
  0x35u, 0x32u, 0x38u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x35u, 0x32u, 0x39u, 0x00u, 0x66u,
  0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x35u, 0x33u, 0x30u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu,
  0x30u, 0x35u, 0x33u, 0x31u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x35u, 0x33u, 0x32u, 0x00u,
  0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x35u, 0x33u, 0x33u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u,
  0x5Fu, 0x30u, 0x35u, 0x33u, 0x34u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x35u, 0x33u, 0x35u,
  0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x35u, 0x33u, 0x36u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du,
  0x65u, 0x5Fu, 0x30u, 0x35u, 0x33u, 0x37u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x35u, 0x33u,
  0x38u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x35u, 0x33u, 0x39u, 0x00u, 0x66u, 0x72u, 0x61u,
  0x6Du, 0x65u, 0x5Fu, 0x30u, 0x35u, 0x34u, 0x30u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x35u,
  0x34u, 0x31u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x35u, 0x34u, 0x32u, 0x00u, 0x66u, 0x72u,
  0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x35u, 0x34u, 0x33u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u,
  0x35u, 0x34u, 0x34u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x35u, 0x34u, 0x35u, 0x00u, 0x66u,
  0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x35u, 0x34u, 0x36u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu,
  0x30u, 0x35u, 0x34u, 0x37u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x35u, 0x34u, 0x38u, 0x00u,
  0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x35u, 0x34u, 0x39u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u,
  0x5Fu, 0x30u, 0x35u, 0x35u, 0x30u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x35u, 0x35u, 0x31u,
  0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x35u, 0x35u, 0x32u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du,
  0x65u, 0x5Fu, 0x30u, 0x35u, 0x35u, 0x33u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x35u, 0x35u,
  0x34u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x35u, 0x35u, 0x35u, 0x00u, 0x66u, 0x72u, 0x61u,
  0x6Du, 0x65u, 0x5Fu, 0x30u, 0x35u, 0x35u, 0x36u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x35u,
  0x35u, 0x37u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x35u, 0x35u, 0x38u, 0x00u, 0x66u, 0x72u,
  0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x35u, 0x35u, 0x39u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u,
  0x35u, 0x36u, 0x30u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x35u, 0x36u, 0x31u, 0x00u, 0x66u,
  0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x35u, 0x36u, 0x32u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu,
  0x30u, 0x35u, 0x36u, 0x33u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x35u, 0x36u, 0x34u, 0x00u,
  0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x35u, 0x36u, 0x35u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u,
  0x5Fu, 0x30u, 0x35u, 0x36u, 0x36u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x35u, 0x36u, 0x37u,
  0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x35u, 0x36u, 0x38u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du,
  0x65u, 0x5Fu, 0x30u, 0x35u, 0x36u, 0x39u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x35u, 0x37u,
  0x30u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x35u, 0x37u, 0x31u, 0x00u, 0x66u, 0x72u, 0x61u,
  0x6Du, 0x65u, 0x5Fu, 0x30u, 0x35u, 0x37u, 0x32u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x35u,
  0x37u, 0x33u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x35u, 0x37u, 0x34u, 0x00u, 0x66u, 0x72u,
  0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x35u, 0x37u, 0x35u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u,
  0x35u, 0x37u, 0x36u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x35u, 0x37u, 0x37u, 0x00u, 0x66u,
  0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x35u, 0x37u, 0x38u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu,
  0x30u, 0x35u, 0x37u, 0x39u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x35u, 0x38u, 0x30u, 0x00u,
  0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x35u, 0x38u, 0x31u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u,
  0x5Fu, 0x30u, 0x35u, 0x38u, 0x32u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x35u, 0x38u, 0x33u,
  0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x35u, 0x38u, 0x34u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du,
  0x65u, 0x5Fu, 0x30u, 0x35u, 0x38u, 0x35u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x35u, 0x38u,
  0x36u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x35u, 0x38u, 0x37u, 0x00u, 0x66u, 0x72u, 0x61u,
  0x6Du, 0x65u, 0x5Fu, 0x30u, 0x35u, 0x38u, 0x38u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x35u,
  0x38u, 0x39u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x35u, 0x39u, 0x30u, 0x00u, 0x66u, 0x72u,
  0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x35u, 0x39u, 0x31u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u,
  0x35u, 0x39u, 0x32u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x35u, 0x39u, 0x33u, 0x00u, 0x66u,
  0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x35u, 0x39u, 0x34u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu,
  0x30u, 0x35u, 0x39u, 0x35u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x35u, 0x39u, 0x36u, 0x00u,
  0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x35u, 0x39u, 0x37u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u,
  0x5Fu, 0x30u, 0x35u, 0x39u, 0x38u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x35u, 0x39u, 0x39u,
  0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x36u, 0x30u, 0x30u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du,
  0x65u, 0x5Fu, 0x30u, 0x36u, 0x30u, 0x31u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x36u, 0x30u,
  0x32u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x36u, 0x30u, 0x33u, 0x00u, 0x66u, 0x72u, 0x61u,
  0x6Du, 0x65u, 0x5Fu, 0x30u, 0x36u, 0x30u, 0x34u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x36u,
  0x30u, 0x35u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x36u, 0x30u, 0x36u, 0x00u, 0x66u, 0x72u,
  0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x36u, 0x30u, 0x37u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u,
  0x36u, 0x30u, 0x38u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x36u, 0x30u, 0x39u, 0x00u, 0x66u,
  0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x36u, 0x31u, 0x30u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu,
  0x30u, 0x36u, 0x31u, 0x31u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x36u, 0x31u, 0x32u, 0x00u,
  0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x36u, 0x31u, 0x33u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u,
  0x5Fu, 0x30u, 0x36u, 0x31u, 0x34u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x36u, 0x31u, 0x35u,
  0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x36u, 0x31u, 0x36u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du,
  0x65u, 0x5Fu, 0x30u, 0x36u, 0x31u, 0x37u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x36u, 0x31u,
  0x38u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x36u, 0x31u, 0x39u, 0x00u, 0x66u, 0x72u, 0x61u,
  0x6Du, 0x65u, 0x5Fu, 0x30u, 0x36u, 0x32u, 0x30u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x36u,
  0x32u, 0x31u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x36u, 0x32u, 0x32u, 0x00u, 0x66u, 0x72u,
  0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x36u, 0x32u, 0x33u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u,
  0x36u, 0x32u, 0x34u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x36u, 0x32u, 0x35u, 0x00u, 0x66u,
  0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x36u, 0x32u, 0x36u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu,
  0x30u, 0x36u, 0x32u, 0x37u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x36u, 0x32u, 0x38u, 0x00u,
  0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x36u, 0x32u, 0x39u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u,
  0x5Fu, 0x30u, 0x36u, 0x33u, 0x30u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x36u, 0x33u, 0x31u,
  0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x36u, 0x33u, 0x32u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du,
  0x65u, 0x5Fu, 0x30u, 0x36u, 0x33u, 0x33u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x36u, 0x33u,
  0x34u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x36u, 0x33u, 0x35u, 0x00u, 0x66u, 0x72u, 0x61u,
  0x6Du, 0x65u, 0x5Fu, 0x30u, 0x36u, 0x33u, 0x36u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x36u,
  0x33u, 0x37u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x36u, 0x33u, 0x38u, 0x00u, 0x66u, 0x72u,
  0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x36u, 0x33u, 0x39u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u,
  0x36u, 0x34u, 0x30u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x36u, 0x34u, 0x31u, 0x00u, 0x66u,
  0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x36u, 0x34u, 0x32u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu,
  0x30u, 0x36u, 0x34u, 0x33u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x36u, 0x34u, 0x34u, 0x00u,
  0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x36u, 0x34u, 0x35u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u,
  0x5Fu, 0x30u, 0x36u, 0x34u, 0x36u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x36u, 0x34u, 0x37u,
  0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x36u, 0x34u, 0x38u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du,
  0x65u, 0x5Fu, 0x30u, 0x36u, 0x34u, 0x39u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x36u, 0x35u,
  0x30u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x36u, 0x35u, 0x31u, 0x00u, 0x66u, 0x72u, 0x61u,
  0x6Du, 0x65u, 0x5Fu, 0x30u, 0x36u, 0x35u, 0x32u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x36u,
  0x35u, 0x33u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x36u, 0x35u, 0x34u, 0x00u, 0x66u, 0x72u,
  0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x36u, 0x35u, 0x35u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u,
  0x36u, 0x35u, 0x36u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x36u, 0x35u, 0x37u, 0x00u, 0x66u,
  0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x36u, 0x35u, 0x38u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu,
  0x30u, 0x36u, 0x35u, 0x39u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x36u, 0x36u, 0x30u, 0x00u,
  0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x36u, 0x36u, 0x31u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u,
  0x5Fu, 0x30u, 0x36u, 0x36u, 0x32u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x36u, 0x36u, 0x33u,
  0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x36u, 0x36u, 0x34u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du,
  0x65u, 0x5Fu, 0x30u, 0x36u, 0x36u, 0x35u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x36u, 0x36u,
  0x36u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x36u, 0x36u, 0x37u, 0x00u, 0x66u, 0x72u, 0x61u,
  0x6Du, 0x65u, 0x5Fu, 0x30u, 0x36u, 0x36u, 0x38u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x36u,
  0x36u, 0x39u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x36u, 0x37u, 0x30u, 0x00u, 0x66u, 0x72u,
  0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x36u, 0x37u, 0x31u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u,
  0x36u, 0x37u, 0x32u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x36u, 0x37u, 0x33u, 0x00u, 0x66u,
  0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x36u, 0x37u, 0x34u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu,
  0x30u, 0x36u, 0x37u, 0x35u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x36u, 0x37u, 0x36u, 0x00u,
  0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x36u, 0x37u, 0x37u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u,
  0x5Fu, 0x30u, 0x36u, 0x37u, 0x38u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x36u, 0x37u, 0x39u,
  0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x36u, 0x38u, 0x30u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du,
  0x65u, 0x5Fu, 0x30u, 0x36u, 0x38u, 0x31u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x36u, 0x38u,
  0x32u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x36u, 0x38u, 0x33u, 0x00u, 0x66u, 0x72u, 0x61u,
  0x6Du, 0x65u, 0x5Fu, 0x30u, 0x36u, 0x38u, 0x34u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x36u,
  0x38u, 0x35u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x36u, 0x38u, 0x36u, 0x00u, 0x66u, 0x72u,
  0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x36u, 0x38u, 0x37u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u,
  0x36u, 0x38u, 0x38u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x36u, 0x38u, 0x39u, 0x00u, 0x66u,
  0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x36u, 0x39u, 0x30u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu,
  0x30u, 0x36u, 0x39u, 0x31u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x36u, 0x39u, 0x32u, 0x00u,
  0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x36u, 0x39u, 0x33u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u,
  0x5Fu, 0x30u, 0x36u, 0x39u, 0x34u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x36u, 0x39u, 0x35u,
  0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x36u, 0x39u, 0x36u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du,
  0x65u, 0x5Fu, 0x30u, 0x36u, 0x39u, 0x37u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x36u, 0x39u,
  0x38u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x36u, 0x39u, 0x39u, 0x00u, 0x66u, 0x72u, 0x61u,
  0x6Du, 0x65u, 0x5Fu, 0x30u, 0x37u, 0x30u, 0x30u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x37u,
  0x30u, 0x31u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x37u, 0x30u, 0x32u, 0x00u, 0x66u, 0x72u,
  0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x37u, 0x30u, 0x33u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u,
  0x37u, 0x30u, 0x34u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x37u, 0x30u, 0x35u, 0x00u, 0x66u,
  0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x37u, 0x30u, 0x36u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu,
  0x30u, 0x37u, 0x30u, 0x37u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x37u, 0x30u, 0x38u, 0x00u,
  0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x37u, 0x30u, 0x39u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u,
  0x5Fu, 0x30u, 0x37u, 0x31u, 0x30u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x37u, 0x31u, 0x31u,
  0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x37u, 0x31u, 0x32u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du,
  0x65u, 0x5Fu, 0x30u, 0x37u, 0x31u, 0x33u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x37u, 0x31u,
  0x34u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x37u, 0x31u, 0x35u, 0x00u, 0x66u, 0x72u, 0x61u,
  0x6Du, 0x65u, 0x5Fu, 0x30u, 0x37u, 0x31u, 0x36u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x37u,
  0x31u, 0x37u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x37u, 0x31u, 0x38u, 0x00u, 0x66u, 0x72u,
  0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x37u, 0x31u, 0x39u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u,
  0x37u, 0x32u, 0x30u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x37u, 0x32u, 0x31u, 0x00u, 0x66u,
  0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x37u, 0x32u, 0x32u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu,
  0x30u, 0x37u, 0x32u, 0x33u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x37u, 0x32u, 0x34u, 0x00u,
  0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x37u, 0x32u, 0x35u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u,
  0x5Fu, 0x30u, 0x37u, 0x32u, 0x36u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x37u, 0x32u, 0x37u,
  0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x37u, 0x32u, 0x38u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du,
  0x65u, 0x5Fu, 0x30u, 0x37u, 0x32u, 0x39u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x37u, 0x33u,
  0x30u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x37u, 0x33u, 0x31u, 0x00u, 0x66u, 0x72u, 0x61u,
  0x6Du, 0x65u, 0x5Fu, 0x30u, 0x37u, 0x33u, 0x32u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x37u,
  0x33u, 0x33u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x37u, 0x33u, 0x34u, 0x00u, 0x66u, 0x72u,
  0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x37u, 0x33u, 0x35u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u,
  0x37u, 0x33u, 0x36u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x37u, 0x33u, 0x37u, 0x00u, 0x66u,
  0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x37u, 0x33u, 0x38u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu,
  0x30u, 0x37u, 0x33u, 0x39u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x37u, 0x34u, 0x30u, 0x00u,
  0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x37u, 0x34u, 0x31u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u,
  0x5Fu, 0x30u, 0x37u, 0x34u, 0x32u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x37u, 0x34u, 0x33u,
  0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x37u, 0x34u, 0x34u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du,
  0x65u, 0x5Fu, 0x30u, 0x37u, 0x34u, 0x35u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x37u, 0x34u,
  0x36u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x37u, 0x34u, 0x37u, 0x00u, 0x66u, 0x72u, 0x61u,
  0x6Du, 0x65u, 0x5Fu, 0x30u, 0x37u, 0x34u, 0x38u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x37u,
  0x34u, 0x39u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x37u, 0x35u, 0x30u, 0x00u, 0x66u, 0x72u,
  0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x37u, 0x35u, 0x31u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u,
  0x37u, 0x35u, 0x32u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x37u, 0x35u, 0x33u, 0x00u, 0x66u,
  0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x37u, 0x35u, 0x34u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu,
  0x30u, 0x37u, 0x35u, 0x35u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x37u, 0x35u, 0x36u, 0x00u,
  0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x37u, 0x35u, 0x37u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u,
  0x5Fu, 0x30u, 0x37u, 0x35u, 0x38u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x37u, 0x35u, 0x39u,
  0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x37u, 0x36u, 0x30u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du,
  0x65u, 0x5Fu, 0x30u, 0x37u, 0x36u, 0x31u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x37u, 0x36u,
  0x32u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x37u, 0x36u, 0x33u, 0x00u, 0x66u, 0x72u, 0x61u,
  0x6Du, 0x65u, 0x5Fu, 0x30u, 0x37u, 0x36u, 0x34u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x37u,
  0x36u, 0x35u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x37u, 0x36u, 0x36u, 0x00u, 0x66u, 0x72u,
  0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x37u, 0x36u, 0x37u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u,
  0x37u, 0x36u, 0x38u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x37u, 0x36u, 0x39u, 0x00u, 0x66u,
  0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x37u, 0x37u, 0x30u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu,
  0x30u, 0x37u, 0x37u, 0x31u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x37u, 0x37u, 0x32u, 0x00u,
  0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x37u, 0x37u, 0x33u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u,
  0x5Fu, 0x30u, 0x37u, 0x37u, 0x34u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x37u, 0x37u, 0x35u,
  0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x37u, 0x37u, 0x36u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du,
  0x65u, 0x5Fu, 0x30u, 0x37u, 0x37u, 0x37u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x37u, 0x37u,
  0x38u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x37u, 0x37u, 0x39u, 0x00u, 0x66u, 0x72u, 0x61u,
  0x6Du, 0x65u, 0x5Fu, 0x30u, 0x37u, 0x38u, 0x30u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x37u,
  0x38u, 0x31u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x37u, 0x38u, 0x32u, 0x00u, 0x66u, 0x72u,
  0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x37u, 0x38u, 0x33u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u,
  0x37u, 0x38u, 0x34u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x37u, 0x38u, 0x35u, 0x00u, 0x66u,
  0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x37u, 0x38u, 0x36u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu,
  0x30u, 0x37u, 0x38u, 0x37u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x37u, 0x38u, 0x38u, 0x00u,
  0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x37u, 0x38u, 0x39u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u,
  0x5Fu, 0x30u, 0x37u, 0x39u, 0x30u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x37u, 0x39u, 0x31u,
  0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x37u, 0x39u, 0x32u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du,
  0x65u, 0x5Fu, 0x30u, 0x37u, 0x39u, 0x33u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x37u, 0x39u,
  0x34u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x37u, 0x39u, 0x35u, 0x00u, 0x66u, 0x72u, 0x61u,
  0x6Du, 0x65u, 0x5Fu, 0x30u, 0x37u, 0x39u, 0x36u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x37u,
  0x39u, 0x37u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x37u, 0x39u, 0x38u, 0x00u, 0x66u, 0x72u,
  0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x37u, 0x39u, 0x39u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u,
  0x38u, 0x30u, 0x30u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x38u, 0x30u, 0x31u, 0x00u, 0x66u,
  0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x38u, 0x30u, 0x32u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu,
  0x30u, 0x38u, 0x30u, 0x33u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x38u, 0x30u, 0x34u, 0x00u,
  0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x38u, 0x30u, 0x35u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u,
  0x5Fu, 0x30u, 0x38u, 0x30u, 0x36u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x38u, 0x30u, 0x37u,
  0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x38u, 0x30u, 0x38u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du,
  0x65u, 0x5Fu, 0x30u, 0x38u, 0x30u, 0x39u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x38u, 0x31u,
  0x30u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x38u, 0x31u, 0x31u, 0x00u, 0x66u, 0x72u, 0x61u,
  0x6Du, 0x65u, 0x5Fu, 0x30u, 0x38u, 0x31u, 0x32u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x38u,
  0x31u, 0x33u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x38u, 0x31u, 0x34u, 0x00u, 0x66u, 0x72u,
  0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x38u, 0x31u, 0x35u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u,
  0x38u, 0x31u, 0x36u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x38u, 0x31u, 0x37u, 0x00u, 0x66u,
  0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x38u, 0x31u, 0x38u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu,
  0x30u, 0x38u, 0x31u, 0x39u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x38u, 0x32u, 0x30u, 0x00u,
  0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x38u, 0x32u, 0x31u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u,
  0x5Fu, 0x30u, 0x38u, 0x32u, 0x32u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x38u, 0x32u, 0x33u,
  0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x38u, 0x32u, 0x34u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du,
  0x65u, 0x5Fu, 0x30u, 0x38u, 0x32u, 0x35u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x38u, 0x32u,
  0x36u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x38u, 0x32u, 0x37u, 0x00u, 0x66u, 0x72u, 0x61u,
  0x6Du, 0x65u, 0x5Fu, 0x30u, 0x38u, 0x32u, 0x38u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x38u,
  0x32u, 0x39u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x38u, 0x33u, 0x30u, 0x00u, 0x66u, 0x72u,
  0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x38u, 0x33u, 0x31u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u,
  0x38u, 0x33u, 0x32u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x38u, 0x33u, 0x33u, 0x00u, 0x66u,
  0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x38u, 0x33u, 0x34u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu,
  0x30u, 0x38u, 0x33u, 0x35u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x38u, 0x33u, 0x36u, 0x00u,
  0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x38u, 0x33u, 0x37u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u,
  0x5Fu, 0x30u, 0x38u, 0x33u, 0x38u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x38u, 0x33u, 0x39u,
  0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x38u, 0x34u, 0x30u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du,
  0x65u, 0x5Fu, 0x30u, 0x38u, 0x34u, 0x31u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x38u, 0x34u,
  0x32u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x38u, 0x34u, 0x33u, 0x00u, 0x66u, 0x72u, 0x61u,
  0x6Du, 0x65u, 0x5Fu, 0x30u, 0x38u, 0x34u, 0x34u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x38u,
  0x34u, 0x35u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x38u, 0x34u, 0x36u, 0x00u, 0x66u, 0x72u,
  0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x38u, 0x34u, 0x37u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u,
  0x38u, 0x34u, 0x38u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x38u, 0x34u, 0x39u, 0x00u, 0x66u,
  0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x38u, 0x35u, 0x30u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu,
  0x30u, 0x38u, 0x35u, 0x31u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x38u, 0x35u, 0x32u, 0x00u,
  0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x38u, 0x35u, 0x33u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u,
  0x5Fu, 0x30u, 0x38u, 0x35u, 0x34u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x38u, 0x35u, 0x35u,
  0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x38u, 0x35u, 0x36u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du,
  0x65u, 0x5Fu, 0x30u, 0x38u, 0x35u, 0x37u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x38u, 0x35u,
  0x38u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x38u, 0x35u, 0x39u, 0x00u, 0x66u, 0x72u, 0x61u,
  0x6Du, 0x65u, 0x5Fu, 0x30u, 0x38u, 0x36u, 0x30u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x38u,
  0x36u, 0x31u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x38u, 0x36u, 0x32u, 0x00u, 0x66u, 0x72u,
  0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x38u, 0x36u, 0x33u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u,
  0x38u, 0x36u, 0x34u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x38u, 0x36u, 0x35u, 0x00u, 0x66u,
  0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x38u, 0x36u, 0x36u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu,
  0x30u, 0x38u, 0x36u, 0x37u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x38u, 0x36u, 0x38u, 0x00u,
  0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x38u, 0x36u, 0x39u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u,
  0x5Fu, 0x30u, 0x38u, 0x37u, 0x30u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x38u, 0x37u, 0x31u,
  0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x38u, 0x37u, 0x32u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du,
  0x65u, 0x5Fu, 0x30u, 0x38u, 0x37u, 0x33u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x38u, 0x37u,
  0x34u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x38u, 0x37u, 0x35u, 0x00u, 0x66u, 0x72u, 0x61u,
  0x6Du, 0x65u, 0x5Fu, 0x30u, 0x38u, 0x37u, 0x36u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x38u,
  0x37u, 0x37u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x38u, 0x37u, 0x38u, 0x00u, 0x66u, 0x72u,
  0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x38u, 0x37u, 0x39u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u,
  0x38u, 0x38u, 0x30u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x38u, 0x38u, 0x31u, 0x00u, 0x66u,
  0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x38u, 0x38u, 0x32u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu,
  0x30u, 0x38u, 0x38u, 0x33u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x38u, 0x38u, 0x34u, 0x00u,
  0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x38u, 0x38u, 0x35u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u,
  0x5Fu, 0x30u, 0x38u, 0x38u, 0x36u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x38u, 0x38u, 0x37u,
  0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x38u, 0x38u, 0x38u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du,
  0x65u, 0x5Fu, 0x30u, 0x38u, 0x38u, 0x39u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x38u, 0x39u,
  0x30u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x38u, 0x39u, 0x31u, 0x00u, 0x66u, 0x72u, 0x61u,
  0x6Du, 0x65u, 0x5Fu, 0x30u, 0x38u, 0x39u, 0x32u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x38u,
  0x39u, 0x33u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x38u, 0x39u, 0x34u, 0x00u, 0x66u, 0x72u,
  0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x38u, 0x39u, 0x35u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u,
  0x38u, 0x39u, 0x36u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x38u, 0x39u, 0x37u, 0x00u, 0x66u,
  0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x38u, 0x39u, 0x38u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu,
  0x30u, 0x38u, 0x39u, 0x39u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x39u, 0x30u, 0x30u, 0x00u,
  0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x39u, 0x30u, 0x31u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u,
  0x5Fu, 0x30u, 0x39u, 0x30u, 0x32u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x39u, 0x30u, 0x33u,
  0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x39u, 0x30u, 0x34u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du,
  0x65u, 0x5Fu, 0x30u, 0x39u, 0x30u, 0x35u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x39u, 0x30u,
  0x36u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x39u, 0x30u, 0x37u, 0x00u, 0x66u, 0x72u, 0x61u,
  0x6Du, 0x65u, 0x5Fu, 0x30u, 0x39u, 0x30u, 0x38u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x39u,
  0x30u, 0x39u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x39u, 0x31u, 0x30u, 0x00u, 0x66u, 0x72u,
  0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x39u, 0x31u, 0x31u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u,
  0x39u, 0x31u, 0x32u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x39u, 0x31u, 0x33u, 0x00u, 0x66u,
  0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x39u, 0x31u, 0x34u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu,
  0x30u, 0x39u, 0x31u, 0x35u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x39u, 0x31u, 0x36u, 0x00u,
  0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x39u, 0x31u, 0x37u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u,
  0x5Fu, 0x30u, 0x39u, 0x31u, 0x38u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x39u, 0x31u, 0x39u,
  0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x39u, 0x32u, 0x30u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du,
  0x65u, 0x5Fu, 0x30u, 0x39u, 0x32u, 0x31u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x39u, 0x32u,
  0x32u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x39u, 0x32u, 0x33u, 0x00u, 0x66u, 0x72u, 0x61u,
  0x6Du, 0x65u, 0x5Fu, 0x30u, 0x39u, 0x32u, 0x34u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x39u,
  0x32u, 0x35u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x39u, 0x32u, 0x36u, 0x00u, 0x66u, 0x72u,
  0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x39u, 0x32u, 0x37u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u,
  0x39u, 0x32u, 0x38u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x39u, 0x32u, 0x39u, 0x00u, 0x66u,
  0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x39u, 0x33u, 0x30u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu,
  0x30u, 0x39u, 0x33u, 0x31u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x39u, 0x33u, 0x32u, 0x00u,
  0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x39u, 0x33u, 0x33u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u,
  0x5Fu, 0x30u, 0x39u, 0x33u, 0x34u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x39u, 0x33u, 0x35u,
  0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x39u, 0x33u, 0x36u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du,
  0x65u, 0x5Fu, 0x30u, 0x39u, 0x33u, 0x37u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x39u, 0x33u,
  0x38u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x39u, 0x33u, 0x39u, 0x00u, 0x66u, 0x72u, 0x61u,
  0x6Du, 0x65u, 0x5Fu, 0x30u, 0x39u, 0x34u, 0x30u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x39u,
  0x34u, 0x31u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x39u, 0x34u, 0x32u, 0x00u, 0x66u, 0x72u,
  0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x39u, 0x34u, 0x33u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u,
  0x39u, 0x34u, 0x34u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x39u, 0x34u, 0x35u, 0x00u, 0x66u,
  0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x39u, 0x34u, 0x36u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu,
  0x30u, 0x39u, 0x34u, 0x37u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x39u, 0x34u, 0x38u, 0x00u,
  0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x39u, 0x34u, 0x39u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u,
  0x5Fu, 0x30u, 0x39u, 0x35u, 0x30u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x39u, 0x35u, 0x31u,
  0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x39u, 0x35u, 0x32u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du,
  0x65u, 0x5Fu, 0x30u, 0x39u, 0x35u, 0x33u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x39u, 0x35u,
  0x34u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x39u, 0x35u, 0x35u, 0x00u, 0x66u, 0x72u, 0x61u,
  0x6Du, 0x65u, 0x5Fu, 0x30u, 0x39u, 0x35u, 0x36u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x39u,
  0x35u, 0x37u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x39u, 0x35u, 0x38u, 0x00u, 0x66u, 0x72u,
  0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x39u, 0x35u, 0x39u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u,
  0x39u, 0x36u, 0x30u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x39u, 0x36u, 0x31u, 0x00u, 0x66u,
  0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x39u, 0x36u, 0x32u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu,
  0x30u, 0x39u, 0x36u, 0x33u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x39u, 0x36u, 0x34u, 0x00u,
  0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x39u, 0x36u, 0x35u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u,
  0x5Fu, 0x30u, 0x39u, 0x36u, 0x36u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x39u, 0x36u, 0x37u,
  0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x39u, 0x36u, 0x38u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du,
  0x65u, 0x5Fu, 0x30u, 0x39u, 0x36u, 0x39u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x39u, 0x37u,
  0x30u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x39u, 0x37u, 0x31u, 0x00u, 0x66u, 0x72u, 0x61u,
  0x6Du, 0x65u, 0x5Fu, 0x30u, 0x39u, 0x37u, 0x32u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x39u,
  0x37u, 0x33u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x39u, 0x37u, 0x34u, 0x00u, 0x66u, 0x72u,
  0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x39u, 0x37u, 0x35u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u,
  0x39u, 0x37u, 0x36u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x39u, 0x37u, 0x37u, 0x00u, 0x66u,
  0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x39u, 0x37u, 0x38u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu,
  0x30u, 0x39u, 0x37u, 0x39u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x39u, 0x38u, 0x30u, 0x00u,
  0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x39u, 0x38u, 0x31u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u,
  0x5Fu, 0x30u, 0x39u, 0x38u, 0x32u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x39u, 0x38u, 0x33u,
  0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x39u, 0x38u, 0x34u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du,
  0x65u, 0x5Fu, 0x30u, 0x39u, 0x38u, 0x35u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x39u, 0x38u,
  0x36u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x39u, 0x38u, 0x37u, 0x00u, 0x66u, 0x72u, 0x61u,
  0x6Du, 0x65u, 0x5Fu, 0x30u, 0x39u, 0x38u, 0x38u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x39u,
  0x38u, 0x39u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x39u, 0x39u, 0x30u, 0x00u, 0x66u, 0x72u,
  0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x39u, 0x39u, 0x31u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u,
  0x39u, 0x39u, 0x32u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x39u, 0x39u, 0x33u, 0x00u, 0x66u,
  0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x39u, 0x39u, 0x34u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu,
  0x30u, 0x39u, 0x39u, 0x35u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x39u, 0x39u, 0x36u, 0x00u,
  0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x39u, 0x39u, 0x37u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u,
  0x5Fu, 0x30u, 0x39u, 0x39u, 0x38u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x30u, 0x39u, 0x39u, 0x39u,
  0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x31u, 0x30u, 0x30u, 0x30u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du,
  0x65u, 0x5Fu, 0x31u, 0x30u, 0x30u, 0x31u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x31u, 0x30u, 0x30u,
  0x32u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x31u, 0x30u, 0x30u, 0x33u, 0x00u, 0x66u, 0x72u, 0x61u,
  0x6Du, 0x65u, 0x5Fu, 0x31u, 0x30u, 0x30u, 0x34u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x31u, 0x30u,
  0x30u, 0x35u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x31u, 0x30u, 0x30u, 0x36u, 0x00u, 0x66u, 0x72u,
  0x61u, 0x6Du, 0x65u, 0x5Fu, 0x31u, 0x30u, 0x30u, 0x37u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x31u,
  0x30u, 0x30u, 0x38u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x31u, 0x30u, 0x30u, 0x39u, 0x00u, 0x66u,
  0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x31u, 0x30u, 0x31u, 0x30u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu,
  0x31u, 0x30u, 0x31u, 0x31u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x31u, 0x30u, 0x31u, 0x32u, 0x00u,
  0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x31u, 0x30u, 0x31u, 0x33u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u,
  0x5Fu, 0x31u, 0x30u, 0x31u, 0x34u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x31u, 0x30u, 0x31u, 0x35u,
  0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x31u, 0x30u, 0x31u, 0x36u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du,
  0x65u, 0x5Fu, 0x31u, 0x30u, 0x31u, 0x37u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x31u, 0x30u, 0x31u,
  0x38u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x31u, 0x30u, 0x31u, 0x39u, 0x00u, 0x66u, 0x72u, 0x61u,
  0x6Du, 0x65u, 0x5Fu, 0x31u, 0x30u, 0x32u, 0x30u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x31u, 0x30u,
  0x32u, 0x31u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x31u, 0x30u, 0x32u, 0x32u, 0x00u, 0x66u, 0x72u,
  0x61u, 0x6Du, 0x65u, 0x5Fu, 0x31u, 0x30u, 0x32u, 0x33u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x31u,
  0x30u, 0x32u, 0x34u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x31u, 0x30u, 0x32u, 0x35u, 0x00u, 0x66u,
  0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x31u, 0x30u, 0x32u, 0x36u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu,
  0x31u, 0x30u, 0x32u, 0x37u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x31u, 0x30u, 0x32u, 0x38u, 0x00u,
  0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x31u, 0x30u, 0x32u, 0x39u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u,
  0x5Fu, 0x31u, 0x30u, 0x33u, 0x30u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x31u, 0x30u, 0x33u, 0x31u,
  0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x31u, 0x30u, 0x33u, 0x32u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du,
  0x65u, 0x5Fu, 0x31u, 0x30u, 0x33u, 0x33u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x31u, 0x30u, 0x33u,
  0x34u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x31u, 0x30u, 0x33u, 0x35u, 0x00u, 0x66u, 0x72u, 0x61u,
  0x6Du, 0x65u, 0x5Fu, 0x31u, 0x30u, 0x33u, 0x36u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x31u, 0x30u,
  0x33u, 0x37u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x31u, 0x30u, 0x33u, 0x38u, 0x00u, 0x66u, 0x72u,
  0x61u, 0x6Du, 0x65u, 0x5Fu, 0x31u, 0x30u, 0x33u, 0x39u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x31u,
  0x30u, 0x34u, 0x30u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x31u, 0x30u, 0x34u, 0x31u, 0x00u, 0x66u,
  0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x31u, 0x30u, 0x34u, 0x32u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu,
  0x31u, 0x30u, 0x34u, 0x33u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x31u, 0x30u, 0x34u, 0x34u, 0x00u,
  0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x31u, 0x30u, 0x34u, 0x35u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u,
  0x5Fu, 0x31u, 0x30u, 0x34u, 0x36u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x31u, 0x30u, 0x34u, 0x37u,
  0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x31u, 0x30u, 0x34u, 0x38u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du,
  0x65u, 0x5Fu, 0x31u, 0x30u, 0x34u, 0x39u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x31u, 0x30u, 0x35u,
  0x30u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x31u, 0x30u, 0x35u, 0x31u, 0x00u, 0x66u, 0x72u, 0x61u,
  0x6Du, 0x65u, 0x5Fu, 0x31u, 0x30u, 0x35u, 0x32u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x31u, 0x30u,
  0x35u, 0x33u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x31u, 0x30u, 0x35u, 0x34u, 0x00u, 0x66u, 0x72u,
  0x61u, 0x6Du, 0x65u, 0x5Fu, 0x31u, 0x30u, 0x35u, 0x35u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x31u,
  0x30u, 0x35u, 0x36u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x31u, 0x30u, 0x35u, 0x37u, 0x00u, 0x66u,
  0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x31u, 0x30u, 0x35u, 0x38u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu,
  0x31u, 0x30u, 0x35u, 0x39u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x31u, 0x30u, 0x36u, 0x30u, 0x00u,
  0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x31u, 0x30u, 0x36u, 0x31u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u,
  0x5Fu, 0x31u, 0x30u, 0x36u, 0x32u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x31u, 0x30u, 0x36u, 0x33u,
  0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x31u, 0x30u, 0x36u, 0x34u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du,
  0x65u, 0x5Fu, 0x31u, 0x30u, 0x36u, 0x35u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x31u, 0x30u, 0x36u,
  0x36u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x31u, 0x30u, 0x36u, 0x37u, 0x00u, 0x66u, 0x72u, 0x61u,
  0x6Du, 0x65u, 0x5Fu, 0x31u, 0x30u, 0x36u, 0x38u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x31u, 0x30u,
  0x36u, 0x39u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x31u, 0x30u, 0x37u, 0x30u, 0x00u, 0x66u, 0x72u,
  0x61u, 0x6Du, 0x65u, 0x5Fu, 0x31u, 0x30u, 0x37u, 0x31u, 0x00u, 0x66u, 0x72u, 0x61u, 0x6Du, 0x65u, 0x5Fu, 0x31u,
  0x30u, 0x37u, 0x32u, 0x00u, 0x69u, 0x64u, 0x6Cu, 0x65u, 0x00u, 0x74u, 0x6Fu, 0x75u, 0x63u, 0x68u, 0x00u, 0x73u,
  0x77u, 0x69u, 0x70u, 0x65u, 0x5Fu, 0x6Cu, 0x65u, 0x66u, 0x74u, 0x00u, 0x73u, 0x77u, 0x69u, 0x70u, 0x65u, 0x5Fu,
  0x72u, 0x69u, 0x67u, 0x68u, 0x74u, 0x00u, 0x73u, 0x77u, 0x69u, 0x70u, 0x65u, 0x5Fu, 0x75u, 0x70u, 0x00u, 0x73u,
  0x77u, 0x69u, 0x70u, 0x65u, 0x5Fu, 0x64u, 0x6Fu, 0x77u, 0x6Eu, 0x00u, 0x6Cu, 0x69u, 0x73u, 0x74u, 0x65u, 0x6Eu,
  0x69u, 0x6Eu, 0x67u, 0x00u, 0x74u, 0x68u, 0x69u, 0x6Eu, 0x6Bu, 0x69u, 0x6Eu, 0x67u, 0x00u, 0x73u, 0x70u, 0x65u,
  0x61u, 0x6Bu, 0x69u, 0x6Eu, 0x67u, 0x00u, 0x68u, 0x61u, 0x70u, 0x70u, 0x79u, 0x00u, 0x73u, 0x6Cu, 0x65u, 0x65u,
  0x70u, 0x79u, 0x00u, 0x72u, 0x65u, 0x63u, 0x6Fu, 0x72u, 0x64u, 0x69u, 0x6Eu, 0x67u, 0x00u, 0x73u, 0x70u, 0x65u,
  0x61u, 0x6Bu, 0x65u, 0x72u, 0x00u, 0x63u, 0x68u, 0x61u, 0x72u, 0x67u, 0x69u, 0x6Eu, 0x67u, 0x00u, 0x73u, 0x79u,
  0x6Eu, 0x63u, 0x5Fu, 0x63u, 0x6Fu, 0x6Du, 0x70u, 0x6Cu, 0x65u, 0x74u, 0x65u, 0x00u, 0x6Cu, 0x6Fu, 0x77u, 0x5Fu,
  0x62u, 0x61u, 0x74u, 0x74u, 0x65u, 0x72u, 0x79u, 0x00u, 0x65u, 0x72u, 0x72u, 0x6Fu, 0x72u, 0x00u, 0x6Du, 0x65u,
  0x6Eu, 0x75u, 0x5Fu, 0x68u, 0x6Fu, 0x6Cu, 0x64u, 0x00u, 0x73u, 0x61u, 0x76u, 0x69u, 0x6Eu, 0x67u, 0x00u, 0x73u,
  0x61u, 0x76u, 0x65u, 0x64u, 0x00u, 0x73u, 0x6Cu, 0x65u, 0x65u, 0x70u, 0x00u, 0x77u, 0x61u, 0x6Bu, 0x65u, 0x00u,
  0x61u, 0x74u, 0x74u, 0x65u, 0x6Eu, 0x74u, 0x69u, 0x6Fu, 0x6Eu, 0x2Eu, 0x63u, 0x65u, 0x6Eu, 0x74u, 0x65u, 0x72u,
  0x00u, 0x61u, 0x74u, 0x74u, 0x65u, 0x6Eu, 0x74u, 0x69u, 0x6Fu, 0x6Eu, 0x2Eu, 0x75u, 0x70u, 0x5Fu, 0x6Cu, 0x65u,
  0x66u, 0x74u, 0x00u, 0x61u, 0x74u, 0x74u, 0x65u, 0x6Eu, 0x74u, 0x69u, 0x6Fu, 0x6Eu, 0x2Eu, 0x75u, 0x70u, 0x00u,
  0x61u, 0x74u, 0x74u, 0x65u, 0x6Eu, 0x74u, 0x69u, 0x6Fu, 0x6Eu, 0x2Eu, 0x75u, 0x70u, 0x5Fu, 0x72u, 0x69u, 0x67u,
  0x68u, 0x74u, 0x00u, 0x61u, 0x74u, 0x74u, 0x65u, 0x6Eu, 0x74u, 0x69u, 0x6Fu, 0x6Eu, 0x2Eu, 0x6Cu, 0x65u, 0x66u,
  0x74u, 0x00u, 0x61u, 0x74u, 0x74u, 0x65u, 0x6Eu, 0x74u, 0x69u, 0x6Fu, 0x6Eu, 0x2Eu, 0x72u, 0x69u, 0x67u, 0x68u,
  0x74u, 0x00u, 0x61u, 0x74u, 0x74u, 0x65u, 0x6Eu, 0x74u, 0x69u, 0x6Fu, 0x6Eu, 0x2Eu, 0x64u, 0x6Fu, 0x77u, 0x6Eu,
  0x5Fu, 0x6Cu, 0x65u, 0x66u, 0x74u, 0x00u, 0x61u, 0x74u, 0x74u, 0x65u, 0x6Eu, 0x74u, 0x69u, 0x6Fu, 0x6Eu, 0x2Eu,
  0x64u, 0x6Fu, 0x77u, 0x6Eu, 0x00u, 0x61u, 0x74u, 0x74u, 0x65u, 0x6Eu, 0x74u, 0x69u, 0x6Fu, 0x6Eu, 0x2Eu, 0x64u,
  0x6Fu, 0x77u, 0x6Eu, 0x5Fu, 0x72u, 0x69u, 0x67u, 0x68u, 0x74u, 0x00u, 0x74u, 0x61u, 0x70u, 0x2Eu, 0x74u, 0x72u,
  0x61u, 0x6Eu, 0x73u, 0x69u, 0x74u, 0x69u, 0x6Fu, 0x6Eu, 0x2Eu, 0x63u, 0x65u, 0x6Eu, 0x74u, 0x65u, 0x72u, 0x00u,
  0x74u, 0x61u, 0x70u, 0x2Eu, 0x74u, 0x72u, 0x61u, 0x6Eu, 0x73u, 0x69u, 0x74u, 0x69u, 0x6Fu, 0x6Eu, 0x2Eu, 0x64u,
  0x6Fu, 0x77u, 0x6Eu, 0x00u, 0x74u, 0x61u, 0x70u, 0x2Eu, 0x74u, 0x72u, 0x61u, 0x6Eu, 0x73u, 0x69u, 0x74u, 0x69u,
  0x6Fu, 0x6Eu, 0x2Eu, 0x6Cu, 0x65u, 0x66u, 0x74u, 0x00u, 0x74u, 0x61u, 0x70u, 0x2Eu, 0x74u, 0x72u, 0x61u, 0x6Eu,
  0x73u, 0x69u, 0x74u, 0x69u, 0x6Fu, 0x6Eu, 0x2Eu, 0x72u, 0x69u, 0x67u, 0x68u, 0x74u, 0x00u, 0x74u, 0x61u, 0x70u,
  0x2Eu, 0x74u, 0x72u, 0x61u, 0x6Eu, 0x73u, 0x69u, 0x74u, 0x69u, 0x6Fu, 0x6Eu, 0x2Eu, 0x75u, 0x70u, 0x00u, 0x74u,
  0x61u, 0x70u, 0x2Eu, 0x65u, 0x64u, 0x67u, 0x65u, 0x2Eu, 0x61u, 0x6Cu, 0x65u, 0x72u, 0x74u, 0x2Eu, 0x63u, 0x61u,
  0x6Cu, 0x6Du, 0x2Eu, 0x63u, 0x65u, 0x6Eu, 0x74u, 0x65u, 0x72u, 0x00u, 0x74u, 0x61u, 0x70u, 0x2Eu, 0x65u, 0x64u,
  0x67u, 0x65u, 0x2Eu, 0x61u, 0x6Cu, 0x65u, 0x72u, 0x74u, 0x2Eu, 0x63u, 0x61u, 0x6Cu, 0x6Du, 0x2Eu, 0x64u, 0x6Fu,
  0x77u, 0x6Eu, 0x00u, 0x74u, 0x61u, 0x70u, 0x2Eu, 0x65u, 0x64u, 0x67u, 0x65u, 0x2Eu, 0x61u, 0x6Cu, 0x65u, 0x72u,
  0x74u, 0x2Eu, 0x63u, 0x61u, 0x6Cu, 0x6Du, 0x2Eu, 0x6Cu, 0x65u, 0x66u, 0x74u, 0x00u, 0x74u, 0x61u, 0x70u, 0x2Eu,
  0x65u, 0x64u, 0x67u, 0x65u, 0x2Eu, 0x61u, 0x6Cu, 0x65u, 0x72u, 0x74u, 0x2Eu, 0x63u, 0x61u, 0x6Cu, 0x6Du, 0x2Eu,
  0x72u, 0x69u, 0x67u, 0x68u, 0x74u, 0x00u, 0x74u, 0x61u, 0x70u, 0x2Eu, 0x65u, 0x64u, 0x67u, 0x65u, 0x2Eu, 0x61u,
  0x6Cu, 0x65u, 0x72u, 0x74u, 0x2Eu, 0x63u, 0x61u, 0x6Cu, 0x6Du, 0x2Eu, 0x75u, 0x70u, 0x00u, 0x74u, 0x61u, 0x70u,
  0x2Eu, 0x65u, 0x64u, 0x67u, 0x65u, 0x2Eu, 0x61u, 0x6Cu, 0x65u, 0x72u, 0x74u, 0x2Eu, 0x63u, 0x75u, 0x72u, 0x69u,
  0x6Fu, 0x75u, 0x73u, 0x2Eu, 0x63u, 0x65u, 0x6Eu, 0x74u, 0x65u, 0x72u, 0x00u, 0x74u, 0x61u, 0x70u, 0x2Eu, 0x65u,
  0x64u, 0x67u, 0x65u, 0x2Eu, 0x61u, 0x6Cu, 0x65u, 0x72u, 0x74u, 0x2Eu, 0x63u, 0x75u, 0x72u, 0x69u, 0x6Fu, 0x75u,
  0x73u, 0x2Eu, 0x64u, 0x6Fu, 0x77u, 0x6Eu, 0x00u, 0x74u, 0x61u, 0x70u, 0x2Eu, 0x65u, 0x64u, 0x67u, 0x65u, 0x2Eu,
  0x61u, 0x6Cu, 0x65u, 0x72u, 0x74u, 0x2Eu, 0x63u, 0x75u, 0x72u, 0x69u, 0x6Fu, 0x75u, 0x73u, 0x2Eu, 0x6Cu, 0x65u,
  0x66u, 0x74u, 0x00u, 0x74u, 0x61u, 0x70u, 0x2Eu, 0x65u, 0x64u, 0x67u, 0x65u, 0x2Eu, 0x61u, 0x6Cu, 0x65u, 0x72u,
  0x74u, 0x2Eu, 0x63u, 0x75u, 0x72u, 0x69u, 0x6Fu, 0x75u, 0x73u, 0x2Eu, 0x72u, 0x69u, 0x67u, 0x68u, 0x74u, 0x00u,
  0x74u, 0x61u, 0x70u, 0x2Eu, 0x65u, 0x64u, 0x67u, 0x65u, 0x2Eu, 0x61u, 0x6Cu, 0x65u, 0x72u, 0x74u, 0x2Eu, 0x63u,
  0x75u, 0x72u, 0x69u, 0x6Fu, 0x75u, 0x73u, 0x2Eu, 0x75u, 0x70u, 0x00u, 0x74u, 0x61u, 0x70u, 0x2Eu, 0x65u, 0x64u,
  0x67u, 0x65u, 0x2Eu, 0x61u, 0x6Cu, 0x65u, 0x72u, 0x74u, 0x2Eu, 0x66u, 0x6Fu, 0x63u, 0x75u, 0x73u, 0x65u, 0x64u,
  0x2Eu, 0x63u, 0x65u, 0x6Eu, 0x74u, 0x65u, 0x72u, 0x00u, 0x74u, 0x61u, 0x70u, 0x2Eu, 0x65u, 0x64u, 0x67u, 0x65u,
  0x2Eu, 0x61u, 0x6Cu, 0x65u, 0x72u, 0x74u, 0x2Eu, 0x66u, 0x6Fu, 0x63u, 0x75u, 0x73u, 0x65u, 0x64u, 0x2Eu, 0x64u,
  0x6Fu, 0x77u, 0x6Eu, 0x00u, 0x74u, 0x61u, 0x70u, 0x2Eu, 0x65u, 0x64u, 0x67u, 0x65u, 0x2Eu, 0x61u, 0x6Cu, 0x65u,
  0x72u, 0x74u, 0x2Eu, 0x66u, 0x6Fu, 0x63u, 0x75u, 0x73u, 0x65u, 0x64u, 0x2Eu, 0x6Cu, 0x65u, 0x66u, 0x74u, 0x00u,
  0x74u, 0x61u, 0x70u, 0x2Eu, 0x65u, 0x64u, 0x67u, 0x65u, 0x2Eu, 0x61u, 0x6Cu, 0x65u, 0x72u, 0x74u, 0x2Eu, 0x66u,
  0x6Fu, 0x63u, 0x75u, 0x73u, 0x65u, 0x64u, 0x2Eu, 0x72u, 0x69u, 0x67u, 0x68u, 0x74u, 0x00u, 0x74u, 0x61u, 0x70u,
  0x2Eu, 0x65u, 0x64u, 0x67u, 0x65u, 0x2Eu, 0x61u, 0x6Cu, 0x65u, 0x72u, 0x74u, 0x2Eu, 0x66u, 0x6Fu, 0x63u, 0x75u,
  0x73u, 0x65u, 0x64u, 0x2Eu, 0x75u, 0x70u, 0x00u, 0x74u, 0x61u, 0x70u, 0x2Eu, 0x65u, 0x64u, 0x67u, 0x65u, 0x2Eu,
  0x62u, 0x61u, 0x73u, 0x68u, 0x66u, 0x75u, 0x6Cu, 0x2Eu, 0x63u, 0x61u, 0x6Cu, 0x6Du, 0x2Eu, 0x63u, 0x65u, 0x6Eu,
  0x74u, 0x65u, 0x72u, 0x00u, 0x74u, 0x61u, 0x70u, 0x2Eu, 0x65u, 0x64u, 0x67u, 0x65u, 0x2Eu, 0x62u, 0x61u, 0x73u,
  0x68u, 0x66u, 0x75u, 0x6Cu, 0x2Eu, 0x63u, 0x61u, 0x6Cu, 0x6Du, 0x2Eu, 0x64u, 0x6Fu, 0x77u, 0x6Eu, 0x00u, 0x74u,
  0x61u, 0x70u, 0x2Eu, 0x65u, 0x64u, 0x67u, 0x65u, 0x2Eu, 0x62u, 0x61u, 0x73u, 0x68u, 0x66u, 0x75u, 0x6Cu, 0x2Eu,
  0x63u, 0x61u, 0x6Cu, 0x6Du, 0x2Eu, 0x6Cu, 0x65u, 0x66u, 0x74u, 0x00u, 0x74u, 0x61u, 0x70u, 0x2Eu, 0x65u, 0x64u,
  0x67u, 0x65u, 0x2Eu, 0x62u, 0x61u, 0x73u, 0x68u, 0x66u, 0x75u, 0x6Cu, 0x2Eu, 0x63u, 0x61u, 0x6Cu, 0x6Du, 0x2Eu,
  0x72u, 0x69u, 0x67u, 0x68u, 0x74u, 0x00u, 0x74u, 0x61u, 0x70u, 0x2Eu, 0x65u, 0x64u, 0x67u, 0x65u, 0x2Eu, 0x62u,
  0x61u, 0x73u, 0x68u, 0x66u, 0x75u, 0x6Cu, 0x2Eu, 0x63u, 0x61u, 0x6Cu, 0x6Du, 0x2Eu, 0x75u, 0x70u, 0x00u, 0x74u,
  0x61u, 0x70u, 0x2Eu, 0x65u, 0x64u, 0x67u, 0x65u, 0x2Eu, 0x62u, 0x61u, 0x73u, 0x68u, 0x66u, 0x75u, 0x6Cu, 0x2Eu,
  0x63u, 0x75u, 0x72u, 0x69u, 0x6Fu, 0x75u, 0x73u, 0x2Eu, 0x63u, 0x65u, 0x6Eu, 0x74u, 0x65u, 0x72u, 0x00u, 0x74u,
  0x61u, 0x70u, 0x2Eu, 0x65u, 0x64u, 0x67u, 0x65u, 0x2Eu, 0x62u, 0x61u, 0x73u, 0x68u, 0x66u, 0x75u, 0x6Cu, 0x2Eu,
  0x63u, 0x75u, 0x72u, 0x69u, 0x6Fu, 0x75u, 0x73u, 0x2Eu, 0x64u, 0x6Fu, 0x77u, 0x6Eu, 0x00u, 0x74u, 0x61u, 0x70u,
  0x2Eu, 0x65u, 0x64u, 0x67u, 0x65u, 0x2Eu, 0x62u, 0x61u, 0x73u, 0x68u, 0x66u, 0x75u, 0x6Cu, 0x2Eu, 0x63u, 0x75u,
  0x72u, 0x69u, 0x6Fu, 0x75u, 0x73u, 0x2Eu, 0x6Cu, 0x65u, 0x66u, 0x74u, 0x00u, 0x74u, 0x61u, 0x70u, 0x2Eu, 0x65u,
  0x64u, 0x67u, 0x65u, 0x2Eu, 0x62u, 0x61u, 0x73u, 0x68u, 0x66u, 0x75u, 0x6Cu, 0x2Eu, 0x63u, 0x75u, 0x72u, 0x69u,
  0x6Fu, 0x75u, 0x73u, 0x2Eu, 0x72u, 0x69u, 0x67u, 0x68u, 0x74u, 0x00u, 0x74u, 0x61u, 0x70u, 0x2Eu, 0x65u, 0x64u,
  0x67u, 0x65u, 0x2Eu, 0x62u, 0x61u, 0x73u, 0x68u, 0x66u, 0x75u, 0x6Cu, 0x2Eu, 0x63u, 0x75u, 0x72u, 0x69u, 0x6Fu,
  0x75u, 0x73u, 0x2Eu, 0x75u, 0x70u, 0x00u, 0x74u, 0x61u, 0x70u, 0x2Eu, 0x65u, 0x64u, 0x67u, 0x65u, 0x2Eu, 0x62u,
  0x61u, 0x73u, 0x68u, 0x66u, 0x75u, 0x6Cu, 0x2Eu, 0x77u, 0x61u, 0x72u, 0x6Du, 0x2Eu, 0x63u, 0x65u, 0x6Eu, 0x74u,
  0x65u, 0x72u, 0x00u, 0x74u, 0x61u, 0x70u, 0x2Eu, 0x65u, 0x64u, 0x67u, 0x65u, 0x2Eu, 0x62u, 0x61u, 0x73u, 0x68u,
  0x66u, 0x75u, 0x6Cu, 0x2Eu, 0x77u, 0x61u, 0x72u, 0x6Du, 0x2Eu, 0x64u, 0x6Fu, 0x77u, 0x6Eu, 0x00u, 0x74u, 0x61u,
  0x70u, 0x2Eu, 0x65u, 0x64u, 0x67u, 0x65u, 0x2Eu, 0x62u, 0x61u, 0x73u, 0x68u, 0x66u, 0x75u, 0x6Cu, 0x2Eu, 0x77u,
  0x61u, 0x72u, 0x6Du, 0x2Eu, 0x6Cu, 0x65u, 0x66u, 0x74u, 0x00u, 0x74u, 0x61u, 0x70u, 0x2Eu, 0x65u, 0x64u, 0x67u,
  0x65u, 0x2Eu, 0x62u, 0x61u, 0x73u, 0x68u, 0x66u, 0x75u, 0x6Cu, 0x2Eu, 0x77u, 0x61u, 0x72u, 0x6Du, 0x2Eu, 0x72u,
  0x69u, 0x67u, 0x68u, 0x74u, 0x00u, 0x74u, 0x61u, 0x70u, 0x2Eu, 0x65u, 0x64u, 0x67u, 0x65u, 0x2Eu, 0x62u, 0x61u,
  0x73u, 0x68u, 0x66u, 0x75u, 0x6Cu, 0x2Eu, 0x77u, 0x61u, 0x72u, 0x6Du, 0x2Eu, 0x75u, 0x70u, 0x00u, 0x74u, 0x61u,
  0x70u, 0x2Eu, 0x65u, 0x64u, 0x67u, 0x65u, 0x2Eu, 0x63u, 0x61u, 0x6Cu, 0x6Du, 0x2Eu, 0x63u, 0x75u, 0x72u, 0x69u,
  0x6Fu, 0x75u, 0x73u, 0x2Eu, 0x63u, 0x65u, 0x6Eu, 0x74u, 0x65u, 0x72u, 0x00u, 0x74u, 0x61u, 0x70u, 0x2Eu, 0x65u,
  0x64u, 0x67u, 0x65u, 0x2Eu, 0x63u, 0x61u, 0x6Cu, 0x6Du, 0x2Eu, 0x63u, 0x75u, 0x72u, 0x69u, 0x6Fu, 0x75u, 0x73u,
  0x2Eu, 0x64u, 0x6Fu, 0x77u, 0x6Eu, 0x00u, 0x74u, 0x61u, 0x70u, 0x2Eu, 0x65u, 0x64u, 0x67u, 0x65u, 0x2Eu, 0x63u,
  0x61u, 0x6Cu, 0x6Du, 0x2Eu, 0x63u, 0x75u, 0x72u, 0x69u, 0x6Fu, 0x75u, 0x73u, 0x2Eu, 0x6Cu, 0x65u, 0x66u, 0x74u,
  0x00u, 0x74u, 0x61u, 0x70u, 0x2Eu, 0x65u, 0x64u, 0x67u, 0x65u, 0x2Eu, 0x63u, 0x61u, 0x6Cu, 0x6Du, 0x2Eu, 0x63u,
  0x75u, 0x72u, 0x69u, 0x6Fu, 0x75u, 0x73u, 0x2Eu, 0x72u, 0x69u, 0x67u, 0x68u, 0x74u, 0x00u, 0x74u, 0x61u, 0x70u,
  0x2Eu, 0x65u, 0x64u, 0x67u, 0x65u, 0x2Eu, 0x63u, 0x61u, 0x6Cu, 0x6Du, 0x2Eu, 0x63u, 0x75u, 0x72u, 0x69u, 0x6Fu,
  0x75u, 0x73u, 0x2Eu, 0x75u, 0x70u, 0x00u, 0x74u, 0x61u, 0x70u, 0x2Eu, 0x65u, 0x64u, 0x67u, 0x65u, 0x2Eu, 0x63u,
  0x61u, 0x6Cu, 0x6Du, 0x2Eu, 0x73u, 0x6Cu, 0x65u, 0x65u, 0x70u, 0x79u, 0x2Eu, 0x63u, 0x65u, 0x6Eu, 0x74u, 0x65u,
  0x72u, 0x00u, 0x74u, 0x61u, 0x70u, 0x2Eu, 0x65u, 0x64u, 0x67u, 0x65u, 0x2Eu, 0x63u, 0x61u, 0x6Cu, 0x6Du, 0x2Eu,
  0x73u, 0x6Cu, 0x65u, 0x65u, 0x70u, 0x79u, 0x2Eu, 0x64u, 0x6Fu, 0x77u, 0x6Eu, 0x00u, 0x74u, 0x61u, 0x70u, 0x2Eu,
  0x65u, 0x64u, 0x67u, 0x65u, 0x2Eu, 0x63u, 0x61u, 0x6Cu, 0x6Du, 0x2Eu, 0x73u, 0x6Cu, 0x65u, 0x65u, 0x70u, 0x79u,
  0x2Eu, 0x6Cu, 0x65u, 0x66u, 0x74u, 0x00u, 0x74u, 0x61u, 0x70u, 0x2Eu, 0x65u, 0x64u, 0x67u, 0x65u, 0x2Eu, 0x63u,
  0x61u, 0x6Cu, 0x6Du, 0x2Eu, 0x73u, 0x6Cu, 0x65u, 0x65u, 0x70u, 0x79u, 0x2Eu, 0x72u, 0x69u, 0x67u, 0x68u, 0x74u,
  0x00u, 0x74u, 0x61u, 0x70u, 0x2Eu, 0x65u, 0x64u, 0x67u, 0x65u, 0x2Eu, 0x63u, 0x61u, 0x6Cu, 0x6Du, 0x2Eu, 0x73u,
  0x6Cu, 0x65u, 0x65u, 0x70u, 0x79u, 0x2Eu, 0x75u, 0x70u, 0x00u, 0x74u, 0x61u, 0x70u, 0x2Eu, 0x65u, 0x64u, 0x67u,
  0x65u, 0x2Eu, 0x63u, 0x61u, 0x6Cu, 0x6Du, 0x2Eu, 0x77u, 0x61u, 0x72u, 0x6Du, 0x2Eu, 0x63u, 0x65u, 0x6Eu, 0x74u,
  0x65u, 0x72u, 0x00u, 0x74u, 0x61u, 0x70u, 0x2Eu, 0x65u, 0x64u, 0x67u, 0x65u, 0x2Eu, 0x63u, 0x61u, 0x6Cu, 0x6Du,
  0x2Eu, 0x77u, 0x61u, 0x72u, 0x6Du, 0x2Eu, 0x64u, 0x6Fu, 0x77u, 0x6Eu, 0x00u, 0x74u, 0x61u, 0x70u, 0x2Eu, 0x65u,
  0x64u, 0x67u, 0x65u, 0x2Eu, 0x63u, 0x61u, 0x6Cu, 0x6Du, 0x2Eu, 0x77u, 0x61u, 0x72u, 0x6Du, 0x2Eu, 0x6Cu, 0x65u,
  0x66u, 0x74u, 0x00u, 0x74u, 0x61u, 0x70u, 0x2Eu, 0x65u, 0x64u, 0x67u, 0x65u, 0x2Eu, 0x63u, 0x61u, 0x6Cu, 0x6Du,
  0x2Eu, 0x77u, 0x61u, 0x72u, 0x6Du, 0x2Eu, 0x72u, 0x69u, 0x67u, 0x68u, 0x74u, 0x00u, 0x74u, 0x61u, 0x70u, 0x2Eu,
  0x65u, 0x64u, 0x67u, 0x65u, 0x2Eu, 0x63u, 0x61u, 0x6Cu, 0x6Du, 0x2Eu, 0x77u, 0x61u, 0x72u, 0x6Du, 0x2Eu, 0x75u,
  0x70u, 0x00u, 0x74u, 0x61u, 0x70u, 0x2Eu, 0x65u, 0x64u, 0x67u, 0x65u, 0x2Eu, 0x63u, 0x75u, 0x72u, 0x69u, 0x6Fu,
  0x75u, 0x73u, 0x2Eu, 0x61u, 0x6Cu, 0x65u, 0x72u, 0x74u, 0x2Eu, 0x63u, 0x65u, 0x6Eu, 0x74u, 0x65u, 0x72u, 0x00u,
  0x74u, 0x61u, 0x70u, 0x2Eu, 0x65u, 0x64u, 0x67u, 0x65u, 0x2Eu, 0x63u, 0x75u, 0x72u, 0x69u, 0x6Fu, 0x75u, 0x73u,
  0x2Eu, 0x61u, 0x6Cu, 0x65u, 0x72u, 0x74u, 0x2Eu, 0x64u, 0x6Fu, 0x77u, 0x6Eu, 0x00u, 0x74u, 0x61u, 0x70u, 0x2Eu,
  0x65u, 0x64u, 0x67u, 0x65u, 0x2Eu, 0x63u, 0x75u, 0x72u, 0x69u, 0x6Fu, 0x75u, 0x73u, 0x2Eu, 0x61u, 0x6Cu, 0x65u,
  0x72u, 0x74u, 0x2Eu, 0x6Cu, 0x65u, 0x66u, 0x74u, 0x00u, 0x74u, 0x61u, 0x70u, 0x2Eu, 0x65u, 0x64u, 0x67u, 0x65u,
  0x2Eu, 0x63u, 0x75u, 0x72u, 0x69u, 0x6Fu, 0x75u, 0x73u, 0x2Eu, 0x61u, 0x6Cu, 0x65u, 0x72u, 0x74u, 0x2Eu, 0x72u,
  0x69u, 0x67u, 0x68u, 0x74u, 0x00u, 0x74u, 0x61u, 0x70u, 0x2Eu, 0x65u, 0x64u, 0x67u, 0x65u, 0x2Eu, 0x63u, 0x75u,
  0x72u, 0x69u, 0x6Fu, 0x75u, 0x73u, 0x2Eu, 0x61u, 0x6Cu, 0x65u, 0x72u, 0x74u, 0x2Eu, 0x75u, 0x70u, 0x00u, 0x74u,
  0x61u, 0x70u, 0x2Eu, 0x65u, 0x64u, 0x67u, 0x65u, 0x2Eu, 0x63u, 0x75u, 0x72u, 0x69u, 0x6Fu, 0x75u, 0x73u, 0x2Eu,
  0x63u, 0x61u, 0x6Cu, 0x6Du, 0x2Eu, 0x63u, 0x65u, 0x6Eu, 0x74u, 0x65u, 0x72u, 0x00u, 0x74u, 0x61u, 0x70u, 0x2Eu,
  0x65u, 0x64u, 0x67u, 0x65u, 0x2Eu, 0x63u, 0x75u, 0x72u, 0x69u, 0x6Fu, 0x75u, 0x73u, 0x2Eu, 0x63u, 0x61u, 0x6Cu,
  0x6Du, 0x2Eu, 0x64u, 0x6Fu, 0x77u, 0x6Eu, 0x00u, 0x74u, 0x61u, 0x70u, 0x2Eu, 0x65u, 0x64u, 0x67u, 0x65u, 0x2Eu,
  0x63u, 0x75u, 0x72u, 0x69u, 0x6Fu, 0x75u, 0x73u, 0x2Eu, 0x63u, 0x61u, 0x6Cu, 0x6Du, 0x2Eu, 0x6Cu, 0x65u, 0x66u,
  0x74u, 0x00u, 0x74u, 0x61u, 0x70u, 0x2Eu, 0x65u, 0x64u, 0x67u, 0x65u, 0x2Eu, 0x63u, 0x75u, 0x72u, 0x69u, 0x6Fu,
  0x75u, 0x73u, 0x2Eu, 0x63u, 0x61u, 0x6Cu, 0x6Du, 0x2Eu, 0x72u, 0x69u, 0x67u, 0x68u, 0x74u, 0x00u, 0x74u, 0x61u,
  0x70u, 0x2Eu, 0x65u, 0x64u, 0x67u, 0x65u, 0x2Eu, 0x63u, 0x75u, 0x72u, 0x69u, 0x6Fu, 0x75u, 0x73u, 0x2Eu, 0x63u,
  0x61u, 0x6Cu, 0x6Du, 0x2Eu, 0x75u, 0x70u, 0x00u, 0x74u, 0x61u, 0x70u, 0x2Eu, 0x65u, 0x64u, 0x67u, 0x65u, 0x2Eu,
  0x63u, 0x75u, 0x72u, 0x69u, 0x6Fu, 0x75u, 0x73u, 0x2Eu, 0x66u, 0x6Fu, 0x63u, 0x75u, 0x73u, 0x65u, 0x64u, 0x2Eu,
  0x63u, 0x65u, 0x6Eu, 0x74u, 0x65u, 0x72u, 0x00u, 0x74u, 0x61u, 0x70u, 0x2Eu, 0x65u, 0x64u, 0x67u, 0x65u, 0x2Eu,
  0x63u, 0x75u, 0x72u, 0x69u, 0x6Fu, 0x75u, 0x73u, 0x2Eu, 0x66u, 0x6Fu, 0x63u, 0x75u, 0x73u, 0x65u, 0x64u, 0x2Eu,
  0x64u, 0x6Fu, 0x77u, 0x6Eu, 0x00u, 0x74u, 0x61u, 0x70u, 0x2Eu, 0x65u, 0x64u, 0x67u, 0x65u, 0x2Eu, 0x63u, 0x75u,
  0x72u, 0x69u, 0x6Fu, 0x75u, 0x73u, 0x2Eu, 0x66u, 0x6Fu, 0x63u, 0x75u, 0x73u, 0x65u, 0x64u, 0x2Eu, 0x6Cu, 0x65u,
  0x66u, 0x74u, 0x00u, 0x74u, 0x61u, 0x70u, 0x2Eu, 0x65u, 0x64u, 0x67u, 0x65u, 0x2Eu, 0x63u, 0x75u, 0x72u, 0x69u,
  0x6Fu, 0x75u, 0x73u, 0x2Eu, 0x66u, 0x6Fu, 0x63u, 0x75u, 0x73u, 0x65u, 0x64u, 0x2Eu, 0x72u, 0x69u, 0x67u, 0x68u,
  0x74u, 0x00u, 0x74u, 0x61u, 0x70u, 0x2Eu, 0x65u, 0x64u, 0x67u, 0x65u, 0x2Eu, 0x63u, 0x75u, 0x72u, 0x69u, 0x6Fu,
  0x75u, 0x73u, 0x2Eu, 0x66u, 0x6Fu, 0x63u, 0x75u, 0x73u, 0x65u, 0x64u, 0x2Eu, 0x75u, 0x70u, 0x00u, 0x74u, 0x61u,
  0x70u, 0x2Eu, 0x65u, 0x64u, 0x67u, 0x65u, 0x2Eu, 0x63u, 0x75u, 0x72u, 0x69u, 0x6Fu, 0x75u, 0x73u, 0x2Eu, 0x70u,
  0x6Cu, 0x61u, 0x79u, 0x66u, 0x75u, 0x6Cu, 0x2Eu, 0x63u, 0x65u, 0x6Eu, 0x74u, 0x65u, 0x72u, 0x00u, 0x74u, 0x61u,
  0x70u, 0x2Eu, 0x65u, 0x64u, 0x67u, 0x65u, 0x2Eu, 0x63u, 0x75u, 0x72u, 0x69u, 0x6Fu, 0x75u, 0x73u, 0x2Eu, 0x70u,
  0x6Cu, 0x61u, 0x79u, 0x66u, 0x75u, 0x6Cu, 0x2Eu, 0x64u, 0x6Fu, 0x77u, 0x6Eu, 0x00u, 0x74u, 0x61u, 0x70u, 0x2Eu,
  0x65u, 0x64u, 0x67u, 0x65u, 0x2Eu, 0x63u, 0x75u, 0x72u, 0x69u, 0x6Fu, 0x75u, 0x73u, 0x2Eu, 0x70u, 0x6Cu, 0x61u,
  0x79u, 0x66u, 0x75u, 0x6Cu, 0x2Eu, 0x6Cu, 0x65u, 0x66u, 0x74u, 0x00u, 0x74u, 0x61u, 0x70u, 0x2Eu, 0x65u, 0x64u,
  0x67u, 0x65u, 0x2Eu, 0x63u, 0x75u, 0x72u, 0x69u, 0x6Fu, 0x75u, 0x73u, 0x2Eu, 0x70u, 0x6Cu, 0x61u, 0x79u, 0x66u,
  0x75u, 0x6Cu, 0x2Eu, 0x72u, 0x69u, 0x67u, 0x68u, 0x74u, 0x00u, 0x74u, 0x61u, 0x70u, 0x2Eu, 0x65u, 0x64u, 0x67u,
  0x65u, 0x2Eu, 0x63u, 0x75u, 0x72u, 0x69u, 0x6Fu, 0x75u, 0x73u, 0x2Eu, 0x70u, 0x6Cu, 0x61u, 0x79u, 0x66u, 0x75u,
  0x6Cu, 0x2Eu, 0x75u, 0x70u, 0x00u, 0x74u, 0x61u, 0x70u, 0x2Eu, 0x65u, 0x64u, 0x67u, 0x65u, 0x2Eu, 0x63u, 0x75u,
  0x72u, 0x69u, 0x6Fu, 0x75u, 0x73u, 0x2Eu, 0x74u, 0x68u, 0x6Fu, 0x75u, 0x67u, 0x68u, 0x74u, 0x66u, 0x75u, 0x6Cu,
  0x2Eu, 0x63u, 0x65u, 0x6Eu, 0x74u, 0x65u, 0x72u, 0x00u, 0x74u, 0x61u, 0x70u, 0x2Eu, 0x65u, 0x64u, 0x67u, 0x65u,
  0x2Eu, 0x63u, 0x75u, 0x72u, 0x69u, 0x6Fu, 0x75u, 0x73u, 0x2Eu, 0x74u, 0x68u, 0x6Fu, 0x75u, 0x67u, 0x68u, 0x74u,
  0x66u, 0x75u, 0x6Cu, 0x2Eu, 0x64u, 0x6Fu, 0x77u, 0x6Eu, 0x00u, 0x74u, 0x61u, 0x70u, 0x2Eu, 0x65u, 0x64u, 0x67u,
  0x65u, 0x2Eu, 0x63u, 0x75u, 0x72u, 0x69u, 0x6Fu, 0x75u, 0x73u, 0x2Eu, 0x74u, 0x68u, 0x6Fu, 0x75u, 0x67u, 0x68u,
  0x74u, 0x66u, 0x75u, 0x6Cu, 0x2Eu, 0x6Cu, 0x65u, 0x66u, 0x74u, 0x00u, 0x74u, 0x61u, 0x70u, 0x2Eu, 0x65u, 0x64u,
  0x67u, 0x65u, 0x2Eu, 0x63u, 0x75u, 0x72u, 0x69u, 0x6Fu, 0x75u, 0x73u, 0x2Eu, 0x74u, 0x68u, 0x6Fu, 0x75u, 0x67u,
  0x68u, 0x74u, 0x66u, 0x75u, 0x6Cu, 0x2Eu, 0x72u, 0x69u, 0x67u, 0x68u, 0x74u, 0x00u, 0x74u, 0x61u, 0x70u, 0x2Eu,
  0x65u, 0x64u, 0x67u, 0x65u, 0x2Eu, 0x63u, 0x75u, 0x72u, 0x69u, 0x6Fu, 0x75u, 0x73u, 0x2Eu, 0x74u, 0x68u, 0x6Fu,
  0x75u, 0x67u, 0x68u, 0x74u, 0x66u, 0x75u, 0x6Cu, 0x2Eu, 0x75u, 0x70u, 0x00u, 0x74u, 0x61u, 0x70u, 0x2Eu, 0x65u,
  0x64u, 0x67u, 0x65u, 0x2Eu, 0x63u, 0x75u, 0x72u, 0x69u, 0x6Fu, 0x75u, 0x73u, 0x2Eu, 0x77u, 0x61u, 0x72u, 0x6Du,
  0x2Eu, 0x63u, 0x65u, 0x6Eu, 0x74u, 0x65u, 0x72u, 0x00u, 0x74u, 0x61u, 0x70u, 0x2Eu, 0x65u, 0x64u, 0x67u, 0x65u,
  0x2Eu, 0x63u, 0x75u, 0x72u, 0x69u, 0x6Fu, 0x75u, 0x73u, 0x2Eu, 0x77u, 0x61u, 0x72u, 0x6Du, 0x2Eu, 0x64u, 0x6Fu,
  0x77u, 0x6Eu, 0x00u, 0x74u, 0x61u, 0x70u, 0x2Eu, 0x65u, 0x64u, 0x67u, 0x65u, 0x2Eu, 0x63u, 0x75u, 0x72u, 0x69u,
  0x6Fu, 0x75u, 0x73u, 0x2Eu, 0x77u, 0x61u, 0x72u, 0x6Du, 0x2Eu, 0x6Cu, 0x65u, 0x66u, 0x74u, 0x00u, 0x74u, 0x61u,
  0x70u, 0x2Eu, 0x65u, 0x64u, 0x67u, 0x65u, 0x2Eu, 0x63u, 0x75u, 0x72u, 0x69u, 0x6Fu, 0x75u, 0x73u, 0x2Eu, 0x77u,
  0x61u, 0x72u, 0x6Du, 0x2Eu, 0x72u, 0x69u, 0x67u, 0x68u, 0x74u, 0x00u, 0x74u, 0x61u, 0x70u, 0x2Eu, 0x65u, 0x64u,
  0x67u, 0x65u, 0x2Eu, 0x63u, 0x75u, 0x72u, 0x69u, 0x6Fu, 0x75u, 0x73u, 0x2Eu, 0x77u, 0x61u, 0x72u, 0x6Du, 0x2Eu,
  0x75u, 0x70u, 0x00u, 0x74u, 0x61u, 0x70u, 0x2Eu, 0x65u, 0x64u, 0x67u, 0x65u, 0x2Eu, 0x64u, 0x65u, 0x6Cu, 0x69u,
  0x67u, 0x68u, 0x74u, 0x65u, 0x64u, 0x2Eu, 0x63u, 0x61u, 0x6Cu, 0x6Du, 0x2Eu, 0x63u, 0x65u, 0x6Eu, 0x74u, 0x65u,
  0x72u, 0x00u, 0x74u, 0x61u, 0x70u, 0x2Eu, 0x65u, 0x64u, 0x67u, 0x65u, 0x2Eu, 0x64u, 0x65u, 0x6Cu, 0x69u, 0x67u,
  0x68u, 0x74u, 0x65u, 0x64u, 0x2Eu, 0x63u, 0x61u, 0x6Cu, 0x6Du, 0x2Eu, 0x64u, 0x6Fu, 0x77u, 0x6Eu, 0x00u, 0x74u,
  0x61u, 0x70u, 0x2Eu, 0x65u, 0x64u, 0x67u, 0x65u, 0x2Eu, 0x64u, 0x65u, 0x6Cu, 0x69u, 0x67u, 0x68u, 0x74u, 0x65u,
  0x64u, 0x2Eu, 0x63u, 0x61u, 0x6Cu, 0x6Du, 0x2Eu, 0x6Cu, 0x65u, 0x66u, 0x74u, 0x00u, 0x74u, 0x61u, 0x70u, 0x2Eu,
  0x65u, 0x64u, 0x67u, 0x65u, 0x2Eu, 0x64u, 0x65u, 0x6Cu, 0x69u, 0x67u, 0x68u, 0x74u, 0x65u, 0x64u, 0x2Eu, 0x63u,
  0x61u, 0x6Cu, 0x6Du, 0x2Eu, 0x72u, 0x69u, 0x67u, 0x68u, 0x74u, 0x00u, 0x74u, 0x61u, 0x70u, 0x2Eu, 0x65u, 0x64u,
  0x67u, 0x65u, 0x2Eu, 0x64u, 0x65u, 0x6Cu, 0x69u, 0x67u, 0x68u, 0x74u, 0x65u, 0x64u, 0x2Eu, 0x63u, 0x61u, 0x6Cu,
  0x6Du, 0x2Eu, 0x75u, 0x70u, 0x00u, 0x74u, 0x61u, 0x70u, 0x2Eu, 0x65u, 0x64u, 0x67u, 0x65u, 0x2Eu, 0x64u, 0x65u,
  0x6Cu, 0x69u, 0x67u, 0x68u, 0x74u, 0x65u, 0x64u, 0x2Eu, 0x70u, 0x6Cu, 0x61u, 0x79u, 0x66u, 0x75u, 0x6Cu, 0x2Eu,
  0x63u, 0x65u, 0x6Eu, 0x74u, 0x65u, 0x72u, 0x00u, 0x74u, 0x61u, 0x70u, 0x2Eu, 0x65u, 0x64u, 0x67u, 0x65u, 0x2Eu,
  0x64u, 0x65u, 0x6Cu, 0x69u, 0x67u, 0x68u, 0x74u, 0x65u, 0x64u, 0x2Eu, 0x70u, 0x6Cu, 0x61u, 0x79u, 0x66u, 0x75u,
  0x6Cu, 0x2Eu, 0x64u, 0x6Fu, 0x77u, 0x6Eu, 0x00u, 0x74u, 0x61u, 0x70u, 0x2Eu, 0x65u, 0x64u, 0x67u, 0x65u, 0x2Eu,
  0x64u, 0x65u, 0x6Cu, 0x69u, 0x67u, 0x68u, 0x74u, 0x65u, 0x64u, 0x2Eu, 0x70u, 0x6Cu, 0x61u, 0x79u, 0x66u, 0x75u,
  0x6Cu, 0x2Eu, 0x6Cu, 0x65u, 0x66u, 0x74u, 0x00u, 0x74u, 0x61u, 0x70u, 0x2Eu, 0x65u, 0x64u, 0x67u, 0x65u, 0x2Eu,
  0x64u, 0x65u, 0x6Cu, 0x69u, 0x67u, 0x68u, 0x74u, 0x65u, 0x64u, 0x2Eu, 0x70u, 0x6Cu, 0x61u, 0x79u, 0x66u, 0x75u,
  0x6Cu, 0x2Eu, 0x72u, 0x69u, 0x67u, 0x68u, 0x74u, 0x00u, 0x74u, 0x61u, 0x70u, 0x2Eu, 0x65u, 0x64u, 0x67u, 0x65u,
  0x2Eu, 0x64u, 0x65u, 0x6Cu, 0x69u, 0x67u, 0x68u, 0x74u, 0x65u, 0x64u, 0x2Eu, 0x70u, 0x6Cu, 0x61u, 0x79u, 0x66u,
  0x75u, 0x6Cu, 0x2Eu, 0x75u, 0x70u, 0x00u, 0x74u, 0x61u, 0x70u, 0x2Eu, 0x65u, 0x64u, 0x67u, 0x65u, 0x2Eu, 0x64u,
  0x65u, 0x6Cu, 0x69u, 0x67u, 0x68u, 0x74u, 0x65u, 0x64u, 0x2Eu, 0x77u, 0x61u, 0x72u, 0x6Du, 0x2Eu, 0x63u, 0x65u,
  0x6Eu, 0x74u, 0x65u, 0x72u, 0x00u, 0x74u, 0x61u, 0x70u, 0x2Eu, 0x65u, 0x64u, 0x67u, 0x65u, 0x2Eu, 0x64u, 0x65u,
  0x6Cu, 0x69u, 0x67u, 0x68u, 0x74u, 0x65u, 0x64u, 0x2Eu, 0x77u, 0x61u, 0x72u, 0x6Du, 0x2Eu, 0x64u, 0x6Fu, 0x77u,
  0x6Eu, 0x00u, 0x74u, 0x61u, 0x70u, 0x2Eu, 0x65u, 0x64u, 0x67u, 0x65u, 0x2Eu, 0x64u, 0x65u, 0x6Cu, 0x69u, 0x67u,
  0x68u, 0x74u, 0x65u, 0x64u, 0x2Eu, 0x77u, 0x61u, 0x72u, 0x6Du, 0x2Eu, 0x6Cu, 0x65u, 0x66u, 0x74u, 0x00u, 0x74u,
  0x61u, 0x70u, 0x2Eu, 0x65u, 0x64u, 0x67u, 0x65u, 0x2Eu, 0x64u, 0x65u, 0x6Cu, 0x69u, 0x67u, 0x68u, 0x74u, 0x65u,
  0x64u, 0x2Eu, 0x77u, 0x61u, 0x72u, 0x6Du, 0x2Eu, 0x72u, 0x69u, 0x67u, 0x68u, 0x74u, 0x00u, 0x74u, 0x61u, 0x70u,
  0x2Eu, 0x65u, 0x64u, 0x67u, 0x65u, 0x2Eu, 0x64u, 0x65u, 0x6Cu, 0x69u, 0x67u, 0x68u, 0x74u, 0x65u, 0x64u, 0x2Eu,
  0x77u, 0x61u, 0x72u, 0x6Du, 0x2Eu, 0x75u, 0x70u, 0x00u, 0x74u, 0x61u, 0x70u, 0x2Eu, 0x65u, 0x64u, 0x67u, 0x65u,
  0x2Eu, 0x66u, 0x6Fu, 0x63u, 0x75u, 0x73u, 0x65u, 0x64u, 0x2Eu, 0x61u, 0x6Cu, 0x65u, 0x72u, 0x74u, 0x2Eu, 0x63u,
  0x65u, 0x6Eu, 0x74u, 0x65u, 0x72u, 0x00u, 0x74u, 0x61u, 0x70u, 0x2Eu, 0x65u, 0x64u, 0x67u, 0x65u, 0x2Eu, 0x66u,
  0x6Fu, 0x63u, 0x75u, 0x73u, 0x65u, 0x64u, 0x2Eu, 0x61u, 0x6Cu, 0x65u, 0x72u, 0x74u, 0x2Eu, 0x64u, 0x6Fu, 0x77u,
  0x6Eu, 0x00u, 0x74u, 0x61u, 0x70u, 0x2Eu, 0x65u, 0x64u, 0x67u, 0x65u, 0x2Eu, 0x66u, 0x6Fu, 0x63u, 0x75u, 0x73u,
  0x65u, 0x64u, 0x2Eu, 0x61u, 0x6Cu, 0x65u, 0x72u, 0x74u, 0x2Eu, 0x6Cu, 0x65u, 0x66u, 0x74u, 0x00u, 0x74u, 0x61u,
  0x70u, 0x2Eu, 0x65u, 0x64u, 0x67u, 0x65u, 0x2Eu, 0x66u, 0x6Fu, 0x63u, 0x75u, 0x73u, 0x65u, 0x64u, 0x2Eu, 0x61u,
  0x6Cu, 0x65u, 0x72u, 0x74u, 0x2Eu, 0x72u, 0x69u, 0x67u, 0x68u, 0x74u, 0x00u, 0x74u, 0x61u, 0x70u, 0x2Eu, 0x65u,
  0x64u, 0x67u, 0x65u, 0x2Eu, 0x66u, 0x6Fu, 0x63u, 0x75u, 0x73u, 0x65u, 0x64u, 0x2Eu, 0x61u, 0x6Cu, 0x65u, 0x72u,
  0x74u, 0x2Eu, 0x75u, 0x70u, 0x00u, 0x74u, 0x61u, 0x70u, 0x2Eu, 0x65u, 0x64u, 0x67u, 0x65u, 0x2Eu, 0x66u, 0x6Fu,
  0x63u, 0x75u, 0x73u, 0x65u, 0x64u, 0x2Eu, 0x63u, 0x61u, 0x6Cu, 0x6Du, 0x2Eu, 0x63u, 0x65u, 0x6Eu, 0x74u, 0x65u,
  0x72u, 0x00u, 0x74u, 0x61u, 0x70u, 0x2Eu, 0x65u, 0x64u, 0x67u, 0x65u, 0x2Eu, 0x66u, 0x6Fu, 0x63u, 0x75u, 0x73u,
  0x65u, 0x64u, 0x2Eu, 0x63u, 0x61u, 0x6Cu, 0x6Du, 0x2Eu, 0x64u, 0x6Fu, 0x77u, 0x6Eu, 0x00u, 0x74u, 0x61u, 0x70u,
  0x2Eu, 0x65u, 0x64u, 0x67u, 0x65u, 0x2Eu, 0x66u, 0x6Fu, 0x63u, 0x75u, 0x73u, 0x65u, 0x64u, 0x2Eu, 0x63u, 0x61u,
  0x6Cu, 0x6Du, 0x2Eu, 0x6Cu, 0x65u, 0x66u, 0x74u, 0x00u, 0x74u, 0x61u, 0x70u, 0x2Eu, 0x65u, 0x64u, 0x67u, 0x65u,
  0x2Eu, 0x66u, 0x6Fu, 0x63u, 0x75u, 0x73u, 0x65u, 0x64u, 0x2Eu, 0x63u, 0x61u, 0x6Cu, 0x6Du, 0x2Eu, 0x72u, 0x69u,
  0x67u, 0x68u, 0x74u, 0x00u, 0x74u, 0x61u, 0x70u, 0x2Eu, 0x65u, 0x64u, 0x67u, 0x65u, 0x2Eu, 0x66u, 0x6Fu, 0x63u,
  0x75u, 0x73u, 0x65u, 0x64u, 0x2Eu, 0x63u, 0x61u, 0x6Cu, 0x6Du, 0x2Eu, 0x75u, 0x70u, 0x00u, 0x74u, 0x61u, 0x70u,
  0x2Eu, 0x65u, 0x64u, 0x67u, 0x65u, 0x2Eu, 0x66u, 0x6Fu, 0x63u, 0x75u, 0x73u, 0x65u, 0x64u, 0x2Eu, 0x63u, 0x75u,
  0x72u, 0x69u, 0x6Fu, 0x75u, 0x73u, 0x2Eu, 0x63u, 0x65u, 0x6Eu, 0x74u, 0x65u, 0x72u, 0x00u, 0x74u, 0x61u, 0x70u,
  0x2Eu, 0x65u, 0x64u, 0x67u, 0x65u, 0x2Eu, 0x66u, 0x6Fu, 0x63u, 0x75u, 0x73u, 0x65u, 0x64u, 0x2Eu, 0x63u, 0x75u,
  0x72u, 0x69u, 0x6Fu, 0x75u, 0x73u, 0x2Eu, 0x64u, 0x6Fu, 0x77u, 0x6Eu, 0x00u, 0x74u, 0x61u, 0x70u, 0x2Eu, 0x65u,
  0x64u, 0x67u, 0x65u, 0x2Eu, 0x66u, 0x6Fu, 0x63u, 0x75u, 0x73u, 0x65u, 0x64u, 0x2Eu, 0x63u, 0x75u, 0x72u, 0x69u,
  0x6Fu, 0x75u, 0x73u, 0x2Eu, 0x6Cu, 0x65u, 0x66u, 0x74u, 0x00u, 0x74u, 0x61u, 0x70u, 0x2Eu, 0x65u, 0x64u, 0x67u,
  0x65u, 0x2Eu, 0x66u, 0x6Fu, 0x63u, 0x75u, 0x73u, 0x65u, 0x64u, 0x2Eu, 0x63u, 0x75u, 0x72u, 0x69u, 0x6Fu, 0x75u,
  0x73u, 0x2Eu, 0x72u, 0x69u, 0x67u, 0x68u, 0x74u, 0x00u, 0x74u, 0x61u, 0x70u, 0x2Eu, 0x65u, 0x64u, 0x67u, 0x65u,
  0x2Eu, 0x66u, 0x6Fu, 0x63u, 0x75u, 0x73u, 0x65u, 0x64u, 0x2Eu, 0x63u, 0x75u, 0x72u, 0x69u, 0x6Fu, 0x75u, 0x73u,
  0x2Eu, 0x75u, 0x70u, 0x00u, 0x74u, 0x61u, 0x70u, 0x2Eu, 0x65u, 0x64u, 0x67u, 0x65u, 0x2Eu, 0x66u, 0x6Fu, 0x63u,
  0x75u, 0x73u, 0x65u, 0x64u, 0x2Eu, 0x74u, 0x68u, 0x6Fu, 0x75u, 0x67u, 0x68u, 0x74u, 0x66u, 0x75u, 0x6Cu, 0x2Eu,
  0x63u, 0x65u, 0x6Eu, 0x74u, 0x65u, 0x72u, 0x00u, 0x74u, 0x61u, 0x70u, 0x2Eu, 0x65u, 0x64u, 0x67u, 0x65u, 0x2Eu,
  0x66u, 0x6Fu, 0x63u, 0x75u, 0x73u, 0x65u, 0x64u, 0x2Eu, 0x74u, 0x68u, 0x6Fu, 0x75u, 0x67u, 0x68u, 0x74u, 0x66u,
  0x75u, 0x6Cu, 0x2Eu, 0x64u, 0x6Fu, 0x77u, 0x6Eu, 0x00u, 0x74u, 0x61u, 0x70u, 0x2Eu, 0x65u, 0x64u, 0x67u, 0x65u,
  0x2Eu, 0x66u, 0x6Fu, 0x63u, 0x75u, 0x73u, 0x65u, 0x64u, 0x2Eu, 0x74u, 0x68u, 0x6Fu, 0x75u, 0x67u, 0x68u, 0x74u,
  0x66u, 0x75u, 0x6Cu, 0x2Eu, 0x6Cu, 0x65u, 0x66u, 0x74u, 0x00u, 0x74u, 0x61u, 0x70u, 0x2Eu, 0x65u, 0x64u, 0x67u,
  0x65u, 0x2Eu, 0x66u, 0x6Fu, 0x63u, 0x75u, 0x73u, 0x65u, 0x64u, 0x2Eu, 0x74u, 0x68u, 0x6Fu, 0x75u, 0x67u, 0x68u,
  0x74u, 0x66u, 0x75u, 0x6Cu, 0x2Eu, 0x72u, 0x69u, 0x67u, 0x68u, 0x74u, 0x00u, 0x74u, 0x61u, 0x70u, 0x2Eu, 0x65u,
  0x64u, 0x67u, 0x65u, 0x2Eu, 0x66u, 0x6Fu, 0x63u, 0x75u, 0x73u, 0x65u, 0x64u, 0x2Eu, 0x74u, 0x68u, 0x6Fu, 0x75u,
  0x67u, 0x68u, 0x74u, 0x66u, 0x75u, 0x6Cu, 0x2Eu, 0x75u, 0x70u, 0x00u, 0x74u, 0x61u, 0x70u, 0x2Eu, 0x65u, 0x64u,
  0x67u, 0x65u, 0x2Eu, 0x70u, 0x6Cu, 0x61u, 0x79u, 0x66u, 0x75u, 0x6Cu, 0x2Eu, 0x63u, 0x61u, 0x6Cu, 0x6Du, 0x2Eu,
  0x63u, 0x65u, 0x6Eu, 0x74u, 0x65u, 0x72u, 0x00u, 0x74u, 0x61u, 0x70u, 0x2Eu, 0x65u, 0x64u, 0x67u, 0x65u, 0x2Eu,
  0x70u, 0x6Cu, 0x61u, 0x79u, 0x66u, 0x75u, 0x6Cu, 0x2Eu, 0x63u, 0x61u, 0x6Cu, 0x6Du, 0x2Eu, 0x64u, 0x6Fu, 0x77u,
  0x6Eu, 0x00u, 0x74u, 0x61u, 0x70u, 0x2Eu, 0x65u, 0x64u, 0x67u, 0x65u, 0x2Eu, 0x70u, 0x6Cu, 0x61u, 0x79u, 0x66u,
  0x75u, 0x6Cu, 0x2Eu, 0x63u, 0x61u, 0x6Cu, 0x6Du, 0x2Eu, 0x6Cu, 0x65u, 0x66u, 0x74u, 0x00u, 0x74u, 0x61u, 0x70u,
  0x2Eu, 0x65u, 0x64u, 0x67u, 0x65u, 0x2Eu, 0x70u, 0x6Cu, 0x61u, 0x79u, 0x66u, 0x75u, 0x6Cu, 0x2Eu, 0x63u, 0x61u,
  0x6Cu, 0x6Du, 0x2Eu, 0x72u, 0x69u, 0x67u, 0x68u, 0x74u, 0x00u, 0x74u, 0x61u, 0x70u, 0x2Eu, 0x65u, 0x64u, 0x67u,
  0x65u, 0x2Eu, 0x70u, 0x6Cu, 0x61u, 0x79u, 0x66u, 0x75u, 0x6Cu, 0x2Eu, 0x63u, 0x61u, 0x6Cu, 0x6Du, 0x2Eu, 0x75u,
  0x70u, 0x00u, 0x74u, 0x61u, 0x70u, 0x2Eu, 0x65u, 0x64u, 0x67u, 0x65u, 0x2Eu, 0x70u, 0x6Cu, 0x61u, 0x79u, 0x66u,
  0x75u, 0x6Cu, 0x2Eu, 0x63u, 0x75u, 0x72u, 0x69u, 0x6Fu, 0x75u, 0x73u, 0x2Eu, 0x63u, 0x65u, 0x6Eu, 0x74u, 0x65u,
  0x72u, 0x00u, 0x74u, 0x61u, 0x70u, 0x2Eu, 0x65u, 0x64u, 0x67u, 0x65u, 0x2Eu, 0x70u, 0x6Cu, 0x61u, 0x79u, 0x66u,
  0x75u, 0x6Cu, 0x2Eu, 0x63u, 0x75u, 0x72u, 0x69u, 0x6Fu, 0x75u, 0x73u, 0x2Eu, 0x64u, 0x6Fu, 0x77u, 0x6Eu, 0x00u,
  0x74u, 0x61u, 0x70u, 0x2Eu, 0x65u, 0x64u, 0x67u, 0x65u, 0x2Eu, 0x70u, 0x6Cu, 0x61u, 0x79u, 0x66u, 0x75u, 0x6Cu,
  0x2Eu, 0x63u, 0x75u, 0x72u, 0x69u, 0x6Fu, 0x75u, 0x73u, 0x2Eu, 0x6Cu, 0x65u, 0x66u, 0x74u, 0x00u, 0x74u, 0x61u,
  0x70u, 0x2Eu, 0x65u, 0x64u, 0x67u, 0x65u, 0x2Eu, 0x70u, 0x6Cu, 0x61u, 0x79u, 0x66u, 0x75u, 0x6Cu, 0x2Eu, 0x63u,
  0x75u, 0x72u, 0x69u, 0x6Fu, 0x75u, 0x73u, 0x2Eu, 0x72u, 0x69u, 0x67u, 0x68u, 0x74u, 0x00u, 0x74u, 0x61u, 0x70u,
  0x2Eu, 0x65u, 0x64u, 0x67u, 0x65u, 0x2Eu, 0x70u, 0x6Cu, 0x61u, 0x79u, 0x66u, 0x75u, 0x6Cu, 0x2Eu, 0x63u, 0x75u,
  0x72u, 0x69u, 0x6Fu, 0x75u, 0x73u, 0x2Eu, 0x75u, 0x70u, 0x00u, 0x74u, 0x61u, 0x70u, 0x2Eu, 0x65u, 0x64u, 0x67u,
  0x65u, 0x2Eu, 0x70u, 0x6Cu, 0x61u, 0x79u, 0x66u, 0x75u, 0x6Cu, 0x2Eu, 0x64u, 0x65u, 0x6Cu, 0x69u, 0x67u, 0x68u,
  0x74u, 0x65u, 0x64u, 0x2Eu, 0x63u, 0x65u, 0x6Eu, 0x74u, 0x65u, 0x72u, 0x00u, 0x74u, 0x61u, 0x70u, 0x2Eu, 0x65u,
  0x64u, 0x67u, 0x65u, 0x2Eu, 0x70u, 0x6Cu, 0x61u, 0x79u, 0x66u, 0x75u, 0x6Cu, 0x2Eu, 0x64u, 0x65u, 0x6Cu, 0x69u,
  0x67u, 0x68u, 0x74u, 0x65u, 0x64u, 0x2Eu, 0x64u, 0x6Fu, 0x77u, 0x6Eu, 0x00u, 0x74u, 0x61u, 0x70u, 0x2Eu, 0x65u,
  0x64u, 0x67u, 0x65u, 0x2Eu, 0x70u, 0x6Cu, 0x61u, 0x79u, 0x66u, 0x75u, 0x6Cu, 0x2Eu, 0x64u, 0x65u, 0x6Cu, 0x69u,
  0x67u, 0x68u, 0x74u, 0x65u, 0x64u, 0x2Eu, 0x6Cu, 0x65u, 0x66u, 0x74u, 0x00u, 0x74u, 0x61u, 0x70u, 0x2Eu, 0x65u,
  0x64u, 0x67u, 0x65u, 0x2Eu, 0x70u, 0x6Cu, 0x61u, 0x79u, 0x66u, 0x75u, 0x6Cu, 0x2Eu, 0x64u, 0x65u, 0x6Cu, 0x69u,
  0x67u, 0x68u, 0x74u, 0x65u, 0x64u, 0x2Eu, 0x72u, 0x69u, 0x67u, 0x68u, 0x74u, 0x00u, 0x74u, 0x61u, 0x70u, 0x2Eu,
  0x65u, 0x64u, 0x67u, 0x65u, 0x2Eu, 0x70u, 0x6Cu, 0x61u, 0x79u, 0x66u, 0x75u, 0x6Cu, 0x2Eu, 0x64u, 0x65u, 0x6Cu,
  0x69u, 0x67u, 0x68u, 0x74u, 0x65u, 0x64u, 0x2Eu, 0x75u, 0x70u, 0x00u, 0x74u, 0x61u, 0x70u, 0x2Eu, 0x65u, 0x64u,
  0x67u, 0x65u, 0x2Eu, 0x70u, 0x6Cu, 0x61u, 0x79u, 0x66u, 0x75u, 0x6Cu, 0x2Eu, 0x77u, 0x61u, 0x72u, 0x6Du, 0x2Eu,
  0x63u, 0x65u, 0x6Eu, 0x74u, 0x65u, 0x72u, 0x00u, 0x74u, 0x61u, 0x70u, 0x2Eu, 0x65u, 0x64u, 0x67u, 0x65u, 0x2Eu,
  0x70u, 0x6Cu, 0x61u, 0x79u, 0x66u, 0x75u, 0x6Cu, 0x2Eu, 0x77u, 0x61u, 0x72u, 0x6Du, 0x2Eu, 0x64u, 0x6Fu, 0x77u,
  0x6Eu, 0x00u, 0x74u, 0x61u, 0x70u, 0x2Eu, 0x65u, 0x64u, 0x67u, 0x65u, 0x2Eu, 0x70u, 0x6Cu, 0x61u, 0x79u, 0x66u,
  0x75u, 0x6Cu, 0x2Eu, 0x77u, 0x61u, 0x72u, 0x6Du, 0x2Eu, 0x6Cu, 0x65u, 0x66u, 0x74u, 0x00u, 0x74u, 0x61u, 0x70u,
  0x2Eu, 0x65u, 0x64u, 0x67u, 0x65u, 0x2Eu, 0x70u, 0x6Cu, 0x61u, 0x79u, 0x66u, 0x75u, 0x6Cu, 0x2Eu, 0x77u, 0x61u,
  0x72u, 0x6Du, 0x2Eu, 0x72u, 0x69u, 0x67u, 0x68u, 0x74u, 0x00u, 0x74u, 0x61u, 0x70u, 0x2Eu, 0x65u, 0x64u, 0x67u,
  0x65u, 0x2Eu, 0x70u, 0x6Cu, 0x61u, 0x79u, 0x66u, 0x75u, 0x6Cu, 0x2Eu, 0x77u, 0x61u, 0x72u, 0x6Du, 0x2Eu, 0x75u,
  0x70u, 0x00u, 0x74u, 0x61u, 0x70u, 0x2Eu, 0x65u, 0x64u, 0x67u, 0x65u, 0x2Eu, 0x73u, 0x6Cu, 0x65u, 0x65u, 0x70u,
  0x79u, 0x2Eu, 0x63u, 0x61u, 0x6Cu, 0x6Du, 0x2Eu, 0x63u, 0x65u, 0x6Eu, 0x74u, 0x65u, 0x72u, 0x00u, 0x74u, 0x61u,
  0x70u, 0x2Eu, 0x65u, 0x64u, 0x67u, 0x65u, 0x2Eu, 0x73u, 0x6Cu, 0x65u, 0x65u, 0x70u, 0x79u, 0x2Eu, 0x63u, 0x61u,
  0x6Cu, 0x6Du, 0x2Eu, 0x64u, 0x6Fu, 0x77u, 0x6Eu, 0x00u, 0x74u, 0x61u, 0x70u, 0x2Eu, 0x65u, 0x64u, 0x67u, 0x65u,
  0x2Eu, 0x73u, 0x6Cu, 0x65u, 0x65u, 0x70u, 0x79u, 0x2Eu, 0x63u, 0x61u, 0x6Cu, 0x6Du, 0x2Eu, 0x6Cu, 0x65u, 0x66u,
  0x74u, 0x00u, 0x74u, 0x61u, 0x70u, 0x2Eu, 0x65u, 0x64u, 0x67u, 0x65u, 0x2Eu, 0x73u, 0x6Cu, 0x65u, 0x65u, 0x70u,
  0x79u, 0x2Eu, 0x63u, 0x61u, 0x6Cu, 0x6Du, 0x2Eu, 0x72u, 0x69u, 0x67u, 0x68u, 0x74u, 0x00u, 0x74u, 0x61u, 0x70u,
  0x2Eu, 0x65u, 0x64u, 0x67u, 0x65u, 0x2Eu, 0x73u, 0x6Cu, 0x65u, 0x65u, 0x70u, 0x79u, 0x2Eu, 0x63u, 0x61u, 0x6Cu,
  0x6Du, 0x2Eu, 0x75u, 0x70u, 0x00u, 0x74u, 0x61u, 0x70u, 0x2Eu, 0x65u, 0x64u, 0x67u, 0x65u, 0x2Eu, 0x73u, 0x6Cu,
  0x65u, 0x65u, 0x70u, 0x79u, 0x2Eu, 0x77u, 0x61u, 0x72u, 0x6Du, 0x2Eu, 0x63u, 0x65u, 0x6Eu, 0x74u, 0x65u, 0x72u,
  0x00u, 0x74u, 0x61u, 0x70u, 0x2Eu, 0x65u, 0x64u, 0x67u, 0x65u, 0x2Eu, 0x73u, 0x6Cu, 0x65u, 0x65u, 0x70u, 0x79u,
  0x2Eu, 0x77u, 0x61u, 0x72u, 0x6Du, 0x2Eu, 0x64u, 0x6Fu, 0x77u, 0x6Eu, 0x00u, 0x74u, 0x61u, 0x70u, 0x2Eu, 0x65u,
  0x64u, 0x67u, 0x65u, 0x2Eu, 0x73u, 0x6Cu, 0x65u, 0x65u, 0x70u, 0x79u, 0x2Eu, 0x77u, 0x61u, 0x72u, 0x6Du, 0x2Eu,
  0x6Cu, 0x65u, 0x66u, 0x74u, 0x00u, 0x74u, 0x61u, 0x70u, 0x2Eu, 0x65u, 0x64u, 0x67u, 0x65u, 0x2Eu, 0x73u, 0x6Cu,
  0x65u, 0x65u, 0x70u, 0x79u, 0x2Eu, 0x77u, 0x61u, 0x72u, 0x6Du, 0x2Eu, 0x72u, 0x69u, 0x67u, 0x68u, 0x74u, 0x00u,
  0x74u, 0x61u, 0x70u, 0x2Eu, 0x65u, 0x64u, 0x67u, 0x65u, 0x2Eu, 0x73u, 0x6Cu, 0x65u, 0x65u, 0x70u, 0x79u, 0x2Eu,
  0x77u, 0x61u, 0x72u, 0x6Du, 0x2Eu, 0x75u, 0x70u, 0x00u, 0x74u, 0x61u, 0x70u, 0x2Eu, 0x65u, 0x64u, 0x67u, 0x65u,
  0x2Eu, 0x74u, 0x68u, 0x6Fu, 0x75u, 0x67u, 0x68u, 0x74u, 0x66u, 0x75u, 0x6Cu, 0x2Eu, 0x61u, 0x6Cu, 0x65u, 0x72u,
  0x74u, 0x2Eu, 0x63u, 0x65u, 0x6Eu, 0x74u, 0x65u, 0x72u, 0x00u, 0x74u, 0x61u, 0x70u, 0x2Eu, 0x65u, 0x64u, 0x67u,
  0x65u, 0x2Eu, 0x74u, 0x68u, 0x6Fu, 0x75u, 0x67u, 0x68u, 0x74u, 0x66u, 0x75u, 0x6Cu, 0x2Eu, 0x61u, 0x6Cu, 0x65u,
  0x72u, 0x74u, 0x2Eu, 0x64u, 0x6Fu, 0x77u, 0x6Eu, 0x00u, 0x74u, 0x61u, 0x70u, 0x2Eu, 0x65u, 0x64u, 0x67u, 0x65u,
  0x2Eu, 0x74u, 0x68u, 0x6Fu, 0x75u, 0x67u, 0x68u, 0x74u, 0x66u, 0x75u, 0x6Cu, 0x2Eu, 0x61u, 0x6Cu, 0x65u, 0x72u,
  0x74u, 0x2Eu, 0x6Cu, 0x65u, 0x66u, 0x74u, 0x00u, 0x74u, 0x61u, 0x70u, 0x2Eu, 0x65u, 0x64u, 0x67u, 0x65u, 0x2Eu,
  0x74u, 0x68u, 0x6Fu, 0x75u, 0x67u, 0x68u, 0x74u, 0x66u, 0x75u, 0x6Cu, 0x2Eu, 0x61u, 0x6Cu, 0x65u, 0x72u, 0x74u,
  0x2Eu, 0x72u, 0x69u, 0x67u, 0x68u, 0x74u, 0x00u, 0x74u, 0x61u, 0x70u, 0x2Eu, 0x65u, 0x64u, 0x67u, 0x65u, 0x2Eu,
  0x74u, 0x68u, 0x6Fu, 0x75u, 0x67u, 0x68u, 0x74u, 0x66u, 0x75u, 0x6Cu, 0x2Eu, 0x61u, 0x6Cu, 0x65u, 0x72u, 0x74u,
  0x2Eu, 0x75u, 0x70u, 0x00u, 0x74u, 0x61u, 0x70u, 0x2Eu, 0x65u, 0x64u, 0x67u, 0x65u, 0x2Eu, 0x74u, 0x68u, 0x6Fu,
  0x75u, 0x67u, 0x68u, 0x74u, 0x66u, 0x75u, 0x6Cu, 0x2Eu, 0x63u, 0x61u, 0x6Cu, 0x6Du, 0x2Eu, 0x63u, 0x65u, 0x6Eu,
  0x74u, 0x65u, 0x72u, 0x00u, 0x74u, 0x61u, 0x70u, 0x2Eu, 0x65u, 0x64u, 0x67u, 0x65u, 0x2Eu, 0x74u, 0x68u, 0x6Fu,
  0x75u, 0x67u, 0x68u, 0x74u, 0x66u, 0x75u, 0x6Cu, 0x2Eu, 0x63u, 0x61u, 0x6Cu, 0x6Du, 0x2Eu, 0x64u, 0x6Fu, 0x77u,
  0x6Eu, 0x00u, 0x74u, 0x61u, 0x70u, 0x2Eu, 0x65u, 0x64u, 0x67u, 0x65u, 0x2Eu, 0x74u, 0x68u, 0x6Fu, 0x75u, 0x67u,
  0x68u, 0x74u, 0x66u, 0x75u, 0x6Cu, 0x2Eu, 0x63u, 0x61u, 0x6Cu, 0x6Du, 0x2Eu, 0x6Cu, 0x65u, 0x66u, 0x74u, 0x00u,
  0x74u, 0x61u, 0x70u, 0x2Eu, 0x65u, 0x64u, 0x67u, 0x65u, 0x2Eu, 0x74u, 0x68u, 0x6Fu, 0x75u, 0x67u, 0x68u, 0x74u,
  0x66u, 0x75u, 0x6Cu, 0x2Eu, 0x63u, 0x61u, 0x6Cu, 0x6Du, 0x2Eu, 0x72u, 0x69u, 0x67u, 0x68u, 0x74u, 0x00u, 0x74u,
  0x61u, 0x70u, 0x2Eu, 0x65u, 0x64u, 0x67u, 0x65u, 0x2Eu, 0x74u, 0x68u, 0x6Fu, 0x75u, 0x67u, 0x68u, 0x74u, 0x66u,
  0x75u, 0x6Cu, 0x2Eu, 0x63u, 0x61u, 0x6Cu, 0x6Du, 0x2Eu, 0x75u, 0x70u, 0x00u, 0x74u, 0x61u, 0x70u, 0x2Eu, 0x65u,
  0x64u, 0x67u, 0x65u, 0x2Eu, 0x74u, 0x68u, 0x6Fu, 0x75u, 0x67u, 0x68u, 0x74u, 0x66u, 0x75u, 0x6Cu, 0x2Eu, 0x63u,
  0x75u, 0x72u, 0x69u, 0x6Fu, 0x75u, 0x73u, 0x2Eu, 0x63u, 0x65u, 0x6Eu, 0x74u, 0x65u, 0x72u, 0x00u, 0x74u, 0x61u,
  0x70u, 0x2Eu, 0x65u, 0x64u, 0x67u, 0x65u, 0x2Eu, 0x74u, 0x68u, 0x6Fu, 0x75u, 0x67u, 0x68u, 0x74u, 0x66u, 0x75u,
  0x6Cu, 0x2Eu, 0x63u, 0x75u, 0x72u, 0x69u, 0x6Fu, 0x75u, 0x73u, 0x2Eu, 0x64u, 0x6Fu, 0x77u, 0x6Eu, 0x00u, 0x74u,
  0x61u, 0x70u, 0x2Eu, 0x65u, 0x64u, 0x67u, 0x65u, 0x2Eu, 0x74u, 0x68u, 0x6Fu, 0x75u, 0x67u, 0x68u, 0x74u, 0x66u,
  0x75u, 0x6Cu, 0x2Eu, 0x63u, 0x75u, 0x72u, 0x69u, 0x6Fu, 0x75u, 0x73u, 0x2Eu, 0x6Cu, 0x65u, 0x66u, 0x74u, 0x00u,
  0x74u, 0x61u, 0x70u, 0x2Eu, 0x65u, 0x64u, 0x67u, 0x65u, 0x2Eu, 0x74u, 0x68u, 0x6Fu, 0x75u, 0x67u, 0x68u, 0x74u,
  0x66u, 0x75u, 0x6Cu, 0x2Eu, 0x63u, 0x75u, 0x72u, 0x69u, 0x6Fu, 0x75u, 0x73u, 0x2Eu, 0x72u, 0x69u, 0x67u, 0x68u,
  0x74u, 0x00u, 0x74u, 0x61u, 0x70u, 0x2Eu, 0x65u, 0x64u, 0x67u, 0x65u, 0x2Eu, 0x74u, 0x68u, 0x6Fu, 0x75u, 0x67u,
  0x68u, 0x74u, 0x66u, 0x75u, 0x6Cu, 0x2Eu, 0x63u, 0x75u, 0x72u, 0x69u, 0x6Fu, 0x75u, 0x73u, 0x2Eu, 0x75u, 0x70u,
  0x00u, 0x74u, 0x61u, 0x70u, 0x2Eu, 0x65u, 0x64u, 0x67u, 0x65u, 0x2Eu, 0x74u, 0x68u, 0x6Fu, 0x75u, 0x67u, 0x68u,
  0x74u, 0x66u, 0x75u, 0x6Cu, 0x2Eu, 0x66u, 0x6Fu, 0x63u, 0x75u, 0x73u, 0x65u, 0x64u, 0x2Eu, 0x63u, 0x65u, 0x6Eu,
  0x74u, 0x65u, 0x72u, 0x00u, 0x74u, 0x61u, 0x70u, 0x2Eu, 0x65u, 0x64u, 0x67u, 0x65u, 0x2Eu, 0x74u, 0x68u, 0x6Fu,
  0x75u, 0x67u, 0x68u, 0x74u, 0x66u, 0x75u, 0x6Cu, 0x2Eu, 0x66u, 0x6Fu, 0x63u, 0x75u, 0x73u, 0x65u, 0x64u, 0x2Eu,
  0x64u, 0x6Fu, 0x77u, 0x6Eu, 0x00u, 0x74u, 0x61u, 0x70u, 0x2Eu, 0x65u, 0x64u, 0x67u, 0x65u, 0x2Eu, 0x74u, 0x68u,
  0x6Fu, 0x75u, 0x67u, 0x68u, 0x74u, 0x66u, 0x75u, 0x6Cu, 0x2Eu, 0x66u, 0x6Fu, 0x63u, 0x75u, 0x73u, 0x65u, 0x64u,
  0x2Eu, 0x6Cu, 0x65u, 0x66u, 0x74u, 0x00u, 0x74u, 0x61u, 0x70u, 0x2Eu, 0x65u, 0x64u, 0x67u, 0x65u, 0x2Eu, 0x74u,
  0x68u, 0x6Fu, 0x75u, 0x67u, 0x68u, 0x74u, 0x66u, 0x75u, 0x6Cu, 0x2Eu, 0x66u, 0x6Fu, 0x63u, 0x75u, 0x73u, 0x65u,
  0x64u, 0x2Eu, 0x72u, 0x69u, 0x67u, 0x68u, 0x74u, 0x00u, 0x74u, 0x61u, 0x70u, 0x2Eu, 0x65u, 0x64u, 0x67u, 0x65u,
  0x2Eu, 0x74u, 0x68u, 0x6Fu, 0x75u, 0x67u, 0x68u, 0x74u, 0x66u, 0x75u, 0x6Cu, 0x2Eu, 0x66u, 0x6Fu, 0x63u, 0x75u,
  0x73u, 0x65u, 0x64u, 0x2Eu, 0x75u, 0x70u, 0x00u, 0x74u, 0x61u, 0x70u, 0x2Eu, 0x65u, 0x64u, 0x67u, 0x65u, 0x2Eu,
  0x77u, 0x61u, 0x72u, 0x6Du, 0x2Eu, 0x62u, 0x61u, 0x73u, 0x68u, 0x66u, 0x75u, 0x6Cu, 0x2Eu, 0x63u, 0x65u, 0x6Eu,
  0x74u, 0x65u, 0x72u, 0x00u, 0x74u, 0x61u, 0x70u, 0x2Eu, 0x65u, 0x64u, 0x67u, 0x65u, 0x2Eu, 0x77u, 0x61u, 0x72u,
  0x6Du, 0x2Eu, 0x62u, 0x61u, 0x73u, 0x68u, 0x66u, 0x75u, 0x6Cu, 0x2Eu, 0x64u, 0x6Fu, 0x77u, 0x6Eu, 0x00u, 0x74u,
  0x61u, 0x70u, 0x2Eu, 0x65u, 0x64u, 0x67u, 0x65u, 0x2Eu, 0x77u, 0x61u, 0x72u, 0x6Du, 0x2Eu, 0x62u, 0x61u, 0x73u,
  0x68u, 0x66u, 0x75u, 0x6Cu, 0x2Eu, 0x6Cu, 0x65u, 0x66u, 0x74u, 0x00u, 0x74u, 0x61u, 0x70u, 0x2Eu, 0x65u, 0x64u,
  0x67u, 0x65u, 0x2Eu, 0x77u, 0x61u, 0x72u, 0x6Du, 0x2Eu, 0x62u, 0x61u, 0x73u, 0x68u, 0x66u, 0x75u, 0x6Cu, 0x2Eu,
  0x72u, 0x69u, 0x67u, 0x68u, 0x74u, 0x00u, 0x74u, 0x61u, 0x70u, 0x2Eu, 0x65u, 0x64u, 0x67u, 0x65u, 0x2Eu, 0x77u,
  0x61u, 0x72u, 0x6Du, 0x2Eu, 0x62u, 0x61u, 0x73u, 0x68u, 0x66u, 0x75u, 0x6Cu, 0x2Eu, 0x75u, 0x70u, 0x00u, 0x74u,
  0x61u, 0x70u, 0x2Eu, 0x65u, 0x64u, 0x67u, 0x65u, 0x2Eu, 0x77u, 0x61u, 0x72u, 0x6Du, 0x2Eu, 0x63u, 0x61u, 0x6Cu,
  0x6Du, 0x2Eu, 0x63u, 0x65u, 0x6Eu, 0x74u, 0x65u, 0x72u, 0x00u, 0x74u, 0x61u, 0x70u, 0x2Eu, 0x65u, 0x64u, 0x67u,
  0x65u, 0x2Eu, 0x77u, 0x61u, 0x72u, 0x6Du, 0x2Eu, 0x63u, 0x61u, 0x6Cu, 0x6Du, 0x2Eu, 0x64u, 0x6Fu, 0x77u, 0x6Eu,
  0x00u, 0x74u, 0x61u, 0x70u, 0x2Eu, 0x65u, 0x64u, 0x67u, 0x65u, 0x2Eu, 0x77u, 0x61u, 0x72u, 0x6Du, 0x2Eu, 0x63u,
  0x61u, 0x6Cu, 0x6Du, 0x2Eu, 0x6Cu, 0x65u, 0x66u, 0x74u, 0x00u, 0x74u, 0x61u, 0x70u, 0x2Eu, 0x65u, 0x64u, 0x67u,
  0x65u, 0x2Eu, 0x77u, 0x61u, 0x72u, 0x6Du, 0x2Eu, 0x63u, 0x61u, 0x6Cu, 0x6Du, 0x2Eu, 0x72u, 0x69u, 0x67u, 0x68u,
  0x74u, 0x00u, 0x74u, 0x61u, 0x70u, 0x2Eu, 0x65u, 0x64u, 0x67u, 0x65u, 0x2Eu, 0x77u, 0x61u, 0x72u, 0x6Du, 0x2Eu,
  0x63u, 0x61u, 0x6Cu, 0x6Du, 0x2Eu, 0x75u, 0x70u, 0x00u, 0x74u, 0x61u, 0x70u, 0x2Eu, 0x65u, 0x64u, 0x67u, 0x65u,
  0x2Eu, 0x77u, 0x61u, 0x72u, 0x6Du, 0x2Eu, 0x63u, 0x75u, 0x72u, 0x69u, 0x6Fu, 0x75u, 0x73u, 0x2Eu, 0x63u, 0x65u,
  0x6Eu, 0x74u, 0x65u, 0x72u, 0x00u, 0x74u, 0x61u, 0x70u, 0x2Eu, 0x65u, 0x64u, 0x67u, 0x65u, 0x2Eu, 0x77u, 0x61u,
  0x72u, 0x6Du, 0x2Eu, 0x63u, 0x75u, 0x72u, 0x69u, 0x6Fu, 0x75u, 0x73u, 0x2Eu, 0x64u, 0x6Fu, 0x77u, 0x6Eu, 0x00u,
  0x74u, 0x61u, 0x70u, 0x2Eu, 0x65u, 0x64u, 0x67u, 0x65u, 0x2Eu, 0x77u, 0x61u, 0x72u, 0x6Du, 0x2Eu, 0x63u, 0x75u,
  0x72u, 0x69u, 0x6Fu, 0x75u, 0x73u, 0x2Eu, 0x6Cu, 0x65u, 0x66u, 0x74u, 0x00u, 0x74u, 0x61u, 0x70u, 0x2Eu, 0x65u,
  0x64u, 0x67u, 0x65u, 0x2Eu, 0x77u, 0x61u, 0x72u, 0x6Du, 0x2Eu, 0x63u, 0x75u, 0x72u, 0x69u, 0x6Fu, 0x75u, 0x73u,
  0x2Eu, 0x72u, 0x69u, 0x67u, 0x68u, 0x74u, 0x00u, 0x74u, 0x61u, 0x70u, 0x2Eu, 0x65u, 0x64u, 0x67u, 0x65u, 0x2Eu,
  0x77u, 0x61u, 0x72u, 0x6Du, 0x2Eu, 0x63u, 0x75u, 0x72u, 0x69u, 0x6Fu, 0x75u, 0x73u, 0x2Eu, 0x75u, 0x70u, 0x00u,
  0x74u, 0x61u, 0x70u, 0x2Eu, 0x65u, 0x64u, 0x67u, 0x65u, 0x2Eu, 0x77u, 0x61u, 0x72u, 0x6Du, 0x2Eu, 0x64u, 0x65u,
  0x6Cu, 0x69u, 0x67u, 0x68u, 0x74u, 0x65u, 0x64u, 0x2Eu, 0x63u, 0x65u, 0x6Eu, 0x74u, 0x65u, 0x72u, 0x00u, 0x74u,
  0x61u, 0x70u, 0x2Eu, 0x65u, 0x64u, 0x67u, 0x65u, 0x2Eu, 0x77u, 0x61u, 0x72u, 0x6Du, 0x2Eu, 0x64u, 0x65u, 0x6Cu,
  0x69u, 0x67u, 0x68u, 0x74u, 0x65u, 0x64u, 0x2Eu, 0x64u, 0x6Fu, 0x77u, 0x6Eu, 0x00u, 0x74u, 0x61u, 0x70u, 0x2Eu,
  0x65u, 0x64u, 0x67u, 0x65u, 0x2Eu, 0x77u, 0x61u, 0x72u, 0x6Du, 0x2Eu, 0x64u, 0x65u, 0x6Cu, 0x69u, 0x67u, 0x68u,
  0x74u, 0x65u, 0x64u, 0x2Eu, 0x6Cu, 0x65u, 0x66u, 0x74u, 0x00u, 0x74u, 0x61u, 0x70u, 0x2Eu, 0x65u, 0x64u, 0x67u,
  0x65u, 0x2Eu, 0x77u, 0x61u, 0x72u, 0x6Du, 0x2Eu, 0x64u, 0x65u, 0x6Cu, 0x69u, 0x67u, 0x68u, 0x74u, 0x65u, 0x64u,
  0x2Eu, 0x72u, 0x69u, 0x67u, 0x68u, 0x74u, 0x00u, 0x74u, 0x61u, 0x70u, 0x2Eu, 0x65u, 0x64u, 0x67u, 0x65u, 0x2Eu,
  0x77u, 0x61u, 0x72u, 0x6Du, 0x2Eu, 0x64u, 0x65u, 0x6Cu, 0x69u, 0x67u, 0x68u, 0x74u, 0x65u, 0x64u, 0x2Eu, 0x75u,
  0x70u, 0x00u, 0x74u, 0x61u, 0x70u, 0x2Eu, 0x65u, 0x64u, 0x67u, 0x65u, 0x2Eu, 0x77u, 0x61u, 0x72u, 0x6Du, 0x2Eu,
  0x70u, 0x6Cu, 0x61u, 0x79u, 0x66u, 0x75u, 0x6Cu, 0x2Eu, 0x63u, 0x65u, 0x6Eu, 0x74u, 0x65u, 0x72u, 0x00u, 0x74u,
  0x61u, 0x70u, 0x2Eu, 0x65u, 0x64u, 0x67u, 0x65u, 0x2Eu, 0x77u, 0x61u, 0x72u, 0x6Du, 0x2Eu, 0x70u, 0x6Cu, 0x61u,
  0x79u, 0x66u, 0x75u, 0x6Cu, 0x2Eu, 0x64u, 0x6Fu, 0x77u, 0x6Eu, 0x00u, 0x74u, 0x61u, 0x70u, 0x2Eu, 0x65u, 0x64u,
  0x67u, 0x65u, 0x2Eu, 0x77u, 0x61u, 0x72u, 0x6Du, 0x2Eu, 0x70u, 0x6Cu, 0x61u, 0x79u, 0x66u, 0x75u, 0x6Cu, 0x2Eu,
  0x6Cu, 0x65u, 0x66u, 0x74u, 0x00u, 0x74u, 0x61u, 0x70u, 0x2Eu, 0x65u, 0x64u, 0x67u, 0x65u, 0x2Eu, 0x77u, 0x61u,
  0x72u, 0x6Du, 0x2Eu, 0x70u, 0x6Cu, 0x61u, 0x79u, 0x66u, 0x75u, 0x6Cu, 0x2Eu, 0x72u, 0x69u, 0x67u, 0x68u, 0x74u,
  0x00u, 0x74u, 0x61u, 0x70u, 0x2Eu, 0x65u, 0x64u, 0x67u, 0x65u, 0x2Eu, 0x77u, 0x61u, 0x72u, 0x6Du, 0x2Eu, 0x70u,
  0x6Cu, 0x61u, 0x79u, 0x66u, 0x75u, 0x6Cu, 0x2Eu, 0x75u, 0x70u, 0x00u,
};

static const comp_emote_clip_t companion_browser_cemp_clips[
    COMPANION_BROWSER_CEMP_CLIP_COUNT + 1u] = {
  {.name = (const char *)&companion_browser_cemp_strings[41u], .first_frame = 0u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[52u], .first_frame = 1u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[63u], .first_frame = 2u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[74u], .first_frame = 3u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[85u], .first_frame = 4u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[96u], .first_frame = 5u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[107u], .first_frame = 6u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[118u], .first_frame = 7u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[129u], .first_frame = 8u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[140u], .first_frame = 9u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[151u], .first_frame = 10u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[162u], .first_frame = 11u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[173u], .first_frame = 12u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[184u], .first_frame = 13u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[195u], .first_frame = 14u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[206u], .first_frame = 15u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[217u], .first_frame = 16u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[228u], .first_frame = 17u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[239u], .first_frame = 18u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[250u], .first_frame = 19u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[261u], .first_frame = 20u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[272u], .first_frame = 21u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[283u], .first_frame = 22u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[294u], .first_frame = 23u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[305u], .first_frame = 24u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[316u], .first_frame = 25u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[327u], .first_frame = 26u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[338u], .first_frame = 27u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[349u], .first_frame = 28u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[360u], .first_frame = 29u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[371u], .first_frame = 30u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[382u], .first_frame = 31u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[393u], .first_frame = 32u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[404u], .first_frame = 33u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[415u], .first_frame = 34u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[426u], .first_frame = 35u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[437u], .first_frame = 36u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[448u], .first_frame = 37u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[459u], .first_frame = 38u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[470u], .first_frame = 39u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[481u], .first_frame = 40u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[492u], .first_frame = 41u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[503u], .first_frame = 42u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[514u], .first_frame = 43u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[525u], .first_frame = 44u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[536u], .first_frame = 45u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[547u], .first_frame = 46u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[558u], .first_frame = 47u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[569u], .first_frame = 48u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[580u], .first_frame = 49u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[591u], .first_frame = 50u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[602u], .first_frame = 51u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[613u], .first_frame = 52u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[624u], .first_frame = 53u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[635u], .first_frame = 54u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[646u], .first_frame = 55u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[657u], .first_frame = 56u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[668u], .first_frame = 57u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[679u], .first_frame = 58u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[690u], .first_frame = 59u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[701u], .first_frame = 60u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[712u], .first_frame = 61u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[723u], .first_frame = 62u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[734u], .first_frame = 63u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[745u], .first_frame = 64u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[756u], .first_frame = 65u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[767u], .first_frame = 66u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[778u], .first_frame = 67u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[789u], .first_frame = 68u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[800u], .first_frame = 69u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[811u], .first_frame = 70u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[822u], .first_frame = 71u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[833u], .first_frame = 72u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[844u], .first_frame = 73u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[855u], .first_frame = 74u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[866u], .first_frame = 75u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[877u], .first_frame = 76u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[888u], .first_frame = 77u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[899u], .first_frame = 78u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[910u], .first_frame = 79u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[921u], .first_frame = 80u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[932u], .first_frame = 81u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[943u], .first_frame = 82u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[954u], .first_frame = 83u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[965u], .first_frame = 84u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[976u], .first_frame = 85u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[987u], .first_frame = 86u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[998u], .first_frame = 87u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[1009u], .first_frame = 88u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[1020u], .first_frame = 89u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[1031u], .first_frame = 90u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[1042u], .first_frame = 91u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[1053u], .first_frame = 92u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[1064u], .first_frame = 93u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[1075u], .first_frame = 94u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[1086u], .first_frame = 95u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[1097u], .first_frame = 96u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[1108u], .first_frame = 97u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[1119u], .first_frame = 98u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[1130u], .first_frame = 99u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[1141u], .first_frame = 100u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[1152u], .first_frame = 101u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[1163u], .first_frame = 102u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[1174u], .first_frame = 103u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[1185u], .first_frame = 104u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[1196u], .first_frame = 105u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[1207u], .first_frame = 106u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[1218u], .first_frame = 107u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[1229u], .first_frame = 108u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[1240u], .first_frame = 109u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[1251u], .first_frame = 110u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[1262u], .first_frame = 111u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[1273u], .first_frame = 112u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[1284u], .first_frame = 113u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[1295u], .first_frame = 114u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[1306u], .first_frame = 115u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[1317u], .first_frame = 116u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[1328u], .first_frame = 117u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[1339u], .first_frame = 118u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[1350u], .first_frame = 119u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[1361u], .first_frame = 120u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[1372u], .first_frame = 121u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[1383u], .first_frame = 122u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[1394u], .first_frame = 123u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[1405u], .first_frame = 124u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[1416u], .first_frame = 125u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[1427u], .first_frame = 126u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[1438u], .first_frame = 127u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[1449u], .first_frame = 128u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[1460u], .first_frame = 129u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[1471u], .first_frame = 130u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[1482u], .first_frame = 131u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[1493u], .first_frame = 132u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[1504u], .first_frame = 133u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[1515u], .first_frame = 134u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[1526u], .first_frame = 135u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[1537u], .first_frame = 136u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[1548u], .first_frame = 137u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[1559u], .first_frame = 138u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[1570u], .first_frame = 139u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[1581u], .first_frame = 140u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[1592u], .first_frame = 141u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[1603u], .first_frame = 142u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[1614u], .first_frame = 143u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[1625u], .first_frame = 144u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[1636u], .first_frame = 145u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[1647u], .first_frame = 146u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[1658u], .first_frame = 147u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[1669u], .first_frame = 148u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[1680u], .first_frame = 149u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[1691u], .first_frame = 150u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[1702u], .first_frame = 151u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[1713u], .first_frame = 152u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[1724u], .first_frame = 153u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[1735u], .first_frame = 154u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[1746u], .first_frame = 155u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[1757u], .first_frame = 156u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[1768u], .first_frame = 157u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[1779u], .first_frame = 158u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[1790u], .first_frame = 159u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[1801u], .first_frame = 160u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[1812u], .first_frame = 161u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[1823u], .first_frame = 162u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[1834u], .first_frame = 163u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[1845u], .first_frame = 164u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[1856u], .first_frame = 165u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[1867u], .first_frame = 166u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[1878u], .first_frame = 167u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[1889u], .first_frame = 168u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[1900u], .first_frame = 169u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[1911u], .first_frame = 170u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[1922u], .first_frame = 171u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[1933u], .first_frame = 172u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[1944u], .first_frame = 173u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[1955u], .first_frame = 174u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[1966u], .first_frame = 175u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[1977u], .first_frame = 176u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[1988u], .first_frame = 177u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[1999u], .first_frame = 178u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[2010u], .first_frame = 179u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[2021u], .first_frame = 180u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[2032u], .first_frame = 181u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[2043u], .first_frame = 182u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[2054u], .first_frame = 183u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[2065u], .first_frame = 184u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[2076u], .first_frame = 185u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[2087u], .first_frame = 186u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[2098u], .first_frame = 187u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[2109u], .first_frame = 188u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[2120u], .first_frame = 189u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[2131u], .first_frame = 190u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[2142u], .first_frame = 191u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[2153u], .first_frame = 192u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[2164u], .first_frame = 193u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[2175u], .first_frame = 194u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[2186u], .first_frame = 195u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[2197u], .first_frame = 196u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[2208u], .first_frame = 197u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[2219u], .first_frame = 198u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[2230u], .first_frame = 199u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[2241u], .first_frame = 200u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[2252u], .first_frame = 201u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[2263u], .first_frame = 202u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[2274u], .first_frame = 203u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[2285u], .first_frame = 204u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[2296u], .first_frame = 205u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[2307u], .first_frame = 206u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[2318u], .first_frame = 207u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[2329u], .first_frame = 208u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[2340u], .first_frame = 209u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[2351u], .first_frame = 210u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[2362u], .first_frame = 211u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[2373u], .first_frame = 212u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[2384u], .first_frame = 213u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[2395u], .first_frame = 214u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[2406u], .first_frame = 215u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[2417u], .first_frame = 216u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[2428u], .first_frame = 217u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[2439u], .first_frame = 218u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[2450u], .first_frame = 219u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[2461u], .first_frame = 220u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[2472u], .first_frame = 221u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[2483u], .first_frame = 222u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[2494u], .first_frame = 223u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[2505u], .first_frame = 224u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[2516u], .first_frame = 225u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[2527u], .first_frame = 226u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[2538u], .first_frame = 227u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[2549u], .first_frame = 228u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[2560u], .first_frame = 229u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[2571u], .first_frame = 230u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[2582u], .first_frame = 231u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[2593u], .first_frame = 232u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[2604u], .first_frame = 233u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[2615u], .first_frame = 234u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[2626u], .first_frame = 235u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[2637u], .first_frame = 236u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[2648u], .first_frame = 237u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[2659u], .first_frame = 238u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[2670u], .first_frame = 239u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[2681u], .first_frame = 240u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[2692u], .first_frame = 241u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[2703u], .first_frame = 242u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[2714u], .first_frame = 243u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[2725u], .first_frame = 244u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[2736u], .first_frame = 245u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[2747u], .first_frame = 246u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[2758u], .first_frame = 247u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[2769u], .first_frame = 248u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[2780u], .first_frame = 249u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[2791u], .first_frame = 250u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[2802u], .first_frame = 251u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[2813u], .first_frame = 252u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[2824u], .first_frame = 253u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[2835u], .first_frame = 254u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[2846u], .first_frame = 255u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[2857u], .first_frame = 256u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[2868u], .first_frame = 257u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[2879u], .first_frame = 258u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[2890u], .first_frame = 259u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[2901u], .first_frame = 260u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[2912u], .first_frame = 261u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[2923u], .first_frame = 262u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[2934u], .first_frame = 263u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[2945u], .first_frame = 264u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[2956u], .first_frame = 265u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[2967u], .first_frame = 266u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[2978u], .first_frame = 267u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[2989u], .first_frame = 268u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[3000u], .first_frame = 269u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[3011u], .first_frame = 270u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[3022u], .first_frame = 271u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[3033u], .first_frame = 272u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[3044u], .first_frame = 273u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[3055u], .first_frame = 274u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[3066u], .first_frame = 275u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[3077u], .first_frame = 276u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[3088u], .first_frame = 277u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[3099u], .first_frame = 278u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[3110u], .first_frame = 279u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[3121u], .first_frame = 280u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[3132u], .first_frame = 281u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[3143u], .first_frame = 282u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[3154u], .first_frame = 283u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[3165u], .first_frame = 284u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[3176u], .first_frame = 285u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[3187u], .first_frame = 286u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[3198u], .first_frame = 287u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[3209u], .first_frame = 288u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[3220u], .first_frame = 289u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[3231u], .first_frame = 290u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[3242u], .first_frame = 291u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[3253u], .first_frame = 292u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[3264u], .first_frame = 293u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[3275u], .first_frame = 294u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[3286u], .first_frame = 295u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[3297u], .first_frame = 296u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[3308u], .first_frame = 297u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[3319u], .first_frame = 298u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[3330u], .first_frame = 299u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[3341u], .first_frame = 300u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[3352u], .first_frame = 301u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[3363u], .first_frame = 302u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[3374u], .first_frame = 303u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[3385u], .first_frame = 304u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[3396u], .first_frame = 305u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[3407u], .first_frame = 306u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[3418u], .first_frame = 307u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[3429u], .first_frame = 308u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[3440u], .first_frame = 309u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[3451u], .first_frame = 310u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[3462u], .first_frame = 311u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[3473u], .first_frame = 312u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[3484u], .first_frame = 313u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[3495u], .first_frame = 314u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[3506u], .first_frame = 315u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[3517u], .first_frame = 316u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[3528u], .first_frame = 317u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[3539u], .first_frame = 318u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[3550u], .first_frame = 319u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[3561u], .first_frame = 320u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[3572u], .first_frame = 321u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[3583u], .first_frame = 322u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[3594u], .first_frame = 323u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[3605u], .first_frame = 324u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[3616u], .first_frame = 325u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[3627u], .first_frame = 326u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[3638u], .first_frame = 327u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[3649u], .first_frame = 328u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[3660u], .first_frame = 329u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[3671u], .first_frame = 330u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[3682u], .first_frame = 331u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[3693u], .first_frame = 332u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[3704u], .first_frame = 333u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[3715u], .first_frame = 334u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[3726u], .first_frame = 335u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[3737u], .first_frame = 336u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[3748u], .first_frame = 337u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[3759u], .first_frame = 338u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[3770u], .first_frame = 339u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[3781u], .first_frame = 340u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[3792u], .first_frame = 341u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[3803u], .first_frame = 342u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[3814u], .first_frame = 343u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[3825u], .first_frame = 344u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[3836u], .first_frame = 345u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[3847u], .first_frame = 346u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[3858u], .first_frame = 347u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[3869u], .first_frame = 348u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[3880u], .first_frame = 349u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[3891u], .first_frame = 350u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[3902u], .first_frame = 351u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[3913u], .first_frame = 352u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[3924u], .first_frame = 353u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[3935u], .first_frame = 354u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[3946u], .first_frame = 355u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[3957u], .first_frame = 356u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[3968u], .first_frame = 357u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[3979u], .first_frame = 358u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[3990u], .first_frame = 359u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[4001u], .first_frame = 360u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[4012u], .first_frame = 361u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[4023u], .first_frame = 362u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[4034u], .first_frame = 363u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[4045u], .first_frame = 364u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[4056u], .first_frame = 365u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[4067u], .first_frame = 366u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[4078u], .first_frame = 367u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[4089u], .first_frame = 368u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[4100u], .first_frame = 369u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[4111u], .first_frame = 370u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[4122u], .first_frame = 371u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[4133u], .first_frame = 372u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[4144u], .first_frame = 373u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[4155u], .first_frame = 374u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[4166u], .first_frame = 375u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[4177u], .first_frame = 376u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[4188u], .first_frame = 377u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[4199u], .first_frame = 378u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[4210u], .first_frame = 379u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[4221u], .first_frame = 380u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[4232u], .first_frame = 381u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[4243u], .first_frame = 382u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[4254u], .first_frame = 383u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[4265u], .first_frame = 384u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[4276u], .first_frame = 385u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[4287u], .first_frame = 386u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[4298u], .first_frame = 387u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[4309u], .first_frame = 388u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[4320u], .first_frame = 389u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[4331u], .first_frame = 390u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[4342u], .first_frame = 391u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[4353u], .first_frame = 392u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[4364u], .first_frame = 393u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[4375u], .first_frame = 394u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[4386u], .first_frame = 395u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[4397u], .first_frame = 396u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[4408u], .first_frame = 397u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[4419u], .first_frame = 398u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[4430u], .first_frame = 399u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[4441u], .first_frame = 400u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[4452u], .first_frame = 401u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[4463u], .first_frame = 402u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[4474u], .first_frame = 403u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[4485u], .first_frame = 404u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[4496u], .first_frame = 405u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[4507u], .first_frame = 406u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[4518u], .first_frame = 407u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[4529u], .first_frame = 408u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[4540u], .first_frame = 409u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[4551u], .first_frame = 410u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[4562u], .first_frame = 411u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[4573u], .first_frame = 412u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[4584u], .first_frame = 413u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[4595u], .first_frame = 414u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[4606u], .first_frame = 415u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[4617u], .first_frame = 416u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[4628u], .first_frame = 417u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[4639u], .first_frame = 418u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[4650u], .first_frame = 419u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[4661u], .first_frame = 420u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[4672u], .first_frame = 421u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[4683u], .first_frame = 422u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[4694u], .first_frame = 423u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[4705u], .first_frame = 424u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[4716u], .first_frame = 425u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[4727u], .first_frame = 426u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[4738u], .first_frame = 427u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[4749u], .first_frame = 428u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[4760u], .first_frame = 429u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[4771u], .first_frame = 430u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[4782u], .first_frame = 431u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[4793u], .first_frame = 432u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[4804u], .first_frame = 433u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[4815u], .first_frame = 434u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[4826u], .first_frame = 435u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[4837u], .first_frame = 436u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[4848u], .first_frame = 437u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[4859u], .first_frame = 438u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[4870u], .first_frame = 439u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[4881u], .first_frame = 440u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[4892u], .first_frame = 441u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[4903u], .first_frame = 442u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[4914u], .first_frame = 443u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[4925u], .first_frame = 444u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[4936u], .first_frame = 445u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[4947u], .first_frame = 446u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[4958u], .first_frame = 447u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[4969u], .first_frame = 448u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[4980u], .first_frame = 449u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[4991u], .first_frame = 450u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[5002u], .first_frame = 451u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[5013u], .first_frame = 452u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[5024u], .first_frame = 453u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[5035u], .first_frame = 454u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[5046u], .first_frame = 455u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[5057u], .first_frame = 456u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[5068u], .first_frame = 457u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[5079u], .first_frame = 458u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[5090u], .first_frame = 459u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[5101u], .first_frame = 460u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[5112u], .first_frame = 461u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[5123u], .first_frame = 462u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[5134u], .first_frame = 463u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[5145u], .first_frame = 464u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[5156u], .first_frame = 465u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[5167u], .first_frame = 466u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[5178u], .first_frame = 467u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[5189u], .first_frame = 468u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[5200u], .first_frame = 469u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[5211u], .first_frame = 470u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[5222u], .first_frame = 471u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[5233u], .first_frame = 472u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[5244u], .first_frame = 473u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[5255u], .first_frame = 474u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[5266u], .first_frame = 475u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[5277u], .first_frame = 476u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[5288u], .first_frame = 477u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[5299u], .first_frame = 478u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[5310u], .first_frame = 479u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[5321u], .first_frame = 480u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[5332u], .first_frame = 481u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[5343u], .first_frame = 482u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[5354u], .first_frame = 483u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[5365u], .first_frame = 484u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[5376u], .first_frame = 485u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[5387u], .first_frame = 486u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[5398u], .first_frame = 487u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[5409u], .first_frame = 488u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[5420u], .first_frame = 489u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[5431u], .first_frame = 490u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[5442u], .first_frame = 491u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[5453u], .first_frame = 492u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[5464u], .first_frame = 493u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[5475u], .first_frame = 494u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[5486u], .first_frame = 495u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[5497u], .first_frame = 496u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[5508u], .first_frame = 497u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[5519u], .first_frame = 498u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[5530u], .first_frame = 499u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[5541u], .first_frame = 500u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[5552u], .first_frame = 501u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[5563u], .first_frame = 502u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[5574u], .first_frame = 503u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[5585u], .first_frame = 504u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[5596u], .first_frame = 505u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[5607u], .first_frame = 506u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[5618u], .first_frame = 507u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[5629u], .first_frame = 508u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[5640u], .first_frame = 509u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[5651u], .first_frame = 510u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[5662u], .first_frame = 511u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[5673u], .first_frame = 512u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[5684u], .first_frame = 513u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[5695u], .first_frame = 514u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[5706u], .first_frame = 515u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[5717u], .first_frame = 516u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[5728u], .first_frame = 517u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[5739u], .first_frame = 518u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[5750u], .first_frame = 519u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[5761u], .first_frame = 520u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[5772u], .first_frame = 521u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[5783u], .first_frame = 522u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[5794u], .first_frame = 523u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[5805u], .first_frame = 524u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[5816u], .first_frame = 525u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[5827u], .first_frame = 526u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[5838u], .first_frame = 527u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[5849u], .first_frame = 528u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[5860u], .first_frame = 529u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[5871u], .first_frame = 530u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[5882u], .first_frame = 531u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[5893u], .first_frame = 532u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[5904u], .first_frame = 533u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[5915u], .first_frame = 534u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[5926u], .first_frame = 535u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[5937u], .first_frame = 536u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[5948u], .first_frame = 537u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[5959u], .first_frame = 538u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[5970u], .first_frame = 539u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[5981u], .first_frame = 540u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[5992u], .first_frame = 541u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[6003u], .first_frame = 542u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[6014u], .first_frame = 543u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[6025u], .first_frame = 544u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[6036u], .first_frame = 545u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[6047u], .first_frame = 546u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[6058u], .first_frame = 547u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[6069u], .first_frame = 548u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[6080u], .first_frame = 549u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[6091u], .first_frame = 550u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[6102u], .first_frame = 551u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[6113u], .first_frame = 552u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[6124u], .first_frame = 553u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[6135u], .first_frame = 554u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[6146u], .first_frame = 555u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[6157u], .first_frame = 556u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[6168u], .first_frame = 557u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[6179u], .first_frame = 558u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[6190u], .first_frame = 559u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[6201u], .first_frame = 560u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[6212u], .first_frame = 561u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[6223u], .first_frame = 562u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[6234u], .first_frame = 563u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[6245u], .first_frame = 564u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[6256u], .first_frame = 565u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[6267u], .first_frame = 566u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[6278u], .first_frame = 567u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[6289u], .first_frame = 568u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[6300u], .first_frame = 569u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[6311u], .first_frame = 570u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[6322u], .first_frame = 571u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[6333u], .first_frame = 572u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[6344u], .first_frame = 573u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[6355u], .first_frame = 574u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[6366u], .first_frame = 575u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[6377u], .first_frame = 576u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[6388u], .first_frame = 577u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[6399u], .first_frame = 578u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[6410u], .first_frame = 579u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[6421u], .first_frame = 580u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[6432u], .first_frame = 581u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[6443u], .first_frame = 582u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[6454u], .first_frame = 583u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[6465u], .first_frame = 584u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[6476u], .first_frame = 585u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[6487u], .first_frame = 586u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[6498u], .first_frame = 587u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[6509u], .first_frame = 588u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[6520u], .first_frame = 589u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[6531u], .first_frame = 590u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[6542u], .first_frame = 591u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[6553u], .first_frame = 592u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[6564u], .first_frame = 593u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[6575u], .first_frame = 594u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[6586u], .first_frame = 595u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[6597u], .first_frame = 596u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[6608u], .first_frame = 597u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[6619u], .first_frame = 598u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[6630u], .first_frame = 599u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[6641u], .first_frame = 600u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[6652u], .first_frame = 601u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[6663u], .first_frame = 602u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[6674u], .first_frame = 603u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[6685u], .first_frame = 604u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[6696u], .first_frame = 605u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[6707u], .first_frame = 606u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[6718u], .first_frame = 607u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[6729u], .first_frame = 608u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[6740u], .first_frame = 609u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[6751u], .first_frame = 610u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[6762u], .first_frame = 611u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[6773u], .first_frame = 612u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[6784u], .first_frame = 613u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[6795u], .first_frame = 614u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[6806u], .first_frame = 615u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[6817u], .first_frame = 616u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[6828u], .first_frame = 617u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[6839u], .first_frame = 618u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[6850u], .first_frame = 619u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[6861u], .first_frame = 620u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[6872u], .first_frame = 621u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[6883u], .first_frame = 622u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[6894u], .first_frame = 623u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[6905u], .first_frame = 624u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[6916u], .first_frame = 625u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[6927u], .first_frame = 626u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[6938u], .first_frame = 627u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[6949u], .first_frame = 628u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[6960u], .first_frame = 629u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[6971u], .first_frame = 630u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[6982u], .first_frame = 631u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[6993u], .first_frame = 632u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[7004u], .first_frame = 633u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[7015u], .first_frame = 634u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[7026u], .first_frame = 635u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[7037u], .first_frame = 636u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[7048u], .first_frame = 637u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[7059u], .first_frame = 638u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[7070u], .first_frame = 639u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[7081u], .first_frame = 640u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[7092u], .first_frame = 641u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[7103u], .first_frame = 642u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[7114u], .first_frame = 643u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[7125u], .first_frame = 644u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[7136u], .first_frame = 645u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[7147u], .first_frame = 646u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[7158u], .first_frame = 647u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[7169u], .first_frame = 648u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[7180u], .first_frame = 649u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[7191u], .first_frame = 650u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[7202u], .first_frame = 651u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[7213u], .first_frame = 652u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[7224u], .first_frame = 653u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[7235u], .first_frame = 654u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[7246u], .first_frame = 655u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[7257u], .first_frame = 656u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[7268u], .first_frame = 657u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[7279u], .first_frame = 658u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[7290u], .first_frame = 659u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[7301u], .first_frame = 660u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[7312u], .first_frame = 661u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[7323u], .first_frame = 662u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[7334u], .first_frame = 663u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[7345u], .first_frame = 664u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[7356u], .first_frame = 665u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[7367u], .first_frame = 666u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[7378u], .first_frame = 667u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[7389u], .first_frame = 668u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[7400u], .first_frame = 669u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[7411u], .first_frame = 670u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[7422u], .first_frame = 671u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[7433u], .first_frame = 672u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[7444u], .first_frame = 673u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[7455u], .first_frame = 674u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[7466u], .first_frame = 675u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[7477u], .first_frame = 676u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[7488u], .first_frame = 677u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[7499u], .first_frame = 678u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[7510u], .first_frame = 679u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[7521u], .first_frame = 680u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[7532u], .first_frame = 681u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[7543u], .first_frame = 682u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[7554u], .first_frame = 683u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[7565u], .first_frame = 684u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[7576u], .first_frame = 685u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[7587u], .first_frame = 686u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[7598u], .first_frame = 687u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[7609u], .first_frame = 688u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[7620u], .first_frame = 689u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[7631u], .first_frame = 690u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[7642u], .first_frame = 691u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[7653u], .first_frame = 692u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[7664u], .first_frame = 693u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[7675u], .first_frame = 694u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[7686u], .first_frame = 695u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[7697u], .first_frame = 696u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[7708u], .first_frame = 697u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[7719u], .first_frame = 698u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[7730u], .first_frame = 699u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[7741u], .first_frame = 700u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[7752u], .first_frame = 701u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[7763u], .first_frame = 702u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[7774u], .first_frame = 703u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[7785u], .first_frame = 704u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[7796u], .first_frame = 705u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[7807u], .first_frame = 706u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[7818u], .first_frame = 707u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[7829u], .first_frame = 708u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[7840u], .first_frame = 709u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[7851u], .first_frame = 710u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[7862u], .first_frame = 711u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[7873u], .first_frame = 712u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[7884u], .first_frame = 713u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[7895u], .first_frame = 714u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[7906u], .first_frame = 715u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[7917u], .first_frame = 716u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[7928u], .first_frame = 717u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[7939u], .first_frame = 718u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[7950u], .first_frame = 719u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[7961u], .first_frame = 720u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[7972u], .first_frame = 721u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[7983u], .first_frame = 722u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[7994u], .first_frame = 723u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[8005u], .first_frame = 724u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[8016u], .first_frame = 725u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[8027u], .first_frame = 726u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[8038u], .first_frame = 727u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[8049u], .first_frame = 728u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[8060u], .first_frame = 729u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[8071u], .first_frame = 730u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[8082u], .first_frame = 731u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[8093u], .first_frame = 732u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[8104u], .first_frame = 733u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[8115u], .first_frame = 734u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[8126u], .first_frame = 735u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[8137u], .first_frame = 736u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[8148u], .first_frame = 737u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[8159u], .first_frame = 738u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[8170u], .first_frame = 739u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[8181u], .first_frame = 740u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[8192u], .first_frame = 741u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[8203u], .first_frame = 742u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[8214u], .first_frame = 743u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[8225u], .first_frame = 744u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[8236u], .first_frame = 745u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[8247u], .first_frame = 746u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[8258u], .first_frame = 747u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[8269u], .first_frame = 748u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[8280u], .first_frame = 749u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[8291u], .first_frame = 750u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[8302u], .first_frame = 751u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[8313u], .first_frame = 752u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[8324u], .first_frame = 753u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[8335u], .first_frame = 754u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[8346u], .first_frame = 755u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[8357u], .first_frame = 756u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[8368u], .first_frame = 757u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[8379u], .first_frame = 758u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[8390u], .first_frame = 759u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[8401u], .first_frame = 760u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[8412u], .first_frame = 761u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[8423u], .first_frame = 762u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[8434u], .first_frame = 763u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[8445u], .first_frame = 764u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[8456u], .first_frame = 765u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[8467u], .first_frame = 766u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[8478u], .first_frame = 767u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[8489u], .first_frame = 768u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[8500u], .first_frame = 769u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[8511u], .first_frame = 770u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[8522u], .first_frame = 771u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[8533u], .first_frame = 772u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[8544u], .first_frame = 773u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[8555u], .first_frame = 774u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[8566u], .first_frame = 775u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[8577u], .first_frame = 776u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[8588u], .first_frame = 777u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[8599u], .first_frame = 778u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[8610u], .first_frame = 779u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[8621u], .first_frame = 780u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[8632u], .first_frame = 781u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[8643u], .first_frame = 782u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[8654u], .first_frame = 783u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[8665u], .first_frame = 784u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[8676u], .first_frame = 785u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[8687u], .first_frame = 786u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[8698u], .first_frame = 787u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[8709u], .first_frame = 788u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[8720u], .first_frame = 789u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[8731u], .first_frame = 790u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[8742u], .first_frame = 791u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[8753u], .first_frame = 792u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[8764u], .first_frame = 793u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[8775u], .first_frame = 794u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[8786u], .first_frame = 795u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[8797u], .first_frame = 796u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[8808u], .first_frame = 797u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[8819u], .first_frame = 798u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[8830u], .first_frame = 799u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[8841u], .first_frame = 800u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[8852u], .first_frame = 801u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[8863u], .first_frame = 802u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[8874u], .first_frame = 803u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[8885u], .first_frame = 804u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[8896u], .first_frame = 805u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[8907u], .first_frame = 806u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[8918u], .first_frame = 807u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[8929u], .first_frame = 808u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[8940u], .first_frame = 809u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[8951u], .first_frame = 810u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[8962u], .first_frame = 811u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[8973u], .first_frame = 812u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[8984u], .first_frame = 813u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[8995u], .first_frame = 814u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[9006u], .first_frame = 815u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[9017u], .first_frame = 816u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[9028u], .first_frame = 817u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[9039u], .first_frame = 818u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[9050u], .first_frame = 819u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[9061u], .first_frame = 820u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[9072u], .first_frame = 821u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[9083u], .first_frame = 822u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[9094u], .first_frame = 823u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[9105u], .first_frame = 824u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[9116u], .first_frame = 825u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[9127u], .first_frame = 826u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[9138u], .first_frame = 827u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[9149u], .first_frame = 828u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[9160u], .first_frame = 829u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[9171u], .first_frame = 830u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[9182u], .first_frame = 831u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[9193u], .first_frame = 832u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[9204u], .first_frame = 833u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[9215u], .first_frame = 834u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[9226u], .first_frame = 835u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[9237u], .first_frame = 836u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[9248u], .first_frame = 837u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[9259u], .first_frame = 838u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[9270u], .first_frame = 839u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[9281u], .first_frame = 840u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[9292u], .first_frame = 841u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[9303u], .first_frame = 842u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[9314u], .first_frame = 843u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[9325u], .first_frame = 844u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[9336u], .first_frame = 845u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[9347u], .first_frame = 846u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[9358u], .first_frame = 847u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[9369u], .first_frame = 848u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[9380u], .first_frame = 849u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[9391u], .first_frame = 850u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[9402u], .first_frame = 851u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[9413u], .first_frame = 852u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[9424u], .first_frame = 853u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[9435u], .first_frame = 854u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[9446u], .first_frame = 855u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[9457u], .first_frame = 856u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[9468u], .first_frame = 857u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[9479u], .first_frame = 858u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[9490u], .first_frame = 859u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[9501u], .first_frame = 860u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[9512u], .first_frame = 861u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[9523u], .first_frame = 862u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[9534u], .first_frame = 863u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[9545u], .first_frame = 864u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[9556u], .first_frame = 865u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[9567u], .first_frame = 866u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[9578u], .first_frame = 867u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[9589u], .first_frame = 868u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[9600u], .first_frame = 869u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[9611u], .first_frame = 870u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[9622u], .first_frame = 871u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[9633u], .first_frame = 872u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[9644u], .first_frame = 873u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[9655u], .first_frame = 874u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[9666u], .first_frame = 875u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[9677u], .first_frame = 876u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[9688u], .first_frame = 877u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[9699u], .first_frame = 878u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[9710u], .first_frame = 879u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[9721u], .first_frame = 880u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[9732u], .first_frame = 881u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[9743u], .first_frame = 882u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[9754u], .first_frame = 883u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[9765u], .first_frame = 884u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[9776u], .first_frame = 885u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[9787u], .first_frame = 886u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[9798u], .first_frame = 887u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[9809u], .first_frame = 888u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[9820u], .first_frame = 889u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[9831u], .first_frame = 890u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[9842u], .first_frame = 891u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[9853u], .first_frame = 892u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[9864u], .first_frame = 893u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[9875u], .first_frame = 894u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[9886u], .first_frame = 895u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[9897u], .first_frame = 896u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[9908u], .first_frame = 897u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[9919u], .first_frame = 898u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[9930u], .first_frame = 899u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[9941u], .first_frame = 900u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[9952u], .first_frame = 901u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[9963u], .first_frame = 902u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[9974u], .first_frame = 903u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[9985u], .first_frame = 904u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[9996u], .first_frame = 905u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[10007u], .first_frame = 906u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[10018u], .first_frame = 907u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[10029u], .first_frame = 908u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[10040u], .first_frame = 909u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[10051u], .first_frame = 910u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[10062u], .first_frame = 911u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[10073u], .first_frame = 912u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[10084u], .first_frame = 913u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[10095u], .first_frame = 914u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[10106u], .first_frame = 915u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[10117u], .first_frame = 916u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[10128u], .first_frame = 917u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[10139u], .first_frame = 918u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[10150u], .first_frame = 919u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[10161u], .first_frame = 920u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[10172u], .first_frame = 921u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[10183u], .first_frame = 922u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[10194u], .first_frame = 923u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[10205u], .first_frame = 924u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[10216u], .first_frame = 925u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[10227u], .first_frame = 926u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[10238u], .first_frame = 927u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[10249u], .first_frame = 928u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[10260u], .first_frame = 929u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[10271u], .first_frame = 930u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[10282u], .first_frame = 931u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[10293u], .first_frame = 932u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[10304u], .first_frame = 933u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[10315u], .first_frame = 934u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[10326u], .first_frame = 935u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[10337u], .first_frame = 936u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[10348u], .first_frame = 937u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[10359u], .first_frame = 938u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[10370u], .first_frame = 939u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[10381u], .first_frame = 940u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[10392u], .first_frame = 941u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[10403u], .first_frame = 942u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[10414u], .first_frame = 943u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[10425u], .first_frame = 944u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[10436u], .first_frame = 945u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[10447u], .first_frame = 946u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[10458u], .first_frame = 947u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[10469u], .first_frame = 948u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[10480u], .first_frame = 949u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[10491u], .first_frame = 950u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[10502u], .first_frame = 951u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[10513u], .first_frame = 952u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[10524u], .first_frame = 953u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[10535u], .first_frame = 954u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[10546u], .first_frame = 955u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[10557u], .first_frame = 956u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[10568u], .first_frame = 957u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[10579u], .first_frame = 958u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[10590u], .first_frame = 959u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[10601u], .first_frame = 960u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[10612u], .first_frame = 961u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[10623u], .first_frame = 962u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[10634u], .first_frame = 963u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[10645u], .first_frame = 964u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[10656u], .first_frame = 965u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[10667u], .first_frame = 966u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[10678u], .first_frame = 967u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[10689u], .first_frame = 968u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[10700u], .first_frame = 969u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[10711u], .first_frame = 970u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[10722u], .first_frame = 971u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[10733u], .first_frame = 972u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[10744u], .first_frame = 973u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[10755u], .first_frame = 974u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[10766u], .first_frame = 975u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[10777u], .first_frame = 976u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[10788u], .first_frame = 977u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[10799u], .first_frame = 978u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[10810u], .first_frame = 979u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[10821u], .first_frame = 980u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[10832u], .first_frame = 981u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[10843u], .first_frame = 982u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[10854u], .first_frame = 983u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[10865u], .first_frame = 984u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[10876u], .first_frame = 985u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[10887u], .first_frame = 986u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[10898u], .first_frame = 987u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[10909u], .first_frame = 988u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[10920u], .first_frame = 989u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[10931u], .first_frame = 990u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[10942u], .first_frame = 991u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[10953u], .first_frame = 992u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[10964u], .first_frame = 993u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[10975u], .first_frame = 994u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[10986u], .first_frame = 995u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[10997u], .first_frame = 996u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[11008u], .first_frame = 997u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[11019u], .first_frame = 998u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[11030u], .first_frame = 999u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[11041u], .first_frame = 1000u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[11052u], .first_frame = 1001u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[11063u], .first_frame = 1002u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[11074u], .first_frame = 1003u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[11085u], .first_frame = 1004u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[11096u], .first_frame = 1005u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[11107u], .first_frame = 1006u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[11118u], .first_frame = 1007u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[11129u], .first_frame = 1008u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[11140u], .first_frame = 1009u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[11151u], .first_frame = 1010u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[11162u], .first_frame = 1011u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[11173u], .first_frame = 1012u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[11184u], .first_frame = 1013u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[11195u], .first_frame = 1014u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[11206u], .first_frame = 1015u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[11217u], .first_frame = 1016u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[11228u], .first_frame = 1017u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[11239u], .first_frame = 1018u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[11250u], .first_frame = 1019u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[11261u], .first_frame = 1020u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[11272u], .first_frame = 1021u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[11283u], .first_frame = 1022u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[11294u], .first_frame = 1023u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[11305u], .first_frame = 1024u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[11316u], .first_frame = 1025u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[11327u], .first_frame = 1026u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[11338u], .first_frame = 1027u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[11349u], .first_frame = 1028u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[11360u], .first_frame = 1029u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[11371u], .first_frame = 1030u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[11382u], .first_frame = 1031u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[11393u], .first_frame = 1032u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[11404u], .first_frame = 1033u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[11415u], .first_frame = 1034u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[11426u], .first_frame = 1035u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[11437u], .first_frame = 1036u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[11448u], .first_frame = 1037u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[11459u], .first_frame = 1038u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[11470u], .first_frame = 1039u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[11481u], .first_frame = 1040u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[11492u], .first_frame = 1041u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[11503u], .first_frame = 1042u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[11514u], .first_frame = 1043u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[11525u], .first_frame = 1044u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[11536u], .first_frame = 1045u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[11547u], .first_frame = 1046u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[11558u], .first_frame = 1047u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[11569u], .first_frame = 1048u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[11580u], .first_frame = 1049u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[11591u], .first_frame = 1050u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[11602u], .first_frame = 1051u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[11613u], .first_frame = 1052u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[11624u], .first_frame = 1053u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[11635u], .first_frame = 1054u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[11646u], .first_frame = 1055u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[11657u], .first_frame = 1056u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[11668u], .first_frame = 1057u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[11679u], .first_frame = 1058u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[11690u], .first_frame = 1059u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[11701u], .first_frame = 1060u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[11712u], .first_frame = 1061u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[11723u], .first_frame = 1062u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[11734u], .first_frame = 1063u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[11745u], .first_frame = 1064u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[11756u], .first_frame = 1065u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[11767u], .first_frame = 1066u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[11778u], .first_frame = 1067u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[11789u], .first_frame = 1068u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[11800u], .first_frame = 1069u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[11811u], .first_frame = 1070u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[11822u], .first_frame = 1071u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[11833u], .first_frame = 1072u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[11844u], .first_frame = 1073u, .frame_count = 3u, .loop_start = 0u, .loop_end = 3u},
  {.name = (const char *)&companion_browser_cemp_strings[11849u], .first_frame = 1076u, .frame_count = 3u, .loop_start = 0u, .loop_end = 3u},
  {.name = (const char *)&companion_browser_cemp_strings[11855u], .first_frame = 1079u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[11866u], .first_frame = 1080u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[11878u], .first_frame = 1081u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[11887u], .first_frame = 1082u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[11898u], .first_frame = 1083u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[11908u], .first_frame = 1084u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[11917u], .first_frame = 1085u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[11926u], .first_frame = 1086u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[11932u], .first_frame = 1087u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[11939u], .first_frame = 1088u, .frame_count = 3u, .loop_start = 0u, .loop_end = 3u},
  {.name = (const char *)&companion_browser_cemp_strings[11949u], .first_frame = 1091u, .frame_count = 3u, .loop_start = 0u, .loop_end = 3u},
  {.name = (const char *)&companion_browser_cemp_strings[11957u], .first_frame = 1094u, .frame_count = 3u, .loop_start = 0u, .loop_end = 3u},
  {.name = (const char *)&companion_browser_cemp_strings[11966u], .first_frame = 1097u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[11980u], .first_frame = 1098u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[11992u], .first_frame = 1099u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[11998u], .first_frame = 1100u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[12008u], .first_frame = 1101u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[12015u], .first_frame = 1102u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[12021u], .first_frame = 1103u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[12027u], .first_frame = 1104u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[12032u], .first_frame = 1105u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[12049u], .first_frame = 1106u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[12067u], .first_frame = 1107u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[12080u], .first_frame = 1108u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[12099u], .first_frame = 1109u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[12114u], .first_frame = 1110u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[12130u], .first_frame = 1111u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[12150u], .first_frame = 1112u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[12165u], .first_frame = 1113u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
  {.name = (const char *)&companion_browser_cemp_strings[12186u], .first_frame = 1114u, .frame_count = 10u, .loop_start = 0u, .loop_end = 10u},
  {.name = (const char *)&companion_browser_cemp_strings[12208u], .first_frame = 1124u, .frame_count = 10u, .loop_start = 0u, .loop_end = 10u},
  {.name = (const char *)&companion_browser_cemp_strings[12228u], .first_frame = 1134u, .frame_count = 10u, .loop_start = 0u, .loop_end = 10u},
  {.name = (const char *)&companion_browser_cemp_strings[12248u], .first_frame = 1144u, .frame_count = 10u, .loop_start = 0u, .loop_end = 10u},
  {.name = (const char *)&companion_browser_cemp_strings[12269u], .first_frame = 1154u, .frame_count = 5u, .loop_start = 0u, .loop_end = 5u},
  {.name = (const char *)&companion_browser_cemp_strings[12287u], .first_frame = 1159u, .frame_count = 5u, .loop_start = 0u, .loop_end = 5u},
  {.name = (const char *)&companion_browser_cemp_strings[12314u], .first_frame = 1164u, .frame_count = 5u, .loop_start = 0u, .loop_end = 5u},
  {.name = (const char *)&companion_browser_cemp_strings[12339u], .first_frame = 1169u, .frame_count = 5u, .loop_start = 0u, .loop_end = 5u},
  {.name = (const char *)&companion_browser_cemp_strings[12364u], .first_frame = 1174u, .frame_count = 5u, .loop_start = 0u, .loop_end = 5u},
  {.name = (const char *)&companion_browser_cemp_strings[12390u], .first_frame = 1179u, .frame_count = 5u, .loop_start = 0u, .loop_end = 5u},
  {.name = (const char *)&companion_browser_cemp_strings[12413u], .first_frame = 1184u, .frame_count = 5u, .loop_start = 0u, .loop_end = 5u},
  {.name = (const char *)&companion_browser_cemp_strings[12443u], .first_frame = 1189u, .frame_count = 5u, .loop_start = 0u, .loop_end = 5u},
  {.name = (const char *)&companion_browser_cemp_strings[12471u], .first_frame = 1194u, .frame_count = 5u, .loop_start = 0u, .loop_end = 5u},
  {.name = (const char *)&companion_browser_cemp_strings[12499u], .first_frame = 1199u, .frame_count = 5u, .loop_start = 0u, .loop_end = 5u},
  {.name = (const char *)&companion_browser_cemp_strings[12528u], .first_frame = 1204u, .frame_count = 5u, .loop_start = 0u, .loop_end = 5u},
  {.name = (const char *)&companion_browser_cemp_strings[12554u], .first_frame = 1209u, .frame_count = 5u, .loop_start = 0u, .loop_end = 5u},
  {.name = (const char *)&companion_browser_cemp_strings[12584u], .first_frame = 1214u, .frame_count = 5u, .loop_start = 0u, .loop_end = 5u},
  {.name = (const char *)&companion_browser_cemp_strings[12612u], .first_frame = 1219u, .frame_count = 5u, .loop_start = 0u, .loop_end = 5u},
  {.name = (const char *)&companion_browser_cemp_strings[12640u], .first_frame = 1224u, .frame_count = 5u, .loop_start = 0u, .loop_end = 5u},
  {.name = (const char *)&companion_browser_cemp_strings[12669u], .first_frame = 1229u, .frame_count = 5u, .loop_start = 0u, .loop_end = 5u},
  {.name = (const char *)&companion_browser_cemp_strings[12695u], .first_frame = 1234u, .frame_count = 5u, .loop_start = 0u, .loop_end = 5u},
  {.name = (const char *)&companion_browser_cemp_strings[12724u], .first_frame = 1239u, .frame_count = 5u, .loop_start = 0u, .loop_end = 5u},
  {.name = (const char *)&companion_browser_cemp_strings[12751u], .first_frame = 1244u, .frame_count = 5u, .loop_start = 0u, .loop_end = 5u},
  {.name = (const char *)&companion_browser_cemp_strings[12778u], .first_frame = 1249u, .frame_count = 5u, .loop_start = 0u, .loop_end = 5u},
  {.name = (const char *)&companion_browser_cemp_strings[12806u], .first_frame = 1254u, .frame_count = 5u, .loop_start = 0u, .loop_end = 5u},
  {.name = (const char *)&companion_browser_cemp_strings[12831u], .first_frame = 1259u, .frame_count = 5u, .loop_start = 0u, .loop_end = 5u},
  {.name = (const char *)&companion_browser_cemp_strings[12863u], .first_frame = 1264u, .frame_count = 5u, .loop_start = 0u, .loop_end = 5u},
  {.name = (const char *)&companion_browser_cemp_strings[12893u], .first_frame = 1269u, .frame_count = 5u, .loop_start = 0u, .loop_end = 5u},
  {.name = (const char *)&companion_browser_cemp_strings[12923u], .first_frame = 1274u, .frame_count = 5u, .loop_start = 0u, .loop_end = 5u},
  {.name = (const char *)&companion_browser_cemp_strings[12954u], .first_frame = 1279u, .frame_count = 5u, .loop_start = 0u, .loop_end = 5u},
  {.name = (const char *)&companion_browser_cemp_strings[12982u], .first_frame = 1284u, .frame_count = 5u, .loop_start = 0u, .loop_end = 5u},
  {.name = (const char *)&companion_browser_cemp_strings[13011u], .first_frame = 1289u, .frame_count = 5u, .loop_start = 0u, .loop_end = 5u},
  {.name = (const char *)&companion_browser_cemp_strings[13038u], .first_frame = 1294u, .frame_count = 5u, .loop_start = 0u, .loop_end = 5u},
  {.name = (const char *)&companion_browser_cemp_strings[13065u], .first_frame = 1299u, .frame_count = 5u, .loop_start = 0u, .loop_end = 5u},
  {.name = (const char *)&companion_browser_cemp_strings[13093u], .first_frame = 1304u, .frame_count = 5u, .loop_start = 0u, .loop_end = 5u},
  {.name = (const char *)&companion_browser_cemp_strings[13118u], .first_frame = 1309u, .frame_count = 5u, .loop_start = 0u, .loop_end = 5u},
  {.name = (const char *)&companion_browser_cemp_strings[13147u], .first_frame = 1314u, .frame_count = 5u, .loop_start = 0u, .loop_end = 5u},
  {.name = (const char *)&companion_browser_cemp_strings[13174u], .first_frame = 1319u, .frame_count = 5u, .loop_start = 0u, .loop_end = 5u},
  {.name = (const char *)&companion_browser_cemp_strings[13201u], .first_frame = 1324u, .frame_count = 5u, .loop_start = 0u, .loop_end = 5u},
  {.name = (const char *)&companion_browser_cemp_strings[13229u], .first_frame = 1329u, .frame_count = 5u, .loop_start = 0u, .loop_end = 5u},
  {.name = (const char *)&companion_browser_cemp_strings[13254u], .first_frame = 1334u, .frame_count = 5u, .loop_start = 0u, .loop_end = 5u},
  {.name = (const char *)&companion_browser_cemp_strings[13282u], .first_frame = 1339u, .frame_count = 5u, .loop_start = 0u, .loop_end = 5u},
  {.name = (const char *)&companion_browser_cemp_strings[13308u], .first_frame = 1344u, .frame_count = 5u, .loop_start = 0u, .loop_end = 5u},
  {.name = (const char *)&companion_browser_cemp_strings[13334u], .first_frame = 1349u, .frame_count = 5u, .loop_start = 0u, .loop_end = 5u},
  {.name = (const char *)&companion_browser_cemp_strings[13361u], .first_frame = 1354u, .frame_count = 5u, .loop_start = 0u, .loop_end = 5u},
  {.name = (const char *)&companion_browser_cemp_strings[13385u], .first_frame = 1359u, .frame_count = 5u, .loop_start = 0u, .loop_end = 5u},
  {.name = (const char *)&companion_browser_cemp_strings[13411u], .first_frame = 1364u, .frame_count = 5u, .loop_start = 0u, .loop_end = 5u},
  {.name = (const char *)&companion_browser_cemp_strings[13435u], .first_frame = 1369u, .frame_count = 5u, .loop_start = 0u, .loop_end = 5u},
  {.name = (const char *)&companion_browser_cemp_strings[13459u], .first_frame = 1374u, .frame_count = 5u, .loop_start = 0u, .loop_end = 5u},
  {.name = (const char *)&companion_browser_cemp_strings[13484u], .first_frame = 1379u, .frame_count = 5u, .loop_start = 0u, .loop_end = 5u},
  {.name = (const char *)&companion_browser_cemp_strings[13506u], .first_frame = 1384u, .frame_count = 5u, .loop_start = 0u, .loop_end = 5u},
  {.name = (const char *)&companion_browser_cemp_strings[13536u], .first_frame = 1389u, .frame_count = 5u, .loop_start = 0u, .loop_end = 5u},
  {.name = (const char *)&companion_browser_cemp_strings[13564u], .first_frame = 1394u, .frame_count = 5u, .loop_start = 0u, .loop_end = 5u},
  {.name = (const char *)&companion_browser_cemp_strings[13592u], .first_frame = 1399u, .frame_count = 5u, .loop_start = 0u, .loop_end = 5u},
  {.name = (const char *)&companion_browser_cemp_strings[13621u], .first_frame = 1404u, .frame_count = 5u, .loop_start = 0u, .loop_end = 5u},
  {.name = (const char *)&companion_browser_cemp_strings[13647u], .first_frame = 1409u, .frame_count = 5u, .loop_start = 0u, .loop_end = 5u},
  {.name = (const char *)&companion_browser_cemp_strings[13676u], .first_frame = 1414u, .frame_count = 5u, .loop_start = 0u, .loop_end = 5u},
  {.name = (const char *)&companion_browser_cemp_strings[13703u], .first_frame = 1419u, .frame_count = 5u, .loop_start = 0u, .loop_end = 5u},
  {.name = (const char *)&companion_browser_cemp_strings[13730u], .first_frame = 1424u, .frame_count = 5u, .loop_start = 0u, .loop_end = 5u},
  {.name = (const char *)&companion_browser_cemp_strings[13758u], .first_frame = 1429u, .frame_count = 5u, .loop_start = 0u, .loop_end = 5u},
  {.name = (const char *)&companion_browser_cemp_strings[13783u], .first_frame = 1434u, .frame_count = 5u, .loop_start = 0u, .loop_end = 5u},
  {.name = (const char *)&companion_browser_cemp_strings[13815u], .first_frame = 1439u, .frame_count = 5u, .loop_start = 0u, .loop_end = 5u},
  {.name = (const char *)&companion_browser_cemp_strings[13845u], .first_frame = 1444u, .frame_count = 5u, .loop_start = 0u, .loop_end = 5u},
  {.name = (const char *)&companion_browser_cemp_strings[13875u], .first_frame = 1449u, .frame_count = 5u, .loop_start = 0u, .loop_end = 5u},
  {.name = (const char *)&companion_browser_cemp_strings[13906u], .first_frame = 1454u, .frame_count = 5u, .loop_start = 0u, .loop_end = 5u},
  {.name = (const char *)&companion_browser_cemp_strings[13934u], .first_frame = 1459u, .frame_count = 5u, .loop_start = 0u, .loop_end = 5u},
  {.name = (const char *)&companion_browser_cemp_strings[13966u], .first_frame = 1464u, .frame_count = 5u, .loop_start = 0u, .loop_end = 5u},
  {.name = (const char *)&companion_browser_cemp_strings[13996u], .first_frame = 1469u, .frame_count = 5u, .loop_start = 0u, .loop_end = 5u},
  {.name = (const char *)&companion_browser_cemp_strings[14026u], .first_frame = 1474u, .frame_count = 5u, .loop_start = 0u, .loop_end = 5u},
  {.name = (const char *)&companion_browser_cemp_strings[14057u], .first_frame = 1479u, .frame_count = 5u, .loop_start = 0u, .loop_end = 5u},
  {.name = (const char *)&companion_browser_cemp_strings[14085u], .first_frame = 1484u, .frame_count = 5u, .loop_start = 0u, .loop_end = 5u},
  {.name = (const char *)&companion_browser_cemp_strings[14120u], .first_frame = 1489u, .frame_count = 5u, .loop_start = 0u, .loop_end = 5u},
  {.name = (const char *)&companion_browser_cemp_strings[14153u], .first_frame = 1494u, .frame_count = 5u, .loop_start = 0u, .loop_end = 5u},
  {.name = (const char *)&companion_browser_cemp_strings[14186u], .first_frame = 1499u, .frame_count = 5u, .loop_start = 0u, .loop_end = 5u},
  {.name = (const char *)&companion_browser_cemp_strings[14220u], .first_frame = 1504u, .frame_count = 5u, .loop_start = 0u, .loop_end = 5u},
  {.name = (const char *)&companion_browser_cemp_strings[14251u], .first_frame = 1509u, .frame_count = 5u, .loop_start = 0u, .loop_end = 5u},
  {.name = (const char *)&companion_browser_cemp_strings[14280u], .first_frame = 1514u, .frame_count = 5u, .loop_start = 0u, .loop_end = 5u},
  {.name = (const char *)&companion_browser_cemp_strings[14307u], .first_frame = 1519u, .frame_count = 5u, .loop_start = 0u, .loop_end = 5u},
  {.name = (const char *)&companion_browser_cemp_strings[14334u], .first_frame = 1524u, .frame_count = 5u, .loop_start = 0u, .loop_end = 5u},
  {.name = (const char *)&companion_browser_cemp_strings[14362u], .first_frame = 1529u, .frame_count = 5u, .loop_start = 0u, .loop_end = 5u},
  {.name = (const char *)&companion_browser_cemp_strings[14387u], .first_frame = 1534u, .frame_count = 5u, .loop_start = 0u, .loop_end = 5u},
  {.name = (const char *)&companion_browser_cemp_strings[14418u], .first_frame = 1539u, .frame_count = 5u, .loop_start = 0u, .loop_end = 5u},
  {.name = (const char *)&companion_browser_cemp_strings[14447u], .first_frame = 1544u, .frame_count = 5u, .loop_start = 0u, .loop_end = 5u},
  {.name = (const char *)&companion_browser_cemp_strings[14476u], .first_frame = 1549u, .frame_count = 5u, .loop_start = 0u, .loop_end = 5u},
  {.name = (const char *)&companion_browser_cemp_strings[14506u], .first_frame = 1554u, .frame_count = 5u, .loop_start = 0u, .loop_end = 5u},
  {.name = (const char *)&companion_browser_cemp_strings[14533u], .first_frame = 1559u, .frame_count = 5u, .loop_start = 0u, .loop_end = 5u},
  {.name = (const char *)&companion_browser_cemp_strings[14567u], .first_frame = 1564u, .frame_count = 5u, .loop_start = 0u, .loop_end = 5u},
  {.name = (const char *)&companion_browser_cemp_strings[14599u], .first_frame = 1569u, .frame_count = 5u, .loop_start = 0u, .loop_end = 5u},
  {.name = (const char *)&companion_browser_cemp_strings[14631u], .first_frame = 1574u, .frame_count = 5u, .loop_start = 0u, .loop_end = 5u},
  {.name = (const char *)&companion_browser_cemp_strings[14664u], .first_frame = 1579u, .frame_count = 5u, .loop_start = 0u, .loop_end = 5u},
  {.name = (const char *)&companion_browser_cemp_strings[14694u], .first_frame = 1584u, .frame_count = 5u, .loop_start = 0u, .loop_end = 5u},
  {.name = (const char *)&companion_browser_cemp_strings[14725u], .first_frame = 1589u, .frame_count = 5u, .loop_start = 0u, .loop_end = 5u},
  {.name = (const char *)&companion_browser_cemp_strings[14754u], .first_frame = 1594u, .frame_count = 5u, .loop_start = 0u, .loop_end = 5u},
  {.name = (const char *)&companion_browser_cemp_strings[14783u], .first_frame = 1599u, .frame_count = 5u, .loop_start = 0u, .loop_end = 5u},
  {.name = (const char *)&companion_browser_cemp_strings[14813u], .first_frame = 1604u, .frame_count = 5u, .loop_start = 0u, .loop_end = 5u},
  {.name = (const char *)&companion_browser_cemp_strings[14840u], .first_frame = 1609u, .frame_count = 5u, .loop_start = 0u, .loop_end = 5u},
  {.name = (const char *)&companion_browser_cemp_strings[14870u], .first_frame = 1614u, .frame_count = 5u, .loop_start = 0u, .loop_end = 5u},
  {.name = (const char *)&companion_browser_cemp_strings[14898u], .first_frame = 1619u, .frame_count = 5u, .loop_start = 0u, .loop_end = 5u},
  {.name = (const char *)&companion_browser_cemp_strings[14926u], .first_frame = 1624u, .frame_count = 5u, .loop_start = 0u, .loop_end = 5u},
  {.name = (const char *)&companion_browser_cemp_strings[14955u], .first_frame = 1629u, .frame_count = 5u, .loop_start = 0u, .loop_end = 5u},
  {.name = (const char *)&companion_browser_cemp_strings[14981u], .first_frame = 1634u, .frame_count = 5u, .loop_start = 0u, .loop_end = 5u},
  {.name = (const char *)&companion_browser_cemp_strings[15010u], .first_frame = 1639u, .frame_count = 5u, .loop_start = 0u, .loop_end = 5u},
  {.name = (const char *)&companion_browser_cemp_strings[15037u], .first_frame = 1644u, .frame_count = 5u, .loop_start = 0u, .loop_end = 5u},
  {.name = (const char *)&companion_browser_cemp_strings[15064u], .first_frame = 1649u, .frame_count = 5u, .loop_start = 0u, .loop_end = 5u},
  {.name = (const char *)&companion_browser_cemp_strings[15092u], .first_frame = 1654u, .frame_count = 5u, .loop_start = 0u, .loop_end = 5u},
  {.name = (const char *)&companion_browser_cemp_strings[15117u], .first_frame = 1659u, .frame_count = 5u, .loop_start = 0u, .loop_end = 5u},
  {.name = (const char *)&companion_browser_cemp_strings[15149u], .first_frame = 1664u, .frame_count = 5u, .loop_start = 0u, .loop_end = 5u},
  {.name = (const char *)&companion_browser_cemp_strings[15179u], .first_frame = 1669u, .frame_count = 5u, .loop_start = 0u, .loop_end = 5u},
  {.name = (const char *)&companion_browser_cemp_strings[15209u], .first_frame = 1674u, .frame_count = 5u, .loop_start = 0u, .loop_end = 5u},
  {.name = (const char *)&companion_browser_cemp_strings[15240u], .first_frame = 1679u, .frame_count = 5u, .loop_start = 0u, .loop_end = 5u},
  {.name = (const char *)&companion_browser_cemp_strings[15268u], .first_frame = 1684u, .frame_count = 5u, .loop_start = 0u, .loop_end = 5u},
  {.name = (const char *)&companion_browser_cemp_strings[15303u], .first_frame = 1689u, .frame_count = 5u, .loop_start = 0u, .loop_end = 5u},
  {.name = (const char *)&companion_browser_cemp_strings[15336u], .first_frame = 1694u, .frame_count = 5u, .loop_start = 0u, .loop_end = 5u},
  {.name = (const char *)&companion_browser_cemp_strings[15369u], .first_frame = 1699u, .frame_count = 5u, .loop_start = 0u, .loop_end = 5u},
  {.name = (const char *)&companion_browser_cemp_strings[15403u], .first_frame = 1704u, .frame_count = 5u, .loop_start = 0u, .loop_end = 5u},
  {.name = (const char *)&companion_browser_cemp_strings[15434u], .first_frame = 1709u, .frame_count = 5u, .loop_start = 0u, .loop_end = 5u},
  {.name = (const char *)&companion_browser_cemp_strings[15463u], .first_frame = 1714u, .frame_count = 5u, .loop_start = 0u, .loop_end = 5u},
  {.name = (const char *)&companion_browser_cemp_strings[15490u], .first_frame = 1719u, .frame_count = 5u, .loop_start = 0u, .loop_end = 5u},
  {.name = (const char *)&companion_browser_cemp_strings[15517u], .first_frame = 1724u, .frame_count = 5u, .loop_start = 0u, .loop_end = 5u},
  {.name = (const char *)&companion_browser_cemp_strings[15545u], .first_frame = 1729u, .frame_count = 5u, .loop_start = 0u, .loop_end = 5u},
  {.name = (const char *)&companion_browser_cemp_strings[15570u], .first_frame = 1734u, .frame_count = 5u, .loop_start = 0u, .loop_end = 5u},
  {.name = (const char *)&companion_browser_cemp_strings[15602u], .first_frame = 1739u, .frame_count = 5u, .loop_start = 0u, .loop_end = 5u},
  {.name = (const char *)&companion_browser_cemp_strings[15632u], .first_frame = 1744u, .frame_count = 5u, .loop_start = 0u, .loop_end = 5u},
  {.name = (const char *)&companion_browser_cemp_strings[15662u], .first_frame = 1749u, .frame_count = 5u, .loop_start = 0u, .loop_end = 5u},
  {.name = (const char *)&companion_browser_cemp_strings[15693u], .first_frame = 1754u, .frame_count = 5u, .loop_start = 0u, .loop_end = 5u},
  {.name = (const char *)&companion_browser_cemp_strings[15721u], .first_frame = 1759u, .frame_count = 5u, .loop_start = 0u, .loop_end = 5u},
  {.name = (const char *)&companion_browser_cemp_strings[15755u], .first_frame = 1764u, .frame_count = 5u, .loop_start = 0u, .loop_end = 5u},
  {.name = (const char *)&companion_browser_cemp_strings[15787u], .first_frame = 1769u, .frame_count = 5u, .loop_start = 0u, .loop_end = 5u},
  {.name = (const char *)&companion_browser_cemp_strings[15819u], .first_frame = 1774u, .frame_count = 5u, .loop_start = 0u, .loop_end = 5u},
  {.name = (const char *)&companion_browser_cemp_strings[15852u], .first_frame = 1779u, .frame_count = 5u, .loop_start = 0u, .loop_end = 5u},
  {.name = (const char *)&companion_browser_cemp_strings[15882u], .first_frame = 1784u, .frame_count = 5u, .loop_start = 0u, .loop_end = 5u},
  {.name = (const char *)&companion_browser_cemp_strings[15911u], .first_frame = 1789u, .frame_count = 5u, .loop_start = 0u, .loop_end = 5u},
  {.name = (const char *)&companion_browser_cemp_strings[15938u], .first_frame = 1794u, .frame_count = 5u, .loop_start = 0u, .loop_end = 5u},
  {.name = (const char *)&companion_browser_cemp_strings[15965u], .first_frame = 1799u, .frame_count = 5u, .loop_start = 0u, .loop_end = 5u},
  {.name = (const char *)&companion_browser_cemp_strings[15993u], .first_frame = 1804u, .frame_count = 5u, .loop_start = 0u, .loop_end = 5u},
  {.name = (const char *)&companion_browser_cemp_strings[16018u], .first_frame = 1809u, .frame_count = 5u, .loop_start = 0u, .loop_end = 5u},
  {.name = (const char *)&companion_browser_cemp_strings[16046u], .first_frame = 1814u, .frame_count = 5u, .loop_start = 0u, .loop_end = 5u},
  {.name = (const char *)&companion_browser_cemp_strings[16072u], .first_frame = 1819u, .frame_count = 5u, .loop_start = 0u, .loop_end = 5u},
  {.name = (const char *)&companion_browser_cemp_strings[16098u], .first_frame = 1824u, .frame_count = 5u, .loop_start = 0u, .loop_end = 5u},
  {.name = (const char *)&companion_browser_cemp_strings[16125u], .first_frame = 1829u, .frame_count = 5u, .loop_start = 0u, .loop_end = 5u},
  {.name = (const char *)&companion_browser_cemp_strings[16149u], .first_frame = 1834u, .frame_count = 5u, .loop_start = 0u, .loop_end = 5u},
  {.name = (const char *)&companion_browser_cemp_strings[16177u], .first_frame = 1839u, .frame_count = 5u, .loop_start = 0u, .loop_end = 5u},
  {.name = (const char *)&companion_browser_cemp_strings[16203u], .first_frame = 1844u, .frame_count = 5u, .loop_start = 0u, .loop_end = 5u},
  {.name = (const char *)&companion_browser_cemp_strings[16229u], .first_frame = 1849u, .frame_count = 5u, .loop_start = 0u, .loop_end = 5u},
  {.name = (const char *)&companion_browser_cemp_strings[16256u], .first_frame = 1854u, .frame_count = 5u, .loop_start = 0u, .loop_end = 5u},
  {.name = (const char *)&companion_browser_cemp_strings[16280u], .first_frame = 1859u, .frame_count = 5u, .loop_start = 0u, .loop_end = 5u},
  {.name = (const char *)&companion_browser_cemp_strings[16313u], .first_frame = 1864u, .frame_count = 5u, .loop_start = 0u, .loop_end = 5u},
  {.name = (const char *)&companion_browser_cemp_strings[16344u], .first_frame = 1869u, .frame_count = 5u, .loop_start = 0u, .loop_end = 5u},
  {.name = (const char *)&companion_browser_cemp_strings[16375u], .first_frame = 1874u, .frame_count = 5u, .loop_start = 0u, .loop_end = 5u},
  {.name = (const char *)&companion_browser_cemp_strings[16407u], .first_frame = 1879u, .frame_count = 5u, .loop_start = 0u, .loop_end = 5u},
  {.name = (const char *)&companion_browser_cemp_strings[16436u], .first_frame = 1884u, .frame_count = 5u, .loop_start = 0u, .loop_end = 5u},
  {.name = (const char *)&companion_browser_cemp_strings[16468u], .first_frame = 1889u, .frame_count = 5u, .loop_start = 0u, .loop_end = 5u},
  {.name = (const char *)&companion_browser_cemp_strings[16498u], .first_frame = 1894u, .frame_count = 5u, .loop_start = 0u, .loop_end = 5u},
  {.name = (const char *)&companion_browser_cemp_strings[16528u], .first_frame = 1899u, .frame_count = 5u, .loop_start = 0u, .loop_end = 5u},
  {.name = (const char *)&companion_browser_cemp_strings[16559u], .first_frame = 1904u, .frame_count = 5u, .loop_start = 0u, .loop_end = 5u},
  {.name = (const char *)&companion_browser_cemp_strings[16587u], .first_frame = 1909u, .frame_count = 5u, .loop_start = 0u, .loop_end = 5u},
  {.name = (const char *)&companion_browser_cemp_strings[16622u], .first_frame = 1914u, .frame_count = 5u, .loop_start = 0u, .loop_end = 5u},
  {.name = (const char *)&companion_browser_cemp_strings[16655u], .first_frame = 1919u, .frame_count = 5u, .loop_start = 0u, .loop_end = 5u},
  {.name = (const char *)&companion_browser_cemp_strings[16688u], .first_frame = 1924u, .frame_count = 5u, .loop_start = 0u, .loop_end = 5u},
  {.name = (const char *)&companion_browser_cemp_strings[16722u], .first_frame = 1929u, .frame_count = 5u, .loop_start = 0u, .loop_end = 5u},
  {.name = (const char *)&companion_browser_cemp_strings[16753u], .first_frame = 1934u, .frame_count = 5u, .loop_start = 0u, .loop_end = 5u},
  {.name = (const char *)&companion_browser_cemp_strings[16788u], .first_frame = 1939u, .frame_count = 5u, .loop_start = 0u, .loop_end = 5u},
  {.name = (const char *)&companion_browser_cemp_strings[16821u], .first_frame = 1944u, .frame_count = 5u, .loop_start = 0u, .loop_end = 5u},
  {.name = (const char *)&companion_browser_cemp_strings[16854u], .first_frame = 1949u, .frame_count = 5u, .loop_start = 0u, .loop_end = 5u},
  {.name = (const char *)&companion_browser_cemp_strings[16888u], .first_frame = 1954u, .frame_count = 5u, .loop_start = 0u, .loop_end = 5u},
  {.name = (const char *)&companion_browser_cemp_strings[16919u], .first_frame = 1959u, .frame_count = 5u, .loop_start = 0u, .loop_end = 5u},
  {.name = (const char *)&companion_browser_cemp_strings[16948u], .first_frame = 1964u, .frame_count = 5u, .loop_start = 0u, .loop_end = 5u},
  {.name = (const char *)&companion_browser_cemp_strings[16975u], .first_frame = 1969u, .frame_count = 5u, .loop_start = 0u, .loop_end = 5u},
  {.name = (const char *)&companion_browser_cemp_strings[17002u], .first_frame = 1974u, .frame_count = 5u, .loop_start = 0u, .loop_end = 5u},
  {.name = (const char *)&companion_browser_cemp_strings[17030u], .first_frame = 1979u, .frame_count = 5u, .loop_start = 0u, .loop_end = 5u},
  {.name = (const char *)&companion_browser_cemp_strings[17055u], .first_frame = 1984u, .frame_count = 5u, .loop_start = 0u, .loop_end = 5u},
  {.name = (const char *)&companion_browser_cemp_strings[17081u], .first_frame = 1989u, .frame_count = 5u, .loop_start = 0u, .loop_end = 5u},
  {.name = (const char *)&companion_browser_cemp_strings[17105u], .first_frame = 1994u, .frame_count = 5u, .loop_start = 0u, .loop_end = 5u},
  {.name = (const char *)&companion_browser_cemp_strings[17129u], .first_frame = 1999u, .frame_count = 5u, .loop_start = 0u, .loop_end = 5u},
  {.name = (const char *)&companion_browser_cemp_strings[17154u], .first_frame = 2004u, .frame_count = 5u, .loop_start = 0u, .loop_end = 5u},
  {.name = (const char *)&companion_browser_cemp_strings[17176u], .first_frame = 2009u, .frame_count = 5u, .loop_start = 0u, .loop_end = 5u},
  {.name = (const char *)&companion_browser_cemp_strings[17205u], .first_frame = 2014u, .frame_count = 5u, .loop_start = 0u, .loop_end = 5u},
  {.name = (const char *)&companion_browser_cemp_strings[17232u], .first_frame = 2019u, .frame_count = 5u, .loop_start = 0u, .loop_end = 5u},
  {.name = (const char *)&companion_browser_cemp_strings[17259u], .first_frame = 2024u, .frame_count = 5u, .loop_start = 0u, .loop_end = 5u},
  {.name = (const char *)&companion_browser_cemp_strings[17287u], .first_frame = 2029u, .frame_count = 5u, .loop_start = 0u, .loop_end = 5u},
  {.name = (const char *)&companion_browser_cemp_strings[17312u], .first_frame = 2034u, .frame_count = 5u, .loop_start = 0u, .loop_end = 5u},
  {.name = (const char *)&companion_browser_cemp_strings[17343u], .first_frame = 2039u, .frame_count = 5u, .loop_start = 0u, .loop_end = 5u},
  {.name = (const char *)&companion_browser_cemp_strings[17372u], .first_frame = 2044u, .frame_count = 5u, .loop_start = 0u, .loop_end = 5u},
  {.name = (const char *)&companion_browser_cemp_strings[17401u], .first_frame = 2049u, .frame_count = 5u, .loop_start = 0u, .loop_end = 5u},
  {.name = (const char *)&companion_browser_cemp_strings[17431u], .first_frame = 2054u, .frame_count = 5u, .loop_start = 0u, .loop_end = 5u},
  {.name = (const char *)&companion_browser_cemp_strings[17458u], .first_frame = 2059u, .frame_count = 5u, .loop_start = 0u, .loop_end = 5u},
  {.name = (const char *)&companion_browser_cemp_strings[17487u], .first_frame = 2064u, .frame_count = 5u, .loop_start = 0u, .loop_end = 5u},
  {.name = (const char *)&companion_browser_cemp_strings[17514u], .first_frame = 2069u, .frame_count = 5u, .loop_start = 0u, .loop_end = 5u},
  {.name = (const char *)&companion_browser_cemp_strings[17541u], .first_frame = 2074u, .frame_count = 5u, .loop_start = 0u, .loop_end = 5u},
  {.name = (const char *)&companion_browser_cemp_strings[17569u], .first_frame = 2079u, .frame_count = 5u, .loop_start = 0u, .loop_end = 5u},
  {.name = "browser_state_override", .first_frame = 2084u, .frame_count = 1u, .loop_start = 0u, .loop_end = 1u},
};

static const comp_emote_frame_t companion_browser_cemp_frames[
    COMPANION_BROWSER_CEMP_FRAME_COUNT + 1u] = {
  {.data_offset = 0u, .data_size = 1104u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1104u, .data_size = 1104u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 2208u, .data_size = 1104u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 3312u, .data_size = 1102u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 4414u, .data_size = 1104u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 5518u, .data_size = 1104u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 6622u, .data_size = 1104u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 7726u, .data_size = 1104u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 8830u, .data_size = 1102u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 9932u, .data_size = 1104u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 11036u, .data_size = 1104u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 12140u, .data_size = 1104u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 13244u, .data_size = 1102u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 14346u, .data_size = 1104u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 15450u, .data_size = 1210u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 16660u, .data_size = 1210u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 17870u, .data_size = 1210u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 19080u, .data_size = 1212u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 20292u, .data_size = 1210u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 21502u, .data_size = 1210u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 22712u, .data_size = 1210u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 23922u, .data_size = 1210u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 25132u, .data_size = 1212u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 26344u, .data_size = 1210u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 27554u, .data_size = 1210u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 28764u, .data_size = 1210u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 29974u, .data_size = 1212u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 31186u, .data_size = 1210u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 32396u, .data_size = 1263u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 33659u, .data_size = 1263u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 34922u, .data_size = 1265u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 36187u, .data_size = 1269u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 37456u, .data_size = 1265u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 38721u, .data_size = 1263u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 39984u, .data_size = 1263u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 41247u, .data_size = 1265u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 42512u, .data_size = 1269u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 43781u, .data_size = 1265u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 45046u, .data_size = 1263u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 46309u, .data_size = 1265u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 47574u, .data_size = 1269u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 48843u, .data_size = 1265u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 50108u, .data_size = 1180u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 51288u, .data_size = 1180u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 52468u, .data_size = 1178u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 53646u, .data_size = 1184u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 54830u, .data_size = 1178u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 56008u, .data_size = 1180u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 57188u, .data_size = 1180u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 58368u, .data_size = 1178u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 59546u, .data_size = 1184u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 60730u, .data_size = 1178u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 61908u, .data_size = 1180u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 63088u, .data_size = 1178u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 64266u, .data_size = 1184u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 65450u, .data_size = 1178u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 66628u, .data_size = 1213u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 67841u, .data_size = 1213u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 69054u, .data_size = 1213u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 70267u, .data_size = 1220u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 71487u, .data_size = 1213u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 72700u, .data_size = 1213u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 73913u, .data_size = 1213u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 75126u, .data_size = 1213u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 76339u, .data_size = 1220u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 77559u, .data_size = 1213u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 78772u, .data_size = 1213u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 79985u, .data_size = 1213u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 81198u, .data_size = 1220u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 82418u, .data_size = 1213u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 83631u, .data_size = 671u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 84302u, .data_size = 706u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 85008u, .data_size = 1084u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 86092u, .data_size = 1084u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 87176u, .data_size = 1084u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 88260u, .data_size = 1088u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 89348u, .data_size = 1084u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 90432u, .data_size = 1084u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 91516u, .data_size = 1084u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 92600u, .data_size = 1084u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 93684u, .data_size = 1088u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 94772u, .data_size = 1084u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 95856u, .data_size = 1084u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 96940u, .data_size = 1084u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 98024u, .data_size = 1088u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 99112u, .data_size = 1084u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 100196u, .data_size = 1179u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 101375u, .data_size = 1179u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 102554u, .data_size = 1176u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 103730u, .data_size = 1177u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 104907u, .data_size = 1176u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 106083u, .data_size = 1179u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 107262u, .data_size = 1179u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 108441u, .data_size = 1176u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 109617u, .data_size = 1177u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 110794u, .data_size = 1176u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 111970u, .data_size = 1179u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 113149u, .data_size = 1176u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 114325u, .data_size = 1177u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 115502u, .data_size = 1176u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 116678u, .data_size = 1159u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 117837u, .data_size = 1159u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 118996u, .data_size = 1159u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 120155u, .data_size = 1159u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 121314u, .data_size = 1159u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 122473u, .data_size = 1159u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 123632u, .data_size = 1159u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 124791u, .data_size = 1159u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 125950u, .data_size = 1159u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 127109u, .data_size = 1159u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 128268u, .data_size = 1159u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 129427u, .data_size = 1159u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 130586u, .data_size = 1159u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 131745u, .data_size = 1159u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 132904u, .data_size = 1227u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 134131u, .data_size = 1227u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 135358u, .data_size = 1227u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 136585u, .data_size = 1233u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 137818u, .data_size = 1227u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 139045u, .data_size = 1227u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 140272u, .data_size = 1227u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 141499u, .data_size = 1227u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 142726u, .data_size = 1233u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 143959u, .data_size = 1227u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 145186u, .data_size = 1227u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 146413u, .data_size = 1227u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 147640u, .data_size = 1233u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 148873u, .data_size = 1227u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 150100u, .data_size = 1064u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 151164u, .data_size = 516u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 151680u, .data_size = 1208u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 152888u, .data_size = 1232u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 154120u, .data_size = 1248u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 155368u, .data_size = 1222u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 156590u, .data_size = 1232u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 157822u, .data_size = 1243u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 159065u, .data_size = 1182u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 160247u, .data_size = 1182u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 161429u, .data_size = 1243u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 162672u, .data_size = 1182u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 163854u, .data_size = 1243u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 165097u, .data_size = 1182u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 166279u, .data_size = 1243u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 167522u, .data_size = 1182u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 168704u, .data_size = 1243u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 169947u, .data_size = 1104u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 171051u, .data_size = 1100u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 172151u, .data_size = 1100u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 173251u, .data_size = 1100u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 174351u, .data_size = 1100u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 175451u, .data_size = 1104u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 176555u, .data_size = 1102u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 177657u, .data_size = 1097u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 178754u, .data_size = 1095u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 179849u, .data_size = 1099u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 180948u, .data_size = 1099u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 182047u, .data_size = 1104u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 183151u, .data_size = 1108u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 184259u, .data_size = 1106u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 185365u, .data_size = 1108u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 186473u, .data_size = 1108u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 187581u, .data_size = 1104u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 188685u, .data_size = 1100u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 189785u, .data_size = 1100u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 190885u, .data_size = 1104u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 191989u, .data_size = 1106u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 193095u, .data_size = 1106u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 194201u, .data_size = 1100u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 195301u, .data_size = 1104u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 196405u, .data_size = 1102u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 197507u, .data_size = 1104u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 198611u, .data_size = 1099u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 199710u, .data_size = 1095u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 200805u, .data_size = 1093u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 201898u, .data_size = 1099u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 202997u, .data_size = 1099u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 204096u, .data_size = 1102u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 205198u, .data_size = 1106u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 206304u, .data_size = 1106u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 207410u, .data_size = 1108u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 208518u, .data_size = 1108u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 209626u, .data_size = 1104u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 210730u, .data_size = 1099u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 211829u, .data_size = 1095u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 212924u, .data_size = 1099u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 214023u, .data_size = 1099u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 215122u, .data_size = 1100u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 216222u, .data_size = 1100u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 217322u, .data_size = 1100u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 218422u, .data_size = 1106u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 219528u, .data_size = 1104u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 220632u, .data_size = 1102u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 221734u, .data_size = 1104u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 222838u, .data_size = 1099u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 223937u, .data_size = 1104u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 225041u, .data_size = 1098u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 226139u, .data_size = 1098u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 227237u, .data_size = 1104u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 228341u, .data_size = 1104u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 229445u, .data_size = 1098u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 230543u, .data_size = 1104u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 231647u, .data_size = 1104u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 232751u, .data_size = 1099u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 233850u, .data_size = 1099u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 234949u, .data_size = 1099u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 236048u, .data_size = 1102u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 237150u, .data_size = 1097u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 238247u, .data_size = 1095u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 239342u, .data_size = 1099u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 240441u, .data_size = 1104u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 241545u, .data_size = 1108u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 242653u, .data_size = 1106u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 243759u, .data_size = 1106u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 244865u, .data_size = 1106u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 245971u, .data_size = 1104u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 247075u, .data_size = 1099u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 248174u, .data_size = 1095u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 249269u, .data_size = 1097u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 250366u, .data_size = 1104u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 251470u, .data_size = 1106u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 252576u, .data_size = 1106u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 253682u, .data_size = 1100u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 254782u, .data_size = 1104u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 255886u, .data_size = 1104u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 256990u, .data_size = 1100u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 258090u, .data_size = 1100u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 259190u, .data_size = 1098u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 260288u, .data_size = 1098u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 261386u, .data_size = 1104u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 262490u, .data_size = 1102u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 263592u, .data_size = 1097u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 264689u, .data_size = 1097u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 265786u, .data_size = 1095u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 266881u, .data_size = 1099u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 267980u, .data_size = 1097u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 269077u, .data_size = 1104u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 270181u, .data_size = 1099u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 271280u, .data_size = 1099u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 272379u, .data_size = 1106u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 273485u, .data_size = 1106u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 274591u, .data_size = 1106u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 275697u, .data_size = 1104u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 276801u, .data_size = 1100u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 277901u, .data_size = 1098u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 278999u, .data_size = 1100u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 280099u, .data_size = 1104u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 281203u, .data_size = 1099u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 282302u, .data_size = 1095u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 283397u, .data_size = 1108u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 284505u, .data_size = 1106u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 285611u, .data_size = 1104u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 286715u, .data_size = 1100u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 287815u, .data_size = 1100u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 288915u, .data_size = 1100u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 290015u, .data_size = 1104u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 291119u, .data_size = 1099u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 292218u, .data_size = 1097u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 293315u, .data_size = 1095u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 294410u, .data_size = 1099u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 295509u, .data_size = 1104u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 296613u, .data_size = 1099u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 297712u, .data_size = 1095u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 298807u, .data_size = 1099u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 299906u, .data_size = 1106u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 301012u, .data_size = 1106u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 302118u, .data_size = 1098u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 303216u, .data_size = 1104u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 304320u, .data_size = 1100u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 305420u, .data_size = 1098u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 306518u, .data_size = 1102u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 307620u, .data_size = 1106u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 308726u, .data_size = 1104u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 309830u, .data_size = 1097u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 310927u, .data_size = 1095u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 312022u, .data_size = 1099u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 313121u, .data_size = 1210u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 314331u, .data_size = 1210u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 315541u, .data_size = 1207u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 316748u, .data_size = 1198u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 317946u, .data_size = 1215u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 319161u, .data_size = 1209u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 320370u, .data_size = 1206u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 321576u, .data_size = 1198u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 322774u, .data_size = 1206u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 323980u, .data_size = 1220u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 325200u, .data_size = 1210u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 326410u, .data_size = 1210u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 327620u, .data_size = 1207u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 328827u, .data_size = 1212u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 330039u, .data_size = 1210u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 331249u, .data_size = 1210u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 332459u, .data_size = 1206u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 333665u, .data_size = 1207u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 334872u, .data_size = 1211u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 336083u, .data_size = 1210u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 337293u, .data_size = 1203u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 338496u, .data_size = 1198u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 339694u, .data_size = 1207u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 340901u, .data_size = 1218u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 342119u, .data_size = 1210u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 343329u, .data_size = 1214u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 344543u, .data_size = 1198u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 345741u, .data_size = 1207u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 346948u, .data_size = 1210u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 348158u, .data_size = 1207u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 349365u, .data_size = 1217u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 350582u, .data_size = 1211u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 351793u, .data_size = 1207u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 353000u, .data_size = 1212u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 354212u, .data_size = 1210u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 355422u, .data_size = 1210u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 356632u, .data_size = 1211u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 357843u, .data_size = 1197u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 359040u, .data_size = 1208u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 360248u, .data_size = 1209u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 361457u, .data_size = 1206u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 362663u, .data_size = 1198u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 363861u, .data_size = 1208u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 365069u, .data_size = 1198u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 366267u, .data_size = 1215u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 367482u, .data_size = 1210u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 368692u, .data_size = 1207u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 369899u, .data_size = 1204u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 371103u, .data_size = 1210u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 372313u, .data_size = 1210u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 373523u, .data_size = 1207u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 374730u, .data_size = 1207u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 375937u, .data_size = 1210u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 377147u, .data_size = 1208u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 378355u, .data_size = 1211u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 379566u, .data_size = 1210u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 380776u, .data_size = 1206u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 381982u, .data_size = 1206u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 383188u, .data_size = 1218u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 384406u, .data_size = 1218u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 385624u, .data_size = 1207u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 386831u, .data_size = 1205u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 388036u, .data_size = 1210u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 389246u, .data_size = 1203u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 390449u, .data_size = 1197u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 391646u, .data_size = 1217u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 392863u, .data_size = 1211u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 394074u, .data_size = 1210u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 395284u, .data_size = 1206u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 396490u, .data_size = 1206u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 397696u, .data_size = 1206u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 398902u, .data_size = 1210u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 400112u, .data_size = 1210u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 401322u, .data_size = 1207u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 402529u, .data_size = 1208u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 403737u, .data_size = 1207u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 404944u, .data_size = 1210u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 406154u, .data_size = 1215u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 407369u, .data_size = 1218u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 408587u, .data_size = 1217u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 409804u, .data_size = 1199u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 411003u, .data_size = 1211u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 412214u, .data_size = 1211u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 413425u, .data_size = 1206u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 414631u, .data_size = 1210u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 415841u, .data_size = 1210u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 417051u, .data_size = 1203u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 418254u, .data_size = 1210u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 419464u, .data_size = 1210u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 420674u, .data_size = 1217u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 421891u, .data_size = 1204u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 423095u, .data_size = 1210u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 424305u, .data_size = 1207u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 425512u, .data_size = 1207u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 426719u, .data_size = 1220u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 427939u, .data_size = 1219u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 429158u, .data_size = 1211u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 430369u, .data_size = 1208u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 431577u, .data_size = 1210u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 432787u, .data_size = 1210u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 433997u, .data_size = 1208u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 435205u, .data_size = 1209u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 436414u, .data_size = 1216u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 437630u, .data_size = 1198u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 438828u, .data_size = 1204u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 440032u, .data_size = 1263u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 441295u, .data_size = 1267u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 442562u, .data_size = 1265u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 443827u, .data_size = 1233u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 445060u, .data_size = 1265u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 446325u, .data_size = 1263u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 447588u, .data_size = 1264u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 448852u, .data_size = 1262u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 450114u, .data_size = 1233u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 451347u, .data_size = 1262u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 452609u, .data_size = 1261u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 453870u, .data_size = 1237u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 455107u, .data_size = 1265u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 456372u, .data_size = 1241u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 457613u, .data_size = 1245u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 458858u, .data_size = 1265u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 460123u, .data_size = 1255u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 461378u, .data_size = 1265u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 462643u, .data_size = 1241u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 463884u, .data_size = 1242u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 465126u, .data_size = 1262u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 466388u, .data_size = 1255u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 467643u, .data_size = 1262u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 468905u, .data_size = 1263u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 470168u, .data_size = 1259u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 471427u, .data_size = 1255u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 472682u, .data_size = 1259u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 473941u, .data_size = 1241u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 475182u, .data_size = 1239u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 476421u, .data_size = 1259u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 477680u, .data_size = 1265u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 478945u, .data_size = 1263u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 480208u, .data_size = 1265u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 481473u, .data_size = 1243u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 482716u, .data_size = 1263u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 483979u, .data_size = 1259u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 485238u, .data_size = 1255u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 486493u, .data_size = 1237u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 487730u, .data_size = 1241u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 488971u, .data_size = 1242u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 490213u, .data_size = 1255u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 491468u, .data_size = 1263u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 492731u, .data_size = 1267u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 493998u, .data_size = 1233u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 495231u, .data_size = 1265u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 496496u, .data_size = 1263u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 497759u, .data_size = 1240u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 498999u, .data_size = 1241u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 500240u, .data_size = 1237u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 501477u, .data_size = 1259u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 502736u, .data_size = 1241u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 503977u, .data_size = 1239u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 505216u, .data_size = 1259u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 506475u, .data_size = 1265u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 507740u, .data_size = 1263u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 509003u, .data_size = 1233u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 510236u, .data_size = 1263u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 511499u, .data_size = 1240u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 512739u, .data_size = 1255u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 513994u, .data_size = 1263u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 515257u, .data_size = 1261u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 516518u, .data_size = 1259u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 517777u, .data_size = 1263u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 519040u, .data_size = 1264u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 520304u, .data_size = 1240u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 521544u, .data_size = 1259u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 522803u, .data_size = 1264u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 524067u, .data_size = 1262u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 525329u, .data_size = 1240u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 526569u, .data_size = 1263u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 527832u, .data_size = 1259u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 529091u, .data_size = 1233u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 530324u, .data_size = 1262u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 531586u, .data_size = 1263u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 532849u, .data_size = 1241u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 534090u, .data_size = 1255u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 535345u, .data_size = 1241u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 536586u, .data_size = 1255u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 537841u, .data_size = 1263u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 539104u, .data_size = 1180u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 540284u, .data_size = 1218u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 541502u, .data_size = 1212u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 542714u, .data_size = 1222u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 543936u, .data_size = 1180u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 545116u, .data_size = 1177u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 546293u, .data_size = 1213u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 547506u, .data_size = 1186u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 548692u, .data_size = 1213u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 549905u, .data_size = 1180u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 551085u, .data_size = 1180u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 552265u, .data_size = 1194u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 553459u, .data_size = 1210u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 554669u, .data_size = 1216u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 555885u, .data_size = 1180u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 557065u, .data_size = 1188u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 558253u, .data_size = 1180u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 559433u, .data_size = 1184u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 560617u, .data_size = 1220u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 561837u, .data_size = 1186u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 563023u, .data_size = 1220u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 564243u, .data_size = 1154u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 565397u, .data_size = 1151u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 566548u, .data_size = 1213u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 567761u, .data_size = 1210u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 568971u, .data_size = 1154u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 570125u, .data_size = 1180u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 571305u, .data_size = 1218u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 572523u, .data_size = 1210u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 573733u, .data_size = 1192u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 574925u, .data_size = 1184u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 576109u, .data_size = 1196u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 577305u, .data_size = 1210u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 578515u, .data_size = 1180u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 579695u, .data_size = 1218u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 580913u, .data_size = 1180u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 582093u, .data_size = 1213u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 583306u, .data_size = 1210u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 584516u, .data_size = 1213u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 585729u, .data_size = 1180u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 586909u, .data_size = 1210u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 588119u, .data_size = 1220u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 589339u, .data_size = 1180u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 590519u, .data_size = 1177u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 591696u, .data_size = 1189u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 592885u, .data_size = 1210u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 594095u, .data_size = 1212u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 595307u, .data_size = 1222u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 596529u, .data_size = 1220u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 597749u, .data_size = 1196u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 598945u, .data_size = 1180u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 600125u, .data_size = 1180u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 601305u, .data_size = 1194u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 602499u, .data_size = 1216u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 603715u, .data_size = 1180u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 604895u, .data_size = 1222u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 606117u, .data_size = 1180u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 607297u, .data_size = 1189u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 608486u, .data_size = 1184u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 609670u, .data_size = 1196u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 610866u, .data_size = 1196u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 612062u, .data_size = 1154u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 613216u, .data_size = 1154u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 614370u, .data_size = 1180u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 615550u, .data_size = 1180u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 616730u, .data_size = 1186u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 617916u, .data_size = 1220u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 619136u, .data_size = 1154u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 620290u, .data_size = 1218u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 621508u, .data_size = 1210u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 622718u, .data_size = 1216u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 623934u, .data_size = 1154u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 625088u, .data_size = 1192u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 626280u, .data_size = 1220u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 627500u, .data_size = 1210u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 628710u, .data_size = 1180u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 629890u, .data_size = 1218u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 631108u, .data_size = 1154u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 632262u, .data_size = 1158u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 633420u, .data_size = 1154u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 634574u, .data_size = 1151u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 635725u, .data_size = 1179u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 636904u, .data_size = 1177u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 638081u, .data_size = 1172u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 639253u, .data_size = 1170u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 640423u, .data_size = 1172u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 641595u, .data_size = 1164u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 642759u, .data_size = 1176u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 643935u, .data_size = 1176u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 645111u, .data_size = 1173u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 646284u, .data_size = 1170u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 647454u, .data_size = 1171u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 648625u, .data_size = 1176u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 649801u, .data_size = 1175u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 650976u, .data_size = 1171u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 652147u, .data_size = 1153u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 653300u, .data_size = 1171u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 654471u, .data_size = 1176u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 655647u, .data_size = 1179u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 656826u, .data_size = 1179u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 658005u, .data_size = 1160u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 659165u, .data_size = 1172u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 660337u, .data_size = 1161u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 661498u, .data_size = 1162u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 662660u, .data_size = 1170u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 663830u, .data_size = 1172u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 665002u, .data_size = 1179u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 666181u, .data_size = 1170u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 667351u, .data_size = 1176u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 668527u, .data_size = 1175u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 669702u, .data_size = 1167u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 670869u, .data_size = 1156u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 672025u, .data_size = 1177u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 673202u, .data_size = 1172u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 674374u, .data_size = 1156u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 675530u, .data_size = 1176u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 676706u, .data_size = 1174u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 677880u, .data_size = 1179u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 679059u, .data_size = 1174u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 680233u, .data_size = 1177u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 681410u, .data_size = 1172u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 682582u, .data_size = 1158u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 683740u, .data_size = 1164u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 684904u, .data_size = 1160u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 686064u, .data_size = 1171u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 687235u, .data_size = 1179u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 688414u, .data_size = 1173u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 689587u, .data_size = 1167u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 690754u, .data_size = 1174u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 691928u, .data_size = 1172u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 693100u, .data_size = 1176u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 694276u, .data_size = 1167u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 695443u, .data_size = 1171u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 696614u, .data_size = 1161u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 697775u, .data_size = 1156u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 698931u, .data_size = 1164u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 700095u, .data_size = 1162u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 701257u, .data_size = 1176u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 702433u, .data_size = 1171u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 703604u, .data_size = 1170u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 704774u, .data_size = 1179u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 705953u, .data_size = 1179u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 707132u, .data_size = 1160u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 708292u, .data_size = 1172u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 709464u, .data_size = 1167u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 710631u, .data_size = 1161u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 711792u, .data_size = 1179u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 712971u, .data_size = 1179u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 714150u, .data_size = 1157u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 715307u, .data_size = 1164u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 716471u, .data_size = 1171u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 717642u, .data_size = 1179u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 718821u, .data_size = 1175u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 719996u, .data_size = 1156u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 721152u, .data_size = 1164u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 722316u, .data_size = 1164u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 723480u, .data_size = 1173u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 724653u, .data_size = 1170u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 725823u, .data_size = 1174u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 726997u, .data_size = 1176u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 728173u, .data_size = 1164u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 729337u, .data_size = 1164u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 730501u, .data_size = 1171u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 731672u, .data_size = 1227u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 732899u, .data_size = 1233u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 734132u, .data_size = 1235u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 735367u, .data_size = 1227u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 736594u, .data_size = 1227u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 737821u, .data_size = 1227u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 739048u, .data_size = 1229u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 740277u, .data_size = 1227u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 741504u, .data_size = 1229u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 742733u, .data_size = 1227u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 743960u, .data_size = 1230u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 745190u, .data_size = 1232u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 746422u, .data_size = 1227u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 747649u, .data_size = 1232u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 748881u, .data_size = 1227u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 750108u, .data_size = 1223u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 751331u, .data_size = 1223u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 752554u, .data_size = 1229u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 753783u, .data_size = 1223u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 755006u, .data_size = 1230u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 756236u, .data_size = 1228u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 757464u, .data_size = 1230u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 758694u, .data_size = 1227u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 759921u, .data_size = 1227u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 761148u, .data_size = 1233u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 762381u, .data_size = 1233u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 763614u, .data_size = 1229u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 764843u, .data_size = 1227u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 766070u, .data_size = 1227u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 767297u, .data_size = 1229u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 768526u, .data_size = 1227u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 769753u, .data_size = 1223u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 770976u, .data_size = 1223u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 772199u, .data_size = 1227u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 773426u, .data_size = 1224u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 774650u, .data_size = 1227u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 775877u, .data_size = 1230u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 777107u, .data_size = 1227u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 778334u, .data_size = 1227u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 779561u, .data_size = 1227u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 780788u, .data_size = 1229u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 782017u, .data_size = 1229u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 783246u, .data_size = 1233u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 784479u, .data_size = 1229u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 785708u, .data_size = 1225u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 786933u, .data_size = 1227u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 788160u, .data_size = 1229u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 789389u, .data_size = 1232u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 790621u, .data_size = 1227u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 791848u, .data_size = 1227u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 793075u, .data_size = 1227u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 794302u, .data_size = 1227u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 795529u, .data_size = 1229u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 796758u, .data_size = 1225u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 797983u, .data_size = 1223u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 799206u, .data_size = 1227u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 800433u, .data_size = 1227u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 801660u, .data_size = 1230u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 802890u, .data_size = 1230u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 804120u, .data_size = 1230u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 805350u, .data_size = 1227u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 806577u, .data_size = 1234u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 807811u, .data_size = 1227u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 809038u, .data_size = 1228u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 810266u, .data_size = 1224u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 811490u, .data_size = 1230u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 812720u, .data_size = 1232u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 813952u, .data_size = 1227u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 815179u, .data_size = 1230u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 816409u, .data_size = 1227u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 817636u, .data_size = 1229u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 818865u, .data_size = 1229u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 820094u, .data_size = 1227u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 821321u, .data_size = 1235u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 822556u, .data_size = 1233u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 823789u, .data_size = 1227u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 825016u, .data_size = 1232u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 826248u, .data_size = 1229u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 827477u, .data_size = 1225u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 828702u, .data_size = 1229u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 829931u, .data_size = 1223u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 831154u, .data_size = 1227u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 832381u, .data_size = 1228u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 833609u, .data_size = 1227u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 834836u, .data_size = 1229u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 836065u, .data_size = 1232u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 837297u, .data_size = 1229u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 838526u, .data_size = 1223u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 839749u, .data_size = 1228u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 840977u, .data_size = 1228u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 842205u, .data_size = 1233u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 843438u, .data_size = 1231u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 844669u, .data_size = 1229u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 845898u, .data_size = 1225u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 847123u, .data_size = 1223u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 848346u, .data_size = 1229u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 849575u, .data_size = 1351u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 850926u, .data_size = 1361u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 852287u, .data_size = 1361u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 853648u, .data_size = 1431u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 855079u, .data_size = 1443u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 856522u, .data_size = 1388u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 857910u, .data_size = 1429u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 859339u, .data_size = 1396u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 860735u, .data_size = 1443u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 862178u, .data_size = 1460u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 863638u, .data_size = 1388u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 865026u, .data_size = 1468u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 866494u, .data_size = 1406u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 867900u, .data_size = 1398u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 869298u, .data_size = 1460u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 870758u, .data_size = 1437u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 872195u, .data_size = 1531u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 873726u, .data_size = 1481u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 875207u, .data_size = 1445u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 876652u, .data_size = 1486u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 878138u, .data_size = 1461u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 879599u, .data_size = 1535u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 881134u, .data_size = 1531u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 882665u, .data_size = 1475u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 884140u, .data_size = 1471u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 885611u, .data_size = 1948u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 887559u, .data_size = 1956u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 889515u, .data_size = 2005u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 891520u, .data_size = 2021u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 893541u, .data_size = 1930u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 895471u, .data_size = 1970u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 897441u, .data_size = 1940u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 899381u, .data_size = 1955u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 901336u, .data_size = 2010u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 903346u, .data_size = 1912u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 905258u, .data_size = 1987u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 907245u, .data_size = 1940u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 909185u, .data_size = 1924u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 911109u, .data_size = 1885u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 912994u, .data_size = 1956u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 914950u, .data_size = 1949u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 916899u, .data_size = 1615u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 918514u, .data_size = 1686u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 920200u, .data_size = 1764u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 921964u, .data_size = 1829u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 923793u, .data_size = 1898u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 925691u, .data_size = 1843u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 927534u, .data_size = 1799u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 929333u, .data_size = 1899u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 931232u, .data_size = 1881u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 933113u, .data_size = 1825u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 934938u, .data_size = 1868u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 936806u, .data_size = 2019u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 938825u, .data_size = 1897u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 940722u, .data_size = 1875u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 942597u, .data_size = 1822u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 944419u, .data_size = 1899u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 946318u, .data_size = 1800u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 948118u, .data_size = 1655u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 949773u, .data_size = 1729u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 951502u, .data_size = 1731u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 953233u, .data_size = 1741u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 954974u, .data_size = 1739u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 956713u, .data_size = 1074u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 957787u, .data_size = 1148u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 958935u, .data_size = 1145u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 960080u, .data_size = 949u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 961029u, .data_size = 1025u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 962054u, .data_size = 1026u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 963080u, .data_size = 1841u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 964921u, .data_size = 1888u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 966809u, .data_size = 1876u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 968685u, .data_size = 1884u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 970569u, .data_size = 1922u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 972491u, .data_size = 1949u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 974440u, .data_size = 1969u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 976409u, .data_size = 2018u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 978427u, .data_size = 1983u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 980410u, .data_size = 1977u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 982387u, .data_size = 2015u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 984402u, .data_size = 1898u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 986300u, .data_size = 1982u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 988282u, .data_size = 1938u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 990220u, .data_size = 1910u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 992130u, .data_size = 1955u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 994085u, .data_size = 2014u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 996099u, .data_size = 1983u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 998082u, .data_size = 1993u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1000075u, .data_size = 1973u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1002048u, .data_size = 2050u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1004098u, .data_size = 1938u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1006036u, .data_size = 1928u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1007964u, .data_size = 1943u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1009907u, .data_size = 2071u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1011978u, .data_size = 1960u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1013938u, .data_size = 1975u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1015913u, .data_size = 2041u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1017954u, .data_size = 1205u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1019159u, .data_size = 1350u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1020509u, .data_size = 1322u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1021831u, .data_size = 1191u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1023022u, .data_size = 1341u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1024363u, .data_size = 1308u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1025671u, .data_size = 1369u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1027040u, .data_size = 1379u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1028419u, .data_size = 1379u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1029798u, .data_size = 1449u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1031247u, .data_size = 1461u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1032708u, .data_size = 1436u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1034144u, .data_size = 1477u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1035621u, .data_size = 1444u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1037065u, .data_size = 1491u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1038556u, .data_size = 1508u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1040064u, .data_size = 1385u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1041449u, .data_size = 1463u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1042912u, .data_size = 1403u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1044315u, .data_size = 1395u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1045710u, .data_size = 1457u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1047167u, .data_size = 1362u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1048529u, .data_size = 1454u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1049983u, .data_size = 1406u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1051389u, .data_size = 1370u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1052759u, .data_size = 1411u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1054170u, .data_size = 1358u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1055528u, .data_size = 1432u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1056960u, .data_size = 1428u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1058388u, .data_size = 1372u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1059760u, .data_size = 1368u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1061128u, .data_size = 1789u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1062917u, .data_size = 1797u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1064714u, .data_size = 1847u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1066561u, .data_size = 1863u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1068424u, .data_size = 1801u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1070225u, .data_size = 1843u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1072068u, .data_size = 1811u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1073879u, .data_size = 1826u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1075705u, .data_size = 1881u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1077586u, .data_size = 1765u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1079351u, .data_size = 1841u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1081192u, .data_size = 1793u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1082985u, .data_size = 1777u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1084762u, .data_size = 1775u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1086537u, .data_size = 1847u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1088384u, .data_size = 1839u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1090223u, .data_size = 1501u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1091724u, .data_size = 1573u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1093297u, .data_size = 1623u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1094920u, .data_size = 1694u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1096614u, .data_size = 1746u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1098360u, .data_size = 1702u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1100062u, .data_size = 1630u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1101692u, .data_size = 1736u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1103428u, .data_size = 1701u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1105129u, .data_size = 1656u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1106785u, .data_size = 1657u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1108442u, .data_size = 1797u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1110239u, .data_size = 1686u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1111925u, .data_size = 1752u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1113677u, .data_size = 1654u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1115331u, .data_size = 1731u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1117062u, .data_size = 1720u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1118782u, .data_size = 1548u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1120330u, .data_size = 1623u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1121953u, .data_size = 1624u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1123577u, .data_size = 1636u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1125213u, .data_size = 1632u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1126845u, .data_size = 1051u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1127896u, .data_size = 1130u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1129026u, .data_size = 1126u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1130152u, .data_size = 952u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1131104u, .data_size = 1031u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1132135u, .data_size = 1033u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1133168u, .data_size = 1783u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1134951u, .data_size = 1777u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1136728u, .data_size = 1786u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1138514u, .data_size = 1794u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1140308u, .data_size = 1833u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1142141u, .data_size = 1859u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1144000u, .data_size = 1881u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1145881u, .data_size = 1932u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1147813u, .data_size = 1896u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1149709u, .data_size = 1889u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1151598u, .data_size = 1927u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1153525u, .data_size = 1816u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1155341u, .data_size = 1902u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1157243u, .data_size = 1856u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1159099u, .data_size = 1828u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1160927u, .data_size = 1729u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1162656u, .data_size = 1788u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1164444u, .data_size = 1712u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1166156u, .data_size = 1722u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1167878u, .data_size = 1747u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1169625u, .data_size = 1824u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1171449u, .data_size = 1709u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1173158u, .data_size = 1721u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1174879u, .data_size = 1736u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1176615u, .data_size = 1856u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1178471u, .data_size = 1784u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1180255u, .data_size = 1799u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1182054u, .data_size = 1857u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1183911u, .data_size = 1120u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1185031u, .data_size = 1257u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1186288u, .data_size = 1237u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1187525u, .data_size = 1042u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1188567u, .data_size = 1184u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1189751u, .data_size = 1159u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1190910u, .data_size = 1099u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1192009u, .data_size = 1099u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1193108u, .data_size = 1108u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1194216u, .data_size = 1100u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1195316u, .data_size = 1210u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1196526u, .data_size = 1263u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1197789u, .data_size = 1263u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1199052u, .data_size = 1213u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1200265u, .data_size = 1213u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1201478u, .data_size = 1214u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1202692u, .data_size = 1213u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1203905u, .data_size = 669u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1204574u, .data_size = 670u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1205244u, .data_size = 1084u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1206328u, .data_size = 1084u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1207412u, .data_size = 1083u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1208495u, .data_size = 1086u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1209581u, .data_size = 1179u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1210760u, .data_size = 1159u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1211919u, .data_size = 1159u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1213078u, .data_size = 1161u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1214239u, .data_size = 1163u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1215402u, .data_size = 1227u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1216629u, .data_size = 1052u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1217681u, .data_size = 1146u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1218827u, .data_size = 1190u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1220017u, .data_size = 1211u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1221228u, .data_size = 1205u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1222433u, .data_size = 1098u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1223531u, .data_size = 1186u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1224717u, .data_size = 1166u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1225883u, .data_size = 1181u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1227064u, .data_size = 1176u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1228240u, .data_size = 1052u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1229292u, .data_size = 1052u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1230344u, .data_size = 1098u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1231442u, .data_size = 1052u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1232494u, .data_size = 1098u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1233592u, .data_size = 1052u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1234644u, .data_size = 1098u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1235742u, .data_size = 1156u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1236898u, .data_size = 1213u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1238111u, .data_size = 1239u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1239350u, .data_size = 1235u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1240585u, .data_size = 1125u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1241710u, .data_size = 691u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1242401u, .data_size = 706u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1243107u, .data_size = 1118u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1244225u, .data_size = 1115u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1245340u, .data_size = 1104u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1246444u, .data_size = 1098u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1247542u, .data_size = 1178u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1248720u, .data_size = 1180u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1249900u, .data_size = 1205u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1251105u, .data_size = 1220u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1252325u, .data_size = 1213u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1253538u, .data_size = 1186u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1254724u, .data_size = 1181u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1255905u, .data_size = 1144u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1257049u, .data_size = 1134u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1258183u, .data_size = 1159u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1259342u, .data_size = 1159u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1260501u, .data_size = 1179u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1261680u, .data_size = 1214u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1262894u, .data_size = 1233u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1264127u, .data_size = 1138u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1265265u, .data_size = 1208u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1266473u, .data_size = 1138u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1267611u, .data_size = 1138u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1268749u, .data_size = 1138u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1269887u, .data_size = 1138u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1271025u, .data_size = 1210u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1272235u, .data_size = 1148u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1273383u, .data_size = 1130u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1274513u, .data_size = 1136u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1275649u, .data_size = 1130u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1276779u, .data_size = 1130u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1277909u, .data_size = 1130u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1279039u, .data_size = 1130u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1280169u, .data_size = 1186u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1281355u, .data_size = 1209u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1282564u, .data_size = 1245u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1283809u, .data_size = 1267u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1285076u, .data_size = 1198u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1286274u, .data_size = 1143u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1287417u, .data_size = 1131u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1288548u, .data_size = 1142u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1289690u, .data_size = 1136u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1290826u, .data_size = 1105u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1291931u, .data_size = 1183u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1293114u, .data_size = 1105u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1294219u, .data_size = 1105u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1295324u, .data_size = 1105u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1296429u, .data_size = 1105u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1297534u, .data_size = 1106u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1298640u, .data_size = 1171u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1299811u, .data_size = 1106u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1300917u, .data_size = 1106u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1302023u, .data_size = 1106u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1303129u, .data_size = 1106u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1304235u, .data_size = 1160u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1305395u, .data_size = 1111u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1306506u, .data_size = 552u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1307058u, .data_size = 599u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1307657u, .data_size = 1099u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1308756u, .data_size = 659u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1309415u, .data_size = 1197u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1310612u, .data_size = 1052u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1311664u, .data_size = 1167u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1312831u, .data_size = 1210u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1314041u, .data_size = 1052u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1315093u, .data_size = 1052u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1316145u, .data_size = 1052u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1317197u, .data_size = 1052u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1318249u, .data_size = 1157u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1319406u, .data_size = 1185u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1320591u, .data_size = 1107u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1321698u, .data_size = 1109u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1322807u, .data_size = 1046u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1323853u, .data_size = 1120u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1324973u, .data_size = 1046u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1326019u, .data_size = 1046u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1327065u, .data_size = 1046u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1328111u, .data_size = 1046u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1329157u, .data_size = 1096u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1330253u, .data_size = 1131u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1331384u, .data_size = 1043u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1332427u, .data_size = 1067u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1333494u, .data_size = 1043u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1334537u, .data_size = 1043u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1335580u, .data_size = 1043u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1336623u, .data_size = 1043u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1337666u, .data_size = 1047u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1338713u, .data_size = 1143u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1339856u, .data_size = 1047u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1340903u, .data_size = 1047u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1341950u, .data_size = 1047u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1342997u, .data_size = 1047u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1344044u, .data_size = 1161u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1345205u, .data_size = 1154u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1346359u, .data_size = 1093u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1347452u, .data_size = 1140u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1348592u, .data_size = 1161u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1349753u, .data_size = 1140u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1350893u, .data_size = 1140u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1352033u, .data_size = 1140u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1353173u, .data_size = 1140u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1354313u, .data_size = 1185u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1355498u, .data_size = 1135u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1104u, .data_size = 1104u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 4414u, .data_size = 1104u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 5518u, .data_size = 1104u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 33659u, .data_size = 1263u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 37456u, .data_size = 1265u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 38721u, .data_size = 1263u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 67841u, .data_size = 1213u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 86092u, .data_size = 1084u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 16660u, .data_size = 1210u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 117837u, .data_size = 1159u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 15450u, .data_size = 1210u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 100196u, .data_size = 1179u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 50108u, .data_size = 1180u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 32396u, .data_size = 1263u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 83631u, .data_size = 671u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 155368u, .data_size = 1222u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 155368u, .data_size = 1222u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 155368u, .data_size = 1222u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 156590u, .data_size = 1232u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 156590u, .data_size = 1232u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 156590u, .data_size = 1232u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 151680u, .data_size = 1208u, .duration_ms = 1440u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 152888u, .data_size = 1232u, .duration_ms = 1440u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 154120u, .data_size = 1248u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 32396u, .data_size = 1263u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 132904u, .data_size = 1227u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 136585u, .data_size = 1233u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 157822u, .data_size = 1243u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 162672u, .data_size = 1182u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 167522u, .data_size = 1182u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 83631u, .data_size = 671u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1104u, .data_size = 1104u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 20292u, .data_size = 1210u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 89348u, .data_size = 1084u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 20292u, .data_size = 1210u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 121314u, .data_size = 1159u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 54830u, .data_size = 1178u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 37456u, .data_size = 1265u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 89348u, .data_size = 1084u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 83631u, .data_size = 671u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 71487u, .data_size = 1213u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1216629u, .data_size = 1052u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1217681u, .data_size = 1146u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1218827u, .data_size = 1190u, .duration_ms = 1920u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1220017u, .data_size = 1211u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1221228u, .data_size = 1205u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1222433u, .data_size = 1098u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1223531u, .data_size = 1186u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1224717u, .data_size = 1166u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1225883u, .data_size = 1181u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1227064u, .data_size = 1176u, .duration_ms = 1920u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1229292u, .data_size = 1052u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1217681u, .data_size = 1146u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1218827u, .data_size = 1190u, .duration_ms = 1920u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1220017u, .data_size = 1211u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1221228u, .data_size = 1205u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1230344u, .data_size = 1098u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1223531u, .data_size = 1186u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1224717u, .data_size = 1166u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1225883u, .data_size = 1181u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1227064u, .data_size = 1176u, .duration_ms = 1920u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1231442u, .data_size = 1052u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1217681u, .data_size = 1146u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1218827u, .data_size = 1190u, .duration_ms = 1920u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1220017u, .data_size = 1211u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1221228u, .data_size = 1205u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1232494u, .data_size = 1098u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1223531u, .data_size = 1186u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1224717u, .data_size = 1166u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1225883u, .data_size = 1181u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1227064u, .data_size = 1176u, .duration_ms = 1920u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1233592u, .data_size = 1052u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1217681u, .data_size = 1146u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1218827u, .data_size = 1190u, .duration_ms = 1920u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1220017u, .data_size = 1211u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1221228u, .data_size = 1205u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1234644u, .data_size = 1098u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1223531u, .data_size = 1186u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1224717u, .data_size = 1166u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1225883u, .data_size = 1181u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1227064u, .data_size = 1176u, .duration_ms = 1920u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1228240u, .data_size = 1052u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1217681u, .data_size = 1146u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1218827u, .data_size = 1190u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1220017u, .data_size = 1211u, .duration_ms = 1440u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1221228u, .data_size = 1205u, .duration_ms = 1440u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1347452u, .data_size = 1140u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1355498u, .data_size = 1135u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1244225u, .data_size = 1115u, .duration_ms = 1440u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1245340u, .data_size = 1104u, .duration_ms = 1440u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1245340u, .data_size = 1104u, .duration_ms = 1920u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1350893u, .data_size = 1140u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1355498u, .data_size = 1135u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1244225u, .data_size = 1115u, .duration_ms = 1440u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1245340u, .data_size = 1104u, .duration_ms = 1440u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1245340u, .data_size = 1104u, .duration_ms = 1920u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1352033u, .data_size = 1140u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1355498u, .data_size = 1135u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1244225u, .data_size = 1115u, .duration_ms = 1440u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1245340u, .data_size = 1104u, .duration_ms = 1440u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1245340u, .data_size = 1104u, .duration_ms = 1920u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1353173u, .data_size = 1140u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1355498u, .data_size = 1135u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1244225u, .data_size = 1115u, .duration_ms = 1440u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1245340u, .data_size = 1104u, .duration_ms = 1440u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1245340u, .data_size = 1104u, .duration_ms = 1920u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1349753u, .data_size = 1140u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1355498u, .data_size = 1135u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1244225u, .data_size = 1115u, .duration_ms = 1440u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1245340u, .data_size = 1104u, .duration_ms = 1440u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1245340u, .data_size = 1104u, .duration_ms = 1920u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1347452u, .data_size = 1140u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1354313u, .data_size = 1185u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1218827u, .data_size = 1190u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1220017u, .data_size = 1211u, .duration_ms = 1440u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1221228u, .data_size = 1205u, .duration_ms = 1440u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1350893u, .data_size = 1140u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1354313u, .data_size = 1185u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1218827u, .data_size = 1190u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1220017u, .data_size = 1211u, .duration_ms = 1440u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1221228u, .data_size = 1205u, .duration_ms = 1440u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1352033u, .data_size = 1140u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1354313u, .data_size = 1185u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1218827u, .data_size = 1190u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1220017u, .data_size = 1211u, .duration_ms = 1440u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1221228u, .data_size = 1205u, .duration_ms = 1440u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1353173u, .data_size = 1140u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1354313u, .data_size = 1185u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1218827u, .data_size = 1190u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1220017u, .data_size = 1211u, .duration_ms = 1440u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1221228u, .data_size = 1205u, .duration_ms = 1440u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1349753u, .data_size = 1140u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1354313u, .data_size = 1185u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1218827u, .data_size = 1190u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1220017u, .data_size = 1211u, .duration_ms = 1440u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1221228u, .data_size = 1205u, .duration_ms = 1440u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1347452u, .data_size = 1140u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1348592u, .data_size = 1161u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1257049u, .data_size = 1134u, .duration_ms = 1440u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1258183u, .data_size = 1159u, .duration_ms = 1440u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1259342u, .data_size = 1159u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1350893u, .data_size = 1140u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1348592u, .data_size = 1161u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1257049u, .data_size = 1134u, .duration_ms = 1440u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1258183u, .data_size = 1159u, .duration_ms = 1440u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1259342u, .data_size = 1159u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1352033u, .data_size = 1140u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1348592u, .data_size = 1161u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1257049u, .data_size = 1134u, .duration_ms = 1440u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1258183u, .data_size = 1159u, .duration_ms = 1440u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1259342u, .data_size = 1159u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1353173u, .data_size = 1140u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1348592u, .data_size = 1161u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1257049u, .data_size = 1134u, .duration_ms = 1440u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1258183u, .data_size = 1159u, .duration_ms = 1440u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1259342u, .data_size = 1159u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1349753u, .data_size = 1140u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1348592u, .data_size = 1161u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1257049u, .data_size = 1134u, .duration_ms = 1440u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1258183u, .data_size = 1159u, .duration_ms = 1440u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1259342u, .data_size = 1159u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1310612u, .data_size = 1052u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1320591u, .data_size = 1107u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1321698u, .data_size = 1109u, .duration_ms = 1440u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1245340u, .data_size = 1104u, .duration_ms = 1440u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1245340u, .data_size = 1104u, .duration_ms = 1920u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1315093u, .data_size = 1052u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1320591u, .data_size = 1107u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1321698u, .data_size = 1109u, .duration_ms = 1440u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1245340u, .data_size = 1104u, .duration_ms = 1440u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1245340u, .data_size = 1104u, .duration_ms = 1920u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1316145u, .data_size = 1052u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1320591u, .data_size = 1107u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1321698u, .data_size = 1109u, .duration_ms = 1440u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1245340u, .data_size = 1104u, .duration_ms = 1440u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1245340u, .data_size = 1104u, .duration_ms = 1920u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1317197u, .data_size = 1052u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1320591u, .data_size = 1107u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1321698u, .data_size = 1109u, .duration_ms = 1440u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1245340u, .data_size = 1104u, .duration_ms = 1440u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1245340u, .data_size = 1104u, .duration_ms = 1920u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1314041u, .data_size = 1052u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1320591u, .data_size = 1107u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1321698u, .data_size = 1109u, .duration_ms = 1440u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1245340u, .data_size = 1104u, .duration_ms = 1440u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1245340u, .data_size = 1104u, .duration_ms = 1920u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1310612u, .data_size = 1052u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1318249u, .data_size = 1157u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1319406u, .data_size = 1185u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1220017u, .data_size = 1211u, .duration_ms = 1440u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1221228u, .data_size = 1205u, .duration_ms = 1440u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1315093u, .data_size = 1052u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1318249u, .data_size = 1157u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1319406u, .data_size = 1185u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1220017u, .data_size = 1211u, .duration_ms = 1440u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1221228u, .data_size = 1205u, .duration_ms = 1440u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1316145u, .data_size = 1052u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1318249u, .data_size = 1157u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1319406u, .data_size = 1185u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1220017u, .data_size = 1211u, .duration_ms = 1440u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1221228u, .data_size = 1205u, .duration_ms = 1440u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1317197u, .data_size = 1052u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1318249u, .data_size = 1157u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1319406u, .data_size = 1185u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1220017u, .data_size = 1211u, .duration_ms = 1440u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1221228u, .data_size = 1205u, .duration_ms = 1440u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1314041u, .data_size = 1052u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1318249u, .data_size = 1157u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1319406u, .data_size = 1185u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1220017u, .data_size = 1211u, .duration_ms = 1440u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1221228u, .data_size = 1205u, .duration_ms = 1440u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1310612u, .data_size = 1052u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1311664u, .data_size = 1167u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1312831u, .data_size = 1210u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1238111u, .data_size = 1239u, .duration_ms = 1440u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1239350u, .data_size = 1235u, .duration_ms = 1440u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1315093u, .data_size = 1052u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1311664u, .data_size = 1167u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1312831u, .data_size = 1210u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1238111u, .data_size = 1239u, .duration_ms = 1440u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1239350u, .data_size = 1235u, .duration_ms = 1440u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1316145u, .data_size = 1052u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1311664u, .data_size = 1167u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1312831u, .data_size = 1210u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1238111u, .data_size = 1239u, .duration_ms = 1440u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1239350u, .data_size = 1235u, .duration_ms = 1440u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1317197u, .data_size = 1052u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1311664u, .data_size = 1167u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1312831u, .data_size = 1210u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1238111u, .data_size = 1239u, .duration_ms = 1440u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1239350u, .data_size = 1235u, .duration_ms = 1440u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1314041u, .data_size = 1052u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1311664u, .data_size = 1167u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1312831u, .data_size = 1210u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1238111u, .data_size = 1239u, .duration_ms = 1440u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1239350u, .data_size = 1235u, .duration_ms = 1440u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1216629u, .data_size = 1052u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1217681u, .data_size = 1146u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1218827u, .data_size = 1190u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1220017u, .data_size = 1211u, .duration_ms = 1440u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1221228u, .data_size = 1205u, .duration_ms = 1440u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1229292u, .data_size = 1052u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1217681u, .data_size = 1146u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1218827u, .data_size = 1190u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1220017u, .data_size = 1211u, .duration_ms = 1440u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1221228u, .data_size = 1205u, .duration_ms = 1440u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1231442u, .data_size = 1052u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1217681u, .data_size = 1146u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1218827u, .data_size = 1190u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1220017u, .data_size = 1211u, .duration_ms = 1440u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1221228u, .data_size = 1205u, .duration_ms = 1440u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1233592u, .data_size = 1052u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1217681u, .data_size = 1146u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1218827u, .data_size = 1190u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1220017u, .data_size = 1211u, .duration_ms = 1440u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1221228u, .data_size = 1205u, .duration_ms = 1440u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1228240u, .data_size = 1052u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1217681u, .data_size = 1146u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1218827u, .data_size = 1190u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1220017u, .data_size = 1211u, .duration_ms = 1440u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1221228u, .data_size = 1205u, .duration_ms = 1440u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1216629u, .data_size = 1052u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1240585u, .data_size = 1125u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1241710u, .data_size = 691u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1242401u, .data_size = 706u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 83631u, .data_size = 671u, .duration_ms = 1440u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1229292u, .data_size = 1052u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1240585u, .data_size = 1125u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1241710u, .data_size = 691u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1242401u, .data_size = 706u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 83631u, .data_size = 671u, .duration_ms = 1440u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1231442u, .data_size = 1052u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1240585u, .data_size = 1125u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1241710u, .data_size = 691u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1242401u, .data_size = 706u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 83631u, .data_size = 671u, .duration_ms = 1440u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1233592u, .data_size = 1052u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1240585u, .data_size = 1125u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1241710u, .data_size = 691u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1242401u, .data_size = 706u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 83631u, .data_size = 671u, .duration_ms = 1440u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1228240u, .data_size = 1052u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1240585u, .data_size = 1125u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1241710u, .data_size = 691u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1242401u, .data_size = 706u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 83631u, .data_size = 671u, .duration_ms = 1440u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1216629u, .data_size = 1052u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1235742u, .data_size = 1156u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1236898u, .data_size = 1213u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1238111u, .data_size = 1239u, .duration_ms = 1440u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1239350u, .data_size = 1235u, .duration_ms = 1440u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1229292u, .data_size = 1052u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1235742u, .data_size = 1156u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1236898u, .data_size = 1213u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1238111u, .data_size = 1239u, .duration_ms = 1440u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1239350u, .data_size = 1235u, .duration_ms = 1440u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1231442u, .data_size = 1052u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1235742u, .data_size = 1156u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1236898u, .data_size = 1213u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1238111u, .data_size = 1239u, .duration_ms = 1440u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1239350u, .data_size = 1235u, .duration_ms = 1440u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1233592u, .data_size = 1052u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1235742u, .data_size = 1156u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1236898u, .data_size = 1213u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1238111u, .data_size = 1239u, .duration_ms = 1440u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1239350u, .data_size = 1235u, .duration_ms = 1440u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1228240u, .data_size = 1052u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1235742u, .data_size = 1156u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1236898u, .data_size = 1213u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1238111u, .data_size = 1239u, .duration_ms = 1440u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1239350u, .data_size = 1235u, .duration_ms = 1440u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1222433u, .data_size = 1098u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1260501u, .data_size = 1179u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1261680u, .data_size = 1214u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1262894u, .data_size = 1233u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 132904u, .data_size = 1227u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1230344u, .data_size = 1098u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1260501u, .data_size = 1179u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1261680u, .data_size = 1214u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1262894u, .data_size = 1233u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 132904u, .data_size = 1227u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1232494u, .data_size = 1098u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1260501u, .data_size = 1179u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1261680u, .data_size = 1214u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1262894u, .data_size = 1233u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 132904u, .data_size = 1227u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1234644u, .data_size = 1098u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1260501u, .data_size = 1179u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1261680u, .data_size = 1214u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1262894u, .data_size = 1233u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 132904u, .data_size = 1227u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1246444u, .data_size = 1098u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1260501u, .data_size = 1179u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1261680u, .data_size = 1214u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1262894u, .data_size = 1233u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 132904u, .data_size = 1227u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1222433u, .data_size = 1098u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1243107u, .data_size = 1118u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1244225u, .data_size = 1115u, .duration_ms = 1440u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1245340u, .data_size = 1104u, .duration_ms = 1440u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1245340u, .data_size = 1104u, .duration_ms = 1920u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1230344u, .data_size = 1098u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1243107u, .data_size = 1118u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1244225u, .data_size = 1115u, .duration_ms = 1440u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1245340u, .data_size = 1104u, .duration_ms = 1440u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1245340u, .data_size = 1104u, .duration_ms = 1920u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1232494u, .data_size = 1098u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1243107u, .data_size = 1118u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1244225u, .data_size = 1115u, .duration_ms = 1440u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1245340u, .data_size = 1104u, .duration_ms = 1440u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1245340u, .data_size = 1104u, .duration_ms = 1920u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1234644u, .data_size = 1098u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1243107u, .data_size = 1118u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1244225u, .data_size = 1115u, .duration_ms = 1440u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1245340u, .data_size = 1104u, .duration_ms = 1440u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1245340u, .data_size = 1104u, .duration_ms = 1920u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1246444u, .data_size = 1098u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1243107u, .data_size = 1118u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1244225u, .data_size = 1115u, .duration_ms = 1440u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1245340u, .data_size = 1104u, .duration_ms = 1440u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1245340u, .data_size = 1104u, .duration_ms = 1920u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1222433u, .data_size = 1098u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1255905u, .data_size = 1144u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1257049u, .data_size = 1134u, .duration_ms = 1440u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1258183u, .data_size = 1159u, .duration_ms = 1440u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1259342u, .data_size = 1159u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1230344u, .data_size = 1098u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1255905u, .data_size = 1144u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1257049u, .data_size = 1134u, .duration_ms = 1440u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1258183u, .data_size = 1159u, .duration_ms = 1440u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1259342u, .data_size = 1159u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1232494u, .data_size = 1098u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1255905u, .data_size = 1144u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1257049u, .data_size = 1134u, .duration_ms = 1440u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1258183u, .data_size = 1159u, .duration_ms = 1440u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1259342u, .data_size = 1159u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1234644u, .data_size = 1098u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1255905u, .data_size = 1144u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1257049u, .data_size = 1134u, .duration_ms = 1440u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1258183u, .data_size = 1159u, .duration_ms = 1440u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1259342u, .data_size = 1159u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1246444u, .data_size = 1098u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1255905u, .data_size = 1144u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1257049u, .data_size = 1134u, .duration_ms = 1440u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1258183u, .data_size = 1159u, .duration_ms = 1440u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1259342u, .data_size = 1159u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1222433u, .data_size = 1098u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1248720u, .data_size = 1180u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1249900u, .data_size = 1205u, .duration_ms = 1920u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1251105u, .data_size = 1220u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1252325u, .data_size = 1213u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1230344u, .data_size = 1098u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1248720u, .data_size = 1180u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1249900u, .data_size = 1205u, .duration_ms = 1920u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1251105u, .data_size = 1220u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1252325u, .data_size = 1213u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1232494u, .data_size = 1098u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1248720u, .data_size = 1180u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1249900u, .data_size = 1205u, .duration_ms = 1920u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1251105u, .data_size = 1220u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1252325u, .data_size = 1213u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1234644u, .data_size = 1098u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1248720u, .data_size = 1180u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1249900u, .data_size = 1205u, .duration_ms = 1920u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1251105u, .data_size = 1220u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1252325u, .data_size = 1213u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1246444u, .data_size = 1098u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1248720u, .data_size = 1180u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1249900u, .data_size = 1205u, .duration_ms = 1920u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1251105u, .data_size = 1220u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1252325u, .data_size = 1213u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1222433u, .data_size = 1098u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1253538u, .data_size = 1186u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1224717u, .data_size = 1166u, .duration_ms = 1920u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1254724u, .data_size = 1181u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 635725u, .data_size = 1179u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1230344u, .data_size = 1098u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1253538u, .data_size = 1186u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1224717u, .data_size = 1166u, .duration_ms = 1920u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1254724u, .data_size = 1181u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 635725u, .data_size = 1179u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1232494u, .data_size = 1098u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1253538u, .data_size = 1186u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1224717u, .data_size = 1166u, .duration_ms = 1920u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1254724u, .data_size = 1181u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 635725u, .data_size = 1179u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1234644u, .data_size = 1098u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1253538u, .data_size = 1186u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1224717u, .data_size = 1166u, .duration_ms = 1920u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1254724u, .data_size = 1181u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 635725u, .data_size = 1179u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1246444u, .data_size = 1098u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1253538u, .data_size = 1186u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1224717u, .data_size = 1166u, .duration_ms = 1920u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1254724u, .data_size = 1181u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 635725u, .data_size = 1179u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1222433u, .data_size = 1098u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1247542u, .data_size = 1178u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1236898u, .data_size = 1213u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1238111u, .data_size = 1239u, .duration_ms = 1440u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1239350u, .data_size = 1235u, .duration_ms = 1440u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1230344u, .data_size = 1098u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1247542u, .data_size = 1178u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1236898u, .data_size = 1213u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1238111u, .data_size = 1239u, .duration_ms = 1440u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1239350u, .data_size = 1235u, .duration_ms = 1440u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1232494u, .data_size = 1098u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1247542u, .data_size = 1178u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1236898u, .data_size = 1213u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1238111u, .data_size = 1239u, .duration_ms = 1440u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1239350u, .data_size = 1235u, .duration_ms = 1440u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1234644u, .data_size = 1098u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1247542u, .data_size = 1178u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1236898u, .data_size = 1213u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1238111u, .data_size = 1239u, .duration_ms = 1440u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1239350u, .data_size = 1235u, .duration_ms = 1440u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1246444u, .data_size = 1098u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1247542u, .data_size = 1178u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1236898u, .data_size = 1213u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1238111u, .data_size = 1239u, .duration_ms = 1440u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1239350u, .data_size = 1235u, .duration_ms = 1440u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1264127u, .data_size = 1138u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1272235u, .data_size = 1148u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1244225u, .data_size = 1115u, .duration_ms = 1440u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1245340u, .data_size = 1104u, .duration_ms = 1440u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1245340u, .data_size = 1104u, .duration_ms = 1920u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1267611u, .data_size = 1138u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1272235u, .data_size = 1148u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1244225u, .data_size = 1115u, .duration_ms = 1440u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1245340u, .data_size = 1104u, .duration_ms = 1440u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1245340u, .data_size = 1104u, .duration_ms = 1920u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1268749u, .data_size = 1138u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1272235u, .data_size = 1148u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1244225u, .data_size = 1115u, .duration_ms = 1440u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1245340u, .data_size = 1104u, .duration_ms = 1440u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1245340u, .data_size = 1104u, .duration_ms = 1920u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1269887u, .data_size = 1138u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1272235u, .data_size = 1148u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1244225u, .data_size = 1115u, .duration_ms = 1440u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1245340u, .data_size = 1104u, .duration_ms = 1440u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1245340u, .data_size = 1104u, .duration_ms = 1920u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1266473u, .data_size = 1138u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1272235u, .data_size = 1148u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1244225u, .data_size = 1115u, .duration_ms = 1440u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1245340u, .data_size = 1104u, .duration_ms = 1440u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1245340u, .data_size = 1104u, .duration_ms = 1920u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1264127u, .data_size = 1138u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1271025u, .data_size = 1210u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1249900u, .data_size = 1205u, .duration_ms = 1920u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1251105u, .data_size = 1220u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1252325u, .data_size = 1213u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1267611u, .data_size = 1138u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1271025u, .data_size = 1210u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1249900u, .data_size = 1205u, .duration_ms = 1920u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1251105u, .data_size = 1220u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1252325u, .data_size = 1213u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1268749u, .data_size = 1138u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1271025u, .data_size = 1210u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1249900u, .data_size = 1205u, .duration_ms = 1920u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1251105u, .data_size = 1220u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1252325u, .data_size = 1213u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1269887u, .data_size = 1138u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1271025u, .data_size = 1210u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1249900u, .data_size = 1205u, .duration_ms = 1920u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1251105u, .data_size = 1220u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1252325u, .data_size = 1213u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1266473u, .data_size = 1138u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1271025u, .data_size = 1210u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1249900u, .data_size = 1205u, .duration_ms = 1920u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1251105u, .data_size = 1220u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1252325u, .data_size = 1213u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1264127u, .data_size = 1138u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1265265u, .data_size = 1208u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1236898u, .data_size = 1213u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1238111u, .data_size = 1239u, .duration_ms = 1440u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1239350u, .data_size = 1235u, .duration_ms = 1440u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1267611u, .data_size = 1138u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1265265u, .data_size = 1208u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1236898u, .data_size = 1213u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1238111u, .data_size = 1239u, .duration_ms = 1440u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1239350u, .data_size = 1235u, .duration_ms = 1440u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1268749u, .data_size = 1138u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1265265u, .data_size = 1208u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1236898u, .data_size = 1213u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1238111u, .data_size = 1239u, .duration_ms = 1440u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1239350u, .data_size = 1235u, .duration_ms = 1440u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1269887u, .data_size = 1138u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1265265u, .data_size = 1208u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1236898u, .data_size = 1213u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1238111u, .data_size = 1239u, .duration_ms = 1440u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1239350u, .data_size = 1235u, .duration_ms = 1440u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1266473u, .data_size = 1138u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1265265u, .data_size = 1208u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1236898u, .data_size = 1213u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1238111u, .data_size = 1239u, .duration_ms = 1440u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1239350u, .data_size = 1235u, .duration_ms = 1440u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1337666u, .data_size = 1047u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1345205u, .data_size = 1154u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1261680u, .data_size = 1214u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1262894u, .data_size = 1233u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 132904u, .data_size = 1227u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1340903u, .data_size = 1047u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1345205u, .data_size = 1154u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1261680u, .data_size = 1214u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1262894u, .data_size = 1233u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 132904u, .data_size = 1227u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1341950u, .data_size = 1047u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1345205u, .data_size = 1154u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1261680u, .data_size = 1214u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1262894u, .data_size = 1233u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 132904u, .data_size = 1227u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1342997u, .data_size = 1047u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1345205u, .data_size = 1154u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1261680u, .data_size = 1214u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1262894u, .data_size = 1233u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 132904u, .data_size = 1227u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1339856u, .data_size = 1047u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1345205u, .data_size = 1154u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1261680u, .data_size = 1214u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1262894u, .data_size = 1233u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 132904u, .data_size = 1227u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1337666u, .data_size = 1047u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1346359u, .data_size = 1093u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1244225u, .data_size = 1115u, .duration_ms = 1440u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1245340u, .data_size = 1104u, .duration_ms = 1440u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1245340u, .data_size = 1104u, .duration_ms = 1920u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1340903u, .data_size = 1047u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1346359u, .data_size = 1093u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1244225u, .data_size = 1115u, .duration_ms = 1440u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1245340u, .data_size = 1104u, .duration_ms = 1440u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1245340u, .data_size = 1104u, .duration_ms = 1920u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1341950u, .data_size = 1047u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1346359u, .data_size = 1093u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1244225u, .data_size = 1115u, .duration_ms = 1440u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1245340u, .data_size = 1104u, .duration_ms = 1440u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1245340u, .data_size = 1104u, .duration_ms = 1920u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1342997u, .data_size = 1047u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1346359u, .data_size = 1093u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1244225u, .data_size = 1115u, .duration_ms = 1440u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1245340u, .data_size = 1104u, .duration_ms = 1440u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1245340u, .data_size = 1104u, .duration_ms = 1920u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1339856u, .data_size = 1047u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1346359u, .data_size = 1093u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1244225u, .data_size = 1115u, .duration_ms = 1440u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1245340u, .data_size = 1104u, .duration_ms = 1440u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1245340u, .data_size = 1104u, .duration_ms = 1920u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1337666u, .data_size = 1047u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1338713u, .data_size = 1143u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1218827u, .data_size = 1190u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1220017u, .data_size = 1211u, .duration_ms = 1440u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1221228u, .data_size = 1205u, .duration_ms = 1440u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1340903u, .data_size = 1047u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1338713u, .data_size = 1143u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1218827u, .data_size = 1190u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1220017u, .data_size = 1211u, .duration_ms = 1440u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1221228u, .data_size = 1205u, .duration_ms = 1440u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1341950u, .data_size = 1047u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1338713u, .data_size = 1143u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1218827u, .data_size = 1190u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1220017u, .data_size = 1211u, .duration_ms = 1440u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1221228u, .data_size = 1205u, .duration_ms = 1440u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1342997u, .data_size = 1047u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1338713u, .data_size = 1143u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1218827u, .data_size = 1190u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1220017u, .data_size = 1211u, .duration_ms = 1440u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1221228u, .data_size = 1205u, .duration_ms = 1440u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1339856u, .data_size = 1047u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1338713u, .data_size = 1143u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1218827u, .data_size = 1190u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1220017u, .data_size = 1211u, .duration_ms = 1440u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1221228u, .data_size = 1205u, .duration_ms = 1440u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1337666u, .data_size = 1047u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1344044u, .data_size = 1161u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1224717u, .data_size = 1166u, .duration_ms = 1920u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1254724u, .data_size = 1181u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 635725u, .data_size = 1179u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1340903u, .data_size = 1047u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1344044u, .data_size = 1161u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1224717u, .data_size = 1166u, .duration_ms = 1920u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1254724u, .data_size = 1181u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 635725u, .data_size = 1179u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1341950u, .data_size = 1047u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1344044u, .data_size = 1161u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1224717u, .data_size = 1166u, .duration_ms = 1920u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1254724u, .data_size = 1181u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 635725u, .data_size = 1179u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1342997u, .data_size = 1047u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1344044u, .data_size = 1161u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1224717u, .data_size = 1166u, .duration_ms = 1920u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1254724u, .data_size = 1181u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 635725u, .data_size = 1179u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1339856u, .data_size = 1047u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1344044u, .data_size = 1161u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1224717u, .data_size = 1166u, .duration_ms = 1920u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1254724u, .data_size = 1181u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 635725u, .data_size = 1179u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1297534u, .data_size = 1106u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1305395u, .data_size = 1111u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1244225u, .data_size = 1115u, .duration_ms = 1440u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1245340u, .data_size = 1104u, .duration_ms = 1440u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1245340u, .data_size = 1104u, .duration_ms = 1920u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1300917u, .data_size = 1106u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1305395u, .data_size = 1111u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1244225u, .data_size = 1115u, .duration_ms = 1440u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1245340u, .data_size = 1104u, .duration_ms = 1440u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1245340u, .data_size = 1104u, .duration_ms = 1920u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1302023u, .data_size = 1106u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1305395u, .data_size = 1111u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1244225u, .data_size = 1115u, .duration_ms = 1440u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1245340u, .data_size = 1104u, .duration_ms = 1440u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1245340u, .data_size = 1104u, .duration_ms = 1920u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1303129u, .data_size = 1106u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1305395u, .data_size = 1111u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1244225u, .data_size = 1115u, .duration_ms = 1440u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1245340u, .data_size = 1104u, .duration_ms = 1440u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1245340u, .data_size = 1104u, .duration_ms = 1920u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1299811u, .data_size = 1106u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1305395u, .data_size = 1111u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1244225u, .data_size = 1115u, .duration_ms = 1440u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1245340u, .data_size = 1104u, .duration_ms = 1440u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1245340u, .data_size = 1104u, .duration_ms = 1920u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1290826u, .data_size = 1105u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1304235u, .data_size = 1160u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1218827u, .data_size = 1190u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1220017u, .data_size = 1211u, .duration_ms = 1440u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1221228u, .data_size = 1205u, .duration_ms = 1440u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1294219u, .data_size = 1105u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1304235u, .data_size = 1160u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1218827u, .data_size = 1190u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1220017u, .data_size = 1211u, .duration_ms = 1440u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1221228u, .data_size = 1205u, .duration_ms = 1440u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1295324u, .data_size = 1105u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1304235u, .data_size = 1160u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1218827u, .data_size = 1190u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1220017u, .data_size = 1211u, .duration_ms = 1440u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1221228u, .data_size = 1205u, .duration_ms = 1440u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1296429u, .data_size = 1105u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1304235u, .data_size = 1160u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1218827u, .data_size = 1190u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1220017u, .data_size = 1211u, .duration_ms = 1440u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1221228u, .data_size = 1205u, .duration_ms = 1440u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1293114u, .data_size = 1105u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1304235u, .data_size = 1160u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1218827u, .data_size = 1190u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1220017u, .data_size = 1211u, .duration_ms = 1440u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1221228u, .data_size = 1205u, .duration_ms = 1440u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1290826u, .data_size = 1105u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1291931u, .data_size = 1183u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1282564u, .data_size = 1245u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1283809u, .data_size = 1267u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 526569u, .data_size = 1263u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1294219u, .data_size = 1105u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1291931u, .data_size = 1183u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1282564u, .data_size = 1245u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1283809u, .data_size = 1267u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 526569u, .data_size = 1263u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1295324u, .data_size = 1105u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1291931u, .data_size = 1183u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1282564u, .data_size = 1245u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1283809u, .data_size = 1267u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 526569u, .data_size = 1263u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1296429u, .data_size = 1105u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1291931u, .data_size = 1183u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1282564u, .data_size = 1245u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1283809u, .data_size = 1267u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 526569u, .data_size = 1263u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1293114u, .data_size = 1105u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1291931u, .data_size = 1183u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1282564u, .data_size = 1245u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1283809u, .data_size = 1267u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 526569u, .data_size = 1263u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1297534u, .data_size = 1106u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1298640u, .data_size = 1171u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1236898u, .data_size = 1213u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1238111u, .data_size = 1239u, .duration_ms = 1440u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1239350u, .data_size = 1235u, .duration_ms = 1440u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1300917u, .data_size = 1106u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1298640u, .data_size = 1171u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1236898u, .data_size = 1213u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1238111u, .data_size = 1239u, .duration_ms = 1440u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1239350u, .data_size = 1235u, .duration_ms = 1440u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1302023u, .data_size = 1106u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1298640u, .data_size = 1171u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1236898u, .data_size = 1213u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1238111u, .data_size = 1239u, .duration_ms = 1440u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1239350u, .data_size = 1235u, .duration_ms = 1440u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1303129u, .data_size = 1106u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1298640u, .data_size = 1171u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1236898u, .data_size = 1213u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1238111u, .data_size = 1239u, .duration_ms = 1440u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1239350u, .data_size = 1235u, .duration_ms = 1440u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1299811u, .data_size = 1106u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1298640u, .data_size = 1171u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1236898u, .data_size = 1213u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1238111u, .data_size = 1239u, .duration_ms = 1440u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1239350u, .data_size = 1235u, .duration_ms = 1440u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1306506u, .data_size = 552u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1307058u, .data_size = 599u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1307657u, .data_size = 1099u, .duration_ms = 1440u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1245340u, .data_size = 1104u, .duration_ms = 1440u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1245340u, .data_size = 1104u, .duration_ms = 1920u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1306506u, .data_size = 552u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1307058u, .data_size = 599u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1307657u, .data_size = 1099u, .duration_ms = 1440u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1245340u, .data_size = 1104u, .duration_ms = 1440u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1245340u, .data_size = 1104u, .duration_ms = 1920u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1306506u, .data_size = 552u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1307058u, .data_size = 599u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1307657u, .data_size = 1099u, .duration_ms = 1440u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1245340u, .data_size = 1104u, .duration_ms = 1440u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1245340u, .data_size = 1104u, .duration_ms = 1920u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1306506u, .data_size = 552u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1307058u, .data_size = 599u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1307657u, .data_size = 1099u, .duration_ms = 1440u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1245340u, .data_size = 1104u, .duration_ms = 1440u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1245340u, .data_size = 1104u, .duration_ms = 1920u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1306506u, .data_size = 552u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1307058u, .data_size = 599u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1307657u, .data_size = 1099u, .duration_ms = 1440u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1245340u, .data_size = 1104u, .duration_ms = 1440u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1245340u, .data_size = 1104u, .duration_ms = 1920u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1306506u, .data_size = 552u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1308756u, .data_size = 659u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1309415u, .data_size = 1197u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1238111u, .data_size = 1239u, .duration_ms = 1440u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1239350u, .data_size = 1235u, .duration_ms = 1440u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1306506u, .data_size = 552u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1308756u, .data_size = 659u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1309415u, .data_size = 1197u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1238111u, .data_size = 1239u, .duration_ms = 1440u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1239350u, .data_size = 1235u, .duration_ms = 1440u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1306506u, .data_size = 552u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1308756u, .data_size = 659u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1309415u, .data_size = 1197u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1238111u, .data_size = 1239u, .duration_ms = 1440u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1239350u, .data_size = 1235u, .duration_ms = 1440u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1306506u, .data_size = 552u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1308756u, .data_size = 659u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1309415u, .data_size = 1197u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1238111u, .data_size = 1239u, .duration_ms = 1440u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1239350u, .data_size = 1235u, .duration_ms = 1440u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1306506u, .data_size = 552u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1308756u, .data_size = 659u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1309415u, .data_size = 1197u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1238111u, .data_size = 1239u, .duration_ms = 1440u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1239350u, .data_size = 1235u, .duration_ms = 1440u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1322807u, .data_size = 1046u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1330253u, .data_size = 1131u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1261680u, .data_size = 1214u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1262894u, .data_size = 1233u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 132904u, .data_size = 1227u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1326019u, .data_size = 1046u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1330253u, .data_size = 1131u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1261680u, .data_size = 1214u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1262894u, .data_size = 1233u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 132904u, .data_size = 1227u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1327065u, .data_size = 1046u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1330253u, .data_size = 1131u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1261680u, .data_size = 1214u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1262894u, .data_size = 1233u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 132904u, .data_size = 1227u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1328111u, .data_size = 1046u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1330253u, .data_size = 1131u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1261680u, .data_size = 1214u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1262894u, .data_size = 1233u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 132904u, .data_size = 1227u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1324973u, .data_size = 1046u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1330253u, .data_size = 1131u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1261680u, .data_size = 1214u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1262894u, .data_size = 1233u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 132904u, .data_size = 1227u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1331384u, .data_size = 1043u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1332427u, .data_size = 1067u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1244225u, .data_size = 1115u, .duration_ms = 1440u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1245340u, .data_size = 1104u, .duration_ms = 1440u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1245340u, .data_size = 1104u, .duration_ms = 1920u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1334537u, .data_size = 1043u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1332427u, .data_size = 1067u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1244225u, .data_size = 1115u, .duration_ms = 1440u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1245340u, .data_size = 1104u, .duration_ms = 1440u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1245340u, .data_size = 1104u, .duration_ms = 1920u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1335580u, .data_size = 1043u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1332427u, .data_size = 1067u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1244225u, .data_size = 1115u, .duration_ms = 1440u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1245340u, .data_size = 1104u, .duration_ms = 1440u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1245340u, .data_size = 1104u, .duration_ms = 1920u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1336623u, .data_size = 1043u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1332427u, .data_size = 1067u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1244225u, .data_size = 1115u, .duration_ms = 1440u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1245340u, .data_size = 1104u, .duration_ms = 1440u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1245340u, .data_size = 1104u, .duration_ms = 1920u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1333494u, .data_size = 1043u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1332427u, .data_size = 1067u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1244225u, .data_size = 1115u, .duration_ms = 1440u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1245340u, .data_size = 1104u, .duration_ms = 1440u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1245340u, .data_size = 1104u, .duration_ms = 1920u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1322807u, .data_size = 1046u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1323853u, .data_size = 1120u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1218827u, .data_size = 1190u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1220017u, .data_size = 1211u, .duration_ms = 1440u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1221228u, .data_size = 1205u, .duration_ms = 1440u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1326019u, .data_size = 1046u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1323853u, .data_size = 1120u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1218827u, .data_size = 1190u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1220017u, .data_size = 1211u, .duration_ms = 1440u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1221228u, .data_size = 1205u, .duration_ms = 1440u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1327065u, .data_size = 1046u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1323853u, .data_size = 1120u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1218827u, .data_size = 1190u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1220017u, .data_size = 1211u, .duration_ms = 1440u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1221228u, .data_size = 1205u, .duration_ms = 1440u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1328111u, .data_size = 1046u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1323853u, .data_size = 1120u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1218827u, .data_size = 1190u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1220017u, .data_size = 1211u, .duration_ms = 1440u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1221228u, .data_size = 1205u, .duration_ms = 1440u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1324973u, .data_size = 1046u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1323853u, .data_size = 1120u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1218827u, .data_size = 1190u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1220017u, .data_size = 1211u, .duration_ms = 1440u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1221228u, .data_size = 1205u, .duration_ms = 1440u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1322807u, .data_size = 1046u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1329157u, .data_size = 1096u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1257049u, .data_size = 1134u, .duration_ms = 1440u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1258183u, .data_size = 1159u, .duration_ms = 1440u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1259342u, .data_size = 1159u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1326019u, .data_size = 1046u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1329157u, .data_size = 1096u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1257049u, .data_size = 1134u, .duration_ms = 1440u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1258183u, .data_size = 1159u, .duration_ms = 1440u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1259342u, .data_size = 1159u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1327065u, .data_size = 1046u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1329157u, .data_size = 1096u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1257049u, .data_size = 1134u, .duration_ms = 1440u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1258183u, .data_size = 1159u, .duration_ms = 1440u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1259342u, .data_size = 1159u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1328111u, .data_size = 1046u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1329157u, .data_size = 1096u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1257049u, .data_size = 1134u, .duration_ms = 1440u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1258183u, .data_size = 1159u, .duration_ms = 1440u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1259342u, .data_size = 1159u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1324973u, .data_size = 1046u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1329157u, .data_size = 1096u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1257049u, .data_size = 1134u, .duration_ms = 1440u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1258183u, .data_size = 1159u, .duration_ms = 1440u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1259342u, .data_size = 1159u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1273383u, .data_size = 1130u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1286274u, .data_size = 1143u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1287417u, .data_size = 1131u, .duration_ms = 1440u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1288548u, .data_size = 1142u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1289690u, .data_size = 1136u, .duration_ms = 1440u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1276779u, .data_size = 1130u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1286274u, .data_size = 1143u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1287417u, .data_size = 1131u, .duration_ms = 1440u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1288548u, .data_size = 1142u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1289690u, .data_size = 1136u, .duration_ms = 1440u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1277909u, .data_size = 1130u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1286274u, .data_size = 1143u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1287417u, .data_size = 1131u, .duration_ms = 1440u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1288548u, .data_size = 1142u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1289690u, .data_size = 1136u, .duration_ms = 1440u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1279039u, .data_size = 1130u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1286274u, .data_size = 1143u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1287417u, .data_size = 1131u, .duration_ms = 1440u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1288548u, .data_size = 1142u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1289690u, .data_size = 1136u, .duration_ms = 1440u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1275649u, .data_size = 1130u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1286274u, .data_size = 1143u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1287417u, .data_size = 1131u, .duration_ms = 1440u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1288548u, .data_size = 1142u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1289690u, .data_size = 1136u, .duration_ms = 1440u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1273383u, .data_size = 1130u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1274513u, .data_size = 1136u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1244225u, .data_size = 1115u, .duration_ms = 1440u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1245340u, .data_size = 1104u, .duration_ms = 1440u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1245340u, .data_size = 1104u, .duration_ms = 1920u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1276779u, .data_size = 1130u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1274513u, .data_size = 1136u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1244225u, .data_size = 1115u, .duration_ms = 1440u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1245340u, .data_size = 1104u, .duration_ms = 1440u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1245340u, .data_size = 1104u, .duration_ms = 1920u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1277909u, .data_size = 1130u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1274513u, .data_size = 1136u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1244225u, .data_size = 1115u, .duration_ms = 1440u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1245340u, .data_size = 1104u, .duration_ms = 1440u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1245340u, .data_size = 1104u, .duration_ms = 1920u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1279039u, .data_size = 1130u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1274513u, .data_size = 1136u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1244225u, .data_size = 1115u, .duration_ms = 1440u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1245340u, .data_size = 1104u, .duration_ms = 1440u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1245340u, .data_size = 1104u, .duration_ms = 1920u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1275649u, .data_size = 1130u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1274513u, .data_size = 1136u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1244225u, .data_size = 1115u, .duration_ms = 1440u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1245340u, .data_size = 1104u, .duration_ms = 1440u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1245340u, .data_size = 1104u, .duration_ms = 1920u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1273383u, .data_size = 1130u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1280169u, .data_size = 1186u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1218827u, .data_size = 1190u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1220017u, .data_size = 1211u, .duration_ms = 1440u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1221228u, .data_size = 1205u, .duration_ms = 1440u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1276779u, .data_size = 1130u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1280169u, .data_size = 1186u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1218827u, .data_size = 1190u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1220017u, .data_size = 1211u, .duration_ms = 1440u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1221228u, .data_size = 1205u, .duration_ms = 1440u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1277909u, .data_size = 1130u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1280169u, .data_size = 1186u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1218827u, .data_size = 1190u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1220017u, .data_size = 1211u, .duration_ms = 1440u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1221228u, .data_size = 1205u, .duration_ms = 1440u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1279039u, .data_size = 1130u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1280169u, .data_size = 1186u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1218827u, .data_size = 1190u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1220017u, .data_size = 1211u, .duration_ms = 1440u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1221228u, .data_size = 1205u, .duration_ms = 1440u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1275649u, .data_size = 1130u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1280169u, .data_size = 1186u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1218827u, .data_size = 1190u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1220017u, .data_size = 1211u, .duration_ms = 1440u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1221228u, .data_size = 1205u, .duration_ms = 1440u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1273383u, .data_size = 1130u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1281355u, .data_size = 1209u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1282564u, .data_size = 1245u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1283809u, .data_size = 1267u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 526569u, .data_size = 1263u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1276779u, .data_size = 1130u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1281355u, .data_size = 1209u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1282564u, .data_size = 1245u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1283809u, .data_size = 1267u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 526569u, .data_size = 1263u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1277909u, .data_size = 1130u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1281355u, .data_size = 1209u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1282564u, .data_size = 1245u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1283809u, .data_size = 1267u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 526569u, .data_size = 1263u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1279039u, .data_size = 1130u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1281355u, .data_size = 1209u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1282564u, .data_size = 1245u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1283809u, .data_size = 1267u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 526569u, .data_size = 1263u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1275649u, .data_size = 1130u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1281355u, .data_size = 1209u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1282564u, .data_size = 1245u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1283809u, .data_size = 1267u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 526569u, .data_size = 1263u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1273383u, .data_size = 1130u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1285076u, .data_size = 1198u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1249900u, .data_size = 1205u, .duration_ms = 1920u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1251105u, .data_size = 1220u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1252325u, .data_size = 1213u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1276779u, .data_size = 1130u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1285076u, .data_size = 1198u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1249900u, .data_size = 1205u, .duration_ms = 1920u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1251105u, .data_size = 1220u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1252325u, .data_size = 1213u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1277909u, .data_size = 1130u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1285076u, .data_size = 1198u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1249900u, .data_size = 1205u, .duration_ms = 1920u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1251105u, .data_size = 1220u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1252325u, .data_size = 1213u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1279039u, .data_size = 1130u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1285076u, .data_size = 1198u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1249900u, .data_size = 1205u, .duration_ms = 1920u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1251105u, .data_size = 1220u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1252325u, .data_size = 1213u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1275649u, .data_size = 1130u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1285076u, .data_size = 1198u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1249900u, .data_size = 1205u, .duration_ms = 1920u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1251105u, .data_size = 1220u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 1252325u, .data_size = 1213u, .duration_ms = 960u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
  {.data_offset = 0u, .data_size = 1u, .duration_ms = 480u, .dirty_x = 0u, .dirty_y = 0u, .dirty_width = 0u, .dirty_height = 0u},
};

typedef struct {
  const char *name;
  uint16_t durations_ms[3];
} companion_browser_cemp_function_clip_timing_t;

static const companion_browser_cemp_function_clip_timing_t
    companion_browser_cemp_function_clip_timings
    [COMPANION_BROWSER_CEMP_FUNCTION_CLIP_TIMING_COUNT] = {
  {"charging", {1440u, 1440u, 480u}},
  {"recording", {960u, 480u, 960u}},
  {"speaker", {480u, 960u, 480u}},
};

typedef struct {
  uint32_t hash;
  uint16_t unique_frame_index;
} companion_browser_cemp_state_map_entry_t;

static const companion_browser_cemp_state_map_entry_t
    companion_browser_cemp_state_map[COMPANION_BROWSER_CEMP_STATE_MAP_COUNT] = {
  {0x001E42A1u, 948u}, /* tap_transition_left_e0_anticipate */
  {0x0023EF54u, 713u}, /* life_alert_e29_s1_notice_left_anticipate */
  {0x002E560Fu, 132u}, /* charging_2 */
  {0x00730F14u, 1048u}, /* tap_edge_thoughtful_focused_left_anticipate */
  {0x00769AFBu, 977u}, /* tap_edge_delighted_playful_down_accent */
  {0x0090C8EEu, 987u}, /* tap_edge_focused_alert_center_accent */
  {0x009568C6u, 1005u}, /* tap_edge_warm_delighted_left_accent */
  {0x01156C40u, 274u}, /* life_calm_e31_s2_small_breath_follow */
  {0x012E57A2u, 131u}, /* charging_1 */
  {0x015A771Cu, 460u}, /* life_warm_e0_s0_soften_anticipate */
  {0x015EC6CDu, 978u}, /* tap_edge_curious_playful_up_follow */
  {0x017D4243u, 1004u}, /* tap_edge_warm_delighted_down_anticipate */
  {0x01817D62u, 970u}, /* tap_edge_calm_sleepy_right_follow */
  {0x01EB705Au, 949u}, /* tap_transition_right_e0_accent */
  {0x022E5935u, 130u}, /* charging_0 */
  {0x022FFDBBu, 427u}, /* life_delighted_e13_s0_rest_hold */
  {0x0233825Eu, 19u}, /* life_curious_e10_s4_notice_left_settle */
  {0x024FA9D7u, 1057u}, /* tap_edge_focused_curious_down_anticipate */
  {0x026A5A55u, 392u}, /* life_delighted_e10_s2_beam_follow */
  {0x02719F73u, 114u}, /* expression_alert_v0_1_hold */
  {0x027664A9u, 309u}, /* life_curious_e8_s0_rest_hold */
  {0x028911F7u, 519u}, /* life_warm_e19_s2_soften_follow */
  {0x029E4563u, 973u}, /* tap_edge_alert_calm_up_follow */
  {0x02BE9CCEu, 417u}, /* life_delighted_e8_s2_soften_follow */
  {0x02E23456u, 965u}, /* tap_edge_curious_warm_up_accent */
  {0x02FB2B8Fu, 1000u}, /* tap_edge_warm_calm_down_orient */
  {0x031D932Fu, 1065u}, /* tap_edge_alert_calm_center_orient */
  {0x036053F5u, 965u}, /* tap_edge_curious_warm_down_accent */
  {0x039554A2u, 467u}, /* life_warm_e27_s3_notice_left_follow */
  {0x03D523F4u, 111u}, /* expression_focused_v2_2_anticipate */
  {0x03D8A7E8u, 965u}, /* tap_edge_playful_warm_right_accent */
  {0x03F1E672u, 241u}, /* life_calm_e22_s0_rest_hold */
  {0x03FBBF11u, 345u}, /* life_curious_e17_s3_notice_right_follow */
  {0x041E3EA6u, 580u}, /* life_thoughtful_e19_s3_notice_left_follow */
  {0x0428E940u, 972u}, /* tap_edge_curious_calm_up_accent */
  {0x042FA96Au, 966u}, /* tap_edge_sleepy_warm_right_follow */
  {0x043BD553u, 541u}, /* life_thoughtful_e0_s0_notice_left_orient */
  {0x04459E56u, 578u}, /* life_thoughtful_e25_s0_notice_left_orient */
  {0x0450214Eu, 467u}, /* life_warm_e12_s3_notice_left_follow */
  {0x04734197u, 396u}, /* life_delighted_e7_s2_notice_left_accent */
  {0x047DD77Au, 660u}, /* life_alert_e29_s0_rest_hold */
  {0x047F5209u, 599u}, /* life_thoughtful_e20_s0_rest_hold */
  {0x049B8C8Eu, 1005u}, /* tap_edge_warm_delighted_center_accent */
  {0x04C061DEu, 977u}, /* tap_edge_curious_playful_left_accent */
  {0x050CD9A8u, 955u}, /* tap_transition_right_e1_follow */
  {0x052F3D09u, 950u}, /* tap_edge_playful_curious_center_follow */
  {0x058A2074u, 948u}, /* tap_transition_down_e0_anticipate */
  {0x059AFE64u, 582u}, /* life_thoughtful_e11_s0_notice_right_orient */
  {0x05A08FC4u, 948u}, /* tap_transition_right_e0_anticipate */
  {0x05AAE34Cu, 114u}, /* tap_edge_curious_alert_left_settle */
  {0x05ABD0DFu, 552u}, /* life_thoughtful_e30_s0_notice_right_orient */
  {0x05C34888u, 1004u}, /* tap_edge_warm_delighted_left_anticipate */
  {0x066FF7BDu, 998u}, /* tap_edge_warm_calm_left_anticipate */
  {0x06792767u, 303u}, /* life_curious_e6_s0_rest_hold */
  {0x06B1BB6Eu, 985u}, /* tap_edge_alert_focused_right_settle */
  {0x070A746Bu, 39u}, /* expression_delighted_v0_2_anticipate */
  {0x070CA50Bu, 476u}, /* life_warm_e4_s0_notice_right_orient */
  {0x07195DB2u, 655u}, /* life_alert_e7_s2_notice_right_accent */
  {0x0721201Cu, 331u}, /* life_curious_e23_s2_notice_right_accent */
  {0x07485C81u, 569u}, /* life_thoughtful_e11_s2_notice_right_accent */
  {0x07869C77u, 70u}, /* expression_sleepy_v0_0_anticipate */
  {0x07920CF7u, 123u}, /* expression_alert_v0_1_follow */
  {0x07A31898u, 65u}, /* expression_playful_v0_1_follow */
  {0x07A7B0B5u, 76u}, /* expression_bashful_v0_0_follow */
  {0x07D15F90u, 290u}, /* life_curious_e25_s0_notice_left_orient */
  {0x07EE762Fu, 965u}, /* tap_edge_playful_warm_left_accent */
  {0x07F4EA41u, 485u}, /* life_warm_e6_s0_listen_up_orient */
  {0x0802717Au, 988u}, /* tap_edge_curious_alert_center_follow */
  {0x082EAD13u, 385u}, /* life_delighted_e26_s0_rest_hold */
  {0x0846C536u, 951u}, /* tap_edge_playful_curious_right_settle */
  {0x0862CC9Fu, 565u}, /* life_thoughtful_e9_s0_listen_up_orient */
  {0x0865CCF8u, 33u}, /* expression_delighted_v0_2_settle */
  {0x0866BFE2u, 488u}, /* life_warm_e6_s3_listen_up_follow */
  {0x0867181Eu, 278u}, /* life_curious_e6_s2_notice_left_accent */
  {0x086C74AEu, 972u}, /* tap_edge_delighted_calm_left_accent */
  {0x087F4DADu, 119u}, /* life_alert_e19_s4_notice_left_settle */
  {0x08958C3Cu, 640u}, /* life_alert_e27_s3_notice_right_follow */
  {0x089B2072u, 973u}, /* tap_edge_sleepy_calm_down_follow */
  {0x08A31C9Cu, 1040u}, /* tap_edge_bashful_calm_right_anticipate */
  {0x08AB7B95u, 141u}, /* upgrade_progress_0_75 */
  {0x08B95D9Bu, 80u}, /* expression_bashful_v0_1_accent */
  {0x08BDB494u, 982u}, /* tap_edge_curious_focused_up_anticipate */
  {0x08CD4237u, 598u}, /* life_thoughtful_e25_s2_notice_left_accent */
  {0x0929C2C4u, 71u}, /* expression_sleepy_v0_1_accent */
  {0x0929CFB7u, 1064u}, /* tap_edge_focused_calm_up_anticipate */
  {0x0935DC0Bu, 629u}, /* life_alert_e20_s3_listen_up_follow */
  {0x093F567Au, 963u}, /* tap_edge_curious_calm_right_orient */
  {0x094AF945u, 1058u}, /* tap_edge_focused_curious_up_orient */
  {0x0983AEE4u, 966u}, /* tap_edge_calm_warm_left_follow */
  {0x09B2A152u, 765u}, /* menu_ui_zh_cn_s3_o1_normal */
  {0x09B6B595u, 286u}, /* life_curious_e2_s0_question_orient */
  {0x09DED90Eu, 977u}, /* tap_edge_curious_playful_up_accent */
  {0x09E77B1Cu, 175u}, /* life_calm_e16_s3_small_breath_settle */
  {0x0A3A4649u, 1001u}, /* tap_edge_warm_delighted_left_orient */
  {0x0A641080u, 468u}, /* life_warm_e2_s0_rest_hold */
  {0x0A7F43CDu, 973u}, /* tap_edge_playful_calm_right_follow */
  {0x0A89BEFDu, 973u}, /* tap_edge_alert_calm_center_settle */
  {0x0A89C71Du, 30u}, /* expression_delighted_v0_0_anticipate */
  {0x0AAE57E8u, 1063u}, /* tap_edge_focused_alert_left_anticipate */
  {0x0AB30925u, 641u}, /* life_alert_e26_s1_notice_left_anticipate */
  {0x0ADEB5D8u, 114u}, /* expression_alert_v0_2_hold */
  {0x0B1B5F07u, 956u}, /* tap_transition_center_e1_settle */
  {0x0B1C703Cu, 965u}, /* tap_edge_calm_warm_down_accent */
  {0x0B6165BAu, 1069u}, /* tap_edge_alert_curious_left_orient */
  {0x0B6BE83Du, 91u}, /* life_thoughtful_e5_s4_listen_up_settle */
  {0x0B95C480u, 996u}, /* tap_edge_delighted_calm_up_anticipate */
  {0x0BCB72EBu, 957u}, /* tap_edge_calm_sleepy_up_orient */
  {0x0C033ED1u, 208u}, /* life_calm_e14_s3_listen_up_follow */
  {0x0C42EAFAu, 979u}, /* tap_edge_warm_playful_left_settle */
  {0x0C45EAF7u, 1u}, /* expression_calm_v0_0_orient */
  {0x0C7D5BB9u, 545u}, /* life_thoughtful_e22_s4_notice_left_settle */
  {0x0CE1DBF8u, 751u}, /* menu_ui_zh_cn_s1_o1_ack_i4 */
  {0x0D026650u, 1025u}, /* tap_edge_playful_calm_right_anticipate */
  {0x0D08F83Du, 972u}, /* tap_edge_delighted_calm_down_accent */
  {0x0D1E2760u, 1043u}, /* tap_edge_thoughtful_curious_down_anticipate */
  {0x0D2443D6u, 340u}, /* life_curious_e16_s3_listen_up_follow */
  {0x0DC7E881u, 349u}, /* life_curious_e18_s2_notice_left_accent */
  {0x0DF16AF1u, 189u}, /* life_calm_e9_s1_notice_left_anticipate */
  {0x0E0137B0u, 209u}, /* life_calm_e15_s0_rest_hold */
  {0x0E1EAFC7u, 973u}, /* tap_edge_focused_calm_right_settle */
  {0x0E20E959u, 213u}, /* life_calm_e21_s3_soften_settle */
  {0x0E236A04u, 642u}, /* life_alert_e4_s2_notice_left_accent */
  {0x0E259BFFu, 325u}, /* life_curious_e22_s2_listen_up_accent */
  {0x0E4B1902u, 764u}, /* menu_ui_zh_cn_s3_o0_ack_i3 */
  {0x0E4E157Cu, 1005u}, /* tap_edge_playful_delighted_center_accent */
  {0x0E59EE3Du, 100u}, /* expression_focused_v0_0_hold */
  {0x0E90C6F5u, 715u}, /* life_alert_e30_s0_notice_right_orient */
  {0x0E90D4BFu, 1016u}, /* tap_edge_playful_delighted_left_orient */
  {0x0EAA5A76u, 19u}, /* life_curious_e18_s4_notice_left_settle */
  {0x0EC6657Fu, 332u}, /* life_curious_e20_s3_notice_right_follow */
  {0x0EE65AE3u, 540u}, /* tap_edge_focused_thoughtful_center_settle */
  {0x0F1B6064u, 951u}, /* tap_edge_alert_curious_center_settle */
  {0x0F8D291Cu, 1030u}, /* tap_edge_sleepy_warm_left_accent */
  {0x0F8E3C70u, 102u}, /* expression_focused_v0_0_anticipate */
  {0x0F9777F5u, 973u}, /* tap_edge_sleepy_calm_center_follow */
  {0x0FCEC1B6u, 19u}, /* life_curious_e2_s3_question_settle */
  {0x0FF63A6Du, 698u}, /* life_alert_e23_s3_notice_left_follow */
  {0x10001D02u, 332u}, /* life_curious_e14_s3_notice_right_follow */
  {0x1030B3D6u, 542u}, /* life_thoughtful_e25_s1_notice_left_anticipate */
  {0x104C11D5u, 955u}, /* tap_transition_center_e1_follow */
  {0x1078C0C1u, 33u}, /* life_delighted_e16_s4_notice_right_settle */
  {0x10A58EF6u, 965u}, /* tap_edge_curious_warm_left_accent */
  {0x10AF9AE3u, 978u}, /* tap_edge_warm_playful_right_follow */
  {0x10F0102Au, 983u}, /* tap_edge_thoughtful_focused_left_accent */
  {0x10F34B13u, 33u}, /* life_delighted_e8_s3_soften_settle */
  {0x10FB17EEu, 96u}, /* expression_thoughtful_v0_2_orient */
  {0x1139E160u, 383u}, /* life_delighted_e20_s2_notice_left_accent */
  {0x1167857Du, 810u}, /* menu_ui_zh_cn_s10_o0_ack_i2 */
  {0x116A1331u, 1032u}, /* tap_edge_bashful_warm_center_anticipate */
  {0x11883337u, 661u}, /* life_alert_e17_s2_listen_up_accent */
  {0x11DE343Bu, 1049u}, /* tap_edge_thoughtful_alert_center_anticipate */
  {0x11E1E3D7u, 748u}, /* menu_ui_zh_cn_s1_o1_ack_i1 */
  {0x11F548A8u, 91u}, /* life_thoughtful_e25_s4_notice_left_settle */
  {0x120748B5u, 926u}, /* tap_local_calm_down */
  {0x121378BCu, 973u}, /* tap_edge_thoughtful_calm_down_follow */
  {0x12255472u, 47u}, /* life_warm_e28_s0_rest_hold */
  {0x122C67BFu, 161u}, /* life_calm_e3_s0_rest_hold */
  {0x1259F485u, 634u}, /* life_alert_e29_s2_notice_left_accent */
  {0x125BCF1Du, 580u}, /* life_thoughtful_e10_s3_notice_left_follow */
  {0x12A206BBu, 31u}, /* expression_delighted_v0_0_accent */
  {0x12A5121Du, 950u}, /* tap_edge_thoughtful_curious_down_follow */
  {0x12A5E9C2u, 478u}, /* life_warm_e4_s2_notice_right_accent */
  {0x12CCF3D5u, 1007u}, /* tap_edge_warm_playful_center_anticipate */
  {0x12E1E56Au, 749u}, /* menu_ui_zh_cn_s1_o1_ack_i2 */
  {0x12E7BB0Cu, 667u}, /* life_alert_e27_s2_notice_right_accent */
  {0x12FF560Eu, 972u}, /* tap_edge_playful_calm_right_accent */
  {0x13374C50u, 219u}, /* life_calm_e17_s0_notice_left_orient */
  {0x1365EBA4u, 38u}, /* expression_delighted_v2_2_orient */
  {0x136D24CEu, 930u}, /* tap_local_delighted_down */
  {0x13837F9Eu, 540u}, /* tap_edge_curious_thoughtful_up_settle */
  {0x13994E59u, 70u}, /* expression_sleepy_v0_2_anticipate */
  {0x13A48141u, 949u}, /* tap_edge_focused_curious_down_accent */
  {0x13A6E713u, 364u}, /* life_curious_e24_s1_question_anticipate */
  {0x13E1E6FDu, 750u}, /* menu_ui_zh_cn_s1_o1_ack_i3 */
  {0x13F8D3FFu, 993u}, /* tap_edge_delighted_playful_left_orient */
  {0x1403D94Cu, 959u}, /* tap_transition_down_e1_orient */
  {0x141EBBE5u, 891u}, /* menu_ui_en_s7_o1_normal */
  {0x14352529u, 653u}, /* life_alert_e27_s0_notice_right_orient */
  {0x145D5097u, 97u}, /* expression_thoughtful_v0_2_anticipate */
  {0x1460C261u, 554u}, /* life_thoughtful_e2_s2_notice_right_accent */
  {0x1475BFF1u, 101u}, /* expression_focused_v0_0_orient */
  {0x148BFEC7u, 949u}, /* tap_transition_up_e0_accent */
  {0x149B7C58u, 449u}, /* tap_edge_playful_delighted_right_settle */
  {0x149F5324u, 984u}, /* tap_edge_thoughtful_focused_right_follow */
  {0x14AD78E7u, 449u}, /* tap_edge_warm_delighted_left_settle */
  {0x14B74EF4u, 33u}, /* expression_delighted_v2_0_settle */
  {0x14BD9986u, 788u}, /* menu_ui_zh_cn_s7_o1_normal */
  {0x15338882u, 35u}, /* expression_delighted_v2_1_anticipate */
  {0x1562FB5Fu, 965u}, /* tap_edge_playful_warm_up_accent */
  {0x15B7E13Du, 1008u}, /* tap_edge_warm_bashful_up_anticipate */
  {0x15E1C907u, 850u}, /* menu_ui_en_s1_o1_normal */
  {0x15E9FF12u, 395u}, /* life_delighted_e3_s1_notice_left_anticipate */
  {0x15EC78A7u, 33u}, /* life_delighted_e17_s3_soften_settle */
  {0x15F08CAEu, 624u}, /* life_alert_e0_s2_startle_follow */
  {0x15F85A3Eu, 537u}, /* life_warm_e29_s0_notice_right_orient */
  {0x160332E2u, 949u}, /* tap_edge_playful_curious_center_accent */
  {0x16072603u, 985u}, /* tap_edge_thoughtful_focused_center_settle */
  {0x1639FFBAu, 383u}, /* life_delighted_e0_s2_notice_left_accent */
  {0x163C528Bu, 972u}, /* tap_edge_thoughtful_calm_down_accent */
  {0x168D5D75u, 643u}, /* life_alert_e12_s3_notice_left_follow */
  {0x1696331Bu, 978u}, /* tap_edge_delighted_playful_up_follow */
  {0x169FC9DCu, 323u}, /* life_curious_e12_s0_rest_hold */
  {0x16A8058Du, 204u}, /* life_calm_e26_s4_listen_up_settle */
  {0x16AD305Fu, 183u}, /* life_calm_e7_s1_small_breath_accent */
  {0x16B038B4u, 629u}, /* life_alert_e25_s3_listen_up_follow */
  {0x16E2227Du, 626u}, /* life_alert_e1_s0_listen_up_orient */
  {0x16E49EE0u, 825u}, /* menu_ui_en_s0_o0_ack_i3 */
  {0x16FBDECCu, 962u}, /* tap_edge_calm_curious_right_orient */
  {0x17170B17u, 405u}, /* life_delighted_e21_s1_soften_accent */
  {0x1728366Eu, 1039u}, /* tap_edge_bashful_curious_center_accent */
  {0x1742FD4Eu, 476u}, /* life_warm_e10_s0_notice_right_orient */
  {0x17541338u, 973u}, /* tap_edge_sleepy_calm_down_settle */
  {0x175DF9D8u, 668u}, /* life_alert_e12_s0_rest_hold */
  {0x175F7770u, 70u}, /* expression_sleepy_v0_2_hold */
  {0x176BCEB0u, 1038u}, /* tap_edge_bashful_curious_center_anticipate */
  {0x178F1DA3u, 377u}, /* life_curious_e30_s1_notice_right_anticipate */
  {0x179450A6u, 667u}, /* life_alert_e18_s2_notice_right_accent */
  {0x17CDEF62u, 956u}, /* tap_transition_right_e1_settle */
  {0x17D9EB48u, 339u}, /* life_curious_e16_s2_listen_up_accent */
  {0x17DE8124u, 1031u}, /* tap_edge_bashful_warm_center_orient */
  {0x17E4A073u, 824u}, /* menu_ui_en_s0_o0_ack_i2 */
  {0x183CF5ACu, 72u}, /* expression_bashful_v0_1_hold */
  {0x1866800Au, 553u}, /* life_thoughtful_e6_s1_notice_right_anticipate */
  {0x18754917u, 679u}, /* life_alert_e15_s0_notice_left_orient */
  {0x18AD4A10u, 86u}, /* expression_thoughtful_v0_0_hold */
  {0x18BCF85Au, 520u}, /* life_warm_e20_s0_rest_hold */
  {0x18C0D959u, 47u}, /* life_warm_e3_s3_soften_settle */
  {0x18E4A206u, 823u}, /* menu_ui_en_s0_o0_ack_i1 */
  {0x1900B5B1u, 596u}, /* life_thoughtful_e28_s0_rest_hold */
  {0x1903D45Cu, 357u}, /* life_curious_e21_s0_notice_left_orient */
  {0x190C7B5Au, 85u}, /* expression_bashful_v1_2_follow */
  {0x1915BEAFu, 89u}, /* expression_thoughtful_v0_0_accent */
  {0x192E5EA8u, 869u}, /* menu_ui_en_s3_o1_processing_i1 */
  {0x193C48A4u, 19u}, /* life_curious_e8_s4_listen_up_settle */
  {0x1961D119u, 661u}, /* life_alert_e20_s2_listen_up_accent */
  {0x1986D841u, 1045u}, /* tap_edge_thoughtful_curious_down_orient */
  {0x19877B7Fu, 704u}, /* life_alert_e25_s1_listen_up_anticipate */
  {0x19889446u, 1002u}, /* tap_edge_warm_curious_right_orient */
  {0x19AFC1BFu, 973u}, /* tap_edge_delighted_calm_up_settle */
  {0x19E4A399u, 822u}, /* menu_ui_en_s0_o0_ack_i0 */
  {0x19FB5926u, 9u}, /* expression_calm_v0_1_follow */
  {0x1A00FFBCu, 1048u}, /* tap_edge_thoughtful_focused_up_anticipate */
  {0x1A0E649Fu, 973u}, /* tap_edge_alert_calm_center_follow */
  {0x1A36E4CAu, 951u}, /* tap_transition_up_e0_settle */
  {0x1A5FFE3Eu, 973u}, /* tap_edge_thoughtful_calm_down_settle */
  {0x1A82F9B8u, 939u}, /* tap_local_bashful_left */
  {0x1A9AA1E4u, 232u}, /* life_calm_e19_s2_listen_up_accent */
  {0x1ABA32BEu, 549u}, /* life_thoughtful_e1_s2_listen_up_accent */
  {0x1AC52EC0u, 815u}, /* menu_ui_zh_cn_s11_o0_normal */
  {0x1ACB8949u, 987u}, /* tap_edge_thoughtful_alert_left_accent */
  {0x1ACF38CAu, 171u}, /* life_calm_e5_s0_listen_up_orient */
  {0x1ADB169Fu, 951u}, /* tap_edge_thoughtful_curious_down_settle */
  {0x1ADD7DC0u, 925u}, /* tap_local_calm_up */
  {0x1B06D4E8u, 70u}, /* tap_edge_calm_sleepy_right_settle */
  {0x1B324B99u, 1047u}, /* tap_edge_thoughtful_curious_right_orient */
  {0x1B53323Eu, 47u}, /* life_warm_e8_s3_soften_settle */
  {0x1B581C93u, 583u}, /* life_thoughtful_e14_s1_notice_right_anticipate */
  {0x1B65C94Au, 1070u}, /* tap_edge_alert_calm_right_orient */
  {0x1BDCB666u, 404u}, /* life_delighted_e21_s0_soften_anticipate */
  {0x1C052482u, 1034u}, /* tap_edge_bashful_calm_up_orient */
  {0x1C07F11Fu, 381u}, /* life_delighted_e0_s0_notice_left_orient */
  {0x1C1186BBu, 448u}, /* life_delighted_e22_s3_notice_right_follow */
  {0x1C2E6361u, 870u}, /* menu_ui_en_s3_o1_processing_i2 */
  {0x1C331560u, 794u}, /* menu_ui_zh_cn_s8_o1_ack_i1 */
  {0x1C33B9F9u, 781u}, /* menu_ui_zh_cn_s5_o0_normal */
  {0x1C63198Bu, 951u}, /* tap_edge_focused_curious_center_settle */
  {0x1C9A5E68u, 999u}, /* tap_edge_warm_calm_up_orient */
  {0x1C9A72FCu, 953u}, /* tap_transition_left_e1_anticipate */
  {0x1C9D3DA7u, 710u}, /* life_alert_e28_s0_rest_hold */
  {0x1CC8C805u, 966u}, /* tap_edge_curious_warm_up_follow */
  {0x1CEAD1C8u, 435u}, /* life_delighted_e15_s2_notice_left_accent */
  {0x1D0E320Au, 248u}, /* life_calm_e24_s0_soften_anticipate */
  {0x1D12AE54u, 76u}, /* expression_bashful_v1_0_follow */
  {0x1D2C24A7u, 1043u}, /* tap_edge_thoughtful_curious_up_anticipate */
  {0x1D3566CDu, 564u}, /* life_thoughtful_e25_s3_notice_left_follow */
  {0x1D6FC2DDu, 969u}, /* tap_edge_calm_sleepy_right_accent */
  {0x1D8C9BFAu, 549u}, /* life_thoughtful_e23_s2_listen_up_accent */
  {0x1DAE8330u, 471u}, /* life_warm_e2_s2_listen_up_accent */
  {0x1DB5FF34u, 19u}, /* life_curious_e22_s4_listen_up_settle */
  {0x1DC7E9E1u, 71u}, /* expression_sleepy_v0_0_accent */
  {0x1DCCBD35u, 506u}, /* life_warm_e13_s2_soften_follow */
  {0x1DFA72E3u, 1040u}, /* tap_edge_bashful_calm_center_anticipate */
  {0x1E0C83F5u, 47u}, /* expression_warm_v0_2_settle */
  {0x1E1955E7u, 966u}, /* tap_edge_sleepy_warm_left_follow */
  {0x1E32C8D4u, 282u}, /* life_curious_e1_s2_notice_right_accent */
  {0x1E331886u, 796u}, /* menu_ui_zh_cn_s8_o1_ack_i3 */
  {0x1E445E4Cu, 73u}, /* tap_local_bashful_center */
  {0x1ED712CBu, 951u}, /* tap_edge_playful_curious_left_settle */
  {0x1EFD79EAu, 33u}, /* life_delighted_e19_s4_notice_right_settle */
  {0x1F331A19u, 795u}, /* menu_ui_zh_cn_s8_o1_ack_i2 */
  {0x1F47B4CDu, 25u}, /* expression_curious_v0_2_anticipate */
  {0x1F4888D5u, 236u}, /* life_calm_e20_s0_small_breath_anticipate */
  {0x1F8FFD6Eu, 669u}, /* life_alert_e12_s0_notice_left_orient */
  {0x1FA5FB8Du, 1037u}, /* tap_edge_bashful_calm_right_orient */
  {0x1FB6B8DFu, 951u}, /* tap_edge_alert_curious_right_settle */
  {0x1FE7019Fu, 1049u}, /* tap_edge_thoughtful_alert_left_anticipate */
  {0x200A5AE2u, 165u}, /* life_calm_e4_s0_notice_left_orient */
  {0x201491F3u, 579u}, /* life_thoughtful_e22_s1_notice_left_anticipate */
  {0x202381EDu, 676u}, /* life_alert_e18_s1_notice_right_anticipate */
  {0x2099BC9Du, 514u}, /* life_warm_e22_s2_soften_follow */
  {0x209ED216u, 985u}, /* tap_edge_thoughtful_focused_right_settle */
  {0x20B6C3BBu, 1005u}, /* tap_edge_playful_delighted_down_accent */
  {0x20C679FAu, 100u}, /* expression_focused_v2_1_hold */
  {0x20DAB1A6u, 987u}, /* tap_edge_focused_alert_up_accent */
  {0x20EFFD03u, 70u}, /* tap_local_sleepy_up */
  {0x20F2C18Fu, 304u}, /* life_curious_e6_s1_notice_left_anticipate */
  {0x20F7B04Cu, 966u}, /* tap_edge_bashful_warm_left_follow */
  {0x21116338u, 860u}, /* menu_ui_en_s1_o3_ack_i3 */
  {0x21230075u, 1072u}, /* tap_edge_alert_calm_down_anticipate */
  {0x21331D3Fu, 797u}, /* menu_ui_zh_cn_s8_o1_ack_i4 */
  {0x21416B15u, 608u}, /* life_thoughtful_e24_s0_rest_hold */
  {0x214C00F2u, 440u}, /* life_delighted_e18_s0_beam_anticipate */
  {0x21B57549u, 250u}, /* life_calm_e25_s0_rest_hold */
  {0x21F68D89u, 867u}, /* menu_ui_en_s3_o0_ack_i3 */
  {0x21F9D01Cu, 152u}, /* life_calm_e1_s0_small_breath_anticipate */
  {0x21FAEB16u, 1015u}, /* tap_edge_playful_curious_down_orient */
  {0x2209F03Au, 952u}, /* tap_edge_curious_alert_center_orient */
  {0x221297D1u, 70u}, /* tap_edge_calm_sleepy_up_settle */
  {0x222A2265u, 1041u}, /* tap_edge_bashful_calm_center_accent */
  {0x2250476Du, 465u}, /* life_warm_e27_s1_notice_left_anticipate */
  {0x227D3900u, 119u}, /* life_alert_e31_s4_listen_up_settle */
  {0x2288C86Au, 949u}, /* tap_edge_focused_curious_up_accent */
  {0x22930D6Au, 973u}, /* tap_edge_alert_calm_right_follow */
  {0x229B2D07u, 626u}, /* life_alert_e16_s0_startle_orient */
  {0x229B822Au, 959u}, /* tap_edge_curious_warm_down_orient */
  {0x2337AEE8u, 254u}, /* life_calm_e28_s0_rest_hold */
  {0x237FD791u, 92u}, /* tap_local_thoughtful_center */
  {0x2387DFDAu, 983u}, /* tap_edge_alert_focused_up_accent */
  {0x240435E2u, 394u}, /* life_delighted_e3_s0_notice_left_orient */
  {0x24644C56u, 207u}, /* life_calm_e14_s1_listen_up_anticipate */
  {0x246647E9u, 545u}, /* life_thoughtful_e1_s4_listen_up_settle */
  {0x247B594Cu, 62u}, /* expression_playful_v0_1_orient */
  {0x24D0E45Fu, 245u}, /* life_calm_e23_s0_rest_hold */
  {0x24DDC86Cu, 969u}, /* tap_edge_calm_sleepy_center_accent */
  {0x250737F7u, 949u}, /* tap_transition_left_e0_accent */
  {0x25329424u, 972u}, /* tap_edge_alert_calm_center_accent */
  {0x2559F3C3u, 47u}, /* life_warm_e6_s4_listen_up_settle */
  {0x25658437u, 967u}, /* tap_edge_curious_warm_up_settle */
  {0x2586D646u, 578u}, /* life_thoughtful_e10_s0_notice_left_orient */
  {0x2587F7F9u, 484u}, /* life_warm_e5_s4_notice_left_settle */
  {0x2589AC0Au, 738u}, /* menu_ui_zh_cn_s0_o4_normal */
  {0x25A1A423u, 542u}, /* life_thoughtful_e4_s1_notice_left_anticipate */
  {0x25A4D65Du, 950u}, /* tap_edge_calm_curious_up_follow */
  {0x25ADEF07u, 33u}, /* expression_delighted_v0_1_settle */
  {0x25B5B2A7u, 397u}, /* life_delighted_e23_s3_notice_left_follow */
  {0x25CC8368u, 1026u}, /* tap_edge_sleepy_warm_down_orient */
  {0x25FCC13Fu, 887u}, /* menu_ui_en_s6_o0_normal */
  {0x25FF1096u, 176u}, /* life_calm_e6_s0_rest_hold */
  {0x26116CB2u, 905u}, /* menu_ui_en_s9_o0_normal */
  {0x26471934u, 708u}, /* life_alert_e26_s2_notice_left_accent */
  {0x26499DE4u, 645u}, /* life_alert_e5_s0_rest_hold */
  {0x2666272Bu, 502u}, /* life_warm_e21_s0_notice_left_orient */
  {0x26683538u, 1043u}, /* tap_edge_thoughtful_curious_right_anticipate */
  {0x267C226Du, 959u}, /* tap_edge_curious_alert_down_orient */
  {0x26C50443u, 954u}, /* tap_edge_curious_thoughtful_left_accent */
  {0x26ECC34Cu, 336u}, /* life_curious_e28_s2_question_accent */
  {0x26F27876u, 590u}, /* life_thoughtful_e27_s2_notice_right_accent */
  {0x27007A22u, 995u}, /* tap_edge_delighted_playful_center_anticipate */
  {0x27289614u, 290u}, /* life_curious_e10_s0_notice_left_orient */
  {0x274E5D4Au, 966u}, /* tap_edge_curious_warm_down_follow */
  {0x274F79E4u, 293u}, /* life_curious_e23_s0_rest_hold */
  {0x275EDEF3u, 1000u}, /* tap_edge_warm_playful_down_orient */
  {0x27BC5FE1u, 632u}, /* tap_local_alert_left */
  {0x27DAD91Bu, 284u}, /* life_curious_e9_s4_notice_right_settle */
  {0x2806B929u, 1058u}, /* tap_edge_focused_alert_up_orient */
  {0x28116E3Du, 861u}, /* menu_ui_en_s1_o3_ack_i4 */
  {0x2820BB67u, 986u}, /* tap_edge_curious_alert_left_anticipate */
  {0x283F2ACCu, 985u}, /* tap_edge_alert_focused_down_settle */
  {0x287C7872u, 70u}, /* expression_sleepy_v0_2_settle */
  {0x287DA648u, 119u}, /* life_alert_e23_s4_notice_left_settle */
  {0x28BC2361u, 770u}, /* menu_ui_zh_cn_s3_o2_processing_i2 */
  {0x28CEE1F2u, 183u}, /* life_calm_e13_s1_small_breath_accent */
  {0x28F657C2u, 228u}, /* life_calm_e18_s4_notice_right_settle */
  {0x28F87264u, 985u}, /* tap_edge_thoughtful_focused_down_settle */
  {0x28FBD3B8u, 544u}, /* life_thoughtful_e0_s3_notice_left_follow */
  {0x290A00B2u, 973u}, /* tap_edge_bashful_calm_up_follow */
  {0x290A371Fu, 643u}, /* life_alert_e29_s3_notice_left_follow */
  {0x290E0C19u, 973u}, /* tap_edge_bashful_calm_down_follow */
  {0x29254698u, 960u}, /* tap_edge_calm_warm_left_orient */
  {0x29766660u, 348u}, /* life_curious_e29_s1_notice_left_anticipate */
  {0x2984ADF7u, 120u}, /* expression_alert_v0_1_orient */
  {0x2998B3A2u, 964u}, /* tap_edge_calm_warm_down_anticipate */
  {0x29A69284u, 919u}, /* menu_ui_en_s11_o0_processing_i1 */
  {0x29BC24F4u, 772u}, /* menu_ui_zh_cn_s3_o2_processing_i5 */
  {0x29D8852Bu, 966u}, /* tap_edge_playful_warm_right_follow */
  {0x2A0CF6FCu, 1057u}, /* tap_edge_focused_curious_left_anticipate */
  {0x2A203773u, 480u}, /* life_warm_e5_s0_rest_hold */
  {0x2A20A60Cu, 19u}, /* life_curious_e20_s4_notice_right_settle */
  {0x2A59FEC7u, 33u}, /* life_delighted_e26_s3_beam_settle */
  {0x2A60CD28u, 430u}, /* life_delighted_e14_s0_rest_hold */
  {0x2A6C3728u, 512u}, /* life_warm_e20_s3_listen_up_follow */
  {0x2A92417Au, 505u}, /* life_warm_e16_s1_soften_accent */
  {0x2A94B8B4u, 544u}, /* life_thoughtful_e17_s3_notice_left_follow */
  {0x2A96C3ABu, 904u}, /* menu_ui_en_s8_o2_ack_i4 */
  {0x2A9E50FBu, 983u}, /* tap_edge_alert_focused_right_accent */
  {0x2ABA04AFu, 973u}, /* tap_edge_delighted_calm_left_settle */
  {0x2AC92AB3u, 47u}, /* life_warm_e25_s3_soften_settle */
  {0x2ACDF89Fu, 505u}, /* life_warm_e22_s1_soften_accent */
  {0x2ADAD075u, 626u}, /* life_alert_e9_s0_listen_up_orient */
  {0x2ADB3FB4u, 508u}, /* life_warm_e26_s3_notice_right_follow */
  {0x2ADEA1D5u, 37u}, /* expression_delighted_v0_1_follow */
  {0x2AF1D9BDu, 422u}, /* life_delighted_e11_s0_notice_left_orient */
  {0x2B030F68u, 1010u}, /* tap_edge_warm_bashful_center_follow */
  {0x2B043399u, 20u}, /* tap_local_curious_center */
  {0x2B2C7DFBu, 320u}, /* life_curious_e11_s0_rest_hold */
  {0x2B4B799Cu, 421u}, /* life_delighted_e10_s0_rest_hold */
  {0x2B6A26FEu, 47u}, /* life_warm_e23_s4_notice_right_settle */
  {0x2BA15AB3u, 956u}, /* tap_transition_left_e1_settle */
  {0x2BB18A0Eu, 973u}, /* tap_edge_focused_calm_up_follow */
  {0x2BCCBD8Du, 622u}, /* tap_local_alert_up */
  {0x2BDC54FAu, 379u}, /* life_curious_e31_s1_listen_up_anticipate */
  {0x2BF6880Bu, 281u}, /* life_curious_e1_s1_notice_right_anticipate */
  {0x2C788D2Bu, 464u}, /* life_warm_e9_s0_notice_left_orient */
  {0x2C78CE4Fu, 521u}, /* life_warm_e20_s0_listen_up_orient */
  {0x2CA7272Fu, 1026u}, /* tap_edge_sleepy_warm_center_orient */
  {0x2CC6FA70u, 317u}, /* life_curious_e10_s1_notice_left_anticipate */
  {0x2CCA6050u, 972u}, /* tap_edge_alert_calm_up_accent */
  {0x2CF16DDDu, 371u}, /* life_curious_e27_s1_listen_up_anticipate */
  {0x2D088D4Bu, 56u}, /* expression_playful_v0_2_hold */
  {0x2D0BE50Fu, 654u}, /* life_alert_e30_s1_notice_right_anticipate */
  {0x2D0E3242u, 279u}, /* life_curious_e0_s3_notice_left_follow */
  {0x2D53BAC0u, 79u}, /* expression_bashful_v1_1_anticipate */
  {0x2D596426u, 987u}, /* tap_edge_focused_alert_left_accent */
  {0x2D7818F9u, 953u}, /* tap_transition_down_e1_anticipate */
  {0x2D7C4961u, 449u}, /* tap_edge_playful_delighted_up_settle */
  {0x2D86F2C6u, 643u}, /* life_alert_e8_s3_notice_left_follow */
  {0x2D95E21Cu, 322u}, /* life_curious_e11_s2_question_accent */
  {0x2DA08162u, 580u}, /* life_thoughtful_e28_s3_notice_left_follow */
  {0x2DAD6CB1u, 556u}, /* life_thoughtful_e30_s4_notice_right_settle */
  {0x2DB9BDB0u, 106u}, /* tap_local_focused_center */
  {0x2DBA7524u, 1066u}, /* tap_edge_alert_focused_center_anticipate */
  {0x2DDD0E59u, 584u}, /* life_thoughtful_e15_s0_rest_hold */
  {0x2DDFC40Fu, 71u}, /* expression_sleepy_v0_2_accent */
  {0x2E02697Eu, 471u}, /* life_warm_e11_s2_listen_up_accent */
  {0x2E40F8FCu, 105u}, /* expression_focused_v2_1_settle */
  {0x2E4ACC50u, 587u}, /* life_thoughtful_e12_s3_listen_up_follow */
  {0x2E65A092u, 693u}, /* life_alert_e21_s0_rest_hold */
  {0x2E7484FEu, 239u}, /* life_calm_e21_s1_soften_accent */
  {0x2E890FB8u, 965u}, /* tap_edge_playful_warm_down_accent */
  {0x2E8E4295u, 465u}, /* life_warm_e30_s1_notice_left_anticipate */
  {0x2E955D07u, 522u}, /* life_warm_e21_s0_rest_hold */
  {0x2E9DA929u, 170u}, /* life_calm_e5_s0_rest_hold */
  {0x2EA09775u, 1045u}, /* tap_edge_thoughtful_alert_down_orient */
  {0x2ED01A7Au, 640u}, /* life_alert_e18_s3_notice_right_follow */
  {0x2ED5E1D8u, 921u}, /* menu_ui_en_s12_o0_normal */
  {0x2EEA3F8Cu, 386u}, /* tap_local_delighted_right */
  {0x2EEFA138u, 996u}, /* tap_edge_delighted_calm_center_anticipate */
  {0x2EF3635Cu, 11u}, /* expression_calm_v0_2_anticipate */
  {0x2F171114u, 607u}, /* life_thoughtful_e23_s3_listen_up_follow */
  {0x2F562130u, 404u}, /* life_delighted_e27_s0_soften_anticipate */
  {0x2F63D3A3u, 709u}, /* life_alert_e27_s1_notice_right_anticipate */
  {0x2F7AC9B8u, 1061u}, /* tap_edge_focused_thoughtful_right_orient */
  {0x2F96CB8Au, 903u}, /* menu_ui_en_s8_o2_ack_i3 */
  {0x2F96FB32u, 91u}, /* life_thoughtful_e27_s0_rest_hold */
  {0x2F99BA99u, 609u}, /* life_thoughtful_e24_s3_notice_right_follow */
  {0x2FC0EE9Bu, 292u}, /* life_curious_e3_s3_notice_left_follow */
  {0x2FF9C4F2u, 836u}, /* menu_ui_en_s0_o3_normal */
  {0x302615CFu, 999u}, /* tap_edge_warm_curious_up_orient */
  {0x302EEBE9u, 706u}, /* life_alert_e26_s0_rest_hold */
  {0x30340B41u, 984u}, /* tap_edge_curious_focused_center_follow */
  {0x3042FE03u, 518u}, /* life_warm_e18_s3_notice_right_follow */
  {0x30504465u, 958u}, /* tap_transition_down_e0_orient */
  {0x305461C3u, 827u}, /* menu_ui_en_s0_o1_ack_i1 */
  {0x3096CD1Du, 902u}, /* menu_ui_en_s8_o2_ack_i2 */
  {0x30A21313u, 432u}, /* life_delighted_e14_s1_beam_accent */
  {0x30B5A043u, 491u}, /* life_warm_e14_s2_notice_right_accent */
  {0x30F38B99u, 33u}, /* life_delighted_e0_s4_notice_left_settle */
  {0x3105A9EDu, 967u}, /* tap_edge_calm_warm_right_settle */
  {0x31292FF7u, 977u}, /* tap_edge_warm_playful_up_accent */
  {0x312ABDD4u, 973u}, /* tap_edge_alert_calm_down_follow */
  {0x312C3ED7u, 409u}, /* life_delighted_e10_s1_beam_accent */
  {0x31319BD2u, 28u}, /* expression_delighted_v2_0_hold */
  {0x31339EB3u, 951u}, /* tap_edge_focused_curious_left_settle */
  {0x31546356u, 828u}, /* menu_ui_en_s0_o1_ack_i2 */
  {0x316B1CE8u, 523u}, /* life_warm_e22_s0_rest_hold */
  {0x316E266Fu, 595u}, /* life_thoughtful_e17_s0_notice_left_orient */
  {0x31AC34FCu, 514u}, /* life_warm_e16_s2_soften_follow */
  {0x31D2DB3Cu, 784u}, /* menu_ui_zh_cn_s6_o0_normal */
  {0x31DFBCE9u, 314u}, /* life_curious_e9_s0_notice_right_orient */
  {0x32014252u, 155u}, /* life_calm_e10_s3_small_breath_settle */
  {0x320D14C4u, 47u}, /* life_warm_e17_s4_notice_left_settle */
  {0x3231634Du, 10u}, /* expression_calm_v0_2_orient */
  {0x324B749Eu, 949u}, /* tap_edge_calm_curious_up_accent */
  {0x325464E9u, 829u}, /* menu_ui_en_s0_o1_ack_i3 */
  {0x328D6BEFu, 269u}, /* life_calm_e30_s0_rest_hold */
  {0x328EB599u, 100u}, /* expression_focused_v2_2_hold */
  {0x32A79DE3u, 23u}, /* expression_curious_v0_1_follow */
  {0x32B22947u, 1064u}, /* tap_edge_focused_calm_center_anticipate */
  {0x32D9C4E2u, 18u}, /* expression_curious_v0_0_follow */
  {0x32F322D4u, 913u}, /* menu_ui_en_s10_o0_ack_i2 */
  {0x32F5352Bu, 70u}, /* expression_sleepy_v0_1_hold */
  {0x3304525Fu, 536u}, /* life_warm_e29_s0_rest_hold */
  {0x330BB7CFu, 165u}, /* life_calm_e12_s0_notice_left_orient */
  {0x330D0E9Eu, 331u}, /* life_curious_e14_s2_notice_right_accent */
  {0x3313FA1Au, 82u}, /* expression_bashful_v1_2_orient */
  {0x3327A3DDu, 454u}, /* life_delighted_e28_s0_rest_hold */
  {0x33351C9Au, 436u}, /* life_delighted_e16_s0_rest_hold */
  {0x333A44D5u, 967u}, /* tap_edge_calm_warm_down_settle */
  {0x33428B8Au, 618u}, /* life_thoughtful_e30_s0_rest_hold */
  {0x3354667Cu, 830u}, /* menu_ui_en_s0_o1_ack_i4 */
  {0x33667A4Du, 733u}, /* menu_ui_zh_cn_s0_o3_normal */
  {0x3367A605u, 1011u}, /* tap_edge_warm_bashful_down_settle */
  {0x336B4948u, 348u}, /* life_curious_e18_s1_notice_left_anticipate */
  {0x33A641B8u, 568u}, /* life_thoughtful_e6_s0_notice_right_orient */
  {0x33D27EB5u, 973u}, /* tap_edge_alert_calm_left_settle */
  {0x341352FDu, 967u}, /* tap_edge_sleepy_warm_center_settle */
  {0x3416FCD3u, 540u}, /* tap_edge_focused_thoughtful_up_settle */
  {0x34355CF0u, 488u}, /* life_warm_e11_s3_listen_up_follow */
  {0x34856BA9u, 1060u}, /* tap_edge_focused_alert_left_orient */
  {0x34956DEAu, 690u}, /* life_alert_e26_s3_notice_left_follow */
  {0x349BABB5u, 33u}, /* expression_delighted_v2_1_settle */
  {0x34D1E982u, 980u}, /* tap_edge_curious_thoughtful_down_anticipate */
  {0x34DFB545u, 964u}, /* tap_edge_calm_warm_left_anticipate */
  {0x34E086C4u, 136u}, /* upgrade_progress_0 */
  {0x34EFC73Au, 293u}, /* life_curious_e7_s0_rest_hold */
  {0x35471900u, 305u}, /* life_curious_e6_s3_notice_left_follow */
  {0x3549B6DFu, 147u}, /* life_calm_e0_s1_notice_right_anticipate */
  {0x358547E3u, 505u}, /* life_warm_e31_s1_soften_accent */
  {0x35986B2Eu, 21u}, /* expression_curious_v0_1_anticipate */
  {0x35B978F5u, 74u}, /* expression_bashful_v1_0_anticipate */
  {0x35BE9ACAu, 576u}, /* life_thoughtful_e9_s0_rest_hold */
  {0x35C30FCDu, 982u}, /* tap_edge_curious_focused_right_anticipate */
  {0x35E08857u, 143u}, /* upgrade_progress_1 */
  {0x363DC95Bu, 119u}, /* life_alert_e27_s4_notice_right_settle */
  {0x36687599u, 1068u}, /* tap_edge_alert_curious_down_orient */
  {0x366B1301u, 98u}, /* expression_thoughtful_v0_2_accent */
  {0x366F070Fu, 511u}, /* life_warm_e15_s1_listen_up_anticipate */
  {0x367EAD9Eu, 1044u}, /* tap_edge_thoughtful_curious_up_orient */
  {0x36979B2Cu, 978u}, /* tap_edge_delighted_playful_down_follow */
  {0x36BB53D8u, 1047u}, /* tap_edge_thoughtful_focused_right_orient */
  {0x36DACB2Du, 545u}, /* life_thoughtful_e0_s4_notice_left_settle */
  {0x36DB8D25u, 980u}, /* tap_edge_curious_thoughtful_left_anticipate */
  {0x36F04927u, 989u}, /* tap_edge_delighted_playful_center_orient */
  {0x373A1C26u, 118u}, /* expression_alert_v0_0_follow */
  {0x374AB934u, 746u}, /* menu_ui_zh_cn_s1_o0_ack_i3 */
  {0x374B5A56u, 284u}, /* life_curious_e11_s3_question_settle */
  {0x375A3A37u, 154u}, /* life_calm_e1_s2_small_breath_follow */
  {0x37634670u, 188u}, /* life_calm_e8_s3_notice_right_follow */
  {0x37760B1Cu, 981u}, /* tap_edge_curious_thoughtful_up_follow */
  {0x3782E751u, 387u}, /* life_delighted_e1_s1_notice_right_anticipate */
  {0x37924EE5u, 226u}, /* life_calm_e18_s2_notice_right_accent */
  {0x37AA4AA0u, 988u}, /* tap_edge_focused_alert_right_follow */
  {0x37B6F0EAu, 19u}, /* life_curious_e25_s4_notice_left_settle */
  {0x37B709A8u, 298u}, /* life_curious_e4_s4_listen_up_settle */
  {0x37D217ECu, 3u}, /* expression_calm_v0_0_accent */
  {0x37D95B67u, 390u}, /* life_delighted_e2_s0_beam_anticipate */
  {0x38000CD8u, 948u}, /* tap_edge_calm_curious_center_anticipate */
  {0x38184848u, 906u}, /* menu_ui_en_s9_o0_ack_i2 */
  {0x382AE800u, 1053u}, /* tap_edge_thoughtful_calm_down_orient */
  {0x3847C15Bu, 525u}, /* life_warm_e29_s3_notice_right_follow */
  {0x384ABAC7u, 745u}, /* menu_ui_zh_cn_s1_o0_ack_i2 */
  {0x384B8F23u, 914u}, /* menu_ui_en_s10_o0_processing_i3 */
  {0x38534EC6u, 988u}, /* tap_edge_thoughtful_alert_left_follow */
  {0x388F1520u, 655u}, /* life_alert_e30_s2_notice_right_accent */
  {0x38A1F2AAu, 640u}, /* life_alert_e21_s3_notice_right_follow */
  {0x38EF32A5u, 987u}, /* tap_edge_focused_alert_down_accent */
  {0x38F8B1E0u, 343u}, /* life_curious_e20_s1_notice_right_anticipate */
  {0x391474FEu, 474u}, /* life_warm_e3_s1_soften_accent */
  {0x3922E952u, 1055u}, /* tap_edge_thoughtful_calm_right_orient */
  {0x39248003u, 47u}, /* expression_warm_v0_0_settle */
  {0x393AF292u, 967u}, /* tap_edge_calm_warm_center_settle */
  {0x394ABC5Au, 744u}, /* menu_ui_zh_cn_s1_o0_ack_i1 */
  {0x39564872u, 973u}, /* tap_edge_delighted_calm_right_settle */
  {0x395B786Du, 683u}, /* life_alert_e16_s1_startle_accent */
  {0x399DDA04u, 981u}, /* tap_edge_focused_thoughtful_right_follow */
  {0x39E0C2F7u, 688u}, /* life_alert_e19_s1_notice_left_anticipate */
  {0x39E714DFu, 963u}, /* tap_edge_curious_thoughtful_right_orient */
  {0x3A2CC2B5u, 310u}, /* life_curious_e11_s0_question_orient */
  {0x3A424485u, 297u}, /* life_curious_e31_s3_listen_up_follow */
  {0x3A484346u, 556u}, /* life_thoughtful_e2_s4_notice_right_settle */
  {0x3A99D46Eu, 373u}, /* life_curious_e29_s0_rest_hold */
  {0x3AB5D77Fu, 652u}, /* life_alert_e6_s3_listen_up_follow */
  {0x3AC0CD95u, 597u}, /* life_thoughtful_e30_s1_notice_right_anticipate */
  {0x3ADBB5D0u, 977u}, /* tap_edge_warm_playful_right_accent */
  {0x3ADE7703u, 464u}, /* life_warm_e1_s0_notice_left_orient */
  {0x3AE526F9u, 381u}, /* life_delighted_e20_s0_notice_left_orient */
  {0x3B1ED67Au, 980u}, /* tap_edge_curious_thoughtful_right_anticipate */
  {0x3B7200B4u, 533u}, /* life_warm_e26_s2_notice_right_accent */
  {0x3B91FAE7u, 1066u}, /* tap_edge_alert_focused_down_anticipate */
  {0x3B9C6683u, 47u}, /* life_warm_e26_s4_notice_right_settle */
  {0x3B9EE4EBu, 954u}, /* tap_edge_curious_thoughtful_up_accent */
  {0x3BDB8606u, 950u}, /* tap_edge_alert_curious_center_follow */
  {0x3BE40B8Eu, 273u}, /* life_calm_e31_s1_small_breath_accent */
  {0x3C26E468u, 47u}, /* life_warm_e29_s4_notice_right_settle */
  {0x3C4D8D66u, 639u}, /* life_alert_e3_s2_notice_right_accent */
  {0x3C91169Cu, 1020u}, /* tap_edge_playful_warm_up_orient */
  {0x3C93D7B6u, 412u}, /* life_delighted_e7_s1_notice_left_anticipate */
  {0x3C9D7D46u, 48u}, /* tap_local_warm_center */
  {0x3CE64489u, 1026u}, /* tap_edge_sleepy_calm_center_orient */
  {0x3CE7A499u, 124u}, /* tap_local_alert_center */
  {0x3D0F8FF5u, 641u}, /* life_alert_e4_s1_notice_left_anticipate */
  {0x3D14CEE4u, 931u}, /* tap_local_playful_up */
  {0x3D2F6825u, 415u}, /* life_delighted_e8_s0_soften_anticipate */
  {0x3D63D623u, 119u}, /* life_alert_e28_s3_startle_settle */
  {0x3D9F005Bu, 414u}, /* life_delighted_e8_s0_rest_hold */
  {0x3DB11B23u, 198u}, /* life_calm_e12_s1_notice_left_anticipate */
  {0x3DE01B44u, 42u}, /* life_warm_e31_s0_rest_hold */
  {0x3DF54D45u, 539u}, /* life_warm_e30_s0_notice_left_orient */
  {0x3DFD51AAu, 201u}, /* life_calm_e25_s4_notice_right_settle */
  {0x3E0F2396u, 6u}, /* expression_calm_v0_1_orient */
  {0x3E10596Au, 549u}, /* life_thoughtful_e5_s2_listen_up_accent */
  {0x3E78F352u, 990u}, /* tap_edge_delighted_warm_left_anticipate */
  {0x3E791BE7u, 987u}, /* tap_edge_focused_alert_right_accent */
  {0x3EB0D67Du, 286u}, /* life_curious_e27_s0_listen_up_orient */
  {0x3EB9940Fu, 972u}, /* tap_edge_delighted_calm_right_accent */
  {0x3ED8542Fu, 312u}, /* life_curious_e8_s2_listen_up_accent */
  {0x3EDA5DCCu, 81u}, /* expression_bashful_v0_1_follow */
  {0x3EDA7224u, 175u}, /* life_calm_e5_s4_listen_up_settle */
  {0x3EE145D0u, 306u}, /* life_curious_e7_s0_question_orient */
  {0x3EEAC020u, 949u}, /* tap_edge_warm_curious_center_accent */
  {0x3F26DEA1u, 542u}, /* life_thoughtful_e19_s1_notice_left_anticipate */
  {0x3F2EED99u, 967u}, /* tap_edge_sleepy_warm_up_settle */
  {0x3F358C7Cu, 318u}, /* life_curious_e13_s2_notice_left_accent */
  {0x3F35AF85u, 1048u}, /* tap_edge_thoughtful_focused_right_anticipate */
  {0x3F36F479u, 433u}, /* life_delighted_e14_s2_beam_follow */
  {0x3F3D14F4u, 883u}, /* menu_ui_en_s4_o0_ack_i3 */
  {0x3F66CD23u, 990u}, /* tap_edge_delighted_warm_right_anticipate */
  {0x3F7E74E6u, 1019u}, /* tap_edge_playful_warm_right_anticipate */
  {0x3F84AE4Au, 662u}, /* life_alert_e10_s0_rest_hold */
  {0x3FC0022Fu, 960u}, /* tap_edge_calm_sleepy_left_orient */
  {0x3FD3FFD2u, 12u}, /* expression_calm_v0_2_accent */
  {0x3FEAAF83u, 381u}, /* tap_local_delighted_left */
  {0x3FF529E4u, 973u}, /* tap_edge_curious_calm_down_follow */
  {0x400861A5u, 950u}, /* tap_edge_thoughtful_curious_right_follow */
  {0x4013B469u, 952u}, /* tap_transition_center_e1_orient */
  {0x403D1687u, 882u}, /* menu_ui_en_s4_o0_ack_i2 */
  {0x403DF8AAu, 102u}, /* expression_focused_v2_0_anticipate */
  {0x404FCF74u, 142u}, /* menu_progress_1 */
  {0x408FAC35u, 1006u}, /* tap_edge_warm_delighted_up_follow */
  {0x409F28B0u, 452u}, /* life_delighted_e29_s3_notice_right_follow */
  {0x40AB7810u, 559u}, /* life_thoughtful_e3_s1_ponder_anticipate */
  {0x40AEF331u, 280u}, /* life_curious_e1_s0_notice_right_orient */
  {0x40C7C465u, 57u}, /* expression_playful_v0_0_orient */
  {0x40D73CB7u, 973u}, /* tap_edge_warm_calm_right_follow */
  {0x4101BD3Fu, 468u}, /* tap_local_warm_down */
  {0x41122FBFu, 989u}, /* tap_edge_delighted_warm_center_orient */
  {0x413D181Au, 881u}, /* menu_ui_en_s4_o0_ack_i1 */
  {0x414FD107u, 135u}, /* menu_progress_0 */
  {0x4153736Cu, 477u}, /* life_warm_e10_s1_notice_right_anticipate */
  {0x41A3473Eu, 950u}, /* tap_edge_thoughtful_curious_up_follow */
  {0x41A7786Au, 1051u}, /* tap_edge_thoughtful_calm_left_anticipate */
  {0x41E150ADu, 449u}, /* tap_edge_playful_delighted_left_settle */
  {0x41EA0FE5u, 110u}, /* expression_focused_v2_2_orient */
  {0x41F6B292u, 967u}, /* tap_edge_playful_warm_left_settle */
  {0x42367213u, 862u}, /* menu_ui_en_s2_o0_normal */
  {0x423D19ADu, 880u}, /* menu_ui_en_s4_o0_ack_i0 */
  {0x4243B9E0u, 1027u}, /* tap_edge_sleepy_calm_left_anticipate */
  {0x426246C8u, 112u}, /* expression_focused_v0_2_accent */
  {0x428A0DA0u, 560u}, /* life_thoughtful_e26_s2_ponder_accent */
  {0x42EE0953u, 1009u}, /* tap_edge_warm_bashful_left_accent */
  {0x4312AFFDu, 47u}, /* life_warm_e15_s4_listen_up_settle */
  {0x43372EFFu, 116u}, /* expression_alert_v0_0_anticipate */
  {0x4359F436u, 210u}, /* life_calm_e15_s0_soften_anticipate */
  {0x4365F47Au, 923u}, /* menu_ui_en_s12_o0_ack_i2 */
  {0x436D4507u, 966u}, /* tap_edge_calm_warm_down_follow */
  {0x43861C0Du, 950u}, /* tap_edge_calm_curious_left_follow */
  {0x43900055u, 962u}, /* tap_transition_right_e0_orient */
  {0x4397F89Fu, 966u}, /* tap_edge_sleepy_warm_center_follow */
  {0x439FA07Cu, 138u}, /* menu_mode_1 */
  {0x43AC1F79u, 981u}, /* tap_edge_focused_thoughtful_up_follow */
  {0x43C78677u, 973u}, /* tap_edge_thoughtful_calm_center_follow */
  {0x43D33806u, 711u}, /* life_alert_e28_s0_startle_orient */
  {0x43E679E2u, 19u}, /* life_curious_e24_s3_question_settle */
  {0x43E84F4Du, 963u}, /* tap_edge_curious_alert_right_orient */
  {0x43EA3DCCu, 1048u}, /* tap_edge_thoughtful_focused_center_anticipate */
  {0x43EB0514u, 965u}, /* tap_edge_calm_warm_right_accent */
  {0x43F82216u, 549u}, /* life_thoughtful_e9_s2_listen_up_accent */
  {0x4440C560u, 974u}, /* tap_edge_curious_thoughtful_up_orient */
  {0x4442D4F8u, 70u}, /* expression_sleepy_v0_2_follow */
  {0x4448744Eu, 389u}, /* life_delighted_e1_s3_notice_right_follow */
  {0x4498EED9u, 461u}, /* life_warm_e19_s1_soften_accent */
  {0x449C7E3Fu, 950u}, /* tap_edge_warm_curious_up_follow */
  {0x449FA20Fu, 135u}, /* menu_mode_0 */
  {0x44D4AC9Cu, 951u}, /* tap_edge_thoughtful_curious_center_settle */
  {0x44D4AF61u, 991u}, /* tap_edge_delighted_calm_up_orient */
  {0x44E64524u, 966u}, /* tap_edge_delighted_warm_down_follow */
  {0x4561CE02u, 38u}, /* expression_delighted_v0_2_orient */
  {0x4565ED2Du, 961u}, /* tap_edge_curious_focused_left_orient */
  {0x45812CA1u, 979u}, /* tap_edge_delighted_playful_up_settle */
  {0x45F79D56u, 160u}, /* life_calm_e2_s3_soften_settle */
  {0x45FC3328u, 28u}, /* expression_delighted_v2_2_hold */
  {0x460CFA78u, 961u}, /* tap_edge_curious_thoughtful_left_orient */
  {0x465D0E59u, 344u}, /* life_curious_e17_s2_notice_right_accent */
  {0x4678D37Du, 987u}, /* tap_edge_thoughtful_alert_center_accent */
  {0x468A4E88u, 114u}, /* tap_edge_thoughtful_alert_center_settle */
  {0x4699D683u, 974u}, /* tap_edge_curious_calm_up_orient */
  {0x469D9F1Bu, 16u}, /* expression_curious_v0_0_anticipate */
  {0x469FA535u, 142u}, /* menu_mode_2 */
  {0x46A07D47u, 1006u}, /* tap_edge_playful_delighted_center_follow */
  {0x46A552C1u, 988u}, /* tap_edge_thoughtful_alert_right_follow */
  {0x46C728D3u, 382u}, /* life_delighted_e0_s1_notice_left_anticipate */
  {0x46DA9C37u, 977u}, /* tap_edge_warm_playful_left_accent */
  {0x46DF444Au, 623u}, /* life_alert_e0_s1_startle_accent */
  {0x46E8E1B9u, 950u}, /* tap_edge_playful_curious_up_follow */
  {0x46FA4997u, 438u}, /* life_delighted_e22_s2_notice_right_accent */
  {0x47087E44u, 552u}, /* life_thoughtful_e2_s0_notice_right_orient */
  {0x4718BDC6u, 75u}, /* expression_bashful_v0_0_accent */
  {0x472C2DFDu, 70u}, /* tap_edge_calm_sleepy_left_settle */
  {0x47493178u, 937u}, /* tap_local_bashful_up */
  {0x475BF0C1u, 165u}, /* life_calm_e9_s0_notice_left_orient */
  {0x477DFFEDu, 399u}, /* life_delighted_e29_s0_notice_right_orient */
  {0x477EBEECu, 950u}, /* tap_transition_center_e0_follow */
  {0x47C1877Fu, 691u}, /* life_alert_e20_s0_rest_hold */
  {0x47D73159u, 979u}, /* tap_edge_warm_playful_down_settle */
  {0x4801D37Du, 569u}, /* life_thoughtful_e6_s2_notice_right_accent */
  {0x48081055u, 473u}, /* life_warm_e3_s0_rest_hold */
  {0x480AE7BBu, 327u}, /* life_curious_e12_s4_listen_up_settle */
  {0x48149A3Du, 818u}, /* menu_ui_zh_cn_s12_o0_normal */
  {0x4855672Bu, 110u}, /* expression_focused_v0_2_orient */
  {0x485A1837u, 222u}, /* life_calm_e17_s3_notice_left_follow */
  {0x4884FE65u, 315u}, /* life_curious_e14_s1_notice_right_anticipate */
  {0x4889AF56u, 397u}, /* life_delighted_e15_s3_notice_left_follow */
  {0x488DE392u, 464u}, /* life_warm_e17_s0_notice_left_orient */
  {0x48A38AD7u, 951u}, /* tap_edge_thoughtful_curious_right_settle */
  {0x48F9EB21u, 984u}, /* tap_edge_curious_focused_up_follow */
  {0x49027ED6u, 1013u}, /* tap_edge_playful_delighted_up_anticipate */
  {0x490559D3u, 548u}, /* life_thoughtful_e9_s1_listen_up_anticipate */
  {0x491EB51Cu, 535u}, /* life_warm_e28_s0_soften_anticipate */
  {0x495A95A2u, 501u}, /* life_warm_e11_s0_rest_hold */
  {0x495C1BB7u, 633u}, /* life_alert_e2_s1_notice_left_anticipate */
  {0x4962F094u, 966u}, /* tap_edge_bashful_warm_up_follow */
  {0x4965257Eu, 384u}, /* life_delighted_e20_s3_notice_left_follow */
  {0x499CDC77u, 965u}, /* tap_edge_curious_warm_right_accent */
  {0x49BA257Fu, 952u}, /* tap_edge_curious_calm_center_orient */
  {0x49D35139u, 568u}, /* life_thoughtful_e14_s0_notice_right_orient */
  {0x49FF8FDEu, 146u}, /* life_calm_e3_s0_notice_right_orient */
  {0x4A0337CCu, 44u}, /* expression_warm_v0_0_anticipate */
  {0x4A062BD3u, 380u}, /* life_delighted_e0_s0_rest_hold */
  {0x4A270CD2u, 998u}, /* tap_edge_warm_calm_right_anticipate */
  {0x4A3FD6E0u, 976u}, /* tap_edge_curious_playful_left_anticipate */
  {0x4A4EE76Du, 968u}, /* tap_edge_calm_sleepy_down_anticipate */
  {0x4A5AFB7Eu, 293u}, /* life_curious_e3_s4_notice_left_settle */
  {0x4A9BBD2Bu, 985u}, /* tap_edge_thoughtful_focused_left_settle */
  {0x4AC47310u, 977u}, /* tap_edge_warm_playful_down_accent */
  {0x4ACE8891u, 525u}, /* life_warm_e23_s3_notice_right_follow */
  {0x4AD0B267u, 499u}, /* life_warm_e10_s2_notice_right_accent */
  {0x4AD2B98Bu, 565u}, /* life_thoughtful_e5_s0_listen_up_orient */
  {0x4ADBA681u, 1070u}, /* tap_edge_alert_curious_right_orient */
  {0x4B03252Cu, 965u}, /* tap_edge_delighted_warm_left_accent */
  {0x4B36EC8Cu, 682u}, /* life_alert_e16_s0_rest_hold */
  {0x4B719C8Du, 1019u}, /* tap_edge_playful_warm_center_anticipate */
  {0x4B823567u, 485u}, /* life_warm_e11_s0_listen_up_orient */
  {0x4B8CD519u, 270u}, /* life_calm_e30_s0_soften_anticipate */
  {0x4B9F7386u, 754u}, /* menu_ui_zh_cn_s1_o2_ack_i3 */
  {0x4BA24C52u, 180u}, /* life_calm_e6_s3_soften_settle */
  {0x4BA547CEu, 260u}, /* life_calm_e27_s0_small_breath_anticipate */
  {0x4BB13B95u, 950u}, /* tap_edge_bashful_curious_left_follow */
  {0x4BC6A0C7u, 114u}, /* tap_edge_focused_alert_up_settle */
  {0x4BDA3592u, 954u}, /* tap_edge_focused_thoughtful_up_accent */
  {0x4BED25B6u, 244u}, /* life_calm_e22_s2_notice_right_accent */
  {0x4C085CA4u, 957u}, /* tap_transition_up_e0_orient */
  {0x4C393594u, 660u}, /* life_alert_e27_s0_rest_hold */
  {0x4C3F2CA6u, 1018u}, /* tap_edge_playful_calm_center_orient */
  {0x4C5D38DEu, 289u}, /* life_curious_e3_s0_rest_hold */
  {0x4C5F1C68u, 19u}, /* expression_curious_v0_0_settle */
  {0x4C8C8906u, 1028u}, /* tap_edge_sleepy_calm_center_accent */
  {0x4C98D4FFu, 393u}, /* life_delighted_e29_s4_notice_right_settle */
  {0x4C9F7519u, 753u}, /* menu_ui_zh_cn_s1_o2_ack_i2 */
  {0x4D677C14u, 416u}, /* life_delighted_e13_s1_soften_accent */
  {0x4D9EE8E4u, 760u}, /* menu_ui_zh_cn_s2_o0_ack_i0 */
  {0x4DA5FCB5u, 540u}, /* tap_edge_curious_thoughtful_down_settle */
  {0x4E471FE2u, 556u}, /* life_thoughtful_e31_s3_ponder_settle */
  {0x4E545629u, 1019u}, /* tap_edge_playful_warm_up_anticipate */
  {0x4E74FBC2u, 114u}, /* expression_alert_v0_0_hold */
  {0x4E9F783Fu, 755u}, /* menu_ui_zh_cn_s1_o2_ack_i4 */
  {0x4EBC2824u, 1030u}, /* tap_edge_sleepy_warm_center_accent */
  {0x4EC2810Du, 977u}, /* tap_edge_delighted_playful_right_accent */
  {0x4EC80A5Du, 17u}, /* expression_curious_v0_0_accent */
  {0x4EC91FBCu, 452u}, /* life_delighted_e25_s3_notice_right_follow */
  {0x4EEF35FCu, 1026u}, /* tap_edge_sleepy_calm_right_orient */
  {0x4F1D1462u, 1017u}, /* tap_edge_playful_delighted_right_orient */
  {0x4F36D5A2u, 572u}, /* life_thoughtful_e7_s1_notice_left_anticipate */
  {0x4F51D223u, 978u}, /* tap_edge_warm_playful_down_follow */
  {0x4F578E4Bu, 1023u}, /* tap_edge_playful_warm_right_orient */
  {0x4F57AF1Du, 967u}, /* tap_edge_bashful_warm_down_settle */
  {0x4F6C790Eu, 1042u}, /* tap_edge_thoughtful_curious_center_orient */
  {0x4FB051B7u, 1043u}, /* tap_edge_thoughtful_curious_center_anticipate */
  {0x4FBD7F47u, 439u}, /* life_delighted_e17_s0_rest_hold */
  {0x4FC0ADC4u, 949u}, /* tap_edge_warm_curious_up_accent */
  {0x4FEFA8F9u, 295u}, /* life_curious_e12_s1_listen_up_anticipate */
  {0x4FF6D094u, 153u}, /* life_calm_e20_s1_small_breath_accent */
  {0x50077476u, 47u}, /* life_warm_e28_s3_soften_settle */
  {0x50166F8Fu, 560u}, /* life_thoughtful_e3_s2_ponder_accent */
  {0x502724CEu, 70u}, /* expression_sleepy_v0_0_follow */
  {0x50694536u, 254u}, /* life_calm_e26_s0_rest_hold */
  {0x506B1009u, 217u}, /* life_calm_e16_s2_small_breath_follow */
  {0x50863462u, 950u}, /* tap_edge_calm_curious_down_follow */
  {0x50BD9B49u, 73u}, /* expression_bashful_v0_0_orient */
  {0x50BE2589u, 976u}, /* tap_edge_curious_playful_right_anticipate */
  {0x50CEDADAu, 329u}, /* life_curious_e14_s0_rest_hold */
  {0x50E5C416u, 967u}, /* tap_edge_delighted_warm_down_settle */
  {0x5112407Fu, 630u}, /* life_alert_e1_s4_listen_up_settle */
  {0x51210974u, 473u}, /* life_warm_e6_s0_rest_hold */
  {0x512464C7u, 300u}, /* life_curious_e5_s1_notice_right_anticipate */
  {0x512CD38Du, 420u}, /* life_delighted_e19_s2_notice_right_accent */
  {0x514DCA8Fu, 386u}, /* life_delighted_e16_s0_notice_right_orient */
  {0x51847B1Au, 1006u}, /* tap_edge_warm_delighted_down_follow */
  {0x518755BFu, 1028u}, /* tap_edge_sleepy_calm_right_accent */
  {0x518AEBD2u, 987u}, /* tap_edge_curious_alert_right_accent */
  {0x519AB6F6u, 493u}, /* life_warm_e13_s0_soften_anticipate */
  {0x51AEA4F6u, 640u}, /* life_alert_e14_s3_notice_right_follow */
  {0x51B911CEu, 973u}, /* tap_edge_warm_calm_left_settle */
  {0x51B92217u, 47u}, /* life_warm_e30_s4_notice_left_settle */
  {0x51D4ACC6u, 403u}, /* life_delighted_e30_s0_rest_hold */
  {0x51D5AB42u, 1026u}, /* tap_edge_sleepy_calm_down_orient */
  {0x51EA0CA8u, 35u}, /* expression_delighted_v0_1_anticipate */
  {0x52089DF0u, 302u}, /* life_curious_e5_s3_notice_right_follow */
  {0x5266AA32u, 41u}, /* expression_delighted_v0_2_follow */
  {0x527CBA7Eu, 504u}, /* life_warm_e21_s2_notice_left_accent */
  {0x52B3CD89u, 774u}, /* menu_ui_zh_cn_s3_o3_ack_i3 */
  {0x52C13D88u, 33u}, /* life_delighted_e7_s4_notice_left_settle */
  {0x52C97B2Cu, 973u}, /* tap_edge_focused_calm_center_settle */
  {0x52D813B7u, 546u}, /* life_thoughtful_e8_s0_rest_hold */
  {0x52F9745Au, 233u}, /* life_calm_e19_s3_listen_up_follow */
  {0x530889B2u, 983u}, /* tap_edge_curious_focused_left_accent */
  {0x531DFB12u, 91u}, /* expression_thoughtful_v0_0_settle */
  {0x5342E8B0u, 950u}, /* tap_transition_left_e0_follow */
  {0x5343D514u, 124u}, /* expression_alert_v0_2_orient */
  {0x5345362Du, 470u}, /* life_warm_e2_s1_listen_up_anticipate */
  {0x539D25E7u, 211u}, /* life_calm_e15_s1_soften_accent */
  {0x53B1E02Fu, 321u}, /* life_curious_e11_s1_question_anticipate */
  {0x53D05A0Du, 973u}, /* tap_edge_focused_calm_down_follow */
  {0x53EFA8A7u, 547u}, /* life_thoughtful_e1_s0_listen_up_orient */
  {0x53F80E0Du, 972u}, /* tap_edge_focused_calm_left_accent */
  {0x53F94168u, 1038u}, /* tap_edge_bashful_curious_left_anticipate */
  {0x542469DDu, 1042u}, /* tap_edge_thoughtful_focused_center_orient */
  {0x54379259u, 972u}, /* tap_edge_playful_calm_center_accent */
  {0x54443CB4u, 425u}, /* life_delighted_e18_s0_rest_hold */
  {0x544CDE01u, 950u}, /* tap_transition_down_e0_follow */
  {0x544FD813u, 5u}, /* expression_calm_v0_2_settle */
  {0x5451F58Au, 286u}, /* life_curious_e31_s0_listen_up_orient */
  {0x5483EAEEu, 431u}, /* life_delighted_e14_s0_beam_anticipate */
  {0x548A7FFBu, 966u}, /* tap_edge_playful_warm_down_follow */
  {0x54ABDE20u, 204u}, /* life_calm_e14_s4_listen_up_settle */
  {0x54B4468Eu, 19u}, /* life_curious_e29_s4_notice_left_settle */
  {0x54C4C0FAu, 119u}, /* life_alert_e16_s3_startle_settle */
  {0x54E60EC6u, 1011u}, /* tap_edge_warm_bashful_left_settle */
  {0x551078ABu, 986u}, /* tap_edge_curious_alert_up_anticipate */
  {0x5510DAECu, 122u}, /* expression_alert_v0_1_accent */
  {0x551CA4F8u, 973u}, /* tap_edge_delighted_calm_right_follow */
  {0x5593195Eu, 438u}, /* life_delighted_e16_s2_notice_right_accent */
  {0x55992EFFu, 508u}, /* life_warm_e14_s3_notice_right_follow */
  {0x55B89806u, 984u}, /* tap_edge_thoughtful_focused_down_follow */
  {0x55D0E465u, 972u}, /* tap_edge_curious_calm_right_accent */
  {0x55D3B18Eu, 472u}, /* life_warm_e2_s3_listen_up_follow */
  {0x55FB69B4u, 325u}, /* life_curious_e12_s2_listen_up_accent */
  {0x56A09244u, 512u}, /* life_warm_e15_s3_listen_up_follow */
  {0x56A6A587u, 14u}, /* expression_curious_v0_1_hold */
  {0x56A9C6E9u, 297u}, /* life_curious_e4_s3_listen_up_follow */
  {0x56B0D39Fu, 970u}, /* tap_edge_calm_sleepy_left_follow */
  {0x56C3E42Au, 543u}, /* life_thoughtful_e17_s2_notice_left_accent */
  {0x56CED219u, 984u}, /* tap_edge_thoughtful_focused_up_follow */
  {0x56DAF799u, 989u}, /* tap_edge_delighted_calm_center_orient */
  {0x56DB9320u, 271u}, /* life_calm_e30_s1_soften_accent */
  {0x56DEE5A3u, 983u}, /* tap_edge_thoughtful_focused_right_accent */
  {0x56EEA1B2u, 634u}, /* life_alert_e15_s2_notice_left_accent */
  {0x570F4722u, 1011u}, /* tap_edge_warm_bashful_center_settle */
  {0x575E8345u, 313u}, /* life_curious_e8_s3_listen_up_follow */
  {0x579DEFDFu, 951u}, /* tap_edge_calm_curious_up_settle */
  {0x582CB2EBu, 1040u}, /* tap_edge_bashful_calm_up_anticipate */
  {0x583454DFu, 1071u}, /* tap_edge_alert_curious_center_anticipate */
  {0x58455347u, 114u}, /* tap_edge_focused_alert_left_settle */
  {0x58485C56u, 206u}, /* life_calm_e14_s0_listen_up_orient */
  {0x585B5B10u, 728u}, /* menu_ui_zh_cn_s0_o2_normal */
  {0x586F9720u, 950u}, /* tap_edge_bashful_curious_right_follow */
  {0x588F207Eu, 496u}, /* life_warm_e9_s2_notice_left_accent */
  {0x58948AD6u, 967u}, /* tap_edge_calm_warm_left_settle */
  {0x58994BABu, 678u}, /* life_alert_e15_s0_rest_hold */
  {0x58BA530Fu, 19u}, /* life_curious_e13_s4_notice_left_settle */
  {0x58C65E58u, 560u}, /* life_thoughtful_e8_s2_ponder_accent */
  {0x58C86180u, 967u}, /* tap_edge_sleepy_warm_right_settle */
  {0x58F1D2B1u, 1056u}, /* tap_edge_focused_alert_center_orient */
  {0x59121F9Bu, 585u}, /* life_thoughtful_e12_s1_listen_up_anticipate */
  {0x591B4E8Cu, 420u}, /* life_delighted_e25_s2_notice_right_accent */
  {0x5929633Du, 629u}, /* life_alert_e17_s3_listen_up_follow */
  {0x594E45F4u, 896u}, /* menu_ui_en_s8_o1_normal */
  {0x5958261Cu, 1062u}, /* tap_edge_focused_thoughtful_up_anticipate */
  {0x59697094u, 973u}, /* tap_edge_playful_calm_up_settle */
  {0x5990270Du, 47u}, /* life_warm_e4_s4_notice_right_settle */
  {0x59BB1A86u, 19u}, /* life_curious_e26_s4_notice_right_settle */
  {0x59BB9F6Bu, 951u}, /* tap_edge_focused_curious_up_settle */
  {0x5A176460u, 628u}, /* life_alert_e1_s2_listen_up_accent */
  {0x5A1F4E15u, 973u}, /* tap_edge_playful_calm_down_follow */
  {0x5A333507u, 19u}, /* life_curious_e16_s4_listen_up_settle */
  {0x5A39485Du, 802u}, /* menu_ui_zh_cn_s9_o0_normal */
  {0x5A56FD68u, 1063u}, /* tap_edge_focused_alert_up_anticipate */
  {0x5A60F134u, 1049u}, /* tap_edge_thoughtful_alert_right_anticipate */
  {0x5A68B8A9u, 419u}, /* life_delighted_e25_s0_notice_right_orient */
  {0x5AA64469u, 34u}, /* expression_delighted_v0_1_orient */
  {0x5AAC2EC8u, 299u}, /* life_curious_e5_s0_rest_hold */
  {0x5ADDF9EDu, 104u}, /* expression_focused_v0_0_follow */
  {0x5AFECD15u, 950u}, /* tap_edge_bashful_curious_up_follow */
  {0x5B096852u, 648u}, /* life_alert_e5_s3_startle_settle */
  {0x5B253C31u, 632u}, /* life_alert_e8_s0_notice_left_orient */
  {0x5B2D0BF8u, 659u}, /* life_alert_e8_s2_notice_left_accent */
  {0x5B2F8C3Bu, 486u}, /* life_warm_e11_s1_listen_up_anticipate */
  {0x5B30CDE7u, 77u}, /* expression_bashful_v0_0_settle */
  {0x5B3E8BA5u, 950u}, /* tap_edge_alert_curious_down_follow */
  {0x5B4AF679u, 948u}, /* tap_edge_calm_curious_right_anticipate */
  {0x5B4DE696u, 115u}, /* expression_alert_v0_0_orient */
  {0x5B5C98CAu, 401u}, /* life_delighted_e12_s2_notice_right_accent */
  {0x5B745F71u, 590u}, /* life_thoughtful_e24_s2_notice_right_accent */
  {0x5BB2F684u, 1009u}, /* tap_edge_warm_bashful_right_accent */
  {0x5BF54EBFu, 600u}, /* life_thoughtful_e20_s0_ponder_orient */
  {0x5C0F3BFFu, 7u}, /* expression_calm_v0_1_anticipate */
  {0x5C4279B7u, 352u}, /* life_curious_e19_s1_question_anticipate */
  {0x5C5141E2u, 546u}, /* life_thoughtful_e1_s0_rest_hold */
  {0x5C8E1B2Fu, 30u}, /* expression_delighted_v2_0_anticipate */
  {0x5C9E2737u, 665u}, /* life_alert_e11_s0_rest_hold */
  {0x5CBF1CC8u, 997u}, /* tap_edge_warm_playful_center_orient */
  {0x5CC25319u, 33u}, /* life_delighted_e6_s3_beam_settle */
  {0x5CD3B8D0u, 22u}, /* expression_curious_v0_1_accent */
  {0x5CF03AF9u, 119u}, /* life_alert_e21_s4_notice_right_settle */
  {0x5CF222ABu, 1027u}, /* tap_edge_sleepy_calm_down_anticipate */
  {0x5CFB0351u, 997u}, /* tap_edge_warm_delighted_center_orient */
  {0x5D14246Eu, 959u}, /* tap_edge_curious_focused_down_orient */
  {0x5D1B9EACu, 928u}, /* tap_local_curious_down */
  {0x5D28FCC4u, 540u}, /* tap_edge_focused_thoughtful_down_settle */
  {0x5D404F05u, 70u}, /* tap_edge_calm_sleepy_center_settle */
  {0x5D7701A8u, 978u}, /* tap_edge_curious_playful_right_follow */
  {0x5D9C0B90u, 951u}, /* tap_edge_bashful_curious_down_settle */
  {0x5DC53106u, 402u}, /* life_delighted_e12_s3_notice_right_follow */
  {0x5E034344u, 950u}, /* tap_edge_playful_curious_right_follow */
  {0x5E1B9BEDu, 979u}, /* tap_edge_delighted_playful_left_settle */
  {0x5E26E8F5u, 694u}, /* life_alert_e22_s0_rest_hold */
  {0x5E40363Cu, 332u}, /* life_curious_e30_s3_notice_right_follow */
  {0x5E589CE4u, 19u}, /* life_curious_e31_s4_listen_up_settle */
  {0x5E667CCFu, 33u}, /* life_delighted_e11_s4_notice_left_settle */
  {0x5E7F226Eu, 671u}, /* life_alert_e13_s0_listen_up_orient */
  {0x5E8881CDu, 973u}, /* tap_edge_sleepy_calm_up_follow */
  {0x5EC1F8DBu, 1014u}, /* tap_edge_playful_delighted_up_orient */
  {0x5EDD6199u, 503u}, /* life_warm_e12_s1_notice_left_anticipate */
  {0x5EEA0DF6u, 540u}, /* tap_edge_focused_thoughtful_right_settle */
  {0x5F0338CBu, 573u}, /* life_thoughtful_e7_s2_notice_left_accent */
  {0x5F1422ADu, 186u}, /* life_calm_e8_s0_notice_right_orient */
  {0x5F31124Eu, 949u}, /* tap_edge_calm_curious_left_accent */
  {0x5F3D3083u, 806u}, /* menu_ui_zh_cn_s9_o2_normal */
  {0x5F3E6867u, 1039u}, /* tap_edge_bashful_curious_right_accent */
  {0x5F40F431u, 477u}, /* life_warm_e4_s1_notice_right_anticipate */
  {0x5F64E0B0u, 978u}, /* tap_edge_warm_playful_up_follow */
  {0x5F8CBEAFu, 820u}, /* menu_ui_zh_cn_s12_o0_ack_i2 */
  {0x5F96C198u, 959u}, /* tap_edge_curious_calm_down_orient */
  {0x5FA62023u, 498u}, /* life_warm_e14_s0_rest_hold */
  {0x5FA79DDDu, 966u}, /* tap_edge_curious_warm_center_follow */
  {0x5FAD634Eu, 1011u}, /* tap_edge_warm_bashful_up_settle */
  {0x5FC5DAA3u, 284u}, /* life_curious_e1_s4_notice_right_settle */
  {0x5FC8A689u, 91u}, /* life_thoughtful_e17_s4_notice_left_settle */
  {0x5FEB1FEAu, 114u}, /* tap_edge_focused_alert_right_settle */
  {0x6000ADF1u, 988u}, /* tap_edge_thoughtful_alert_down_follow */
  {0x600E5723u, 350u}, /* life_curious_e18_s3_notice_left_follow */
  {0x604A3CD3u, 75u}, /* expression_bashful_v1_0_accent */
  {0x604FA0FAu, 988u}, /* tap_edge_focused_alert_down_follow */
  {0x6071013Au, 257u}, /* life_calm_e26_s2_listen_up_accent */
  {0x609581EBu, 532u}, /* life_warm_e26_s1_notice_right_anticipate */
  {0x60A33995u, 918u}, /* menu_ui_en_s11_o0_normal */
  {0x60A49927u, 973u}, /* tap_edge_sleepy_calm_center_settle */
  {0x60B71240u, 973u}, /* tap_edge_warm_calm_center_follow */
  {0x60BF512Cu, 984u}, /* tap_edge_alert_focused_right_follow */
  {0x60E56C36u, 28u}, /* expression_delighted_v0_2_hold */
  {0x60F4BD62u, 684u}, /* life_alert_e17_s1_listen_up_anticipate */
  {0x616EA9DCu, 966u}, /* tap_edge_playful_warm_center_follow */
  {0x61BBABE6u, 389u}, /* life_delighted_e9_s3_notice_right_follow */
  {0x61D50324u, 969u}, /* tap_edge_calm_sleepy_left_accent */
  {0x61D671FAu, 846u}, /* menu_ui_en_s1_o0_normal */
  {0x62114EECu, 32u}, /* expression_delighted_v0_0_follow */
  {0x623E4FD1u, 974u}, /* tap_edge_curious_playful_up_orient */
  {0x62477435u, 407u}, /* life_delighted_e6_s0_rest_hold */
  {0x628CB277u, 619u}, /* life_thoughtful_e31_s0_rest_hold */
  {0x6291D7ABu, 386u}, /* life_delighted_e1_s0_notice_right_orient */
  {0x62C9DDB7u, 1002u}, /* tap_edge_warm_calm_right_orient */
  {0x62DAC88Au, 949u}, /* tap_transition_down_e0_accent */
  {0x63300DCFu, 540u}, /* life_thoughtful_e0_s0_rest_hold */
  {0x637F64D3u, 737u}, /* menu_ui_zh_cn_s0_o3_ack_i6 */
  {0x638C9AE9u, 954u}, /* tap_edge_focused_thoughtful_down_accent */
  {0x6393DE97u, 814u}, /* menu_ui_zh_cn_s10_o1_processing_i3 */
  {0x63957EACu, 70u}, /* expression_sleepy_v0_2_orient */
  {0x63C2C99Du, 978u}, /* tap_edge_curious_playful_left_follow */
  {0x63D4801Bu, 991u}, /* tap_edge_delighted_playful_up_orient */
  {0x63D69877u, 542u}, /* life_thoughtful_e0_s1_notice_left_anticipate */
  {0x63D9B4D7u, 951u}, /* tap_edge_alert_curious_down_settle */
  {0x64197D9Au, 490u}, /* life_warm_e7_s1_notice_right_anticipate */
  {0x64236FF2u, 1042u}, /* tap_edge_thoughtful_alert_center_orient */
  {0x644048FEu, 150u}, /* life_calm_e29_s4_notice_right_settle */
  {0x645C12FDu, 79u}, /* expression_bashful_v0_1_anticipate */
  {0x6461B533u, 114u}, /* tap_edge_curious_alert_down_settle */
  {0x64767DAFu, 173u}, /* life_calm_e5_s2_listen_up_accent */
  {0x6477111Du, 286u}, /* life_curious_e19_s0_question_orient */
  {0x647F6666u, 736u}, /* menu_ui_zh_cn_s0_o3_ack_i5 */
  {0x64B07B5Bu, 296u}, /* life_curious_e4_s2_listen_up_accent */
  {0x64C45E01u, 60u}, /* expression_playful_v0_0_follow */
  {0x64D6D7DAu, 387u}, /* life_delighted_e19_s1_notice_right_anticipate */
  {0x64E28724u, 467u}, /* life_warm_e5_s3_notice_left_follow */
  {0x64E9DDF5u, 565u}, /* tap_local_thoughtful_up */
  {0x64EE3FABu, 976u}, /* tap_edge_curious_playful_down_anticipate */
  {0x651C6877u, 966u}, /* tap_edge_bashful_warm_right_follow */
  {0x652C6FD5u, 1067u}, /* tap_edge_alert_focused_up_orient */
  {0x654E0017u, 527u}, /* life_warm_e24_s1_listen_up_anticipate */
  {0x6555DC58u, 845u}, /* menu_ui_en_s0_o4_ack_i7 */
  {0x657F67F9u, 735u}, /* menu_ui_zh_cn_s0_o3_ack_i4 */
  {0x659783ABu, 965u}, /* tap_edge_playful_warm_center_accent */
  {0x659AEDF7u, 597u}, /* life_thoughtful_e18_s1_notice_right_anticipate */
  {0x65BA2777u, 1050u}, /* tap_edge_thoughtful_calm_center_orient */
  {0x65E6A981u, 113u}, /* expression_focused_v2_2_follow */
  {0x66048ECAu, 1044u}, /* tap_edge_thoughtful_alert_up_orient */
  {0x6606C413u, 114u}, /* tap_edge_curious_alert_right_settle */
  {0x66175562u, 685u}, /* life_alert_e18_s0_rest_hold */
  {0x6653118Fu, 449u}, /* tap_edge_warm_delighted_center_settle */
  {0x6655DDEBu, 844u}, /* menu_ui_en_s0_o4_ack_i6 */
  {0x666EFF43u, 985u}, /* tap_edge_alert_focused_left_settle */
  {0x6673A656u, 393u}, /* life_delighted_e5_s3_soften_settle */
  {0x667B2DBBu, 238u}, /* life_calm_e21_s0_soften_anticipate */
  {0x667F698Cu, 734u}, /* menu_ui_zh_cn_s0_o3_ack_i3 */
  {0x6692E462u, 465u}, /* life_warm_e17_s1_notice_left_anticipate */
  {0x669DA5B1u, 39u}, /* expression_delighted_v2_2_anticipate */
  {0x66A73F87u, 333u}, /* life_curious_e15_s0_rest_hold */
  {0x66C17547u, 465u}, /* life_warm_e1_s1_notice_left_anticipate */
  {0x66CD3FA1u, 682u}, /* life_alert_e17_s0_rest_hold */
  {0x66D3FCD6u, 469u}, /* tap_local_warm_up */
  {0x66D76AD4u, 393u}, /* life_delighted_e3_s0_rest_hold */
  {0x66FA4D8Bu, 540u}, /* tap_edge_focused_thoughtful_left_settle */
  {0x670245D8u, 992u}, /* tap_edge_delighted_warm_down_orient */
  {0x6708940Eu, 1028u}, /* tap_edge_sleepy_calm_up_accent */
  {0x671C8F1Cu, 278u}, /* life_curious_e0_s2_notice_left_accent */
  {0x6755DF7Eu, 843u}, /* menu_ui_en_s0_o4_ack_i5 */
  {0x6763382Eu, 1007u}, /* tap_edge_warm_playful_right_anticipate */
  {0x67718747u, 202u}, /* life_calm_e13_s0_small_breath_anticipate */
  {0x67803C60u, 411u}, /* life_delighted_e7_s0_rest_hold */
  {0x678461F3u, 985u}, /* tap_edge_curious_focused_left_settle */
  {0x6798D78Fu, 134u}, /* speaker_2 */
  {0x679DF80Au, 609u}, /* life_thoughtful_e27_s3_notice_right_follow */
  {0x67A020C5u, 967u}, /* tap_edge_delighted_warm_left_settle */
  {0x6811E6BDu, 61u}, /* expression_playful_v0_2_settle */
  {0x6855E111u, 842u}, /* menu_ui_en_s0_o4_ack_i4 */
  {0x685B8CFCu, 466u}, /* life_warm_e27_s2_notice_left_accent */
  {0x6863B70Bu, 113u}, /* expression_focused_v0_2_follow */
  {0x6892650Cu, 378u}, /* life_curious_e30_s2_notice_right_accent */
  {0x6898D922u, 134u}, /* speaker_1 */
  {0x68A66033u, 1067u}, /* tap_edge_alert_calm_up_orient */
  {0x68C6462Du, 572u}, /* life_thoughtful_e28_s1_notice_left_anticipate */
  {0x68D37E8Bu, 863u}, /* menu_ui_en_s2_o0_ack_i0 */
  {0x690CA379u, 168u}, /* life_calm_e4_s3_notice_left_follow */
  {0x6934323Du, 105u}, /* expression_focused_v2_0_settle */
  {0x69544A36u, 237u}, /* life_calm_e20_s2_small_breath_follow */
  {0x695F92C1u, 658u}, /* life_alert_e8_s1_notice_left_anticipate */
  {0x697CFF68u, 337u}, /* life_curious_e16_s0_rest_hold */
  {0x6998DAB5u, 134u}, /* speaker_0 */
  {0x69BCC25Eu, 967u}, /* tap_edge_playful_warm_center_settle */
  {0x69C3D179u, 400u}, /* life_delighted_e9_s1_notice_right_anticipate */
  {0x69CAA7EBu, 234u}, /* life_calm_e19_s4_listen_up_settle */
  {0x69CF7ACFu, 667u}, /* life_alert_e11_s2_notice_right_accent */
  {0x69D1878Fu, 160u}, /* life_calm_e30_s3_soften_settle */
  {0x69DFCF29u, 376u}, /* life_curious_e30_s0_notice_right_orient */
  {0x69E5FA57u, 163u}, /* life_calm_e3_s2_notice_right_accent */
  {0x6A0B8BE8u, 951u}, /* tap_edge_calm_curious_down_settle */
  {0x6A15B0CFu, 562u}, /* life_thoughtful_e4_s0_notice_left_orient */
  {0x6A31C859u, 556u}, /* life_thoughtful_e27_s4_notice_right_settle */
  {0x6A6062D3u, 1049u}, /* tap_edge_thoughtful_alert_up_anticipate */
  {0x6A6B4AE9u, 502u}, /* life_warm_e12_s0_notice_left_orient */
  {0x6AA48FC1u, 961u}, /* tap_edge_curious_playful_left_orient */
  {0x6AAE9A7Fu, 100u}, /* expression_focused_v0_2_hold */
  {0x6ABD27CDu, 540u}, /* tap_edge_curious_thoughtful_right_settle */
  {0x6AE28933u, 33u}, /* life_delighted_e28_s4_notice_left_settle */
  {0x6AE71FFBu, 167u}, /* life_calm_e4_s2_notice_left_accent */
  {0x6AF32CD0u, 392u}, /* life_delighted_e2_s2_beam_follow */
  {0x6B3B0CD4u, 973u}, /* tap_edge_warm_calm_up_follow */
  {0x6B416685u, 338u}, /* life_curious_e16_s1_listen_up_anticipate */
  {0x6B44B6EEu, 99u}, /* expression_thoughtful_v0_2_follow */
  {0x6B488635u, 1032u}, /* tap_edge_bashful_warm_up_anticipate */
  {0x6B54BAFEu, 1003u}, /* tap_edge_warm_curious_center_anticipate */
  {0x6B5ECCD1u, 1023u}, /* tap_edge_playful_calm_right_orient */
  {0x6B8D8CDAu, 1000u}, /* tap_edge_warm_delighted_down_orient */
  {0x6B965E0Fu, 979u}, /* tap_edge_curious_playful_up_settle */
  {0x6BA099BEu, 80u}, /* expression_bashful_v1_1_accent */
  {0x6BC24515u, 1030u}, /* tap_edge_sleepy_warm_right_accent */
  {0x6BC7A148u, 569u}, /* life_thoughtful_e18_s2_notice_right_accent */
  {0x6BD50261u, 574u}, /* life_thoughtful_e8_s0_ponder_orient */
  {0x6BF8CE1Fu, 979u}, /* tap_edge_curious_playful_left_settle */
  {0x6C0CC296u, 973u}, /* tap_edge_playful_calm_center_follow */
  {0x6C4E3C1Eu, 965u}, /* tap_edge_curious_warm_center_accent */
  {0x6C5B0848u, 140u}, /* menu_progress_0_75 */
  {0x6C72E3FFu, 441u}, /* life_delighted_e18_s1_beam_accent */
  {0x6C7479DDu, 949u}, /* tap_edge_calm_curious_down_accent */
  {0x6C8C760Cu, 229u}, /* life_calm_e19_s0_rest_hold */
  {0x6CF6214Fu, 645u}, /* life_alert_e19_s0_rest_hold */
  {0x6CF7718Bu, 91u}, /* expression_thoughtful_v0_1_settle */
  {0x6D067E79u, 397u}, /* life_delighted_e3_s3_notice_left_follow */
  {0x6D1043EFu, 495u}, /* life_warm_e9_s1_notice_left_anticipate */
  {0x6D31D2EAu, 988u}, /* tap_edge_thoughtful_alert_up_follow */
  {0x6D3EE526u, 579u}, /* life_thoughtful_e10_s1_notice_left_anticipate */
  {0x6D7D7A24u, 550u}, /* life_thoughtful_e16_s3_listen_up_follow */
  {0x6DAF09CAu, 885u}, /* menu_ui_en_s5_o0_ack_i0 */
  {0x6DD3F0F1u, 951u}, /* tap_edge_warm_curious_left_settle */
  {0x6DE97CC2u, 53u}, /* expression_warm_v0_2_anticipate */
  {0x6DF3B2C6u, 111u}, /* expression_focused_v0_2_anticipate */
  {0x6E220466u, 981u}, /* tap_edge_focused_thoughtful_down_follow */
  {0x6E2C2598u, 646u}, /* life_alert_e28_s1_startle_accent */
  {0x6E3C03EAu, 326u}, /* life_curious_e12_s3_listen_up_follow */
  {0x6E510DBCu, 543u}, /* life_thoughtful_e28_s2_notice_left_accent */
  {0x6E5E8D18u, 187u}, /* life_calm_e8_s2_notice_right_accent */
  {0x6E62C170u, 1001u}, /* tap_edge_warm_calm_left_orient */
  {0x6E7C86ADu, 977u}, /* tap_edge_curious_playful_down_accent */
  {0x6E8E9360u, 507u}, /* life_warm_e14_s1_notice_right_anticipate */
  {0x6E998828u, 240u}, /* life_calm_e21_s2_soften_follow */
  {0x6EAF0B5Du, 886u}, /* menu_ui_en_s5_o0_ack_i1 */
  {0x6EBD8D60u, 497u}, /* life_warm_e21_s3_notice_left_follow */
  {0x6EC858F0u, 504u}, /* life_warm_e12_s2_notice_left_accent */
  {0x6EE0FAFBu, 396u}, /* life_delighted_e3_s2_notice_left_accent */
  {0x6EE1F8F1u, 49u}, /* expression_warm_v0_1_anticipate */
  {0x6EF539A8u, 798u}, /* menu_ui_zh_cn_s8_o2_normal */
  {0x6F0B7F04u, 589u}, /* life_thoughtful_e14_s0_rest_hold */
  {0x6F1DB9CCu, 681u}, /* life_alert_e15_s3_notice_left_follow */
  {0x6F51940Cu, 393u}, /* life_delighted_e10_s3_beam_settle */
  {0x6F7B504Eu, 972u}, /* tap_edge_focused_calm_down_accent */
  {0x6F80C03Eu, 696u}, /* life_alert_e22_s2_startle_follow */
  {0x6F894031u, 1031u}, /* tap_edge_bashful_curious_center_orient */
  {0x6F91DD9Eu, 1036u}, /* tap_edge_bashful_calm_left_orient */
  {0x6FAB328Au, 973u}, /* tap_edge_warm_calm_center_settle */
  {0x6FACD10Fu, 803u}, /* menu_ui_zh_cn_s9_o0_ack_i2 */
  {0x6FC39B5Du, 1011u}, /* tap_edge_warm_bashful_right_settle */
  {0x6FFEC423u, 951u}, /* tap_edge_playful_curious_center_settle */
  {0x70260BECu, 1006u}, /* tap_edge_playful_delighted_down_follow */
  {0x70349E85u, 5u}, /* expression_calm_v0_0_settle */
  {0x70362140u, 848u}, /* menu_ui_en_s1_o0_ack_i2 */
  {0x70381762u, 979u}, /* tap_edge_curious_playful_right_settle */
  {0x703F5AB2u, 992u}, /* tap_edge_delighted_calm_down_orient */
  {0x704EF8EEu, 182u}, /* life_calm_e7_s0_small_breath_anticipate */
  {0x7050146Bu, 680u}, /* life_alert_e15_s1_notice_left_anticipate */
  {0x70620D9Au, 252u}, /* life_calm_e25_s1_notice_right_anticipate */
  {0x706AA4A1u, 474u}, /* life_warm_e28_s1_soften_accent */
  {0x70924A9Cu, 973u}, /* tap_edge_focused_calm_up_settle */
  {0x70A677C9u, 283u}, /* life_curious_e26_s3_notice_right_follow */
  {0x70C6DA18u, 966u}, /* tap_edge_calm_warm_center_follow */
  {0x70DFC15Cu, 342u}, /* life_curious_e17_s0_notice_right_orient */
  {0x70EE6AE8u, 1038u}, /* tap_edge_bashful_curious_up_anticipate */
  {0x70F36F8Cu, 47u}, /* life_warm_e14_s4_notice_right_settle */
  {0x7100F714u, 977u}, /* tap_edge_delighted_playful_left_accent */
  {0x711807BEu, 425u}, /* life_delighted_e12_s0_rest_hold */
  {0x712E329Du, 457u}, /* life_delighted_e30_s1_soften_accent */
  {0x713622D3u, 849u}, /* menu_ui_en_s1_o0_ack_i3 */
  {0x713AC553u, 1072u}, /* tap_edge_alert_calm_right_anticipate */
  {0x713CCEBCu, 977u}, /* tap_edge_delighted_playful_center_accent */
  {0x71542845u, 531u}, /* life_warm_e25_s0_soften_anticipate */
  {0x716386F7u, 920u}, /* menu_ui_en_s11_o0_ack_i2 */
  {0x719B3D8Du, 277u}, /* life_curious_e0_s1_notice_left_anticipate */
  {0x71A78120u, 697u}, /* life_alert_e23_s0_rest_hold */
  {0x71D343C4u, 384u}, /* life_delighted_e0_s3_notice_left_follow */
  {0x71D40F11u, 987u}, /* tap_edge_curious_alert_left_accent */
  {0x71D97D89u, 953u}, /* tap_transition_right_e1_anticipate */
  {0x721AA517u, 982u}, /* tap_edge_curious_focused_down_anticipate */
  {0x722C1DF9u, 614u}, /* life_thoughtful_e29_s0_listen_up_orient */
  {0x72424246u, 77u}, /* expression_bashful_v1_0_settle */
  {0x724D38D2u, 403u}, /* life_delighted_e5_s0_rest_hold */
  {0x7258F3ADu, 395u}, /* life_delighted_e11_s1_notice_left_anticipate */
  {0x7271C6F7u, 973u}, /* tap_edge_curious_calm_left_follow */
  {0x7289A61Eu, 343u}, /* life_curious_e17_s1_notice_right_anticipate */
  {0x72ADD7E5u, 19u}, /* life_curious_e6_s4_notice_left_settle */
  {0x72CD50F1u, 42u}, /* expression_warm_v0_0_hold */
  {0x72E32080u, 235u}, /* life_calm_e20_s0_rest_hold */
  {0x730D7D5Bu, 816u}, /* menu_ui_zh_cn_s11_o0_processing_i1 */
  {0x73243E8Fu, 1006u}, /* tap_edge_playful_delighted_left_follow */
  {0x732DEC0Du, 575u}, /* life_thoughtful_e15_s1_ponder_anticipate */
  {0x733625F9u, 847u}, /* menu_ui_en_s1_o0_ack_i1 */
  {0x733A3665u, 1056u}, /* tap_edge_focused_curious_center_orient */
  {0x734E1A4Au, 149u}, /* life_calm_e22_s3_notice_right_follow */
  {0x7352488Au, 59u}, /* expression_playful_v0_0_accent */
  {0x737364F1u, 119u}, /* life_alert_e15_s4_notice_left_settle */
  {0x73F82C2Fu, 462u}, /* life_warm_e0_s2_soften_follow */
  {0x74624C53u, 972u}, /* tap_edge_alert_calm_down_accent */
  {0x7462ABADu, 967u}, /* tap_edge_delighted_warm_center_settle */
  {0x746D31D4u, 966u}, /* tap_edge_sleepy_warm_down_follow */
  {0x746F4EACu, 994u}, /* tap_edge_delighted_calm_right_orient */
  {0x74709230u, 811u}, /* menu_ui_zh_cn_s10_o0_processing_i3 */
  {0x7474940Au, 112u}, /* expression_focused_v2_2_accent */
  {0x748ADB87u, 387u}, /* life_delighted_e29_s1_notice_right_anticipate */
  {0x74B4CB34u, 638u}, /* life_alert_e11_s1_notice_right_anticipate */
  {0x74B6DB0Fu, 973u}, /* tap_edge_playful_calm_right_settle */
  {0x74B6F9F2u, 540u}, /* tap_edge_curious_thoughtful_center_settle */
  {0x74CFF360u, 497u}, /* life_warm_e9_s3_notice_left_follow */
  {0x74DC5B6Au, 602u}, /* life_thoughtful_e20_s2_ponder_accent */
  {0x75261430u, 148u}, /* life_calm_e0_s2_notice_right_accent */
  {0x753AF3CFu, 966u}, /* tap_edge_calm_warm_right_follow */
  {0x755E371Du, 948u}, /* tap_transition_center_e0_anticipate */
  {0x757B963Bu, 985u}, /* tap_edge_alert_focused_center_settle */
  {0x757C3EB6u, 540u}, /* tap_edge_curious_thoughtful_left_settle */
  {0x757E35A6u, 29u}, /* expression_delighted_v2_0_orient */
  {0x759000BEu, 629u}, /* life_alert_e1_s3_listen_up_follow */
  {0x75D77215u, 449u}, /* tap_edge_playful_delighted_center_settle */
  {0x75E86210u, 967u}, /* tap_edge_delighted_warm_right_settle */
  {0x7641A406u, 563u}, /* life_thoughtful_e13_s2_notice_left_accent */
  {0x7688F02Eu, 103u}, /* expression_focused_v0_0_accent */
  {0x769485A7u, 505u}, /* life_warm_e13_s1_soften_accent */
  {0x76B7B5B3u, 1002u}, /* tap_edge_warm_playful_right_orient */
  {0x76CD0CF5u, 978u}, /* tap_edge_curious_playful_center_follow */
  {0x770032E6u, 583u}, /* life_thoughtful_e11_s1_notice_right_anticipate */
  {0x7712B4B4u, 416u}, /* life_delighted_e8_s1_soften_accent */
  {0x7714F2B5u, 967u}, /* tap_edge_sleepy_warm_left_settle */
  {0x772BC580u, 973u}, /* tap_edge_alert_calm_right_settle */
  {0x773199ACu, 180u}, /* life_calm_e24_s3_soften_settle */
  {0x7741C3DDu, 43u}, /* expression_warm_v0_0_orient */
  {0x7746824Bu, 510u}, /* life_warm_e15_s0_listen_up_orient */
  {0x77674D4Au, 1022u}, /* tap_edge_playful_calm_left_orient */
  {0x77A7F2FFu, 77u}, /* expression_bashful_v1_1_settle */
  {0x77D88D30u, 966u}, /* tap_edge_curious_warm_right_follow */
  {0x77F59435u, 650u}, /* life_alert_e9_s1_listen_up_anticipate */
  {0x77FF3721u, 620u}, /* life_thoughtful_e31_s0_ponder_orient */
  {0x78270CB9u, 324u}, /* life_curious_e12_s0_listen_up_orient */
  {0x785470AAu, 390u}, /* life_delighted_e10_s0_beam_anticipate */
  {0x7855FDE7u, 666u}, /* life_alert_e21_s0_notice_right_orient */
  {0x78AC7697u, 72u}, /* expression_bashful_v0_2_hold */
  {0x78E0F47Fu, 19u}, /* life_curious_e27_s4_listen_up_settle */
  {0x78F939DEu, 586u}, /* life_thoughtful_e12_s2_listen_up_accent */
  {0x79397828u, 462u}, /* life_warm_e3_s2_soften_follow */
  {0x795F6D72u, 978u}, /* tap_edge_curious_playful_down_follow */
  {0x79829A18u, 966u}, /* tap_edge_playful_warm_left_follow */
  {0x79AF30A1u, 316u}, /* life_curious_e26_s2_notice_right_accent */
  {0x79B97A2Du, 280u}, /* life_curious_e5_s0_notice_right_orient */
  {0x79E0CCD4u, 505u}, /* life_warm_e25_s1_soften_accent */
  {0x79F147FEu, 433u}, /* life_delighted_e26_s2_beam_follow */
  {0x79F40BCBu, 1013u}, /* tap_edge_playful_delighted_right_anticipate */
  {0x79FD4FBDu, 243u}, /* life_calm_e22_s1_notice_right_anticipate */
  {0x7A179B85u, 879u}, /* menu_ui_en_s4_o0_normal */
  {0x7A1A458Fu, 954u}, /* tap_edge_curious_thoughtful_center_accent */
  {0x7A2BC309u, 179u}, /* life_calm_e24_s2_soften_follow */
  {0x7A37A3F9u, 949u}, /* tap_edge_warm_curious_right_accent */
  {0x7A524EDFu, 907u}, /* menu_ui_en_s9_o1_normal */
  {0x7A53F27Fu, 1009u}, /* tap_edge_warm_bashful_center_accent */
  {0x7A571FBAu, 1059u}, /* tap_edge_focused_alert_down_orient */
  {0x7A5F5473u, 0u}, /* expression_calm_v0_0_hold */
  {0x7A6097DCu, 529u}, /* life_warm_e24_s3_listen_up_follow */
  {0x7A701A49u, 676u}, /* life_alert_e14_s1_notice_right_anticipate */
  {0x7AB6773Eu, 973u}, /* tap_edge_bashful_calm_left_follow */
  {0x7AC64036u, 626u}, /* life_alert_e31_s0_listen_up_orient */
  {0x7AC66246u, 1020u}, /* tap_edge_playful_calm_up_orient */
  {0x7B05AFE8u, 133u}, /* recording_1 */
  {0x7B0F6A17u, 107u}, /* expression_focused_v2_1_anticipate */
  {0x7B29ACF4u, 954u}, /* tap_edge_curious_thoughtful_right_accent */
  {0x7B2A170Eu, 1058u}, /* tap_edge_focused_calm_up_orient */
  {0x7B2BE387u, 1069u}, /* tap_edge_alert_calm_left_orient */
  {0x7B6E6CE2u, 950u}, /* tap_edge_thoughtful_curious_left_follow */
  {0x7B8A44FCu, 963u}, /* tap_transition_right_e1_orient */
  {0x7BA10C7Du, 119u}, /* life_alert_e7_s4_notice_right_settle */
  {0x7BB10DA5u, 973u}, /* tap_edge_delighted_calm_center_follow */
  {0x7BC41B58u, 622u}, /* life_alert_e20_s0_listen_up_orient */
  {0x7BC9BA40u, 610u}, /* life_thoughtful_e25_s0_rest_hold */
  {0x7BD6D490u, 556u}, /* life_thoughtful_e10_s0_rest_hold */
  {0x7BDD6C83u, 954u}, /* tap_edge_focused_thoughtful_right_accent */
  {0x7BEE26B0u, 185u}, /* life_calm_e7_s3_small_breath_settle */
  {0x7BF51087u, 34u}, /* expression_delighted_v2_1_orient */
  {0x7C05B17Bu, 133u}, /* recording_0 */
  {0x7C5712F0u, 999u}, /* tap_edge_warm_bashful_up_orient */
  {0x7C715CDBu, 33u}, /* life_delighted_e25_s4_notice_right_settle */
  {0x7C7BFB9Du, 70u}, /* expression_sleepy_v0_1_settle */
  {0x7C7C91E9u, 984u}, /* tap_edge_thoughtful_focused_center_follow */
  {0x7CA62B1Cu, 14u}, /* expression_curious_v0_2_hold */
  {0x7CC27296u, 70u}, /* tap_local_sleepy_down */
  {0x7CCA7DD2u, 805u}, /* menu_ui_zh_cn_s9_o1_ack_i2 */
  {0x7CCBF5F4u, 941u}, /* tap_local_thoughtful_down */
  {0x7CD6AE6Du, 964u}, /* tap_edge_calm_warm_up_anticipate */
  {0x7CDC69AAu, 451u}, /* life_delighted_e24_s1_soften_accent */
  {0x7CF83845u, 47u}, /* life_warm_e12_s0_rest_hold */
  {0x7CFCACC5u, 174u}, /* life_calm_e5_s3_listen_up_follow */
  {0x7D139137u, 119u}, /* life_alert_e9_s4_listen_up_settle */
  {0x7D17C2A0u, 450u}, /* life_delighted_e30_s0_soften_anticipate */
  {0x7D3F2728u, 1034u}, /* tap_edge_bashful_warm_up_orient */
  {0x7D53BBA5u, 651u}, /* life_alert_e6_s2_listen_up_accent */
  {0x7D58CA03u, 915u}, /* menu_ui_en_s10_o1_normal */
  {0x7D769B59u, 31u}, /* expression_delighted_v2_0_accent */
  {0x7DB3FB85u, 974u}, /* tap_edge_curious_focused_up_orient */
  {0x7DC88B0Cu, 332u}, /* life_curious_e23_s3_notice_right_follow */
  {0x7DD797A2u, 215u}, /* life_calm_e16_s0_small_breath_anticipate */
  {0x7DE3AB41u, 950u}, /* tap_edge_playful_curious_left_follow */
  {0x7E05B4A1u, 133u}, /* recording_2 */
  {0x7E1CCF9Cu, 447u}, /* life_delighted_e22_s1_notice_right_anticipate */
  {0x7E2264BFu, 954u}, /* tap_transition_right_e1_accent */
  {0x7E545EACu, 1062u}, /* tap_edge_focused_thoughtful_center_anticipate */
  {0x7E5AFC13u, 33u}, /* life_delighted_e15_s4_notice_left_settle */
  {0x7E5B7D6Cu, 819u}, /* menu_ui_zh_cn_s12_o0_processing_i1 */
  {0x7E7E781Au, 483u}, /* life_warm_e5_s2_notice_left_accent */
  {0x7E84400Bu, 1064u}, /* tap_edge_focused_calm_left_anticipate */
  {0x7E94916Au, 973u}, /* tap_edge_playful_calm_left_follow */
  {0x7EB29DC7u, 52u}, /* expression_warm_v0_2_orient */
  {0x7EB5959Du, 138u}, /* menu_hold_1500ms */
  {0x7EB66F87u, 563u}, /* life_thoughtful_e10_s2_notice_left_accent */
  {0x7EBC6D5Du, 1066u}, /* tap_edge_alert_focused_right_anticipate */
  {0x7ED43B4Bu, 290u}, /* life_curious_e6_s0_notice_left_orient */
  {0x7EDA0AF6u, 949u}, /* tap_edge_thoughtful_curious_right_accent */
  {0x7EDD9F49u, 77u}, /* expression_bashful_v0_2_settle */
  {0x7EE0259Eu, 789u}, /* menu_ui_zh_cn_s8_o0_normal */
  {0x7EEB3F99u, 237u}, /* life_calm_e23_s2_small_breath_follow */
  {0x7F2F8439u, 947u}, /* tap_edge_calm_curious_center_orient */
  {0x7F3237F1u, 892u}, /* menu_ui_en_s8_o0_normal */
  {0x7F4840FFu, 1010u}, /* tap_edge_warm_bashful_right_follow */
  {0x7F6BB812u, 449u}, /* life_delighted_e23_s0_rest_hold */
  {0x7FE316EDu, 1041u}, /* tap_edge_bashful_calm_up_accent */
  {0x8000B946u, 1005u}, /* tap_edge_warm_delighted_up_accent */
  {0x80414C3Au, 172u}, /* life_calm_e5_s1_listen_up_anticipate */
  {0x8065E909u, 582u}, /* life_thoughtful_e21_s0_notice_right_orient */
  {0x80669C22u, 636u}, /* life_alert_e3_s0_rest_hold */
  {0x809DB279u, 1019u}, /* tap_edge_playful_warm_left_anticipate */
  {0x80A1FF55u, 47u}, /* life_warm_e16_s3_soften_settle */
  {0x80A62552u, 962u}, /* tap_edge_calm_sleepy_right_orient */
  {0x80B06C6Au, 951u}, /* tap_edge_bashful_curious_right_settle */
  {0x80FD2FADu, 987u}, /* tap_edge_curious_alert_up_accent */
  {0x81350369u, 425u}, /* life_delighted_e24_s0_rest_hold */
  {0x81534BBBu, 175u}, /* life_calm_e20_s3_small_breath_settle */
  {0x8156C071u, 556u}, /* life_thoughtful_e3_s3_ponder_settle */
  {0x8156FF38u, 1071u}, /* tap_edge_alert_curious_down_anticipate */
  {0x815BAD63u, 997u}, /* tap_edge_warm_curious_center_orient */
  {0x8165D131u, 967u}, /* tap_edge_playful_warm_right_settle */
  {0x816B0930u, 1063u}, /* tap_edge_focused_alert_center_anticipate */
  {0x816C7822u, 366u}, /* life_curious_e25_s0_rest_hold */
  {0x81765D54u, 1057u}, /* tap_edge_focused_curious_up_anticipate */
  {0x8179C185u, 990u}, /* tap_edge_delighted_warm_down_anticipate */
  {0x817ADB1Cu, 555u}, /* life_thoughtful_e21_s3_notice_right_follow */
  {0x817EA24Fu, 951u}, /* tap_edge_calm_curious_left_settle */
  {0x818BB4D9u, 514u}, /* life_warm_e31_s2_soften_follow */
  {0x81A3FC68u, 119u}, /* life_alert_e10_s3_startle_settle */
  {0x81AB5B5Au, 990u}, /* tap_edge_delighted_warm_center_anticipate */
  {0x81AFE733u, 723u}, /* menu_ui_zh_cn_s0_o1_normal */
  {0x81B2184Eu, 460u}, /* life_warm_e22_s0_soften_anticipate */
  {0x81E0538Fu, 47u}, /* life_warm_e27_s4_notice_left_settle */
  {0x81E0FC68u, 1064u}, /* tap_edge_focused_calm_right_anticipate */
  {0x81E61860u, 339u}, /* life_curious_e27_s2_listen_up_accent */
  {0x8226CC39u, 513u}, /* life_warm_e16_s0_rest_hold */
  {0x82320AAEu, 1072u}, /* tap_edge_alert_calm_up_anticipate */
  {0x824DC446u, 553u}, /* life_thoughtful_e2_s1_notice_right_anticipate */
  {0x82841F81u, 983u}, /* tap_edge_curious_focused_down_accent */
  {0x82B4F3AFu, 981u}, /* tap_edge_curious_thoughtful_right_follow */
  {0x82B928E4u, 68u}, /* expression_playful_v0_2_accent */
  {0x82BEEBF8u, 635u}, /* life_alert_e2_s3_notice_left_follow */
  {0x82C2DD81u, 957u}, /* tap_edge_calm_curious_up_orient */
  {0x832E018Fu, 498u}, /* life_warm_e10_s0_rest_hold */
  {0x83307134u, 290u}, /* life_curious_e3_s0_notice_left_orient */
  {0x83385B4Cu, 119u}, /* life_alert_e17_s4_listen_up_settle */
  {0x834588F0u, 996u}, /* tap_edge_delighted_calm_left_anticipate */
  {0x8378D29Au, 119u}, /* expression_alert_v0_2_settle */
  {0x8389EF88u, 972u}, /* tap_edge_thoughtful_calm_up_accent */
  {0x8391240Fu, 159u}, /* life_calm_e2_s2_soften_follow */
  {0x83A4AA91u, 188u}, /* life_calm_e29_s3_notice_right_follow */
  {0x83D28689u, 442u}, /* life_delighted_e19_s0_rest_hold */
  {0x83DB7464u, 103u}, /* expression_focused_v2_0_accent */
  {0x8423E598u, 979u}, /* tap_edge_delighted_playful_right_settle */
  {0x842BBEB1u, 308u}, /* life_curious_e7_s2_question_accent */
  {0x84381853u, 179u}, /* life_calm_e6_s2_soften_follow */
  {0x844C36D7u, 973u}, /* tap_edge_delighted_calm_center_settle */
  {0x846D528Fu, 287u}, /* life_curious_e2_s1_question_anticipate */
  {0x848F5AC0u, 1006u}, /* tap_edge_warm_delighted_right_follow */
  {0x84929609u, 556u}, /* life_thoughtful_e12_s4_listen_up_settle */
  {0x84A02AE6u, 509u}, /* life_warm_e15_s0_rest_hold */
  {0x84A4DF68u, 42u}, /* expression_warm_v0_1_hold */
  {0x84B08DD2u, 571u}, /* life_thoughtful_e7_s0_notice_left_orient */
  {0x84C95586u, 968u}, /* tap_edge_calm_sleepy_up_anticipate */
  {0x84DAD6D0u, 973u}, /* tap_edge_bashful_calm_center_settle */
  {0x84DDF3D5u, 326u}, /* life_curious_e22_s3_listen_up_follow */
  {0x84EDD511u, 153u}, /* life_calm_e1_s1_small_breath_accent */
  {0x850C96E1u, 276u}, /* tap_local_curious_left */
  {0x8511DC25u, 437u}, /* life_delighted_e16_s1_notice_right_anticipate */
  {0x852E4829u, 949u}, /* tap_edge_playful_curious_down_accent */
  {0x85546721u, 949u}, /* tap_edge_thoughtful_curious_center_accent */
  {0x85975B56u, 114u}, /* life_alert_e25_s0_rest_hold */
  {0x859774AFu, 954u}, /* tap_transition_down_e1_accent */
  {0x85A87B8Du, 1057u}, /* tap_edge_focused_curious_right_anticipate */
  {0x85ABADC7u, 611u}, /* life_thoughtful_e27_s0_notice_right_orient */
  {0x85F9A074u, 58u}, /* expression_playful_v0_0_anticipate */
  {0x86193AD0u, 5u}, /* life_calm_e28_s4_notice_left_settle */
  {0x861C545Eu, 961u}, /* tap_edge_curious_alert_left_orient */
  {0x86463BADu, 392u}, /* life_delighted_e18_s2_beam_follow */
  {0x865A51C6u, 973u}, /* tap_edge_alert_calm_down_settle */
  {0x8665E08Bu, 496u}, /* life_warm_e17_s2_notice_left_accent */
  {0x868EB610u, 785u}, /* menu_ui_zh_cn_s6_o0_ack_i0 */
  {0x86951055u, 227u}, /* life_calm_e18_s3_notice_right_follow */
  {0x86D37348u, 181u}, /* life_calm_e8_s0_rest_hold */
  {0x870F0977u, 1037u}, /* tap_edge_bashful_warm_right_orient */
  {0x8725D7A3u, 965u}, /* tap_edge_delighted_warm_down_accent */
  {0x8727AB24u, 924u}, /* tap_local_calm_center */
  {0x875AAE2Fu, 1054u}, /* tap_edge_thoughtful_calm_left_orient */
  {0x876CDEE2u, 218u}, /* life_calm_e17_s0_rest_hold */
  {0x8789AF21u, 975u}, /* tap_edge_curious_warm_right_anticipate */
  {0x878EB7A3u, 786u}, /* menu_ui_zh_cn_s6_o0_ack_i1 */
  {0x8794827Du, 33u}, /* life_delighted_e2_s3_beam_settle */
  {0x87955F10u, 277u}, /* life_curious_e3_s1_notice_left_anticipate */
  {0x87CA2F2Fu, 19u}, /* life_curious_e0_s4_notice_left_settle */
  {0x8809E0BFu, 398u}, /* life_delighted_e4_s0_rest_hold */
  {0x881127F6u, 666u}, /* life_alert_e11_s0_notice_right_orient */
  {0x88186038u, 979u}, /* tap_edge_curious_playful_down_settle */
  {0x8822C921u, 223u}, /* life_calm_e18_s0_rest_hold */
  {0x885B1944u, 951u}, /* tap_edge_alert_curious_up_settle */
  {0x88678CC3u, 42u}, /* expression_warm_v0_2_hold */
  {0x886B572Fu, 450u}, /* life_delighted_e24_s0_soften_anticipate */
  {0x8887D072u, 817u}, /* menu_ui_zh_cn_s11_o0_ack_i2 */
  {0x888F7A2Fu, 949u}, /* tap_edge_calm_curious_right_accent */
  {0x88AE330Bu, 33u}, /* life_delighted_e20_s4_notice_left_settle */
  {0x88B76AE5u, 646u}, /* life_alert_e5_s1_startle_accent */
  {0x8903E498u, 301u}, /* life_curious_e5_s2_notice_right_accent */
  {0x890E0FF2u, 246u}, /* life_calm_e23_s0_small_breath_anticipate */
  {0x89597298u, 973u}, /* tap_edge_focused_calm_left_settle */
  {0x89A596C9u, 999u}, /* tap_edge_warm_delighted_up_orient */
  {0x89CFBE8Cu, 951u}, /* tap_edge_thoughtful_curious_up_settle */
  {0x89F69963u, 966u}, /* tap_edge_sleepy_warm_up_follow */
  {0x8A25A915u, 972u}, /* tap_edge_alert_calm_right_accent */
  {0x8A2B2853u, 350u}, /* life_curious_e21_s3_notice_left_follow */
  {0x8A2C0250u, 62u}, /* tap_local_playful_center */
  {0x8A737E98u, 577u}, /* life_thoughtful_e9_s3_listen_up_follow */
  {0x8AA9E298u, 90u}, /* expression_thoughtful_v0_0_follow */
  {0x8ADB6A92u, 1006u}, /* tap_edge_playful_delighted_right_follow */
  {0x8AEACFADu, 178u}, /* life_calm_e6_s1_soften_accent */
  {0x8AED6FFFu, 265u}, /* life_calm_e28_s2_notice_left_accent */
  {0x8B1F0036u, 1046u}, /* tap_edge_thoughtful_alert_left_orient */
  {0x8B20B5A6u, 1039u}, /* tap_edge_bashful_curious_left_accent */
  {0x8B390C7Du, 81u}, /* expression_bashful_v1_1_follow */
  {0x8B82A234u, 960u}, /* tap_transition_left_e0_orient */
  {0x8B862FE0u, 381u}, /* life_delighted_e23_s0_notice_left_orient */
  {0x8B98A415u, 153u}, /* life_calm_e10_s1_small_breath_accent */
  {0x8BA3273Cu, 982u}, /* tap_edge_curious_focused_left_anticipate */
  {0x8BA4FFD2u, 409u}, /* life_delighted_e6_s1_beam_accent */
  {0x8BBA3F82u, 1029u}, /* tap_edge_sleepy_warm_left_anticipate */
  {0x8BE01672u, 988u}, /* tap_edge_curious_alert_up_follow */
  {0x8BE8735Bu, 19u}, /* life_curious_e30_s4_notice_right_settle */
  {0x8BFB6990u, 47u}, /* life_warm_e13_s3_soften_settle */
  {0x8C0ECEA8u, 949u}, /* tap_edge_warm_curious_left_accent */
  {0x8C2E6176u, 1065u}, /* tap_edge_alert_curious_center_orient */
  {0x8C401E59u, 996u}, /* tap_edge_delighted_calm_right_anticipate */
  {0x8C5350DEu, 399u}, /* life_delighted_e4_s0_notice_right_orient */
  {0x8C5A3540u, 224u}, /* life_calm_e18_s0_notice_right_orient */
  {0x8CAC0C6Eu, 641u}, /* life_alert_e12_s1_notice_left_anticipate */
  {0x8CF7B479u, 567u}, /* life_thoughtful_e6_s0_rest_hold */
  {0x8D12FA80u, 41u}, /* expression_delighted_v2_2_follow */
  {0x8D2FD7D9u, 524u}, /* life_warm_e23_s2_notice_right_accent */
  {0x8D5BCD51u, 1038u}, /* tap_edge_bashful_curious_right_anticipate */
  {0x8D5E3F2Bu, 169u}, /* life_calm_e11_s4_notice_right_settle */
  {0x8D736185u, 119u}, /* expression_alert_v0_1_settle */
  {0x8D9F1ACCu, 947u}, /* tap_edge_calm_warm_center_orient */
  {0x8DD4C71Bu, 1043u}, /* tap_edge_thoughtful_curious_left_anticipate */
  {0x8DD5FBE8u, 1025u}, /* tap_edge_playful_calm_down_anticipate */
  {0x8DE47288u, 467u}, /* life_warm_e1_s3_notice_left_follow */
  {0x8DF6531Au, 705u}, /* life_alert_e25_s2_listen_up_accent */
  {0x8DFEC6EBu, 793u}, /* menu_ui_zh_cn_s8_o1_normal */
  {0x8E214D9Cu, 889u}, /* menu_ui_en_s6_o0_ack_i1 */
  {0x8E2ABFB6u, 381u}, /* life_delighted_e7_s0_notice_left_orient */
  {0x8E32EC85u, 334u}, /* life_curious_e28_s0_question_orient */
  {0x8E4BAACFu, 214u}, /* life_calm_e16_s0_rest_hold */
  {0x8E6301F0u, 978u}, /* tap_edge_warm_playful_left_follow */
  {0x8EBEB769u, 949u}, /* tap_edge_alert_curious_up_accent */
  {0x8EC6D9FDu, 973u}, /* tap_edge_thoughtful_calm_left_settle */
  {0x8ECB6653u, 85u}, /* expression_bashful_v0_2_follow */
  {0x8ED63163u, 965u}, /* tap_edge_calm_warm_left_accent */
  {0x8F0605D6u, 973u}, /* tap_edge_curious_calm_down_settle */
  {0x8F0F93E4u, 855u}, /* menu_ui_en_s1_o2_normal */
  {0x8F16996Eu, 106u}, /* expression_focused_v2_1_orient */
  {0x8F214F2Fu, 888u}, /* menu_ui_en_s6_o0_ack_i0 */
  {0x8F3626B1u, 948u}, /* tap_transition_up_e0_anticipate */
  {0x8F422EC4u, 1061u}, /* tap_edge_focused_alert_right_orient */
  {0x8F5086DFu, 1048u}, /* tap_edge_thoughtful_focused_down_anticipate */
  {0x8FC9AB33u, 922u}, /* menu_ui_en_s12_o0_processing_i1 */
  {0x8FE18450u, 1027u}, /* tap_edge_sleepy_calm_up_anticipate */
  {0x9027822Fu, 1025u}, /* tap_edge_playful_calm_center_anticipate */
  {0x906BAD7Bu, 149u}, /* life_calm_e3_s3_notice_right_follow */
  {0x906D541Du, 1013u}, /* tap_edge_playful_delighted_down_anticipate */
  {0x907D5678u, 981u}, /* tap_edge_curious_thoughtful_center_follow */
  {0x907FA6E7u, 119u}, /* life_alert_e26_s4_notice_left_settle */
  {0x90978622u, 91u}, /* life_thoughtful_e8_s3_ponder_settle */
  {0x90C16522u, 119u}, /* life_alert_e20_s4_listen_up_settle */
  {0x90DF0010u, 951u}, /* tap_edge_alert_curious_left_settle */
  {0x9105E56Bu, 298u}, /* life_curious_e28_s0_rest_hold */
  {0x910E9227u, 865u}, /* menu_ui_en_s3_o0_processing_i1 */
  {0x91225014u, 493u}, /* life_warm_e19_s0_soften_anticipate */
  {0x912F4FC6u, 19u}, /* life_curious_e28_s3_question_settle */
  {0x914177F9u, 375u}, /* life_curious_e29_s2_notice_left_accent */
  {0x9146546Cu, 972u}, /* tap_edge_thoughtful_calm_center_accent */
  {0x9171D559u, 541u}, /* tap_local_thoughtful_left */
  {0x9187C27Eu, 264u}, /* life_calm_e28_s1_notice_left_anticipate */
  {0x918B9000u, 966u}, /* tap_edge_bashful_warm_center_follow */
  {0x918D78ADu, 647u}, /* life_alert_e5_s2_startle_follow */
  {0x91A0B75Fu, 967u}, /* tap_edge_curious_warm_center_settle */
  {0x91BDB226u, 487u}, /* life_warm_e20_s2_listen_up_accent */
  {0x91C8E04Fu, 973u}, /* tap_edge_focused_calm_down_settle */
  {0x91D2A977u, 393u}, /* life_delighted_e31_s3_beam_settle */
  {0x91FBA10Bu, 247u}, /* life_calm_e23_s1_small_breath_accent */
  {0x920CD436u, 950u}, /* tap_edge_warm_curious_right_follow */
  {0x920E93BAu, 866u}, /* menu_ui_en_s3_o0_processing_i2 */
  {0x9212A973u, 571u}, /* life_thoughtful_e13_s0_notice_left_orient */
  {0x9214A934u, 978u}, /* tap_edge_warm_playful_center_follow */
  {0x922DEA2Eu, 47u}, /* life_warm_e19_s3_soften_settle */
  {0x9236F7E9u, 201u}, /* life_calm_e12_s4_notice_left_settle */
  {0x924CBD29u, 1036u}, /* tap_edge_bashful_curious_left_orient */
  {0x929F4773u, 259u}, /* life_calm_e27_s0_rest_hold */
  {0x92AEE533u, 701u}, /* life_alert_e24_s2_notice_right_accent */
  {0x931A2E90u, 948u}, /* tap_edge_calm_curious_left_anticipate */
  {0x934C51B4u, 1024u}, /* tap_edge_playful_curious_left_anticipate */
  {0x935C7374u, 169u}, /* life_calm_e4_s4_notice_left_settle */
  {0x93837B0Au, 449u}, /* tap_edge_warm_delighted_right_settle */
  {0x93A0B67Eu, 526u}, /* life_warm_e24_s0_rest_hold */
  {0x93A46B1Fu, 546u}, /* life_thoughtful_e26_s0_rest_hold */
  {0x93A93F75u, 998u}, /* tap_edge_warm_calm_up_anticipate */
  {0x93C2A4B7u, 499u}, /* life_warm_e29_s2_notice_right_accent */
  {0x93C4F487u, 972u}, /* tap_edge_warm_calm_center_accent */
  {0x93D6DC6Fu, 702u}, /* life_alert_e24_s3_notice_right_follow */
  {0x93DCED6Du, 973u}, /* tap_edge_curious_calm_center_settle */
  {0x93E9010Cu, 791u}, /* menu_ui_zh_cn_s8_o0_ack_i2 */
  {0x93FC14DEu, 1028u}, /* tap_edge_sleepy_calm_left_accent */
  {0x94054602u, 33u}, /* life_delighted_e30_s3_soften_settle */
  {0x9418C967u, 449u}, /* tap_edge_warm_delighted_up_settle */
  {0x941DC1AAu, 47u}, /* life_warm_e7_s4_notice_right_settle */
  {0x94227571u, 358u}, /* life_curious_e21_s2_notice_left_accent */
  {0x943FB8DAu, 598u}, /* life_thoughtful_e22_s2_notice_left_accent */
  {0x943FB938u, 596u}, /* life_thoughtful_e18_s0_rest_hold */
  {0x946467F7u, 961u}, /* tap_edge_curious_calm_left_orient */
  {0x94671EA5u, 204u}, /* life_calm_e13_s3_small_breath_settle */
  {0x94685691u, 983u}, /* tap_edge_alert_focused_down_accent */
  {0x94756D0Du, 1058u}, /* tap_edge_focused_thoughtful_up_orient */
  {0x94765B6Du, 253u}, /* life_calm_e25_s3_notice_right_follow */
  {0x947C580Bu, 1001u}, /* tap_edge_warm_curious_left_orient */
  {0x94A40934u, 137u}, /* upgrade_progress_0_25 */
  {0x94B8EC2Eu, 951u}, /* tap_transition_center_e0_settle */
  {0x94C045D1u, 334u}, /* life_curious_e15_s0_question_orient */
  {0x94C079D9u, 945u}, /* tap_local_focused_right */
  {0x94E5FAD3u, 787u}, /* menu_ui_zh_cn_s7_o0_normal */
  {0x94E9029Fu, 792u}, /* menu_ui_zh_cn_s8_o0_ack_i3 */
  {0x94F3C468u, 951u}, /* tap_edge_thoughtful_curious_left_settle */
  {0x94FF4E64u, 374u}, /* life_curious_e29_s0_notice_left_orient */
  {0x94FF6187u, 959u}, /* tap_edge_curious_thoughtful_down_orient */
  {0x951805A3u, 70u}, /* tap_local_sleepy_center */
  {0x954A4C90u, 1064u}, /* tap_edge_focused_calm_down_anticipate */
  {0x954BCB96u, 32u}, /* expression_delighted_v2_0_follow */
  {0x9557C1B6u, 808u}, /* menu_ui_zh_cn_s9_o3_normal */
  {0x957B09DBu, 47u}, /* life_warm_e12_s4_notice_left_settle */
  {0x95974C16u, 995u}, /* tap_edge_delighted_playful_up_anticipate */
  {0x959E77ADu, 1035u}, /* tap_edge_bashful_calm_down_orient */
  {0x95E80CC2u, 973u}, /* tap_edge_delighted_calm_down_follow */
  {0x960925D0u, 213u}, /* life_calm_e15_s3_soften_settle */
  {0x960EF4AFu, 64u}, /* expression_playful_v0_1_accent */
  {0x9610C4ABu, 672u}, /* life_alert_e13_s2_listen_up_accent */
  {0x9653D147u, 565u}, /* life_thoughtful_e12_s0_listen_up_orient */
  {0x965ADACCu, 1022u}, /* tap_edge_playful_warm_left_orient */
  {0x969DB4F9u, 911u}, /* menu_ui_en_s9_o3_normal */
  {0x96A6355Cu, 909u}, /* menu_ui_en_s9_o2_normal */
  {0x96AE95B6u, 346u}, /* life_curious_e18_s0_rest_hold */
  {0x96B226A3u, 649u}, /* life_alert_e6_s0_rest_hold */
  {0x96B68425u, 1039u}, /* tap_edge_bashful_curious_down_accent */
  {0x96BF2969u, 663u}, /* life_alert_e10_s0_startle_orient */
  {0x96C25A9Bu, 837u}, /* menu_ui_en_s0_o3_ack_i3 */
  {0x96C7864Au, 128u}, /* blink_open */
  {0x96E905C5u, 790u}, /* menu_ui_zh_cn_s8_o0_ack_i1 */
  {0x96F35DAAu, 983u}, /* tap_edge_curious_focused_up_accent */
  {0x9714C965u, 324u}, /* life_curious_e16_s0_listen_up_orient */
  {0x9731C2FCu, 288u}, /* life_curious_e2_s2_question_accent */
  {0x9736D001u, 950u}, /* tap_edge_focused_curious_center_follow */
  {0x97564E74u, 33u}, /* life_delighted_e3_s4_notice_left_settle */
  {0x975CB25Du, 949u}, /* tap_edge_thoughtful_curious_left_accent */
  {0x9779D9BCu, 1040u}, /* tap_edge_bashful_calm_down_anticipate */
  {0x977A32CAu, 983u}, /* tap_edge_curious_focused_center_accent */
  {0x97A49A34u, 999u}, /* tap_edge_warm_playful_up_orient */
  {0x97B802A3u, 353u}, /* life_curious_e20_s0_rest_hold */
  {0x97C034AEu, 674u}, /* life_alert_e14_s0_rest_hold */
  {0x97C048A4u, 483u}, /* life_warm_e30_s2_notice_left_accent */
  {0x97C9C5E9u, 19u}, /* life_curious_e31_s0_rest_hold */
  {0x97FB6DA8u, 650u}, /* life_alert_e6_s1_listen_up_anticipate */
  {0x9812E56Cu, 445u}, /* life_delighted_e24_s2_soften_follow */
  {0x9813B6D4u, 1005u}, /* tap_edge_playful_delighted_left_accent */
  {0x9853EA31u, 28u}, /* life_delighted_e11_s0_rest_hold */
  {0x98AB30BCu, 19u}, /* life_curious_e1_s0_rest_hold */
  {0x98AFB8B3u, 20u}, /* expression_curious_v0_1_orient */
  {0x98C37D65u, 107u}, /* expression_focused_v0_1_anticipate */
  {0x98C79EFFu, 33u}, /* life_delighted_e22_s0_rest_hold */
  {0x98D6802Fu, 105u}, /* expression_focused_v0_0_settle */
  {0x98F23D05u, 84u}, /* expression_bashful_v1_2_accent */
  {0x994C49D4u, 410u}, /* life_delighted_e6_s2_beam_follow */
  {0x995420E6u, 950u}, /* tap_edge_alert_curious_up_follow */
  {0x995AA355u, 979u}, /* tap_edge_delighted_playful_center_settle */
  {0x998EC826u, 972u}, /* tap_edge_playful_calm_down_accent */
  {0x999942F6u, 1019u}, /* tap_edge_playful_warm_down_anticipate */
  {0x999C4BDBu, 775u}, /* menu_ui_zh_cn_s3_o3_processing_i5 */
  {0x99C25F54u, 840u}, /* menu_ui_en_s0_o3_ack_i6 */
  {0x99C93CE3u, 675u}, /* life_alert_e14_s0_notice_right_orient */
  {0x9A1034F6u, 949u}, /* tap_edge_alert_curious_down_accent */
  {0x9A3ADFADu, 444u}, /* life_delighted_e19_s3_notice_right_follow */
  {0x9A67F938u, 975u}, /* tap_edge_curious_warm_left_anticipate */
  {0x9A6E4726u, 1039u}, /* tap_edge_bashful_curious_up_accent */
  {0x9A781159u, 955u}, /* tap_transition_left_e1_follow */
  {0x9A972EBAu, 560u}, /* life_thoughtful_e15_s2_ponder_accent */
  {0x9A990938u, 114u}, /* tap_edge_curious_alert_up_settle */
  {0x9AE56CD3u, 19u}, /* life_curious_e7_s3_question_settle */
  {0x9B0B4D09u, 119u}, /* life_alert_e0_s3_startle_settle */
  {0x9B23EA1Du, 276u}, /* life_curious_e0_s0_notice_left_orient */
  {0x9B587F7Cu, 590u}, /* life_thoughtful_e14_s2_notice_right_accent */
  {0x9B72D672u, 459u}, /* life_warm_e0_s0_rest_hold */
  {0x9B9A42DBu, 285u}, /* life_curious_e2_s0_rest_hold */
  {0x9BB576E4u, 712u}, /* life_alert_e28_s2_startle_follow */
  {0x9BC23B8Eu, 603u}, /* life_thoughtful_e30_s2_notice_right_accent */
  {0x9BC2627Au, 838u}, /* menu_ui_en_s0_o3_ack_i4 */
  {0x9BDC8996u, 385u}, /* life_delighted_e1_s0_rest_hold */
  {0x9BE766D2u, 240u}, /* life_calm_e30_s2_soften_follow */
  {0x9BEFA988u, 456u}, /* life_delighted_e29_s0_rest_hold */
  {0x9C57EC84u, 370u}, /* life_curious_e26_s0_notice_right_orient */
  {0x9C6194A8u, 747u}, /* menu_ui_zh_cn_s1_o1_normal */
  {0x9C734F66u, 556u}, /* life_thoughtful_e11_s4_notice_right_settle */
  {0x9C74FD63u, 561u}, /* life_thoughtful_e4_s0_rest_hold */
  {0x9C908289u, 119u}, /* life_alert_e18_s4_notice_right_settle */
  {0x9CC2640Du, 839u}, /* menu_ui_en_s0_o3_ack_i5 */
  {0x9CD08953u, 1025u}, /* tap_edge_playful_calm_left_anticipate */
  {0x9CDD5531u, 984u}, /* tap_edge_alert_focused_center_follow */
  {0x9D230A74u, 93u}, /* expression_thoughtful_v0_1_anticipate */
  {0x9D37E085u, 551u}, /* life_thoughtful_e2_s0_rest_hold */
  {0x9D3F4D14u, 427u}, /* life_delighted_e25_s0_rest_hold */
  {0x9D5EB4BEu, 372u}, /* life_curious_e27_s3_listen_up_follow */
  {0x9DA00884u, 972u}, /* tap_edge_warm_calm_down_accent */
  {0x9DB99828u, 251u}, /* life_calm_e25_s0_notice_right_orient */
  {0x9DC40B68u, 443u}, /* life_delighted_e19_s0_notice_right_orient */
  {0x9E010F10u, 992u}, /* tap_edge_delighted_playful_down_orient */
  {0x9E351D4Du, 244u}, /* life_calm_e25_s2_notice_right_accent */
  {0x9E4B7F9Fu, 973u}, /* tap_edge_thoughtful_calm_left_follow */
  {0x9E6AEFBAu, 429u}, /* life_delighted_e17_s2_soften_follow */
  {0x9E6D528Au, 199u}, /* life_calm_e12_s2_notice_left_accent */
  {0x9E83D15Au, 33u}, /* life_delighted_e23_s4_notice_left_settle */
  {0x9E8A7B49u, 230u}, /* life_calm_e19_s0_listen_up_orient */
  {0x9EBBF92Eu, 950u}, /* tap_edge_focused_curious_down_follow */
  {0x9F024164u, 997u}, /* tap_edge_warm_calm_center_orient */
  {0x9F7906BDu, 266u}, /* life_calm_e29_s0_rest_hold */
  {0x9F79A299u, 868u}, /* menu_ui_en_s3_o1_normal */
  {0x9F7F031Bu, 703u}, /* life_alert_e25_s0_listen_up_orient */
  {0x9F96BEEDu, 72u}, /* expression_bashful_v1_1_hold */
  {0x9F99EBE9u, 46u}, /* expression_warm_v0_0_follow */
  {0x9F9C55CAu, 998u}, /* tap_edge_warm_calm_down_anticipate */
  {0xA00A5559u, 950u}, /* tap_edge_focused_curious_left_follow */
  {0xA01AAC71u, 998u}, /* tap_edge_warm_calm_center_anticipate */
  {0xA03FD6ECu, 933u}, /* tap_local_playful_left */
  {0xA06826E7u, 119u}, /* life_alert_e30_s4_notice_right_settle */
  {0xA0A63355u, 262u}, /* life_calm_e27_s2_small_breath_follow */
  {0xA0AD639Bu, 1051u}, /* tap_edge_thoughtful_calm_right_anticipate */
  {0xA0BACFA9u, 1021u}, /* tap_edge_playful_calm_down_orient */
  {0xA11FCF1Bu, 929u}, /* tap_local_delighted_up */
  {0xA14280A9u, 8u}, /* expression_calm_v0_1_accent */
  {0xA152C5EFu, 558u}, /* life_thoughtful_e15_s0_ponder_orient */
  {0xA16A83F2u, 622u}, /* life_alert_e17_s0_listen_up_orient */
  {0xA17B13D9u, 362u}, /* life_curious_e23_s0_notice_right_orient */
  {0xA19A4EA9u, 1034u}, /* tap_edge_bashful_curious_up_orient */
  {0xA19E34C8u, 365u}, /* life_curious_e24_s2_question_accent */
  {0xA1A13274u, 1057u}, /* tap_edge_focused_curious_center_anticipate */
  {0xA1DB06D3u, 672u}, /* life_alert_e31_s2_listen_up_accent */
  {0xA2054D6Eu, 72u}, /* expression_bashful_v1_2_hold */
  {0xA20A7A5Au, 492u}, /* life_warm_e8_s0_rest_hold */
  {0xA210788Au, 1032u}, /* tap_edge_bashful_warm_down_anticipate */
  {0xA250E5CFu, 978u}, /* tap_edge_delighted_playful_left_follow */
  {0xA26486D6u, 556u}, /* life_thoughtful_e24_s4_notice_right_settle */
  {0xA266ED88u, 74u}, /* expression_bashful_v0_0_anticipate */
  {0xA2A49472u, 954u}, /* tap_transition_left_e1_accent */
  {0xA3411432u, 1041u}, /* tap_edge_bashful_calm_down_accent */
  {0xA35BFF13u, 249u}, /* life_calm_e24_s1_soften_accent */
  {0xA36598DCu, 950u}, /* tap_edge_focused_curious_right_follow */
  {0xA38A9E45u, 168u}, /* life_calm_e28_s3_notice_left_follow */
  {0xA38FF34Fu, 566u}, /* life_thoughtful_e5_s1_listen_up_anticipate */
  {0xA39395A4u, 91u}, /* life_thoughtful_e7_s0_rest_hold */
  {0xA397043Du, 541u}, /* life_thoughtful_e28_s0_notice_left_orient */
  {0xA3B53FFDu, 434u}, /* life_delighted_e15_s0_rest_hold */
  {0xA3C34695u, 973u}, /* tap_edge_focused_calm_right_follow */
  {0xA3D202F8u, 405u}, /* life_delighted_e17_s1_soften_accent */
  {0xA3D4A05Cu, 162u}, /* life_calm_e3_s1_notice_right_anticipate */
  {0xA40223BCu, 966u}, /* tap_edge_calm_warm_up_follow */
  {0xA40D2D0Fu, 406u}, /* life_delighted_e5_s2_soften_follow */
  {0xA41BD989u, 952u}, /* tap_edge_curious_playful_center_orient */
  {0xA44F575Du, 995u}, /* tap_edge_delighted_playful_down_anticipate */
  {0xA47B2229u, 33u}, /* life_delighted_e2_s0_rest_hold */
  {0xA47F80C8u, 976u}, /* tap_edge_curious_playful_center_anticipate */
  {0xA4D2C93Cu, 626u}, /* life_alert_e6_s0_listen_up_orient */
  {0xA4E5CFA6u, 391u}, /* life_delighted_e2_s1_beam_accent */
  {0xA525159Au, 995u}, /* tap_edge_delighted_playful_left_anticipate */
  {0xA558C8A2u, 994u}, /* tap_edge_delighted_playful_right_orient */
  {0xA564FDE8u, 47u}, /* life_warm_e22_s3_soften_settle */
  {0xA57E1902u, 376u}, /* tap_local_curious_right */
  {0xA5A5998Fu, 966u}, /* tap_edge_delighted_warm_center_follow */
  {0xA5B2A350u, 813u}, /* menu_ui_zh_cn_s10_o1_ack_i2 */
  {0xA5C4BA8Au, 949u}, /* tap_edge_focused_curious_center_accent */
  {0xA5CD6583u, 83u}, /* expression_bashful_v1_2_anticipate */
  {0xA5F87BC1u, 390u}, /* life_delighted_e26_s0_beam_anticipate */
  {0xA5FBA792u, 1008u}, /* tap_edge_warm_bashful_down_anticipate */
  {0xA60B7376u, 1045u}, /* tap_edge_thoughtful_focused_down_orient */
  {0xA6594471u, 993u}, /* tap_edge_delighted_calm_left_orient */
  {0xA6A44E11u, 105u}, /* expression_focused_v0_2_settle */
  {0xA6C24894u, 972u}, /* tap_edge_curious_calm_center_accent */
  {0xA6C6D770u, 492u}, /* life_warm_e13_s0_rest_hold */
  {0xA706AC1Du, 1069u}, /* tap_edge_alert_focused_left_orient */
  {0xA773E45Eu, 990u}, /* tap_edge_delighted_warm_up_anticipate */
  {0xA782234Cu, 87u}, /* expression_thoughtful_v0_0_orient */
  {0xA7878A90u, 114u}, /* tap_edge_curious_alert_center_settle */
  {0xA78E72ABu, 949u}, /* tap_edge_focused_curious_right_accent */
  {0xA7B2DBA6u, 1003u}, /* tap_edge_warm_curious_left_anticipate */
  {0xA81F879Eu, 477u}, /* life_warm_e23_s1_notice_right_anticipate */
  {0xA822039Au, 964u}, /* tap_edge_calm_warm_right_anticipate */
  {0xA82AFD8Bu, 965u}, /* tap_edge_calm_warm_up_accent */
  {0xA83644BDu, 1056u}, /* tap_edge_focused_thoughtful_center_orient */
  {0xA836D872u, 949u}, /* tap_edge_focused_curious_left_accent */
  {0xA89A22A5u, 445u}, /* life_delighted_e21_s2_soften_follow */
  {0xA8A52898u, 975u}, /* tap_edge_curious_warm_up_anticipate */
  {0xA8A9EAFBu, 606u}, /* life_thoughtful_e23_s0_listen_up_orient */
  {0xA8B09BDEu, 1068u}, /* tap_edge_alert_focused_down_orient */
  {0xA8CF2D8Au, 593u}, /* life_thoughtful_e16_s2_listen_up_accent */
  {0xA8F24F88u, 5u}, /* life_calm_e3_s4_notice_right_settle */
  {0xA932A532u, 354u}, /* life_curious_e20_s0_notice_right_orient */
  {0xA93FC06Du, 40u}, /* expression_delighted_v0_2_accent */
  {0xA944450Eu, 856u}, /* menu_ui_en_s1_o2_ack_i2 */
  {0xA96FAF24u, 972u}, /* tap_edge_thoughtful_calm_left_accent */
  {0xA98B5FCBu, 973u}, /* tap_edge_thoughtful_calm_up_follow */
  {0xA98DA387u, 978u}, /* tap_edge_delighted_playful_center_follow */
  {0xA9B1BC6Eu, 650u}, /* life_alert_e13_s1_listen_up_anticipate */
  {0xAA1B3619u, 56u}, /* expression_playful_v0_0_hold */
  {0xAA4446A1u, 857u}, /* menu_ui_en_s1_o2_ack_i3 */
  {0xAA45AD57u, 647u}, /* life_alert_e10_s2_startle_follow */
  {0xAA6DA9BAu, 360u}, /* life_curious_e22_s0_listen_up_orient */
  {0xAA7B74A5u, 952u}, /* tap_edge_curious_focused_center_orient */
  {0xAA8E55A2u, 1060u}, /* tap_edge_focused_calm_left_orient */
  {0xAA9432EDu, 405u}, /* life_delighted_e27_s1_soften_accent */
  {0xAAA3E0FBu, 114u}, /* tap_edge_thoughtful_alert_down_settle */
  {0xAABA62DBu, 653u}, /* life_alert_e7_s0_notice_right_orient */
  {0xAB444834u, 858u}, /* menu_ui_en_s1_o2_ack_i4 */
  {0xAB947385u, 428u}, /* life_delighted_e13_s0_soften_anticipate */
  {0xABB3B15Eu, 951u}, /* tap_edge_focused_curious_right_settle */
  {0xABBB9EAEu, 1029u}, /* tap_edge_sleepy_warm_up_anticipate */
  {0xABC62FF1u, 972u}, /* tap_edge_focused_calm_center_accent */
  {0xABE8536Du, 1051u}, /* tap_edge_thoughtful_calm_down_anticipate */
  {0xABEFFDA3u, 986u}, /* tap_edge_curious_alert_center_anticipate */
  {0xABF8451Cu, 613u}, /* life_thoughtful_e29_s0_rest_hold */
  {0xAC0CDEAEu, 392u}, /* life_delighted_e31_s2_beam_follow */
  {0xAC39BB57u, 401u}, /* life_delighted_e4_s2_notice_right_accent */
  {0xAC4C809Eu, 756u}, /* menu_ui_zh_cn_s1_o3_normal */
  {0xAC4EA93Eu, 967u}, /* tap_edge_calm_warm_up_settle */
  {0xAC5BC4B5u, 707u}, /* life_alert_e26_s0_notice_left_orient */
  {0xAC6E38D1u, 1063u}, /* tap_edge_focused_alert_right_anticipate */
  {0xAC9BC28Du, 221u}, /* life_calm_e17_s2_notice_left_accent */
  {0xACC56348u, 966u}, /* tap_edge_playful_warm_up_follow */
  {0xACFDCF99u, 961u}, /* tap_edge_curious_warm_left_orient */
  {0xAD14491Fu, 831u}, /* menu_ui_en_s0_o2_normal */
  {0xAD48BBFBu, 996u}, /* tap_edge_delighted_calm_down_anticipate */
  {0xAD574F55u, 841u}, /* menu_ui_en_s0_o4_normal */
  {0xAD865177u, 1010u}, /* tap_edge_warm_bashful_down_follow */
  {0xADA4E772u, 951u}, /* tap_edge_warm_curious_down_settle */
  {0xADAC74BDu, 473u}, /* life_warm_e23_s0_rest_hold */
  {0xADAF505Au, 1013u}, /* tap_edge_playful_delighted_left_anticipate */
  {0xADE325B8u, 106u}, /* expression_focused_v0_1_orient */
  {0xADE798F9u, 63u}, /* expression_playful_v0_1_anticipate */
  {0xADEB7A4Au, 987u}, /* tap_edge_thoughtful_alert_right_accent */
  {0xAE729B53u, 972u}, /* tap_edge_warm_calm_up_accent */
  {0xAF02DAA5u, 965u}, /* tap_edge_delighted_warm_right_accent */
  {0xAF21D9D1u, 404u}, /* life_delighted_e17_s0_soften_anticipate */
  {0xAF2D0075u, 439u}, /* life_delighted_e20_s0_rest_hold */
  {0xAF4B7C2Eu, 33u}, /* expression_delighted_v0_0_settle */
  {0xAF4FED5Cu, 1024u}, /* tap_edge_playful_curious_up_anticipate */
  {0xAFD0002Cu, 952u}, /* tap_edge_curious_thoughtful_center_orient */
  {0xAFD683CCu, 316u}, /* life_curious_e9_s2_notice_right_accent */
  {0xB0077B44u, 1037u}, /* tap_edge_bashful_curious_right_orient */
  {0xB01846B4u, 963u}, /* tap_edge_curious_warm_right_orient */
  {0xB025777Cu, 91u}, /* expression_thoughtful_v0_2_settle */
  {0xB058B5FFu, 876u}, /* menu_ui_en_s3_o3_normal */
  {0xB05CCFB1u, 390u}, /* life_delighted_e31_s0_beam_anticipate */
  {0xB0872055u, 169u}, /* life_calm_e21_s0_rest_hold */
  {0xB0B16A1Du, 294u}, /* life_curious_e4_s0_rest_hold */
  {0xB0C34645u, 47u}, /* life_warm_e24_s4_listen_up_settle */
  {0xB0C46BECu, 185u}, /* life_calm_e23_s3_small_breath_settle */
  {0xB0E06592u, 528u}, /* life_warm_e24_s2_listen_up_accent */
  {0xB1120521u, 972u}, /* tap_edge_focused_calm_up_accent */
  {0xB11300BBu, 874u}, /* menu_ui_en_s3_o2_ack_i3 */
  {0xB115CC68u, 1001u}, /* tap_edge_warm_bashful_left_orient */
  {0xB11C8A7Cu, 157u}, /* life_calm_e2_s0_soften_anticipate */
  {0xB133915Au, 70u}, /* expression_sleepy_v0_0_hold */
  {0xB14EFCF1u, 1004u}, /* tap_edge_warm_delighted_right_anticipate */
  {0xB1629BD0u, 947u}, /* tap_transition_center_e0_orient */
  {0xB16D7412u, 166u}, /* life_calm_e4_s1_notice_left_anticipate */
  {0xB181901Au, 307u}, /* life_curious_e7_s1_question_anticipate */
  {0xB1981B97u, 572u}, /* life_thoughtful_e13_s1_notice_left_anticipate */
  {0xB1B0AD5Du, 973u}, /* tap_edge_warm_calm_down_settle */
  {0xB1C0A523u, 1063u}, /* tap_edge_focused_alert_down_anticipate */
  {0xB1E659DEu, 973u}, /* tap_edge_focused_calm_center_follow */
  {0xB1FE6CD2u, 15u}, /* expression_curious_v0_0_orient */
  {0xB2103EEBu, 950u}, /* tap_edge_warm_curious_left_follow */
  {0xB226D9A5u, 632u}, /* life_alert_e4_s0_notice_left_orient */
  {0xB23A1FA4u, 493u}, /* life_warm_e8_s0_soften_anticipate */
  {0xB242B1B4u, 982u}, /* tap_edge_curious_focused_center_anticipate */
  {0xB26EDB4Bu, 34u}, /* tap_local_delighted_center */
  {0xB29B366Cu, 1033u}, /* tap_edge_bashful_warm_right_accent */
  {0xB2B082E7u, 664u}, /* life_alert_e10_s1_startle_accent */
  {0xB2CC9709u, 318u}, /* life_curious_e10_s2_notice_left_accent */
  {0xB2F44AE3u, 91u}, /* life_thoughtful_e19_s4_notice_left_settle */
  {0xB308330Fu, 949u}, /* tap_edge_warm_curious_down_accent */
  {0xB333C144u, 942u}, /* tap_local_focused_up */
  {0xB34EB7BFu, 169u}, /* life_calm_e8_s4_notice_right_settle */
  {0xB3735B36u, 912u}, /* menu_ui_en_s10_o0_normal */
  {0xB3794D4Du, 1014u}, /* tap_edge_playful_curious_up_orient */
  {0xB3A2AA5Eu, 949u}, /* tap_edge_thoughtful_curious_down_accent */
  {0xB3C21E06u, 977u}, /* tap_edge_curious_playful_center_accent */
  {0xB3C6BD20u, 1018u}, /* tap_edge_playful_warm_center_orient */
  {0xB3D40F94u, 14u}, /* life_curious_e30_s0_rest_hold */
  {0xB4043EC5u, 119u}, /* life_alert_e0_s0_rest_hold */
  {0xB422B450u, 1030u}, /* tap_edge_sleepy_warm_up_accent */
  {0xB48467BAu, 776u}, /* menu_ui_zh_cn_s4_o0_normal */
  {0xB4869481u, 108u}, /* expression_focused_v2_1_accent */
  {0xB4A03530u, 1036u}, /* tap_edge_bashful_warm_left_orient */
  {0xB4D8B361u, 422u}, /* life_delighted_e15_s0_notice_left_orient */
  {0xB4FB56E2u, 424u}, /* life_delighted_e11_s3_notice_left_follow */
  {0xB50A1AC5u, 369u}, /* life_curious_e26_s0_rest_hold */
  {0xB5316165u, 1062u}, /* tap_edge_focused_thoughtful_right_anticipate */
  {0xB5351CE1u, 185u}, /* life_calm_e31_s3_small_breath_settle */
  {0xB565060Cu, 1066u}, /* tap_edge_alert_focused_left_anticipate */
  {0xB56BAB6Cu, 591u}, /* life_thoughtful_e14_s3_notice_right_follow */
  {0xB57C0CCBu, 100u}, /* expression_focused_v2_0_hold */
  {0xB57FBB37u, 966u}, /* tap_edge_delighted_warm_left_follow */
  {0xB5B25CB4u, 91u}, /* life_thoughtful_e20_s3_ponder_settle */
  {0xB5C3DC99u, 538u}, /* life_warm_e30_s0_rest_hold */
  {0xB5C4C02Au, 617u}, /* life_thoughtful_e29_s3_listen_up_follow */
  {0xB5DA979Eu, 985u}, /* tap_edge_curious_focused_right_settle */
  {0xB60CA4C7u, 951u}, /* tap_edge_bashful_curious_left_settle */
  {0xB64AB6F1u, 534u}, /* life_warm_e27_s0_rest_hold */
  {0xB64D0D0Au, 70u}, /* expression_sleepy_v0_1_anticipate */
  {0xB6587C3Au, 611u}, /* tap_local_thoughtful_right */
  {0xB66D51DAu, 535u}, /* life_warm_e31_s0_soften_anticipate */
  {0xB681939Cu, 826u}, /* menu_ui_en_s0_o1_normal */
  {0xB683275Cu, 54u}, /* expression_warm_v0_2_accent */
  {0xB68B2399u, 150u}, /* life_calm_e22_s4_notice_right_settle */
  {0xB68BCF51u, 949u}, /* tap_edge_thoughtful_curious_up_accent */
  {0xB69EDE73u, 195u}, /* life_calm_e11_s1_notice_right_anticipate */
  {0xB6B1E2CDu, 938u}, /* tap_local_bashful_down */
  {0xB70A2680u, 871u}, /* menu_ui_en_s3_o1_ack_i3 */
  {0xB71575ABu, 897u}, /* menu_ui_en_s8_o1_ack_i1 */
  {0xB71FC2CFu, 330u}, /* life_curious_e14_s0_notice_right_orient */
  {0xB7289593u, 699u}, /* life_alert_e24_s0_rest_hold */
  {0xB72A1DBBu, 460u}, /* life_warm_e3_s0_soften_anticipate */
  {0xB74D7B89u, 516u}, /* life_warm_e17_s3_notice_left_follow */
  {0xB75DC36Eu, 984u}, /* tap_edge_curious_focused_down_follow */
  {0xB7639FA2u, 954u}, /* tap_edge_focused_thoughtful_center_accent */
  {0xB78A055Bu, 972u}, /* tap_edge_warm_calm_left_accent */
  {0xB79D3D07u, 1005u}, /* tap_edge_warm_delighted_right_accent */
  {0xB7A4C053u, 1030u}, /* tap_edge_sleepy_warm_down_accent */
  {0xB7B28ADCu, 517u}, /* life_warm_e23_s0_notice_right_orient */
  {0xB7BCEC73u, 973u}, /* tap_edge_bashful_calm_down_settle */
  {0xB7D06C4Cu, 944u}, /* tap_local_focused_left */
  {0xB7D69999u, 973u}, /* tap_edge_alert_calm_up_settle */
  {0xB7DC2177u, 368u}, /* life_curious_e25_s3_notice_left_follow */
  {0xB7E2DF07u, 494u}, /* life_warm_e9_s0_rest_hold */
  {0xB7E5F279u, 964u}, /* tap_edge_calm_warm_center_anticipate */
  {0xB7EA8D20u, 975u}, /* tap_edge_curious_warm_center_anticipate */
  {0xB7ED8D75u, 1008u}, /* tap_edge_warm_bashful_left_anticipate */
  {0xB7F55176u, 632u}, /* life_alert_e23_s0_notice_left_orient */
  {0xB8063604u, 109u}, /* expression_focused_v0_1_follow */
  {0xB8135179u, 192u}, /* life_calm_e10_s0_rest_hold */
  {0xB813CCADu, 33u}, /* life_delighted_e1_s4_notice_right_settle */
  {0xB815773Eu, 898u}, /* menu_ui_en_s8_o1_ack_i2 */
  {0xB88198D0u, 973u}, /* tap_edge_curious_calm_right_settle */
  {0xB8A6C1ADu, 988u}, /* tap_edge_focused_alert_center_follow */
  {0xB8C837E1u, 950u}, /* tap_edge_focused_curious_up_follow */
  {0xB8CF73D1u, 47u}, /* life_warm_e20_s4_listen_up_settle */
  {0xB8D1B34Au, 361u}, /* life_curious_e22_s1_listen_up_anticipate */
  {0xB8D99013u, 1033u}, /* tap_edge_bashful_warm_up_accent */
  {0xB8DD7094u, 441u}, /* life_delighted_e31_s1_beam_accent */
  {0xB8F78140u, 84u}, /* expression_bashful_v0_2_accent */
  {0xB90A370Du, 940u}, /* tap_local_bashful_right */
  {0xB91519BAu, 973u}, /* tap_edge_bashful_calm_center_follow */
  {0xB91578D1u, 899u}, /* menu_ui_en_s8_o1_ack_i3 */
  {0xB932D2B9u, 625u}, /* life_alert_e4_s0_rest_hold */
  {0xB9366549u, 47u}, /* life_warm_e7_s0_rest_hold */
  {0xB9891B06u, 14u}, /* expression_curious_v0_0_hold */
  {0xB98F8AC3u, 949u}, /* tap_edge_playful_curious_right_accent */
  {0xB9A01974u, 5u}, /* life_calm_e24_s0_rest_hold */
  {0xB9A5AF26u, 634u}, /* life_alert_e2_s2_notice_left_accent */
  {0xB9C46D7Cu, 864u}, /* menu_ui_en_s3_o0_normal */
  {0xB9D2F326u, 91u}, /* life_thoughtful_e5_s0_rest_hold */
  {0xB9EB79DDu, 627u}, /* life_alert_e1_s1_listen_up_anticipate */
  {0xB9F5212Au, 487u}, /* life_warm_e15_s2_listen_up_accent */
  {0xB9FE4162u, 973u}, /* tap_edge_thoughtful_calm_right_follow */
  {0xBA157A64u, 900u}, /* menu_ui_en_s8_o1_ack_i4 */
  {0xBA2A2BC3u, 991u}, /* tap_edge_delighted_warm_up_orient */
  {0xBA38AEB9u, 359u}, /* life_curious_e22_s0_rest_hold */
  {0xBA3A080Fu, 631u}, /* life_alert_e2_s0_rest_hold */
  {0xBA4A1534u, 33u}, /* life_delighted_e18_s3_beam_settle */
  {0xBA4E25BAu, 983u}, /* tap_edge_alert_focused_center_accent */
  {0xBA82B6F6u, 972u}, /* tap_edge_delighted_calm_center_accent */
  {0xBA9C2E92u, 1032u}, /* tap_edge_bashful_warm_right_anticipate */
  {0xBAB32108u, 1004u}, /* tap_edge_warm_delighted_up_anticipate */
  {0xBAD183AFu, 91u}, /* life_thoughtful_e13_s0_rest_hold */
  {0xBAEDA358u, 724u}, /* menu_ui_zh_cn_s0_o1_ack_i1 */
  {0xBB039926u, 979u}, /* tap_edge_warm_playful_center_settle */
  {0xBB08CF73u, 173u}, /* life_calm_e14_s2_listen_up_accent */
  {0xBB312087u, 138u}, /* menu_progress_0_5 */
  {0xBB3FE40Fu, 363u}, /* life_curious_e24_s0_rest_hold */
  {0xBB6B21EBu, 752u}, /* menu_ui_zh_cn_s1_o2_normal */
  {0xBB77A674u, 1062u}, /* tap_edge_focused_thoughtful_left_anticipate */
  {0xBBAC3166u, 119u}, /* life_alert_e7_s0_rest_hold */
  {0xBBF60BE0u, 804u}, /* menu_ui_zh_cn_s9_o1_normal */
  {0xBC0B94C2u, 983u}, /* tap_edge_thoughtful_focused_center_accent */
  {0xBC40C863u, 575u}, /* life_thoughtful_e26_s1_ponder_anticipate */
  {0xBC42E30Bu, 995u}, /* tap_edge_delighted_playful_right_anticipate */
  {0xBC51D45Fu, 463u}, /* life_warm_e1_s0_rest_hold */
  {0xBC6ADE4Fu, 1035u}, /* tap_edge_bashful_warm_down_orient */
  {0xBC9B9C3Fu, 562u}, /* life_thoughtful_e22_s0_notice_left_orient */
  {0xBC9EB139u, 615u}, /* life_thoughtful_e29_s1_listen_up_anticipate */
  {0xBCAA96C0u, 51u}, /* expression_warm_v0_1_follow */
  {0xBCB20D66u, 356u}, /* life_curious_e21_s0_rest_hold */
  {0xBCBE7CA8u, 953u}, /* tap_transition_center_e1_anticipate */
  {0xBCC5A501u, 952u}, /* tap_edge_curious_warm_center_orient */
  {0xBCC8C198u, 1005u}, /* tap_edge_playful_delighted_up_accent */
  {0xBCEDA67Eu, 726u}, /* menu_ui_zh_cn_s0_o1_ack_i3 */
  {0xBCF15566u, 718u}, /* menu_ui_zh_cn_s0_o0_normal */
  {0xBCF21AECu, 603u}, /* life_thoughtful_e21_s2_notice_right_accent */
  {0xBD174DDBu, 951u}, /* tap_transition_right_e0_settle */
  {0xBD20BF5Fu, 69u}, /* expression_playful_v0_2_follow */
  {0xBD2745C9u, 564u}, /* life_thoughtful_e7_s3_notice_left_follow */
  {0xBD30D6E7u, 1012u}, /* tap_edge_playful_delighted_center_orient */
  {0xBD539814u, 200u}, /* life_calm_e12_s3_notice_left_follow */
  {0xBD60392Eu, 449u}, /* tap_edge_playful_delighted_down_settle */
  {0xBD986992u, 393u}, /* life_delighted_e27_s3_soften_settle */
  {0xBDA3B3CCu, 196u}, /* life_calm_e11_s3_notice_right_follow */
  {0xBDD16A65u, 1060u}, /* tap_edge_focused_thoughtful_left_orient */
  {0xBDD22388u, 969u}, /* tap_edge_calm_sleepy_up_accent */
  {0xBDE79B12u, 121u}, /* expression_alert_v0_1_anticipate */
  {0xBDEDA811u, 725u}, /* menu_ui_zh_cn_s0_o1_ack_i2 */
  {0xBE16F27Au, 950u}, /* tap_edge_bashful_curious_down_follow */
  {0xBE3075BAu, 951u}, /* tap_transition_left_e0_settle */
  {0xBE430ADFu, 104u}, /* expression_focused_v2_0_follow */
  {0xBE4C8895u, 33u}, /* life_delighted_e12_s4_notice_right_settle */
  {0xBE6E5787u, 1026u}, /* tap_edge_sleepy_warm_left_orient */
  {0xBE7B7A33u, 975u}, /* tap_edge_curious_warm_down_anticipate */
  {0xBE7D6AD7u, 637u}, /* life_alert_e3_s0_notice_right_orient */
  {0xBE8143A9u, 117u}, /* expression_alert_v0_0_accent */
  {0xBEA69A45u, 119u}, /* life_alert_e14_s4_notice_right_settle */
  {0xBEA6C590u, 654u}, /* life_alert_e24_s1_notice_right_anticipate */
  {0xBEDC7E89u, 1027u}, /* tap_edge_sleepy_calm_right_anticipate */
  {0xBEDE4783u, 648u}, /* life_alert_e8_s4_notice_left_settle */
  {0xBEE1245Eu, 656u}, /* life_alert_e7_s3_notice_right_follow */
  {0xBF323E40u, 33u}, /* life_delighted_e21_s3_soften_settle */
  {0xBF478B53u, 973u}, /* tap_edge_bashful_calm_right_settle */
  {0xBF5558E6u, 758u}, /* menu_ui_zh_cn_s1_o3_ack_i4 */
  {0xBF680AD1u, 1026u}, /* tap_edge_sleepy_calm_up_orient */
  {0xBF6BB9A5u, 682u}, /* life_alert_e31_s0_rest_hold */
  {0xBF938598u, 193u}, /* life_calm_e10_s0_small_breath_anticipate */
  {0xBF987133u, 482u}, /* life_warm_e5_s1_notice_left_anticipate */
  {0xBF9FB112u, 956u}, /* tap_transition_down_e1_settle */
  {0xBFA9CC74u, 582u}, /* life_thoughtful_e24_s0_notice_right_orient */
  {0xBFEDAB37u, 727u}, /* menu_ui_zh_cn_s0_o1_ack_i4 */
  {0xBFF094ECu, 972u}, /* tap_edge_curious_calm_left_accent */
  {0xBFFA67FEu, 988u}, /* tap_edge_curious_alert_left_follow */
  {0xC0163D11u, 489u}, /* life_warm_e26_s0_notice_right_orient */
  {0xC0378402u, 637u}, /* tap_local_alert_right */
  {0xC039A279u, 673u}, /* life_alert_e13_s3_listen_up_follow */
  {0xC05DD0F9u, 934u}, /* tap_local_playful_right */
  {0xC06AA0C6u, 973u}, /* tap_edge_warm_calm_up_settle */
  {0xC087FFDFu, 307u}, /* life_curious_e28_s1_question_anticipate */
  {0xC08AECD7u, 126u}, /* expression_alert_v0_2_accent */
  {0xC0B09B04u, 951u}, /* tap_edge_playful_curious_down_settle */
  {0xC0ECBC25u, 1047u}, /* tap_edge_thoughtful_alert_right_orient */
  {0xC0EDB5D6u, 1059u}, /* tap_edge_focused_thoughtful_down_orient */
  {0xC10E198Fu, 1002u}, /* tap_edge_warm_bashful_right_orient */
  {0xC11BE9D2u, 949u}, /* tap_edge_playful_curious_up_accent */
  {0xC1245BB5u, 1006u}, /* tap_edge_warm_delighted_left_follow */
  {0xC13552FFu, 973u}, /* tap_edge_warm_calm_down_follow */
  {0xC182E42Eu, 479u}, /* life_warm_e4_s3_notice_right_follow */
  {0xC1CA8B00u, 114u}, /* tap_edge_thoughtful_alert_up_settle */
  {0xC1F5752Eu, 1059u}, /* tap_edge_focused_curious_down_orient */
  {0xC23EB503u, 597u}, /* life_thoughtful_e21_s1_notice_right_anticipate */
  {0xC2555D9Fu, 757u}, /* menu_ui_zh_cn_s1_o3_ack_i3 */
  {0xC262752Au, 67u}, /* expression_playful_v0_2_anticipate */
  {0xC27C6F47u, 462u}, /* life_warm_e8_s2_soften_follow */
  {0xC297B692u, 951u}, /* tap_edge_calm_curious_right_settle */
  {0xC299F842u, 959u}, /* tap_edge_curious_playful_down_orient */
  {0xC2A9F541u, 807u}, /* menu_ui_zh_cn_s9_o2_ack_i2 */
  {0xC2AD98A0u, 403u}, /* life_delighted_e21_s0_rest_hold */
  {0xC2DA89E4u, 1002u}, /* tap_edge_warm_delighted_right_orient */
  {0xC2E2EE8Cu, 973u}, /* tap_edge_bashful_calm_left_settle */
  {0xC2F69DA1u, 984u}, /* tap_edge_thoughtful_focused_left_follow */
  {0xC312E69Du, 951u}, /* tap_edge_warm_curious_up_settle */
  {0xC34D5789u, 412u}, /* life_delighted_e20_s1_notice_left_anticipate */
  {0xC35F3DADu, 1044u}, /* tap_edge_thoughtful_focused_up_orient */
  {0xC3BD85F0u, 177u}, /* life_calm_e6_s0_soften_anticipate */
  {0xC3CE8E65u, 92u}, /* expression_thoughtful_v0_1_orient */
  {0xC3EC5DF6u, 605u}, /* life_thoughtful_e23_s0_rest_hold */
  {0xC433FCE8u, 455u}, /* life_delighted_e28_s2_notice_left_accent */
  {0xC47AB747u, 973u}, /* tap_edge_playful_calm_down_settle */
  {0xC4BD2D11u, 932u}, /* tap_local_playful_down */
  {0xC4D2AD54u, 19u}, /* life_curious_e9_s0_rest_hold */
  {0xC51102F9u, 88u}, /* expression_thoughtful_v0_0_anticipate */
  {0xC512A689u, 967u}, /* tap_edge_delighted_warm_up_settle */
  {0xC53293C2u, 584u}, /* life_thoughtful_e12_s0_rest_hold */
  {0xC547AC63u, 972u}, /* tap_edge_curious_calm_down_accent */
  {0xC54D5306u, 629u}, /* life_alert_e9_s3_listen_up_follow */
  {0xC55A3647u, 951u}, /* tap_edge_bashful_curious_up_settle */
  {0xC57E56DBu, 1009u}, /* tap_edge_warm_bashful_up_accent */
  {0xC5A0F7B9u, 13u}, /* expression_calm_v0_2_follow */
  {0xC5A5F57Cu, 986u}, /* tap_edge_curious_alert_down_anticipate */
  {0xC5A94317u, 686u}, /* life_alert_e18_s0_notice_right_orient */
  {0xC5B56B80u, 950u}, /* tap_transition_up_e0_follow */
  {0xC5E7EF19u, 979u}, /* tap_edge_warm_playful_right_settle */
  {0xC605F9D9u, 268u}, /* life_calm_e29_s2_notice_right_accent */
  {0xC65C937Fu, 626u}, /* life_alert_e5_s0_startle_orient */
  {0xC662B0C2u, 0u}, /* expression_calm_v0_1_hold */
  {0xC6A9F46Bu, 19u}, /* life_curious_e23_s4_notice_right_settle */
  {0xC6C6706Fu, 592u}, /* life_thoughtful_e18_s4_notice_right_settle */
  {0xC6E3B339u, 821u}, /* menu_ui_en_s0_o0_normal */
  {0xC6EBAD8Eu, 967u}, /* tap_edge_bashful_warm_left_settle */
  {0xC7052153u, 1029u}, /* tap_edge_sleepy_warm_right_anticipate */
  {0xC71EA46Au, 812u}, /* menu_ui_zh_cn_s10_o1_normal */
  {0xC7286A78u, 91u}, /* life_thoughtful_e10_s4_notice_left_settle */
  {0xC7909A63u, 197u}, /* life_calm_e12_s0_rest_hold */
  {0xC79F9666u, 689u}, /* life_alert_e19_s2_notice_left_accent */
  {0xC7ADED9Cu, 367u}, /* life_curious_e25_s1_notice_left_anticipate */
  {0xC7DA2E27u, 979u}, /* tap_edge_curious_playful_center_settle */
  {0xC828C510u, 1070u}, /* tap_edge_alert_focused_right_orient */
  {0xC8537D85u, 205u}, /* life_calm_e14_s0_rest_hold */
  {0xC85B2C92u, 1051u}, /* tap_edge_thoughtful_calm_center_anticipate */
  {0xC88BFC33u, 604u}, /* life_thoughtful_e22_s0_rest_hold */
  {0xC895B7F5u, 33u}, /* life_delighted_e9_s4_notice_right_settle */
  {0xC8B246ADu, 413u}, /* life_delighted_e7_s3_notice_left_follow */
  {0xC8C0190Fu, 973u}, /* tap_edge_sleepy_calm_up_settle */
  {0xC8E288CFu, 1003u}, /* tap_edge_warm_curious_right_anticipate */
  {0xC8FFAC81u, 967u}, /* tap_edge_playful_warm_down_settle */
  {0xC938CB1Eu, 293u}, /* life_curious_e19_s3_question_settle */
  {0xC940F0E9u, 91u}, /* life_thoughtful_e4_s4_notice_left_settle */
  {0xC95E837Du, 568u}, /* life_thoughtful_e18_s0_notice_right_orient */
  {0xC967E5FBu, 592u}, /* life_thoughtful_e29_s4_listen_up_settle */
  {0xC96B43F8u, 950u}, /* tap_edge_warm_curious_down_follow */
  {0xC9888B58u, 598u}, /* life_thoughtful_e19_s2_notice_left_accent */
  {0xC99CC5C6u, 967u}, /* tap_edge_sleepy_warm_down_settle */
  {0xC9A8DB05u, 973u}, /* tap_edge_thoughtful_calm_center_settle */
  {0xC9BD973Au, 640u}, /* life_alert_e3_s3_notice_right_follow */
  {0xC9C48B82u, 1072u}, /* tap_edge_alert_calm_left_anticipate */
  {0xC9C7D813u, 386u}, /* life_delighted_e12_s0_notice_right_orient */
  {0xC9F978A5u, 949u}, /* tap_edge_alert_curious_left_accent */
  {0xCA0F0749u, 973u}, /* tap_edge_curious_calm_up_settle */
  {0xCA1771A5u, 146u}, /* life_calm_e0_s0_notice_right_orient */
  {0xCA199300u, 957u}, /* tap_edge_calm_warm_up_orient */
  {0xCA526DBAu, 979u}, /* tap_edge_warm_playful_up_settle */
  {0xCA569780u, 779u}, /* menu_ui_zh_cn_s4_o0_ack_i2 */
  {0xCA67BAA1u, 1007u}, /* tap_edge_warm_playful_up_anticipate */
  {0xCA6DE535u, 28u}, /* expression_delighted_v0_1_hold */
  {0xCA70F17Bu, 548u}, /* life_thoughtful_e1_s1_listen_up_anticipate */
  {0xCA78CCBCu, 970u}, /* tap_edge_calm_sleepy_down_follow */
  {0xCA8B7E24u, 936u}, /* tap_local_sleepy_right */
  {0xCA9511D4u, 965u}, /* tap_edge_delighted_warm_center_accent */
  {0xCAC43DE6u, 954u}, /* tap_transition_center_e1_accent */
  {0xCAF5E092u, 968u}, /* tap_edge_calm_sleepy_center_anticipate */
  {0xCB0B7A8Au, 47u}, /* life_warm_e19_s0_rest_hold */
  {0xCB2C57D1u, 950u}, /* tap_transition_right_e0_follow */
  {0xCB32EF48u, 973u}, /* tap_edge_delighted_calm_down_settle */
  {0xCB38BCC4u, 981u}, /* tap_edge_curious_thoughtful_left_follow */
  {0xCB4CB4CDu, 278u}, /* life_curious_e25_s2_notice_left_accent */
  {0xCB569913u, 780u}, /* menu_ui_zh_cn_s4_o0_ack_i3 */
  {0xCB595901u, 158u}, /* life_calm_e2_s1_soften_accent */
  {0xCB5A67D9u, 980u}, /* tap_edge_curious_thoughtful_center_anticipate */
  {0xCB9C5929u, 291u}, /* life_curious_e3_s2_notice_left_accent */
  {0xCB9EB70Au, 47u}, /* expression_warm_v0_1_settle */
  {0xCBAA59D2u, 978u}, /* tap_edge_delighted_playful_right_follow */
  {0xCBB298FEu, 289u}, /* life_curious_e10_s0_rest_hold */
  {0xCBB3E6C3u, 640u}, /* life_alert_e11_s3_notice_right_follow */
  {0xCBF3AD6Au, 1072u}, /* tap_edge_alert_calm_center_anticipate */
  {0xCBF4DF1Au, 556u}, /* life_thoughtful_e6_s4_notice_right_settle */
  {0xCBF52BD0u, 29u}, /* expression_delighted_v0_0_orient */
  {0xCBF80B2Du, 657u}, /* life_alert_e8_s0_rest_hold */
  {0xCC09FF1Au, 971u}, /* tap_edge_curious_calm_center_anticipate */
  {0xCC18DDCEu, 70u}, /* expression_sleepy_v0_0_orient */
  {0xCC193736u, 717u}, /* life_alert_e31_s1_listen_up_anticipate */
  {0xCC2971B6u, 190u}, /* life_calm_e9_s3_notice_left_follow */
  {0xCC3888BBu, 575u}, /* life_thoughtful_e8_s1_ponder_anticipate */
  {0xCC3A7CFDu, 290u}, /* life_curious_e13_s0_notice_left_orient */
  {0xCC4AB51Cu, 972u}, /* tap_edge_alert_calm_left_accent */
  {0xCC569AA6u, 777u}, /* menu_ui_zh_cn_s4_o0_ack_i0 */
  {0xCC64E4A9u, 47u}, /* life_warm_e11_s4_listen_up_settle */
  {0xCC9FF835u, 908u}, /* menu_ui_en_s9_o1_ack_i2 */
  {0xCCD7F1F2u, 570u}, /* life_thoughtful_e30_s3_notice_right_follow */
  {0xCCE8797Bu, 621u}, /* life_thoughtful_e31_s1_ponder_anticipate */
  {0xCD13E21Cu, 36u}, /* expression_delighted_v2_1_accent */
  {0xCD2EEC9Eu, 19u}, /* expression_curious_v0_2_settle */
  {0xCD569C39u, 778u}, /* menu_ui_zh_cn_s4_o0_ack_i1 */
  {0xCD7A2E01u, 19u}, /* life_curious_e14_s4_notice_right_settle */
  {0xCD9C0D7Du, 1032u}, /* tap_edge_bashful_warm_left_anticipate */
  {0xCDF40F3Fu, 19u}, /* life_curious_e5_s4_notice_right_settle */
  {0xCE07DDFBu, 1021u}, /* tap_edge_playful_warm_down_orient */
  {0xCE1FD2F3u, 191u}, /* life_calm_e9_s4_notice_left_settle */
  {0xCE56F0E8u, 895u}, /* menu_ui_en_s8_o0_ack_i3 */
  {0xCE71FFE8u, 73u}, /* expression_bashful_v1_0_orient */
  {0xCE9FC67Du, 435u}, /* life_delighted_e23_s2_notice_left_accent */
  {0xCEA1A68Bu, 969u}, /* tap_edge_calm_sleepy_down_accent */
  {0xCEAF32A4u, 194u}, /* life_calm_e11_s0_rest_hold */
  {0xCEB7C183u, 28u}, /* expression_delighted_v2_1_hold */
  {0xCECFFB7Fu, 1024u}, /* tap_edge_playful_curious_down_anticipate */
  {0xCEDCADF9u, 973u}, /* tap_edge_bashful_calm_right_follow */
  {0xCF0BF1A1u, 78u}, /* expression_bashful_v1_1_orient */
  {0xCF0D023Fu, 493u}, /* life_warm_e16_s0_soften_anticipate */
  {0xCF1523B1u, 673u}, /* life_alert_e31_s3_listen_up_follow */
  {0xCF3E2F2Du, 950u}, /* tap_edge_bashful_curious_center_follow */
  {0xCF56F27Bu, 894u}, /* menu_ui_en_s8_o0_ack_i2 */
  {0xCF7023CAu, 1008u}, /* tap_edge_warm_bashful_right_anticipate */
  {0xCF78F277u, 1000u}, /* tap_edge_warm_bashful_down_orient */
  {0xCF824F02u, 983u}, /* tap_edge_alert_focused_left_accent */
  {0xCF8F55AAu, 169u}, /* life_calm_e17_s4_notice_left_settle */
  {0xCF9CE3C2u, 389u}, /* life_delighted_e16_s3_notice_right_follow */
  {0xCFA048CFu, 47u}, /* life_warm_e2_s4_listen_up_settle */
  {0xCFAADC52u, 958u}, /* tap_edge_calm_curious_down_orient */
  {0xCFD22D6Fu, 339u}, /* life_curious_e31_s2_listen_up_accent */
  {0xD0173112u, 61u}, /* expression_playful_v0_1_settle */
  {0xD036E299u, 769u}, /* menu_ui_zh_cn_s3_o2_normal */
  {0xD044AB45u, 950u}, /* tap_edge_calm_curious_center_follow */
  {0xD056F40Eu, 893u}, /* menu_ui_en_s8_o0_ack_i1 */
  {0xD0717B80u, 965u}, /* tap_edge_delighted_warm_up_accent */
  {0xD09746E1u, 654u}, /* life_alert_e7_s1_notice_right_anticipate */
  {0xD09906DDu, 556u}, /* life_thoughtful_e16_s4_listen_up_settle */
  {0xD09F0AABu, 985u}, /* tap_edge_curious_focused_up_settle */
  {0xD0CDC361u, 859u}, /* menu_ui_en_s1_o3_normal */
  {0xD0CFEAA7u, 958u}, /* tap_edge_calm_warm_down_orient */
  {0xD0DFE6D2u, 973u}, /* tap_edge_focused_calm_left_follow */
  {0xD0E146BFu, 966u}, /* tap_edge_bashful_warm_down_follow */
  {0xD101DA32u, 983u}, /* tap_edge_thoughtful_focused_up_accent */
  {0xD12772CBu, 985u}, /* tap_edge_curious_focused_center_settle */
  {0xD172E93Fu, 1062u}, /* tap_edge_focused_thoughtful_down_anticipate */
  {0xD1833EEBu, 1052u}, /* tap_edge_thoughtful_calm_up_orient */
  {0xD186ADC0u, 119u}, /* life_alert_e12_s4_notice_left_settle */
  {0xD1932D6Eu, 514u}, /* life_warm_e25_s2_soften_follow */
  {0xD1A11547u, 147u}, /* life_calm_e8_s1_notice_right_anticipate */
  {0xD1A59E0Au, 19u}, /* life_curious_e15_s3_question_settle */
  {0xD1C5F67Du, 47u}, /* life_warm_e1_s4_notice_left_settle */
  {0xD1C605E5u, 581u}, /* life_thoughtful_e11_s0_rest_hold */
  {0xD1D3E5A5u, 966u}, /* tap_edge_curious_warm_left_follow */
  {0xD1D47CD9u, 630u}, /* life_alert_e22_s3_startle_settle */
  {0xD1DCBFC3u, 579u}, /* life_thoughtful_e17_s1_notice_left_anticipate */
  {0xD1E1606Du, 119u}, /* life_alert_e25_s4_listen_up_settle */
  {0xD213BD5Cu, 917u}, /* menu_ui_en_s10_o1_processing_i3 */
  {0xD214C921u, 0u}, /* expression_calm_v0_2_hold */
  {0xD22C78E4u, 564u}, /* life_thoughtful_e22_s3_notice_left_follow */
  {0xD27B1A69u, 324u}, /* life_curious_e24_s0_question_orient */
  {0xD282E2B0u, 78u}, /* expression_bashful_v0_1_orient */
  {0xD287F714u, 100u}, /* expression_focused_v0_1_hold */
  {0xD28E8554u, 258u}, /* life_calm_e26_s3_listen_up_follow */
  {0xD29758BFu, 261u}, /* life_calm_e27_s1_small_breath_accent */
  {0xD2A9591Eu, 446u}, /* life_delighted_e22_s0_notice_right_orient */
  {0xD2BF6E7Bu, 402u}, /* life_delighted_e4_s3_notice_right_follow */
  {0xD2C0AF4Du, 91u}, /* life_thoughtful_e13_s4_notice_left_settle */
  {0xD2C4356Fu, 585u}, /* life_thoughtful_e16_s1_listen_up_anticipate */
  {0xD2C5523Eu, 70u}, /* tap_edge_calm_sleepy_down_settle */
  {0xD31BE57Fu, 481u}, /* life_warm_e5_s0_notice_left_orient */
  {0xD32D4980u, 973u}, /* tap_edge_playful_calm_left_settle */
  {0xD3386BD9u, 988u}, /* tap_edge_curious_alert_down_follow */
  {0xD3409257u, 901u}, /* menu_ui_en_s8_o2_normal */
  {0xD38398E8u, 973u}, /* tap_edge_thoughtful_calm_right_settle */
  {0xD3BF26A0u, 1071u}, /* tap_edge_alert_curious_right_anticipate */
  {0xD3D37498u, 47u}, /* life_warm_e10_s4_notice_right_settle */
  {0xD3E3715Cu, 400u}, /* life_delighted_e4_s1_notice_right_anticipate */
  {0xD3E638C5u, 1005u}, /* tap_edge_warm_delighted_down_accent */
  {0xD3F46CFCu, 963u}, /* tap_edge_curious_playful_right_orient */
  {0xD4152416u, 648u}, /* life_alert_e6_s4_listen_up_settle */
  {0xD4156A3Bu, 255u}, /* life_calm_e26_s0_listen_up_orient */
  {0xD428B2D3u, 181u}, /* life_calm_e7_s0_rest_hold */
  {0xD47E8C5Fu, 548u}, /* life_thoughtful_e23_s1_listen_up_anticipate */
  {0xD48B2B96u, 910u}, /* menu_ui_en_s9_o2_ack_i2 */
  {0xD4C46E95u, 987u}, /* tap_edge_thoughtful_alert_up_accent */
  {0xD4F10834u, 592u}, /* life_thoughtful_e21_s0_rest_hold */
  {0xD4FEDA93u, 966u}, /* tap_edge_delighted_warm_up_follow */
  {0xD51AA142u, 974u}, /* tap_edge_curious_alert_up_orient */
  {0xD52382EFu, 66u}, /* expression_playful_v0_2_orient */
  {0xD54C37B3u, 977u}, /* tap_edge_warm_playful_center_accent */
  {0xD56B9AECu, 1024u}, /* tap_edge_playful_curious_center_anticipate */
  {0xD5774B8Au, 563u}, /* life_thoughtful_e4_s2_notice_left_accent */
  {0xD597C213u, 951u}, /* tap_edge_playful_curious_up_settle */
  {0xD598947Au, 1031u}, /* tap_edge_bashful_calm_center_orient */
  {0xD5D316C4u, 72u}, /* expression_bashful_v1_0_hold */
  {0xD5E057D3u, 687u}, /* life_alert_e19_s0_notice_left_orient */
  {0xD5EC86DDu, 972u}, /* tap_edge_thoughtful_calm_right_accent */
  {0xD6150989u, 949u}, /* tap_edge_alert_curious_center_accent */
  {0xD645CE6Fu, 101u}, /* expression_focused_v2_0_orient */
  {0xD65AA6ACu, 972u}, /* tap_edge_warm_calm_right_accent */
  {0xD66348FAu, 966u}, /* tap_edge_delighted_warm_right_follow */
  {0xD664D6E4u, 1049u}, /* tap_edge_thoughtful_alert_down_anticipate */
  {0xD66F02F7u, 150u}, /* life_calm_e0_s4_notice_right_settle */
  {0xD68C8CBFu, 977u}, /* tap_edge_curious_playful_right_accent */
  {0xD696F89Du, 654u}, /* life_alert_e21_s1_notice_right_anticipate */
  {0xD69D72D6u, 453u}, /* life_delighted_e27_s0_rest_hold */
  {0xD6BFA812u, 2u}, /* expression_calm_v0_0_anticipate */
  {0xD70AC412u, 1041u}, /* tap_edge_bashful_calm_right_accent */
  {0xD70BA74Fu, 91u}, /* life_thoughtful_e28_s4_notice_left_settle */
  {0xD71A1010u, 56u}, /* expression_playful_v0_1_hold */
  {0xD73C5BE8u, 33u}, /* life_delighted_e14_s3_beam_settle */
  {0xD7418081u, 125u}, /* expression_alert_v0_2_anticipate */
  {0xD74F2A38u, 661u}, /* life_alert_e9_s2_listen_up_accent */
  {0xD757E3B9u, 988u}, /* tap_edge_curious_alert_right_follow */
  {0xD75EFA77u, 970u}, /* tap_edge_calm_sleepy_center_follow */
  {0xD7725C37u, 993u}, /* tap_edge_delighted_warm_left_orient */
  {0xD7A8A3AAu, 420u}, /* life_delighted_e9_s2_notice_right_accent */
  {0xD812374Fu, 973u}, /* tap_edge_curious_calm_center_follow */
  {0xD81E713Au, 1035u}, /* tap_edge_bashful_curious_down_orient */
  {0xD871CAA8u, 973u}, /* tap_edge_sleepy_calm_right_follow */
  {0xD881869Bu, 948u}, /* tap_edge_calm_curious_down_anticipate */
  {0xD8A3B6FBu, 319u}, /* life_curious_e10_s3_notice_left_follow */
  {0xD8D32E02u, 967u}, /* tap_edge_playful_warm_up_settle */
  {0xD8D58199u, 984u}, /* tap_edge_curious_focused_left_follow */
  {0xD8D780F8u, 1017u}, /* tap_edge_playful_curious_right_orient */
  {0xD8E497F3u, 351u}, /* life_curious_e19_s0_rest_hold */
  {0xD8F56152u, 872u}, /* menu_ui_en_s3_o2_normal */
  {0xD92B1676u, 47u}, /* life_warm_e0_s3_soften_settle */
  {0xD92E74B9u, 875u}, /* menu_ui_en_s3_o2_processing_i5 */
  {0xD96E0402u, 151u}, /* life_calm_e31_s0_rest_hold */
  {0xD979278Bu, 951u}, /* tap_transition_down_e0_settle */
  {0xD982816Au, 1029u}, /* tap_edge_sleepy_warm_center_anticipate */
  {0xD9938474u, 1001u}, /* tap_edge_warm_playful_left_orient */
  {0xD99F2C4Bu, 592u}, /* life_thoughtful_e14_s4_notice_right_settle */
  {0xD9A8F78Bu, 500u}, /* life_warm_e10_s3_notice_right_follow */
  {0xD9CD231Cu, 984u}, /* tap_edge_curious_focused_right_follow */
  {0xD9D4EC71u, 943u}, /* tap_local_focused_down */
  {0xD9E6347Au, 86u}, /* expression_thoughtful_v0_2_hold */
  {0xD9FCCE53u, 973u}, /* tap_edge_curious_calm_up_follow */
  {0xD9FFDCF3u, 33u}, /* life_delighted_e13_s3_soften_settle */
  {0xDA09E8D0u, 1015u}, /* tap_edge_playful_delighted_down_orient */
  {0xDA2E764Cu, 873u}, /* menu_ui_en_s3_o2_processing_i2 */
  {0xDA5B18FDu, 1012u}, /* tap_edge_playful_curious_center_orient */
  {0xDA64BFF8u, 348u}, /* life_curious_e21_s1_notice_left_anticipate */
  {0xDA6F0ED7u, 967u}, /* tap_edge_curious_warm_left_settle */
  {0xDA6F5422u, 319u}, /* life_curious_e13_s3_notice_left_follow */
  {0xDAD6E1E7u, 973u}, /* tap_edge_alert_calm_left_follow */
  {0xDB4E5F3Bu, 556u}, /* life_thoughtful_e21_s4_notice_right_settle */
  {0xDB64EEF2u, 987u}, /* tap_edge_curious_alert_down_accent */
  {0xDB7571F9u, 972u}, /* tap_edge_playful_calm_up_accent */
  {0xDB77F5DBu, 335u}, /* life_curious_e15_s1_question_anticipate */
  {0xDB832DE5u, 647u}, /* life_alert_e16_s2_startle_follow */
  {0xDB898F05u, 33u}, /* life_delighted_e24_s3_soften_settle */
  {0xDB95CD96u, 639u}, /* life_alert_e21_s2_notice_right_accent */
  {0xDBA00EE7u, 37u}, /* expression_delighted_v2_1_follow */
  {0xDBAF36CFu, 1025u}, /* tap_edge_playful_calm_up_anticipate */
  {0xDBE98DC7u, 40u}, /* expression_delighted_v2_2_accent */
  {0xDC057644u, 1033u}, /* tap_edge_bashful_warm_down_accent */
  {0xDC8A056Eu, 979u}, /* tap_edge_delighted_playful_down_settle */
  {0xDC9C9236u, 466u}, /* life_warm_e1_s2_notice_left_accent */
  {0xDCC4D384u, 5u}, /* expression_calm_v0_1_settle */
  {0xDCD8AE9Du, 0u}, /* life_calm_e9_s0_rest_hold */
  {0xDD0725CDu, 91u}, /* life_thoughtful_e19_s0_rest_hold */
  {0xDD0FDC03u, 458u}, /* life_delighted_e31_s0_rest_hold */
  {0xDD1649DCu, 148u}, /* life_calm_e11_s2_notice_right_accent */
  {0xDD5269F6u, 105u}, /* expression_focused_v0_1_settle */
  {0xDD5D5C6Bu, 272u}, /* life_calm_e31_s0_small_breath_anticipate */
  {0xDD88F512u, 971u}, /* tap_edge_curious_calm_left_anticipate */
  {0xDD8DD902u, 877u}, /* menu_ui_en_s3_o3_ack_i3 */
  {0xDDD2DDF0u, 625u}, /* life_alert_e1_s0_rest_hold */
  {0xDDD8414Du, 91u}, /* life_thoughtful_e23_s4_listen_up_settle */
  {0xDDF5FCEBu, 983u}, /* tap_edge_curious_focused_right_accent */
  {0xDDFE0C86u, 967u}, /* tap_edge_bashful_warm_up_settle */
  {0xDE07B3B0u, 731u}, /* menu_ui_zh_cn_s0_o2_ack_i4 */
  {0xDE2E4C18u, 602u}, /* life_thoughtful_e31_s2_ponder_accent */
  {0xDE4AB6ADu, 638u}, /* life_alert_e3_s1_notice_right_anticipate */
  {0xDE5C6736u, 517u}, /* life_warm_e18_s0_notice_right_orient */
  {0xDE8DE75Cu, 47u}, /* life_warm_e26_s0_rest_hold */
  {0xDE982D6Fu, 634u}, /* life_alert_e12_s2_notice_left_accent */
  {0xDEAD49C1u, 545u}, /* life_thoughtful_e9_s4_listen_up_settle */
  {0xDEB3BD5Bu, 985u}, /* tap_edge_alert_focused_up_settle */
  {0xDEC83EA2u, 144u}, /* menu_hold_2500ms */
  {0xDECB5ACAu, 545u}, /* life_thoughtful_e26_s3_ponder_settle */
  {0xDED8B9F0u, 320u}, /* life_curious_e27_s0_rest_hold */
  {0xDEF0817Eu, 972u}, /* tap_edge_delighted_calm_up_accent */
  {0xDEF29FF4u, 616u}, /* life_thoughtful_e29_s2_listen_up_accent */
  {0xDF07B543u, 732u}, /* menu_ui_zh_cn_s0_o2_ack_i5 */
  {0xDF092378u, 973u}, /* tap_edge_bashful_calm_up_settle */
  {0xDF1277CDu, 980u}, /* tap_edge_curious_thoughtful_up_anticipate */
  {0xDF28EEC2u, 45u}, /* expression_warm_v0_0_accent */
  {0xDF416E66u, 19u}, /* life_curious_e21_s4_notice_left_settle */
  {0xDF7580F8u, 801u}, /* menu_ui_zh_cn_s8_o2_ack_i4 */
  {0xDF80C000u, 47u}, /* life_warm_e18_s4_notice_right_settle */
  {0xDFCCFBEFu, 114u}, /* tap_edge_focused_alert_center_settle */
  {0xE00E0C6Au, 968u}, /* tap_edge_calm_sleepy_left_anticipate */
  {0xE038BDF2u, 225u}, /* life_calm_e18_s1_notice_right_anticipate */
  {0xE04254A7u, 1040u}, /* tap_edge_bashful_calm_left_anticipate */
  {0xE0622347u, 1033u}, /* tap_edge_bashful_warm_center_accent */
  {0xE093C288u, 687u}, /* life_alert_e29_s0_notice_left_orient */
  {0xE0A20325u, 987u}, /* tap_edge_curious_alert_center_accent */
  {0xE0C58EC1u, 916u}, /* menu_ui_en_s10_o1_ack_i2 */
  {0xE0F2ACFEu, 286u}, /* life_curious_e4_s0_listen_up_orient */
  {0xE10FFCA9u, 231u}, /* life_calm_e19_s1_listen_up_anticipate */
  {0xE115F5FFu, 761u}, /* menu_ui_zh_cn_s3_o0_normal */
  {0xE16B3795u, 988u}, /* tap_edge_focused_alert_up_follow */
  {0xE19473CAu, 33u}, /* expression_delighted_v2_2_settle */
  {0xE1AE5C8Du, 310u}, /* tap_local_curious_up */
  {0xE1BD2144u, 322u}, /* life_curious_e19_s2_question_accent */
  {0xE1C1E293u, 406u}, /* life_delighted_e27_s2_soften_follow */
  {0xE1CE0401u, 981u}, /* tap_edge_focused_thoughtful_left_follow */
  {0xE1D040BBu, 768u}, /* menu_ui_zh_cn_s3_o1_ack_i3 */
  {0xE20B6291u, 541u}, /* life_thoughtful_e19_s0_notice_left_orient */
  {0xE2563C70u, 77u}, /* expression_bashful_v1_2_settle */
  {0xE264301Eu, 155u}, /* life_calm_e1_s3_small_breath_settle */
  {0xE28A0F68u, 1068u}, /* tap_edge_alert_calm_down_orient */
  {0xE28EAF7Eu, 984u}, /* tap_edge_alert_focused_down_follow */
  {0xE2A94B23u, 1071u}, /* tap_edge_alert_curious_left_anticipate */
  {0xE2BA9369u, 574u}, /* life_thoughtful_e26_s0_ponder_orient */
  {0xE2BCD105u, 927u}, /* tap_local_calm_right */
  {0xE2C61A3Au, 967u}, /* tap_edge_curious_warm_right_settle */
  {0xE2CA31DBu, 1006u}, /* tap_edge_playful_delighted_up_follow */
  {0xE2D6D0F3u, 521u}, /* life_warm_e24_s0_listen_up_orient */
  {0xE2D74396u, 949u}, /* tap_edge_calm_curious_center_accent */
  {0xE2DCEE7Cu, 203u}, /* life_calm_e13_s2_small_breath_follow */
  {0xE2E25E50u, 714u}, /* life_alert_e30_s0_rest_hold */
  {0xE2E4CB99u, 186u}, /* life_calm_e11_s0_notice_right_orient */
  {0xE2E59AB0u, 557u}, /* life_thoughtful_e3_s0_rest_hold */
  {0xE2F549B3u, 343u}, /* life_curious_e23_s1_notice_right_anticipate */
  {0xE30CE258u, 420u}, /* life_delighted_e29_s2_notice_right_accent */
  {0xE318B475u, 1029u}, /* tap_edge_sleepy_warm_down_anticipate */
  {0xE332C0A6u, 972u}, /* tap_edge_focused_calm_right_accent */
  {0xE37F1057u, 689u}, /* life_alert_e23_s2_notice_left_accent */
  {0xE39CB9BCu, 951u}, /* tap_edge_focused_curious_down_settle */
  {0xE3ADE045u, 971u}, /* tap_edge_curious_calm_down_anticipate */
  {0xE3D12D11u, 960u}, /* tap_edge_calm_curious_left_orient */
  {0xE3D393CBu, 970u}, /* tap_edge_calm_sleepy_up_follow */
  {0xE3F4E273u, 154u}, /* life_calm_e10_s2_small_breath_follow */
  {0xE407BD22u, 729u}, /* menu_ui_zh_cn_s0_o2_ack_i2 */
  {0xE41D1F23u, 447u}, /* life_delighted_e25_s1_notice_right_anticipate */
  {0xE45D8174u, 507u}, /* life_warm_e18_s1_notice_right_anticipate */
  {0xE46B7886u, 315u}, /* life_curious_e26_s1_notice_right_anticipate */
  {0xE47E5493u, 632u}, /* life_alert_e2_s0_notice_left_orient */
  {0xE4975D7Eu, 19u}, /* life_curious_e17_s4_notice_right_settle */
  {0xE4A2CDA0u, 948u}, /* tap_edge_calm_curious_up_anticipate */
  {0xE4CE5B0Eu, 77u}, /* expression_bashful_v0_1_settle */
  {0xE4E62BDBu, 935u}, /* tap_local_sleepy_left */
  {0xE4EE9026u, 197u}, /* life_calm_e13_s0_rest_hold */
  {0xE4FEC802u, 988u}, /* tap_edge_thoughtful_alert_center_follow */
  {0xE507BEB5u, 730u}, /* menu_ui_zh_cn_s0_o2_ack_i3 */
  {0xE529D2CAu, 949u}, /* tap_edge_playful_curious_left_accent */
  {0xE53C3F3Du, 973u}, /* tap_edge_delighted_calm_up_follow */
  {0xE556CDE6u, 36u}, /* expression_delighted_v0_1_accent */
  {0xE56E339Eu, 295u}, /* life_curious_e4_s1_listen_up_anticipate */
  {0xE5758A6Au, 799u}, /* menu_ui_zh_cn_s8_o2_ack_i2 */
  {0xE57DB273u, 985u}, /* tap_edge_thoughtful_focused_up_settle */
  {0xE5BE573Du, 341u}, /* life_curious_e17_s0_rest_hold */
  {0xE5DD1CCCu, 28u}, /* expression_delighted_v0_0_hold */
  {0xE5EABA42u, 119u}, /* life_alert_e29_s4_notice_left_settle */
  {0xE60D094Au, 967u}, /* tap_edge_bashful_warm_center_settle */
  {0xE61E331Cu, 954u}, /* tap_edge_curious_thoughtful_down_accent */
  {0xE6272D15u, 972u}, /* tap_edge_playful_calm_left_accent */
  {0xE63B8C88u, 759u}, /* menu_ui_zh_cn_s2_o0_normal */
  {0xE6550184u, 550u}, /* life_thoughtful_e5_s3_listen_up_follow */
  {0xE6758BFDu, 800u}, /* menu_ui_zh_cn_s8_o2_ack_i3 */
  {0xE697DD60u, 963u}, /* tap_edge_curious_focused_right_orient */
  {0xE6BC364Cu, 767u}, /* menu_ui_zh_cn_s3_o1_processing_i2 */
  {0xE6E2E1FFu, 962u}, /* tap_edge_calm_warm_right_orient */
  {0xE7814689u, 555u}, /* life_thoughtful_e2_s3_notice_right_follow */
  {0xE798BA4Bu, 114u}, /* tap_edge_thoughtful_alert_right_settle */
  {0xE7C76680u, 771u}, /* menu_ui_zh_cn_s3_o2_ack_i3 */
  {0xE7CA63D1u, 973u}, /* tap_edge_thoughtful_calm_up_settle */
  {0xE7CB2801u, 95u}, /* expression_thoughtful_v0_1_follow */
  {0xE7CB84D0u, 1004u}, /* tap_edge_warm_delighted_center_anticipate */
  {0xE7DFF219u, 19u}, /* expression_curious_v0_1_settle */
  {0xE7EA3536u, 475u}, /* life_warm_e4_s0_rest_hold */
  {0xE7EBA6F0u, 835u}, /* menu_ui_en_s0_o2_ack_i5 */
  {0xE88B1A82u, 700u}, /* life_alert_e24_s0_notice_right_orient */
  {0xE8A5157Bu, 854u}, /* menu_ui_en_s1_o1_ack_i4 */
  {0xE8A5FB98u, 660u}, /* life_alert_e9_s0_rest_hold */
  {0xE8A65238u, 149u}, /* life_calm_e0_s3_notice_right_follow */
  {0xE8AD1C29u, 984u}, /* tap_edge_alert_focused_left_follow */
  {0xE8BDEDACu, 1000u}, /* tap_edge_warm_curious_down_orient */
  {0xE8EBA883u, 834u}, /* menu_ui_en_s0_o2_ack_i4 */
  {0xE9052C9Au, 464u}, /* tap_local_warm_left */
  {0xE960386Eu, 109u}, /* expression_focused_v2_1_follow */
  {0xE98F2ACFu, 70u}, /* expression_sleepy_v0_1_orient */
  {0xE9A3C2C8u, 890u}, /* menu_ui_en_s7_o0_normal */
  {0xE9BC3B05u, 766u}, /* menu_ui_zh_cn_s3_o1_processing_i1 */
  {0xE9BD2901u, 394u}, /* life_delighted_e28_s0_notice_left_orient */
  {0xE9DB21C9u, 981u}, /* tap_edge_focused_thoughtful_center_follow */
  {0xE9E2D6C3u, 355u}, /* life_curious_e20_s2_notice_right_accent */
  {0xE9F0A78Bu, 61u}, /* expression_playful_v0_0_settle */
  {0xEA494D86u, 576u}, /* life_thoughtful_e16_s0_rest_hold */
  {0xEA5349F7u, 4u}, /* expression_calm_v0_0_follow */
  {0xEA5EC829u, 1061u}, /* tap_edge_focused_calm_right_orient */
  {0xEA747744u, 1066u}, /* tap_edge_alert_focused_up_anticipate */
  {0xEA7EB36Du, 670u}, /* life_alert_e13_s0_rest_hold */
  {0xEA81AD7Cu, 773u}, /* menu_ui_zh_cn_s3_o3_normal */
  {0xEA96CB6Du, 479u}, /* life_warm_e7_s3_notice_right_follow */
  {0xEABFDE90u, 234u}, /* life_calm_e27_s3_small_breath_settle */
  {0xEACA4DBFu, 1071u}, /* tap_edge_alert_curious_up_anticipate */
  {0xEAD48A2Fu, 462u}, /* life_warm_e28_s2_soften_follow */
  {0xEAD6B01Bu, 1033u}, /* tap_edge_bashful_warm_left_accent */
  {0xEAFDBD05u, 967u}, /* tap_edge_bashful_warm_right_settle */
  {0xEB12F30Bu, 105u}, /* expression_focused_v2_2_settle */
  {0xEB32E062u, 973u}, /* tap_edge_sleepy_calm_right_settle */
  {0xEB461088u, 33u}, /* life_delighted_e4_s4_notice_right_settle */
  {0xEB499BDAu, 695u}, /* life_alert_e22_s1_startle_accent */
  {0xEB607238u, 119u}, /* life_alert_e13_s4_listen_up_settle */
  {0xEB67FBA5u, 1024u}, /* tap_edge_playful_curious_right_anticipate */
  {0xEB7845F4u, 973u}, /* tap_edge_playful_calm_center_settle */
  {0xEB90237Cu, 404u}, /* life_delighted_e5_s0_soften_anticipate */
  {0xEB9E6EA2u, 558u}, /* life_thoughtful_e3_s0_ponder_orient */
  {0xEBA51A34u, 851u}, /* menu_ui_en_s1_o1_ack_i1 */
  {0xEBAE7019u, 86u}, /* expression_thoughtful_v0_1_hold */
  {0xEBD56201u, 405u}, /* life_delighted_e5_s1_soften_accent */
  {0xEC1FD256u, 1067u}, /* tap_edge_alert_curious_up_orient */
  {0xEC69FB35u, 151u}, /* life_calm_e1_s0_rest_hold */
  {0xECBBDBBAu, 973u}, /* tap_edge_curious_calm_right_follow */
  {0xECC17E6Du, 973u}, /* tap_edge_delighted_calm_left_follow */
  {0xECC64A0Au, 878u}, /* menu_ui_en_s3_o3_processing_i5 */
  {0xECC8C751u, 984u}, /* tap_edge_alert_focused_up_follow */
  {0xECFF38BCu, 477u}, /* life_warm_e29_s1_notice_right_anticipate */
  {0xED067B7Cu, 741u}, /* menu_ui_zh_cn_s0_o4_ack_i6 */
  {0xED4999F3u, 419u}, /* life_delighted_e9_s0_notice_right_orient */
  {0xED698B5Cu, 220u}, /* life_calm_e17_s1_notice_left_anticipate */
  {0xED85BD3Bu, 216u}, /* life_calm_e16_s1_small_breath_accent */
  {0xED8DCB0Cu, 347u}, /* life_curious_e18_s0_notice_left_orient */
  {0xEDA51D5Au, 853u}, /* menu_ui_en_s1_o1_ack_i3 */
  {0xEDAC988Cu, 973u}, /* tap_edge_warm_calm_left_follow */
  {0xEDB65431u, 395u}, /* life_delighted_e28_s1_notice_left_anticipate */
  {0xEDBBC7EDu, 961u}, /* tap_transition_left_e1_orient */
  {0xEDBD9F5Du, 950u}, /* tap_edge_alert_curious_right_follow */
  {0xEDC0225Cu, 70u}, /* expression_sleepy_v0_0_settle */
  {0xEDCB54E3u, 971u}, /* tap_edge_curious_calm_right_anticipate */
  {0xEDE9EA15u, 988u}, /* tap_edge_focused_alert_left_follow */
  {0xEDEBB062u, 833u}, /* menu_ui_en_s0_o2_ack_i3 */
  {0xEDF3FDF4u, 692u}, /* life_alert_e20_s1_listen_up_anticipate */
  {0xEDFE9229u, 951u}, /* tap_edge_warm_curious_center_settle */
  {0xEE067D0Fu, 742u}, /* menu_ui_zh_cn_s0_o4_ack_i7 */
  {0xEE27A80Au, 1003u}, /* tap_edge_warm_curious_up_anticipate */
  {0xEE2A2EC5u, 47u}, /* life_warm_e21_s4_notice_left_settle */
  {0xEE2FDA7Au, 677u}, /* life_alert_e14_s2_notice_right_accent */
  {0xEE33DF46u, 783u}, /* menu_ui_zh_cn_s5_o0_ack_i1 */
  {0xEE5C9971u, 289u}, /* life_curious_e13_s0_rest_hold */
  {0xEE61F65Eu, 418u}, /* life_delighted_e9_s0_rest_hold */
  {0xEE7E9C91u, 382u}, /* life_delighted_e15_s1_notice_left_anticipate */
  {0xEEA51EEDu, 852u}, /* menu_ui_en_s1_o1_ack_i2 */
  {0xEEC69D90u, 127u}, /* expression_alert_v0_2_follow */
  {0xEED3FC27u, 55u}, /* expression_warm_v0_2_follow */
  {0xEEDB4DEDu, 140u}, /* menu_hold_2000ms */
  {0xEEEBB1F5u, 832u}, /* menu_ui_en_s0_o2_ack_i2 */
  {0xEEFA8877u, 809u}, /* menu_ui_zh_cn_s10_o0_normal */
  {0xEF067EA2u, 739u}, /* menu_ui_zh_cn_s0_o4_ack_i4 */
  {0xEF27480Fu, 491u}, /* life_warm_e18_s2_notice_right_accent */
  {0xEF33E0D9u, 782u}, /* menu_ui_zh_cn_s5_o0_ack_i0 */
  {0xEF3D9764u, 515u}, /* life_warm_e17_s0_rest_hold */
  {0xEF76707Au, 987u}, /* tap_edge_thoughtful_alert_down_accent */
  {0xEF9EFF51u, 1041u}, /* tap_edge_bashful_calm_left_accent */
  {0xEFABA045u, 743u}, /* menu_ui_zh_cn_s1_o0_normal */
  {0xEFB87907u, 50u}, /* expression_warm_v0_1_accent */
  {0xEFF21B89u, 983u}, /* tap_edge_thoughtful_focused_down_accent */
  {0xEFFEB433u, 1026u}, /* tap_edge_sleepy_warm_up_orient */
  {0xF0056EB2u, 489u}, /* life_warm_e14_s0_notice_right_orient */
  {0xF0068035u, 740u}, /* menu_ui_zh_cn_s0_o4_ack_i5 */
  {0xF02D0F5Cu, 986u}, /* tap_edge_curious_alert_right_anticipate */
  {0xF04F0C21u, 135u}, /* menu_progress_0_25 */
  {0xF05BEE8Au, 954u}, /* tap_edge_focused_thoughtful_left_accent */
  {0xF0667060u, 967u}, /* tap_edge_curious_warm_down_settle */
  {0xF06AC7BAu, 994u}, /* tap_edge_delighted_warm_right_orient */
  {0xF088ACDCu, 186u}, /* life_calm_e29_s0_notice_right_orient */
  {0xF0903C00u, 958u}, /* tap_edge_calm_sleepy_down_orient */
  {0xF094C2D8u, 977u}, /* tap_edge_delighted_playful_up_accent */
  {0xF0B7D075u, 212u}, /* life_calm_e15_s2_soften_follow */
  {0xF0F9F1D4u, 164u}, /* life_calm_e4_s0_rest_hold */
  {0xF1099430u, 449u}, /* tap_edge_warm_delighted_down_settle */
  {0xF121781Cu, 27u}, /* expression_curious_v0_2_follow */
  {0xF131E186u, 1051u}, /* tap_edge_thoughtful_calm_up_anticipate */
  {0xF159E6FAu, 950u}, /* tap_edge_alert_curious_left_follow */
  {0xF16944E7u, 489u}, /* tap_local_warm_right */
  {0xF1A2C360u, 145u}, /* life_calm_e0_s0_rest_hold */
  {0xF1B5FF3Au, 643u}, /* life_alert_e4_s3_notice_left_follow */
  {0xF21C0E7Du, 612u}, /* life_thoughtful_e27_s1_notice_right_anticipate */
  {0xF2261644u, 91u}, /* life_thoughtful_e15_s3_ponder_settle */
  {0xF27363DCu, 139u}, /* upgrade_progress_0_5 */
  {0xF28A0ABAu, 311u}, /* life_curious_e8_s1_listen_up_anticipate */
  {0xF28DBC54u, 283u}, /* life_curious_e1_s3_notice_right_follow */
  {0xF296501Eu, 83u}, /* expression_bashful_v0_2_anticipate */
  {0xF299AD59u, 1003u}, /* tap_edge_warm_curious_down_anticipate */
  {0xF2BB19A6u, 884u}, /* menu_ui_en_s5_o0_normal */
  {0xF2D597E4u, 721u}, /* menu_ui_zh_cn_s0_o0_ack_i2 */
  {0xF2F7A245u, 973u}, /* tap_edge_warm_calm_right_settle */
  {0xF2F8FAE2u, 1013u}, /* tap_edge_playful_delighted_center_anticipate */
  {0xF2FE26F6u, 397u}, /* life_delighted_e28_s3_notice_left_follow */
  {0xF2FE7C9Du, 973u}, /* tap_edge_sleepy_calm_left_follow */
  {0xF31A9B7Bu, 530u}, /* life_warm_e25_s0_rest_hold */
  {0xF34AA236u, 973u}, /* tap_edge_playful_calm_up_follow */
  {0xF34E0BEDu, 1060u}, /* tap_edge_focused_curious_left_orient */
  {0xF3D59977u, 722u}, /* menu_ui_zh_cn_s0_o0_ack_i3 */
  {0xF3DA0828u, 489u}, /* life_warm_e7_s0_notice_right_orient */
  {0xF3F13D63u, 486u}, /* life_warm_e20_s1_listen_up_anticipate */
  {0xF41B6B11u, 1059u}, /* tap_edge_focused_calm_down_orient */
  {0xF43C94C5u, 47u}, /* life_warm_e9_s4_notice_left_settle */
  {0xF450A829u, 555u}, /* life_thoughtful_e11_s3_notice_right_follow */
  {0xF454022Bu, 763u}, /* menu_ui_zh_cn_s3_o0_processing_i2 */
  {0xF4558D4Du, 491u}, /* life_warm_e7_s2_notice_right_accent */
  {0xF45D9114u, 564u}, /* life_thoughtful_e4_s3_notice_left_follow */
  {0xF4639BA8u, 167u}, /* life_calm_e9_s2_notice_left_accent */
  {0xF476300Eu, 129u}, /* blink_closed */
  {0xF4A6F277u, 951u}, /* tap_edge_calm_curious_center_settle */
  {0xF4AA5FE7u, 981u}, /* tap_edge_curious_thoughtful_down_follow */
  {0xF4D59B0Au, 719u}, /* menu_ui_zh_cn_s0_o0_ack_i0 */
  {0xF5310F4Au, 310u}, /* life_curious_e8_s0_listen_up_orient */
  {0xF54A51EBu, 26u}, /* expression_curious_v0_2_accent */
  {0xF55403BEu, 762u}, /* menu_ui_zh_cn_s3_o0_processing_i1 */
  {0xF5607D7Du, 464u}, /* life_warm_e27_s0_notice_left_orient */
  {0xF5ABE33Cu, 423u}, /* life_delighted_e11_s2_notice_left_accent */
  {0xF5BDAC20u, 1061u}, /* tap_edge_focused_curious_right_orient */
  {0xF5D59C9Du, 720u}, /* menu_ui_zh_cn_s0_o0_ack_i1 */
  {0xF5DDB362u, 388u}, /* life_delighted_e1_s2_notice_right_accent */
  {0xF5FB13E6u, 543u}, /* life_thoughtful_e0_s2_notice_left_accent */
  {0xF60614DAu, 497u}, /* life_warm_e30_s3_notice_left_follow */
  {0xF625ED04u, 91u}, /* life_thoughtful_e7_s4_notice_left_settle */
  {0xF659128Au, 94u}, /* expression_thoughtful_v0_1_accent */
  {0xF664696Fu, 951u}, /* tap_edge_bashful_curious_center_settle */
  {0xF6A354D1u, 275u}, /* life_curious_e0_s0_rest_hold */
  {0xF6AA9EADu, 469u}, /* life_warm_e2_s0_listen_up_orient */
  {0xF6AABEEDu, 328u}, /* life_curious_e13_s1_notice_left_anticipate */
  {0xF6BD7DEFu, 465u}, /* life_warm_e21_s1_notice_left_anticipate */
  {0xF6C44AA9u, 474u}, /* life_warm_e8_s1_soften_accent */
  {0xF6FE1EC0u, 119u}, /* life_alert_e11_s4_notice_right_settle */
  {0xF7171950u, 976u}, /* tap_edge_curious_playful_up_anticipate */
  {0xF727B130u, 550u}, /* life_thoughtful_e1_s3_listen_up_follow */
  {0xF72B9898u, 955u}, /* tap_transition_down_e1_follow */
  {0xF73BDD5Cu, 487u}, /* life_warm_e6_s2_listen_up_accent */
  {0xF752426Bu, 292u}, /* life_curious_e29_s3_notice_left_follow */
  {0xF7B0AE05u, 1046u}, /* tap_edge_thoughtful_focused_left_orient */
  {0xF7F444F9u, 974u}, /* tap_edge_curious_warm_up_orient */
  {0xF80F76BBu, 949u}, /* tap_transition_center_e0_accent */
  {0xF82B14A5u, 1016u}, /* tap_edge_playful_curious_left_orient */
  {0xF82BA294u, 951u}, /* tap_edge_warm_curious_right_settle */
  {0xF8531B85u, 973u}, /* tap_edge_curious_calm_left_settle */
  {0xF8B5C99Eu, 267u}, /* life_calm_e29_s1_notice_right_anticipate */
  {0xF8BF29C3u, 594u}, /* life_thoughtful_e17_s0_rest_hold */
  {0xF8C3276Eu, 1007u}, /* tap_edge_warm_playful_down_anticipate */
  {0xF8ED7849u, 630u}, /* life_alert_e3_s4_notice_right_settle */
  {0xF90E0F30u, 336u}, /* life_curious_e15_s2_question_accent */
  {0xF9519B77u, 947u}, /* tap_edge_calm_sleepy_center_orient */
  {0xF968E4DBu, 408u}, /* life_delighted_e6_s0_beam_anticipate */
  {0xF976381Eu, 971u}, /* tap_edge_curious_calm_up_anticipate */
  {0xF98E46A1u, 461u}, /* life_warm_e0_s1_soften_accent */
  {0xF9911E9Fu, 256u}, /* life_calm_e26_s1_listen_up_anticipate */
  {0xF9E042C1u, 1026u}, /* tap_edge_sleepy_calm_left_orient */
  {0xF9ED13F5u, 184u}, /* life_calm_e7_s2_small_breath_follow */
  {0xF9FAA73Cu, 119u}, /* life_alert_e24_s4_notice_right_settle */
  {0xFA039684u, 119u}, /* expression_alert_v0_0_settle */
  {0xFA04C0E0u, 622u}, /* life_alert_e0_s0_startle_orient */
  {0xFA239E18u, 950u}, /* tap_edge_calm_curious_right_follow */
  {0xFA411E7Du, 601u}, /* life_thoughtful_e20_s1_ponder_anticipate */
  {0xFA45C883u, 108u}, /* expression_focused_v0_1_accent */
  {0xFA55A177u, 42u}, /* life_warm_e18_s0_rest_hold */
  {0xFA643D9Eu, 949u}, /* tap_edge_alert_curious_right_accent */
  {0xFA7357E8u, 716u}, /* life_alert_e30_s3_notice_right_follow */
  {0xFA9314D2u, 1046u}, /* tap_edge_thoughtful_curious_left_orient */
  {0xFA97B052u, 135u}, /* menu_hold_1000ms */
  {0xFAA05638u, 690u}, /* life_alert_e19_s3_notice_left_follow */
  {0xFAF5C5E4u, 48u}, /* expression_warm_v0_1_orient */
  {0xFAFFA2CDu, 1005u}, /* tap_edge_playful_delighted_right_accent */
  {0xFB051F6Cu, 1009u}, /* tap_edge_warm_bashful_down_accent */
  {0xFB0B8EA3u, 1038u}, /* tap_edge_bashful_curious_down_anticipate */
  {0xFB10F1FCu, 283u}, /* life_curious_e9_s3_notice_right_follow */
  {0xFB1B3624u, 114u}, /* tap_edge_thoughtful_alert_left_settle */
  {0xFB34811Fu, 973u}, /* tap_edge_sleepy_calm_left_settle */
  {0xFB686E83u, 82u}, /* expression_bashful_v0_2_orient */
  {0xFBA0EA0Cu, 1010u}, /* tap_edge_warm_bashful_up_follow */
  {0xFBB78EAEu, 429u}, /* life_delighted_e13_s2_soften_follow */
  {0xFBF2B5B5u, 1065u}, /* tap_edge_alert_focused_center_orient */
  {0xFC1B7A4Du, 1006u}, /* tap_edge_warm_delighted_center_follow */
  {0xFC21FB20u, 591u}, /* life_thoughtful_e18_s3_notice_right_follow */
  {0xFC285F9Bu, 968u}, /* tap_edge_calm_sleepy_right_anticipate */
  {0xFC3E83FCu, 985u}, /* tap_edge_curious_focused_down_settle */
  {0xFC6FBFD2u, 156u}, /* life_calm_e2_s0_rest_hold */
  {0xFC79C21Eu, 263u}, /* life_calm_e28_s0_notice_left_orient */
  {0xFCAD5C6Du, 119u}, /* life_alert_e2_s4_notice_left_settle */
  {0xFCB320BCu, 997u}, /* tap_edge_warm_bashful_center_orient */
  {0xFCC597A4u, 432u}, /* life_delighted_e26_s1_beam_accent */
  {0xFCCDBE15u, 72u}, /* expression_bashful_v0_0_hold */
  {0xFCCE3407u, 242u}, /* life_calm_e22_s0_notice_right_orient */
  {0xFCEE1B5Du, 570u}, /* life_thoughtful_e6_s3_notice_right_follow */
  {0xFCFCEBABu, 565u}, /* life_thoughtful_e16_s0_listen_up_orient */
  {0xFD02654Au, 1026u}, /* tap_edge_sleepy_warm_right_orient */
  {0xFD2933E1u, 1007u}, /* tap_edge_warm_playful_left_anticipate */
  {0xFD616749u, 1008u}, /* tap_edge_warm_bashful_center_anticipate */
  {0xFD7C8ECCu, 412u}, /* life_delighted_e23_s1_notice_left_anticipate */
  {0xFDB839ADu, 1028u}, /* tap_edge_sleepy_calm_down_accent */
  {0xFDE720A6u, 950u}, /* tap_edge_playful_curious_down_follow */
  {0xFDEC3260u, 24u}, /* expression_curious_v0_2_orient */
  {0xFDEC5933u, 950u}, /* tap_edge_warm_curious_center_follow */
  {0xFE029163u, 315u}, /* life_curious_e9_s1_notice_right_anticipate */
  {0xFE05933Fu, 70u}, /* expression_sleepy_v0_1_follow */
  {0xFE459BC8u, 1027u}, /* tap_edge_sleepy_calm_center_anticipate */
  {0xFE48F899u, 426u}, /* life_delighted_e12_s1_notice_right_anticipate */
  {0xFE5C3DD6u, 597u}, /* life_thoughtful_e24_s1_notice_right_anticipate */
  {0xFE5FC17Cu, 484u}, /* life_warm_e31_s3_soften_settle */
  {0xFE6DBED8u, 588u}, /* life_thoughtful_e13_s3_notice_left_follow */
  {0xFECF8CC3u, 429u}, /* life_delighted_e30_s2_soften_follow */
  {0xFF11F476u, 688u}, /* life_alert_e23_s1_notice_left_anticipate */
  {0xFF32B62Fu, 965u}, /* tap_edge_calm_warm_center_accent */
  {0xFF4F66F7u, 644u}, /* life_alert_e4_s4_notice_left_settle */
  {0xFF786A3Eu, 1056u}, /* tap_edge_focused_calm_center_orient */
  {0xFFA4A1D0u, 626u}, /* life_alert_e22_s0_startle_orient */
  {0xFFB67AD4u, 1010u}, /* tap_edge_warm_bashful_left_follow */
  {0xFFCB67ACu, 946u}, /* tap_local_alert_down */
  {0xFFD4BA10u, 114u}, /* tap_edge_focused_alert_down_settle */
  {0xFFE53110u, 165u}, /* tap_local_calm_left */
  {0xFFEB7DC1u, 486u}, /* life_warm_e6_s1_listen_up_anticipate */
  {0xFFF3EC0Eu, 950u}, /* tap_edge_thoughtful_curious_center_follow */
  {0xFFFFFDC8u, 33u}, /* life_delighted_e22_s4_notice_right_settle */
};

static inline uint32_t companion_browser_cemp_state_hash(const char *value)
{
  uint32_t hash = 0x811C9DC5u;
  if (value == NULL) return 0u;
  while (*value != '\0') {
    hash = (hash ^ (uint8_t)*value++) * 0x01000193u;
  }
  return hash;
}

static inline bool companion_browser_cemp_state_unique_index(
    const char *state_id, uint16_t *unique_frame_index)
{
  const uint32_t target = companion_browser_cemp_state_hash(state_id);
  size_t low = 0u;
  size_t high = COMPANION_BROWSER_CEMP_STATE_MAP_COUNT;
  while (low < high) {
    const size_t middle = low + (high - low) / 2u;
    const uint32_t hash = companion_browser_cemp_state_map[middle].hash;
    if (hash < target) low = middle + 1u;
    else high = middle;
  }
  if (low >= COMPANION_BROWSER_CEMP_STATE_MAP_COUNT ||
      companion_browser_cemp_state_map[low].hash != target) return false;
  if (unique_frame_index != NULL) {
    *unique_frame_index = companion_browser_cemp_state_map[low].unique_frame_index;
  }
  return true;
}

#endif /* COMPANION_BROWSER_CEMP_CONTRACT_H */
