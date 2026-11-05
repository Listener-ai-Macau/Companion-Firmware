"""Installed official CubeProgrammer API, one connection through read/write/reset.

Signatures and layouts come from this machine's api/include/CubeProgrammer_API.h.
NORMAL_MODE uses software reset then halt; it does not require an NRST wire.
"""
import ctypes as c
import os
from pathlib import Path


class Freq(c.Structure):
    _fields_ = [('jtagFreq', c.c_uint * 12), ('jtagFreqNumber', c.c_uint),
                ('swdFreq', c.c_uint * 12), ('swdFreqNumber', c.c_uint)]


class Params(c.Structure):
    _fields_ = [('dbgPort', c.c_int), ('index', c.c_int),
                ('serialNumber', c.c_char * 33), ('firmwareVersion', c.c_char * 20),
                ('targetVoltage', c.c_char * 5), ('accessPortNumber', c.c_int),
                ('accessPort', c.c_int), ('connectionMode', c.c_int),
                ('resetMode', c.c_int), ('isOldFirmware', c.c_int), ('freq', Freq),
                ('frequency', c.c_int), ('isBridge', c.c_int), ('shared', c.c_int),
                ('board', c.c_char * 100), ('DBG_Sleep', c.c_int), ('speed', c.c_int)]


Init = c.CFUNCTYPE(None)
Log = c.CFUNCTYPE(None, c.c_int, c.c_wchar_p)
Bar = c.CFUNCTYPE(None, c.c_int, c.c_int)


class Callbacks(c.Structure):
    _fields_ = [('initProgressBar', Init), ('logMessage', Log), ('loadBar', Bar)]


