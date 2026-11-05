"""UI84 customer menu labels in existing static geometry, no device access.

The obsolete raster-menu manifest entries are retired by hash. Their metadata
space holds the new label atlas. CEMP, every surviving entry and payload, old
external atlases and all non-menu artwork remain byte-identical.
"""
from pathlib import Path
import argparse,hashlib,json,re,shutil,struct,zlib
from PIL import Image,ImageDraw
from compact_wba_recording_ui import pack,unpack
from wba_resource_geometry import geometry
from wba_menu_typography import draw_text,text_width
from wba_menu_icons import category_icon
import wba_customer_menu as model
from build_wba_pet_play_labels import LABELS as PLAY_LABELS,raster as play_raster

ROOT=Path(__file__).resolve().parents[1]
sha=lambda b:hashlib.sha256(b).hexdigest()

def atlas_fits_metadata(start,size,first,last,payloads):
    """An existing label atlas may grow only into verified unused metadata."""
    return size>0 and first<=start and start+size<=last and all(
        right<=start or left>=start+size for left,right in payloads)

def build(base,out):
    profile=json.loads((base/'profile.json').read_bytes());old=(base/'ui-partition.bin').read_bytes()
    assert profile['generation'] in (83,84) and sha(old).upper()==profile['uiPartitionSha256'].upper()
    geo=geometry(len(old));root=bytearray(old[geo['rootA']:geo['rootA']+128])
    assert root[:4]==b'CUIR' and zlib.crc32(root[:124])==struct.unpack_from('<I',root,124)[0]
    blob,blob_n=struct.unpack_from('<II',root,16)
    count,entry_n=struct.unpack_from('<HH',old,blob+8);assert entry_n==24
    old_end=blob+32+count*24
    # Enumerate all legacy menu aliases without regenerating character art.
    from build_wba_product_resources import menu_states,fnv
    # Destructive confirmations retain their already reviewed authored art,
    # exact button geometry and original feedback/count renderer.
    rows=[old[blob+32+i*24:blob+56+i*24] for i in range(count)]
    if profile['generation']==83:
        hashes={fnv(s) for s in menu_states() if '_s11_' not in s and '_s12_' not in s}
        kept=[r for r in rows if struct.unpack_from('<I',r)[0] not in hashes]
        removed=count-len(kept);assert removed>500
    else:
        # Refresh labels in the existing retired metadata arena. Keep the
        # already-qualified pet manifest/payloads, including later art fixes.
        prior=profile['customerMenu'];assert prior['retiredMenuStates']>500
        # Later reviewed pet variants add manifest rows and relocate this
        # atlas. The active generated header is authoritative; historical
        # profile geometry is retained only for the retired arena boundary.
        header=(base/'companion_wba_customer_ui.h').read_text(encoding='ascii')
        def current_define(name):
            match=re.search(r'#define '+name+r' (\d+)u',header);assert match,name
            return int(match.group(1))
        current_atlas=current_define('COMP_CUSTOMER_ATLAS_OFFSET')
        current_bytes=current_define('COMP_CUSTOMER_ATLAS_BYTES')
        old_end=prior['atlasOffset']+prior['retiredMetadataBytes']
        assert blob+32+count*24<=current_atlas<current_atlas+current_bytes<=old_end<=geo['rootA']
        kept=rows;removed=prior['retiredMenuStates']
    start=blob+32+len(kept)*24
    keys=list(model.TEXT);play_first=len(keys)+4;per=play_first+len(PLAY_LABELS)*2
    atlas=bytearray(3*per*8);dedup={};max_bytes=0;glyph_hashes=[]
    def put(locale,index,raw,width):
        nonlocal max_bytes
        encoded=pack(raw);assert unpack(encoded,len(raw))==raw
        assert 0<len(encoded)<=199,(locale,index,len(encoded))
        max_bytes=max(max_bytes,len(encoded))
        if encoded not in dedup:dedup[encoded]=len(atlas);atlas.extend(encoded)
        offset=dedup[encoded];assert offset<=65535
        struct.pack_into('<HBBI',atlas,(locale*per+index)*8,offset,len(encoded),width,zlib.crc32(encoded))
        glyph_hashes.append(sha(raw))
    for locale in range(3):
        for i,key in enumerate(keys):
            text=model.TEXT[key][locale];size=12 if key=='MANUAL' else 14
            while size>=11:
                if text_width(text,size,submenu=True)<=176:
                    image=Image.new('1',(176,16),1);d=ImageDraw.Draw(image)
                    draw_text(d,(0,0),text,size,width=176,submenu=True)
                    if len(pack(image.tobytes()))<=199:break
                size-=1
            assert size>=11,(key,text,'native width or199-byte decoder limit')
            put(locale,i,image.tobytes(),text_width(text,size,submenu=True))
        for i,ident in enumerate((1,3,4,7)):
            image=Image.new('1',(48,42),1);category_icon(ImageDraw.Draw(image),ident,2,0)
            put(locale,len(keys)+i,image.tobytes(),48)
        # Keep the exact existing18px play/help text pixels. Two9px slices
        # each fit the unchanged199-byte external glyph buffer. UI84 no longer
        # carries a second copy of these bitmaps in internal program Flash.
        for i,texts in enumerate(PLAY_LABELS):
            image,_,_=play_raster(texts,locale)
            for half in range(2):
                put(locale,play_first+i*2+half,image.crop((0,half*9,160,(half+1)*9)).tobytes(),160)
    if profile['generation']==84:
        payloads = [(struct.unpack_from('<I',row,12)[0],
                      struct.unpack_from('<I',row,12)[0]+struct.unpack_from('<H',row,16)[0])
                     for row in kept if struct.unpack_from('<H',row,6)[0]]
        occupied=[(current_atlas,current_atlas+current_bytes),*payloads]
        # All surviving payload intervals remain immutable. Reuse the
        # existing atlas only if it fits; otherwise select a bounded gap in
        # the already retired metadata arena, never the recording region.
        if atlas_fits_metadata(current_atlas,len(atlas),blob+32+len(kept)*24,old_end,payloads):
            start=current_atlas
        else:
            cursor=blob+32+len(kept)*24;start=None
            for left,right in sorted(occupied)+[(old_end,old_end)]:
                if right<=cursor:continue
                aligned=(cursor+7)&~7
                if aligned+len(atlas)<=min(left,old_end):start=aligned;break
                cursor=max(cursor,right)
            assert start is not None,('No safe retired-metadata gap for customer labels',len(atlas),old_end)
    assert start+len(atlas)<=old_end,'Customer labels must fit retired metadata, not move recording data'
    bank=bytearray(old)
    bank[blob+32:blob+32+len(kept)*24]=b''.join(kept)
    struct.pack_into('<H',bank,blob+8,len(kept))
    struct.pack_into('<I',bank,blob+12,32+len(kept)*24)
    bank[start:start+len(atlas)]=atlas
    # Do not touch anything outside old manifest metadata and rootA.
    assert bank[:blob]==old[:blob] and bank[old_end:geo['rootA']]==old[old_end:geo['rootA']]
    for r in kept:
        h,base_index,flags,crc,offset,n,duration,pcrc=struct.unpack('<IHHIIHHI',r)
        if flags:
            if profile['generation']==83:
                assert offset>=old_end
            else:
                # Later UI84 art patches may occupy the retired arena beyond
                # the atlas. Prove that no surviving payload overlaps labels.
                assert offset+n<=start or offset>=start+len(atlas),(offset,n,start,len(atlas))
            assert bank[offset:offset+n]==old[offset:offset+n]
    identity=hashlib.sha256(b'companion.customer-menu.ui84.v1\0'+bytes.fromhex(profile['resourceId'])+bytes(bank[blob:start+len(atlas)])).digest()
    struct.pack_into('<I',root,8,84);struct.pack_into('<I',root,24,zlib.crc32(bank[blob:blob+blob_n]))
    struct.pack_into('<II',root,32,32+len(kept)*24,zlib.crc32(bank[blob:blob+32+len(kept)*24]))
    root[44:76]=identity;struct.pack_into('<I',root,124,zlib.crc32(root[:124]));bank[geo['rootA']:geo['rootA']+128]=root
    out.mkdir(parents=True,exist_ok=False)
    for p in base.glob('*.h'):shutil.copyfile(p,out/p.name)
    contract=(out/'companion_wba_resource_contract.h').read_text(encoding='utf-8')
    contract=re.sub(r'(COMPANION_WBA_RESOURCE_GENERATION )83u',r'\g<1>84u',contract)
    contract=re.sub(r'(COMPANION_WBA_RESOURCE_STATE_COUNT )\d+u',r'\g<1>'+str(len(kept))+'u',contract)
    contract=contract.replace(profile['resourceId'],identity.hex().upper())
    (out/'companion_wba_resource_contract.h').write_text(contract,encoding='utf-8')
    header=['/* External UI84 label records: offset16, bytes8, width8, crc32. */',
      '#ifndef COMPANION_WBA_CUSTOMER_UI_H','#define COMPANION_WBA_CUSTOMER_UI_H',
      f'#define COMP_CUSTOMER_ATLAS_OFFSET {start}u',f'#define COMP_CUSTOMER_ATLAS_BYTES {len(atlas)}u',
      f'#define COMP_CUSTOMER_GLYPHS_PER_LOCALE {per}u','#define COMP_CUSTOMER_RECORD_BYTES 8u',
      f'#define COMP_CUSTOMER_PLAY_FIRST {play_first}u',f'#define COMP_CUSTOMER_PLAY_LABEL_COUNT {len(PLAY_LABELS)}u',
      '#define COMP_CUSTOMER_BITMAP_FLAG 0x80000000u','#endif','']
    (out/'companion_wba_customer_ui.h').write_text('\n'.join(header),encoding='ascii')
    (out/'ui-partition.bin').write_bytes(bank)
    proof=dict(generation=84,baseGeneration=profile['generation'],retiredMenuStates=removed,survivingStates=len(kept),
      atlasOffset=start,atlasBytes=len(atlas),retiredMetadataBytes=old_end-start,maxGlyphBytes=max_bytes,
      sameStaticAndDynamicGeometry=True,cempByteIdentical=True,survivingEntryAndPayloadBytesIdentical=True,
      originalExternalAtlasBytesIdentical=True,originalPetArtUnchanged=True,installed=False,hardwareOperations=0)
    profile.update(generation=84,resourceId=identity.hex().upper(),uiPartitionSha256=sha(bank).upper(),stateCount=len(kept),
      customerMenu=proof,result='CUSTOMER_MENU_RESOURCE_CANDIDATE_NOT_INSTALLED')
    profile['sourceSha256'].update({str(p.relative_to(ROOT)):sha(p.read_bytes()).upper() for p in (Path(__file__),ROOT/'tools/wba_customer_menu.py')})
    (out/'profile.json').write_text(json.dumps(profile,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    (out/'customer-menu.json').write_text(json.dumps(proof,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    model.write_contract(ROOT/'app/companion_pendant/runtime/generated/companion_customer_menu_contract.h')
    return proof

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--base',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();print(json.dumps(build(a.base.resolve(),a.output.resolve()),ensure_ascii=False))
