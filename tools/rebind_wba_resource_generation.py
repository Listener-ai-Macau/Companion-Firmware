"""Advance an existing resource identity for paired OTA without redrawing art.

Only authenticated CUIR root metadata and its matching compile-time contract
change. CEMP, state patches, fonts and accessories retain every original byte.
This is resource version binding, not a new art build or hardware acceptance.
"""
from pathlib import Path
import argparse,hashlib,json,re,shutil,struct,zlib
from wba_resource_geometry import from_profile

ROOT=Path(__file__).resolve().parents[1]
def sha(value):return hashlib.sha256(value).hexdigest().upper()

def rebind(source:Path,output:Path,generation:int):
    profile=json.loads((source/'profile.json').read_bytes())
    old_generation=profile['generation'];old=(source/'ui-partition.bin').read_bytes()
    if not old_generation<generation<=0xffffffff or sha(old)!=profile['uiPartitionSha256'].upper():
        raise ValueError('Require intact original bank and a strictly newer generation')
    geometry=from_profile(profile,len(old));old_id=bytes.fromhex(profile['resourceId'])
    new_id=hashlib.sha256(b'companion.retained-pixels-generation.v1\0'+
        struct.pack('<II',old_generation,generation)+old_id+hashlib.sha256(old).digest()).digest()
    image=bytearray(old);roots=[]
    for at in (geometry['rootA'],geometry['rootB']):
        root=bytearray(old[at:at+128])
        if root==b'\xff'*128:continue
        if root[:8]!=b'CUIR\x01\x00\x80\x00' or struct.unpack_from('<I',root,8)[0]!=old_generation or root[44:76]!=old_id or struct.unpack_from('<I',root,124)[0]!=zlib.crc32(root[:124]):
            raise ValueError('Unknown or inconsistent existing resource root')
        struct.pack_into('<I',root,8,generation);root[44:76]=new_id
        struct.pack_into('<I',root,124,zlib.crc32(root[:124]));image[at:at+128]=root;roots.append(at)
    if not roots or bytes(image[:geometry['rootA']])!=old[:geometry['rootA']]:
        raise ValueError('No valid root or changed resource pixels')
    changed=[n for n,(a,b) in enumerate(zip(old,image)) if a!=b]
    if any(not any(at<=n<at+128 for at in roots) for n in changed):
        raise ValueError('Modification escaped resource metadata')
    contract=(source/'companion_wba_resource_contract.h').read_text(encoding='utf-8')
    if contract.count('"'+profile['resourceId']+'"')!=1:raise ValueError('Unknown original resource contract')
    contract,count=re.subn(r'(#define COMPANION_WBA_RESOURCE_GENERATION )'+str(old_generation)+r'u\b',lambda m:m[1]+str(generation)+'u',contract)
    if count!=1:raise ValueError('Unknown resource generation macro')
    contract=contract.replace('"'+profile['resourceId']+'"','"'+new_id.hex().upper()+'"')
    shutil.copytree(source,output)
    (output/'ui-partition.bin').write_bytes(image)
    (output/'companion_wba_resource_contract.h').write_text(contract,encoding='utf-8')
    profile.update(generation=generation,resourceId=new_id.hex().upper(),uiPartitionSha256=sha(image),
        result='EXISTING_PIXELS_NEW_RESOURCE_GENERATION_SOFTWARE_ONLY')
    profile['sourceSha256'][Path(__file__).relative_to(ROOT).as_posix()]=sha(Path(__file__).read_bytes())
    receipt=dict(schema='companion.retained-pixels-generation.v1',oldGeneration=old_generation,
        generation=generation,oldResourceId=old_id.hex(),newResourceId=new_id.hex(),
        oldBankSha256=sha(old),bankSha256=sha(image),changedBytes=len(changed),rootOffsets=roots,
        allNonRootBytesPreserved=True,hardwareAcceptance='NOT_RUN',artChanged=False)
    profile['generationRebind']=receipt
    (output/'profile.json').write_text(json.dumps(profile,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    (output/'generation-rebind.json').write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8')
    return receipt

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',required=True,type=Path)
    parser.add_argument('--output',required=True,type=Path)
    parser.add_argument('--generation',required=True,type=int)
    args=parser.parse_args();print(json.dumps(rebind(args.source.resolve(),args.output.resolve(),args.generation)))
