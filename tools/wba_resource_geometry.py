"""Derive the dynamic workspace from the actual static resource bank.

Resource content may grow. A changed boundary is a new media geometry, not an
ordinary in-place resource OTA on an already formatted board.
"""
from __future__ import annotations

NOR_BYTES = 0x1000000
SECTOR_BYTES = 0x1000
RESOURCE_ALIGNMENT = SECTOR_BYTES
RESOURCE_HEADROOM = 0
SYSTEM_BYTES = 0x20000


def geometry(static_bytes: int, total_bytes: int = NOR_BYTES) -> dict:
    if (not isinstance(static_bytes, int) or not isinstance(total_bytes, int)
        or total_bytes not in (1 << n for n in range(20, 25))
        or static_bytes < 2 * SECTOR_BYTES or static_bytes % SECTOR_BYTES
        or static_bytes + SYSTEM_BYTES + SECTOR_BYTES > total_bytes):
        raise ValueError('Static resources leave no valid dynamic payload arena')
    return dict(norBytes=total_bytes, staticBytes=static_bytes,
        rootA=static_bytes-2*SECTOR_BYTES, rootB=static_bytes-SECTOR_BYTES,
        dynamicBase=static_bytes, dynamicBytes=total_bytes-static_bytes,
        systemBytes=SYSTEM_BYTES, recordingCatalog=static_bytes+0x10000,
        payloadBase=static_bytes+SYSTEM_BYTES,
        payloadBytes=total_bytes-static_bytes-SYSTEM_BYTES)


def choose_static_bytes(arena_bytes: int, total_bytes: int = NOR_BYTES,
                        headroom_bytes: int = RESOURCE_HEADROOM) -> int:
    if arena_bytes < 0 or headroom_bytes < 0:
        raise ValueError('Negative resource size or headroom')
    wanted = arena_bytes + 2 * SECTOR_BYTES + headroom_bytes
    size = (wanted + RESOURCE_ALIGNMENT-1)//RESOURCE_ALIGNMENT*RESOURCE_ALIGNMENT
    geometry(size, total_bytes)
    return size


def from_profile(profile: dict, bank_bytes: int) -> dict:
    if profile.get('storageLayoutVersion') != 3 or profile.get('uiPartitionBytes') != bank_bytes:
        raise ValueError('Resource bank and layout profile differ')
    result = geometry(bank_bytes, profile.get('flashGeometry', {}).get('norBytes', NOR_BYTES))
    if profile.get('flashGeometry', result) != result:
        raise ValueError('Resource geometry is inconsistent with bank size')
    return result
