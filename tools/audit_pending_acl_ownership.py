"""Fail closed when the pinned host's pending cancellation is not interposed."""
from pathlib import Path
import re,subprocess

def inspect_elf(path:Path)->dict:
    def disassemble(name):
        return subprocess.run(['arm-none-eabi-objdump','-d','--disassemble='+name,str(path)],check=True,capture_output=True,text=True).stdout
    process=disassemble('LECTRL_Process')
    matched=re.search(r'^([0-9a-f]+) <LECTRL_Process>:',process,re.M)
    assert matched,'Original pinned Process missing'
    start=int(matched.group(1),16)
    removes=[int(m.group(1),16)-start for m in re.finditer(r'^\s*([0-9a-f]+):.*\bbl\b.*<__wrap_ACL_List_Remove>',process,re.M)]
    assert removes==[0x4e],('Pending Remove call is not the qualified wrapper/site',removes)
    assert '<LECTRL_SendAclDataToLL>' in process,'Original send implementation changed'
    top=disassemble('BleStack_Process')
    assert '<__wrap_LECTRL_Process>' in top,'Host main loop bypasses the ownership wrapper'
    wrap=disassemble('__wrap_LECTRL_Process')
    assert '<LECTRL_Process>' in wrap,'Candidate does not call real SDK Process'
    remove=disassemble('__wrap_ACL_List_Remove')
    assert '<ACL_List_Remove>' in remove,'Candidate does not call real SDK Remove'
    text='\n'.join([process,top,wrap,remove])
    (path.parent/'pending-acl-ownership-call-audit.txt').write_text(text,encoding='utf-8')
    return dict(result='PINNED_PENDING_OWNERSHIP_CALLS_BOUND',pendingRemoveOffset=0x4e,expectedReturnOffset=0x52,
        originalProcessCalled=True,originalRemoveCalled=True,hostMainProcessWrapped=True,
        limits='Call-site/archive qualification only; real abnormal disconnect, absence of repeat release and clean pool must also be validated.')
