"""Transport one complete signed CUP to resident Boot over the fixed V3.

This is maintenance transport for an application unable to accept OTA BEGIN.
It never writes internal Flash, UI, a current receipt, bonds, or audio. The
resident Boot alone validates and installs the package. No operation on import.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import re
import struct
import subprocess
import time
import zlib

from cube_programmer_api_session import Session
from migrate_wba_static_ui import external_read, remove_loader
from provision_wba_v11 import validate_identity
from wba_factory_writer import open_bound_loader, validate_writer
from wba_nor_initial import TARGET, require, verify_cup

PROJECT = Path('C:/Users/Billy/Desktop/Denzic/Companion')
UID = '120011000d50335754363720'
PROBE = '004400403532510B31333430'
NOR = 0x90000000
TOTAL = 16777216

def sha(b): return hashlib.sha256(b).hexdigest()
def save(path, data): path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

def uart(path, seconds=12, query=True):
    import serial
    s=serial.Serial(port=None,baudrate=115200,timeout=.1,write_timeout=1)
    s.dtr=False;s.rts=False;s.port='COM9';raw=bytearray()
    try:
        s.open()
        if query:s.write(b'?');s.flush()
        until=time.monotonic()+seconds
        while time.monotonic()<until:raw.extend(s.read(8192))
    finally:s.close();path.write_bytes(raw)
    return bytes(raw)

def sections(raw):
    result={}
    for line in raw.decode(errors='replace').splitlines():
        m=re.match(r'DIAG1 (ID|STORAGE|AUDIO|BLE) (.+)',line)
        if m:result[m[1]]=dict(re.findall(r'(\w+)=([^\s]+)',m[2]))
    return result

def check_idle(raw, version):
    d=sections(raw)
    require(all(k in d for k in ('ID','STORAGE','AUDIO','BLE')),'No complete normal UART reply')
    require(d['ID']['uid']==UID and int(d['ID']['fw'],16)==version and int(d['ID']['ui'])==85,'Unexpected current App/UI/UID')
    require(d['STORAGE']['recording_ready']=='1' and d['STORAGE']['rec_state'] in ('1','6') and
            d['STORAGE']['erase_active']=='0' and d['AUDIO']['mic_run']=='0' and d['BLE']['linked']=='0','Application is not physically idle')
    return d

def pending_record(base,package):
    p=bytearray(196);struct.pack_into('<4sBBHII',p,0,b'SPU3',3,0,196,base,len(package))
    p[16:192]=package[:176];struct.pack_into('<I',p,192,zlib.crc32(p[:192]))
    return bytes(p)+b'\xff'*(4096-len(p))

def free_staging_base(entries, data_base, claim):
    """Use a real gap; resident Boot permits any bounded shared-arena extent."""
    cursor=data_base;gaps=[]
    for e in sorted(entries,key=lambda e:e['start']):
        start,end=e['start'],e['end']
        require(data_base<=cursor<=start<end<=TOTAL and start%4096==end%4096==0,
                'Invalid or overlapping recording ownership')
        if start-cursor>=claim:gaps.append((cursor,start))
        cursor=end
    if TOTAL-cursor>=claim:gaps.append((cursor,TOTAL))
    require(bool(gaps),'No contiguous free extent can hold the signed package')
    base=gaps[-1][1]-claim
    require(all(base+claim<=e['start'] or base>=e['end'] for e in entries),'Candidate staging overlaps an original')
    return base

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--build',type=Path,required=True)
    ap.add_argument('--package',type=Path,required=True)
    ap.add_argument('--loader-directory',type=Path,required=True)
    ap.add_argument('--inspector',type=Path,required=True)
    ap.add_argument('--current-version',type=int,required=True)
    ap.add_argument('--output',type=Path,required=True)
    ap.add_argument('--execute',action='store_true',help='Stage full signed package, publish pending, then let original Boot install')
    ap.add_argument('--inspect-device',action='store_true',help='Read only metadata through fixed V3, then reset original application')
    ap.add_argument('--replace-development-boot',type=Path,help='Explicit lost-development-key recovery: matched Boot build directory; changes board trust, not ordinary OTA')
    ap.add_argument('--development-in-place',action='store_true',help='Explicit authorized development service: unchanged UI, signed App/Boot/current record; no recording arena needed')
    ap.add_argument('--previous-public-key',type=Path,help='Original installed raw public key, required with development Boot replacement')
    a=ap.parse_args();out=a.output.resolve();out.mkdir(parents=True,exist_ok=False)
    package=a.package.read_bytes();build=json.loads((a.build/'result.json').read_bytes())
    xy=bytes(int(x,16) for x in re.findall(r'0x([0-9a-fA-F]{2})',(a.build/'wba_update_trust_anchor.h').read_text()))
    require(not a.development_in_place or a.replace_development_boot,'In-place service requires explicit development Boot replacement')
    replacement=None;replacement_report=None;previous_xy=None
    if a.replace_development_boot:
        require(a.previous_public_key is not None,'Lost development key recovery must identify the old trust anchor')
        replacement_report=json.loads((a.replace_development_boot/'result.json').read_bytes())
        replacement=Path(replacement_report['bin']).read_bytes();previous_xy=a.previous_public_key.read_bytes()
        require(len(previous_xy)==64 and previous_xy!=xy and replacement_report['result']=='PASS' and
                replacement_report['key_id']==build['update_trust_anchor']['key_id'] and
                replacement_report['public_key_sha256']==sha(xy) and sha(replacement)==replacement_report['bin_sha256'] and
                replacement_report['internal_flash_geometry']==build['internal_flash_geometry'] and
                replacement_report['firmware_version']==a.current_version and
                8<=len(replacement)<=TARGET.boot_bytes and xy in replacement,
                'Replacement Boot is not bound to this exact development package/geometry')
        manifest=json.loads((a.package.parent/'ota_manifest.json').read_bytes())
        require(manifest.get('dev_only') is True,'This recovery is only for the explicit development signing key')
    info=verify_cup(package,xy,TARGET,sha(xy)) if replacement else verify_cup(package,xy,TARGET)
    static=info['staticBytes'];data_base=static+131072
    require(static==950272 and info['ui']==85 and info['firmware']==build['firmware_version'] and info['firmware']>a.current_version,'Only current matched UI85 maintenance update is supported')
    require(sha(package[176:176+info['appBytes']])==build['bin_sha256'],'CUP does not contain the compiled application')
    loader=a.loader_directory/'Companion_V11_WBA55_UI.stldr';lr=json.loads((a.loader_directory/'result.json').read_bytes())
    validate_writer(lr,loader.read_bytes(),static)
    # Bound the native inspector to the exact production parsers used here.
    require(a.inspector.is_file(),'Missing compiled metadata inspector')
    claim=(len(package)+4095)//4096*4096;base=TOTAL-claim
    state=dict(result='OFFLINE_SIGNED_PACKAGE_VALID',package=info,tailBase=base,tailBytes=claim,
               hostInternalFlashWrites=0,bootWrites=0,originalAudioReads=0,originalAudioWrites=0,originalReads='SYSTEM_METADATA_ONLY',
               inspectorSha256=sha(a.inspector.read_bytes()),writesStarted=False,pendingPublished=False)
    state['developmentBootReplacementPrepared']=bool(replacement)
    if replacement:state['replacementBootSha256']=sha(replacement)
    save(out/'result.json',state)
    if not(a.execute or a.inspect_device):print(json.dumps(state));return
    def lease():
        d=json.loads((PROJECT/'docs/board_turn.json').read_bytes());require(d.get('holder')=='codex','Fixed board is owned by another task')
    lease();d=check_idle(uart(out/'uart-before.log'),a.current_version)
    endpoint_sections=json.loads(json.dumps(d));endpoint_sections['BLE']['linked']=int(d['BLE']['linked'])
    save(out/'uart-preflight.json',dict(ownHandlesClosed=True,postPhysicalIdle={'sections':endpoint_sections}))
    selected=subprocess.run(['python',str(PROJECT/'tools/select_companion_transport_endpoint.py'),'--stage-result',str(out/'uart-preflight.json'),'--output',str(out/'endpoint-selection.json')],capture_output=True,text=True)
    (out/'endpoint-selection.log').write_text(selected.stdout+selected.stderr,encoding='utf-8')
    require(selected.returncode==0,'Endpoint inspection failed; no probe connection')
    freeze=None;loader_name=None
    with Session(PROBE,out,lease,connection_mode=0,access_port=1) as probe:
        try:
            uid=probe.read(0x0BF90700,12,'uid.bin')
            require(validate_identity(probe.read(0xE0044000,4,'device-id.bin'),probe.read(0x0BF907A0,2,'flash-size.bin'),probe.read(0x40022040,4,'options.bin'),uid,TARGET)==UID,'Wrong fixed target')
            freeze=int.from_bytes(probe.read(0xE0044008,4,'freeze-before.bin'),'little');probe.word(0xE0044008,freeze|(1<<12))
            boot=probe.read(TARGET.flash_base,TARGET.boot_bytes,'resident-boot-before.bin')
            require((previous_xy if replacement else xy) in boot,'Resident Boot does not contain the established trust anchor')
            state['residentBootSha256']=sha(boot)
            loader_name=open_bound_loader(probe,out,loader,lr)
            system=external_read(probe,NOR+static,131072,'private-system-before.bin')
            (out/'identity.bin').write_bytes(system[0x6000:0x8000]);(out/'catalog.bin').write_bytes(system[0x14000:0x20000])
            cp=subprocess.run([str(a.inspector),str(out/'identity.bin'),str(out/'catalog.bin'),UID,str(data_base),str(TOTAL-data_base),str(base)],capture_output=True,text=True)
            (out/'catalog-inspection.log').write_text(cp.stdout+cp.stderr,encoding='utf-8')
            require(cp.returncode==0,'Product metadata parser did not qualify a disjoint OTA tail: '+str(cp.returncode))
            state['catalog']=json.loads(cp.stdout)
            if a.development_in_place:
                from wba_development_in_place import install
                install(probe,out,package,info,system,boot,replacement,previous_xy,a.current_version,a.execute,state,save)
            else:
                base=free_staging_base(state['catalog']['entries'],data_base,claim)
                state['tailBase']=base;state['stagingPolicy']='EXISTING_UNOWNED_GAP_NO_AUDIO_MOVE'
                current=[]
                for rel in (0x2000,0x3000):
                    p=system[rel:rel+192]
                    if p[:8]==b'SCU3\x03\x00\xc0\x00' and struct.unpack_from('<I',p,188)[0]==zlib.crc32(p[:188]):
                        h=p[12:188];fw=struct.unpack_from('<I',h,16)[0];ui=struct.unpack_from('<I',h,156)[0]
                        require(struct.unpack_from('<I',h,168)[0]==static,'Live signed receipt has different static extent')
                        current.append((fw,ui))
                require(current and max(current)==(a.current_version,85),'Live signed current receipt differs from UART')
                require(system[0x5000:0x5000+196]==b'\xff'*196,'Existing pending installation must finish first')
                state['systemBeforeSha256']=sha(system);state['pairingBeforeSha256']=sha(system[0xc000:0xf000]);save(out/'result.json',state)
                if a.execute:
                    lease();state['writesStarted']=True;save(out/'result.json',state)
                    staged=out/'signed-candidate.cup';staged.write_bytes(package)
                    probe.checked(probe.api.downloadFile(str(staged),NOR+base,0,1,None),'complete signed CUP staging')
                    require(external_read(probe,NOR+base,len(package),'candidate-readback.cup')==package,'Full staged CUP readback mismatch')
                    state['candidateReadbackVerified']=True;save(out/'result.json',state)
                    # Exactly the record published by normal OTA finish_stream.
                    target=pending_record(base,package);path=out/'pending-sector.bin';path.write_bytes(target)
                    lease();probe.checked(probe.api.downloadFile(str(path),NOR+static+0x5000,0,1,None),'normal pending publication')
                    require(external_read(probe,NOR+static+0x5000,4096,'pending-readback.bin')==target,'Pending readback mismatch')
                    expected=bytearray(system);expected[0x5000:0x6000]=target
                    require(external_read(probe,NOR+static,131072,'private-system-after-stage.bin')==expected,'Unrelated system metadata changed')
                    state['pendingPublished']=True;state['pairingAndRecordingMetadataPreserved']=True
                    state['result']='SIGNED_PACKAGE_STAGED_FOR_RESIDENT_BOOT';save(out/'result.json',state)
                    if replacement:
                        # Only after the signed payload and normal pending record
                        # are durable: replace the 24KiB Boot prefix, never App,
                        # audio, bonds or current receipts. Resident Boot still
                        # performs the signed application installation itself.
                        lease();boot_path=Path(replacement_report['bin'])
                        state['bootWriteStarted']=True;save(out/'result.json',state)
                        try:
                            probe.checked(probe.api.downloadFile(str(boot_path),TARGET.flash_base,0,1,None),'explicit development Boot trust replacement')
                            observed_boot=probe.read(TARGET.flash_base,TARGET.boot_bytes,'resident-boot-after.bin')
                            require(observed_boot==replacement+b'\xff'*(TARGET.boot_bytes-len(replacement)),'Replacement Boot readback differs')
                        except Exception:
                            # Reversible service operation: restore the exact old
                            # prefix before allowing its normal reset on failure.
                            previous_boot=out/'resident-boot-before.bin'
                            probe.checked(probe.api.downloadFile(str(previous_boot),TARGET.flash_base,0,1,None),'restore original development Boot after failed replacement')
                            require(probe.read(TARGET.flash_base,TARGET.boot_bytes,'resident-boot-restored.bin')==boot,'Original Boot restore readback differs')
                            state['originalBootRestored']=True;save(out/'result.json',state)
                            raise
                        state['bootWrites']=1;state['hostInternalFlashWrites']=1
                        state['boardTrustChanged']=True;save(out/'result.json',state)
                else:
                    state['result']='READ_ONLY_TAIL_QUALIFIED';save(out/'result.json',state)
        finally:
            if loader_name:remove_loader(probe,loader_name)
            if freeze is not None:probe.word(0xE0044008,freeze)
            probe.reset()
    # Start from the normal application after this deliberate maintenance reset.
    time.sleep(2)
    raw=uart(out/'uart-after.log',45,False)
    expected=info['firmware'] if a.execute else a.current_version
    # Installing and verifying the complete UI can outlast the first receive
    # window. A UART query sent during resident Boot is not an App reply.
    # Continue bounded observation before declaring identity unconfirmed.
    for attempt in range(4):
        raw+=uart(out/f'uart-after-query-{attempt}.log',15)
        try:
            observed=check_idle(raw,expected)
            break
        except ValueError:
            identity=sections(raw).get('ID',{})
            if identity and (identity.get('uid')!=UID or int(identity['fw'],16)!=expected):raise
            if attempt==3:raise
    state['postPhysicalIdle']={'sections':observed}
    state['ownHandlesClosed']=True
    if a.execute:
        state['diagnosticJournalVisible']=b'DJ1 seq=' in raw
        state['result']='DEVELOPMENT_IN_PLACE_INSTALLED_AND_BOOT_VERIFIED' if a.development_in_place else ('INSTALLED_BY_ORIGINAL_BOOT' if state['diagnosticJournalVisible'] else 'INSTALLED_JOURNAL_NOT_OBSERVED')
    save(out/'result.json',state);print(json.dumps(state,ensure_ascii=False))

if __name__=='__main__':
    try:
        main()
    except Exception as error:
        # Preserve the actual boundary on failures too. In particular, a
        # quiet UART after publication is not proof of a failed installation.
        import sys
        if '--output' in sys.argv:
            path=Path(sys.argv[sys.argv.index('--output')+1])/'result.json'
            if path.is_file():
                state=json.loads(path.read_bytes())
                state['result']=('DEVELOPMENT_IN_PLACE_FAILED_ORIGINAL_RESTORED' if state.get('originalImagesRestored') else 'DEVELOPMENT_IN_PLACE_NOT_CONFIRMED') if '--development-in-place' in sys.argv else ('INSTALLATION_NOT_CONFIRMED' if state.get('pendingPublished') else 'FAILED_BEFORE_PENDING_PUBLICATION')
                state['error']=str(error);state['ownHandlesClosed']=True
                save(path,state)
        raise
