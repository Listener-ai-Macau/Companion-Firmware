#!/usr/bin/env python3
"""Collect matching app, resident boot, UI and native pet preview; never flash."""
from pathlib import Path
import argparse, hashlib, json, shutil, struct
from wba_resource_geometry import from_profile as resource_geometry

def sha(data):return hashlib.sha256(data).hexdigest()
def load(path):return json.loads(path.read_text(encoding='utf-8-sig'))

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('app','boot','resources','preview','output'):
        parser.add_argument('--'+name,type=Path,required=True)
    args=parser.parse_args()
    app=load(args.app/'result.json');boot=load(args.boot/'result.json')
    ui=load(args.resources/'profile.json');preview=load(args.preview/'preview-result.json')
    payloads={'companion-v11-app.bin':(args.app/'companion-v11-board-bringup.bin').read_bytes(),
        'companion-v11-boot.bin':(args.boot/'companion_wba55_v11_boot.bin').read_bytes(),
        'ui-partition.bin':(args.resources/'ui-partition.bin').read_bytes()}
    if app['result']!='COMPILED_BUILD_ONLY' or boot['result']!='PASS' or boot['flashed']:
        raise RuntimeError('Matching build-only payloads are required')
    if app['firmware_version']!=boot['firmware_version'] or boot['installed_image_size']!=len(payloads['companion-v11-app.bin']):
        raise RuntimeError('Boot version and app extent must match')
    if sha(payloads['companion-v11-app.bin'])!=app['bin_sha256'] or sha(payloads['companion-v11-boot.bin'])!=boot['bin_sha256']:
        raise RuntimeError('Actual binaries differ from build receipts')
    if sha(payloads['ui-partition.bin']).upper()!=ui['uiPartitionSha256'] or app['ui_resource_profile']['resourceId']!=ui['resourceId']:
        raise RuntimeError('Firmware and actual UI bank must match')
    if ui.get('storageLayoutVersion')==3:
        flash_geometry=resource_geometry(ui,len(payloads['ui-partition.bin']))
        expected_ui_bytes=flash_geometry['staticBytes']
    else:flash_geometry=None;expected_ui_bytes=2097152
    if app['mcu']!='STM32WBA55CEU6' or len(payloads['companion-v11-app.bin'])>475136 or len(payloads['companion-v11-boot.bin'])>32768 or len(payloads['ui-partition.bin'])!=expected_ui_bytes:
        raise RuntimeError('Payload must fit the actual CE board geometry')
    if preview['generation']!=ui['generation']:
        raise RuntimeError('Preview must use the delivered UI generation')
    if any(scene['resourceImageSha256'].upper()!=ui['uiPartitionSha256']
           for scene in [*preview['scenes'],*preview.get('emotionScenes',[]),*preview.get('poseScenes',[]),
               *preview.get('repeatScenes',[]),*preview.get('localCaptionScenes',[]),*preview.get('replyLayoutMockups',[])]):
        raise RuntimeError('Rendered preview must use this exact UI image')
    combined=payloads['companion-v11-boot.bin']+b'\xff'*(32768-len(payloads['companion-v11-boot.bin']))+payloads['companion-v11-app.bin']
    for offset in (0,32768):
        stack,reset=struct.unpack_from('<II',combined,offset)
        end=len(payloads['companion-v11-boot.bin']) if offset==0 else len(combined)
        if not (0x20000000<stack<=0x20020000 and stack%8==0 and reset&1 and 0x08000000+offset<=(reset&~1)<0x08000000+end):
            raise RuntimeError('Invalid resident boot/app vector table')
    payloads['companion-v11-initial-boot-and-app.bin']=combined
    out=args.output;out.mkdir(parents=True,exist_ok=True)
    for name,data in payloads.items():(out/name).write_bytes(data)
    for name,path in (('app-build.json',args.app/'result.json'),('boot-build.json',args.boot/'result.json'),
            ('ui-profile.json',args.resources/'profile.json')):shutil.copy2(path,out/name)
    if ui.get('producerSource'):
        workspace=Path(ui['producerAssetRoot'])
        shutil.copy2(workspace/ui['producerSource'],out/'ui-producer-source.py')
        ornament_sources=ui.get('artComposition',{}).get('emotionOrnaments',{}).get('sourceSha256',{})
        if ornament_sources:
            source_out=out/'ornament-sources';source_out.mkdir(exist_ok=True)
            for source,expected in ornament_sources.items():
                path=workspace/source
                if sha(path.read_bytes()).upper()!=expected.upper():
                    raise RuntimeError('Ornament source changed before packaging: '+source)
                shutil.copy2(path,source_out/path.name)
        reply_sources=ui.get('artComposition',{}).get('replyTextReserve',{}).get('sourceSha256',{})
        for source,expected in reply_sources.items():
            path=workspace/source
            if sha(path.read_bytes()).upper()!=expected.upper():
                raise RuntimeError('Reply layout source changed before packaging: '+source)
            shutil.copy2(path,out/path.name)
        for section in ('petPerformance','petArtRefinement','petVariations','localReplyCaptions','proceduralFaceTemplate'):
            for source,expected in ui.get('artComposition',{}).get(section,{}).get('sourceSha256',{}).items():
                path=workspace/source
                if sha(path.read_bytes()).upper()!=expected.upper():
                    raise RuntimeError('Pet design source changed before packaging: '+source)
                shutil.copy2(path,out/path.name)
        captions=ui.get('artComposition',{}).get('localReplyCaptions')
        if captions:
            path=args.resources/captions['header']
            if sha(path.read_bytes()).upper()!=captions['headerSha256']:
                raise RuntimeError('Local reply caption atlas changed before packaging')
            shutil.copy2(path,out/path.name)
        variations=ui.get('artComposition',{}).get('petVariations')
        if variations:
            path=args.resources/variations['header']
            if sha(path.read_bytes()).upper()!=variations['headerSha256']:raise RuntimeError('Accessory atlas changed before packaging')
            shutil.copy2(path,out/path.name)
        template=ui.get('artComposition',{}).get('proceduralFaceTemplate')
        if template:
            path=args.resources/template['header']
            if sha(path.read_bytes()).upper()!=template['headerSha256']:raise RuntimeError('Anatomy template changed before packaging')
            shutil.copy2(path,out/path.name)
    for path in args.preview.glob('*'):
        if path.suffix in ('.png','.gif','.json','.wav'):shutil.copy2(path,out/path.name)
    sound_path=args.preview/'sound-design.json'
    sound=load(sound_path) if sound_path.is_file() else None
    if sound:
        for source,expected in sound['sourceSha256'].items():
            if sha((Path(ui['producerAssetRoot'])/source).read_bytes())!=expected:
                raise RuntimeError('Sound design source changed before packaging: '+source)
        for row in sound['sounds']:
            if sha((out/row['file']).read_bytes())!=row['sha256']:
                raise RuntimeError('Sound audition changed before packaging: '+row['file'])
        if sha((out/sound['mixFile']).read_bytes())!=sound['mixSha256']:
            raise RuntimeError('Combined sound audition changed before packaging')
    version=app['firmware_version']
    result={'schema':'companion.screen-design.candidate.v2','result':'BUILD_ONLY_DESIGN_CANDIDATE',
        'firmware':f'{version>>16}.{(version>>8)&255}.{version&255}','firmwareVersion':version,
        'uiGeneration':ui['generation'],'mcu':app['mcu'],
        'files':{name:{'sha256':sha(data),'bytes':len(data)} for name,data in payloads.items()},
        'internalLoadAddress':'0x08000000','uiLoadAddress':'0x90000000','appFlashMarginBytes':475136-len(payloads['companion-v11-app.bin']),
        'interaction':'visible glance/expression/optional second expression/settle; pickup/shake/head pat/cheek/nose/chin',
        'art':('registered eye dimensions/highlights and nose/cheek masks, native studio brow/mouth curves, paper-white status rail' if
            ui.get('artComposition',{}).get('nativeStudioArt') else
            'registered native eyes/brows/mouth and paper-white status rail; no symbolic forelock'),
        'nativeStudioArt':ui.get('artComposition',{}).get('nativeStudioArt',False),
        'emotionOrnaments':ui.get('artComposition',{}).get('emotionOrnaments'),
        'expressionVariants':ui.get('artComposition',{}).get('expressionVariants',[]),
        'petPerformance':ui.get('artComposition',{}).get('petPerformance'),
        'petArtRefinement':ui.get('artComposition',{}).get('petArtRefinement'),
        'petVariations':ui.get('artComposition',{}).get('petVariations'),
        'storageLayoutVersion':ui.get('storageLayoutVersion',2),
        'flashGeometry':flash_geometry,
        'panelAwareMotion':{'requestToVisibleThresholdMs':650,'fastPosePhases':['arrive','peak','release'],
            'slowPosePhases':['peak'],'extraPeakHoldMs':160,'advanceOnlyOnSuccessfulMatchingCompletion':True},
        'localReplyCaptions':ui.get('artComposition',{}).get('localReplyCaptions'),
        'petSounds':sound,
        'replyTextReserve':ui.get('artComposition',{}).get('replyTextReserve'),
        'eyeReopening':'renderer follows successfully committed authored eyelid masks; existing post-BUSY plane normalization, no extra visible refresh',
        'peripherals':f'simulated inputs and {preview["panelModelMs"]} ms panel model in preview; actual FPS and ghosting not established',
        'touchCandidate':'STOP-separated read only after real address ACK during idle initialization; subsequent reads retain the same total timeout budget',
        'touch':'ADDRESS_ONLY_0x38_ACK_OBSERVED_IDENTITY_READ_FAILS; actual touch unresolved',
        'hardwareAcceptance':'NOT_RUN','ownerAcceptance':'NOT_RUN','fullChainAcceptance':'NOT_RUN','flashed':False,
        'installation':'Acquire the recorded board release. Compare the exact profile boundary with the installed media geometry; a changed static extent needs the authorized empty-media layout transition, not ordinary UI OTA. Retain current recording sources and NVM; observe affected screen and prompt Owner.'}
    if ui['generation']>=66:
        result['proceduralExpression']={'template':'registered native anatomy plus bounded fixed-point curves',
            'dimensions':['gaze','eyelid aperture','brow lift and asymmetry','mouth width and curve','head inclination','ornament placement','pause'],
            'interactionDriven':True,'randomness':'one intent seed per accepted input or daily action boundary; unchanged on retries',
            'repeatContext':'same interaction within 15 seconds, capped at three reinforcement steps','extraFrameRamBytes':0}
        result['panelAwareMotion']['extraPeakHoldMs']={'minimum':90,'maximum':305,'source':'intent and recent repetition'}
        if ui['generation']>=67:
            result['panelAwareMotion']['followupPosePhases']={'cheek':['peak'],'shake':['peak']}
            result['proceduralExpression']['refinement']={
                'eyelids':'bounded oval aperture retaining native highlight shapes',
                'timing':'eyes lead head; compatible mouth curves blend from prior mood and retain a small settling afterglow',
                'ornaments':'one primary motif; native cubic heart contour and phase-bound 0..2 pixel float reused on committed status/blink frames'}
        source_out=out/'behavior-sources';source_out.mkdir(exist_ok=True)
        workspace=Path(ui['producerAssetRoot'])
        for name in ('companion_pet_behavior.c','companion_pet_behavior.h','companion_pet_face.c','companion_pet_face.h',
                'companion_runtime.c','companion_runtime.h','companion_renderer.c','companion_renderer.h'):
            source='app/companion_pendant/runtime/'+name;path=workspace/source
            if sha(path.read_bytes())!=app['source_sha256'][source]:
                raise RuntimeError('Compiled behavior source changed before packaging: '+source)
            shutil.copy2(path,source_out/name)
        behavior=args.preview/'behavior-preview.json'
        if behavior.is_file():
            actual=load(behavior)
            if actual['resourceImageSha256'].upper()!=ui['uiPartitionSha256'] or actual['generation']!=ui['generation']:
                raise RuntimeError('Behavior artwork uses another resource bank')
            result['behaviorPreview']={'file':behavior.name,'panelModelsMs':actual['panelModelsMs'],
                'scope':actual['scope'],'hardwareAcceptance':actual['hardwareAcceptance']}
    (out/'candidate.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:result[k] for k in ('result','firmware','uiGeneration','appFlashMarginBytes','flashed')}))

if __name__=='__main__':main()
