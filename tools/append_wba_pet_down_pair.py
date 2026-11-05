"""Append a reviewed near/far whole-face gaze pair without moving media regions."""
from pathlib import Path
import argparse,copy,hashlib,json,re,shutil,struct,sys,zlib
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools/faraday_upper_art'))
from build_ui_asset_generation import encode_packbits,fnv1a32
from wba_resource_geometry import geometry
from append_wba_pet_polish import replace_number
sha=lambda b:hashlib.sha256(b).hexdigest()
def dump(p,j):p.write_text(json.dumps(j,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def decode(data):
 out=bytearray();i=0
 while i<len(data):
  tag=data[i];i+=1
  if tag<128:
   n=tag+1;assert i+n<=len(data);out.extend(data[i:i+n]);i+=n
  elif tag>128:
   assert i<len(data);out.extend(bytes([data[i]])*(257-tag));i+=1
  assert len(out)<=5000
 return bytes(out)
def build(base,art,out,generation):
 disposition=art/'current-disposition.json'
 if disposition.exists() and not json.loads(disposition.read_bytes()).get('allowResourceImport',False):
  raise RuntimeError('P177 art withdrawn: see current-disposition.json; do not integrate or install FW461/UI81')
 assert not out.exists()
 profile=json.loads((base/'profile.json').read_bytes());bank=(base/'ui-partition.bin').read_bytes()
 assert generation>profile['generation'] and sha(bank).upper()==profile['uiPartitionSha256'].upper()
 geo=geometry(len(bank),profile['flashGeometry']['norBytes']);assert geo==profile['flashGeometry']
 review=json.loads((art/'review.json').read_bytes());assert review['agentStaticSelected'] and not review['physicalAccepted']
 choices=review['selectedStates'];assert set(choices)=={'pet_gaze_calm_down_near','pet_gaze_calm_down_far'}
 root=bytearray(bank[geo['rootA']:geo['rootA']+128])
 assert root[:4]==b'CUIR' and zlib.crc32(root[:124])==struct.unpack_from('<I',root,124)[0]
 bo,bs=struct.unpack_from('<II',root,16);mo,ms,mc=struct.unpack_from('<III',root,28)
 old_blob=bank[bo:bo+bs];manifest=old_blob[:ms]
 assert mo==0 and manifest[:4]==b'CUIM' and zlib.crc32(manifest)==mc and zlib.crc32(old_blob)==struct.unpack_from('<I',root,24)[0]
 count,row_bytes=struct.unpack_from('<HH',manifest,8);assert row_bytes==24 and ms==32+count*24 and count==profile['stateCount']
 old_rows=[list(struct.unpack_from('<IHHIIHHI',manifest,32+i*24)) for i in range(count)]
 rows=copy.deepcopy(old_rows);growth=48
 for row in rows:
  if row[2]:
   assert bo+ms<=row[4] and row[4]+row[5]<=bo+bs
   assert zlib.crc32(bank[row[4]:row[4]+row[5]])==row[7]
   row[4]+=growth
 frames={};tail=bytearray();offset=bo+bs+growth
 for name,choice in choices.items():
  frame=(art/choice['frame']).read_bytes();assert len(frame)==5000 and sha(frame)==choice['frameSha256']
  assert frame[:400]==b'\xff'*400 and frame[-650:]==b'\xff'*650
  hashed=fnv1a32(name);assert hashed not in {r[0] for r in rows}
  packed=encode_packbits(frame);assert decode(packed)==frame
  rows.append([hashed,65535,2,zlib.crc32(frame),offset,len(packed),1000,zlib.crc32(packed)])
  frames[name]=dict(frameSha256=sha(frame),offset=offset,packedBytes=len(packed))
  tail.extend(packed);offset+=len(packed)
 rows.sort(key=lambda r:r[0]);assert all(a[0]<b[0] for a,b in zip(rows,rows[1:]))
 mh=bytearray(manifest[:32]);struct.pack_into('<H',mh,8,len(rows));struct.pack_into('<I',mh,12,ms+growth)
 new_manifest=bytes(mh)+b''.join(struct.pack('<IHHIIHHI',*r) for r in rows)
 blob=new_manifest+old_blob[ms:]+tail;used=bo+len(blob)
 assert used<geo['rootA'],'Do not expand resource/recording geometry for this pair'
 identity=sha(bytes.fromhex(profile['resourceId'])+b'Companion P177 calm down pair\0'+blob).upper()
 struct.pack_into('<I',root,8,generation);struct.pack_into('<II',root,20,len(blob),zlib.crc32(blob))
 struct.pack_into('<II',root,32,len(new_manifest),zlib.crc32(new_manifest));struct.pack_into('<I',root,40,(used+4095)&~4095)
 root[44:76]=bytes.fromhex(identity);struct.pack_into('<I',root,124,zlib.crc32(root[:124]))
 new=bytearray(b'\xff'*len(bank));new[:bo]=bank[:bo];new[bo:used]=blob;new[geo['rootA']:geo['rootA']+128]=root
 assert new[bo+ms+growth:bo+bs+growth]==old_blob[ms:]
 indexed={r[0]:r for r in rows}
 for before in old_rows:
  after=indexed[before[0]];assert before[:4]==after[:4] and before[5:]==after[5:]
  if before[2]:assert new[after[4]:after[4]+after[5]]==bank[before[4]:before[4]+before[5]]
 for name,choice in choices.items():
  r=indexed[fnv1a32(name)];assert decode(new[r[4]:r[4]+r[5]])==(art/choice['frame']).read_bytes()
 out.mkdir(parents=True)
 for p in base.glob('*.h'):shutil.copy2(p,out/p.name)
 ao=profile['externalUi']['extensionOffset']+growth;external=bytes(new[ao:used])
 h=(base/'companion_wba_external_ui.h').read_text()
 h=replace_number(h,'COMP_WBA_EXTERNAL_UI_OFFSET',ao);h=replace_number(h,'COMP_WBA_EXTERNAL_UI_BYTES',len(external))
 h,n=re.subn(r'(COMP_WBA_EXTERNAL_UI_CRC32 )0x[0-9A-Fa-f]+u',r'\g<1>0x%08Xu'%zlib.crc32(external),h);assert n==1
 (out/'companion_wba_external_ui.h').write_text(h,encoding='utf-8',newline='\n')
 h=(base/'companion_wba_resource_contract.h').read_text();cap='COMPANION_WBA_PET_CALM_DOWN_PAIR_V9';assert cap not in h
 h=replace_number(h,'COMPANION_WBA_RESOURCE_GENERATION',generation)
 h=replace_number(h,'COMPANION_WBA_RESOURCE_STATE_COUNT',len(rows)).replace(profile['resourceId'],identity)
 h=h.replace('#include <stdint.h>','#include <stdint.h>\n#define '+cap+' 1')
 (out/'companion_wba_resource_contract.h').write_text(h,encoding='utf-8',newline='\n');(out/'ui-partition.bin').write_bytes(new)
 ext=copy.deepcopy(profile['externalUi']);ext.update(extensionOffset=ao,extensionBytes=len(external),headerSha256=sha((out/'companion_wba_external_ui.h').read_bytes()),generation=generation,newBankSha256=sha(new))
 if 'addedOffset' in ext:ext['addedOffset']+=growth
 result=dict(schema='companion.pet-down-pair-resource.v1',generation=generation,baseGeneration=profile['generation'],states=frames,addedBytes=growth+len(tail),
  oldStateCount=count,newStateCount=len(rows),allOldStateDescriptorsAndPayloadsPreserved=True,oldGeometry=geo,newGeometry=geo,geometryChanged=False,
  staticBytes=len(new),arenaUsedBytes=used,arenaFreeBytes=geo['rootA']-used,imageSha256=sha(new),physicalQualified=False,installed=False)
 profile.update(generation=generation,resourceId=identity,stateCount=len(rows),uiPartitionSha256=sha(new).upper(),resourceArenaUsedBytes=used,
  generationBytes=len(blob),externalUi=ext,recordingRegionPreserved=True,dynamicRegionIncluded=False,hardwareAcceptance='NOT_RUN',fullChainAcceptance='NOT_RUN',result='RESOURCE_CANDIDATE_BUILT',petDownPair=result)
 inputs=[Path(__file__),art/'review.json']
 for choice in choices.values():inputs.extend([art/choice['frame'],art/choice['conversion'],art/choice['prompt']])
 for p in inputs:profile.setdefault('sourceSha256',{})[p.relative_to(ROOT).as_posix()]=sha(p.read_bytes()).upper()
 for p in out.glob('*.h'):profile['sourceSha256'][str(p)]=sha(p.read_bytes()).upper()
 dump(out/'profile.json',profile);dump(out/'pet-down-pair.json',result)
 return result
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__)
 for k in ('base','art','output'):p.add_argument('--'+k,type=Path,required=True)
 p.add_argument('--generation',type=int,required=True);a=p.parse_args()
 print(json.dumps(build(a.base.resolve(),a.art.resolve(),a.output.resolve(),a.generation)))
