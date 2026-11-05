#!/usr/bin/env python3
"""Real C expression runtime with explicitly simulated hardware, loopback only.

No fake resource provider: mount the exact WBA static UI image. The browser only
receives committed framebuffers. No audio is captured and no device is changed.
"""
from pathlib import Path
import argparse
import base64
import ctypes
import functools
import hashlib
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import io
import json
import subprocess
import threading
import time
from urllib.parse import urlsplit
from PIL import Image
from test_wba_runtime import ROOT, APP, INCLUDES, SOURCES
from verify_wba_spi_nor_adapter import find_vsdevcmd
from build_wba_prehardware import run
from wba_resource_geometry import from_profile as resource_geometry

OUT=ROOT/'.cache/wba-runtime-preview'
PUBLIC=ROOT/'.cache/wba-visual-review'
IMAGE=ROOT/'.cache/wba-product-resources/ui-partition.bin'
EXTRA=[APP/p for p in ('runtime/companion_renderer.c','runtime/companion_resources.c',
    'runtime/companion_pet_behavior.c','runtime/companion_pet_face.c',
    'epaper/asset_store.c','epaper/emote_asset_pack.c','epaper/emote_player.c','epaper/ui_asset_generation.c',
    'runtime/tests/wba_runtime_preview.c')]

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()

def build():
    OUT.mkdir(parents=True,exist_ok=True)
    log=OUT/'build.log';log.write_text('',encoding='utf-8')
    dll=OUT/'wba-runtime-preview.dll'
    bank=next((p for p in INCLUDES if (p/'profile.json').is_file() and (p/'ui-partition.bin').is_file()),IMAGE.parent)
    profile=json.loads((bank/'profile.json').read_text())
    static_bytes=(bank/'ui-partition.bin').stat().st_size
    flash_geometry=resource_geometry(profile,static_bytes) if profile.get('storageLayoutVersion')==3 else None
    args=['cl.exe','/nologo','/std:c11','/W4','/WX','/utf-8','/LD',
        '/DCOMPANION_SCREEN_COMP_REQ_638_SOURCE_PACK=1','/DCOMPANION_WBA_RESOURCE_PROFILE=1',
        f'/DCOMP_WBA_NOR_UI_BYTES={static_bytes}u',
        f'/DCOMP_WBA_NOR_TOTAL_BYTES={flash_geometry["norBytes"] if flash_geometry else 16777216}u',
        *(f'/I{p}' for p in INCLUDES),*(str(p) for p in [*SOURCES,*EXTRA]),f'/Fe:{dll}']
    script=OUT/'build.cmd'
    script.write_text(f'@echo off\ncall "{find_vsdevcmd()}" -arch=amd64 -host_arch=amd64 >nul\nif errorlevel 1 exit /b %errorlevel%\n'+subprocess.list2cmdline(args)+'\n',encoding='utf-8')
    run(['cmd.exe','/d','/c',str(script)],OUT,log)
    sources=[Path(__file__),*SOURCES,*EXTRA,*INCLUDES[0].glob('*.h'),*INCLUDES[1].glob('*.h'),APP/'epaper/ssd1681_wba.h']
    receipt={'result':'BUILT_HOST_RUNTIME_ADAPTER','hardwareAcceptance':'NOT_RUN','staticResourceBytes':static_bytes,
        'dll_sha256':sha(dll),'source_sha256':{p.relative_to(ROOT).as_posix():sha(p) for p in sources}}
    (OUT/'build-result.json').write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8')
    return dll

