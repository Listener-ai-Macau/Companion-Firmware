"""Protect the real UI84 retired-metadata boundary during label-only growth."""
from pathlib import Path
import json,re,struct,sys
from build_wba_customer_menu import atlas_fits_metadata
from wba_resource_geometry import geometry

base=Path(sys.argv[1]);profile=json.loads((base/'profile.json').read_bytes())
image=(base/'ui-partition.bin').read_bytes();root=geometry(len(image))['rootA']
blob=struct.unpack_from('<I',image,root+16)[0]
count=struct.unpack_from('<H',image,blob+8)[0]
rows=[image[blob+32+i*24:blob+56+i*24]for i in range(count)]
payloads=[(struct.unpack_from('<I',r,12)[0],struct.unpack_from('<I',r,12)[0]+struct.unpack_from('<H',r,16)[0])for r in rows if struct.unpack_from('<H',r,6)[0]]
first=blob+32+count*24;prior=profile['customerMenu']
header=(base/'companion_wba_customer_ui.h').read_text(encoding='ascii')
start=int(re.search(r'#define COMP_CUSTOMER_ATLAS_OFFSET (\d+)u',header)[1])
old_bytes=int(re.search(r'#define COMP_CUSTOMER_ATLAS_BYTES (\d+)u',header)[1])
last=prior['atlasOffset']+prior['retiredMetadataBytes']
assert atlas_fits_metadata(start,39363,first,last,payloads),'actual new label atlas fits the unoccupied tail'
assert not atlas_fits_metadata(start,last-start+1,first,last,payloads),'one byte beyond retired metadata must fail'
assert not atlas_fits_metadata(start,39363,first,last,[*payloads,(start+old_bytes,start+old_bytes+1)]),'a surviving payload in the proposed extension must fail'
assert not atlas_fits_metadata(first-1,10,first,last,payloads),'manifest metadata cannot be overwritten'
print('PASS UI84 real metadata growth: bounded free tail accepted; overrun/payload/manifest overlap rejected')
