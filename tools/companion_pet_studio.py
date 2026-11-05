#!/usr/bin/env python3
"""Owner art review of a frozen C runtime, with simulated inputs only.

This tool neither loads a serial library nor connects to a board. Framebuffers
come from the already built production C renderer. The layout sheets alone use
explicit draft text; they are not a chatbot or firmware text implementation.
"""
from __future__ import annotations

import argparse
import base64
import ctypes
from datetime import datetime
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import io
import json
from pathlib import Path
import secrets
import sys
import threading
import time
from urllib.parse import urlsplit

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / '.cache/screen-art-polish-20261011'
SOURCE = BASE / 'source190'
DLL = BASE / 'preview-build190/wba-runtime-preview.dll'
IMAGE = SOURCE / '.cache/pet-design-20261007/ui67/ui-partition.bin'
PUBLIC = BASE / 'studio190'
SCENES = BASE / 'studio-p15'
DESIGN = 'P03'
sys.path.insert(0, str(SOURCE / 'tools'))
from wba_runtime_preview import Runtime  # frozen host wrapper; no test execution

FAMILIES = ('calm', 'curious', 'delighted', 'warm', 'playful', 'sleepy',
            'bashful', 'thoughtful', 'focused', 'alert')
LABELS = ('安静', '好奇', '开心', '亲近', '俏皮', '困倦', '害羞', '思考', '专注', '惊讶')
TAPS = {'head': (100, 74), 'cheek': (52, 139),
        'nose': (100, 129), 'chin': (100, 152)}


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def encode_png(frame):
    buffer = io.BytesIO()
    frame.save(buffer, format='PNG')
    return base64.b64encode(buffer.getvalue()).decode('ascii')


def inputs():
    if DESIGN == 'P16':
        receipt=json.loads((BASE/'preview-build-p16-final/build-result.json').read_bytes())
        if sha(DLL)!=receipt['dllSha256'] or sha(IMAGE)!=receipt['resourceImageSha256']:
            raise RuntimeError('Integrated preview differs from its frozen build')
        for path,digest in receipt['sources'].items():
            if sha(path)!=digest: raise RuntimeError('Frozen input changed: '+path)
        return dict(studio='P16',firmwareArt='原开发板整套表情 / 同源运行逻辑',
            artBaseFirmware='FW209/UI68 + P16 screen source',baseFirmware='1.1.209',
            dllSha256=receipt['dllSha256'],resourceImageSha256=receipt['resourceImageSha256'],
            sourceTag='screen-pet-integrated-20261011-p16',playbackRate=1,
            inputs='SIMULATED',physicalGhosting='NOT_MODELED',pairedRamSync='NOT_MODELED',
            artInstalled=False,armFirmwareBuilt=False,productionSourcesChanged=True)
    receipt_path = BASE / (f'preview-build-{DESIGN.lower()}/build-result.json' if DESIGN in ('P04', 'P05', 'P06', 'P07', 'P08', 'P09', 'P15') else 'preview-build190/build-result.json')
    receipt = json.loads(receipt_path.read_text())
    if sha(DLL) != receipt['dllSha256']:
        raise RuntimeError('Frozen native preview DLL changed; do not silently use another renderer')
    if DESIGN in ('P04', 'P05', 'P06', 'P07', 'P08', 'P09', 'P15'):
        for path, digest in receipt['sources'].items():
            if sha(path) != digest:
                raise RuntimeError('Native design differs from its compiled input')
    if sha(IMAGE) != '31222ecd9649a6a6c6b31e2f6a05300f32e8f163be30999ea58147dc37933b22':
        raise RuntimeError('Expected the preserved UI67 bank')
    return dict(studio=DESIGN, firmwareArt='原开发板 UI67 整套表情风格 / P15' if DESIGN == 'P15' else f'{DESIGN} 神态轻重与圆顺轮廓稿 / UI67' if DESIGN == 'P09' else f'{DESIGN} 情绪眼神精修稿 / UI67' if DESIGN == 'P08' else f'{DESIGN} 眉眼衔接与纸面状态栏稿 / UI67' if DESIGN == 'P07' else f'{DESIGN} 嘴形精修稿 / UI67' if DESIGN == 'P06' else f'{DESIGN} 原比例与编舞稿 / UI67' if DESIGN in ('P04', 'P05') else 'FW1.1.190/UI67', artBaseFirmware='FW1.1.190/UI67',
                dllSha256=sha(DLL), resourceImageSha256=sha(IMAGE),
                playbackRate=1, inputs='SIMULATED', physicalGhosting='NOT_MODELED',
                pairedRamSync='NOT_MODELED', artInstalled=False,
                sourceTag=f'screen-pet-design-20261011-{DESIGN.lower()}' if DESIGN in ('P04', 'P05', 'P06', 'P07', 'P08', 'P09', 'P15') else 'screen-art-polish-20261011-source-fw190',
                baseFirmware='1.1.190', armFirmwareBuilt=DESIGN not in ('P04', 'P05', 'P06', 'P07', 'P08', 'P09', 'P15'),
                panelTimingReference=dict(manualTypicalAt25C=260, vendorProductPageMs=300,
                    historicalTransactionModelMs=480, currentPhysicalMaximum='NOT_QUALIFIED'),
                preservedStateKeys=12996, stateKeysAreNotIndependentExpressions=True)


