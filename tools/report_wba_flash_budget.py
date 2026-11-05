"""Bind a read-only Flash budget to exact WBA app/boot/UI build artifacts."""
from pathlib import Path
import argparse, hashlib, json, re, struct
from wba_flash_geometry import from_receipt, SOURCE as GEOMETRY_SOURCE, HEADER as GEOMETRY_HEADER

ROOT=Path(__file__).resolve().parents[1]
LAYOUT=ROOT/'app/companion_pendant/update/wba_storage_layout.h'
PLATFORM=ROOT/'platform/stm32wba55_companion_v11'

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def load(path):return json.loads(path.read_text(encoding='utf-8-sig'))
def region(name,base,size):return {'name':name,'base':base,'endExclusive':base+size,'bytes':size}
def disjoint_cover(regions,base,end):
    cursor=base
    for r in sorted(regions,key=lambda x:x['base']):
        if r['base']!=cursor or r['bytes']<=0 or r['endExclusive']>end:
            raise ValueError('Flash layout gap/overlap/range error: '+r['name'])
        cursor=r['endExclusive']
    if cursor!=end:raise ValueError('Flash layout does not account for every byte')
def linker(path):
    m=re.search(r'FLASH\s*\(rx\)\s*:\s*ORIGIN\s*=\s*(0x[0-9A-Fa-f]+),\s*LENGTH\s*=\s*(\d+)K',path.read_text())
    if not m:raise ValueError('Unsupported linker geometry: '+str(path))
    return int(m[1],16),int(m[2])*1024

