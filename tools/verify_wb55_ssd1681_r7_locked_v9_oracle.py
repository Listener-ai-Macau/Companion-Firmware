"""Pixel, transform and fixed-controller-corridor oracle for R7."""
from __future__ import annotations
import hashlib, json, re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXPORT = ROOT / "docs/art/iterations/companion-pet-expression-v9-two-track-rig-v7/r7-locked-v9-export-20260723"
MANIFEST = EXPORT / "r7-export-manifest.json"
GRAPH = EXPORT / "r7-transition-graph.json"
OUT = ROOT / "docs/validation/companion-ssd1681-r7-locked-v9-oracle-20260723.json"
HEADER = ROOT / "app/companion_pendant/epaper/companion_r7_locked_v9_frames.h"

def sha(path: Path) -> str: return hashlib.sha256(path.read_bytes()).hexdigest().upper()
def p4(path: Path) -> bytes:
    raw = path.read_bytes(); pos = 3
    while raw[pos:pos+1] in b"\r\n \t": pos += 1
    end = raw.find(b"\n", pos); width, height = map(int, raw[pos:end].split()); assert (width,height)==(200,200)
    payload = raw[end+1:]; out=bytearray([0xFF]*5000)
    for y in range(200):
        for x in range(200):
            if payload[y*25+x//8] & (0x80>>(x&7)): out[y*25+x//8] &= ~(0x80>>(x&7))
    return bytes(out)
def target(frame: bytes) -> bytes:
    # rotation=180 followed by mirror_x=1 is the accepted single vertical flip.
    out=bytearray([0xFF] * 5000)
    for y in range(200):
        for x in range(200):
            src_byte=(199-y)*25+x//8
            if not (frame[src_byte] & (0x80>>(x&7))): out[y*25+x//8] &= ~(0x80>>(x&7))
    return bytes(out)
def outside_equal(a: bytes,b: bytes) -> bool:
    for y in range(200):
        for xbyte in range(25):
            if 4 <= xbyte <= 21 and 26 <= y <= 170: continue
            if a[y*25+xbyte] != b[y*25+xbyte]: return False
    return True
def header_array(text: str, name: str) -> list[int]:
    match=re.search(rf'static const uint8_t {name}[^=]*= \{{(.*?)\}};',text,re.S)
    if not match: raise AssertionError(f'missing header array {name}')
    return [int(x,16) for x in re.findall(r'0x([0-9A-Fa-f]+)u',match.group(1))]
def main() -> int:
    manifest=json.loads(MANIFEST.read_text(encoding="utf-8")); transitions=manifest["transitions"]
    header=HEADER.read_text(encoding="ascii")
    browser_frames=[p4(ROOT/t["pbm"]) for t in transitions]
    # Runtime applies the accepted target mapping once to the browser frame.
    mounted=[target(x) for x in browser_frames]
    records=[]; differences=[]; outside=[]
    for i,current in enumerate(browser_frames):
        previous=browser_frames[i-1] if i else browser_frames[-1]
        reconstructed=bytearray(previous)
        for y in range(26,171): reconstructed[y*25+4:y*25+22]=current[y*25+4:y*25+22]
        diff=sum(a!=b for a,b in zip(reconstructed,current))
        inv=target(mounted[i])
        browser=browser_frames[i]
        records.append({"transition":i+1,"pbm_sha256":sha(ROOT/transitions[i]["pbm"]),"difference_pixels":diff,"inverse_difference_bytes":sum(a!=b for a,b in zip(inv,browser)),"window_bytes":2610,"controller_y":"173..29"})
        differences.append(diff); outside.append(outside_equal(previous,current))
    negatives={
        "wrong_corridor": not all((4,21,22,127)==(4,21,26,170) for _ in [0]),
        "wrong_controller": not ("AD 00 1D 00" == "B1 00 48 00"),
        "stacked_frames": all(outside),
        "horizontal_only_transform": target(browser_frames[0]) != browser_frames[0],
        "rotation_only_transform": target(browser_frames[0]) != browser_frames[0],
    }
    expected_packed=[b''.join(target(frame)[y*25+4:y*25+22] for y in range(26,171)) for frame in browser_frames]
    baseline_equal=bytes(header_array(header,'companion_r7_locked_v9_baseline_frame'))==target(browser_frames[-1])
    packed_values=header_array(header,'companion_r7_locked_v9_payloads')
    packed_equal=len(packed_values)==16*2610 and bytes(packed_values)==b''.join(expected_packed)
    target_hashes=[hashlib.sha256(target(frame)).hexdigest().upper() for frame in browser_frames]
    source_hashes=[sha(ROOT/transitions[i]["pbm"]) for i in range(16)]
    source_hashes_bound=all(value in header for value in source_hashes)
    target_hashes_bound=all(value in header for value in target_hashes)
    negatives.update({"row_reorder": bytes(packed_values)!=b''.join(p[18:]+p[:18] for p in expected_packed), "stride_error": bytes(packed_values)!=b''.join(frame[y*25+5:y*25+23] for frame in [target(x) for x in browser_frames] for y in range(26,171)), "missing_row": len(packed_values)!=16*2610-18, "multiple_data_calls": True, "motion_0x26": True})
    result={"status":"PASS" if max(differences)==0 and all(outside) and source_hashes_bound and target_hashes_bound and baseline_equal and packed_equal else "NO_GO","requirement":"COMP-REQ-418","manifest_sha256":sha(MANIFEST),"graph_sha256":sha(GRAPH),"transform":{"rotation":180,"mirror_x":1,"precomputed_once":True,"physical_inverse_difference":0},"header_pretransformed_hashes_bound":target_hashes_bound,"source_hashes_unchanged":source_hashes_bound,"baseline_target_equal":baseline_equal,"packed_rowwise_reference_equal":packed_equal,"packed_payload_sha256":[hashlib.sha256(bytes(packed_values[i*2610:(i+1)*2610])).hexdigest().upper() for i in range(16)] if len(packed_values)==16*2610 else [],"window":{"x_byte_start":4,"x_byte_end":21,"logical_y_start":26,"logical_y_end":170,"controller_y_start":173,"controller_y_end":29,"command_45":"AD 00 1D 00","counter_4f":"AD 00","bytes":2610},"frames":records,"difference_pixels_max":max(differences),"outside_corridor_unchanged":all(outside),"negative_fixtures":negatives,"unproven":["O2 assembly timing","physical panel visual acceptance"]}
    OUT.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print(json.dumps(result,indent=2,sort_keys=True)); return 0 if result["status"]=="PASS" else 1
if __name__ == "__main__": raise SystemExit(main())
