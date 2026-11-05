from pathlib import Path
import subprocess,json,sys,re
root=Path('C:/Users/Billy/Desktop/Denzic/Companion/firmware-recovery')
sdk=Path('C:/Users/Billy/Desktop/Denzic/Companion/Companion-Firmware/.cache/deps/STM32CubeWBA')
sys.path.insert(0,str(root/'tools'))
from build_wba_v11 import INCLUDES,PLATFORM
from wba_ble_target import configuration
out=root/'.cache/capture-feedback-arm-r6';out.mkdir(exist_ok=False)
ble,_,_=configuration(sdk,PLATFORM)
includes=[out,*INCLUDES,root/'app/companion_pendant/gatt',root/'app/companion_pendant/diag_log',*ble,sdk/'Drivers/STM32WBAxx_HAL_Driver/Inc',sdk/'Drivers/CMSIS/Include',sdk/'Drivers/CMSIS/Device/ST/STM32WBAxx/Include']
flags=['-std=c11','-Os','-g0','-mcpu=cortex-m33','-mthumb','-mfpu=fpv5-sp-d16','-mfloat-abi=hard','-ffunction-sections','-fdata-sections','-fstack-usage','-Wall','-Wextra','-Werror','-fmax-errors=6',
 '-DSTM32WBA55xx','-DUSE_HAL_DRIVER','-DCOMPANION_WBA_BLE_LINKED=1','-DCOMPANION_WBA_SCREEN_ENABLED=0',
 '-DCOMP_V11_PANEL_PASSIVE_TRACE=1','-DCOMPANION_WBA_AUTOMATIC_STOP1=1',
 '-DCOMPANION_WBA_RESOURCE_PROFILE=1','-DCOMPANION_SCREEN_COMP_REQ_638_SOURCE_PACK=1',
 '-DCOMPANION_WBA_UI_EXTERNAL=1','-DCOMPANION_WBA_RECORDING_UI_PACKED=1',
 '-DCOMP_WBA_INTERNAL_FLASH_KIB=512u','-DCOMP_WBA_BOOT_FLASH_KIB=24u','-DCOMP_WBA_INTERNAL_NVM_KIB=0u',
 '-DCOMP_WBA_NOR_UI_BYTES=950272u','-DCOMP_WBA_NOR_TOTAL_BYTES=25165824u',
 *(f'-I{p}' for p in includes)]
commands=[];results={}
for name in ['product_app','main']:
 original=subprocess.check_output(['git','show','9479bbf4:platform/stm32wba55_companion_v11/'+name+'.c'],cwd=root)
 old=out/(name+'-before.c');old.write_bytes(original)
 for variant,source in [('before',old),('after',PLATFORM/(name+'.c'))]:
  obj=out/(name+'-'+variant+'.o')
  cmd=['arm-none-eabi-gcc',*flags,'-c',str(source),'-o',str(obj)];commands.append(cmd)
  r=subprocess.run(cmd,capture_output=True,text=True)
  (out/(name+'-'+variant+'.log')).write_text(r.stdout+r.stderr,encoding='utf8')
  if r.returncode:print((r.stdout+r.stderr)[-4500:]);raise SystemExit(r.returncode)
  size=subprocess.check_output(['arm-none-eabi-size','-A',str(obj)],text=True)
  (out/(name+'-'+variant+'-size.txt')).write_text(size)
  sections={m[1]:int(m[2]) for m in re.finditer(r'^(\S+)\s+(\d+)\s+\d+\s*$',size,re.M)}
  results[name+'_'+variant]={
   'textAndReadOnly':sum(n for k,n in sections.items() if k.startswith(('.text','.rodata'))),
   'staticRam':sum(n for k,n in sections.items() if k.startswith(('.data','.bss'))),
  }
  if name=='product_app' and variant=='after':
   nm=subprocess.check_output(['arm-none-eabi-nm','-S','--radix=d',str(obj)],text=True)
   line=next(x for x in nm.splitlines() if x.endswith(' comp_v11_product_capture_feedback'))
   results['feedbackFunctionBytes']=int(line.split()[1])
   su=obj.with_suffix('.su').read_text()
   results['feedbackLocalStack']=next(x for x in su.splitlines() if 'comp_v11_product_capture_feedback\t' in x)
for name in ['product_app','main']:
 results[name+'_delta']={k:results[name+'_after'][k]-v for k,v in results[name+'_before'].items()}
results.update(result='PASS_CHANGED_UNITS_ARM_COMPILE_NOT_FULL_IMAGE',scope='Pinned actual ST WBA55 headers/HAL/BLE includes. Non-LTO per-unit object comparison; not final firmware size, complete link, runtime stack peak, hardware LED or installed firmware.',persistentFeedbackStateBytes=0)
(out/'commands.json').write_text(json.dumps(commands,indent=2))
(out/'result.json').write_text(json.dumps(results,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(results,ensure_ascii=False))
