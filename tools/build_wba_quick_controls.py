"""Append native quick-control labels to an exact UI70 bank, preserving artwork.

No board writes. This emits matched UI71 headers/profile/bank; the existing
dynamic boundary is retained and an overflow is rejected rather than crossed.
"""
from pathlib import Path
import argparse, hashlib, json, re, shutil, struct, zlib
from PIL import Image, ImageDraw, ImageFont
from compact_wba_recording_ui import pack, unpack
from wba_resource_geometry import geometry

sha=lambda b:hashlib.sha256(b).hexdigest()
LABELS=(('Quick','Mute','Settings'),('快捷','静音','设置'),('快捷','靜音','設定'))
def build(base,out):
    profile=json.loads((base/'profile.json').read_bytes());bank=(base/'ui-partition.bin').read_bytes()
    assert profile['generation']==70 and sha(bank).upper()==profile['uiPartitionSha256'].upper()
    geo=geometry(len(bank));assert geo==profile['flashGeometry']
    old=profile['externalUi'];offset=old['extensionOffset'];old_end=offset+old['extensionBytes']
    used=profile['resourceArenaUsedBytes'];assert old_end<=used<geo['rootA']
    header=(base/'companion_wba_external_ui.h').read_text(encoding='utf8')
    assert sha((base/'companion_wba_external_ui.h').read_bytes())==old['headerSha256']
    assert zlib.crc32(bank[offset:old_end])==int(re.search(r'COMP_WBA_EXTERNAL_UI_CRC32 0x([0-9A-Fa-f]+)',header)[1],16)
    # UI70 appended a new CEMP image after its atlas. Cover that unchanged gap
    # in the new atlas extent; all old bitmap offsets and original ink stay put.
    extension=bytearray(bank[offset:used]);dedup={};refs=[];glyphs=[];fonts={}
    width,height,stride=80,18,10
    for locale,labels in enumerate(LABELS):
        font_path=Path('C:/Windows/Fonts')/('segoeui.ttf' if locale==0 else 'simhei.ttf')
        fonts[str(font_path)]=sha(font_path.read_bytes());font=ImageFont.truetype(str(font_path),14)
        for text in labels:
            raster=Image.new('L',(width,height),255);draw=ImageDraw.Draw(raster)
            l,t,r,b=draw.textbbox((0,0),text,font=font);assert r-l<=width and b-t<=height
            draw.text((-l,(height-(b-t))//2-t),text,font=font,fill=0)
            raw=raster.point(lambda v:255 if v>=160 else 0).convert('1').tobytes()
            encoded=pack(raw);assert unpack(encoded,len(raw))==raw
            assert len(encoded)<=old['maxGlyphBytes']
            if encoded not in dedup:
                dedup[encoded]=len(extension);extension.extend(encoded)
            refs.append('{%du,%du,0x%08Xu}'%(dedup[encoded],len(encoded),zlib.crc32(encoded)))
            glyphs.append(raw)
    end=offset+len(extension);assert end<=geo['rootA'],'Quick labels would cross resource boundary'
    addition=bytes(extension[used-offset:]);identity=sha(bytes.fromhex(profile['resourceId'])+b'Quick controls v1\0'+addition).upper()
    root=bytearray(bank[geo['rootA']:geo['rootA']+128])
    assert root[:4]==b'CUIR' and zlib.crc32(root[:124])==struct.unpack_from('<I',root,124)[0]
    blob_offset,blob_bytes=struct.unpack_from('<II',root,16);assert blob_offset+blob_bytes==used
    assert zlib.crc32(bank[blob_offset:used])==struct.unpack_from('<I',root,24)[0]
    result=bytearray(bank);result[used:end]=addition
    struct.pack_into('<I',root,8,71);struct.pack_into('<II',root,20,end-blob_offset,zlib.crc32(result[blob_offset:end]))
    struct.pack_into('<I',root,40,(end+4095)&~4095);root[44:76]=bytes.fromhex(identity)
    struct.pack_into('<I',root,124,zlib.crc32(root[:124]));result[geo['rootA']:geo['rootA']+128]=root
    result[geo['rootB']:]=b'\xff'*(len(result)-geo['rootB'])
    assert result[:used]==bank[:used]
    header=re.sub(r'(COMP_WBA_EXTERNAL_UI_BYTES )\d+u',r'\g<1>'+str(len(extension))+'u',header)
    header=re.sub(r'(COMP_WBA_EXTERNAL_UI_CRC32 )0x[0-9A-Fa-f]+u',r'\g<1>0x'+f'{zlib.crc32(extension):08X}'+'u',header)
    decl='\n#define COMP_WBA_QUICK_LABEL_COUNT 3u\n#define COMP_WBA_QUICK_LABEL_WIDTH 80u\n#define COMP_WBA_QUICK_LABEL_HEIGHT 18u\n#define COMP_WBA_QUICK_LABEL_STRIDE 10u\n'
    decl+='static const comp_wba_external_bitmap_t comp_wba_quick_labels[3][3] = {'+','.join('{'+','.join(refs[i*3:(i+1)*3])+'}' for i in range(3))+'};\n'
    header=header.rsplit('#endif',1)[0]+decl+'#endif\n'
    contract=(base/'companion_wba_resource_contract.h').read_text(encoding='utf8')
    assert 'COMPANION_WBA_RESOURCE_GENERATION 70u' in contract
    contract=contract.replace('COMPANION_WBA_RESOURCE_GENERATION 70u','COMPANION_WBA_RESOURCE_GENERATION 71u').replace(profile['resourceId'],identity)
    out.mkdir(parents=True,exist_ok=False)
    for p in base.glob('*.h'):shutil.copyfile(p,out/p.name)
    (out/'companion_wba_external_ui.h').write_text(header,encoding='utf8',newline='\n')
    (out/'companion_wba_resource_contract.h').write_text(contract,encoding='utf8',newline='\n')
    (out/'ui-partition.bin').write_bytes(result)
    for locale in range(3):
        sheet=Image.new('1',(width,height*3),1)
        for n in range(3):sheet.paste(Image.frombytes('1',(width,height),glyphs[locale*3+n]),(0,n*height))
        sheet.save(out/f'quick-labels-{locale}.png')
    report=dict(result='UI71_QUICK_LABELS_BUILT_NOT_INSTALLED',sourceBankSha256=sha(bank),newBankSha256=sha(result),
        labels=LABELS,fontSources=fonts,addedOffset=used,addedBytes=len(addition),usedBytes=end,arenaFreeBytes=geo['rootA']-end,
        oldGeometry=geo,newGeometry=geo,originalStatePixelsUnchanged=True,originalAtlasOffsetsUnchanged=True,
        matchedAppResourcesRequired=True,pairedGeometryInstallationRequired=False,testsRun=False,installed=False,physicalQualified=False)
    ext=dict(old);ext.update(generation=71,extensionBytes=len(extension),newBankSha256=sha(result),arenaFreeBytes=geo['rootA']-end,
        headerSha256=sha((out/'companion_wba_external_ui.h').read_bytes()))
    ext['atlas']=old['atlas']+[dict(name='comp_wba_quick_labels',shape=[3,3],glyphs=9,decodedBytes=len(b''.join(glyphs)),
        originalSha256=sha(b''.join(glyphs)),lossless=True)]
    profile.update(generation=71,resourceId=identity,uiPartitionSha256=sha(result).upper(),resourceArenaUsedBytes=end,
        generationBytes=end-blob_offset,
        externalUi=ext,quickControls=report,hardwareAcceptance='NOT_RUN',fullChainAcceptance='NOT_RUN')
    assert profile['generationBytes']==struct.unpack_from('<I',root,20)[0]
    assert blob_offset+profile['generationBytes']==profile['resourceArenaUsedBytes']
    profile['sourceSha256'].update({Path(__file__).resolve().relative_to(Path(__file__).resolve().parents[1]).as_posix():sha(Path(__file__).read_bytes()).upper()})
    for name in ('companion_wba_external_ui.h','companion_wba_resource_contract.h'):
        profile['sourceSha256'][str((out/name).resolve())]=sha((out/name).read_bytes()).upper()
    (out/'profile.json').write_text(json.dumps(profile,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    (out/'quick-controls.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    return report
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--base',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();print(json.dumps(build(a.base.resolve(),a.output.resolve()),ensure_ascii=False))
