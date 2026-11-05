#!/usr/bin/env python3
"""Append existing pet/setting rasters to an exact external bank, losslessly.

The bank's authored CEMP/CUIM and existing external atlas remain unchanged.
Use available arena padding before either root: the static/dynamic boundary
must remain the same. This is a matched app/resource candidate, not a write.
"""
from pathlib import Path
import argparse,hashlib,json,re,shutil,struct,zlib
from compact_wba_recording_ui import pack,unpack
from wba_resource_geometry import choose_static_bytes,geometry

ROOT=Path(__file__).resolve().parents[1]
sha=lambda b:hashlib.sha256(b).hexdigest()
def numbers(text):
 text=re.sub(r'/\*.*?\*/|//[^\n]*','',text,flags=re.S)
 return [int(v,16 if v.lower().startswith('0x') else 10) for v in
  re.findall(r'(?<!\w)(0x[0-9a-fA-F]+|\d+)(?:[uUlL]+)?(?!\w)',text)]
def array(text,name):
 m=re.search(r'static const uint(?:8|16)_t '+name+r'((?:\[\d*\])+)\s*=\s*\{(.*?)\};',text,re.S)
 if not m:raise ValueError('Missing native array: '+name)
 return numbers(m[2])
def generate(base,out,generation):
 profile=json.loads((base/'profile.json').read_bytes());bank=(base/'ui-partition.bin').read_bytes()
 assert profile['generation']==68 and generation==69
 assert sha(bank).upper()==profile['uiPartitionSha256'].upper()
 geo=geometry(len(bank));assert geo==profile['flashGeometry']
 previous=profile['externalUi'];offset=previous['extensionOffset'];old_end=offset+previous['extensionBytes']
 external=bytearray(bank[offset:old_end]);old_external=bytes(external)
 header=(base/'companion_wba_external_ui.h').read_text(encoding='utf8')
 assert sha((base/'companion_wba_external_ui.h').read_bytes())==previous['headerSha256']
 crc_macro=re.search(r'COMP_WBA_EXTERNAL_UI_CRC32 0x([0-9A-Fa-f]+)u',header)
 assert crc_macro and zlib.crc32(external)==int(crc_macro[1],16)
 maximum=previous['maxGlyphBytes'];dedup={};atlas=[];refs={};raw_hashes={}
 def put(raw):
  encoded=pack(raw)
  assert unpack(encoded,len(raw))==raw,'Lossless resource build failed'
  assert len(encoded)<=maximum,'New glyph exceeds existing bounded stack buffer'
  if encoded not in dedup:
   dedup[encoded]=len(external);external.extend(encoded)
  return '{%du,%du,0x%08Xu}'%(dedup[encoded],len(encoded),zlib.crc32(encoded))
 def keep(name,glyphs,shape):
  refs[name]=[put(raw) for raw in glyphs]
  raw=b''.join(glyphs);raw_hashes[name]=sha(raw)
  atlas.append(dict(name=name,shape=shape,glyphs=len(glyphs),decodedBytes=len(raw),
   encodedBytes=sum(len(pack(raw)) for raw in glyphs),originalSha256=sha(raw),lossless=True))
  def nested(dims,items):
   if len(dims)==1:return '{'+','.join(items)+'}'
   step=len(items)//dims[0]
   return '{'+','.join(nested(dims[1:],items[i*step:(i+1)*step]) for i in range(dims[0]))+'}'
  return 'static const comp_wba_external_bitmap_t '+name+''.join('['+str(d)+']' for d in shape)+' = '+nested(shape,refs[name])+';'
 generated=ROOT/'app/companion_pendant/runtime/generated'
 help_text=(generated/'companion_pet_help_labels.h').read_text(encoding='ascii').split('#else',1)[1]
 help_raw=bytes(array(help_text,'comp_pet_help_bits'));help_offsets=array(help_text,'comp_pet_help_offsets')
 assert len(help_offsets)==15
 labels=[help_raw[at:at+360] for at in help_offsets];assert all(len(v)==360 for v in labels)
 declarations=[keep('comp_pet_help_labels',labels,[3,5])]
 discovery_raw=bytes(array((generated/'companion_pet_discovery_caption.h').read_text(encoding='ascii'),'comp_pet_discovery_caption'))
 assert len(discovery_raw)==780
 captions=[discovery_raw[i*260:(i+1)*260] for i in range(3)]
 slices=1 if max(len(pack(raw)) for raw in captions)<=maximum else 2
 slice_rows=13 if slices==1 else 7
 parts=[raw[part*slice_rows*20:min((part+1)*slice_rows,13)*20] for raw in captions for part in range(slices)]
 declarations.append(keep('comp_pet_discovery_slices',parts,[3,slices]))
 battery_text=(generated/'companion_battery_display_labels.h').read_text(encoding='ascii')
 battery_raw=bytes(array(battery_text,'comp_battery_display_labels'));widths=array(battery_text,'comp_battery_display_widths')
 assert len(battery_raw)==1134 and len(widths)==9
 declarations.append(keep('comp_battery_display_labels',[battery_raw[i*126:(i+1)*126] for i in range(9)],[3,3]))
 declarations.append('static const uint8_t comp_battery_display_widths[3][3] = {'+','.join('{'+','.join(str(v)+'u' for v in widths[i*3:(i+1)*3])+'}' for i in range(3))+'};')
 defines='''
#define COMP_PET_HELP_LABELS 5u
#define COMP_PET_HELP_WIDTH 160u
#define COMP_PET_HELP_HEIGHT 18u
#define COMP_PET_HELP_STRIDE 20u
#define COMP_PET_DISCOVERY_WIDTH 160u
#define COMP_PET_DISCOVERY_HEIGHT 13u
#define COMP_PET_DISCOVERY_STRIDE 20u
'''+f'#define COMP_PET_DISCOVERY_SLICES {slices}u\n#define COMP_PET_DISCOVERY_SLICE_ROWS {slice_rows}u\n'
 used=offset+len(external)
 assert bytes(external[:len(old_external)])==old_external
 assert used<=geo['rootA'] and geometry(choose_static_bytes(used))==geo,'Boundary would move; no candidate'
 root=bytearray(bank[geo['rootA']:geo['rootA']+128])
 assert root[:4]==b'CUIR' and zlib.crc32(root[:124])==struct.unpack_from('<I',root,124)[0]
 bo,bs=struct.unpack_from('<II',root,16);assert bo+bs==old_end
 assert zlib.crc32(bank[bo:bo+bs])==struct.unpack_from('<I',root,24)[0]
 extension=bytes(external[len(old_external):]);identity=sha(bytes.fromhex(profile['resourceId'])+b'Companion pet labels v1\0'+extension).upper()
 header=re.sub(r'(COMP_WBA_EXTERNAL_UI_BYTES )\d+u',r'\g<1>'+str(len(external))+'u',header)
 header=re.sub(r'(COMP_WBA_EXTERNAL_UI_CRC32 )0x[0-9A-Fa-f]+u',r'\g<1>0x'+f'{zlib.crc32(external):08X}'+'u',header)
 header=header.rsplit('#endif',1)[0]+defines+'\n'.join(declarations)+'\n#endif\n'
 contract=(base/'companion_wba_resource_contract.h').read_text(encoding='utf8')
 assert 'COMPANION_WBA_RESOURCE_GENERATION 68u' in contract and profile['resourceId'] in contract
 contract=contract.replace('COMPANION_WBA_RESOURCE_GENERATION 68u','COMPANION_WBA_RESOURCE_GENERATION 69u').replace(profile['resourceId'],identity)
 merged_blob=bank[bo:bo+bs]+extension
 struct.pack_into('<I',root,8,generation);struct.pack_into('<II',root,20,len(merged_blob),zlib.crc32(merged_blob))
 struct.pack_into('<I',root,40,(used+4095)&~4095);root[44:76]=bytes.fromhex(identity)
 struct.pack_into('<I',root,124,zlib.crc32(root[:124]))
 result_bank=bytearray(bank);result_bank[old_end:used]=extension
 result_bank[geo['rootA']:geo['rootA']+128]=root
 # Root B is an install journal, never copied as a stale active identity.
 result_bank[geo['rootB']:]=b'\xff'*(len(result_bank)-geo['rootB'])
 assert result_bank[:old_end]==bank[:old_end]
 out.mkdir(parents=True,exist_ok=False)
 for p in base.glob('*.h'):shutil.copyfile(p,out/p.name)
 (out/'companion_wba_external_ui.h').write_text(header,encoding='utf8',newline='\n')
 (out/'companion_wba_resource_contract.h').write_text(contract,encoding='utf8',newline='\n')
 (out/'ui-partition.bin').write_bytes(result_bank)
 result=dict(schema='companion.wba.external-pet-labels.v1',generation=69,sourceGeneration=68,
  extensionOffset=offset,extensionBytes=len(external),addedOffset=old_end,addedBytes=len(extension),
  atlas=previous['atlas']+atlas,accessorySpansBytes=previous['accessorySpansBytes'],accessoryVariants=30,
  maxGlyphBytes=maximum,maxAccessoryBytes=previous['maxAccessoryBytes'],headerSha256=sha((out/'companion_wba_external_ui.h').read_bytes()),
  cempAndOriginalManifestUnchanged=True,existingExternalAtlasUnchanged=True,sourceBankSha256=sha(bank),newBankSha256=sha(result_bank),
  oldGeometry=geo,newGeometry=geo,pairedGeometryInstallationRequired=False,matchedAppResourcesRequired=True,
  arenaFreeBytes=geo['rootA']-used,discoverySlices=slices,discoverySliceRows=slice_rows,
  originalRasterHashes=raw_hashes,executableCodeMoved=False,codecTablesMoved=False,testsRun=False)
 profile.update(generation=69,resourceId=identity,uiPartitionSha256=sha(result_bank).upper(),
  resourceArenaUsedBytes=used,externalUi=result,hardwareAcceptance='NOT_RUN',fullChainAcceptance='NOT_RUN',
  recordingRegionPreserved=True,dynamicRegionIncluded=False,result='RESOURCE_CANDIDATE_BUILT')
 profile['sourceSha256'].update({p.relative_to(ROOT).as_posix():sha(p.read_bytes()).upper() for p in
  [Path(__file__),*[generated/n for n in ('companion_pet_help_labels.h','companion_pet_discovery_caption.h','companion_battery_display_labels.h')],
   out/'companion_wba_external_ui.h',out/'companion_wba_resource_contract.h']})
 (out/'profile.json').write_text(json.dumps(profile,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
 (out/'external-ui.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
 return result
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--base',type=Path,required=True)
 p.add_argument('--output',type=Path,required=True);p.add_argument('--generation',type=int,default=69);a=p.parse_args()
 print(json.dumps(generate(a.base.resolve(),a.output.resolve(),a.generation),ensure_ascii=False))
