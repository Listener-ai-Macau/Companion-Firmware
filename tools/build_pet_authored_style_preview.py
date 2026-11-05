"""Build the P15 native preview with original UI67 faces and existing timing."""
from datetime import datetime, timedelta, timezone
import hashlib, json, subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / '.cache/screen-art-polish-20261011'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    prior = json.loads((BASE / 'preview-build-p09/build-result.json').read_bytes())
    for name, digest in prior['sources'].items():
        if sha(Path(name)) != digest: raise RuntimeError('Inherited input changed: ' + name)
    build = BASE / 'preview-build-p15'
    build.mkdir(exist_ok=False)
    original = BASE / 'design-p09/companion_pet_face.c'
    face = ROOT / 'docs/art/iterations/companion-pet-studio-v1/p15/companion_pet_face.c'
    old_dll = BASE / 'preview-build-p09/wba-runtime-preview.dll'
    dll = build / 'wba-runtime-preview.dll'
    command = (BASE / 'preview-build-p09/build.cmd').read_text(encoding='utf-8')
    if command.count(str(original)) != 1 or command.count(str(old_dll)) != 1:
        raise RuntimeError('Native compiler command changed')
    command = command.replace(str(original), str(face)).replace(str(old_dll), str(dll))
    (build / 'build.cmd').write_text(command, encoding='utf-8')
    result = subprocess.run(['cmd.exe', '/d', '/c', str(build / 'build.cmd')],
        cwd=build, capture_output=True)
    (build / 'build.log').write_bytes(result.stdout + result.stderr)
    if result.returncode: raise RuntimeError(result.stdout.decode(errors='replace') + result.stderr.decode(errors='replace'))
    inputs = [face if Path(name) == original else Path(name) for name in prior['sources']]
    receipt = dict(prior, result='BUILT_NATIVE_ORIGINAL_UI67_STYLE_PREVIEW', design='P15',
        previousDesign='P09', createdAtLocal=datetime.now(timezone(timedelta(hours=8))).isoformat(),
        dllSha256=sha(dll), sources={str(p): sha(p) for p in inputs},
        faceStyle='ORIGINAL_UI67_AUTHORED_FULL_FAMILY_GAZE_AND_REACTION_ASSETS',
        proceduralFaceReplacement=False, intensityDeformsFace=False,
        originalProportionsAndOrnamentsPreserved=True,
        blinkAndMotionRuntimeChanged=False, additionalMotionPhases=False,
        physicalTimingOrDriverChanged=False, productionSourcesChanged=False,
        armFirmwareBuilt=False, installed=False, testsRun=False, boardAccess=False)
    (build / 'build-result.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(dict(result=receipt['result'], dllSha256=receipt['dllSha256']), ensure_ascii=False))


if __name__ == '__main__': main()
