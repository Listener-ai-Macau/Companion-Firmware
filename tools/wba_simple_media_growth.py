"""Offline media plan for an explicitly authorized paired development install."""
import struct
import zlib
from wba_resource_geometry import geometry

def plan(old_bank,new_bank,metadata,tail):
    old,new=geometry(len(old_bank)),geometry(len(new_bank))
    assert new['staticBytes']>old['staticBytes']
    assert len(metadata)==131072 and len(tail)==len(new_bank)-len(old_bank)
    # Current signed headers may exist; a pending install must never be lost.
    assert metadata[0x5000:0x6000]==b'\xff'*4096,'Pending OTA; finish it before art migration'
    roots=[]
    for at in (0x8000,0x9000):
        r=metadata[at:at+64]
        if r[:4]==b'CFL3' and struct.unpack_from('<II',r,4)==(3,64) and struct.unpack_from('<I',r,60)[0]==zlib.crc32(r[:60]):
            assert struct.unpack_from('<5I',r,12)==(old['staticBytes'],old['dynamicBase'],old['recordingCatalog'],old['payloadBase'],old['payloadBytes'])
            roots.append(r)
    assert roots and all(r==roots[0] for r in roots),'Unknown/divergent old layout'
    root=bytearray(roots[0]);struct.pack_into('<5I',root,12,new['staticBytes'],new['dynamicBase'],new['recordingCatalog'],new['payloadBase'],new['payloadBytes']);struct.pack_into('<I',root,60,zlib.crc32(root[:60]))
    moved=bytearray(metadata)
    # Existing Owner authorization covers development recordings only. Settings,
    # the current signed headers and every other metadata byte are retained.
    cleared=[(0x6000,0x2000),(0x10000,0x2000),(0x14000,0xc000)]
    for at,n in cleared:moved[at:at+n]=b'\xff'*n
    for at in (0x8000,0x9000):moved[at:at+4096]=bytes(root).ljust(4096,b'\xff')
    protected=[i for i in range(32) if not any(at<=i*4096<at+n for at,n in cleared+[(0x8000,8192)])]
    for i in protected:assert moved[i*4096:(i+1)*4096]==metadata[i*4096:(i+1)*4096]
    before=old_bank+metadata+tail;after=new_bank+bytes(moved)
    assert len(before)==len(after)==new['payloadBase']
    return before,bytes(moved),dict(oldGeometry=old,newGeometry=new,protectedMetadataSectorIndices=protected,developerRecordingNamespaceClearPlanned=True)
