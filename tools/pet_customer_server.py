"""Local headless customer surface over the same production-C pet display.

This exposes ordinary contact input and the existing public simulated physical
controls. Capture/menu/petting must enter through ordinary screen contacts;
the public API has no direct business action or settings shortcuts. Native
committed pixels remain authoritative; no browser or device is accessed.
"""
import argparse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import threading
from urllib.parse import urlsplit
from pathlib import Path
from pet_browser import BrowserRuntime

CONTROLS = {
    'wake': '短按实体键唤醒（模拟）',
    'pickup': '模拟拿起', 'putdown': '模拟放稳', 'shake': '模拟轻晃',
    'tilt-left': '模拟向左倾斜', 'tilt-right': '模拟向右倾斜',
}
# Match P213's existing public pet_browser.html controls exactly. These are
# acquisition flags/tilt codes, not enum ordinals or chosen expression IDs.
MOTION = {'pickup': (1,255), 'putdown': (8,0), 'shake': (2,255),
          'tilt-left': (64,1), 'tilt-right': (64,2)}


def public_state(model):
    s = model.state()
    rec = s['recording']
    status = ('模拟录音中' if s['capturing'] else
              '模拟录音准备中' if s['preparing'] else
              {3:'正在保存模拟录音', 5:'最近模拟录音已保存 · 电脑Type查看',
               6:'正在模拟同步', 7:'模拟录音已同步 · 电脑Type查看',
               8:'模拟录音异常，请检查状态'}.get(rec, '未在录音'))
    return {
        'sessionId': s['sessionId'], 'version': s['version'],
        'frameSha256': s['frameSha256'], 'png': s['png'],
        'width': 200, 'height': 200, 'nowMs': s['nowMs'],
        'candidate': model.manifest.get('candidateLabel', ''),
        'auxiliaryStatus': status,
        'waitingForDisplay': s['panelPending'],
        'scope': 'HEADLESS_NATIVE_C_CUSTOMER_USE_SIMULATED_PERIPHERALS',
        'notPhysicalAcceptance': True,
    }


def command(model, data):
    if data.get('kind') == 'touch':
        if set(data) != {'kind','down','x','y'} or type(data['down']) is not bool:
            raise ValueError('Ordinary touch requires down=true/false and x,y')
        x,y = data['x'],data['y']
        if type(x) is not int or type(y) is not int or not 0<=x<200 or not 0<=y<200:
            raise ValueError('Touch outside200x200 display')
        return model.command(data)
    if set(data) != {'kind','control'} or data.get('kind') != 'control':
        raise ValueError('Only ordinary touch or a public simulated control is available')
    control = data['control']
    if control == 'wake':
        return model.command({'kind':'wake'})
    if control in MOTION:
        flags,tilt = MOTION[control]
        return model.command({'kind':'motion','flags':flags,'tilt':tilt})
    raise ValueError('Unknown public control')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--build',type=Path,required=True)
    parser.add_argument('--evidence',type=Path,required=True)
    parser.add_argument('--port',type=int,default=8894)
    args = parser.parse_args()
    if not 1024<=args.port<=65535:
        parser.error('Use a local unprivileged port')
    model = BrowserRuntime(args.build,args.evidence)
    stop = threading.Event()
    def step():
        try:
            while not stop.wait(.008): model.step()
        except Exception as error:
            model.log('runtime-error',{'error':repr(error)})
            stop.set()
    threading.Thread(target=step,daemon=True).start()
    class Handler(BaseHTTPRequestHandler):
        def log_message(self,*_): pass
        def reply(self,body,status=200):
            encoded=json.dumps(body,ensure_ascii=False).encode('utf8')
            self.send_response(status)
            self.send_header('Content-Type','application/json; charset=utf-8')
            self.send_header('Cache-Control','no-store')
            self.send_header('Content-Length',str(len(encoded)))
            self.end_headers();self.wfile.write(encoded)
        def do_GET(self):
            path=urlsplit(self.path).path
            if path=='/state':self.reply(public_state(model))
            elif path=='/controls':self.reply({'controls':CONTROLS,'touch':'x,y within200x200; hold/drag are ordinary contact sequences'})
            else:self.reply({'error':'Not found'},404)
        def do_POST(self):
            if self.path!='/input':return self.reply({'error':'Not found'},404)
            # A browser cannot use this local customer surface as a fallback
            # controller. The supported client is the explicit background tool.
            if self.headers.get('Origin'):return self.reply({'error':'Background client only'},403)
            try:
                n=int(self.headers.get('Content-Length','0'))
                if not 0<n<=1024:raise ValueError('Invalid request size')
                data=json.loads(self.rfile.read(n))
                self.reply(command(model,data))
            except (ValueError,TypeError,KeyError) as error:
                self.reply({'error':str(error)},400)
    server=ThreadingHTTPServer(('127.0.0.1',args.port),Handler)
    print(f'READY HEADLESS_CUSTOMER http://127.0.0.1:{args.port}',flush=True)
    try:server.serve_forever()
    finally:stop.set();server.server_close()


if __name__=='__main__':main()
