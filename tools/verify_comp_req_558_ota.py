import hashlib
import json
import subprocess
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
PIN='d311af3db60e118a6d2c6e68873b2d00f2647a96'

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()

def main():
    app_path=ROOT/'cubeide/Companion_Nucleo_WB55RG_Bringup/Core/Src/app_ble.c'
    adapter_path=ROOT/'app/companion_pendant/platform/companion_platform_adapters.c'
    app=app_path.read_text(encoding='utf-8')
    adapter=adapter_path.read_text(encoding='utf-8')
    run=subprocess.run(['pwsh','-NoProfile','-File','tools/run_comp_req_558_ota_host.ps1'],cwd=ROOT,text=True,capture_output=True)
    result_path=ROOT/'.cache/validation/comp-req-558-ota-host/result.json'
    result=json.loads(result_path.read_text()) if result_path.exists() else {}
    pin=subprocess.run(['git','ls-tree','HEAD','third_party/denzic-platform'],cwd=ROOT,text=True,capture_output=True).stdout.strip()
    checks={
        'platform_pin':pin.endswith(PIN+'\tthird_party/denzic-platform'),
        'loader_candidate_entry':'Companion_Ota_V1_ReadCandidate' in app,
        'stm32_manifest':'stm32wb_resident_bootloader_pending_verify' in adapter,
        'esp_identity_distinct':'COMPANION_OTA_TARGET_ESP' in (ROOT/'app/companion_pendant/platform/companion_platform_adapters.h').read_text(),
        'runner_pass':run.returncode==0 and result.get('status')=='PASS',
        'negative_trace':all(x in result.get('stdout','') for x in ('stale_offset','out_of_order','malformed_control','truncated_data','capacity_overflow','transport_loss','abort_cleanup')),
        'bounded_no_apply':all(x in result.get('stdout','') for x in ('apply=0','flash=0','reset=0')),
    }
    artifact={'schema':'companion.comp_req_558.ota_gate.v1','status':'PASS' if all(checks.values()) else 'NO_GO','head':subprocess.run(['git','rev-parse','HEAD'],cwd=ROOT,text=True,capture_output=True).stdout.strip(),'platform_pin':PIN,'checks':checks,'runner':result,'source_sha256':{'app_ble':sha(app_path),'platform_adapters':sha(adapter_path)},'physical_gate':'CLOSED_UNPROVEN','side_effects':{'hardware':0,'flash':0,'reset':0,'ota_apply':0,'push':0}}
    out=ROOT/'.cache/validation/comp-req-558-ota.json';out.write_text(json.dumps(artifact,indent=2,sort_keys=True)+'\n');print(json.dumps(artifact,indent=2));return 0 if artifact['status']=='PASS' else 2

if __name__=='__main__':
    raise SystemExit(main())
