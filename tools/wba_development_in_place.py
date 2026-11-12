"""Explicit lost-development-key service install when no CUP staging gap fits.

Uses the existing signed CUP/current-record format. No NOR payload allocation,
recording move, audio read, format or new firmware recovery mechanism.
"""
import struct,zlib
from cryptography.exceptions import InvalidSignature
from migrate_wba_static_ui import external_read
from wba_nor_initial import TARGET,require,verify_cup,sha

def install(probe,out,package,info,system,old_boot,new_boot,previous_xy,current_version,execute,state,save):
    static=info['staticBytes'];nor=0x90000000
    require(system[0x5000:0x6000]==b'\xff'*4096,'An existing pending install must finish first')
    ui=external_read(probe,nor,static,'public-ui-before.bin')
    app=package[176:176+info['appBytes']]
    require(ui==package[176+info['appBytes']:],'In-place service requires exactly unchanged installed UI')
    headers=[]
    for bank in (0x2000,0x3000):
        p=system[bank:bank+192]
        if p[:8]!=b'SCU3\x03\x00\xc0\x00' or struct.unpack_from('<I',p,188)[0]!=zlib.crc32(p[:188]):continue
        h=p[12:188];fw=struct.unpack_from('<I',h,16)[0]
        n,ui_n,extent,address=struct.unpack_from('<4I',h,160)
        if fw==current_version and address==TARGET.app_address and ui_n==extent==static and 8<=n<=TARGET.app_bytes:
            headers.append((bank,h,n))
    require(bool(headers),'No matching existing signed current descriptor')
    old_n=headers[-1][2]
    extent=(max(old_n,len(app))+TARGET.flash_page_bytes-1)//TARGET.flash_page_bytes*TARGET.flash_page_bytes
    require(extent<=TARGET.app_bytes,'In-place internal extent exceeds App slot')
    old_app=probe.read(TARGET.app_address,extent,'original-app-pages.bin')
    matched=[]
    for bank,h,n in headers:
        try:r=verify_cup(h+old_app[:n]+ui,previous_xy,TARGET)
        except (ValueError,InvalidSignature):continue
        if r['firmware']==current_version:matched.append(bank)
    require(bool(matched),'Actual old App/UI do not match their established signed receipt')
    target_bank=0x3000 if matched[-1]==0x2000 else 0x2000
    current=bytearray(192);current[:5]=b'SCU3\x03';struct.pack_into('<H',current,6,192)
    current[12:188]=package[:176];struct.pack_into('<I',current,188,zlib.crc32(current[:188]))
    sector=bytes(current).ljust(4096,b'\xff')
    state.update(stagingPolicy='EXPLICIT_DEVELOPMENT_IN_PLACE_NO_ARENA',oldSignedImageVerified=True,
        existingUiExact=True,originalAppPagesSha256=sha(old_app),inPlacePrepared=True,
        currentRecordRelativeOffset=target_bank,originalAudioReads=0,originalAudioWrites=0)
    save(out/'result.json',state)
    if not execute:return
    app_path=out/'signed-new-app.bin';app_path.write_bytes(app)
    boot_path=out/'signed-new-boot.bin';boot_path.write_bytes(new_boot)
    current_path=out/'signed-current-sector.bin';current_path.write_bytes(sector)
    old_sector=out/'original-current-sector.bin';old_sector.write_bytes(system[target_bank:target_bank+4096])
    state['writesStarted']=True;save(out/'result.json',state)
    published=False
    try:
        probe.checked(probe.api.downloadFile(str(app_path),TARGET.app_address,0,1,None),'authorized development App replacement')
        require(probe.read(TARGET.app_address,len(app),'new-app-readback.bin')==app,'New signed App readback differs')
        probe.checked(probe.api.downloadFile(str(boot_path),TARGET.flash_base,0,1,None),'authorized development Boot trust replacement')
        require(probe.read(TARGET.flash_base,TARGET.boot_bytes,'new-boot-readback.bin')==new_boot.ljust(TARGET.boot_bytes,b'\xff'),'New Boot readback differs')
        published=True
        probe.checked(probe.api.downloadFile(str(current_path),nor+static+target_bank,0,1,None),'publish exact signed current record')
        expected=bytearray(system);expected[target_bank:target_bank+4096]=sector
        require(external_read(probe,nor+static,len(system),'private-system-after-in-place.bin')==expected,'Unrelated system/recording/bond metadata changed')
        state.update(inPlaceCompleted=True,boardTrustChanged=True,bootWrites=1,hostInternalFlashWrites=2,
            currentReceiptPublished=True,pairingAndRecordingMetadataPreserved=True,result='DEVELOPMENT_IN_PLACE_SIGNED_IMAGES_VERIFIED_BEFORE_RESET')
        save(out/'result.json',state)
    except Exception:
        # Restore exact original pages, not a synthesized rescue firmware.
        if published:probe.checked(probe.api.downloadFile(str(old_sector),nor+static+target_bank,0,1,None),'restore original current record')
        probe.checked(probe.api.downloadFile(str(out/'original-app-pages.bin'),TARGET.app_address,0,1,None),'restore original App pages')
        probe.checked(probe.api.downloadFile(str(out/'resident-boot-before.bin'),TARGET.flash_base,0,1,None),'restore original Boot')
        require(probe.read(TARGET.flash_base,TARGET.boot_bytes,'restored-boot-readback.bin')==old_boot,'Old Boot rollback differs')
        require(probe.read(TARGET.app_address,extent,'restored-app-readback.bin')==old_app,'Old App rollback differs')
        state['originalImagesRestored']=True;save(out/'result.json',state)
        raise
