"""Ask the installed ST API to parse our loader, without any probe connection."""
from pathlib import Path
import argparse
import ctypes as c
import hashlib
import json
import os
import shutil
import tempfile

class Sector(c.Structure):
    _fields_ = [('count', c.c_uint32), ('size', c.c_uint32)]

class Loader(c.Structure):
    _fields_ = [('path', c.c_char * 200), ('name', c.c_char * 100), ('type', c.c_int),
        ('start', c.c_uint32), ('size', c.c_uint32), ('page', c.c_uint32),
        ('sector_types', c.c_uint32), ('sectors', c.POINTER(Sector))]

class Storage(c.Structure):
    _fields_ = [('count', c.c_uint), ('loaders', c.POINTER(Loader))]

InitProgress = c.CFUNCTYPE(None)
LogMessage = c.CFUNCTYPE(None, c.c_int, c.c_wchar_p)
LoadBar = c.CFUNCTYPE(None, c.c_int, c.c_int)
class Display(c.Structure):
    _fields_ = [('init', InitProgress), ('log', LogMessage), ('bar', LoadBar)]

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--loader-dir', type=Path, default=Path(__file__).resolve().parents[1] / '.cache/wba-factory/loader')
    parser.add_argument('--api-dir', type=Path, default=Path('C:/ST/STM32CubeProgrammer/api/lib'))
    args = parser.parse_args()
    report = json.loads((args.loader_dir / 'result.json').read_text())
    source = args.loader_dir / report['loader']
    if hashlib.sha256(source.read_bytes()).hexdigest() != report['loader_sha256']:
        raise RuntimeError('Loader build receipt mismatch')
    with os.add_dll_directory(str(args.api_dir)), tempfile.TemporaryDirectory(prefix='wba-loader-') as tmp:
        external = Path(tmp) / 'ExternalLoader'; external.mkdir()
        shutil.copy2(source, external / source.name)
        api = c.CDLL(str(args.api_dir / 'CubeProgrammer_API.dll'))
        messages = []
        callbacks = Display(InitProgress(lambda: None), LogMessage(lambda level, msg: messages.append(msg)), LoadBar(lambda x, n: None))
        api.setDisplayCallbacks.argtypes = [Display]
        api.setDisplayCallbacks(callbacks)
        api.setVerbosityLevel(3)
        api.setLoadersPath.argtypes = [c.c_char_p]
        api.setLoadersPath(str(Path(tmp)).encode())
        api.getExternalLoaders.argtypes = [c.c_char_p, c.POINTER(c.POINTER(Storage))]
        api.getExternalLoaders.restype = c.c_int
        storage = c.POINTER(Storage)()
        result = api.getExternalLoaders(str(Path(tmp)).encode(), c.byref(storage))
        if result != 0 or not storage or storage.contents.count != 1:
            raise RuntimeError(f'ST rejected loader metadata: result={result}')
        # Directory listing is abbreviated (filename, no sector array). Loading
        # the ELF is still offline and returns the complete StorageInfo ABI.
        api.setExternalLoaderPath.argtypes = [c.c_char_p, c.POINTER(c.POINTER(Loader))]
        api.setExternalLoaderPath.restype = None
        loaded = c.POINTER(Loader)()
        api.setExternalLoaderPath(source.name.encode(), c.byref(loaded))
        if not loaded:
            raise RuntimeError('ST rejected callable ELF: ' + '\n'.join(messages))
        loader = loaded.contents
        if not loader.sectors:
            raise RuntimeError(f'ST returned incomplete geometry: name={loader.name!r} type={loader.type} start={loader.start:x} size={loader.size:x} page={loader.page} sector_types={loader.sector_types}')
        values = {'name': loader.name.decode(), 'type': loader.type, 'start': loader.start,
            'size': loader.size, 'page': loader.page, 'sector_types': loader.sector_types,
            'sector_count': loader.sectors[0].count, 'sector_size': loader.sectors[0].size}
        expected_name = ('Companion_V11_WBA55_SPI3_DEV_FORMAT_v3'
                         if report.get('development_format')
                         else 'Companion_V11_WBA55_SPI3_UI_ONLY_v1')
        if values != {'name': expected_name, 'type': 7, 'start': 0x90000000,
                      'size': 0x1000000, 'page': 256, 'sector_types': 1, 'sector_count': 4096, 'sector_size': 4096}:
            raise RuntimeError('ST parsed unexpected loader geometry: ' + str(values))
        api.deleteLoaders()
    receipt = {'result': 'PASS_ST_OFFLINE_LOADER_PARSE_ONLY', 'loader_sha256': report['loader_sha256'],
        'hardwareAcceptance': 'NOT_RUN', 'connected': False, 'metadata': values,
        'verifier_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'api_sha256': hashlib.sha256((args.api_dir / 'CubeProgrammer_API.dll').read_bytes()).hexdigest()}
    (args.loader_dir / 'st-parse-result.json').write_text(json.dumps(receipt, indent=2) + '\n')
    print(json.dumps(receipt, indent=2))

if __name__ == '__main__': main()
