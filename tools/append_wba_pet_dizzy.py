#!/usr/bin/env python3
"""Append one generated dizzy whole-face state without replacing any old state.

The existing CEMP and all old bitmap payloads/atlases are retained byte for byte.
One CUIM row relocates old absolute payload offsets by24 bytes. The new packed
frame fits existing static-arena padding; roots/dynamic boundary do not move.
"""
import argparse,copy,hashlib,json,re,shutil,struct,sys,zlib
from pathlib import Path
from PIL import Image
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"tools/faraday_upper_art"))
from build_ui_asset_generation import encode_packbits,fnv1a32
from wba_resource_geometry import geometry
sha=lambda b:hashlib.sha256(b).hexdigest()
STATE="pet_shake_dizzy"
def generate(base,art,out):
    assert not out.exists(),"Use a fresh immutable candidate directory"
    profile=json.loads((base/"profile.json").read_bytes())
    bank=(base/"ui-partition.bin").read_bytes()
    assert profile["generation"]==69 and sha(bank).upper()==profile["uiPartitionSha256"].upper()
    geo=geometry(len(bank));assert geo==profile["flashGeometry"]
    root=bytearray(bank[geo["rootA"]:geo["rootA"]+128])
    assert root[:4]==b"CUIR" and zlib.crc32(root[:124])==struct.unpack_from("<I",root,124)[0]
    bo,bs=struct.unpack_from("<II",root,16);mo,ms=struct.unpack_from("<II",root,28)
    assert mo==0 and zlib.crc32(bank[bo:bo+bs])==struct.unpack_from("<I",root,24)[0]
    manifest=bytearray(bank[bo:bo+ms]);assert manifest[:4]==b"CUIM"
    count,size=struct.unpack_from("<HH",manifest,8)
    assert size==24 and ms==32+count*size and count==profile["stateCount"]
    assert zlib.crc32(manifest)==struct.unpack_from("<I",root,36)[0]
    rows=[list(struct.unpack_from("<IHHIIHHI",manifest,32+i*24)) for i in range(count)]
    assert all(a[0]<b[0] for a,b in zip(rows,rows[1:]))
    h=fnv1a32(STATE);assert h not in {r[0] for r in rows}
    old_atlas=profile["externalUi"];ao=old_atlas["extensionOffset"];an=old_atlas["extensionBytes"]
    assert bo+bs==profile["resourceArenaUsedBytes"]==ao+an
    original_rows=copy.deepcopy(rows)
    for r in rows:
        if r[2]:
            assert bo+ms<=r[4] and r[4]+r[5]<=ao
            assert zlib.crc32(bank[r[4]:r[4]+r[5]])==r[7]
            r[4]+=24
    im=Image.open(art);assert im.size==(200,200)
    frame=bytearray(im.convert("1",dither=Image.Dither.NONE).tobytes())
    assert len(frame)==5000
    # Status is runtime UI. Preserve all generated facial pixels unchanged.
    frame[:16*25]=b"\xff"*(16*25)
    packed=encode_packbits(bytes(frame))
    new_offset=bo+bs+24;used=new_offset+len(packed)
    assert used<=geo["rootA"],"No silent static/dynamic layout migration"
    row=[h,65535,2,zlib.crc32(frame),new_offset,len(packed),1000,zlib.crc32(packed)]
    rows.append(row);rows.sort(key=lambda r:r[0])
    struct.pack_into("<H",manifest,8,count+1);struct.pack_into("<I",manifest,12,ms+24)
    new_manifest=bytes(manifest[:32])+b"".join(struct.pack("<IHHIIHHI",*r) for r in rows)
    assert len(new_manifest)==ms+24
    blob=new_manifest+bank[bo+ms:bo+bs]+packed
    assert len(blob)==bs+24+len(packed)
    identity=sha(bytes.fromhex(profile["resourceId"])+b"Companion generated dizzy v1\0"+STATE.encode()+bytes(frame)).upper()
    struct.pack_into("<I",root,8,70);struct.pack_into("<II",root,20,len(blob),zlib.crc32(blob))
    struct.pack_into("<II",root,32,len(new_manifest),zlib.crc32(new_manifest))
    struct.pack_into("<I",root,40,(used+4095)&~4095);root[44:76]=bytes.fromhex(identity)
    struct.pack_into("<I",root,124,zlib.crc32(root[:124]))
    new_bank=bytearray(bank);new_bank[bo:used]=blob
    new_bank[geo["rootA"]:geo["rootA"]+128]=root
    new_bank[geo["rootB"]:]=b"\xff"*(len(bank)-geo["rootB"])
    assert new_bank[:bo]==bank[:bo]
    for before,after in zip(original_rows,[r for r in rows if r[0]!=h]):
        assert before[:4]==after[:4] and before[5:]==after[5:]
        if before[2]:
            assert new_bank[after[4]:after[4]+after[5]]==bank[before[4]:before[4]+before[5]]
        else:assert before==after
    assert new_bank[ao+24:ao+24+an]==bank[ao:ao+an]
    out.mkdir(parents=True)
    for p in base.glob("*.h"):shutil.copyfile(p,out/p.name)
    header=(base/"companion_wba_external_ui.h").read_text(encoding="utf8")
    header,n=re.subn(r"(COMP_WBA_EXTERNAL_UI_OFFSET )\d+u",r"\g<1>"+str(ao+24)+"u",header)
    assert n==1
    (out/"companion_wba_external_ui.h").write_text(header,encoding="utf8",newline="\n")
    contract=(base/"companion_wba_resource_contract.h").read_text(encoding="utf8")
    assert f"COMPANION_WBA_RESOURCE_STATE_COUNT {count}u" in contract
    contract=contract.replace("COMPANION_WBA_RESOURCE_GENERATION 69u","COMPANION_WBA_RESOURCE_GENERATION 70u").replace(
        f"COMPANION_WBA_RESOURCE_STATE_COUNT {count}u",f"COMPANION_WBA_RESOURCE_STATE_COUNT {count+1}u").replace(profile["resourceId"],identity)
    (out/"companion_wba_resource_contract.h").write_text(contract,encoding="utf8",newline="\n")
    (out/"ui-partition.bin").write_bytes(new_bank)
    (out/"dizzy-frame.bin").write_bytes(frame)
    addition=dict(schema="companion.wba.generated-pet-state.v1",generation=70,sourceGeneration=69,
        state=STATE,artSource=str(art),artSha256=sha(art.read_bytes()),frameSha256=sha(frame),
        stateHash=h,payloadOffset=new_offset,payloadBytes=len(packed),payloadCrc32=zlib.crc32(packed),
        oldStateCount=count,newStateCount=count+1,oldStatesPreserved=True,cempUnchanged=True,
        originalAtlasBytesPreserved=True,payloadRelocationBytes=24,atlasRelocationBytes=24,
        resourceArenaUsedBytes=used,arenaFreeBytes=geo["rootA"]-used,geometry=geo,
        imageSha256=sha(new_bank),productionFaceChangedOnlyFor="matching SHAKE first expressive peak",
        physicalQualified=False,testsRun=False)
    external=copy.deepcopy(old_atlas);external["extensionOffset"]=ao+24
    external["headerSha256"]=sha((out/"companion_wba_external_ui.h").read_bytes())
    external.update(generation=70,newBankSha256=sha(new_bank),arenaFreeBytes=geo["rootA"]-used,
        cempAndOriginalManifestUnchanged=False,originalStatePixelsUnchanged=True,
        originalManifestReindexedWithOffsets=True,atlasRelocationBytes=24)
    for key in ("addedOffset",):
        if key in external:external[key]+=24
    profile.update(generation=70,resourceId=identity,uiPartitionSha256=sha(new_bank).upper(),
        resourceArenaUsedBytes=used,stateCount=count+1,generationBytes=len(blob),
        generationPatchBytes=profile["generationPatchBytes"]+len(packed),
        externalUi=external,generatedDizzy=addition,hardwareAcceptance="NOT_RUN",fullChainAcceptance="NOT_RUN",
        result="RESOURCE_CANDIDATE_BUILT")
    for p in [Path(__file__),art,out/"companion_wba_external_ui.h",out/"companion_wba_resource_contract.h"]:
        profile["sourceSha256"][p.relative_to(ROOT).as_posix()]=sha(p.read_bytes()).upper()
    (out/"profile.json").write_text(json.dumps(profile,ensure_ascii=False,indent=2)+"\n",encoding="utf8")
    (out/"dizzy-state.json").write_text(json.dumps(addition,ensure_ascii=False,indent=2)+"\n",encoding="utf8")
    return addition
if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__);p.add_argument("--base",type=Path,required=True)
    p.add_argument("--art",type=Path,required=True);p.add_argument("--output",type=Path,required=True)
    a=p.parse_args();print(json.dumps(generate(a.base.resolve(),a.art.resolve(),a.output.resolve()),ensure_ascii=False))