class Session:
    def __init__(self, serial, output, check_lease, connection_mode=0, access_port=None):
        self.serial, self.output, self.lease = serial, output, check_lease
        self.connection_mode = connection_mode
        if access_port is not None and (type(access_port) is not int or not 0 <= access_port <= 255):
            raise ValueError("Invalid explicit debug access port")
        self.access_port = access_port
        self.api = None
        self.log = None
        self.directories = []
        self.interfaces = c.POINTER(Params)()

    def __enter__(self):
        self.lease()
        root = Path('C:/ST/STM32CubeProgrammer')
        assert c.sizeof(Params) == 312
        assert (root / 'bin/FlashLoader').is_dir()
        self.log = (self.output / 'official-api.log').open('w', encoding='utf-8')
        try:
            self.directories = [os.add_dll_directory(str(root / 'api/lib')),
                                os.add_dll_directory(str(root / 'bin'))]
            self.api = c.CDLL(str(root / 'api/lib/CubeProgrammer_API.dll'))
            signatures = {
                'setDisplayCallbacks': ([Callbacks], None),
                'setVerbosityLevel': ([c.c_int], None),
                'setLoadersPath': ([c.c_char_p], None),
                'getStLinkEnumerationList': ([c.POINTER(c.POINTER(Params)), c.c_int], c.c_int),
                'connectStLink': ([Params], c.c_int),
                'readMemory': ([c.c_uint, c.POINTER(c.POINTER(c.c_ubyte)), c.c_uint], c.c_int),
                'freeLibraryMemory': ([c.c_void_p], None),
                'writeMemory': ([c.c_uint, c.c_void_p, c.c_uint], c.c_int),
                'downloadFile': ([c.c_wchar_p, c.c_uint, c.c_uint, c.c_uint, c.c_wchar_p], c.c_int),
                'readCortexReg': ([c.c_uint,c.POINTER(c.c_uint)], c.c_int),
                'reset': ([c.c_int], c.c_int),
                'disconnect': ([], None), 'deleteInterfaceList': ([], None),
            }
            for name, (arguments, result) in signatures.items():
                fn = getattr(self.api, name)
                fn.argtypes, fn.restype = arguments, result
            def log(kind, message):
                self.log.write(f'{kind}: {message}\n')
                self.log.flush()
            self.callbacks = Callbacks(Init(lambda: None), Log(log), Bar(lambda x, n: None))
            self.api.setDisplayCallbacks(self.callbacks)
            self.api.setVerbosityLevel(1)
            self.api.setLoadersPath(os.fsencode(root / 'bin'))
            self.lease()
            count = self.api.getStLinkEnumerationList(c.byref(self.interfaces), 0)
            matches = [Params.from_buffer_copy(bytes(self.interfaces[i])) for i in range(max(0, count))
                       if self.interfaces[i].serialNumber.decode('ascii') == self.serial]
            if len(matches) != 1:
                raise RuntimeError('Fixed V3 must enumerate exactly once')
            params = matches[0]
            params.dbgPort, params.connectionMode, params.resetMode = 1, self.connection_mode, 0
            params.frequency, params.shared = 1000, 0
            if self.access_port is not None:
                # Same supported accessPort selector as the official C header.
                # WBA logs already identify AP1; explicit selection avoids
                # relying on repeated AP0-failure fallback during recovery.
                params.accessPort = self.access_port
            self.log.write(f"HOST_PARAMETERS accessPort={params.accessPort} mode={params.connectionMode} frequency={params.frequency}\n")
            self.log.flush()
            self.lease()
            self.checked(self.api.connectStLink(params), ('HOTPLUG' if self.connection_mode == 1 else 'NORMAL/SOFTWARE_RESET') + ' connect')
            return self
        except BaseException:
            self.close()
            raise

    @staticmethod
    def checked(status, operation):
        if status != 0:
            # Names from the installed CubeProgrammer_API.h, not a guessed
            # electrical/USB diagnosis. A memory I/O error alone identifies
            # neither a discharged battery nor a broken probe.
            names={-1:'NOT_CONNECTED',-2:'NO_DEVICE',-3:'CONNECTION',
                -7:'NO_MEM',-8:'WRONG_PARAM',-9:'READ_MEM',-10:'WRITE_MEM',-11:'ERASE_MEM'}
            raise RuntimeError(f'{operation}: official API rc={status} CUBEPROGRAMMER_ERROR_{names.get(status,"OTHER")}')

    def read(self, address, size, name):
        self.lease()
        target = self.output / name
        if target.exists():
            raise RuntimeError('Refuse to overwrite readback ' + name)
        pointer = c.POINTER(c.c_ubyte)()
        owned = False
        try:
            status = self.api.readMemory(address, c.byref(pointer), size)
            # Match ST's Example1: release only a buffer returned by a
            # successful read. On error, ownership of a non-null output is
            # unspecified; it may already have been released by the DLL.
            owned = status == 0
            self.checked(status, 'read ' + name)
            if not pointer:
                raise RuntimeError('No official read buffer ' + name)
            value = c.string_at(pointer, size)
            target.write_bytes(value)
            return value
        finally:
            if owned and pointer:
                self.api.freeLibraryMemory(c.cast(pointer, c.c_void_p))

    def word(self, address, value):
        self.lease()
        # Only restore/freeze the same watchdog debug bit used by the prior installer.
        if address != 0xE0044008:
            raise RuntimeError('Unexpected peripheral write')
        buffer = c.create_string_buffer(value.to_bytes(4, 'little'))
        self.checked(self.api.writeMemory(address, buffer, 4), 'debug watchdog freeze')

    def core_register(self, register):
        self.lease()
        if register not in (15,17):raise ValueError('Only PC/MSP observation is used here')
        value=c.c_uint()
        self.checked(self.api.readCortexReg(register,c.byref(value)), 'read core register')
        return value.value

    def reset(self):
        self.lease()
        self.checked(self.api.reset(0), 'software reset after verified image')

    def close(self):
        if self.api is not None:
            try:
                self.api.disconnect()
            finally:
                self.api.deleteInterfaceList()
            self.api = None
        for directory in self.directories:
            directory.close()
        self.directories = []
        if self.log is not None:
            self.log.close()
            self.log = None

    def __exit__(self, *exception):
        self.close()
