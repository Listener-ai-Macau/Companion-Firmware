"""Owner-operated finite speaker/reference capture; no BLE, flash or reset."""
from pathlib import Path
from datetime import datetime, timezone, timedelta
import argparse, ctypes, hashlib, json, os, queue, re, sys, tempfile, threading, time, wave
import tkinter as tk
from tkinter import ttk
import numpy as np
import serial
from serial.tools import list_ports
from diagnose_wba_uart import parse_frames

SN='004400403532510B31333430';UID='180010000d50335754363720'
NOW=lambda:datetime.now(timezone(timedelta(hours=8))).isoformat(timespec='milliseconds')
PRESETS={
 '频段对照：1.5k → 2k → 确认音（约10秒）':(-1,'COMPARE'),
 '1kHz 标准纯音（1秒）':(8,'SOUND REF 1'),
 '1.5kHz 标准纯音（1秒）':(9,'SOUND REF 2'),
 '2kHz 标准纯音（1秒）':(10,'SOUND REF 3'),
 '柔和非语言参考（约半秒）':(11,'SOUND SOFT'),
 '确认下降音':(0,'SOUND'), '欢迎短音':(4,'SOUND 4'),
 '满足短音':(5,'SOUND 5'), '活泼短音':(6,'SOUND 6'), '害羞短音':(7,'SOUND 7')}

def atomic(path,data):
    fd,temp=tempfile.mkstemp(prefix=path.name+'.',dir=path.parent)
    try:
        with os.fdopen(fd,'wb') as f:f.write(data);f.flush();os.fsync(f.fileno())
        os.replace(temp,path)
    finally:
        if os.path.exists(temp):os.unlink(temp)
def save(path,value):atomic(path,(json.dumps(value,ensure_ascii=False,indent=2)+'\n').encode())

class Format(ctypes.Structure):
    _pack_=2
    _fields_=[('tag',ctypes.c_ushort),('channels',ctypes.c_ushort),('rate',ctypes.c_uint),('byteRate',ctypes.c_uint),('align',ctypes.c_ushort),('bits',ctypes.c_ushort),('extra',ctypes.c_ushort)]
class Header(ctypes.Structure):
    _fields_=[('data',ctypes.c_void_p),('length',ctypes.c_uint),('recorded',ctypes.c_uint),('user',ctypes.c_size_t),('flags',ctypes.c_uint),('loops',ctypes.c_uint),('next',ctypes.c_void_p),('reserved',ctypes.c_size_t)]
class Microphone:
    def __init__(self,path,seconds):
        self.path=path;self.mm=ctypes.WinDLL('winmm');self.handle=ctypes.c_void_p();self.fmt=Format(1,1,16000,32000,2,16,0)
        self.buffer=ctypes.create_string_buffer(seconds*32000);self.header=Header(ctypes.addressof(self.buffer),len(self.buffer),0,0,0,0,None,0)
        self.opened=self.prepared=self.started=self.closed=False
        for name,args in [('waveInOpen',[ctypes.POINTER(ctypes.c_void_p),ctypes.c_uint,ctypes.POINTER(Format),ctypes.c_size_t,ctypes.c_size_t,ctypes.c_uint]),('waveInPrepareHeader',[ctypes.c_void_p,ctypes.POINTER(Header),ctypes.c_uint]),('waveInAddBuffer',[ctypes.c_void_p,ctypes.POINTER(Header),ctypes.c_uint]),('waveInUnprepareHeader',[ctypes.c_void_p,ctypes.POINTER(Header),ctypes.c_uint])]:getattr(self.mm,name).argtypes=args
        for name in ['waveInStart','waveInStop','waveInReset','waveInClose']:getattr(self.mm,name).argtypes=[ctypes.c_void_p]
        try:
            assert self.mm.waveInOpen(ctypes.byref(self.handle),0,ctypes.byref(self.fmt),0,0,0)==0,'电脑麦克风无法打开'
            self.opened=True
            assert self.mm.waveInPrepareHeader(self.handle,ctypes.byref(self.header),ctypes.sizeof(self.header))==0
            self.prepared=True
            assert self.mm.waveInAddBuffer(self.handle,ctypes.byref(self.header),ctypes.sizeof(self.header))==0
            assert self.mm.waveInStart(self.handle)==0
            self.started=True;self.start=time.monotonic()
        except BaseException:self.close();raise
    def close(self):
        if self.closed:return
        if self.started:self.mm.waveInStop(self.handle);self.mm.waveInReset(self.handle)
        if self.prepared:self.mm.waveInUnprepareHeader(self.handle,ctypes.byref(self.header),ctypes.sizeof(self.header))
        if self.opened:self.mm.waveInClose(self.handle)
        self.closed=True
        if self.header.recorded:
            with wave.open(str(self.path),'wb') as w:w.setnchannels(1);w.setsampwidth(2);w.setframerate(16000);w.writeframes(self.buffer.raw[:self.header.recorded])

