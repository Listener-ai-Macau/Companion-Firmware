"""Private durable migration authority; never connects to a board.

The immutable acquisition and pre-write marker are separate from diagnostic
result.json. A start marker means the App MAY have run, never that it did run
successfully. Process-lifetime locking is checked again by explicit recovery.
These files are crash-recovery evidence, not authenticated key storage.
"""
from __future__ import annotations
from datetime import datetime
import json
import os
from pathlib import Path
import tempfile

from wba_nor_initial import exact, load, require, sha

AUTHORITY = 'migration-authority.json'
WRITE = 'writes-authorized.json'
START_MARKERS = ('start-authorized.json', 'recovery-start-authorized.json', 'recovery-completed.json')
AUTHORITY_SCHEMA = 'companion.wba.nor-migration-authority.v2'
PHASE_SCHEMA = 'companion.wba.nor-migration-phase.v2'


def now():
    return datetime.now().astimezone().isoformat(timespec='seconds')


def new_durable_json(path: Path, value: dict):
    """Publish once after flushing; never overwrite existing phase evidence."""
    require(not path.exists(), 'Durable phase already exists: ' + path.name)
    fd, name = tempfile.mkstemp(prefix=path.name + '.', suffix='.tmp', dir=path.parent)
    try:
        with os.fdopen(fd, 'wb') as stream:
            stream.write((json.dumps(value, ensure_ascii=False, indent=2) + '\n').encode('utf-8'))
            stream.flush(); os.fsync(stream.fileno())
        if os.name == 'nt':
            import ctypes
            kernel = ctypes.WinDLL('kernel32', use_last_error=True)
            move = kernel.MoveFileExW
            move.argtypes = [ctypes.c_wchar_p, ctypes.c_wchar_p, ctypes.c_uint32]
            move.restype = ctypes.c_int
            # WRITE_THROUGH without REPLACE_EXISTING: a concurrent publisher
            # cannot replace a start or acquisition marker.
            if not move(str(Path(name).resolve()), str(path.resolve()), 0x8):
                raise ctypes.WinError(ctypes.get_last_error())
        else:
            os.link(name, path)
            directory = os.open(path.parent, os.O_RDONLY)
            try: os.fsync(directory)
            finally: os.close(directory)
    finally:
        if os.path.exists(name): os.unlink(name)


class JournalLock:
    """OS-owned lifetime lock; a stale filename is not a live owner."""
    def __init__(self, directory: Path):
        self.path, self.handle = directory / 'operation.lock', None

    def acquire(self):
        require(self.handle is None, 'Journal lock already owned')
        handle = self.path.open('a+b')
        try:
            if self.path.stat().st_size == 0:
                handle.write(b'0'); handle.flush(); os.fsync(handle.fileno())
            handle.seek(0)
            if os.name == 'nt':
                import msvcrt
                msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BaseException:
            handle.close(); raise
        self.handle = handle

    def close(self):
        handle, self.handle = self.handle, None
        if handle is not None:
            try:
                handle.seek(0)
                if os.name == 'nt':
                    import msvcrt
                    msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
                else:
                    import fcntl
                    fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
            finally: handle.close()


def require_unstarted(directory: Path):
    require(not any((directory / name).exists() for name in START_MARKERS),
            'A prior install/recovery may already have started; use the installed-product path')


