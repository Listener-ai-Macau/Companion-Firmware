"""Loopback browser acceptance of an explicit installed-firmware host build.

Only native committed 200x200 framebuffers are displayed. Hardware, recording,
settings persistence and IMU acquisition are simulated; no device I/O occurs.
"""
from pathlib import Path
from datetime import datetime
import argparse, base64, copy, ctypes, hashlib, importlib.util, io, json, sys, threading, time, uuid
from collections import OrderedDict
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit
from PIL import Image

ROOT=Path(__file__).resolve().parents[1]

def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()

class BrowserRuntime:
    def __init__(self, build, evidence):
        self.manifest=json.loads(Path(build).read_bytes())
        m=self.manifest
        for f,digest in m['inputs'].items():
            if sha(f)!=digest: raise RuntimeError('Frozen input changed: '+f)
        if sha(m['library'])!=m['librarySha256']: raise RuntimeError('Library changed')
        source=Path(m['frozenSource'])
        sys.path.insert(0,str(source/'tools'))
        spec=importlib.util.spec_from_file_location('bound_wba_preview',source/'tools/wba_runtime_preview.py')
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        self.runtime=module.Runtime(Path(m['resourceDirectory'])/'ui-partition.bin',Path(m['library']))
        if sha(self.runtime.image_path)!=m['resourceImageSha256']: raise RuntimeError('Resource changed')
        for name,n in [('cp_wake_key',0),('cp_motion_pose',2),('cp_update',2),('cp_power_state',3)]:
            fn=getattr(self.runtime.lib,name);fn.argtypes=[ctypes.c_uint]*n;fn.restype=None
        self.runtime.lib.cp_settings.argtypes=[];self.runtime.lib.cp_settings.restype=ctypes.c_char_p
        self.evidence=Path(evidence);self.evidence.mkdir(parents=True,exist_ok=True)
        self.events=self.evidence/'browser-events.jsonl'
        self.last_version=-1;self.panel_ms=600;self.battery=None;self.record_id=0
        self.display_snapshots=OrderedDict()
        self.start()
    def log(self,kind,value):
        row={'atLocal':datetime.now().astimezone().isoformat(timespec='milliseconds'),
             'kind':kind,'firmware':self.manifest['firmware'],'ui':self.manifest['uiGeneration'],
             'sessionId':self.session_id,**value}
        with self.events.open('a',encoding='utf-8') as f:f.write(json.dumps(row,ensure_ascii=False)+'\n')
    def start(self):
        r=self.runtime
        with r.lock:
            self.session_id=uuid.uuid4().hex;self.display_snapshots.clear()
            r.reset();r.lib.cp_panel(self.panel_ms,0);r.lib.cp_language(1)
            now=datetime.now();r.lib.cp_clock(now.hour,now.minute)
            self.battery=None;self.last_clock=(now.hour,now.minute);self.last_version=-1
            self.log('reset',{'panelModelMs':self.panel_ms,'state':r.state()})
    def step(self):
        r=self.runtime
        with r.lock:
            now=datetime.now();clock=(now.hour,now.minute)
            if clock!=self.last_clock:
                r.lib.cp_clock(*clock);self.last_clock=clock
                if self.battery is not None:r.lib.cp_power_state(0,self.battery,0)
            r.advance(int((time.monotonic()-r.started)*1000))
            s=r.state()
            if s['version']!=self.last_version:
                raw=r.raw();self.last_version=s['version']
                self.log('commit',{'state':s,'frameSha256':hashlib.sha256(raw).hexdigest()})
    def state(self):
        with self.runtime.lock:
            s=self.runtime.state(True)
            s['identity']={k:self.manifest[k] for k in ('firmware','uiGeneration','firmwareSourceCommit','resourceImageSha256')}
            for key in ('candidateLabel','installedBaseline','deliveryState'):
                s['identity'][key]=self.manifest.get(key,'')
            s['hardwareSimulated']=True;s['batterySimulated']=self.battery
            s['settings']=json.loads(self.runtime.lib.cp_settings())
            s['sessionId']=self.session_id
            # Cache only real native snapshots issued to a browser. An opinion
            # refers to the image already decoded/displayed by that client,
            # never a newly sampled server frame. Bounded host-only memory.
            key=(s['version'],s['frameSha256'])
            if s['version']>0 and key not in self.display_snapshots:
                self.display_snapshots[key]=copy.deepcopy(s)
                while len(self.display_snapshots)>64:self.display_snapshots.popitem(last=False)
            return s
    def command(self,data):
        r=self.runtime
        with r.lock:
            kind=data.get('kind')
            if kind=='reset':self.start();ok=True
            elif kind=='wake':r.lib.cp_wake_key();ok=True
            elif kind=='motion':
                flags,tilt=int(data.get('flags',0)),int(data.get('tilt',255))
                if flags not in (1,2,4,8,16,32,64) or tilt not in (*range(6),255):raise ValueError('Invalid simulated motion')
                r.lib.cp_motion_pose(flags,tilt);ok=True
            elif kind=='battery':
                value=data.get('percent');value=255 if value is None else int(value)
                if value!=255 and not 0<=value<=100:raise ValueError('Invalid battery')
                self.battery=value if value!=255 else None;r.lib.cp_power_state(0,value,0);ok=True
            elif kind=='update':
                phase,percent=int(data['phase']),int(data['percent'])
                if not 0<=phase<=7 or percent not in (*range(101),255):raise ValueError('Invalid update')
                r.lib.cp_update(phase,percent);ok=True
            elif kind=='review':
                verdict=data.get('verdict');note=str(data.get('note',''))[:1500];item=str(data.get('item','整体'))[:100]
                if verdict not in ('通过','有问题','未看清'):raise ValueError('Invalid verdict')
                if not data.get('sessionId'):
                    raise ValueError('页面已更新，请刷新此页后再记录。')
                if data.get('sessionId')!=self.session_id:
                    raise ValueError('运行器已重新开始，请看到新画面后再记录。')
                key=(int(data.get('displayVersion',-1)),str(data.get('displaySha256','')))
                if key not in self.display_snapshots:
                    raise ValueError('这幅画面的记录已过期，请看到当前画面后再记录。')
                state=copy.deepcopy(self.display_snapshots[key]);stamp=datetime.now().strftime('%Y%m%d-%H%M%S-%f')
                image=self.evidence/(stamp+'.png');image.write_bytes(base64.b64decode(state.pop('png')))
                self.log('owner-review',{'item':item,'verdict':verdict,'note':note,'state':state,'image':str(image),
                    'currentServerVersion':r.state()['version'],'displayFrameMatched':True,
                    'scope':'BROWSER_SOFTWARE_ONLY_NOT_PHYSICAL_ACCEPTANCE'})
                return {'accepted':True,'saved':str(image)}
            else:
                ok=r.command(data)
                if kind=='panel':self.panel_ms=int(data['latencyMs'])
            self.log('input',{'input':data,'accepted':ok,'state':r.state()})
            return {'accepted':ok}

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--build',type=Path,required=True);p.add_argument('--evidence',type=Path,required=True)
    p.add_argument('--port',type=int,default=8893);a=p.parse_args()
    model=BrowserRuntime(a.build,a.evidence)
    page=(Path(model.manifest['frozenSource'])/'tools/pet_browser.html').read_bytes()
    stop=threading.Event()
    def stepper():
        try:
            while not stop.wait(.008):model.step()
        except Exception as error:
            model.log('runtime-error',{'error':repr(error)});stop.set()
    threading.Thread(target=stepper,daemon=True).start()
    class Handler(BaseHTTPRequestHandler):
        def log_message(self,*_):pass
        def reply(self,body,content='application/json; charset=utf-8',status=200):
            if not isinstance(body,bytes):body=json.dumps(body,ensure_ascii=False).encode()
            self.send_response(status);self.send_header('Content-Type',content)
            self.send_header('Cache-Control','no-store');self.send_header('Content-Length',str(len(body)))
            self.send_header('X-Content-Type-Options','nosniff');self.end_headers();self.wfile.write(body)
        def do_GET(self):
            path=urlsplit(self.path).path
            if path=='/api/state':self.reply(model.state());return
            if path=='/api/identity':self.reply(model.manifest);return
            if path in ('/','/art/','/runtime/'):
                self.reply(page,'text/html; charset=utf-8');return
            self.reply({'error':'Not found'},status=404)
        def do_POST(self):
            origin=self.headers.get('Origin')
            if origin and origin not in (f'http://127.0.0.1:{a.port}',f'http://localhost:{a.port}'):
                self.reply({'error':'Origin not allowed'},status=403);return
            if self.path!='/api/input':self.reply({'error':'Not found'},status=404);return
            try:
                size=int(self.headers.get('Content-Length','0'))
                if not 0<size<=8192:raise ValueError('Invalid request size')
                value=model.command(json.loads(self.rfile.read(size)));self.reply(value)
            except (ValueError,KeyError,TypeError) as error:self.reply({'error':str(error)},status=400)
    server=ThreadingHTTPServer(('127.0.0.1',a.port),Handler)
    print(f'READY http://127.0.0.1:{a.port}/ FW{model.manifest["firmware"]} UI{model.manifest["uiGeneration"]}',flush=True)
    try:server.serve_forever()
    finally:stop.set();server.server_close()

if __name__=='__main__':main()
