"""Generate target-oriented baseline plus packed R7 corridor payloads."""
from __future__ import annotations
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
MANIFEST=ROOT/'docs/art/iterations/companion-pet-expression-v9-two-track-rig-v7/r7-locked-v9-export-20260723/r7-export-manifest.json'
HEADER=ROOT/'app/companion_pendant/epaper/companion_r7_locked_v9_frames.h'
EXPECTED='9B55E24EF3E07F4A0832D879F563183728386FE288219D628F7AAF58EB60ABB8'
def sha_path(p): return hashlib.sha256(p.read_bytes()).hexdigest().upper()
def sha_bytes(v): return hashlib.sha256(v).hexdigest().upper()
def read_p4(p):
 raw=p.read_bytes(); end=raw.find(b'\n',3); w,h=map(int,raw[3:end].split()); assert (w,h)==(200,200)
 payload=raw[end+1:]; out=bytearray([0xFF]*5000)
 for y in range(200):
  for x in range(200):
   if payload[y*25+x//8]&(0x80>>(x&7)): out[y*25+x//8]&=~(0x80>>(x&7))
 return bytes(out)
def target(src):
 out=bytearray([0xFF]*5000)
 for y in range(200):
  for x in range(200):
   if not (src[(199-y)*25+x//8]&(0x80>>(x&7))): out[y*25+x//8]&=~(0x80>>(x&7))
 return bytes(out)
def payload(frame): return b''.join(frame[y*25+4:y*25+22] for y in range(26,171))
def emit_array(lines,name,values,per=16):
 lines.append(f'static const uint8_t {name}[{len(values)}] = {{')
 for i in range(0,len(values),per): lines.append('    '+', '.join(f'0x{x:02X}u' for x in values[i:i+per])+',')
 lines.extend(['};',''])
def main():
 m=json.loads(MANIFEST.read_text(encoding='utf-8')); assert sha_path(MANIFEST)==EXPECTED and len(m['transitions'])==16
 sources=[]; targets=[]; source_hashes=[]
 for t in m['transitions']:
  p=ROOT/t['pbm']; s=read_p4(p); sources.append(s); targets.append(target(s)); source_hashes.append(sha_path(p))
 baseline=targets[-1]; packed=[payload(x) for x in targets]
 lines=['#ifndef COMPANION_R7_LOCKED_V9_FRAMES_H','#define COMPANION_R7_LOCKED_V9_FRAMES_H','','#include <stdint.h>','#define COMPANION_R7_LOCKED_V9_FRAME_COUNT 16u','#define COMPANION_R7_LOCKED_V9_FRAME_BYTES 5000u','#define COMPANION_R7_LOCKED_V9_CORRIDOR_BYTES 2610u','']
 emit_array(lines,'companion_r7_locked_v9_baseline_frame',baseline)
 lines.append('static const uint8_t companion_r7_locked_v9_payloads[COMPANION_R7_LOCKED_V9_FRAME_COUNT][COMPANION_R7_LOCKED_V9_CORRIDOR_BYTES] = {')
 for p in packed:
   lines.append('    {')
   for i in range(0,len(p),16): lines.append('        '+', '.join(f'0x{x:02X}u' for x in p[i:i+16])+',')
   lines.append('    },')
 lines.extend(['};','', 'static const char *const companion_r7_locked_v9_source_frame_sha256[COMPANION_R7_LOCKED_V9_FRAME_COUNT] = {'])
 lines += [f'    "{x}",' for x in source_hashes]
 lines += ['};','', 'static const char *const companion_r7_locked_v9_target_frame_sha256[COMPANION_R7_LOCKED_V9_FRAME_COUNT] = {']
 lines += [f'    "{sha_bytes(x)}",' for x in targets]
 lines += ['};','', 'static const char *const companion_r7_locked_v9_payload_sha256[COMPANION_R7_LOCKED_V9_FRAME_COUNT] = {']
 lines += [f'    "{sha_bytes(x)}",' for x in packed]
 lines += ['};','',f'    /* baseline_sha256={sha_bytes(baseline)} */','#define COMPANION_R7_LOCKED_V9_PRETRANSFORM_ROTATION 180u','#define COMPANION_R7_LOCKED_V9_PRETRANSFORM_MIRROR_X 1u','','#endif','']
 HEADER.write_text('\n'.join(lines),encoding='ascii')
 print(json.dumps({'header_sha256':sha_path(HEADER),'source_hashes':source_hashes,'payload_sha256':[sha_bytes(x) for x in packed]},indent=2)); return 0
if __name__=='__main__': raise SystemExit(main())
