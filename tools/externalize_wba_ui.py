#!/usr/bin/env python3
"""Move authored UI data into the existing static NOR bank, losslessly.

This is a paired media-geometry change, not an ordinary resource OTA. CEMP
pixels and CUIM entries remain byte-identical. The appended small atlases use
the existing white-run encoding. No seed, sound, or executable code is added.
"""
from pathlib import Path
import argparse,hashlib,json,re,shutil,struct,zlib
from compact_wba_recording_ui import pack,unpack
from wba_resource_geometry import choose_static_bytes,geometry

ROOT=Path(__file__).resolve().parents[1]
sha=lambda data:hashlib.sha256(data).hexdigest()

def numbers(text):
    text=re.sub(r'/\*.*?\*/|//[^\n]*','',text,flags=re.S)
    return [int(v,16 if v.lower().startswith('0x') else 10)
            for v in re.findall(r'(?<!\w)(0x[0-9a-fA-F]+|\d+)(?:[uUlL]+)?(?!\w)',text)]

def generate(base:Path,out:Path,generation:int):
    out.mkdir(parents=True,exist_ok=False)
    profile=json.loads((base/'profile.json').read_bytes())
    bank=(base/'ui-partition.bin').read_bytes()
    assert sha(bank).upper()==profile['uiPartitionSha256'].upper()
    assert generation>profile['generation']
    old_geometry=geometry(len(bank));root=bytearray(bank[old_geometry['rootA']:old_geometry['rootA']+128])
    assert root[:4]==b'CUIR' and zlib.crc32(root[:124])==struct.unpack_from('<I',root,124)[0]
    bo,bs=struct.unpack_from('<II',root,16)
    blob=bank[bo:bo+bs]
    assert zlib.crc32(blob)==struct.unpack_from('<I',root,24)[0]
    external=bytearray();atlas=[];maximum=0;accessory_max=0;dedup={}
    def put(data):
        if data not in dedup:
            dedup[data]=len(external);external.extend(data)
        return '{%du,%du,0x%08Xu}'%(dedup[data],len(data),zlib.crc32(data))
    def convert(source,names):
        nonlocal maximum
        text=source.read_text(encoding='utf-8')
        for name in names:
            pat=rf'static const uint8_t {name}((?:\[\d+\])+?)\s*=\s*\{{(.*?)\}};'
            m=re.search(pat,text,re.S);assert m,(source,name)
            dims=[int(v) for v in re.findall(r'\d+',m[1])]
            raw=bytes(numbers(m[2]));width=dims[-1]
            glyph_count=1
            for d in dims[:-1]:glyph_count*=d
            assert len(raw)==glyph_count*width
            descriptors=[];encoded_bytes=0
            for i in range(glyph_count):
                glyph=raw[i*width:(i+1)*width];encoded=pack(glyph)
                assert unpack(encoded,width)==glyph
                maximum=max(maximum,len(encoded));encoded_bytes+=len(encoded)
                descriptors.append(put(encoded))
            def nested(shape,refs):
                if len(shape)==1:return '{'+','.join(refs)+'}'
                step=len(refs)//shape[0]
                return '{'+','.join(nested(shape[1:],refs[i*step:(i+1)*step]) for i in range(shape[0]))+'}'
            declaration='static const comp_wba_external_bitmap_t '+name+''.join(f'[{d}]' for d in dims[:-1])+' = '+nested(dims[:-1],descriptors)+';'
            text=text[:m.start()]+declaration+text[m.end():]
            atlas.append(dict(name=name,glyphs=glyph_count,decodedBytes=len(raw),encodedBytes=encoded_bytes,
                originalSha256=sha(raw),lossless=True))
        return text
    texts=[convert(ROOT/'app/companion_pendant/runtime/generated/companion_wba_live_menu_values.h',
        ['comp_wba_live_values','comp_wba_value_digits','comp_wba_clock_digits','comp_wba_count_digits']),
        convert(ROOT/'app/companion_pendant/runtime/generated/companion_wba_menu_feedback.h',['comp_wba_menu_feedback']),
        convert(base/'companion_pet_reply_captions.h',['comp_pet_reply_captions'])]
    variation=(base/'companion_pet_variations.h').read_text(encoding='utf-8')
    spans=re.search(r'static const uint8_t comp_pet_accessory_spans\[(\d+)\]\[3\]\s*=\s*\{(.*?)\};',variation,re.S)
    ranges=re.search(r'static const uint16_t comp_pet_accessory_ranges\[10\]\[3\]\[2\]\s*=\s*\{(.*?)\};',variation,re.S)
    assert spans and ranges
    raw=bytes(numbers(spans[2]));rr=numbers(ranges[1]);assert len(raw)==int(spans[1])*3 and len(rr)==60
    refs=[]
    for i in range(30):
        first,count=rr[i*2:i*2+2];data=raw[first*3:(first+count)*3]
        assert len(data)==count*3;accessory_max=max(accessory_max,len(data));refs.append(put(data))
    variation=variation[:spans.start()]+'static const comp_wba_external_bitmap_t comp_pet_accessory_spans[10][3] = {'+','.join('{'+','.join(refs[i*3:(i+1)*3])+'}' for i in range(10))+'};'+variation[spans.end():]
    variation=re.sub(r'static const uint16_t comp_pet_accessory_ranges\[10\]\[3\]\[2\]\s*=\s*\{.*?\};','',variation,flags=re.S)
    texts.append(variation)
    assert len(external)<65536 and maximum<=512 and accessory_max<=256
    offset=bo+bs;used=offset+len(external)
    new_geometry=geometry(choose_static_bytes(used))
    identity=sha(bytes.fromhex(profile['resourceId'])+b'Companion external UI v1\0'+external).upper()
    header='''/* Generated external UI references; original authored ink retained. */
#ifndef COMPANION_WBA_EXTERNAL_UI_H
#define COMPANION_WBA_EXTERNAL_UI_H
#include <stdint.h>
typedef struct { uint16_t offset,bytes; uint32_t crc32; } comp_wba_external_bitmap_t;
'''+f'#define COMP_WBA_EXTERNAL_UI_OFFSET {offset}u\n#define COMP_WBA_EXTERNAL_UI_BYTES {len(external)}u\n#define COMP_WBA_EXTERNAL_UI_CRC32 0x{zlib.crc32(external):08X}u\n#define COMP_WBA_EXTERNAL_MAX_GLYPH_BYTES {maximum}u\n#define COMP_WBA_EXTERNAL_MAX_ACCESSORY_BYTES {accessory_max}u\n'+'\n'.join(texts)+'\n#endif\n'
    (out/'companion_wba_external_ui.h').write_text(header,encoding='utf-8',newline='\n')
    for p in base.glob('*.h'):shutil.copyfile(p,out/p.name)
    contract=(base/'companion_wba_resource_contract.h').read_text(encoding='utf-8')
    contract=contract.replace(f'COMPANION_WBA_RESOURCE_GENERATION {profile["generation"]}u',f'COMPANION_WBA_RESOURCE_GENERATION {generation}u').replace(profile['resourceId'],identity)
    payload_crc,index_crc=struct.unpack_from('<II',bank,56)
    contract=contract.replace('#include "emote_asset_pack.h"','#include "emote_asset_pack.h"\n'+
        f'#define COMPANION_WBA_CEMP_PAYLOAD_CRC32 0x{payload_crc:08X}u\n#define COMPANION_WBA_CEMP_INDEX_CRC32 0x{index_crc:08X}u')
    # Old generated headers can use a different include spelling.
    if 'COMPANION_WBA_CEMP_INDEX_CRC32' not in contract:
        contract=contract.replace('#define COMPANION_WBA_RESOURCE_PROFILE_REVISION',
            f'#define COMPANION_WBA_CEMP_PAYLOAD_CRC32 0x{payload_crc:08X}u\n#define COMPANION_WBA_CEMP_INDEX_CRC32 0x{index_crc:08X}u\n#define COMPANION_WBA_RESOURCE_PROFILE_REVISION')
    (out/'companion_wba_resource_contract.h').write_text(contract,encoding='utf-8',newline='\n')
    merged_blob=blob+external
    struct.pack_into('<I',root,8,generation);struct.pack_into('<II',root,20,len(merged_blob),zlib.crc32(merged_blob))
    struct.pack_into('<I',root,40,(used+4095)&~4095);root[44:76]=bytes.fromhex(identity)
    struct.pack_into('<I',root,124,zlib.crc32(root[:124]))
    new_bank=bytearray(b'\xff'*new_geometry['staticBytes']);new_bank[:offset]=bank[:offset]
    new_bank[offset:used]=external;new_bank[new_geometry['rootA']:new_geometry['rootA']+128]=root
    assert new_bank[:offset]==bank[:offset]
    assert used<=new_geometry['rootA'] and new_geometry['dynamicBase']==len(new_bank)
    (out/'ui-partition.bin').write_bytes(new_bank)
    result=dict(schema='companion.wba.external-ui.v1',generation=generation,sourceGeneration=profile['generation'],
        extensionOffset=offset,extensionBytes=len(external),atlas=atlas,accessorySpansBytes=len(raw),
        accessoryVariants=30,maxGlyphBytes=maximum,maxAccessoryBytes=accessory_max,
        headerSha256=sha((out/'companion_wba_external_ui.h').read_bytes()),
        cempAndOriginalManifestUnchanged=True,sourceBankSha256=sha(bank),newBankSha256=sha(new_bank),
        oldGeometry=old_geometry,newGeometry=new_geometry,pairedGeometryInstallationRequired=True,
        executableCodeMoved=False,codecTablesMoved=False,testsRun=False)
    profile.update(generation=generation,resourceId=identity,uiPartitionBytes=len(new_bank),
        uiPartitionSha256=sha(new_bank).upper(),flashGeometry=new_geometry,
        resourceArenaUsedBytes=used,resourceBudgetBytes=len(new_bank),externalUi=result,
        hardwareAcceptance='NOT_RUN',recordingRegionPreserved=False,
        dynamicRegionIncluded=False,result='RESOURCE_CANDIDATE_BUILT')
    provenance=profile.setdefault('sourceSha256',{})
    for p in (Path(__file__),ROOT/'tools/compact_wba_recording_ui.py',ROOT/'tools/wba_resource_geometry.py',
              out/'companion_wba_external_ui.h',out/'companion_wba_resource_contract.h'):
        provenance[p.relative_to(ROOT).as_posix()]=sha(p.read_bytes()).upper()
    (out/'profile.json').write_text(json.dumps(profile,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    (out/'external-ui.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    return result

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--base',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--generation',type=int,required=True);a=p.parse_args()
    print(json.dumps(generate(a.base.resolve(),a.output.resolve(),a.generation),ensure_ascii=False))
