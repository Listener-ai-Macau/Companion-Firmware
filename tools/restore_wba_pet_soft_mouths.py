"""Restore the same emotion's existing mouth pixels in authored soft poses.

This restores existing P102 artwork, not new facial drawing. The prior P132
generated brow/eye acting remains. No payload relocation or geometry change.
"""
from pathlib import Path
import argparse,copy,hashlib,json,re,shutil,struct,sys,zlib
from PIL import Image
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools/faraday_upper_art'))
from build_ui_asset_generation import encode_packbits,fnv1a32
from verify_ui_asset_generation import decode_packbits
from wba_resource_geometry import geometry
from append_wba_pet_polish import replace_number
sha=lambda b:hashlib.sha256(b).hexdigest()
def dump(p,v):p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def build(base,out,generation):
 assert not out.exists()
 p=json.loads((base/'profile.json').read_bytes());bank=(base/'ui-partition.bin').read_bytes()
 assert generation>p['generation'] and sha(bank).upper()==p['uiPartitionSha256'].upper()
 geo=geometry(len(bank),p['flashGeometry']['norBytes']);assert geo==p['flashGeometry']
 root=bytearray(bank[geo['rootA']:geo['rootA']+128]);assert root[:4]==b'CUIR'
 assert zlib.crc32(root[:124])==struct.unpack_from('<I',root,124)[0]
 bo,bs=struct.unpack_from('<II',root,16);mo,ms,mc=struct.unpack_from('<III',root,28)
 assert mo==0 and zlib.crc32(bank[bo:bo+bs])==struct.unpack_from('<I',root,24)[0]
 assert zlib.crc32(bank[bo:bo+ms])==mc
 count,rowbytes=struct.unpack_from('<HH',bank,bo+8);assert rowbytes==24 and count==p['stateCount'] and ms==32+count*24
 before=[list(struct.unpack_from('<IHHIIHHI',bank,bo+32+i*24)) for i in range(count)]
 rows=copy.deepcopy(before);indices={r[0]:i for i,r in enumerate(rows)};new=bytearray(bank)
 out.mkdir(parents=True);art=out/'art';art.mkdir()
 changes=[];reviewed=[];frames={};box=(82,144,118,163)
 def read(name):
  r=before[indices[fnv1a32(name)]];assert r[2]==2
  packed=bank[r[4]:r[4]+r[5]];assert zlib.crc32(packed)==r[7]
  frame=decode_packbits(packed);assert zlib.crc32(frame)==r[3]
  return r,frame
 for emotion in ('dejected','protest','nervous','proud'):
  for direction in ('','_left','_right','_up','_down'):
   peak='pet_emotion_'+emotion+direction;name=peak+'_soft'
   prior,old=read(name);peak_row,mother=read(peak);restored=bytearray(old);changed=0
   # Copy a fixed cutout of the existing same-emotion original raster. No
   # generated curve, cross-emotion mouth substitution or runtime paint hook.
   for y in range(box[1],box[3]):
    for x in range(box[0],box[2]):
     i=y*25+x//8;mask=128>>(x%8)
     changed+=bool((old[i]^mother[i])&mask)
     restored[i]=(restored[i]&~mask)|(mother[i]&mask)
   for y in range(200):
    for x in range(200):
     i=y*25+x//8;mask=128>>(x%8)
     if box[0]<=x<box[2] and box[1]<=y<box[3]:assert not((restored[i]^mother[i])&mask)
     else:assert not((restored[i]^old[i])&mask)
   frames[name]=(old,mother,bytes(restored))
   reviewed.append(dict(state=name,peak=peak,pixelDifferences=changed,oldFrameSha256=sha(old),peakFrameSha256=sha(mother),newFrameSha256=sha(restored)))
   if not changed:continue
   packed=encode_packbits(restored);assert decode_packbits(packed)==restored
   assert len(packed)<=prior[5],'No resource growth or relocation in this restoration'
   new[prior[4]:prior[4]+len(packed)]=packed
   row=rows[indices[prior[0]]];row[3]=zlib.crc32(restored);row[5]=len(packed);row[7]=zlib.crc32(packed)
   changes.append(dict(state=name,oldFrameSha256=sha(old),newFrameSha256=sha(restored),restoredPixels=changed,offset=prior[4],oldPackedBytes=prior[5],newPackedBytes=len(packed)))
   (art/(name+'-frame.bin')).write_bytes(restored)
   Image.frombytes('1',(200,200),restored).save(art/(name+'-native-200.png'))
 assert len(changes)==14 and sum(x['restoredPixels'] for x in changes)==63
 manifest=bank[bo:bo+32]+b''.join(struct.pack('<IHHIIHHI',*r) for r in rows)
 new[bo:bo+ms]=manifest
 identity=sha(bytes.fromhex(p['resourceId'])+b'P179 same-emotion original mouth restoration\0'+new[bo:bo+bs]).upper()
 struct.pack_into('<I',root,8,generation);struct.pack_into('<I',root,24,zlib.crc32(new[bo:bo+bs]))
 struct.pack_into('<I',root,36,zlib.crc32(manifest));root[44:76]=bytes.fromhex(identity)
 struct.pack_into('<I',root,124,zlib.crc32(root[:124]));new[geo['rootA']:geo['rootA']+128]=root
 modified={fnv1a32(x['state']) for x in changes}
 for old,row in zip(before,rows):
  if row[0] not in modified:
   assert old==row
   if old[2]:assert new[old[4]:old[4]+old[5]]==bank[old[4]:old[4]+old[5]]
  else:
   assert old[:3]==row[:3] and old[4]==row[4] and old[6]==row[6]
   name=next(x['state'] for x in changes if fnv1a32(x['state'])==row[0])
   assert decode_packbits(new[row[4]:row[4]+row[5]])==frames[name][2]
 assert sum(a!=b for a,b in zip(before,rows))==14
 for path in base.glob('*.h'):shutil.copy2(path,out/path.name)
 ao=p['externalUi']['extensionOffset'];end=p['resourceArenaUsedBytes'];external=new[ao:end]
 header=(base/'companion_wba_external_ui.h').read_text()
 header,n=re.subn(r'(COMP_WBA_EXTERNAL_UI_CRC32 )0x[0-9A-Fa-f]+u',r'\g<1>0x%08Xu'%zlib.crc32(external),header);assert n==1
 (out/'companion_wba_external_ui.h').write_text(header,encoding='utf-8',newline='\n')
 contract=(base/'companion_wba_resource_contract.h').read_text()
 contract=replace_number(contract,'COMPANION_WBA_RESOURCE_GENERATION',generation).replace(p['resourceId'],identity)
 (out/'companion_wba_resource_contract.h').write_text(contract,encoding='utf-8',newline='\n')
 (out/'ui-partition.bin').write_bytes(new)
 # Whole native faces show the accepted existing expression through the same
 # soft/peak/soft phrase. This static strip is not panel timing qualification.
 old_sheet=Image.new('1',(600,800),255);fixed_sheet=old_sheet.copy()
 for i,emotion in enumerate(('dejected','protest','nervous','proud')):
  old,mother,fixed=frames['pet_emotion_'+emotion+'_soft']
  for col,data in enumerate((old,mother,old)):old_sheet.paste(Image.frombytes('1',(200,200),data),(col*200,i*200))
  for col,data in enumerate((fixed,mother,fixed)):fixed_sheet.paste(Image.frombytes('1',(200,200),data),(col*200,i*200))
 old_sheet.save(art/'before-soft-peak-soft.png');fixed_sheet.save(art/'restored-soft-peak-soft.png')
 result=dict(schema='companion.pet-soft-mouth-restoration.p179.v1',generation=generation,baseGeneration=p['generation'],
  sourceOriginalArt='P102 existing same-emotion/direction peaks',sourceSoftArt='P132 existing image_gen whole faces',
  operation='Restore existing authored mouth pixels only; no new facial design or procedural curves',mouthRegion=list(box),
  reviewedStates=reviewed,changedStates=changes,restoredPixels=63,unchangedStateCount=count-14,stateCount=count,
  allOtherDescriptorsAndPayloadsUnchanged=True,nonMouthPixelsUnchanged=True,oldGeometry=geo,newGeometry=geo,
  geometryChanged=False,resourceGrowthBytes=0,payloadOffsetsUnchanged=True,p178DownPosePreserved=True,
  imageSha256=sha(new),agentStaticReviewed=False,ownerAccepted=False,fullFirmwareBuilt=False,installed=False,physicalQualified=False,
  testsAdded=False,testsRun=False,hardwareOperations=0,pairedAppBootRequired=True)
 p.update(generation=generation,resourceId=identity,uiPartitionSha256=sha(new).upper(),softMouthRestoration=result,
  result='RESOURCE_CANDIDATE_ONLY_NOT_INSTALLABLE',hardwareAcceptance='NOT_RUN',fullChainAcceptance='NOT_RUN')
 p['externalUi'].update(generation=generation,headerSha256=sha((out/'companion_wba_external_ui.h').read_bytes()),newBankSha256=sha(new))
 p.setdefault('sourceSha256',{})[Path(__file__).relative_to(ROOT).as_posix()]=sha(Path(__file__).read_bytes()).upper()
 for path in out.glob('*.h'):p['sourceSha256'][str(path)]=sha(path.read_bytes()).upper()
 dump(out/'profile.json',p);dump(out/'soft-mouth-restoration.json',result)
 return result
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__)
 for key in ('base','output'):p.add_argument('--'+key,type=Path,required=True)
 p.add_argument('--generation',type=int,required=True);a=p.parse_args()
 r=build(a.base.resolve(),a.output.resolve(),a.generation)
 print(json.dumps({k:r[k] for k in ('generation','restoredPixels','unchangedStateCount','resourceGrowthBytes','imageSha256','installed')}))
