#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, json, subprocess
from pathlib import Path
from wba_flash_geometry import MCUS, for_mcu, SOURCE as GEOMETRY_SOURCE, HEADER as GEOMETRY_HEADER
from wba_resource_geometry import geometry as resource_geometry

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'.cache/wba-update-storage-confirm-host'

def main()->int:
    global OUT
    parser=argparse.ArgumentParser(description='Host-only installed-image confirmation for selected CE/CG geometry')
    parser.add_argument('--mcu',choices=MCUS,default='STM32WBA55CEU6')
    parser.add_argument('--output',type=Path)
    parser.add_argument('--ui-resource-bytes',type=lambda s:int(s,0),default=0x100000)
    args=parser.parse_args();geometry=for_mcu(args.mcu)
    nor_geometry=resource_geometry(args.ui_resource_bytes)
    if args.output:OUT=args.output.resolve()
    OUT.mkdir(parents=True,exist_ok=True)
    vcvars=Path(r'C:/Program Files (x86)/Microsoft Visual Studio/2022/BuildTools/VC/Auxiliary/Build/vcvars64.bat')
    app=ROOT/'app/companion_pendant/update'; platform=ROOT/'platform/stm32wba55_companion_v11'
    includes=[platform,platform/'tests/update_fakes',app,ROOT/'app/companion_pendant/storage',ROOT/'third_party/denzic-platform/ota/embedded/c/include']
    sources=[platform/'tests/test_update_storage_confirm.c',platform/'update_storage.c',
             app/'wba_update_metadata.c',app/'wba_boot_installer.c',app/'wba_update_service.c',
             app/'wba_update_manifest_wire.c',ROOT/'app/companion_pendant/storage/wba_workspace_layout.c',
             ROOT/'third_party/denzic-platform/ota/embedded/c/src/denzic_ota_v1.c']
    exe=OUT/'test_wba_update_storage_confirm.exe';cmd=OUT/'build.cmd'
    args=f'/DCOMP_WBA_INTERNAL_FLASH_KIB={geometry.flash_kib}u /DCOMP_WBA_NOR_UI_BYTES={nor_geometry["staticBytes"]}u '+' '.join(f'/I"{x}"' for x in includes)+' '+' '.join(f'"{x}"' for x in sources)
    cmd.write_text(f'@echo off\ncall "{vcvars}" amd64 >nul\ncl.exe /nologo /std:c11 /W4 /WX /wd4295 /utf-8 {args} /Fe:"{exe}"\n',encoding='utf-8')
    built=subprocess.run(['cmd.exe','/d','/c',str(cmd)],cwd=OUT,text=True,capture_output=True)
    if built.returncode: raise RuntimeError(built.stdout+built.stderr)
    ran=subprocess.run([str(exe)],cwd=OUT,text=True,capture_output=True)
    if ran.returncode or not ran.stdout.startswith('PASS_WBA_UPDATE_STORAGE_CONFIRM'):raise RuntimeError(ran.stdout+ran.stderr)
    tracked=[*sources,platform/'update_storage.h',platform/'tests/update_fakes/stm32wbaxx_hal.h',
             platform/'tests/update_fakes/stm32wbaxx_hal_pka.h',GEOMETRY_SOURCE,GEOMETRY_HEADER,
             app/'wba_update_service.h',app/'wba_boot_installer.h',app/'wba_storage_layout.h',
             ROOT/'app/companion_pendant/storage/wba_workspace_layout.h',Path(__file__),Path(__file__).with_name('wba_resource_geometry.py')]
    result={'schema':'companion.wba.update-storage-confirm.host.v1','result':'PASS','mcu':geometry.mcu,'internal_flash_geometry':geometry.receipt(),
            'flash_geometry':nor_geometry,
            'host_only':True,'hardwareAcceptance':'NOT_RUN','fullChainAcceptance':'NOT_RUN',
            'actual_running_hash':True,'mismatch_unconfirmed':True,'persisted_version_floors':True,'output':ran.stdout.strip(),
            'sources':{str(p.relative_to(ROOT)).replace('\\','/'):hashlib.sha256(p.read_bytes()).hexdigest() for p in tracked}}
    (OUT/'result.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8');print(ran.stdout.strip());print(OUT/'result.json');return 0

if __name__=='__main__':raise SystemExit(main())
