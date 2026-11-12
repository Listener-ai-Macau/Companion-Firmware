"""App-only service regression with real signed packages and simulated flash I/O."""
from pathlib import Path
import argparse,json,struct,zlib
import wba_development_in_place as service
from wba_nor_initial import TARGET,verify_cup,sha
def main():
 p=argparse.ArgumentParser();p.add_argument("--current-package",type=Path,required=True);p.add_argument("--candidate-package",type=Path,required=True);p.add_argument("--public-key",type=Path,required=True);p.add_argument("--boot",type=Path,required=True);p.add_argument("--output",type=Path,required=True);a=p.parse_args()
 a.output.mkdir(parents=True,exist_ok=False)
 old=a.current_package.read_bytes();new=a.candidate_package.read_bytes();xy=a.public_key.read_bytes()
 oi=verify_cup(old,xy,TARGET,sha(xy));ni=verify_cup(new,xy,TARGET,sha(xy))
 static=ni["staticBytes"];base=0x90000000
 old_app=old[176:176+oi["appBytes"]];ui=old[176+oi["appBytes"]:]
 boot=a.boot.read_bytes().ljust(TARGET.boot_bytes,b"\xff")
 assert ui==new[176+ni["appBytes"]:] and len(boot)==TARGET.boot_bytes
 system=bytearray(b"\xff"*131072)
 current=bytearray(192);current[:5]=b"SCU3\x03";struct.pack_into("<H",current,6,192);current[12:188]=old[:176];struct.pack_into("<I",current,188,zlib.crc32(current[:188]));system[0x2000:0x2000+192]=current
 system[0x14000:0x14020]=b"ORIGINAL_CATALOG_NOT_AUDIO".ljust(32,b"!")
 system[0xc000:0xc020]=b"ORIGINAL_PAIRING_METADATA".ljust(32,b"!")
 outcomes=[]
 for failure in [False,True]:
  out=a.output/("publication-failure"if failure else"success");out.mkdir()
  flash=bytearray(b"\xff"*TARGET.flash_bytes);flash[:len(boot)]=boot
  offset=TARGET.app_address-TARGET.flash_base;flash[offset:offset+len(old_app)]=old_app
  nor=bytearray(ui+system);writes=[];failed=False
  class Probe:
   def __init__(self):self.api=self
   @staticmethod
   def checked(status,label):assert status==0,label
   def read(self,address,n,label):
    data=bytes(flash[address-TARGET.flash_base:address-TARGET.flash_base+n])if address<base else bytes(nor[address-base:address-base+n])
    assert len(data)==n;(out/label).write_bytes(data);return data
   def downloadFile(self,path,address,*args):
    nonlocal failed
    writes.append(address);data=Path(path).read_bytes()
    if failure and address==base+static+0x3000 and not failed:failed=True;return -10
    array=flash if address<base else nor
    at=address-(TARGET.flash_base if address<base else base);array[at:at+len(data)]=data;return 0
  probe=Probe();(out/"resident-boot-before.bin").write_bytes(boot)
  original=service.external_read;service.external_read=lambda p,addr,n,label:p.read(addr,n,label)
  state={};save=lambda path,d:path.write_text(json.dumps(d,indent=2)+"\n",encoding="utf-8")
  try:
   service.install(probe,out,new,ni,bytes(system),boot,None,xy,oi["firmware"],True,state,save)
   assert not failure and state["inPlaceCompleted"] and state["bootWrites"]==0 and not state["boardTrustChanged"]
   assert bytes(flash[offset:offset+ni["appBytes"]])==new[176:176+ni["appBytes"]]
  except AssertionError:
   assert failure and state.get("originalImagesRestored")
   assert bytes(flash[offset:offset+len(old_app)])==old_app
   assert bytes(nor[static:])==bytes(system)
  finally:service.external_read=original
  assert bytes(flash[:len(boot)])==boot and TARGET.flash_base not in writes
  after=bytes(nor[static:]);assert after[:0x3000]==bytes(system[:0x3000]) and after[0x4000:]==bytes(system[0x4000:])
  outcomes.append({"case":"rollback"if failure else"install","bootWrites":0,"unrelatedMetadataPreserved":True,"appRestored":bool(state.get("originalImagesRestored"))})
 result={"result":"PASS_REAL_SIGNATURES_SIMULATED_APP_ONLY_SERVICE_AND_ROLLBACK","cases":outcomes,"hardwareAccess":False}
 (a.output/"result.json").write_text(json.dumps(result,indent=2)+"\n",encoding="utf-8");print(json.dumps(result))
if __name__=="__main__":main()
