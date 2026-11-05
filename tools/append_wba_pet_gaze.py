"""Append a reviewed face or recovered audio ornament, preserving the old bank.

Uses the existing packed-frame format. A new App/Boot/profile must adopt any
resulting geometry; this is never a resource-only OTA across old dynamic data.
"""
from pathlib import Path
import argparse,copy,hashlib,json,re,shutil,struct,sys,zlib

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools/faraday_upper_art'))
from build_ui_asset_generation import encode_packbits,fnv1a32
from wba_resource_geometry import geometry,choose_static_bytes
from append_wba_pet_polish import replace_number

def sha(data):return hashlib.sha256(data).hexdigest()
def dump(path,value):path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

def build(base,art,out,generation,attention=False,speaker=False):
    assert not (attention and speaker),'Choose one appended state'
    assert not out.exists(),'Fresh candidate directory required'
    profile=json.loads((base/'profile.json').read_bytes());bank=(base/'ui-partition.bin').read_bytes()
    assert generation>profile['generation'] and sha(bank).upper()==profile['uiPartitionSha256'].upper()
    old_geo=geometry(len(bank),profile['flashGeometry']['norBytes']);assert old_geo==profile['flashGeometry']
    review=json.loads((art/'review.json').read_bytes())
    if speaker:
        assert review['schema']=='companion.original-audio-ornament-recovery.v1'
        assert review['decision']=='EXACT_ORIGINAL_PIXEL_RESTORATION_NO_ART_REDRAW'
        assert review['blackPixels']==152 and review['bounds']==[159,158,197,177]
        source=(art/'original-speaker-source-frame.bin').read_bytes()
        assert sha(source)==review['sourceFrameSha256']
        frame_path=art/review['frame'];expected=review['frameSha256']
    elif attention:
        assert review['r2']['decision']=='AGENT_STATIC_CANDIDATE_OWNER_NOT_ACCEPTED'
        assert not review['resourceImported'] and not review['physicalAccepted']
        frame_path=art/review['r2']['frame']
        conversion=json.loads((art/'conversion-r2.json').read_bytes())
        expected=conversion['sha256']
        assert conversion['top16Blank'] and conversion['bottom26Blank']
    else:
        assert review['selectedFrame']=='calm-down-r5-frame.bin' and review['agentStaticSelected'] and not review['physicalAccepted']
        frame_path=art/review['selectedFrame'];expected=review['selectedFrameSha256']
    frame=frame_path.read_bytes()
    assert sha(frame)==expected and len(frame)==5000
    assert frame[:400]==b'\xff'*400
    if speaker:
        original={(x,y) for y in range(156,180) for x in range(150,200)
                  if not source[y*25+x//8]&(128>>(x%8))}
        recovered={(x,y) for y in range(200) for x in range(200)
                   if not frame[y*25+x//8]&(128>>(x%8))}
        assert original==recovered and len(recovered)==152
    else:assert frame[-650:]==b'\xff'*650
    root=bytearray(bank[old_geo['rootA']:old_geo['rootA']+128])
    assert root[:4]==b'CUIR' and zlib.crc32(root[:124])==struct.unpack_from('<I',root,124)[0]
    bo,bs=struct.unpack_from('<II',root,16);mo,ms,mc=struct.unpack_from('<III',root,28)
    old_blob=bank[bo:bo+bs];manifest=old_blob[:ms]
    assert mo==0 and manifest[:4]==b'CUIM' and zlib.crc32(manifest)==mc and zlib.crc32(old_blob)==struct.unpack_from('<I',root,24)[0]
    count,row_bytes=struct.unpack_from('<HH',manifest,8)
    assert row_bytes==24 and ms==32+count*24 and count==profile['stateCount']
    old_rows=[list(struct.unpack_from('<IHHIIHHI',manifest,32+i*24)) for i in range(count)]
    assert all(a[0]<b[0] for a,b in zip(old_rows,old_rows[1:]))
    rows=copy.deepcopy(old_rows)
    for row in rows:
        if row[2]:
            assert bo+ms<=row[4] and row[4]+row[5]<=bo+bs
            assert zlib.crc32(bank[row[4]:row[4]+row[5]])==row[7]
            row[4]+=24
    state='speaker_original' if speaker else 'pet_attention_calm' if attention else 'pet_gaze_calm_down';hashed=fnv1a32(state)
    assert hashed not in {r[0] for r in rows}
    packed=encode_packbits(frame);offset=bo+bs+24
    rows.append([hashed,65535,2,zlib.crc32(frame),offset,len(packed),1000,zlib.crc32(packed)])
    rows.sort(key=lambda row:row[0]);mh=bytearray(manifest[:32])
    struct.pack_into('<H',mh,8,len(rows));struct.pack_into('<I',mh,12,ms+24)
    new_manifest=bytes(mh)+b''.join(struct.pack('<IHHIIHHI',*row) for row in rows)
    blob=new_manifest+old_blob[ms:]+packed;used=bo+len(blob)
    geo=geometry(max(len(bank),choose_static_bytes(used,old_geo['norBytes'])),old_geo['norBytes'])
    identity_note=b'Companion original speaker restoration P146\0' if speaker else b'Companion original-style quiet attention P145\0' if attention else b'Companion original-style calm down glance P142\0'
    identity=sha(bytes.fromhex(profile['resourceId'])+identity_note+blob).upper()
    struct.pack_into('<I',root,8,generation);struct.pack_into('<II',root,20,len(blob),zlib.crc32(blob))
    struct.pack_into('<II',root,32,len(new_manifest),zlib.crc32(new_manifest));struct.pack_into('<I',root,40,(used+4095)&~4095)
    root[44:76]=bytes.fromhex(identity);struct.pack_into('<I',root,124,zlib.crc32(root[:124]))
    new_bank=bytearray(b'\xff'*geo['staticBytes']);new_bank[:bo]=bank[:bo]
    new_bank[bo:used]=blob;new_bank[geo['rootA']:geo['rootA']+128]=root
    assert new_bank[bo+ms+24:bo+bs+24]==old_blob[ms:]
    indexed={row[0]:row for row in rows}
    for before in old_rows:
        after=indexed[before[0]];assert before[:4]==after[:4] and before[5:]==after[5:]
        if before[2]:assert new_bank[after[4]:after[4]+after[5]]==bank[before[4]:before[4]+before[5]]
    out.mkdir(parents=True)
    for path in base.glob('*.h'):shutil.copyfile(path,out/path.name)
    ao=profile['externalUi']['extensionOffset']+24;external=bytes(new_bank[ao:used])
    header=(base/'companion_wba_external_ui.h').read_text()
    header=replace_number(header,'COMP_WBA_EXTERNAL_UI_OFFSET',ao);header=replace_number(header,'COMP_WBA_EXTERNAL_UI_BYTES',len(external))
    header,n=re.subn(r'(COMP_WBA_EXTERNAL_UI_CRC32 )0x[0-9A-Fa-f]+u',r'\g<1>0x%08Xu'%zlib.crc32(external),header);assert n==1
    (out/'companion_wba_external_ui.h').write_text(header,encoding='utf-8',newline='\n')
    contract=(base/'companion_wba_resource_contract.h').read_text();capability='COMPANION_WBA_AUDIO_ORNAMENTS_V1' if speaker else 'COMPANION_WBA_PET_ATTENTIVE_V8' if attention else 'COMPANION_WBA_PET_CALM_DOWN_V7'
    assert capability not in contract
    contract=replace_number(contract,'COMPANION_WBA_RESOURCE_GENERATION',generation)
    contract=replace_number(contract,'COMPANION_WBA_RESOURCE_STATE_COUNT',len(rows)).replace(profile['resourceId'],identity)
    contract=contract.replace('#include <stdint.h>','#include <stdint.h>\n#define '+capability+' 1')
    (out/'companion_wba_resource_contract.h').write_text(contract,encoding='utf-8',newline='\n')
    (out/'ui-partition.bin').write_bytes(new_bank)
    ext=copy.deepcopy(profile['externalUi']);ext.update(extensionOffset=ao,extensionBytes=len(external),headerSha256=sha((out/'companion_wba_external_ui.h').read_bytes()),generation=generation,newBankSha256=sha(new_bank))
    if 'addedOffset' in ext:ext['addedOffset']+=24
    result=dict(schema='companion.original-speaker-resource.v1' if speaker else 'companion.pet-attention-resource.v1' if attention else 'companion.pet-calm-down-resource.v1',generation=generation,baseGeneration=profile['generation'],state=state,frameSha256=sha(frame),addedFramePayloadBytes=len(packed),
        oldStateCount=count,newStateCount=len(rows),originalStatePixelsPreserved=True,originalAtlasAndPayloadBytesPreserved=True,
        oldGeometry=old_geo,newGeometry=geo,geometryChanged=old_geo!=geo,pairedAppBootGeometryRequired=True,ordinaryOldGeometryOtaAllowed=old_geo==geo,
        resourceArenaUsedBytes=used,arenaFreeBytes=geo['rootA']-used,imageSha256=sha(new_bank),fullFirmwareBuilt=False,installed=False,physicalQualified=False,testsRun=False)
    profile.update(generation=generation,resourceId=identity,stateCount=len(rows),uiPartitionBytes=len(new_bank),uiPartitionSha256=sha(new_bank).upper(),resourceArenaUsedBytes=used,
        resourceBudgetBytes=len(new_bank),generationBytes=len(blob),flashGeometry=geo,externalUi=ext,recordingRegionPreserved=old_geo==geo,dynamicRegionIncluded=False,hardwareAcceptance='NOT_RUN',fullChainAcceptance='NOT_RUN',result='RESOURCE_CANDIDATE_BUILT')
    profile['originalSpeaker' if speaker else 'petAttention' if attention else 'petCalmDown']=result
    inputs=[Path(__file__),frame_path,art/'review.json']
    inputs+=([art/'original-speaker-source-frame.bin'] if speaker else [art/'attentive-r2-prompt.json',art/'conversion-r2.json'] if attention else [art/'calm-down-r5-prompt.json'])
    for path in inputs:
        profile.setdefault('sourceSha256',{})[path.relative_to(ROOT).as_posix()]=sha(path.read_bytes()).upper()
    for path in out.glob('*.h'):profile.setdefault('sourceSha256',{})[str(path)]=sha(path.read_bytes()).upper()
    dump(out/'profile.json',profile);dump(out/('original-speaker.json' if speaker else 'pet-attention.json' if attention else 'pet-calm-down.json'),result)
    return result

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for key in ('base','art','output'):p.add_argument('--'+key,type=Path,required=True)
    p.add_argument('--generation',type=int,required=True);choice=p.add_mutually_exclusive_group()
    choice.add_argument('--attention',action='store_true');choice.add_argument('--speaker',action='store_true');a=p.parse_args()
    j=build(a.base.resolve(),a.art.resolve(),a.output.resolve(),a.generation,a.attention,a.speaker)
    print(json.dumps({k:j[k] for k in ('generation','addedFramePayloadBytes','newGeometry','imageSha256','installed')}))
