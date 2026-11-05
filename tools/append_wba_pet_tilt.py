"""Add original whole-face posture poses in retired UI metadata space.

The reviewed imagegen reference guides posture only. Integer lifting rotates
the current authored whole face without drawing features or losing ink. Keep
every original state/payload and the CEMP; move the customer atlas byte-exactly
inside the known retired metadata gap. Static/dynamic boundaries stay fixed.
"""
from pathlib import Path
import argparse,copy,hashlib,json,math,re,shutil,struct,zlib
from PIL import Image
from build_wba_pet_soft_smile import Bank
from build_wba_product_resources import fnv
from build_emote_asset_pack import encode_packbits,decode_packbits
from append_wba_pet_polish import replace_number

FAMILIES=('calm','curious','delighted','warm','playful','sleepy','bashful','thoughtful','focused','alert')
sha=lambda b:hashlib.sha256(b).hexdigest()
dump=lambda p,x:Path(p).write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
def nearest(v):return math.floor(v+.5) if v>=0 else -math.floor(-v+.5)
def turn(point,sign,angle=7):
 x,y=point;alpha=sign*math.tan(math.radians(angle)/2);beta=sign*math.sin(math.radians(angle))
 x-=nearest(alpha*(y-124));y+=nearest(beta*(x-100));x-=nearest(alpha*(y-124))
 return x,y
