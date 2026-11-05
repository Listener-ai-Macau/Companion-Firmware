"""Replace a matched same-geometry development static bank in one API session.

Caller owns the board lease, normal-idle qualification and exact app/NVM
preimage. Only changed static sectors may be erased. No layout formatting or
dynamic/recording address is written. Import has no probe or loader effects.
"""
import hashlib,json,os,tempfile
from migrate_wba_static_ui import NOR,SECTOR,open_loader,remove_loader
from wba_resource_geometry import geometry

sha=lambda b:hashlib.sha256(b).hexdigest()
def write_json(path,value):
 fd,tmp=tempfile.mkstemp(prefix=path.name+'.',dir=path.parent)
 try:
  with os.fdopen(fd,'wb') as stream:
   stream.write((json.dumps(value,ensure_ascii=False,indent=2)+'\n').encode());stream.flush();os.fsync(stream.fileno())
  os.replace(tmp,path)
 finally:
  if os.path.exists(tmp):os.unlink(tmp)
def update(probe,out,lease,old_bank,new_bank,state,loader_path):
 assert len(old_bank)==len(new_bank)
 geo=geometry(len(old_bank));pages=[at for at in range(0,len(old_bank),SECTOR)
  if old_bank[at:at+SECTOR]!=new_bank[at:at+SECTOR]]
 assert pages and len(pages)<=4 and all(at+SECTOR<=geo['dynamicBase'] for at in pages)
 # The caller supplies an exact old bank; candidate only appends pixels before
 # the roots. This is not permission for an arbitrary static-area replacement.
 assert old_bank[:892952]==new_bank[:892952] and len(old_bank)==905216
 name=open_loader(probe,out,loader_path);state['externalLoaderEntered']=True;touched=[]
 try:
  actual=bytearray()
  for at in range(0,len(old_bank),65536):
   lease();n=min(65536,len(old_bank)-at)
   actual.extend(probe.read(NOR+at,n,f'private-before-ui-{at:x}.bin'))
  assert bytes(actual)==old_bank,'Actual static bank differs; no sector erased'
  state.update(staticPreimageVerified=True,staticBeforeSha256=sha(actual),staticGeometry=geo,
   staticChangedSectorOffsets=pages,dynamicWrites=0,recordingWrites=0)
  write_json(out/'result.json',state);readback=bytearray(actual)
  for at in pages:
   lease();p=out/f'private-target-ui-{at:x}.bin';p.write_bytes(new_bank[at:at+SECTOR])
   state['norWritesStarted']=True;touched.append(at);write_json(out/'result.json',state)
   probe.checked(probe.api.downloadFile(str(p),NOR+at,0,1,None),'matched static sector erase/write/verify')
   got=probe.read(NOR+at,SECTOR,f'private-after-ui-{at:x}.bin')
   assert got==new_bank[at:at+SECTOR],('Static sector readback differs',at)
   readback[at:at+SECTOR]=got
   state.setdefault('staticVerifiedSectorOffsets',[]).append(at);write_json(out/'result.json',state)
   print('MATCHED_STATIC_SECTOR_VERIFIED',hex(at),flush=True)
  assert bytes(readback)==new_bank
  state.update(staticResourceReadback=True,staticResourceSha256=sha(readback),
   staticReadbackMethod='One full exact preimage + every changed static sector readback; unchanged sectors never erased',
   dynamicGeometryChanged=False)
  write_json(out/'result.json',state)
  return bytes(actual),pages
 except BaseException:
  # One bounded restoration of this operation's own changed sectors. No new
  # install attempt, reset-mode switch or recording/setting media formatting.
  if touched:
   try:
    for at in touched:
     lease();p=out/f'private-original-ui-{at:x}.bin';p.write_bytes(old_bank[at:at+SECTOR])
     probe.checked(probe.api.downloadFile(str(p),NOR+at,0,1,None),'restore own incomplete static-sector write')
     assert probe.read(NOR+at,SECTOR,f'private-restored-ui-{at:x}.bin')==old_bank[at:at+SECTOR]
    state['failedStaticUpdateRestored']=True
   except BaseException as error:state['failedStaticRestoreError']=repr(error)
   write_json(out/'result.json',state)
  raise
 finally:remove_loader(probe,name)