def analyze(folder,fixtures):
    r=json.loads((folder/'result.json').read_bytes())
    with wave.open(str(folder/'pc-microphone.wav')) as w:x=np.frombuffer(w.readframes(w.getnframes()),'<i2').astype(float)
    items=[]
    for command in r['commands']:
        cue=command.get('cue',r['cue'])
        pcm=fixtures/f'cue{cue}.pcm'
        y=np.frombuffer(pcm.read_bytes(),'<i2').astype(float);n=len(y)
        a=command['monotonic']-r['microphoneStartMonotonic'];b=command['replyMonotonic']-r['microphoneStartMonotonic']
        start=max(0,int((a-.1)*16000));end=min(len(x),int((b+.5)*16000));z=x[start:end]
        if len(z)<n:continue
        z=z-z.mean();template=y-y.mean();N=1<<((len(z)+n-2).bit_length())
        v=np.fft.irfft(np.fft.rfft(z,N)*np.fft.rfft(template[::-1],N),N)[n-1:len(z)]
        e=np.cumsum(np.r_[0,z*z]);scores=abs(v)/np.sqrt(np.maximum((e[n:]-e[:-n])*np.dot(template,template),1));at=int(scores.argmax())
        heard=x[start+at:start+at+n];item=dict(cue=cue,command=command['command'],deviceComplete=command['deviceComplete'],normalizedCorrelation=float(scores[at]),matchedOnsetSec=(start+at)/16000,recordedPeak=float(max(abs(heard))),expectedFrames=n,expectedPcmSha256=hashlib.sha256(pcm.read_bytes()).hexdigest())
        if 8<=cue<=10:
            # Acoustic diagnostics only: room/microphone/AGC are not a calibrated amplifier measurement.
            active=heard[1600:-1600];spectrum=abs(np.fft.rfft((active-active.mean())*np.hanning(len(active))))**2
            freq=np.fft.rfftfreq(len(active),1/16000);target=1000+(cue-8)*500
            band=(freq>=target-30)&(freq<=target+30)
            # Every noise recording has a maximum inside a selected band.
            # A candidate peak is not detection, nor evidence of clock error.
            item.update(expectedToneHz=target,expectedBandPeakCandidateHz=float(freq[band][spectrum[band].argmax()]),recordedFundamentalHz=None,referenceToneIdentified=None,toneIdentificationStatus='UNCONFIRMED_REQUIRES_TIME_FREQUENCY_REVIEW',expectedBandEnergyFraction=float(spectrum[band].sum()/max(spectrum.sum(),1)))
            harmonic=[]
            for harmonic_n in [1,2,3]:
                inside=abs(freq-target*harmonic_n)<=15;harmonic.append(float(spectrum[inside].sum()))
            item['acousticHarmonicEnergy']=harmonic;item['notCalibratedThd']=True
        items.append(item)
    result=dict(result='ACTUAL_CAPTURE_ANALYZED_NOT_SOUND_QUALITY_PASS',analysisVersion=2,items=items,
        microphoneSha256=hashlib.sha256((folder/'pc-microphone.wav').read_bytes()).hexdigest(),
        subjectiveQualityQualified=False,hardwareRootCauseConfirmed=False,scope='Actual board speaker to local PC microphone; waveform/frequency diagnostics only. No SPL/THD calibration or claim that matching pitch means pleasant sound.')
    save(folder/'analysis.json',result);return result

