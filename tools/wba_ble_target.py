"""Resolve the pinned ST WBA55 BLE dependency graph, without Nucleo pin code."""
from pathlib import Path
import re
import xml.etree.ElementTree as ET

WPAN_COMMIT = '7e764835982f0a8b94fdd6b2b056d6e0afc4d1ba'

def configuration(sdk: Path, platform: Path, experimental_stop1=False):
    project = sdk / 'Projects/NUCLEO-WBA55CG/Applications/BLE/BLE_p2pServer/STM32CubeIDE'
    overlay = platform / 'ble'
    includes = [overlay]
    xml = ET.parse(project / '.cproject')
    for element in xml.findall('.//option'):
        if element.attrib.get('valueType') == 'includePath':
            for entry in element.findall('listOptionValue'):
                path = (project / 'Debug' / entry.attrib['value']).resolve()
                if path.name=='ble_basic':path=path.with_name('ble_peripheral_only')
                if path.exists() and path not in includes:
                    includes.append(path)
    # Common headers must use Companion's HAL config and copied config overlay.
    includes = [p for p in includes if 'BLE_p2pServer' not in str(p)]
    skip = {'stm32_adv_trace.c', 'adv_trace_usart_if.c', 'app_bsp.c', 'hw_rng.c',
            'stm32wbaxx_nucleo.c', 'scm.c', 'temp_measurement.c', 'adc_ctrl.c',
            'serial_cmd_interpreter.c', 'stm32_lpm.c'}
    if experimental_stop1:
        skip.remove('stm32_lpm.c')
    sources = []
    for link in ET.parse(project / '.project').findall('.//linkedResources/link'):
        uri=link.findtext('locationURI') or ''
        match=re.match(r'PARENT-(\d+)-PROJECT_LOC/(.*)',uri)
        if not match: continue
        path=project.parents[int(match[1])-1] / match[2]
        if path.suffix!='.c' or path.name in skip: continue
        name=link.findtext('name') or ''
        if name.startswith(('Common/WPAN/', 'Middlewares/STM32_WPAN/', 'Utilities/')):
            sources.append(path)
    sources += list(overlay.glob('*.c'))
    wpan=sdk/'Middlewares/ST/STM32_WPAN'
    libraries=[wpan/'ble/stack/lib/stm32wba_ble_stack_full.a',
               wpan/'link_layer/ll_cmd_lib/lib/LinkLayer_BLE_Peripheral_Only_V3_0.a']
    return includes,sources,libraries
