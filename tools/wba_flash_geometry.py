"""Canonical CE/CG internal Flash geometry for builds, packages and installation.

The product default is the installed CE (512KiB); CG requires explicit selection.
The reported package marking never substitutes for the Flash-size register.
"""
from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'platform/stm32wba55_companion_v11/flash_geometry.json'
HEADER = ROOT / 'app/companion_pendant/update/wba_flash_geometry.h'
_spec = json.loads(SOURCE.read_text(encoding='utf-8'))
assert _spec['schema'] == 'companion.wba.internal-flash-geometry.v1'
MCUS = tuple(item['mcu'] for item in _spec['variants'])
DEFAULT_MCU = 'STM32WBA55CEU6'
LAYOUTS = tuple(item['id'] for item in _spec['layouts'])


@dataclass(frozen=True)
class FlashGeometry:
    mcu: str
    flash_kib: int
    board_target: int
    hardware_revision: str
    sram_bytes: int
    sram_regions: tuple[tuple[int, int], ...]
    flash_base: int = _spec['flash_base']
    flash_page_bytes: int = _spec['flash_page_bytes']
    boot_bytes: int = _spec['boot_bytes']
    nvm_bytes: int = _spec['nvm_bytes']
    sram_base: int = _spec['sram_base']

    def valid_stack_pointer(self, address: int) -> bool:
        # A descending stack can start at the exclusive upper bank boundary,
        # but not at the bank's first byte or inside the CE address hole.
        return address % 8 == 0 and any(base < address <= base + size
                                        for base, size in self.sram_regions)

    @property
    def flash_bytes(self) -> int:
        return self.flash_kib * 1024

    @property
    def nvm_offset(self) -> int:
        return self.flash_bytes - self.nvm_bytes

    @property
    def app_bytes(self) -> int:
        return self.nvm_offset - self.boot_bytes

    @property
    def app_address(self) -> int:
        return self.flash_base + self.boot_bytes

    @property
    def app_end(self) -> int:
        return self.flash_base + self.nvm_offset

    def receipt(self) -> dict:
        return {**self.__dict__, 'sram_regions':[list(region) for region in self.sram_regions],
                'flash_bytes': self.flash_bytes,
                'app_address': self.app_address, 'app_bytes': self.app_bytes,
                'nvm_offset': self.nvm_offset}

    def linker(self, platform: Path, *, boot: bool = False) -> Path:
        suffix = '_F24' if self.boot_bytes == 24576 else ''
        if self.nvm_bytes == 0 and not boot: suffix += '_N0'
        name = (self.mcu + '_BOOT' if boot else self.mcu + '_BLE') + suffix + '.ld'
        return platform / name

    def validate_linker(self, path: Path, boot: bool = False, standalone: bool = False) -> None:
        if boot and standalone:
            raise ValueError('Boot and standalone linker roles are distinct')
        text = path.read_text(encoding='utf-8')
        region = re.search(r'FLASH\s*\(rx\)\s*:\s*ORIGIN\s*=\s*(0x[0-9A-Fa-f]+),\s*LENGTH\s*=\s*(\d+)K', text)
        if not region or (int(region[1], 16), int(region[2]) * 1024) != (
                self.flash_base if boot or standalone else self.app_address,
                self.boot_bytes if boot else self.flash_bytes if standalone else self.app_bytes):
            raise ValueError('Linker differs from selected MCU geometry: ' + str(path))
        if self.flash_kib == 512:
            for index, (base, size) in enumerate(self.sram_regions, 1):
                ram = re.search(rf'RAM{index}\s*\(xrw\)\s*:\s*ORIGIN\s*=\s*(0x[0-9A-Fa-f]+),\s*LENGTH\s*=\s*(\d+)K', text)
                if not ram or (int(ram[1], 16), int(ram[2]) * 1024) != (base, size):
                    raise ValueError('CE linker must declare both physical SRAM banks: ' + str(path))


