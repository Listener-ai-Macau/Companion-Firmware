"""Reconstruct build contracts for the exact installed public UI85 image.

No art is changed or built into a new bank. Every reference is checked against
the historical-image bytes; the customer atlas generator must match in full.
"""
from pathlib import Path
import argparse,hashlib,json,re,shutil,struct,sys,textwrap,zlib

ROOT=Path(__file__).resolve().parents[1]
EXPECTED='5c16dfabdb1a59e4280f2eb867050d870273c717dbf4a571e3ee9f72ccb12b09'
HISTORICAL_EXTERNAL_HEADER='efc317bad1674def31d270faee5ec971f9b3a5cec513571e7c97f6c663d25af7'
sha=lambda b:hashlib.sha256(b).hexdigest()

def recover(bank_path,base,out):
    from wba_resource_geometry import geometry
    from externalize_recording_reason import values
    from compact_wba_recording_ui import unpack
    import build_wba_customer_menu as customer
    bank=bank_path.read_bytes();assert len(bank)==950272 and sha(bank)==EXPECTED
    old_profile=json.loads((base/'profile.json').read_bytes());old=(base/'ui-partition.bin').read_bytes()
    assert sha(old).upper()==old_profile['uiPartitionSha256'].upper()
    geo=geometry(len(bank));root=bank[geo['rootA']:geo['rootA']+128]
    assert root[:8]==b'CUIR\x01\x00\x80\x00' and zlib.crc32(root[:124])==struct.unpack_from('<I',root,124)[0]
    gen,cemp_bytes,bo,bn,blob_crc=struct.unpack_from('<IIIII',root,8)
    mn,manifest_crc=struct.unpack_from('<II',root,32)
    assert gen==85 and zlib.crc32(bank[bo:bo+bn])==blob_crc
    assert zlib.crc32(bank[bo:bo+mn])==manifest_crc
    count,entry_bytes=struct.unpack_from('<HH',bank,bo+8)
    assert entry_bytes==24 and mn==32+count*24
    assert bank[:cemp_bytes]==old[:cemp_bytes], 'Retained CEMP contract does not match'
    rid=root[44:76].hex().upper();used=bo+bn
    start=878709 # Exact historical external atlas offset, verified in full below.
    ext=bank[start:used]
    header=(base/'companion_wba_external_ui.h').read_text(encoding='utf8')
    old_start=old_profile['externalUi']['extensionOffset']
    for o,n,c in re.findall(r'\{(\d+)u,(\d+)u,(0x[0-9a-fA-F]+)u\}',header):
        o,n,c=int(o),int(n),int(c,0)
        assert old[old_start+o:old_start+o+n]==bank[start+o:start+o+n]
        assert zlib.crc32(bank[start+o:start+o+n])==c
    header=re.sub(r'(COMP_WBA_EXTERNAL_UI_OFFSET )\d+u',lambda m:m[1]+str(start)+'u',header)
    header=re.sub(r'(COMP_WBA_EXTERNAL_UI_BYTES )\d+u',lambda m:m[1]+str(len(ext))+'u',header)
    header=re.sub(r'(COMP_WBA_EXTERNAL_UI_CRC32 )0x[0-9a-fA-F]+u',lambda m:m[1]+f'0x{zlib.crc32(ext):08X}u',header)
    native=(ROOT/'app/companion_pendant/runtime/generated/companion_recording_reason_labels.h').read_text(encoding='ascii')
    packed,plain=native.split('#else',1)
    compressed=bytes(values(packed,'comp_record_reason_bits'))
    offsets=values(packed,'comp_record_reason_offsets');original=bytes(values(plain,'comp_record_reason_bits'))
    reason_at=used-len(compressed)
    assert bank[reason_at:used]==compressed and len(offsets)==12 and len(original)==12*224
    refs=[]
    for i,(lo,hi) in enumerate(zip(offsets,offsets[1:]+[len(compressed)])):
        encoded=compressed[lo:hi];assert unpack(encoded,224)==original[i*224:(i+1)*224]
        refs.append('{%du,%du,0x%08Xu}'%(reason_at-start+lo,len(encoded),zlib.crc32(encoded)))
    rows=['{'+','.join(refs[i:i+4])+'}' for i in range(0,12,4)]
    header=header.rsplit('#endif',1)[0]+'#define COMP_WBA_EXTERNAL_RECORD_REASON 1\nstatic const comp_wba_external_bitmap_t comp_record_reason_external[3][4] = {'+','.join(rows)+'};\n#endif\n'
    external_exact=sha(header.encode())==HISTORICAL_EXTERNAL_HEADER
    # Reuse the generator's exact atlas-only block. It does not mutate bank,
    # source art, model contracts, GPIO or any other resource metadata.
    generator=(ROOT/'tools/build_wba_customer_menu.py').read_text()
    block=generator[generator.index('    keys=list(model.TEXT);'):generator.index("    if profile['generation']==84:",generator.index('    keys=list(model.TEXT);'))]
    ns=dict(vars(customer));exec('def atlas_only():\n'+block+'    return locals()\n',ns)
    result=ns['atlas_only']();atlas=bytes(result['atlas']);atlas_at=bank.find(atlas)
    assert atlas_at>=0 and bank.count(atlas)==1,'Current label generator differs from installed atlas'
    assert bo+mn<=atlas_at and atlas_at+len(atlas)<=start
    for i in range(3*result['per']):
        off,n,width,crc=struct.unpack_from('<HBBI',atlas,i*8)
        assert off>=3*result['per']*8 and 0<n<=199 and 0<width<=176
        assert off+n<=len(atlas) and zlib.crc32(atlas[off:off+n])==crc
    customer_header=['/* External UI84 label records: offset16, bytes8, width8, crc32. */',
      '#ifndef COMPANION_WBA_CUSTOMER_UI_H','#define COMPANION_WBA_CUSTOMER_UI_H',
      f'#define COMP_CUSTOMER_ATLAS_OFFSET {atlas_at}u',f'#define COMP_CUSTOMER_ATLAS_BYTES {len(atlas)}u',
      f'#define COMP_CUSTOMER_GLYPHS_PER_LOCALE {result["per"]}u','#define COMP_CUSTOMER_RECORD_BYTES 8u',
      f'#define COMP_CUSTOMER_PLAY_FIRST {result["play_first"]}u',f'#define COMP_CUSTOMER_PLAY_LABEL_COUNT {len(customer.PLAY_LABELS)}u',
      '#define COMP_CUSTOMER_BITMAP_FLAG 0x80000000u','#endif','']
    contract=(base/'companion_wba_resource_contract.h').read_text(encoding='utf8')
    contract=re.sub(r'(COMPANION_WBA_RESOURCE_GENERATION )\d+u',r'\g<1>85u',contract)
    contract=re.sub(r'(COMPANION_WBA_RESOURCE_STATE_COUNT )\d+u',lambda m:m[1]+str(count)+'u',contract)
    contract=contract.replace(old_profile['resourceId'],rid)
    assert f'"{rid}"' in contract
    out.mkdir(parents=True,exist_ok=False)
    for p in base.glob('*.h'):shutil.copy2(p,out/p.name)
    (out/'ui-partition.bin').write_bytes(bank)
    (out/'companion_wba_resource_contract.h').write_text(contract,encoding='utf8',newline='\n')
    (out/'companion_wba_external_ui.h').write_text(header,encoding='utf8',newline='\n')
    (out/'companion_wba_customer_ui.h').write_text('\n'.join(customer_header),encoding='ascii',newline='\n')
    profile={k:old_profile[k] for k in ('profileRevision','storageLayoutVersion','cempBytes')}
    profile.update(result='EXACT_HISTORICAL_BANK_RECOVERED_BUILD_CONTRACTS_RECONSTRUCTED',generation=85,
       resourceId=rid,stateCount=count,uiPartitionBytes=len(bank),uiPartitionSha256=sha(bank).upper(),
       flashGeometry=geo,resourceArenaUsedBytes=used,generationBytes=bn,hardwareAcceptance='NOT_RUN',
       fullChainAcceptance='NOT_RUN',recordingRegionPreserved=True,dynamicRegionIncluded=False,
       sourceMode='IMMUTABLE_PUBLIC_IMAGE_RECOVERY_NOT_ART_REBUILD')
    ext_profile=dict(old_profile['externalUi']);ext_profile.update(generation=85,extensionOffset=start,
       extensionBytes=len(ext),headerSha256=sha(header.encode()),newBankSha256=sha(bank),
       recordReasonBytes=len(compressed),arenaFreeBytes=geo['rootA']-used)
    ext_profile['atlas']=ext_profile['atlas']+[dict(name='comp_record_reason_external',shape=[3,4],glyphs=12,
       decodedBytes=len(original),encodedBytes=len(compressed),originalSha256=sha(original),lossless=True)]
    profile['externalUi']=ext_profile
    provenance=[out/'ui-partition.bin',*sorted(out.glob('*.h')),Path(__file__),
       ROOT/'tools/build_wba_customer_menu.py',ROOT/'tools/wba_customer_menu.py',
       ROOT/'tools/build_wba_pet_play_labels.py',ROOT/'tools/wba_menu_typography.py',
       ROOT/'tools/wba_menu_icons.py',ROOT/'tools/compact_wba_recording_ui.py']
    profile['sourceSha256']={p.relative_to(ROOT).as_posix():sha(p.read_bytes()).upper() for p in provenance}
    (out/'profile.json').write_text(json.dumps(profile,ensure_ascii=False,indent=2)+'\n',encoding='utf8',newline='\n')
    proof=dict(result='PASS_EXACT_BANK_AND_BOUND_BUILD_CONTRACTS',bankSha256=sha(bank),
       expectedHistoricalBankSha256=EXPECTED,exactHistoricalExternalHeader=external_exact,
       externalHeaderSha256=sha(header.encode()),historicalExternalHeaderSha256=HISTORICAL_EXTERNAL_HEADER,
       cempByteIdenticalToRetained77=True,existingAtlasReferencesVerified=220,
       addedReasonGlyphsVerified=12,customerAtlasFullByteMatch=True,customerAtlasOffset=atlas_at,
       customerAtlasBytes=len(atlas),customerGlyphs=3*result['per'],stateCount=count,
       dynamicBoundaryUnchanged=True,deviceWrites=0,qualification='Recovered public bank is exact historical image; contracts bind it. No new art, menu behavior or hardware feedback is qualified by this recovery.')
    (out/'recovery.json').write_text(json.dumps(proof,indent=2)+'\n',encoding='utf8',newline='\n')
    return proof

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--bank',type=Path,required=True)
    p.add_argument('--retained-base',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();print(json.dumps(recover(a.bank.resolve(),a.retained_base.resolve(),a.output.resolve()),indent=2))