def report(build,boot):
    defs={n:int(v,0) for n,v in re.findall(r'#define\s+(COMP_WBA_NOR_\w+)\s+UINT32_C\((0x[0-9A-Fa-f]+|\d+)\)',LAYOUT.read_text())}
    get=lambda suffix:defs['COMP_WBA_NOR_'+suffix]
    sector=get('SECTOR_BYTES')
    ext=[region(name,get(prefix+'_BASE'),get(prefix+'_BYTES')) for name,prefix in
         [('UI active','UI'),('Recordings','RECORDING'),('Reserved (unassigned)','RESERVED'),
          ('OTA staging (one component)','UPDATE_STAGING'),('UI rollback','RESOURCE_BACKUP'),('App rollback','FIRMWARE_BACKUP')]]
    ext += [region(name,get(prefix),sector) for name,prefix in [('Preferences A','PREFS_A'),('Preferences B','PREFS_B'),('OTA metadata A','UPDATE_META_A'),('OTA metadata B','UPDATE_META_B')]]
    if any(r['base']%sector or r['bytes']%sector for r in ext):raise ValueError('NOR partition is not erase aligned')
    disjoint_cover(ext,0,get('TOTAL_BYTES'))
    app_path=build/'companion-v11-board-bringup.bin';boot_path=boot/'companion_wba55_v11_boot.bin'
    a,b=load(build/'result.json'),load(boot/'result.json')
    geometry=from_receipt(a)
    if from_receipt(b)!=geometry:raise ValueError('App and boot target different MCU geometry')
    if a.get('result')!='PASS_PREHARDWARE_SOFTWARE_ONLY' or b.get('result')!='PASS':raise ValueError('Successful exact builds required')
    if sha(app_path)!=a['bin_sha256'] or sha(boot_path)!=b['bin_sha256']:raise ValueError('Build payload identity changed')
    app_linker=PLATFORM/(geometry.mcu+'_BLE.ld')
    geometry.validate_linker(app_linker)
    app_base,app_cap=linker(app_linker)
    boot_base,boot_cap=linker(PLATFORM/'STM32WBA55CGU6_BOOT.ld')
    total=geometry.flash_bytes;nvm_base=app_base+app_cap
    internal=[region('Resident boot',boot_base,boot_cap),region('Application + BLE',app_base,app_cap),region('ST SNVMA',nvm_base,boot_base+total-nvm_base)]
    disjoint_cover(internal,boot_base,boot_base+total)
    app_bytes=app_path.stat().st_size;boot_bytes=boot_path.stat().st_size
    if app_bytes>app_cap or boot_bytes>boot_cap:raise ValueError('Internal Flash budget exceeded')
    profile=load(ROOT/'.cache/wba-product-resources/profile.json')
    ui_path=ROOT/'.cache/wba-product-resources/ui-partition.bin';ui=ui_path.read_bytes()
    if sha(ui_path)!=profile['uiPartitionSha256'].lower() or a['ui_resource_profile']['uiPartitionSha256'].lower()!=sha(ui_path):raise ValueError('UI/app resource identity mismatch')
    if len(ui)!=get('UI_BYTES'):raise ValueError('UI partition geometry differs')
    blob_offset,blob_size=struct.unpack_from('<II',ui,0x1FE000+16)
    ui_arena_end=0x1DC000;ui_arena_used=blob_offset+blob_size
    if ui_arena_used>ui_arena_end:raise ValueError('UI arena collides with recording art')
    if len(ui)>get('UPDATE_STAGING_BYTES') or len(ui)>get('RESOURCE_BACKUP_BYTES') or app_bytes>get('UPDATE_STAGING_BYTES') or app_cap>get('FIRMWARE_BACKUP_BYTES'):
        raise ValueError('Update or rollback capacity insufficient')
    journal=ROOT/'app/companion_pendant/recording/companion_recording_journal.h'
    def j(name):return int(re.search(r'#define\s+'+name+r'\s+(\d+)u',journal.read_text())[1])
    catalog=j('COMP_RECORDING_JOURNAL_CATALOG_SECTORS')*j('COMP_RECORDING_JOURNAL_SECTOR_BYTES')
    audio_data=get('RECORDING_BYTES')-catalog
    # WBA service initializes 16 kHz / 20 ms; encoder selects fixed 16 kbps.
    audio_rate=16000//8+2*(1000//20)
    # Planning only: V1 binaries still use fixed staging and rollback bases.
    target_front_bytes=get('UI_BYTES')
    target_system_bytes=64*1024
    target_resource_bytes=target_front_bytes-target_system_bytes
    target_working_metadata_bytes=64*1024
    target_working_bytes=get('TOTAL_BYTES')-target_front_bytes
    pool_data=target_working_bytes-target_working_metadata_bytes
    pool_segments=[region('Working payload pool',target_front_bytes+target_working_metadata_bytes,pool_data)]
    target_regions=[region('Signed resource sub-partition',0,target_resource_bytes),
                    region('Low-frequency system metadata',target_resource_bytes,target_system_bytes),
                    region('Working metadata',target_front_bytes,target_working_metadata_bytes),*pool_segments]
    disjoint_cover(target_regions,0,get('TOTAL_BYTES'))
    target_arena_end=ui_arena_end-target_system_bytes
    if ui_arena_used>target_arena_end:raise ValueError('V2 resource repacking budget insufficient')
    aligned=lambda n:((n+sector-1)//sector)*sector
    reservations=[('noUpdateGuarantee',0),('currentAppOnly',2*aligned(app_bytes)),
                  ('maximumAppOnly',2*aligned(app_cap)),('uiOnly',2*target_resource_bytes),
                  ('atomicAppAndUiMaximum',2*(aligned(app_cap)+target_resource_bytes))]
    shared_scenarios=[]
    for name,reserved in reservations:
        left=pool_data-reserved
        if left<12:raise ValueError('Proposed shared pool cannot fit reservation')
        shared_scenarios.append({'name':name,'pinnedUpdateBytes':reserved,'recordingPayloadBytes':left,
                                'idealEmptyPoolMinutes':round((left-12)/audio_rate/60,3),'guaranteedMinutes':None})
    warnings=[]
    if app_bytes>app_cap*0.8:warnings.append('Application exceeds 80% planning budget')
    if ui_arena_used>ui_arena_end*0.8:warnings.append('UI arena exceeds 80% planning budget')
    if a['memory']['static_gap_bytes']<8192:warnings.append('SRAM static gap is below 8 KiB; this is separate from Flash capacity, physical stack high-water remains required')
    source_paths=[LAYOUT,app_linker,PLATFORM/'STM32WBA55CGU6_BOOT.ld',GEOMETRY_SOURCE,GEOMETRY_HEADER,
                  ROOT/'tools/wba_flash_geometry.py',journal,ROOT/'docs/WBA_FLASH_PLAN.md',Path(__file__),
                  ROOT/'app/companion_pendant/epaper/ui_asset_generation.h',
                  ROOT/'tools/build_companion_recording_resources.py',ROOT/'tools/build_wba_product_resources.py',
                  ROOT/'.cache/wba-product-resources/profile.json']
    return {'schema':'companion.wba.flash-budget.v1','result':'PASS_FLASH_CAPACITY_SOFTWARE_ONLY',
      'hardwareAcceptance':'NOT_RUN','fullChainAcceptance':'NOT_RUN',
      'mcu':geometry.mcu,'internal_flash_geometry':geometry.receipt(),
      'identity':{'firmwareVersion':a['firmware_version'],'appSha256':sha(app_path),'bootSha256':sha(boot_path),'uiGeneration':profile['generation'],'uiSha256':sha(ui_path)},
      'internal':{'totalBytes':total,'regions':internal,'appUsedBytes':app_bytes,'appFreeBytes':app_cap-app_bytes,'bootUsedBytes':boot_bytes,'bootFreeBytes':boot_cap-boot_bytes},
      'external':{'chip':'W25Q128JWPIQ, 1.8 V (schematic)','totalBytes':get('TOTAL_BYTES'),'regions':sorted(ext,key=lambda x:x['base']),'unassignedBytes':get('RESERVED_BYTES'),
         'uiPackageBytes':len(ui),'uiArenaBytes':ui_arena_end,'uiArenaUsedBytes':ui_arena_used,'uiArenaFreeBytes':ui_arena_end-ui_arena_used,
         'uiBankInteriorIsNotRecordingFreeSpace':True,'stagingMode':'serial app OR UI; not a simultaneous combined-image contract'},
      'recording':{'catalogBytes':catalog,'dataBytes':audio_data,'catalogEntries':j('COMP_RECORDING_JOURNAL_MAX_ENTRIES'),'nominalCop1BytesPerSecond':audio_rate,
         'idealEmptyRegionMinutes':round((audio_data-12)/audio_rate/60,3),'guaranteedMinutes':None,
         'limits':['sector rounding and fragmentation','7 catalog entries','current allocation may shorten selected duration','no seamless segment handover yet','unacknowledged recordings are never evicted to extend capacity']},
      'proposedSharedPoolV2':{'implemented':False,'requiresVersionedMigration':True,'regions':target_regions,'segments':pool_segments,
         'lowFrequencyFrontBytes':target_front_bytes,'workingAreaBytes':target_working_bytes,'workingMetadataBudgetBytes':target_working_metadata_bytes,
         'workingMetadataBreakdownBytes':{'catalog':8192,'allocator':16384,'transferCheckpoint':8192,'logs':16384,'crash':8192,'spare':8192},
         'payloadBytesBeforeUpdateReservation':pool_data,'signedResourceBytesNotLent':target_resource_bytes,'lowFrequencySystemBytes':target_system_bytes,
         'requiresResourceFormatMigration':True,'targetUiArenaEnd':target_arena_end,'targetUiArenaFreeBytes':target_arena_end-ui_arena_used,
         'resourceTailRelocationBytes':-target_system_bytes,'replyFontBudgetFitsTargetUiArena':384*1024<=target_arena_end-ui_arena_used,
         'scenarios':shared_scenarios,'pairedAtomicUpdateImplemented':False,
         'consumptionPolicy':{'consumedAfter':'receiver durably saves complete WAV/audio and index, verifies exact encoded id/length/SHA, then board commits ACK',
             'automaticVictims':'oldest consumed completed recordings first','unconsumedVictims':'oldest completed recordings only after explicit confirmation of exact loss',
             'neverVictims':['active recording','OTA pinned candidate','OTA pinned rollback'],
             'warningAloneAuthorizesErase':False,'revalidateVictimIdentityBeforeErase':True},
         'limitations':['V1 fixed-address app and boot do not implement this pool',
             'fragmentation and sector rounding reduce usable recording capacity',
             'update must pin every required candidate and rollback extent before erase',
             'resource format, signature range, erase boundaries and factory loader must change together',
             'resource updates must exclude low-frequency settings/update metadata',
             'resource interior free bytes remain owned by the signed resource sub-partition']},
      'growthPlan':{'replyFontBudgetBytes':384*1024,'replyFontBudgetFitsCurrentUiArena':384*1024<=ui_arena_end-ui_arena_used,'replyFontImplemented':False,
         'replyTextUtf8BudgetBytes':256,'additionalReplyRamBudgetBytes':512,'reuseExistingFramebuffer':True,'onDeviceLargeModel':False,
         'reservedV1AreaRemainsUnassigned':True,'v2WorkingMetadataBudgetBytes':target_working_metadata_bytes,'reservedLayoutImplemented':False},
      'ram':a['memory'],'warnings':warnings,'sourceSha256':{str(p.relative_to(ROOT)):sha(p) for p in source_paths}}

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--build',type=Path,required=True);p.add_argument('--boot',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    args=p.parse_args();result=report(args.build.resolve(),args.boot.resolve())
    args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:result[k] for k in ('result','identity','warnings')},indent=2))
if __name__=='__main__':main()