def persist_acquisition(directory: Path, state: dict) -> dict:
    """Called only after live preflight, exact retention and file fsync."""
    require(state.get('schema') == 'companion.wba.nor-initial-execution.v2' and
            state.get('writesStarted') is False and state.get('normalAfter') is False,
            'Acquisition must precede the first flash mutation')
    require(isinstance(state.get('sharedLeaseLine'), str) and
            state['sharedLeaseLine'].startswith('- **占用中**：Companion ') and
            str(directory.resolve() / 'result.json') in state['sharedLeaseLine'],
            'Exact original shared lease is absent from the acquisition')
    require_unstarted(directory)
    sizes = {'uid.bin': 12, 'device-id.bin': 4, 'flash-size.bin': 2, 'options.bin': 4,
             'freeze-before.bin': 4, 'private-internal-before.bin': 524288,
             'private-metadata-before.bin': 131072, 'current-sector.bin': 4096,
             'target-internal.bin': 524288,
             'before-ui.bin': None, 'retained-new-package.cup': None}
    files = {}
    for name, size in sizes.items():
        data = exact(directory, name, size)
        require(bool(data), 'Empty retained authority file: ' + name)
        files[name] = dict(bytes=len(data), sha256=sha(data))
    require(files['before-ui.bin']['sha256'] == state['plan']['beforeUiSha256'] and
            files['private-internal-before.bin']['sha256'] == state['plan']['beforeInternalSha256'] and
            files['private-metadata-before.bin']['sha256'] == state['plan']['beforeSystemSha256'] and
            files['target-internal.bin']['sha256'] == state['target']['internalTargetSha256'] and
            files['retained-new-package.cup']['sha256'] == state['target']['packageSha256'],
            'Acquisition file digests differ from the qualified live plan')
    value = dict(schema=AUTHORITY_SCHEMA, createdAt=now(), files=files,
                 state=json.loads(json.dumps(state)), privateKeyBytesExported=False,
                 scope='exact retained original/target and normal UART admission; no permission inference')
    new_durable_json(directory / AUTHORITY, value)
    authority_sha = sha(exact(directory, AUTHORITY))
    new_durable_json(directory / WRITE, dict(schema=PHASE_SCHEMA, phase='WRITES_AUTHORIZED', at=now(),
        authoritySha256=authority_sha, uid=state['requiredUid'],
        packageSha256=state['target']['packageSha256']))
    return dict(authoritySha256=authority_sha, writeMarkerSha256=sha(exact(directory, WRITE)))


def read_acquisition(directory: Path):
    require_unstarted(directory)
    value = load(directory / AUTHORITY)
    require(value.get('schema') == AUTHORITY_SCHEMA, 'Unknown immutable migration authority')
    state = value.get('state', {})
    require(state.get('schema') == 'companion.wba.nor-initial-execution.v2' and
            state.get('writesStarted') is False and state.get('normalAfter') is False,
            'Acquisition is not a pre-write normally admitted migration')
    require(isinstance(state.get('sharedLeaseLine'), str) and
            state['sharedLeaseLine'].startswith('- **占用中**：Companion ') and
            str(directory.resolve() / 'result.json') in state['sharedLeaseLine'],
            'Acquisition does not bind the original shared lease')
    required = {'uid.bin', 'device-id.bin', 'flash-size.bin', 'options.bin', 'freeze-before.bin',
                'private-internal-before.bin', 'private-metadata-before.bin',
                'current-sector.bin', 'target-internal.bin', 'before-ui.bin', 'retained-new-package.cup'}
    files = value.get('files', {})
    require(set(files) == required, 'Immutable acquisition file set differs')
    for name, info in files.items():
        require(type(info.get('bytes')) is int and info['bytes'] > 0, 'Bad acquisition file length')
        require(sha(exact(directory, name, info['bytes'])) == info.get('sha256'),
                'Immutable acquisition file changed: ' + name)
    authority_sha = sha(exact(directory, AUTHORITY))
    marker = load(directory / WRITE)
    require(marker.get('schema') == PHASE_SCHEMA and marker.get('phase') == 'WRITES_AUTHORIZED' and
            marker.get('authoritySha256') == authority_sha and marker.get('uid') == state.get('requiredUid') and
            marker.get('packageSha256') == state.get('target', {}).get('packageSha256'),
            'Pre-write durable authority marker differs')
    return state, dict(authoritySha256=authority_sha, writeMarkerSha256=sha(exact(directory, WRITE)))


def mark_start(directory: Path, name: str, uid: str, package_sha: str,
               authority: dict | None, recovery_directory: Path | None = None):
    require(name in START_MARKERS, 'Unknown publication marker')
    if name != 'recovery-completed.json': require_unstarted(directory)
    value = dict(schema=PHASE_SCHEMA, phase=('NORMAL_STARTUP_VERIFIED' if name == 'recovery-completed.json'
                                           else 'START_AUTHORIZED'), at=now(), uid=uid,
                 packageSha256=package_sha, authority=authority,
                 recoveryDirectory=str(recovery_directory) if recovery_directory else None)
    new_durable_json(directory / name, value)