def build(base,art,output):
 base,art,output=(Path(p).resolve() for p in (base,art,output));assert not output.exists()
 review=json.loads((art/'art-intent.json').read_bytes())
 assert review['native200ActuallyViewed'] and review['status']=='REFERENCE_DIRECTION_USEFUL_NOT_EXACT_PIXEL_RESOURCE'
 bank=Bank(base);p=copy.deepcopy(bank.profile);assert p['generation']==84 and bank.count==6131
 data=bytearray(bank.data);old_rows=[row for _,row in bank.entries.values()];rows=list(old_rows)
 header=(base/'companion_wba_customer_ui.h').read_text(encoding='utf8')
 val=lambda n:int(re.search(r'#define '+n+r' (\d+)u',header)[1])
 old_atlas=val('COMP_CUSTOMER_ATLAS_OFFSET');atlas_n=val('COMP_CUSTOMER_ATLAS_BYTES')
 assert bank.blob+32+bank.count*24==old_atlas
 # Same retired metadata interval used for the accepted P210 mouth import.
 free_start=p['softSmile']['payloadRange'][1]
 gap_end=min(row[4] for row in rows if row[2] and row[5] and row[4]>=free_start)
 atlas=(free_start+15)&~15;cursor=(atlas+atlas_n+15)&~15
 assert atlas>=old_atlas+atlas_n and cursor<gap_end<p['externalUi']['extensionOffset']
 for row in rows:
  if row[2] and row[5]:assert row[4]+row[5]<=atlas or row[4]>=gap_end
 data[atlas:atlas+atlas_n]=bank.data[old_atlas:old_atlas+atlas_n]
 output.mkdir(parents=True);frames=output/'posture-art';frames.mkdir()
 added=[];used_hashes=set(bank.entries)
 for family in FAMILIES:
  mother='pointer_follow_'+family+'_gx4_gy4';source=bank.frame(bank.entries[fnv(mother)][1])
  im=Image.frombytes('1',(200,200),source)
  points={(x,y) for y in range(66,174) for x in range(200) if not im.getpixel((x,y))}
  assert points and all(12<=x<=187 for x,y in points)
  for direction,sign in [('left',-1),('right',1)]:
   transformed={turn(q,sign) for q in points}
   assert len(transformed)==len(points) and {turn(q,-sign) for q in transformed}==points
   assert all(12<=x<=187 and 66<=y<=173 for x,y in transformed),(family,direction,min(y for x,y in transformed),max(y for x,y in transformed))
   image=im.copy()
   for q in points:image.putpixel(q,1)
   for q in transformed:image.putpixel(q,0)
   raw=image.tobytes();assert raw[:66*25]==source[:66*25] and raw[174*25:]==source[174*25:]
   packed=encode_packbits(raw);assert decode_packbits(packed,5000)==raw
   assert cursor+len(packed)<=gap_end,'No safe space; never move the recording boundary'
   name='pet_motion_'+family+'_'+direction+'_hold';h=fnv(name);assert h not in used_hashes;used_hashes.add(h)
   data[cursor:cursor+len(packed)]=packed
   rows.append((h,65535,2,zlib.crc32(raw),cursor,len(packed),480,zlib.crc32(packed)))
   added.append({'state':name,'mother':mother,'motherSha256':sha(source),'frameSha256':sha(raw),'packedBytes':len(packed),'offset':cursor,'faceInkPixels':len(points),'inverseLiftingExact':True,'angleDegrees':7})
   (frames/(name+'.bin')).write_bytes(raw);image.save(frames/(name+'.png'));cursor+=len(packed)
  Image.frombytes('1',(200,200),source).save(frames/(family+'-mother.png'))
 rows.sort();manifest=bytearray(bank.data[bank.blob:bank.blob+32]);struct.pack_into('<H',manifest,8,len(rows));struct.pack_into('<I',manifest,12,32+len(rows)*24)
 manifest.extend(b''.join(struct.pack('<IHHIIHHI',*row) for row in rows))
 assert bank.blob+len(manifest)<old_atlas+atlas_n and bank.blob+len(manifest)<=atlas
 data[bank.blob:bank.blob+len(manifest)]=manifest
 assert bytes(data[atlas:atlas+atlas_n])==bank.data[old_atlas:old_atlas+atlas_n]
 indexed={row[0]:row for row in rows}
 for before in old_rows:
  after=indexed[before[0]];assert before==after
  if before[2] and before[5]:assert data[before[4]:before[4]+before[5]]==bank.data[before[4]:before[4]+before[5]]
 assert data[:p['cempBytes']]==bank.data[:p['cempBytes']]
 assert data[p['externalUi']['extensionOffset']:p['resourceArenaUsedBytes']]==bank.data[p['externalUi']['extensionOffset']:p['resourceArenaUsedBytes']]
 root=bytearray(bank.root);identity=hashlib.sha256(b'Companion original whole-face posture P229\0'+data[bank.blob:bank.blob+bank.blob_n]).hexdigest().upper()
 struct.pack_into('<I',root,24,zlib.crc32(data[bank.blob:bank.blob+bank.blob_n]));struct.pack_into('<II',root,32,len(manifest),zlib.crc32(manifest));root[44:76]=bytes.fromhex(identity);struct.pack_into('<I',root,124,zlib.crc32(root[:124]));data[bank.geo['rootA']:bank.geo['rootA']+128]=root
 for path in base.glob('*.h'):shutil.copy2(path,output/path.name)
 customer=replace_number(header,'COMP_CUSTOMER_ATLAS_OFFSET',atlas);(output/'companion_wba_customer_ui.h').write_text(customer,encoding='utf8',newline='\n')
 contract=(base/'companion_wba_resource_contract.h').read_text(encoding='utf8');contract=replace_number(contract,'COMPANION_WBA_RESOURCE_STATE_COUNT',len(rows)).replace(p['resourceId'],identity);contract=contract.replace('#include <stdint.h>','#include <stdint.h>\n#define COMPANION_WBA_PET_TILT_POSES_V1 1')
 (output/'companion_wba_resource_contract.h').write_text(contract,encoding='utf8',newline='\n');(output/'ui-partition.bin').write_bytes(data)
 result={'schema':'companion.original-whole-face-posture.p229.v1','baseImageSha256':sha(bank.data),'imageSha256':sha(data),'originalStateCount':bank.count,'stateCount':len(rows),'added':added,'originalDescriptorsAndPayloadsExact':True,'cempByteIdentical':True,'atlasBytesExact':True,'oldAtlasOffset':old_atlas,'atlasOffset':atlas,'atlasBytes':atlas_n,'usedRetiredGap':[atlas,cursor],'retiredGapEnd':gap_end,'staticDynamicBoundaryChanged':False,'runtimeBufferAdded':False,'sourceReview':str(art/'art-intent.json'),'generatedReferenceImportedAsPixels':False,'transformation':'Three reversible integer lifting shears about100,124; original ink bijective, no curve drawing or interpolation.','installed':False,'physicalQualified':False}
 p.update(resourceId=identity,uiPartitionSha256=sha(data).upper(),stateCount=len(rows),profileRevision='pet-posture-p229-ui84r18',result='RESOURCE_CANDIDATE_NOT_INSTALLED',petPosture=result)
 p['sourceSha256'][Path(__file__).resolve().relative_to(Path(__file__).resolve().parents[1]).as_posix()]=sha(Path(__file__).read_bytes()).upper();p['sourceSha256'][str(art/'art-intent.json')]=sha((art/'art-intent.json').read_bytes()).upper()
 for path in output.glob('*.h'):p['sourceSha256'][str(path)]=sha(path.read_bytes()).upper()
 dump(output/'profile.json',p);dump(output/'posture.json',result)
 verify=Bank(output);assert verify.geo==bank.geo
 for h,(_,row) in bank.entries.items():assert verify.frame(verify.entries[h][1])==bank.frame(row)
 for entry in added:assert sha(verify.frame(verify.entries[fnv(entry['state'])][1]))==entry['frameSha256']
 return result
if __name__=='__main__':
 parser=argparse.ArgumentParser(description=__doc__)
 for name in ('base','art','output'):parser.add_argument('--'+name,type=Path,required=True)
 a=parser.parse_args();x=build(a.base,a.art,a.output);print(json.dumps({k:x[k] for k in ('stateCount','usedRetiredGap','retiredGapEnd','imageSha256','staticDynamicBoundaryChanged')}))
