"""Export P15 authored UI67 art through native C, with silent simulated inputs."""
from copy import deepcopy
import ctypes, hashlib, importlib.util, json
from pathlib import Path
from PIL import Image, ImageChops, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / '.cache/screen-art-polish-20261011'
PUBLIC = BASE / 'studio-p15'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()


class Scene(ctypes.Structure):
    _fields_ = [(name, ctypes.c_uint) for name in ('kind', 'battery_percent',
        'battery_valid', 'battery_estimated', 'progress', 'elapsed_seconds', 'menu_selection')]


def main():
    PUBLIC.mkdir(exist_ok=False)
    spec = importlib.util.spec_from_file_location('authored_pet_studio', ROOT / 'tools/companion_pet_studio.py')
    studio = importlib.util.module_from_spec(spec); spec.loader.exec_module(studio)
    studio.DESIGN = 'P15'; studio.PUBLIC = PUBLIC
    studio.DLL = BASE / 'preview-build-p15/wba-runtime-preview.dll'
    metadata = studio.inputs()
    layout = ctypes.CDLL(str(BASE / 'preview-build-p13/pet-scene-design.dll'))
    layout.comp_scene_design_render.argtypes = [ctypes.POINTER(ctypes.c_uint8), ctypes.POINTER(Scene)]
    layout.comp_scene_design_render.restype = ctypes.c_int
    layout.comp_scene_design_layout.argtypes = [ctypes.POINTER(ctypes.c_uint8)]
    layout.comp_scene_design_layout.restype = ctypes.c_int
    font = ImageFont.truetype('C:/Windows/Fonts/msyh.ttc', 12)
    gallery = []
    for family, label in enumerate(studio.LABELS):
        runtime = studio.Runtime(studio.IMAGE, studio.DLL, seed=17)
        runtime.lib.cp_clock(10, 28); runtime.lib.cp_panel(480, 0); runtime.advance(800)
        frame, state = studio.resting_portrait(runtime, family)
        file = f'pose-{family}.png'; frame.save(PUBLIC / file)
        original = BASE / 'studio-p05' / f'original-pose-{family}.png'
        crop = (20, 65, 182, 172)
        changed = ImageChops.difference(frame.convert('L').crop(crop),
            Image.open(original).convert('L').crop(crop))
        gallery.append(dict(family=family, label=label, file=file, state=state,
            mode='ORIGINAL_AUTHORED_REST', outputSha256=sha(PUBLIC / file),
            referenceSource=str(original.relative_to(ROOT)), referenceSha256=sha(original),
            anatomyChangedPixels=sum(v != 0 for v in changed.getdata())))
    sheet = Image.new('RGB', (1092, 584), '#f4f2eb'); draw = ImageDraw.Draw(sheet)
    draw.text((18, 12), 'Companion · 回到开发板上的整套表情', font=font, fill='#293a33')
    draw.text((18, 35), 'P15 · 原眼形、眉毛、嘴形与饰件 · 原生 200×200 · 原编舞及模拟刷新节奏', font=font, fill='#65736b')
    for i, item in enumerate(gallery):
        x, y = 18 + i % 5 * 216, 68 + i // 5 * 249
        sheet.paste(Image.open(PUBLIC / item['file']).convert('RGB'), (x, y))
        draw.text((x, y + 209), item['label'], font=font, fill='#293a33')
    sheet.save(PUBLIC / 'character-library.png')
    comparison = Image.new('RGB', (670, 779), '#f4f2eb'); draw = ImageDraw.Draw(comparison)
    draw.text((18, 10), '风格对照 · 保留整套原画，日常与互动统一来源', font=font, fill='#293a33')
    for row, family in enumerate((0, 2, 7)):
        y = 47 + row * 243
        for col, (name, path) in enumerate((('原开发板母版', BASE / 'studio-p05' / f'original-pose-{family}.png'),
                 ('之前精修稿 P09', BASE / 'studio-p09' / f'pose-{family}.png'),
                 ('P15 · 恢复原画', PUBLIC / f'pose-{family}.png'))):
            x = 18 + col * 216
            draw.text((x, y), name + ' / ' + studio.LABELS[family], font=font, fill='#293a33')
            comparison.paste(Image.open(path).convert('RGB'), (x, y + 24))
    comparison.save(PUBLIC / 'style-comparison.png')
    interactions = []
    for index, (name, label) in enumerate((('head', '摸摸头'), ('cheek', '戳脸颊'),
            ('nose', '点鼻子'), ('chin', '挠下巴'), ('pickup', '拿起来'), ('shake', '轻轻晃'))):
        runtime = studio.Runtime(studio.IMAGE, studio.DLL, seed=17 + index)
        runtime.lib.cp_clock(10, 28); runtime.lib.cp_panel(480, 0); runtime.advance(800)
        if name in studio.TAPS:
            x, y = studio.TAPS[name]; runtime.lib.cp_touch(1, x, y)
            runtime.advance(runtime.now + 120); runtime.lib.cp_touch(0, x, y)
        else: runtime.lib.cp_action(3 if name == 'pickup' else 8)
        until = runtime.now + 3600
        while runtime.now < until:
            runtime.advance(runtime.now + 20); state = runtime.state()
            if state['replyExpression'] and state['replyPosePhase'] == 1: break
        else: raise RuntimeError('Authored reaction did not commit: ' + name)
        file = f'interaction-{name}.png'
        Image.frombytes('1', (200, 200), runtime.raw()).save(PUBLIC / file)
        interactions.append(dict(name=name, label=label, file=file, state=state,
                                 outputSha256=sha(PUBLIC / file), input='SIMULATED'))
    interaction_sheet = Image.new('RGB', (670, 540), '#f4f2eb'); draw = ImageDraw.Draw(interaction_sheet)
    draw.text((18, 10), '原来的画风，也能回应你 · 既有互动算法 / 480ms模拟完成', font=font, fill='#293a33')
    for i, item in enumerate(interactions):
        x, y = 18 + i % 3 * 216, 48 + i // 3 * 242
        interaction_sheet.paste(Image.open(PUBLIC / item['file']).convert('RGB'), (x, y))
        draw.text((x, y + 208), item['label'], font=font, fill='#293a33')
    interaction_sheet.save(PUBLIC / 'interaction-library.png')
    # One affected full response is exported at wall-clock speed. No interpolation
    # or new timing code. This is native art inspection, not a hardware test.
    runtime = studio.Runtime(studio.IMAGE, studio.DLL, seed=17)
    runtime.lib.cp_clock(10, 28); runtime.lib.cp_panel(480, 0); runtime.advance(800)
    runtime.lib.cp_touch(1, 100, 74)
    start = runtime.now; released = False; seen = False; frames = []; commits = []; version = -1
    for _ in range(100):
        runtime.advance(runtime.now + 100)
        if not released and runtime.now - start >= 120:
            runtime.lib.cp_touch(0, 100, 74); released = True
        state = runtime.state(); seen = seen or state['replyPending']
        pixels = (ctypes.c_uint8 * 5000).from_buffer_copy(runtime.raw())
        if not layout.comp_scene_design_layout(pixels): raise RuntimeError('Layout rejected animation frame')
        frames.append(Image.frombytes('1', (200, 200), bytes(pixels)).convert('RGB'))
        if state['version'] != version:
            version = state['version']; commits.append(state)
        if seen and not state['replyPending'] and not state['panelPending'] and runtime.now - start > 1400: break
    finished = seen and not state['replyPending'] and not state['panelPending']
    frames[0].save(PUBLIC / 'authored-head-response.gif', save_all=True,
        append_images=frames[1:], duration=100, loop=0, optimize=False, disposal=2)
    art = dict(result='NATIVE_ORIGINAL_STYLE_ART_EXPORTED', metadata=metadata, gallery=gallery,
        interactions=interactions, styleReference='ORIGINAL_DEVELOPMENT_BOARD_UI67_FULL_SET',
        nativeInteraction=dict(input='SIMULATED_HEAD_TAP', finished=finished, commits=commits,
            failures=state['failures'], missingStates=state['missingStates'], playbackRate=1,
            durationMs=len(frames) * 100, panelModelMs=480),
        testsRun=False, boardAccess=False, physicalAcceptance='NOT_RUN')
    (PUBLIC / 'art-layout.json').write_text(json.dumps(art, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    prior = json.loads((BASE / 'studio-p14/scene-design.json').read_bytes())
    receipt = deepcopy(prior); samples = []
    for sample in receipt['samples']:
        name, family = sample['name'], sample['family']
        source = PUBLIC / f'pose-{family}.png'
        pixels = (ctypes.c_uint8 * 5000).from_buffer_copy(Image.open(source).convert('1').tobytes())
        context = Scene(sample['kind'], sample['batteryPercentExample'], 1, 1,
                        sample['progressExample'], 312, 0)
        if not layout.comp_scene_design_render(pixels, ctypes.byref(context)):
            raise RuntimeError('Scene rejected its example context')
        Image.frombytes('1', (200, 200), bytes(pixels)).save(PUBLIC / sample['file'])
        sample.update(nativePose=dict(source=str(source.relative_to(ROOT)), sha256=sha(source),
            kind='ORIGINAL_UI67_NATIVE_C_RESTING_FAMILY'), compositionSource='P13_NATIVE_C_LAYOUT',
            outputSha256=sha(PUBLIC / sample['file']))
        samples.append(sample)
    receipt.update(design='P15', parentDesign='P14', rendererDesign='P13', samples=samples,
        reusedFaceDllSha256=metadata['dllSha256'], inheritedScenes={}, comparisonParents={},
        result='ORIGINAL_UI67_STYLE_SCENES_EXPORTED',
        revisionSourceSha256={Path(__file__).relative_to(ROOT).as_posix(): sha(Path(__file__))},
        selectedExpressionExamples={s['name']: 'pose-' + str(s['family']) + '.png' for s in samples},
        completionHeldPose='ORIGINAL_UI67_AUTHORED_HAPPY',
        faceStyle='ORIGINAL_DEVELOPMENT_BOARD_UI67_FULL_SET',
        nativeFaceRendererBuiltThisRevision=True, nativeSceneRendererBuiltThisRevision=False,
        liveMotionChanged=False, timingChanged=False, proceduralFaceReplacement=False,
        ownerFeedback='Use the previous development-board full expression set as the art baseline')
    receipt.pop('responsePeakArtRetained', None)
    (PUBLIC / 'scene-design.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    scene_sheet = Image.new('RGB', (1092, 584), '#f4f2eb'); draw = ImageDraw.Draw(scene_sheet)
    draw.text((18, 12), 'Companion · 原来的它，陪你做不同的事', font=font, fill='#293a33')
    draw.text((18, 35), 'P15 · 原开发板整套神态 / P13布局 · 数值与文案为设计示例，真实状态映射待合入', font=font, fill='#65736b')
    for i, sample in enumerate(samples):
        x, y = 18 + i % 5 * 216, 68 + i // 5 * 249
        scene_sheet.paste(Image.open(PUBLIC / sample['file']).convert('RGB'), (x, y))
        draw.text((x, y + 209), sample['label'], font=font, fill='#293a33')
    scene_sheet.save(PUBLIC / 'scene-library.png')
    print(json.dumps(dict(result=art['result'], anatomyChangedPixels=[s['anatomyChangedPixels'] for s in gallery],
        responseFinished=finished, failures=state['failures'], missingStates=state['missingStates']), ensure_ascii=False))


if __name__ == '__main__': main()
