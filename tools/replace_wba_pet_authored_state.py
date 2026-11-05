"""Replace one reviewed later-authored eye pose, preserving the original bank.

Only the indexed state changes. Its prior payload remains as historical bytes;
new payload goes in existing free arena space. No geometry expansion is allowed.
The output is a resource candidate, requiring a matched App/Boot signed package.
"""
from pathlib import Path
import argparse,copy,hashlib,json,re,shutil,struct,sys,zlib
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools/faraday_upper_art'))
from build_ui_asset_generation import encode_packbits,fnv1a32
from verify_ui_asset_generation import decode_packbits
from wba_resource_geometry import geometry
from append_wba_pet_polish import replace_number
sha=lambda b:hashlib.sha256(b).hexdigest()
def dump(p,v):p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def build(base,art,out,generation):
 assert not out.exists(),'Fresh candidate directory required'
 review=json.loads((art/'review.json').read_bytes())
 assert review['schema']=='companion.whole-eye-repair.p178.v1'
 assert review['allowResourceImport'] and review['agentStaticSelected'] and not review['physicalAccepted']
 disposition=art/'current-disposition.json'
 if disposition.exists():assert json.loads(disposition.read_bytes()).get('allowResourceImport',False),'Art withdrawn'
 state=review['replaceState'];assert state=='pet_gaze_calm_down'
 frame=(art/review['selectedFrame']).read_bytes();assert len(frame)==5000 and sha(frame)==review['selectedFrameSha256']
 assert frame[:400]==b'\xff'*400 and frame[-650:]==b'\xff'*650
 profile=json.loads((base/'profile.json').read_bytes());bank=(base/'ui-partition.bin').read_bytes()
 assert generation>profile['generation'] and sha(bank).upper()==profile['uiPartitionSha256'].upper()
 geo=geometry(len(bank),profile['flashGeometry']['norBytes']);assert geo==profile['flashGeometry']
 root=bytearray(bank[geo['rootA']:geo['rootA']+128]);assert root[:4]==b'CUIR'
 assert zlib.crc32(root[:124])==struct.unpack_from('<I',root,124)[0]
 bo,bs=struct.unpack_from('<II',root,16);mo,ms,mc=struct.unpack_from('<III',root,28)
 old_blob=bank[bo:bo+bs];manifest=old_blob[:ms]
 assert mo==0 and manifest[:4]==b'CUIM' and zlib.crc32(manifest)==mc
 assert zlib.crc32(old_blob)==struct.unpack_from('<I',root,24)[0]
 count,row_bytes=struct.unpack_from('<HH',manifest,8);assert row_bytes==24 and ms==32+count*24 and count==profile['stateCount']
 before=[list(struct.unpack_from('<IHHIIHHI',manifest,32+i*24)) for i in range(count)]
 assert all(a[0]<b[0] for a,b in zip(before,before[1:]))
 rows=copy.deepcopy(before);indices=[i for i,r in enumerate(rows) if r[0]==fnv1a32(state)]
 assert len(indices)==1;index=indices[0];prior=before[index]
 assert prior[1]==65535 and prior[2]==2,'Only the later whole-frame override may be replaced'
 old_frame=decode_packbits(bank[prior[4]:prior[4]+prior[5]])
 assert sha(old_frame)==review['replacesFrameSha256'] and zlib.crc32(old_frame)==prior[3]
 for row in before:
  if row[2]:
   assert bo+ms<=row[4] and row[4]+row[5]<=bo+bs
   assert zlib.crc32(bank[row[4]:row[4]+row[5]])==row[7]
 packed=encode_packbits(frame);assert decode_packbits(packed)==frame
 offset=bo+bs;used=offset+len(packed)
 assert used<geo['rootA'],'No expansion of static/dynamic/recording geometry is allowed'
 rows[index]=[prior[0],prior[1],prior[2],zlib.crc32(frame),offset,len(packed),prior[6],zlib.crc32(packed)]
 new_manifest=manifest[:32]+b''.join(struct.pack('<IHHIIHHI',*r) for r in rows)
 blob=new_manifest+old_blob[ms:]+packed
 identity=sha(bytes.fromhex(profile['resourceId'])+b'Companion P178 complete-eye original-mouth repair\0'+blob).upper()
 struct.pack_into('<I',root,8,generation);struct.pack_into('<II',root,20,len(blob),zlib.crc32(blob))
 struct.pack_into('<II',root,32,len(new_manifest),zlib.crc32(new_manifest));struct.pack_into('<I',root,40,(used+4095)&~4095)
 root[44:76]=bytes.fromhex(identity);struct.pack_into('<I',root,124,zlib.crc32(root[:124]))
 new=bytearray(bank);new[bo:used]=blob;new[geo['rootA']:geo['rootA']+128]=root
 assert new[bo+ms:bo+bs]==bank[bo+ms:bo+bs]
 assert sum(a!=b for a,b in zip(before,rows))==1
 assert all(a==b for i,(a,b) in enumerate(zip(before,rows)) if i!=index)
 assert decode_packbits(new[offset:used])==frame
 assert zlib.crc32(new[bo:bo+ms])==struct.unpack_from('<I',root,36)[0]
 out.mkdir(parents=True)
 for p in base.glob('*.h'):shutil.copy2(p,out/p.name)
 ao=profile['externalUi']['extensionOffset'];external=bytes(new[ao:used])
 assert len(external)<65536,'Existing 16bit external UI reference format is unchanged'
 header=(base/'companion_wba_external_ui.h').read_text()
 header=replace_number(header,'COMP_WBA_EXTERNAL_UI_BYTES',len(external))
 header,n=re.subn(r'(COMP_WBA_EXTERNAL_UI_CRC32 )0x[0-9A-Fa-f]+u',r'\g<1>0x%08Xu'%zlib.crc32(external),header);assert n==1
 (out/'companion_wba_external_ui.h').write_text(header,encoding='utf-8',newline='\n')
 contract=(base/'companion_wba_resource_contract.h').read_text()
 assert 'COMPANION_WBA_PET_CALM_DOWN_V7' in contract and 'COMPANION_WBA_PET_CALM_DOWN_PAIR_V9' not in contract
 contract=replace_number(contract,'COMPANION_WBA_RESOURCE_GENERATION',generation).replace(profile['resourceId'],identity)
 (out/'companion_wba_resource_contract.h').write_text(contract,encoding='utf-8',newline='\n')
 (out/'ui-partition.bin').write_bytes(new)
 result=dict(schema='companion.pet-authored-state-replacement.v1',generation=generation,baseGeneration=profile['generation'],state=state,
  frameSha256=sha(frame),replacesFrameSha256=sha(old_frame),addedBytes=len(packed),priorPayloadBytesRetained=True,
  stateCount=count,unchangedStateCount=count-1,allOtherDescriptorsAndPayloadsUnchanged=True,
  oldGeometry=geo,newGeometry=geo,geometryChanged=False,arenaFreeBytes=geo['rootA']-used,imageSha256=sha(new),
  newAnimationSteps=False,newResourceStateNames=False,runtimeCodeChanged=False,fullFirmwareBuilt=False,installed=False,physicalAccepted=False,
  pairedAppBootResourceIdentityRequired=True,resourceOnlyInstallationAllowed=False)
 ext=copy.deepcopy(profile['externalUi']);ext.update(generation=generation,extensionBytes=len(external),
  headerSha256=sha((out/'companion_wba_external_ui.h').read_bytes()),newBankSha256=sha(new),
  originalStatePixelsUnchanged=False,allOtherStatePixelsUnchanged=True)
 profile['petCalmDownPreviousCandidate']=profile.get('petCalmDown')
 profile.update(generation=generation,resourceId=identity,uiPartitionSha256=sha(new).upper(),resourceArenaUsedBytes=used,
  generationBytes=len(blob),externalUi=ext,petCalmDown=result,hardwareAcceptance='NOT_RUN',fullChainAcceptance='NOT_RUN',result='RESOURCE_CANDIDATE_ONLY_NOT_INSTALLABLE')
 for p in [Path(__file__),art/'review.json',art/review['selectedFrame'],art/'composition-r2.json',art/'tool-prompt-r2.txt']:
  profile.setdefault('sourceSha256',{})[p.relative_to(ROOT).as_posix()]=sha(p.read_bytes()).upper()
 for p in out.glob('*.h'):profile['sourceSha256'][str(p)]=sha(p.read_bytes()).upper()
 dump(out/'profile.json',profile);dump(out/'pet-authored-state-replacement.json',result)
 return result
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__)
 for key in ('base','art','output'):p.add_argument('--'+key,type=Path,required=True)
 p.add_argument('--generation',type=int,required=True);a=p.parse_args()
 print(json.dumps(build(a.base.resolve(),a.art.resolve(),a.output.resolve(),a.generation)))
