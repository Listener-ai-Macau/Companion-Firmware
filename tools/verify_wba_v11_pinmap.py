"""Cross-check the schematic-derived V1.1 pin map against ST's CubeMX package/AF database."""
import argparse
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--cubemx', type=Path, default=Path('C:/ST/STM32CubeMX_6.17.0'))
parser.add_argument('--output', type=Path, default=ROOT / '.cache/wba-v11-prehardware/pinmap-check.json')
parser.add_argument('--pcb', type=Path, help='Current location of the unchanged source PCB; original evidence path is retained as provenance')
args = parser.parse_args()
profile_file = ROOT / 'platform/stm32wba55_companion_v11/pinmap.json'
profile = json.loads(profile_file.read_text())
package_file = args.cubemx / 'db/mcu' / profile['package_db']
af_file = args.cubemx / 'db/mcu/IP/GPIO-STM32WBAx_gpio_v1_0_Modes.xml'
package = ET.parse(package_file).getroot()
af = ET.parse(af_file).getroot()
package_pins = {p.get('Name').split(' ')[0]: p for p in package if p.tag.endswith('}Pin')}
af_pins = {p.get('Name').split(' ')[0]: p for p in af if p.tag.endswith('}GPIO_Pin')}
checked = []
for pin, (signal, alternate) in profile['alternate_functions'].items():
    assert pin in package_pins, f'{pin} absent in selected package'
    assert any(s.get('Name') == signal for s in package_pins[pin]), f'{pin}/{signal} absent in package'
    found = next((s for s in af_pins[pin] if s.get('Name') == signal), None)
    assert found is not None, f'{pin}/{signal} absent in AF table'
    assert any(v.text == alternate for v in found.iter()), f'{pin}/{signal} wrong AF'
    checked.append({'pin': pin, 'signal': signal, 'af': alternate})
for pin in profile['gpio'].values():
    assert pin in package_pins, f'GPIO {pin} absent in package'
hardware = ROOT.parent / 'Companion-Hardware/electronics/companion-v1.1-2026-09-19'
evidence_file = hardware / 'pcb-net-evidence.json'
evidence = json.loads(evidence_file.read_text(encoding='utf-8'))
pcb = args.pcb.resolve() if args.pcb else Path(evidence['source'])
assert hashlib.sha256(pcb.read_bytes()).hexdigest() == evidence['sha256'] == profile['source_pcb_sha256'], 'PCB changed; regenerate evidence and re-audit'
pcb_checks = []
for pin in sorted(set(profile['alternate_functions']) | set(profile['gpio'].values())):
    position = package_pins[pin].get('Position')
    expected_net = f'{pin[1]}{int(pin[2:]):02d}_P{int(position):02d}'
    net = next((n for n in evidence['nets'] if n['name'] == expected_net), None)
    assert net is not None, f'Missing PCB net {expected_net}'
    assert {'component': profile['pcb_mcu_designator'], 'pad': position} in net['pads'], f'{pin} PCB MCU pad mismatch'
    pcb_checks.append({'pin': pin, 'package_pad': position, 'net': expected_net, 'endpoints': net['pads']})
pdf = hardware / 'Companion V1.1.pdf'
assert hashlib.sha256(pdf.read_bytes()).hexdigest() == profile['source_pdf_sha256'], 'Schematic changed; re-audit pin map'
result = {'result': 'PASS_VENDOR_PIN_CAPABILITY_CHECK', 'physical_connectivity': 'NOT_TESTED', 'checked': checked,
          'pcb_logical_assignments': pcb_checks, 'epd_reset_pads': evidence['epd_reset_pads'],
          'gpio_count': len(profile['gpio']), 'unresolved': profile['unresolved'],
          'input_sha256': {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in (profile_file, package_file, af_file, pdf, evidence_file, pcb)}}
args.output.parent.mkdir(parents=True, exist_ok=True)
args.output.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
print(f'{result["result"]}: {len(checked)} alternate functions + {result["gpio_count"]} GPIO; {args.output}')