class Window:
    def __init__(self,args):
        self.args=args;self.root=tk.Tk();self.root.title('Companion 扬声器声音对照');self.root.geometry('790x620')
        self.events=queue.Queue();self.cancel=threading.Event();self.busy=False;self.closing=False;self.needs_reseat=False;self.last=None;self.started=time.monotonic();self.touched=self.started
        args.output.mkdir(parents=True,exist_ok=False);self.window_events=[]
        frame=ttk.Frame(self.root,padding=18);frame.pack(fill='both',expand=True)
        ttk.Label(frame,text='选声音 → 主板播放 → 电脑麦克风自动录音',font=('Microsoft YaHei UI',14,'bold')).pack(anchor='w')
        ttk.Label(frame,text='若宠物已睡着，先短按一次主板实体键唤醒。\n默认对照：第一声1.5k、第二声2k，最后三下原确认音。约10秒内请保持安静。\n标准音本来就是单一嘟声，主要听有无、破音和断续；最终宠物音色另改。',justify='left').pack(anchor='w',pady=(10,12))
        self.selected=tk.StringVar(value=next(iter(PRESETS)));self.combo=ttk.Combobox(frame,textvariable=self.selected,values=list(PRESETS),state='readonly',width=35);self.combo.pack(anchor='w')
        buttons=ttk.Frame(frame);buttons.pack(fill='x',pady=14)
        self.play=ttk.Button(buttons,text='主板播放并录音',command=self.capture);self.play.pack(side='left',padx=(0,12))
        self.reference=ttk.Button(buttons,text='电脑听同一原音',command=self.listen);self.reference.pack(side='left')
        ttk.Label(frame,text='电脑原音只用于对比音色；试听响度已调整，不能据此判断主板功率。').pack(anchor='w')
        self.status=tk.StringVar(value='就绪。每次操作完成后都会关闭串口和麦克风，保存同次记录。')
        ttk.Label(frame,textvariable=self.status,wraplength=710,justify='left',font=('Microsoft YaHei UI',10)).pack(fill='x',pady=(2,12))
        ttk.Separator(frame).pack(fill='x',pady=8)
        ttk.Label(frame,text='听感记录（播放后填写；这些选项不代表机器已经判定硬件原因）').pack(anchor='w')
        self.choice=tk.StringVar(value='未检查')
        for label in ['原音本身也难听','主板比原音更沙哑／破音','声音断断续续','没有听到主板声音','这次听起来清楚','未检查']:
            ttk.Radiobutton(frame,text=label,value=label,variable=self.choice).pack(anchor='w')
        self.notes=ttk.Entry(frame,width=88);self.notes.pack(fill='x',pady=8)
        footer=ttk.Frame(frame);footer.pack(fill='x',pady=(6,0))
        self.record=ttk.Button(footer,text='保存这次听感',command=self.feedback);self.record.pack(side='left')
        self.reseat=ttk.Button(footer,text='我已接稳调试线，再查一次',command=self.reseat_confirm);self.reseat.pack(side='left',padx=10);self.reseat.state(['disabled'])
        ttk.Button(footer,text='结束调试并关闭',command=self.close).pack(side='right')
        self.root.protocol('WM_DELETE_WINDOW',self.close);self.root.after(100,self.poll)
        self.event('opened',output=str(args.output),hostScriptSha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest());print(json.dumps(dict(windowReady=True,output=str(args.output)),ensure_ascii=False),flush=True)
    def event(self,event,**data):
        self.touched=time.monotonic();self.window_events.append(dict(atLocal=NOW(),event=event,**data));save(self.args.output/'window-events.json',self.window_events)
    def controls(self,busy):
        self.busy=busy
        for widget in [self.play,self.reference,self.combo]:widget.configure(state='disabled' if busy or self.closing else ('readonly' if widget==self.combo else 'normal'))
        if self.needs_reseat:self.play.state(['disabled'])
    def reseat_confirm(self):
        self.event('owner_explicit_reseated_retry');self.needs_reseat=False;self.reseat.state(['disabled']);self.play.state(['!disabled']);self.status.set('已记录接稳确认；下次点击播放只检查一次串口。')
    def listen(self):
        if self.busy:return
        cue,_=PRESETS[self.selected.get()];self.event('reference_play',cue=cue);self.controls(True);self.status.set('电脑正在播放同一原音；这段不计作主板录音。')
        def worker():
            import winsound
            try:
                for selected in ([9,10,0,0,0] if cue==-1 else [cue]):
                    if self.cancel.is_set():break
                    winsound.PlaySound(str(self.args.fixtures/f'cue{selected}-listen.wav'),winsound.SND_FILENAME)
                    if cue==-1:time.sleep(.5)
            finally:self.events.put(('reference_done',None))
        threading.Thread(target=worker,daemon=False).start()
    def feedback(self):
        if self.busy:return
        target=self.last or self.args.output
        save(target/'owner-feedback.json',dict(atLocal=NOW(),selected=self.choice.get(),notes=self.notes.get(),capture=str(self.last) if self.last else None))
        self.event('owner_feedback',selected=self.choice.get(),capture=str(self.last) if self.last else None);self.status.set('这次听感已保存，关联本次录音和串口；可换声音再试，或结束调试。')
    def capture(self):
        if self.busy or self.needs_reseat:return
        cue,command=PRESETS[self.selected.get()];self.event('owner_play_request',cue=cue,command=command);self.controls(True);self.status.set('正在检查主板是否空闲；正常后自动播放并录音。')
        threading.Thread(target=self.capture_worker,args=(cue,command),daemon=False).start()
    def capture_worker(self,cue,command,origin='owner'):
        R=self.args.workspace;B=R/'docs/board_operations.md';O=self.args.output/('capture-'+datetime.now().strftime('%H%M%S-%f'));O.mkdir()
        state=dict(result='STARTED',startedAtLocal=NOW(),cue=cue,command=command,triggeredBy=origin,commands=[],uartQueries=0,swd=False,reset=False,flashed=False,ble=False,boardRecording=False,settingsChanged=False,physicalQualityQualified=False)
        actor='Owner点击一次播放' if origin=='owner' else 'agent执行显式有限声音对照'
        row=f'- **占用中**：Companion 扬声器对照窗口（{state["startedAtLocal"]}，{O.name}）；{actor}，固定V3/UID一次正常应用门，显式有限参照/短音；PC麦本机记录，无BLE/刷包/复位/板载开录/设置变更，句柄关闭后释放。'
        held=False;uart=mic=None;raw=bytearray();connection_failed=False
        def owners():
            s=B.read_text(encoding='utf-8-sig').split('## 当前占用',1)[1].split('## 交接方式',1)[0]
            return [line for line in s.splitlines() if '**占用中**' in line]
        def replace(old,new):
            before=B.read_bytes();text=before.decode('utf-8-sig');assert text.count(old)==1 and B.read_bytes()==before;atomic(B,text.replace(old,new,1).encode())
        def save_state():save(O/'result.json',state)
        try:
            assert not owners(),'实板正在被另一个聊天使用；本次没有连接'
            replace('## 当前占用','## 当前占用\n\n'+row);held=True
            ports=[p.device for p in list_ports.comports() if p.serial_number==SN]
            if len(ports)!=1:connection_failed=True;raise RuntimeError('找不到指定V3串口；接稳调试线后再检查')
            uart=serial.Serial(port=None,baudrate=115200,timeout=.05,write_timeout=1,rtscts=False,dsrdtr=False,xonxoff=False);uart.dtr=uart.rts=False;uart.port=ports[0]
            try:uart.open()
            except serial.SerialException:connection_failed=True;raise
            def drain():
                if self.cancel.is_set():raise RuntimeError('Owner关闭窗口；取消后续播放')
                assert owners()==[row],'共享占用发生变化，停止本次'
                raw.extend(uart.read(min(max(uart.in_waiting,1),4096)));(O/'uart.log').write_bytes(raw)
            state['uartQueries']=1;uart.write(b'?');uart.flush();deadline=time.monotonic()+12;normal=None
            while time.monotonic()<deadline:
                drain();frames,_=parse_frames(bytes(raw));normal=next((f for f in reversed(frames) if f['reason']=='query'),None)
                if normal:break
            if not normal:connection_failed=True;raise RuntimeError('没有完整正常应用回复；已停止，不自动重试')
            state['initialSnapshot']=normal;s=normal['sections'];receipt=json.loads(self.args.receipt.read_bytes())
            assert s['ID']['uid']==UID and int(s['ID']['fw'],16)==int(receipt['targetFirmware'],16) and s['ID']['ui']==80,'当前版本或主板身份已变化；本次不播放'
            assert s['AUDIO']['mic_run']==0 and s['BLE']['linked']==0 and s['STORAGE']['rec_state'] in (1,6) and s['STORAGE']['rec_fault']==0,'设备正在录音或连接，先结束本次'
            state.update(sourceCommit=receipt['sourceCommit'],appSha256=receipt['appSha256']);save_state()
            # DIAG1 END is followed by the same query's PANEL/BLE/XFER tail.
            # Do not overrun the MCU RX FIFO while foreground UART TX is busy.
            drain_deadline=time.monotonic()+1.5;last_rx=time.monotonic()
            while time.monotonic()<drain_deadline and time.monotonic()-last_rx<.25:
                previous=len(raw);drain()
                if len(raw)!=previous:last_rx=time.monotonic()
            # Invalidate, then terminate a possibly truncated prior line.
            # A bare LF could execute a valid unfinished REC/PAIR command.
            uart.write(b'\x00\n');uart.flush();time.sleep(.01)
            state['queryTailDrainedBeforeCommand']=True
            # One read-only status snapshot; no status polling or safety bypass.
            offset=len(raw)
            for byte in b'EPD STATUS\n':uart.write(bytes([byte]));uart.flush();time.sleep(.003)
            deadline=time.monotonic()+2.5;lines=[]
            while time.monotonic()<deadline:
                drain();lines=[line.strip() for line in raw[offset:].decode('ascii',errors='replace').splitlines(keepends=True) if line.startswith('EPDDBG STATUS ') and line.endswith('\n')]
                if lines:break
            assert lines,'没有取得完整状态；本次不播放'
            admission=dict(re.findall(r'(\w+)=([^\s]+)',lines[-1]));state['admission']=admission
            assert admission['surface']=='0','宠物尚在待机或其它页面；请短按实体键回到宠物后再点播放'
            assert admission.get('speaker')=='0' and admission.get('pending')=='0','扬声器正在忙，本次不播放'
            assert int(admission['blocks'],16)&sum(1<<b for b in (0,1,8,10,11,12,13,14))==0,'当前有受保护操作，本次不播放'
            sequence=[(9,'SOUND REF 2',1),(10,'SOUND REF 3',3),(0,'SOUND',5),(0,'SOUND',6.5),(0,'SOUND',8)] if cue==-1 else [(cue,command,1+index*1.5) for index in range(1 if cue>=8 else 3)]
            seconds=10 if cue==-1 else (4 if cue>=8 else 7);mic=Microphone(O/'pc-microphone.wav',seconds);state['microphoneStartMonotonic']=mic.start;save_state()
            self.events.put(('status','正在录音。主板即将发声，请保持安静；声音会自动结束。'))
            for selected,selected_command,offset_sec in sequence:
                while time.monotonic()<mic.start+offset_sec:drain()
                self.events.put(('status',f'正在录音：本段{selected_command}。请留意是否听见；最后在备注写哪几段有声。'))
                offset=len(raw);item=dict(cue=selected,command=selected_command,monotonic=time.monotonic(),atLocal=NOW());state['commands'].append(item);save_state()
                for byte in (selected_command+'\n').encode():uart.write(bytes([byte]));uart.flush();time.sleep(.003)
                deadline=time.monotonic()+3;reply=[]
                while time.monotonic()<deadline:
                    drain();reply=[line.strip() for line in raw[offset:].decode('ascii',errors='replace').splitlines(keepends=True) if line.startswith(('SOUND1 ','SOUND2 ')) and line.endswith('\n')]
                    if 'SOUND1 FAILED' in reply or any(line.startswith('SOUND2 ') for line in reply):break
                item.update(replyMonotonic=time.monotonic(),reply=reply,deviceComplete='SOUND1 COMPLETE' in reply);save_state()
                assert item['deviceComplete'] and any('sai_error=00000000' in line for line in reply if line.startswith('SOUND2 ')),'播放未完成或被保护门拒绝；保留本次记录，不重复发声'
            while time.monotonic()-mic.start<seconds:drain()
            state['result']='CAPTURE_COMPLETE_ANALYSIS_PENDING'
        except BaseException as error:
            state.update(result='CAPTURE_NOT_COMPLETED',error=str(error),connectionFailed=connection_failed)
        finally:
            if mic is not None:mic.close();state.update(pcMicrophoneClosed=mic.closed,pcMicrophoneBytes=mic.header.recorded)
            if uart is not None:uart.close()
            state.update(ownedHandlesClosed=True,finishedAtLocal=NOW());save_state()
            if held:replace(row,row.replace('**占用中**','**已释放**',1)+f'；{state["finishedAtLocal"]} {state["result"]}；实际UART/PC麦克风关闭，依据{(O/"result.json").relative_to(R).as_posix()}。')
        if state['result']=='CAPTURE_COMPLETE_ANALYSIS_PENDING':
            try:analysis=analyze(O,self.args.fixtures);state['analysis']='analysis.json';save_state()
            except BaseException as error:state['analysisError']=repr(error);save_state()
        self.events.put(('capture_done',(O,state)))
    def close(self):
        if self.closing:return
        self.event('close_requested');self.closing=True;self.cancel.set();self.controls(self.busy)
        import winsound
        winsound.PlaySound(None,0)
        self.status.set('正在关闭本次实际句柄…')
        if not self.busy:self.root.destroy()
    def poll(self):
        try:
            while True:
                kind,data=self.events.get_nowait()
                if kind=='status':self.status.set(data)
                elif kind=='reference_done':self.controls(False);self.status.set('原音播放结束。可点主板播放并录音，比较实物。')
                elif kind=='capture_done':
                    self.last,state=data;self.controls(False);self.event('capture_finished',output=str(self.last),result=state['result'])
                    if state.get('connectionFailed'):self.needs_reseat=True;self.play.state(['disabled']);self.reseat.state(['!disabled'])
                    self.status.set('录音与对照已保存。请记录这次听感；声音相似不代表音质合格。' if state['result']=='CAPTURE_COMPLETE_ANALYSIS_PENDING' else state.get('error','本次未完成'))
        except queue.Empty:pass
        if self.closing and not self.busy:self.root.destroy();return
        if not self.busy and time.monotonic()-self.touched>300:self.close();return
        self.root.after(100,self.poll)
    def run(self):
        self.root.mainloop();save(self.args.output/'window-result.json',dict(result='WINDOW_CLOSED',finishedAtLocal=NOW(),captures=[str(p) for p in self.args.output.glob('capture-*')],noHardwareHandlesHeld=self.busy is False));print(json.dumps(dict(windowClosed=True,output=str(self.args.output)),ensure_ascii=False),flush=True)

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--workspace',type=Path,required=True);parser.add_argument('--receipt',type=Path,required=True);parser.add_argument('--fixtures',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--machine-once',action='store_true')
    parser.add_argument('--machine-cue',type=int,choices=[8,9,10,11],default=8,
        help='One explicit finite local reference; no automatic retry')
    args=parser.parse_args()
    if args.machine_once:
        from types import SimpleNamespace
        args.output.mkdir(parents=True,exist_ok=False)
        worker=SimpleNamespace(args=args,events=queue.Queue(),cancel=threading.Event())
        command={8:'SOUND REF 1',9:'SOUND REF 2',10:'SOUND REF 3',11:'SOUND SOFT'}[args.machine_cue]
        Window.capture_worker(worker,args.machine_cue,command,origin='agent')
        while not worker.events.empty():
            kind,data=worker.events.get()
            if kind=='capture_done':print(json.dumps(dict(output=str(data[0]),result=data[1]['result'],error=data[1].get('error')),ensure_ascii=False))
    else:Window(args).run()
