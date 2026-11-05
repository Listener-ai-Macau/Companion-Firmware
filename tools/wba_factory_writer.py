"""Register one exact source-bound CE factory writer in an owned API session.

No connection, loader registration, file copying or device operation on import.
Caller verifies source/build provenance, physical identity and the shared lease.
The public receipt is a digest binding, not permission to erase a board.
"""
from pathlib import Path
from wba_nor_initial import require, sha


def validate_writer(receipt: dict, loader: bytes, static: int) -> None:
    require(receipt.get('schema') == 'companion.wba.factory-loader.v1' and
            receipt.get('result') == 'PASS_BUILD_ONLY' and receipt.get('mcu') == 'STM32WBA55CEU6' and
            receipt.get('development_format') is True and receipt.get('read_base') == 0x90000000 and
            receipt.get('read_bytes') == receipt.get('write_bytes') == 16777216 and
            receipt.get('static_geometry', {}).get('staticBytes') == static and
            receipt.get('protected_bond_range') == [static + 0xC000, static + 0xF000] and
            receipt.get('mass_erase') == 'REFUSED' and receipt.get('loader_sha256') == sha(loader),
            'Factory writer lacks exact CE extent and permanent bond/seal protection')


def open_bound_loader(probe, output: Path, loader_path: Path, receipt: dict):
    """Load the already verified guarded writer; reuse its runtime directory."""
    import ctypes as c
    import shutil
    from verify_wba_factory_loader import Loader
    from migrate_wba_static_ui import remove_loader

    validate_writer(receipt, loader_path.read_bytes(), receipt['static_geometry']['staticBytes'])
    root = output / 'loader-runtime'
    if not root.exists():
        (root / 'ExternalLoader').mkdir(parents=True)
        shutil.copyfile(loader_path, root / 'ExternalLoader' / loader_path.name)
        shutil.copytree(Path('C:/ST/STM32CubeProgrammer/bin/FlashLoader'), root / 'FlashLoader')
    require(sha((root / 'ExternalLoader' / loader_path.name).read_bytes()) == receipt['loader_sha256'],
            'Retained bound loader changed')
    probe.api.setLoadersPath(str(root).encode())
    probe.api.setExternalLoaderPath.argtypes = [c.c_char_p, c.POINTER(c.POINTER(Loader))]
    probe.api.setExternalLoaderPath.restype = None
    probe.api.removeExternalLoader.argtypes = [c.c_char_p]
    probe.api.removeExternalLoader.restype = None
    loaded = c.POINTER(Loader)()
    try:
        probe.api.setExternalLoaderPath(loader_path.name.encode(), c.byref(loaded))
        require(bool(loaded) and bool(loaded.contents.sectors), 'Bound writer registration failed')
        info = loaded.contents
        require((info.start, info.size, info.page, info.sector_types, info.sectors[0].count, info.sectors[0].size) ==
                (0x90000000, 16777216, 256, 1, 4096, 4096), 'Bound writer ABI/extent mismatch')
        require(info.name.decode() == 'Companion_V11_WBA55_SPI3_DEV_FORMAT_v3', 'Unexpected writer identity')
    except BaseException:
        remove_loader(probe, loader_path.name)
        raise
    return loader_path.name