def for_mcu(mcu: str = DEFAULT_MCU, layout: str = 'legacy32') -> FlashGeometry:
    selected = next((x for x in _spec['layouts'] if x['id'] == layout), None)
    if selected is None or selected.get('mcu', mcu) != mcu:
        raise ValueError('Unsupported MCU/internal Flash layout: ' + mcu + '/' + layout)
    for item in _spec['variants']:
        if item['mcu'] == mcu:
            values = dict(item, boot_bytes=selected['boot_bytes'],
                          nvm_bytes=selected.get('nvm_bytes', _spec['nvm_bytes']),
                          sram_regions=tuple(tuple(region) for region in item['sram_regions']))
            for key in ('board_target', 'hardware_revision'):
                if key in selected: values[key] = selected[key]
            return FlashGeometry(**values)
    raise ValueError('Unsupported WBA MCU geometry: ' + str(mcu))


def for_target(board_target: int) -> FlashGeometry:
    for item in _spec['variants']:
        for layout in _spec['layouts']:
            if layout.get('mcu', item['mcu']) != item['mcu']: continue
            geometry = for_mcu(item['mcu'], layout['id'])
            if geometry.board_target == board_target: return geometry
    raise ValueError('Unknown Companion internal Flash target identity')


def from_receipt(receipt: dict, *, allow_legacy_cg: bool = False) -> FlashGeometry:
    recorded = receipt.get('internal_flash_geometry')
    candidates = [for_mcu(receipt.get('mcu'), x['id']) for x in _spec['layouts']
                  if x.get('mcu', receipt.get('mcu')) == receipt.get('mcu')]
    for geometry in candidates:
        if recorded == geometry.receipt(): return geometry
    if recorded is None and allow_legacy_cg:
        geometry = for_mcu(receipt.get('mcu'))
        if geometry.flash_kib == 1024: return geometry
    raise ValueError('Missing or inconsistent internal Flash geometry identity')


