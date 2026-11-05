"""Structural R7 host-chain gate derived from the accepted R6 host stages."""
from __future__ import annotations
import json, hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
MASTER={
 'runner':ROOT/'tools/run_wb55_ssd1681_r12_v22_calm_curious_warm_sampler_r6.ps1',
 'monitor':ROOT/'tools/monitor_wb55_ssd1681_r12_v22_calm_curious_warm_sampler_r6.ps1',
 'supervisor':ROOT/'tools/supervise_wb55_ssd1681_r12_v22_calm_curious_wARM_sampler_prompt_r6.ps1',
 'launcher':ROOT/'tools/start_wb55_ssd1681_r12_v22_calm_curious_warm_sampler_r6.ps1',
}
MASTER['supervisor']=ROOT/'tools/supervise_wb55_ssd1681_r12_v22_calm_curious_warm_sampler_prompt_r6.ps1'
TARGET={k:ROOT/f'tools/{name}' for k,name in {
 'runner':'run_wb55_ssd1681_r7_locked_v9.ps1','monitor':'monitor_wb55_ssd1681_r7_locked_v9.ps1','supervisor':'supervise_wb55_ssd1681_r7_locked_v9.ps1','launcher':'start_wb55_ssd1681_r7_locked_v9.ps1'}.items()}
HEX=ROOT/'cubeide/Companion_Nucleo_WB55RG_Bringup/build_ssd1681_r7_locked_v9_choreography/Companion_Nucleo_WB55RG_Ssd1681R7LockedV9Choreography.hex'
COMMON=('$CheckOnly',)
SPECIAL={'runner':('65536','Enter-CompanionWb55Lock','Start-BoundedSerialCapture','Invoke-ProgrammerOnce','Stop-ProcessTree','COMP-REQ-409','524288','223F6E7A7DB8E5562D0F7C34ED4F023DA7E37F5266505A6C84D5BD6FE304CD7C','$Execute'),'monitor':('65536','Write-Json','$Execute'),'supervisor':('Diagnostics.Process]::Start','Stop-ProcessTree','Write-JsonAtomic','通过','失败','$Execute'),'launcher':('Claim-R7Authorization','Start-Process','Write-JsonAtomic','-Execute')}
def check()->dict:
    result={}
    actual_hex=hashlib.sha256(HEX.read_bytes()).hexdigest().upper()
    if actual_hex!='C8E5ABBFB350462ECAAD5E87EE080E71F39252D9D92AE1B70BB928779757FC8D': raise AssertionError('actual candidate HEX hash mismatch')
    for key,path in TARGET.items():
        text=path.read_text(encoding='utf-8'); master_lines=len(MASTER[key].read_text(encoding='utf-8').splitlines())
        if len(text.splitlines()) < int(master_lines*.90): raise AssertionError(f'{key} is not R6-derived length')
        required=COMMON+SPECIAL[key]; missing=[x for x in required if x not in text]
        if missing: raise AssertionError(f'{key} missing {missing}')
        if 'physical contact is intentionally disabled' in text or 'CheckOnly-only' in text: raise AssertionError(f'{key} still has toy disabled lifecycle')
        if key=='runner' and (actual_hex not in text or any(x in text for x in ('332E7B0557D64FE99FAB07C3BB5D3A81FAEEAB156C3DA327952F107DDD65F3B0','B7892C7FBC83D07B124B3E1AEC04581C688F01D6CEB0D6F7B11667137AA5B1D4','69A153612B2330171CEA4ECBC44EC584C36A3AC75AD475732B232526EA7E0EDE'))): raise AssertionError('runner candidate hash is stale or not bound to actual HEX')
        result[key]={'target_lines':len(text.splitlines()),'master_lines':master_lines,'required_tokens':len(required)}
    stub='param([switch]$CheckOnly)\nif(-not $CheckOnly){throw "physical contact is intentionally disabled"}\nWrite-Output CHECK_ONLY'
    stub_rejected=any(x not in stub for x in ('Claim-R7Authorization','Start-BoundedSerialCapture','Invoke-ProgrammerOnce','通过','失败'))
    if not stub_rejected: raise AssertionError('15D23E stub fixture accepted')
    result['negative_current_15D23E_stub_rejected']=stub_rejected
    result['actual_candidate_hex_sha256']=actual_hex
    result['negative_stale_candidate_hash_rejected']=True
    return result
if __name__=='__main__': print(json.dumps({'status':'PASS','host_chain':check()},sort_keys=True))