class Runtime:
    def __init__(self,image=IMAGE,dll=None,seed=17):
        self.image_path=Path(image);self.image=self.image_path.read_bytes()
        if len(self.image)<8192 or len(self.image)%4096:raise ValueError('Expected a sector-aligned complete static UI bank')
        self.backing=(ctypes.c_uint8*len(self.image)).from_buffer_copy(self.image)
        self.lib=ctypes.CDLL(str(dll or OUT/'wba-runtime-preview.dll'))
        self.lib.cp_init.argtypes=[ctypes.POINTER(ctypes.c_uint8),ctypes.c_uint32,ctypes.c_uint32]
        self.lib.cp_init.restype=ctypes.c_int
        for name,args in {'cp_step':[ctypes.c_uint32],'cp_touch':[ctypes.c_uint]*3,
                          'cp_clock':[ctypes.c_uint]*2,'cp_panel':[ctypes.c_uint]*2,
                          'cp_family':[ctypes.c_uint],'cp_language':[ctypes.c_uint],'cp_pose':[ctypes.c_uint]*2,'cp_action':[ctypes.c_uint],
                          'cp_menu_backend':[ctypes.c_uint]*2,'cp_menu_complete':[ctypes.c_uint]*2}.items():
            getattr(self.lib,name).argtypes=args
            getattr(self.lib,name).restype=ctypes.c_int if name in ('cp_action','cp_menu_complete') else None
        self.lib.cp_frame.argtypes=[];self.lib.cp_frame.restype=ctypes.POINTER(ctypes.c_uint8)
        self.lib.cp_snapshot.argtypes=[];self.lib.cp_snapshot.restype=ctypes.c_char_p
        self.lib.cp_cancel.argtypes=[];self.lib.cp_cancel.restype=None
        self.lock=threading.RLock();self.now=0;self.seed=seed;self.reset()
    def reset(self):
        with self.lock:
            if not self.lib.cp_init(self.backing,len(self.image),self.seed):
                raise RuntimeError('Production resource mount rejected this UI image')
            self.now=0;self.seed+=1;self.started=time.monotonic();self.cached_version=-1;self.cached_png=''
    def advance(self,until):
        while self.now<until:
            self.now=min(self.now+4,until);self.lib.cp_step(self.now)
    def raw(self):return ctypes.string_at(self.lib.cp_frame(),5000)
    def state(self,with_pixels=False):
        with self.lock:
            state=json.loads(self.lib.cp_snapshot())
            if with_pixels:
                if self.cached_version!=state['version']:
                    raw=self.raw();buffer=io.BytesIO();Image.frombytes('1',(200,200),raw).save(buffer,format='PNG')
                    self.cached_png=base64.b64encode(buffer.getvalue()).decode('ascii')
                    self.cached_sha=hashlib.sha256(raw).hexdigest();self.cached_version=state['version']
                state.update(png=self.cached_png,frameSha256=self.cached_sha,
                    resourceImageSha256=hashlib.sha256(self.image).hexdigest(),
                    scope='PRODUCTION_C_RUNTIME_WITH_SIMULATED_PERIPHERALS')
            return state
    def command(self,data):
        with self.lock:
            kind=data.get('kind')
            if kind=='touch':
                x,y=int(data['x']),int(data['y'])
                if not 0<=x<200 or not 0<=y<200:raise ValueError('Touch outside display')
                self.lib.cp_touch(int(bool(data.get('down'))),x,y)
            elif kind=='action':
                action=int(data['action'])
                if not 1<=action<=8:raise ValueError('Unknown action')
                return bool(self.lib.cp_action(action))
            elif kind=='family':
                family=int(data['family'])
                if not 0<=family<10:raise ValueError('Unknown family')
                self.lib.cp_family(family)
            elif kind=='menuBackend':
                mode,delay=int(data['mode']),int(data.get('delayMs',0))
                if not 0<=mode<=5 or not 0<=delay<=120000:raise ValueError('Invalid simulated menu backend')
                self.lib.cp_menu_backend(mode,delay)
            elif kind=='menuComplete':
                token,result=int(data['token']),int(data['result'])
                if not 0<token<=0xffffffff or not 0<=result<=3:raise ValueError('Invalid menu completion')
                return bool(self.lib.cp_menu_complete(token,result))
            elif kind=='panel':
                latency=int(data['latencyMs'])
                if not 20<=latency<=2000:raise ValueError('Panel latency outside range')
                self.lib.cp_panel(latency,int(bool(data.get('fail'))))
            elif kind=='clock':
                hour,minute=int(data['hour']),int(data['minute'])
                if not 0<=hour<24 or not 0<=minute<60:raise ValueError('Invalid local time')
                self.lib.cp_clock(hour,minute)
            elif kind=='reset':self.reset()
            elif kind=='cancel':self.lib.cp_cancel()
            else:raise ValueError('Unknown command')
            return True

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--build-only',action='store_true')
    parser.add_argument('--skip-build',action='store_true')
    parser.add_argument('--image',type=Path,default=IMAGE)
    parser.add_argument('--port',type=int,default=8877)
    args=parser.parse_args()
    if not args.skip_build:build()
    if args.build_only:return 0
    runtime=Runtime(args.image)
    destination=PUBLIC/'runtime';destination.mkdir(parents=True,exist_ok=True)
    (destination/'index.html').write_bytes((ROOT/'tools/wba_runtime_preview.html').read_bytes())
    stopped=threading.Event()
    def stepper():
        while not stopped.wait(.004):
            with runtime.lock:runtime.advance(int((time.monotonic()-runtime.started)*1000))
    threading.Thread(target=stepper,name='production-c-runtime',daemon=True).start()
    class Handler(SimpleHTTPRequestHandler):
        def log_message(self,*_):pass
        def reply(self,value,status=200):
            body=json.dumps(value,ensure_ascii=False).encode('utf-8')
            self.send_response(status);self.send_header('Content-Type','application/json; charset=utf-8')
            self.send_header('Cache-Control','no-store');self.send_header('Content-Length',str(len(body)))
            self.end_headers();self.wfile.write(body)
        def do_GET(self):
            route=urlsplit(self.path).path
            if route=='/api/state':self.reply(runtime.state(True));return
            if route in ('/','/art/','/art/index.html'):self.path='/runtime/index.html'
            super().do_GET()
        def do_POST(self):
            # Only this local preview page may mutate the in-memory simulator.
            # Requests never flash hardware, record audio, or change disk data.
            origin=self.headers.get('Origin')
            if origin and origin not in (f'http://127.0.0.1:{args.port}',f'http://localhost:{args.port}'):
                self.reply({'error':'Origin not allowed'},403);return
            if self.path!='/api/input':self.reply({'error':'Not found'},404);return
            try:
                length=int(self.headers.get('Content-Length','0'))
                if not 0<length<=2048:raise ValueError('Invalid input length')
                data=json.loads(self.rfile.read(length));accepted=runtime.command(data)
                self.reply({'accepted':accepted})
            except (ValueError,KeyError,TypeError) as error:self.reply({'error':str(error)},400)
    server=ThreadingHTTPServer(('127.0.0.1',args.port),functools.partial(Handler,directory=str(PUBLIC)))
    print(f'READY http://127.0.0.1:{args.port}/art/ image={sha(args.image)} simulated_hardware=1',flush=True)
    try:server.serve_forever()
    finally:stopped.set();server.server_close()
    return 0

if __name__=='__main__':raise SystemExit(main())
