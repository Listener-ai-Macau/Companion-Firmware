#!/usr/bin/env python3
"""Build legible native pet motion over the existing CEMP catalog.

Sparse XOR entries carry eyes/brows changes without growing firmware's
catalog or RAM. Candidate contract activation is explicit, after preview.
"""
from pathlib import Path
import argparse, hashlib, importlib.util, json, re, struct, zlib
from build_wba_product_resources import ROOT, make_frames, fnv, sha, xor_patch, write_contract
from build_emote_asset_pack import encode_packbits
from wba_resource_geometry import choose_static_bytes,geometry,from_profile as resource_geometry

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--base',type=Path,default=ROOT/'.cache/wba-product-resources')
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--generation',type=int,default=60)
    p.add_argument('--producer',type=Path,help='immutable source snapshot used for candidate art')
    p.add_argument('--refine-ornaments',action='store_true',help='compose registered emotion charms over the native faces')
    p.add_argument('--richer-poses',action='store_true',help='compose six additional native facial poses and readable daily expressions')
    p.add_argument('--performance',action='store_true',help='native-scale facial acting with authored local reply captions')
    p.add_argument('--polished',action='store_true',help='soft eyelids and adaptive-motion intermediate art')
    p.add_argument('--studio',action='store_true',help='imagegen-directed native curves with coherent family anchors')
    p.add_argument('--procedural',action='store_true',help='registered anatomy for the interaction-driven C parameter compositor')
    p.add_argument('--activate-contract',action='store_true')
    args=p.parse_args();base=args.base;out=args.output;out.mkdir(parents=True,exist_ok=True)
    if args.performance and (not args.richer_poses or not args.refine_ornaments or args.generation<63):
        raise ValueError('Performance needs richer poses, registered ornaments and generation >=63')
    if args.polished and (not args.performance or args.generation<64):raise ValueError('Polished motion needs performance and generation >=64')
    if args.studio and (not args.polished or args.generation<65):raise ValueError('Studio art needs polished motion and generation >=65')
    if args.procedural and (not args.studio or args.generation<66):raise ValueError('Procedural anatomy needs studio art and generation >=66')
    producer_path=args.producer.resolve() if args.producer else ROOT/'tools/build_wba_product_resources.py'
    producer_bytes=producer_path.read_bytes()
    if args.producer:
        spec=importlib.util.spec_from_file_location('companion_pet_candidate_producer',producer_path)
        producer=importlib.util.module_from_spec(spec);spec.loader.exec_module(producer)
        # The immutable module contains the exact drawing code. Assets retain
        # their real workspace paths; its CLI/main output defaults are unused.
        producer.ROOT=ROOT
        draw_frames=producer.make_frames
        fnv,sha,xor_patch=producer.fnv,producer.sha,producer.xor_patch
    else:
        draw_frames=make_frames
        fnv,sha,xor_patch=globals()['fnv'],globals()['sha'],globals()['xor_patch']
    profile=json.loads((base/'profile.json').read_text())
    image=(base/'ui-partition.bin').read_bytes()
    layout3=profile.get('storageLayoutVersion')==3
    if len(image)!=profile['uiPartitionBytes'] or len(image)%4096 or sha(image)!=profile['uiPartitionSha256']:
        raise ValueError('Base UI image does not match its preserved profile')
    if layout3:
        base_geometry=resource_geometry(profile,len(image))
        root_offset=arena_end=base_geometry['rootA']
    else:
        if len(image)!=2097152:raise ValueError('Legacy layout requires its original 2 MiB image')
        root_offset=len(image)-8192;arena_end=0x1DC000
    if args.procedural and not layout3:raise ValueError('Procedural candidates use the actual-size static/dynamic layout')
    if args.generation<=profile['generation']:raise ValueError('Generation must increase')
    source_hashes={}
    for source,expected in profile['sourceSha256'].items():
        actual=sha((ROOT/source).read_bytes())
        if source!='tools/build_wba_product_resources.py' and actual!=expected:
            raise ValueError(f'Preserved art source changed: {source}')
        if source!='tools/build_wba_product_resources.py':source_hashes[source]=actual
    source_hashes[producer_path.relative_to(ROOT).as_posix()]=sha(producer_bytes)
    cemp=image[:profile['cempBytes']]
    states=set(profile['states'])
    state_base={state:state for state in states}
    if args.polished:
        from wba_pet_performance import STYLES
        for key in STYLES:
            for phase in ('arrive','release'):
                state=f'pet_motion_{key.removeprefix("tap_local_")}_{phase}'
                states.add(state);state_base[state]=key
    draw_options=dict(lively=True,signature=False,reply_poses=True)
    if args.refine_ornaments:draw_options['refined_ornaments']=True
    if args.richer_poses:draw_options['richer_poses']=True
    if args.performance:draw_options['performance']=True
    if args.polished:draw_options['polished']=True
    if args.studio:draw_options['studio']=True
    captions=None
    if args.performance:
        from wba_pet_reply_captions import build as build_captions
        captions=build_captions(ROOT,out)
    frames,metadata,quality=draw_frames(states,**draw_options)
    if args.procedural:
        from wba_pet_face_template import build as build_template
        template=build_template(ROOT,out,draw_frames);quality['proceduralFaceTemplate']=template
        source_hashes.update(template['sourceSha256'])
        source_hashes[(out/template['header']).resolve().relative_to(ROOT).as_posix()]=template['headerSha256']
    if args.polished:
        from wba_native_art_components import load_authority
        from wba_emotion_ornaments import EmotionOrnaments
        from wba_pet_art_refinement import PetArtRefinement
        from wba_pet_variations import build as build_variations
        if args.studio:
            from wba_pet_studio_art import PetStudioArt
            accessory_art=PetStudioArt(ROOT,EmotionOrnaments(ROOT,load_authority(ROOT)))
        else:accessory_art=PetArtRefinement(ROOT,EmotionOrnaments(ROOT,load_authority(ROOT)))
        variation=build_variations(ROOT,out,accessory_art)
        quality['petVariations']=variation;source_hashes.update(variation['sourceSha256'])
        source_hashes[(out/variation['header']).resolve().relative_to(ROOT).as_posix()]=variation['headerSha256']
    source_hashes.update(quality.get('emotionOrnaments',{}).get('sourceSha256',{}))
    source_hashes.update(quality.get('replyTextReserve',{}).get('sourceSha256',{}))
    source_hashes.update(quality.get('petPerformance',{}).get('sourceSha256',{}))
    source_hashes.update(quality.get('petArtRefinement',{}).get('sourceSha256',{}))
    if args.performance:
        quality['localReplyCaptions']=captions
        source_hashes.update(quality['localReplyCaptions']['sourceSha256'])
        source_hashes[(out/'companion_pet_reply_captions.h').resolve().relative_to(ROOT).as_posix()]=quality['localReplyCaptions']['headerSha256']
    clip_offset,frame_offset,string_offset,string_size,_=struct.unpack_from('<IIIII',cemp,32)
    clip_indices={};base_frames={}
    for index in range(profile['canonicalFrameCount']):
        name_offset,first,count=struct.unpack_from('<IHH',cemp,clip_offset+index*16)
        if count!=1:raise ValueError('Expected the existing single-frame catalog')
        begin=string_offset+name_offset;end=cemp.index(0,begin)
        name=cemp[begin:end].decode('ascii');clip_indices[name]=first
        pbm=(base/'frames'/f'{name}.pbm').read_bytes()
        raw=bytes(v^255 for v in pbm.split(b'\n',2)[2])
        if len(raw)!=5000:raise ValueError('Invalid preserved native frame')
        base_frames[name]=raw
    state_clip={state:profile['states'][state_base[state]]['canonicalClip'] for state in states}
    compact_meta=None
    if args.polished and layout3:
        from wba_pet_compact_catalog import build as compact_catalog
        cemp,compact_meta,base_frames,clip_indices,state_clip=compact_catalog(base,profile,frames,out)
        source=ROOT/'tools/wba_pet_compact_catalog.py';source_hashes[source.relative_to(ROOT).as_posix()]=sha(source.read_bytes())
        quality['compactCatalog']={'familyBases':10,'canonicalFrames':compact_meta['frame_count'],
            'method':'native family bases, original menu and recording rasters; exact final pixels in existing XOR/PackBits entries',
            'extraFrameRamBytes':0}
    identity=hashlib.sha256(f'companion-wba-ui-assets-generation{args.generation}\0'.encode())
    if args.performance:identity.update(bytes.fromhex(quality['localReplyCaptions']['headerSha256']))
    if args.polished:identity.update(bytes.fromhex(quality['petVariations']['headerSha256']))
    if args.procedural:identity.update(bytes.fromhex(template['headerSha256']))
    for state in sorted(states):
        identity.update(state.encode()+b'\0'+bytes.fromhex(metadata[state]['sha256'])+struct.pack('<H',480))
    resource_id=identity.hexdigest().upper()
    offset=(len(cemp)+4095)&~4095
    manifest_bytes=32+24*len(states);blob=bytearray(manifest_bytes);payload=bytearray();offsets={}
    struct.pack_into('<4sHHHHI',blob,0,b'CUIM',1,32,len(states),24,manifest_bytes)
    rows=[];changed=0;changed_kinds={}
    for state in states:
        clip=state_clip[state];original=base_frames[clip]
        target=frames[state];patch=xor_patch(original,target)
        flags=4 if patch else 0
        if patch and compact_meta:
            packed=encode_packbits(target)
            if len(packed)<len(patch):patch=packed;flags=2
        if state not in profile['states'] or metadata[state]['sha256']!=profile['states'][state]['sha256']:
            changed+=1;kind=metadata[state]['kind'];changed_kinds[kind]=changed_kinds.get(kind,0)+1
        rows.append((fnv(state),65535 if flags==2 else clip_indices[clip],target,patch,flags,state))
    rows.sort()
    for index,(state_hash,base_index,target,patch,flags,state) in enumerate(rows):
        where=0
        if patch:
            key=(flags,patch)
            if key not in offsets:
                offsets[key]=offset+manifest_bytes+len(payload);payload.extend(patch)
            where=offsets[key]
        struct.pack_into('<IHHIIHHI',blob,32+index*24,state_hash,base_index,flags,
            zlib.crc32(target),where,len(patch),480,zlib.crc32(patch) if patch else 0)
    blob.extend(payload)
    flash_geometry=None
    if layout3:
        flash_geometry=geometry(choose_static_bytes(offset+len(blob)))
        root_offset=arena_end=flash_geometry['rootA']
        candidate=bytearray(b'\xff'*flash_geometry['staticBytes'])
    else:
        if offset+len(blob)>arena_end:raise ValueError(f'Native art exceeds the atomic UI arena: {offset+len(blob)} > {arena_end}')
        candidate=bytearray(image);candidate[offset:arena_end]=b'\xff'*(arena_end-offset)
    candidate[:offset]=b'\xff'*offset;candidate[:len(cemp)]=cemp
    candidate[offset:offset+len(blob)]=blob
    root=bytearray(b'\xff'*128)
    struct.pack_into('<4sHHIIIIIIIII',root,0,b'CUIR',1,128,args.generation,len(cemp),offset,
        len(blob),zlib.crc32(blob),0,manifest_bytes,zlib.crc32(blob[:manifest_bytes]),
        (offset+len(blob)+4095)&~4095)
    root[44:76]=bytes.fromhex(resource_id);struct.pack_into('<I',root,124,zlib.crc32(root[:124]))
    candidate[root_offset:root_offset+128]=root
    (out/'ui-partition.bin').write_bytes(candidate)
    header=base/'companion_wba_resource_contract.h'
    if not header.exists():header=ROOT/'app/companion_pendant/runtime/generated/companion_wba_resource_contract.h'
    if compact_meta:
        if args.producer:
            producer.GENERATED=out/'companion_wba_resource_contract.h'
            producer.GENERATION=args.generation
            producer.write_contract(cemp,compact_meta,resource_id,len(states))
        else:
            import build_wba_product_resources as live_producer
            live_producer.GENERATED=out/'companion_wba_resource_contract.h';live_producer.GENERATION=args.generation
            write_contract(cemp,compact_meta,resource_id,len(states))
        header=out/'companion_wba_resource_contract.h'
    text=header.read_text(encoding='ascii')
    if not compact_meta and f'"{profile["resourceId"]}"' not in text:
        raise ValueError('Preserved resource contract does not match the base catalog')
    text=re.sub(r'(COMPANION_WBA_RESOURCE_GENERATION )\d+u',rf'\g<1>{args.generation}u',text)
    text=re.sub(r'(COMPANION_WBA_RESOURCE_STATE_COUNT )\d+u',rf'\g<1>{len(states)}u',text)
    text=re.sub(r'(COMPANION_WBA_RESOURCE_ID ")[A-F0-9]+"',rf'\g<1>{resource_id}"',text)
    (out/header.name).write_text(text,encoding='ascii')
    if args.activate_contract:header.write_text(text,encoding='ascii')
    source_hashes[Path(__file__).relative_to(ROOT).as_posix()]=sha(Path(__file__).read_bytes())
    source_hashes['tools/wba_resource_geometry.py']=sha((ROOT/'tools/wba_resource_geometry.py').read_bytes())
    if producer_path.read_bytes()!=producer_bytes:raise ValueError('Art producer changed during this build')
    for source,expected in source_hashes.items():
        if sha((ROOT/source).read_bytes())!=expected:raise ValueError('Art input changed during this build: '+source)
    result={'result':'RESOURCE_CANDIDATE_BUILT','generation':args.generation,
        'resourceId':resource_id,'profileRevision':profile['profileRevision'],
        'uiPartitionSha256':sha(candidate),'uiPartitionBytes':len(candidate),
        'cempBytes':len(cemp),'canonicalFrameCount':len(clip_indices),
        'stateCount':len(states),'changedStates':changed,'changedKinds':changed_kinds,
        'generationBytes':len(blob),'generationPatchBytes':len(payload),
        'baseImageSha256':sha(image),'storageLayoutVersion':profile.get('storageLayoutVersion',2),
        'resourceArenaUsedBytes':offset+len(blob),'resourceBudgetBytes':len(image),
        'diagnosticAudioIncluded':profile.get('diagnosticAudioIncluded',True),
        'recordingRegionPreserved':True if layout3 else candidate[arena_end:root_offset]==image[arena_end:root_offset],
        'dynamicRegionIncluded':False if layout3 else True,
        'artComposition':quality,'contractActivated':args.activate_contract,
        'producerSource':producer_path.relative_to(ROOT).as_posix(),'producerAssetRoot':str(ROOT),
        'hardwareAcceptance':'NOT_RUN','fullChainAcceptance':'NOT_RUN',
        'sourceSha256':source_hashes}
    if flash_geometry:result['flashGeometry']=flash_geometry
    (out/'profile.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:result[k] for k in ('result','generation','changedStates','changedKinds','generationBytes','generationPatchBytes','uiPartitionSha256','contractActivated')}))

if __name__=='__main__':main()
