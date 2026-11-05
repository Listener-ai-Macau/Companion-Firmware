"""Select the quieter P12 completion pose for P14, reusing frozen native art.

No renderer build or device access. Other P13 scenes are inherited byte for
byte. The broad closed-eye response peak remains in the P09 interaction art.
"""
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import shutil
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / '.cache/screen-art-polish-20261011'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    prior = json.loads((BASE / 'studio-p13/scene-design.json').read_bytes())
    older = json.loads((BASE / 'studio-p12/scene-design.json').read_bytes())
    output = BASE / 'studio-p14'
    if (output / 'scene-design.json').exists():
        raise RuntimeError('P14 scene receipt already frozen')
    output.mkdir(exist_ok=True)
    receipt = deepcopy(prior)
    inherited = {}
    for sample in receipt['samples']:
        source_design = 'p12' if sample['name'] == 'done' else 'p13'
        source_receipt = older if source_design == 'p12' else prior
        source_sample = next(s for s in source_receipt['samples'] if s['name'] == sample['name'])
        source = BASE / ('studio-' + source_design) / sample['file']
        expected = source_sample.get('outputSha256', prior['comparisonParents'].get(sample['name']))
        if expected is None or sha(source) != expected:
            raise RuntimeError('Frozen native scene changed: ' + str(source))
        shutil.copyfile(source, output / sample['file'])
        sample.update(nativePose=deepcopy(source_sample['nativePose']),
                      compositionSource=source_design.upper() + '_UNCHANGED_IMAGE',
                      outputSha256=expected)
        inherited[sample['name']] = dict(design=source_design.upper(), sha256=sha(source))
    font = ImageFont.truetype('C:/Windows/Fonts/msyh.ttc', 12)
    comparison = Image.new('RGB', (466, 285), '#f4f2eb')
    draw = ImageDraw.Draw(comparison)
    draw.text((18, 10), '更新完成 · 原生 200×200 黑白', font=font, fill='#293a33')
    for x, version, label in ((18, 'p13', 'P13 · 笑眼停留过于用力'),
                              (248, 'p14', 'P14 · 睁眼，轻轻微笑')):
        comparison.paste(Image.open(BASE / ('studio-' + version) / 'scene-done.png').convert('RGB'), (x, 43))
        draw.text((x, 252), label, font=font, fill='#293a33')
    comparison.save(output / 'composition-comparison.png')
    sheet = Image.new('RGB', (1092, 584), '#f4f2eb')
    draw = ImageDraw.Draw(sheet)
    draw.text((18, 12), 'Companion · 同一个小伙伴，不同的陪伴状态', font=font, fill='#293a33')
    draw.text((18, 35), 'P14 · 完成画面选用睁眼轻笑 · 其它九张继承 P13 · 数值与短句为设计示例', font=font, fill='#65736b')
    for i, sample in enumerate(receipt['samples']):
        x, y = 18 + i % 5 * 216, 68 + i // 5 * 249
        sheet.paste(Image.open(output / sample['file']).convert('RGB'), (x, y))
        draw.text((x, y + 209), sample['label'], font=font, fill='#293a33')
    sheet.save(output / 'scene-library.png')
    receipt.update(design='P14', parentDesign='P13', rendererDesign='P13',
        createdAtLocal=datetime.now(timezone(timedelta(hours=8))).isoformat(),
        result='COMPLETION_POSE_SELECTION_REFINED', inheritedScenes=inherited,
        comparisonParents={'done': prior['samples'][7]['outputSha256']},
        nativeRendererBuiltThisRevision=False,
        revisionSourceSha256={Path(__file__).relative_to(ROOT).as_posix(): sha(Path(__file__))},
        selectedExpressionExamples={**prior['selectedExpressionExamples'], 'done': 'pose-2.png'},
        completionHeldPose='EXISTING_OPEN_EYE_LIGHT_SMILE',
        completionMotionIntent='SHORT_REACTION_THEN_OPEN_EYE_HOLD_NOT_PRODUCTION_INTEGRATED',
        ownerFeedback='P13 completion held smile-eye pose looks odd; keep original identity',
        responsePeakArtRetained=True, timingChanged=False, liveMotionChanged=False,
        testsRun=False, installed=False, boardAccess=False)
    (output / 'scene-design.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(dict(result=receipt['result'], output=str(output),
        completionSha256=receipt['samples'][7]['outputSha256'],
        inheritedRendererSha256=receipt['sceneDllSha256']), ensure_ascii=False))


if __name__ == '__main__':
    main()