def resting_portrait(runtime, family):
    """Show the authored daily family, rather than ten forced reply peaks."""
    runtime.lib.cp_family(family)
    until = runtime.now + 3500
    while runtime.now < until:
        runtime.advance(runtime.now + 20)
        state = runtime.state()
        if state['family'] == FAMILIES[family] and state['visibleKind'] == 1 and state['motionAction'] == 0:
            return Image.frombytes('1', (200, 200), runtime.raw()), state
    raise RuntimeError('Authored resting portrait was not committed')


def portrait(runtime, family, zone):
    runtime.lib.cp_pose(family, zone)
    until = runtime.now + 3500
    while runtime.now < until:
        runtime.advance(runtime.now + 20)
        state = runtime.state()
        if state['replyExpression'] and state['replyPosePhase'] == 1 and state['family'] == FAMILIES[family]:
            return Image.frombytes('1', (200, 200), runtime.raw()), state
    raise RuntimeError('Art inspection pose was not committed')


def export():
    """Export inspectable art and layout drafts; no production sources change."""
    meta = inputs()
    PUBLIC.mkdir(parents=True, exist_ok=True)
    runtime = Runtime(IMAGE, DLL, seed=17)
    font = ImageFont.truetype('C:/Windows/Fonts/msyh.ttc', 14)
    small = ImageFont.truetype('C:/Windows/Fonts/msyh.ttc', 12)
    sheet = Image.new('RGB', (1092, 570), '#f4f2eb')
    draw = ImageDraw.Draw(sheet)
    draw.text((18, 12), 'Companion · 原来的十类日常母版', font=font, fill='#293a33')
    draw.text((18, 37), f'{DESIGN} 原生黑白像素 · 日常、方向与互动神态分开看 · 饰件沿用 UI67', font=small, fill='#65736b')
    gallery = []
    for family, label in enumerate(LABELS):
        runtime.reset()
        runtime.lib.cp_clock(10, 28)
        runtime.lib.cp_panel(480, 0)
        runtime.advance(800)
        zone = {3: 2, 4: 3, 6: 4}.get(family, 0)
        frame, state = resting_portrait(runtime, family) if DESIGN in ('P05', 'P06', 'P07', 'P08', 'P09') else portrait(runtime, family, zone)
        frame.save(PUBLIC / f'pose-{family}.png')
        x, y = 18 + (family % 5) * 216, 72 + (family // 5) * 237
        sheet.paste(frame.convert('RGB'), (x, y))
        draw.text((x, y + 206), label, font=small, fill='#293a33')
        gallery.append(dict(family=family, label=label, file=f'pose-{family}.png', state=state,
                            mode='rest' if DESIGN in ('P05', 'P06', 'P07', 'P08', 'P09') else 'pose'))
    sheet.save(PUBLIC / 'character-library.png')

    # Layout authoring uses a C-rendered calm face at its exact native size.
    # Only the reserved caption strip is replaced with labelled example text.
    base = Image.open(PUBLIC / 'pose-0.png').convert('1')
    layouts = []
    for name, lines in (('quiet', ()), ('short', ('我在，慢慢说。',)),
                        ('two-lines', ('听起来有点累了。', '要不要一起歇一会？'))):
        frame = base.copy()
        d = ImageDraw.Draw(frame)
        d.rectangle((12, 174, 187, 199), fill=1)
        for i, line in enumerate(lines):
            width = d.textlength(line, font=small)
            if width > 176:
                raise RuntimeError('Layout draft overflowed the production reply slot')
            box = d.textbbox((0, 0), line, font=small, anchor='lt')
            if box[3] - box[1] > 12:
                raise RuntimeError('Layout draft exceeded the reserved line height')
            d.text(((200 - width) // 2, 174 + i * 14), line, font=small, fill=0, anchor='lt')
        frame.save(PUBLIC / f'layout-{name}.png')
        layouts.append(dict(name=name, lines=lines, file=f'layout-{name}.png',
                            scope='DRAFT_TEXT_LAYOUT_ONLY', slot=[12, 174, 176, 26]))
    studio = Studio(seed=17)
    studio.advance(800)
    if not studio.command(dict(kind='repeat', name='head')):
        raise RuntimeError('Native interaction preview was not admitted')
    animation = []
    commits = []
    peaks = {}
    previous_version = -1
    for _ in range(240):
        studio.advance(100)
        state = studio.state()
        frame = Image.frombytes('1', (200, 200), studio.runtime.raw()).convert('RGB')
        page = Image.new('RGB', (260, 276), '#f4f2eb')
        d = ImageDraw.Draw(page)
        d.text((12, 10), '连续摸头 · 原速回应', font=font, fill='#293a33')
        page.paste(frame, (30, 40))
        d.text((12, 250), '原生 C / 480ms 模拟刷新 / 未上屏', font=small, fill='#65736b')
        animation.append(page)
        if state['version'] != previous_version:
            commits.append({key: value for key, value in state.items() if key not in ('png', 'studio')})
            previous_version = state['version']
        ordinal = state['repeatSent']
        if state['petInteraction'] == 1 and state['replyExpression'] and state['replyPosePhase'] == 1:
            if ordinal not in peaks:
                peaks[ordinal] = (frame, state)
        if state['repeatSent'] == 3 and not state['repeatRemaining'] and not state['replyPending'] and studio.runtime.now > 10000:
            break
    animation[0].save(PUBLIC / 'three-head-pats.gif', save_all=True, append_images=animation[1:],
                      duration=100, loop=0, optimize=False, disposal=2)
    repeated = Image.new('RGB', (666, 290), '#f4f2eb')
    d = ImageDraw.Draw(repeated)
    d.text((18, 10), '同一个动作 · 三次实际算法回应的表达拍', font=font, fill='#293a33')
    for index, ordinal in enumerate(sorted(peaks)):
        x = 18 + index * 216
        repeated.paste(peaks[ordinal][0], (x, 48))
        d.text((x, 254), f'第 {ordinal} 次摸头', font=small, fill='#293a33')
    repeated.save(PUBLIC / 'three-head-pats.png')
    receipt = dict(result='NATIVE_ART_AND_EXPLICIT_TEXT_LAYOUT_EXPORTED',
                   createdAtLocal=datetime.now().isoformat(), metadata=meta,
                   gallery=gallery, layouts=layouts, testsAdded=False, testsRun=False,
                   nativeInteraction=dict(input='SAME_SIMULATED_HEAD_TAP_THREE_TIMES',
                       count=studio.sent, finished=not studio.remaining and not state['replyPending'],
                       peakCount=len(peaks), playbackRate=1, gifDurationMs=len(animation)*100,
                       peakFrames=[dict(ordinal=i, frameSha256=peaks[i][1]['frameSha256'],
                                       seed=peaks[i][1]['petSeed'], repetitions=peaks[i][1]['petRepetitions']) for i in sorted(peaks)],
                       commits=commits, failures=state['failures'], missingStates=state['missingStates']),
                   boardAccess=False, physicalAcceptance='NOT_RUN')
    if DESIGN in ('P05', 'P06', 'P07', 'P08', 'P09'):
        interaction_sheet = Image.new('RGB', (666, 540), '#f4f2eb')
        draw = ImageDraw.Draw(interaction_sheet)
        draw.text((18, 10), '互动时展开神态 · 保留原来的情绪和小饰件', font=font, fill='#293a33')
        interactions = []
        for i, (name, label) in enumerate((('head', '摸头 · 舒服'), ('cheek', '戳脸 · 害羞与偷看'),
                ('nose', '点鼻子 · 惊喜'), ('chin', '挠下巴 · 笑弯眼'),
                ('pickup', '拿起 · 注意你'), ('shake', '轻晃 · 俏皮眨眼'))):
            sample = Studio(seed=17 + i)
            sample.advance(800)
            sample.command(dict(kind='interact', name=name))
            for _ in range(180):
                sample.advance(20)
                s = sample.state()
                if s['replyExpression'] and s['replyPosePhase'] == 1:
                    frame = Image.frombytes('1', (200, 200), sample.runtime.raw()).convert('RGB')
                    file = f'interaction-{name}.png'
                    frame.save(PUBLIC / file)
                    x, y = 18 + (i % 3) * 216, 48 + (i // 3) * 244
                    interaction_sheet.paste(frame, (x, y))
                    draw.text((x, y + 208), label, font=small, fill='#293a33')
                    interactions.append(dict(name=name, label=label, file=file, state=s))
                    break
            else:
                raise RuntimeError('Native interaction peak was not committed')
        interaction_sheet.save(PUBLIC / 'interaction-library.png')
        receipt['interactions'] = interactions
    (PUBLIC / 'art-layout.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(dict(result=receipt['result'], public=str(PUBLIC)), ensure_ascii=False), flush=True)


class Studio:
    def __init__(self, seed):
        self.metadata = inputs()
        self.runtime = Runtime(IMAGE, DLL, seed=seed)
        self.lock = self.runtime.lock
        self.paused = False
        self.release_due = 0
        self.sequence_name = ''
        self.remaining = 0
        self.sent = 0
        self.wait_due = 0
        self.reply_seen = False
        self.last_input = ''
        self.layout_library = None
        self.layout_version = -1
        if DESIGN in ('P09', 'P15') and (SCENES / 'scene-design.json').is_file():
            receipt = json.loads((SCENES / 'scene-design.json').read_bytes())
            layout_dll = BASE / 'preview-build-p13/pet-scene-design.dll'
            if sha(layout_dll) != receipt['sceneDllSha256']:
                raise RuntimeError('P13 layout differs from its native build')
            for name, digest in receipt['sourceSha256'].items():
                if sha(ROOT / name) != digest:
                    raise RuntimeError('P13 compiled layout input changed: ' + name)
            self.layout_library = ctypes.CDLL(str(layout_dll))
            self.layout_library.comp_scene_design_layout.argtypes = [ctypes.POINTER(ctypes.c_uint8)]
            self.layout_library.comp_scene_design_layout.restype = ctypes.c_int
            self.metadata.update(compositionArt='P13', sceneArt=receipt['design'],
                                 layoutDllSha256=receipt['sceneDllSha256'])
        self.configure()

    def configure(self):
        self.runtime.lib.cp_panel(480, 0)
        self.runtime.lib.cp_language(1)
        self.runtime.lib.cp_clock(datetime.now().hour, datetime.now().minute)
        if DESIGN=='P16':
            self.runtime.lib.cp_power_state.argtypes=(ctypes.c_uint,)*3
            self.runtime.lib.cp_power_state.restype=None
            self.runtime.lib.cp_power_state(0,255,0)

    def cancel_sequence(self):
        self.remaining = 0
        self.sequence_name = ''
        self.release_due = 0
        self.runtime.lib.cp_cancel()

    def trigger(self, name):
        if name in TAPS:
            x, y = TAPS[name]
            self.runtime.lib.cp_touch(1, x, y)
            self.release_due = self.runtime.now + 120
        elif name in ('pickup', 'shake'):
            self.runtime.lib.cp_action(3 if name == 'pickup' else 8)
        else:
            raise ValueError('Unknown interaction')
        self.last_input = name

    def command(self, data):
        with self.lock:
            kind = data.get('kind')
            if kind in ('interact', 'repeat'):
                name = data.get('name')
                if name not in (*TAPS, 'pickup', 'shake'):
                    raise ValueError('Unknown interaction')
                if self.remaining or self.release_due:
                    return False
                if self.paused:
                    self.paused = False
                state = self.runtime.state()
                if state['surface'] != 0 or (state['replyPending'] and (DESIGN!='P16' or kind=='repeat')) or state['preparing'] or state['capturing']:
                    return False
                self.sent = 1
                self.trigger(name)
                if kind == 'repeat':
                    self.remaining = 2
                    self.sequence_name = name
                    self.wait_due = self.runtime.now + 1400
                    self.reply_seen = False
                return True
            if kind == 'pause':
                self.cancel_sequence()
                self.paused = bool(data.get('paused'))
                return True
            if kind == 'newSession':
                self.cancel_sequence()
                self.runtime.seed = secrets.randbelow(0xfffffffe) + 1
                self.runtime.reset()
                self.layout_version = -1
                self.paused = False
                self.sent = 0
                self.last_input = ''
                self.configure()
                return True
            if kind == 'pose':
                family, zone = int(data['family']), int(data.get('zone', 0))
                if not 0 <= family < 10 or not 0 <= zone <= 4:
                    raise ValueError('Invalid inspection pose')
                self.cancel_sequence()
                self.paused = False
                self.runtime.lib.cp_pose(family, zone)
                return True
            if kind == 'language':
                language = int(data['language'])
                if not 0 <= language < 3:
                    raise ValueError('Invalid language')
                self.runtime.lib.cp_language(language)
                return True
            if kind == 'deviceState' and DESIGN == 'P16':
                states={'battery':(3860,78,0),'charging':(3860,78,1<<22),
                        'update':(3860,78,1<<23),'low':(3100,19,0),'unknown':(0,255,0)}
                if data.get('name') not in states: raise ValueError('Unknown supplied state')
                self.runtime.lib.cp_power_state(*states[data['name']])
                self.paused=False
                return True
            if kind == 'action':
                self.cancel_sequence()
                self.paused=False
            if kind == 'family':
                self.cancel_sequence()
                self.paused = False
            if kind == 'touch':
                # Cancel a scripted interaction once, not every pointer sample:
                # cancelling on pointer-up would destroy the native tap gesture.
                if self.remaining or self.release_due:
                    self.cancel_sequence()
                self.paused = False
                # Convert displayed face coordinates back to the unchanged
                # P09 input geometry. Menu/rest surfaces retain their mapping.
                if self.layout_library and self.runtime.state()['surface'] == 0 and 59 <= int(data['y']) < 162:
                    data = dict(data, y=min(199, int(data['y']) + 6))
            return self.runtime.command(data)

    def advance(self, delta):
        with self.lock:
            if self.paused:
                return
            target = self.runtime.now + delta
            while self.runtime.now < target:
                self.runtime.advance(min(target, self.runtime.now + 4))
                now = self.runtime.now
                if self.release_due and now >= self.release_due:
                    x, y = TAPS[self.last_input]
                    self.runtime.lib.cp_touch(0, x, y)
                    self.release_due = 0
                if self.remaining:
                    state = self.runtime.state()
                    if state['replyPending']:
                        self.reply_seen = True
                    if self.reply_seen and not state['replyPending']:
                        self.reply_seen = False
                        self.wait_due = max(self.wait_due, now + 800)
                    if now >= self.wait_due and not state['replyPending'] and not state['panelPending'] and not self.release_due:
                        self.trigger(self.sequence_name)
                        self.sent += 1
                        self.remaining -= 1
                        self.wait_due = now + 1400

    def state(self):
        with self.lock:
            result = self.runtime.state(True)
            if self.layout_library:
                if self.layout_version != result['version']:
                    pixels = (ctypes.c_uint8 * 5000).from_buffer_copy(self.runtime.raw())
                    if result['surface'] == 0 and not self.layout_library.comp_scene_design_layout(pixels):
                        raise RuntimeError('Native layout rejected a pet frame')
                    raw = bytes(pixels)
                    self.layout_png = encode_png(Image.frombytes('1', (200, 200), raw))
                    self.layout_sha = hashlib.sha256(raw).hexdigest()
                    self.layout_version = result['version']
                result.update(sourceFrameSha256=result['frameSha256'], png=self.layout_png,
                              frameSha256=self.layout_sha,
                              scope=f'{DESIGN}_C_RUNTIME_WITH_P13_C_COMPOSITION_SIMULATED_PERIPHERALS')
            result.update(studio=self.metadata, paused=self.paused, repeatRemaining=self.remaining,
                          repeatSent=self.sent, lastInteraction=self.last_input)
            return result


def serve(port, seed):
    if not (PUBLIC / 'art-layout.json').exists():
        raise RuntimeError('Export the studio art before starting the review page')
    studio = Studio(seed)
    stopped = threading.Event()

    def stepper():
        previous = time.monotonic()
        carry = 0.0
        while not stopped.wait(.004):
            current = time.monotonic()
            carry += (current - previous) * 1000
            previous = current
            delta = int(carry)
            carry -= delta
            studio.advance(delta)
    threading.Thread(target=stepper, name='native-pet-studio', daemon=True).start()

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_):
            pass

        def send(self, body, kind, status=200):
            self.send_response(status)
            self.send_header('Content-Type', kind)
            self.send_header('Cache-Control', 'no-store')
            self.send_header('Content-Length', str(len(body)))
            self.end_headers()
            try:
                self.wfile.write(body)
            except (BrokenPipeError, ConnectionResetError):
                pass

        def reply(self, value, status=200):
            self.send(json.dumps(value, ensure_ascii=False).encode('utf-8'), 'application/json; charset=utf-8', status)

        def do_GET(self):
            route = urlsplit(self.path).path
            if route == '/api/state':
                self.reply(studio.state())
            elif route in ('/', '/studio/'):
                page = 'companion_pet_authored_studio.html' if DESIGN in ('P15','P16') else 'companion_pet_studio.html'
                self.send((ROOT / 'tools' / page).read_bytes(), 'text/html; charset=utf-8')
            elif route == '/api/art':
                self.send((PUBLIC / 'art-layout.json').read_bytes(), 'application/json; charset=utf-8')
            elif route == '/api/scenes' and (SCENES / 'scene-design.json').is_file():
                self.send((SCENES / 'scene-design.json').read_bytes(), 'application/json; charset=utf-8')
            elif route.startswith('/scenes/') and '/' not in route[8:] and route.endswith('.png'):
                asset = SCENES / route[8:]
                if asset.is_file():
                    self.send(asset.read_bytes(), 'image/png')
                else:
                    self.reply({'error': 'Unknown scene artwork'}, 404)
            elif route.startswith('/assets/') and '/' not in route[8:] and route.endswith(('.png', '.gif')):
                asset = PUBLIC / route[8:]
                if asset.is_file():
                    self.send(asset.read_bytes(), 'image/gif' if asset.suffix == '.gif' else 'image/png')
                else:
                    self.reply({'error': 'Unknown artwork'}, 404)
            else:
                self.reply({'error': 'Not found'}, 404)

        def do_POST(self):
            if self.headers.get('Origin') not in (None, f'http://127.0.0.1:{port}', f'http://localhost:{port}'):
                self.reply({'error': 'Origin not allowed'}, 403)
                return
            if self.path != '/api/input':
                self.reply({'error': 'Not found'}, 404)
                return
            try:
                length = int(self.headers.get('Content-Length', '0'))
                if not 0 < length <= 2048:
                    raise ValueError('Invalid input length')
                data = json.loads(self.rfile.read(length))
                if not isinstance(data, dict):
                    raise ValueError('Expected a command object')
                self.reply({'accepted': studio.command(data)})
            except (ValueError, KeyError, TypeError) as error:
                self.reply({'error': str(error)}, 400)

    server = ThreadingHTTPServer(('127.0.0.1', port), Handler)
    print(f'READY http://127.0.0.1:{port}/studio/ native_art={DESIGN} simulated_inputs=1', flush=True)
    try:
        server.serve_forever()
    finally:
        stopped.set()
        server.server_close()


def main():
    global DLL, PUBLIC, DESIGN, IMAGE
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--export', action='store_true')
    parser.add_argument('--port', type=int, default=8891)
    parser.add_argument('--seed', type=int, default=17)
    parser.add_argument('--design', choices=('p03', 'p04', 'p05', 'p06', 'p07', 'p08', 'p09', 'p15', 'p16'), default='p16')
    args = parser.parse_args()
    if args.design == 'p04':
        DESIGN = 'P04'
        DLL = BASE / 'preview-build-p04/wba-runtime-preview.dll'
        PUBLIC = BASE / 'studio-p04'
    elif args.design == 'p05':
        DLL = BASE / 'preview-build-p05/wba-runtime-preview.dll'
        PUBLIC = BASE / 'studio-p05'
        DESIGN = 'P05'
    elif args.design == 'p06':
        DLL = BASE / 'preview-build-p06/wba-runtime-preview.dll'
        PUBLIC = BASE / 'studio-p06'
        DESIGN = 'P06'
    elif args.design == 'p07':
        DLL = BASE / 'preview-build-p07/wba-runtime-preview.dll'
        PUBLIC = BASE / 'studio-p07'
        DESIGN = 'P07'
    elif args.design == 'p08':
        DLL = BASE / 'preview-build-p08/wba-runtime-preview.dll'
        PUBLIC = BASE / 'studio-p08'
        DESIGN = 'P08'
    elif args.design == 'p09':
        DLL = BASE / 'preview-build-p09/wba-runtime-preview.dll'
        PUBLIC = BASE / 'studio-p09'
        DESIGN = 'P09'
    elif args.design == 'p15':
        DLL = BASE / 'preview-build-p15/wba-runtime-preview.dll'
        PUBLIC = BASE / 'studio-p15'
        DESIGN = 'P15'
    elif args.design == 'p16':
        DLL = BASE / 'preview-build-p16-final/wba-runtime-preview.dll'
        IMAGE = BASE / 'source-p16-final/.cache/external-ui68/ui-partition.bin'
        PUBLIC = BASE / 'studio-p16-reviewed'
        DESIGN = 'P16'
    if args.export:
        export()
    else:
        serve(args.port, args.seed)


if __name__ == '__main__':
    main()