def header_text() -> str:
    lines = ['/* Generated from platform/stm32wba55_companion_v11/flash_geometry.json. */',
             '#ifndef COMPANION_WBA_FLASH_GEOMETRY_H', '#define COMPANION_WBA_FLASH_GEOMETRY_H',
             '#include <stdint.h>', '', '#ifndef COMP_WBA_INTERNAL_FLASH_KIB',
             f'#define COMP_WBA_INTERNAL_FLASH_KIB {for_mcu().flash_kib}u', '#endif',
             '#ifndef COMP_WBA_BOOT_FLASH_KIB', '#define COMP_WBA_BOOT_FLASH_KIB 32u', '#endif',
             '#ifndef COMP_WBA_INTERNAL_NVM_KIB', '#define COMP_WBA_INTERNAL_NVM_KIB 16u', '#endif',
             '#if COMP_WBA_INTERNAL_NVM_KIB == 0u',
             '#if COMP_WBA_INTERNAL_FLASH_KIB != 512u || COMP_WBA_BOOT_FLASH_KIB != 24u',
             '#error "NVM0 requires the matched CE compact24-nor target"', '#endif',
             f'#define COMP_WBA_UPDATE_BOARD_COMPANION_V11 UINT32_C(0x{for_mcu(layout="compact24-nor").board_target:08X})',
             '#elif COMP_WBA_INTERNAL_NVM_KIB != 16u', '#error "Unsupported internal NVM extent"',
             '#elif COMP_WBA_BOOT_FLASH_KIB == 24u',
             '#if COMP_WBA_INTERNAL_FLASH_KIB != 512u', '#error "compact24 requires CE"', '#endif',
             f'#define COMP_WBA_UPDATE_BOARD_COMPANION_V11 UINT32_C(0x{for_mcu(layout="compact24").board_target:08X})',
             '#elif COMP_WBA_BOOT_FLASH_KIB == 32u']
    for index, item in enumerate(_spec['variants']):
        geometry = for_mcu(item['mcu'])
        lines.extend([f'#{"if" if index == 0 else "elif"} COMP_WBA_INTERNAL_FLASH_KIB == {geometry.flash_kib}u',
                      f'#define COMP_WBA_UPDATE_BOARD_COMPANION_V11 UINT32_C(0x{geometry.board_target:08X})'])
    lines.extend(['#else', '#error "Unsupported WBA55 internal Flash capacity"', '#endif',
                  '#else', '#error "Unsupported resident boot extent"', '#endif', ''])
    for name, value in [('INTERNAL_FLASH_BASE', _spec['flash_base']), ('INTERNAL_FLASH_PAGE_BYTES', _spec['flash_page_bytes'])]:
        lines.append(f'#define COMP_WBA_{name} UINT32_C(0x{value:08X})')
    lines.extend(['#define COMP_WBA_INTERNAL_NVM_BYTES (COMP_WBA_INTERNAL_NVM_KIB * UINT32_C(1024))',
                  '#define COMP_WBA_BOOT_APP_OFFSET (COMP_WBA_BOOT_FLASH_KIB * UINT32_C(1024))',
                  '#define COMP_WBA_INTERNAL_FLASH_BYTES (COMP_WBA_INTERNAL_FLASH_KIB * UINT32_C(1024))',
                  '#define COMP_WBA_BOOT_NVM_OFFSET (COMP_WBA_INTERNAL_FLASH_BYTES - COMP_WBA_INTERNAL_NVM_BYTES)',
                  '#define COMP_WBA_BOOT_APP_CAPACITY (COMP_WBA_BOOT_NVM_OFFSET - COMP_WBA_BOOT_APP_OFFSET)',
                  '#define COMP_WBA_APP_ADDRESS (COMP_WBA_INTERNAL_FLASH_BASE + COMP_WBA_BOOT_APP_OFFSET)',
                  '#define COMP_WBA_APP_END (COMP_WBA_INTERNAL_FLASH_BASE + COMP_WBA_BOOT_NVM_OFFSET)',
                  '', '#define COMP_WBA_SRAM1_BASE UINT32_C(0x20000000)',
                  '#define COMP_WBA_SRAM2_BASE UINT32_C(0x20010000)',
                  '#define COMP_WBA_SRAM2_BYTES UINT32_C(0x00010000)',
                  '#if COMP_WBA_INTERNAL_FLASH_KIB == 512u',
                  '#define COMP_WBA_SRAM1_BYTES UINT32_C(0x00008000)',
                  '#else', '#define COMP_WBA_SRAM1_BYTES UINT32_C(0x00010000)', '#endif',
                  '#define COMP_WBA_SRAM_BYTES (COMP_WBA_SRAM1_BYTES + COMP_WBA_SRAM2_BYTES)',
                  'static inline int comp_wba_sram_stack_pointer_valid(uint32_t sp)',
                  '{', '    return (sp & 7u) == 0u &&',
                  '        ((sp > COMP_WBA_SRAM1_BASE && sp <= COMP_WBA_SRAM1_BASE + COMP_WBA_SRAM1_BYTES) ||',
                  '         (sp > COMP_WBA_SRAM2_BASE && sp <= COMP_WBA_SRAM2_BASE + COMP_WBA_SRAM2_BYTES));',
                  '}', '', '#endif', ''])
    return '\n'.join(lines)


def validate_generated_header() -> None:
    if HEADER.read_text(encoding='utf-8') != header_text():
        raise ValueError('Generated WBA Flash geometry header differs from canonical JSON')


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--write-header', action='store_true')
    args = parser.parse_args()
    if args.write_header:
        HEADER.write_text(header_text(), encoding='utf-8', newline='\n')
    validate_generated_header()
    print(json.dumps([for_mcu(mcu).receipt() for mcu in MCUS], indent=2))
