#!/usr/bin/env python3
"""Build the strict WBA generation-58 UI partition from retained native art.

The accepted WB/gen21 files are inputs only.  This builder creates a separate
WBA profile, enumerates every state name reachable by the WBA renderer, and
fails when a state has no deterministic native frame mapping.
"""
from __future__ import annotations

import argparse, hashlib, json, re, struct, sys, zlib
from functools import lru_cache
from pathlib import Path
from typing import Iterable

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from build_emote_asset_pack import build_pack
from wba_resource_geometry import choose_static_bytes, geometry, RESOURCE_HEADROOM
from render_wba_visual_review import FIXTURES
from wba_product_menu_art import menu_frame as render_menu_frame, write_geometry_header, MENU_VISIBLE_ROWS
from wba_menu_locale_contract import LOCALES
from wba_live_menu_values import build as build_live_values
from wba_recording_art import pixels as recording_pixels, evidence as recording_evidence, ASSET as RECORDING_ASSET
from wba_native_art_components import (
    expression_steps, load_authority, load_component_plan,
    render_expression_frame, write_pbm,
)

OUT = ROOT / ".cache/wba-product-resources"
GENERATED = ROOT / "app/companion_pendant/runtime/generated/companion_wba_resource_contract.h"
INTERACTION = ROOT / "app/companion_pendant/runtime/generated/companion_browser_interaction_contract.h"
OLD_CONTRACT = ROOT / "app/companion_pendant/runtime/generated/companion_browser_cemp_contract.h"
PROFILE_DIR = ROOT / "docs/art/iterations/companion-wba-product-resources-gen58"
WIDTH = HEIGHT = 200
FRAME_BYTES = 5000
REVISION = 5800
GENERATION = 58
FAMILIES = tuple(FIXTURES)[:10]
PHASES = ("hold", "orient", "anticipate", "accent", "follow", "settle")
ACTION_PHASES={
 "notice_left":("orient","anticipate","accent","follow","settle"),
 "notice_right":("orient","anticipate","accent","follow","settle"),
 "soften":("anticipate","accent","follow","settle"),
 "small_breath":("anticipate","accent","follow","settle"),
 "listen_up":("orient","anticipate","accent","follow","settle"),
 "question":("orient","anticipate","accent","settle"),
 "beam":("anticipate","accent","follow","settle"),
 "tease_grin":("orient","accent","follow","settle"),
 "yawn":("anticipate","accent","follow","settle"),
 "shy_smile":("anticipate","accent","settle"),
 "ponder":("orient","anticipate","accent","settle"),
 "refocus":("orient","accent","settle"),
 "startle":("orient","accent","follow","settle"),
}
ACTION_STAGES={
 "notice_left":(0,1,2,3,4),"notice_right":(0,1,2,3,4),
 "soften":(1,2,3,4),"small_breath":(0,1,0,4),
 "listen_up":(0,1,2,3,4),"question":(0,1,3,4),
 "beam":(1,2,3,4),"tease_grin":(0,2,3,4),"yawn":(1,2,3,4),
 "shy_smile":(1,2,4),"ponder":(0,1,2,4),"refocus":(0,2,4),
 "startle":(0,2,3,4),
}
FAMILY_ACTIONS={
 "calm":("notice_left","notice_right","soften","small_breath","listen_up"),
 "curious":("notice_left","notice_right","listen_up","question"),
 "delighted":("notice_left","notice_right","soften","beam"),
 "warm":("notice_left","notice_right","soften","listen_up"),
 "playful":("notice_left","notice_right","tease_grin"),
 "sleepy":("small_breath","yawn"),
 "bashful":("notice_left","notice_right","soften","shy_smile"),
 "thoughtful":("notice_left","notice_right","listen_up","ponder"),
 "focused":("notice_left","notice_right","listen_up","refocus"),
 "alert":("notice_left","notice_right","listen_up","startle"),
}
EPISODE_LIMITS={"calm":32,"curious":32,"delighted":32,"warm":32,"playful":12,"sleepy":12,"bashful":12,"thoughtful":32,"focused":12,"alert":32}
MENU_VARIANTS = (1,32,2,4,9,2,1,1,24,2,4,2,1)
MENU_ITEMS = (8,7,4,7,4,2,3,5,6,7,5,3,3)

def sha(data: bytes) -> str: return hashlib.sha256(data).hexdigest().upper()
def fnv(value: str) -> int:
    h=0x811C9DC5
    for b in value.encode("ascii"): h=((h^b)*0x01000193)&0xffffffff
    return h
def display_bytes(pixels: Iterable[tuple[int,int]]) -> bytes:
    return bytes(v^0xff for v in write_pbm(pixels).split(b"\n",2)[2])
def display_to_pbm(raw: bytes) -> bytes:
    if len(raw)!=FRAME_BYTES: raise ValueError("frame is not 200x200 1bpp")
    return b"P4\n200 200\n"+bytes(v^0xff for v in raw)
def xor_patch(base: bytes, target: bytes) -> bytes:
    """Encode a sparse frame-local XOR patch accepted by ui_asset_generation.

    A short unchanged gap is cheaper inside a run than as another 3-byte run
    header.  Runs remain independently bounded by the format's uint8 length.
    """
    changed=[i for i,(a,b) in enumerate(zip(base,target)) if a!=b]
    out=bytearray();at=0
    while at<len(changed):
        start=changed[at];end=start;at+=1
        while at<len(changed) and changed[at]-end<=4 and changed[at]-start<255:
            end=changed[at];at+=1
        count=end-start+1
        out.extend(struct.pack('<HB',start,count))
        out.extend(a^b for a,b in zip(base[start:start+count],target[start:start+count]))
    return bytes(out)
def move(pixels, dx: int, dy: int):
    result={(x+dx,y+dy) for x,y in pixels}
    if any(x<0 or x>=200 or y<16 or y>=200 for x,y in result):
        raise ValueError("native anatomy translation leaves safe canvas")
    return result
def bounds(pixels):
    return (min(x for x,y in pixels),min(y for x,y in pixels),max(x for x,y in pixels),max(y for x,y in pixels)) if pixels else None
def dock(pixels,center=155,bottom=55):
    if not pixels:return set()
    l,t,r,b=bounds(pixels);return {(x+center-(l+r)//2,y+bottom-b) for x,y in pixels}

def parse_old_states() -> set[str]:
    text=OLD_CONTRACT.read_text(encoding="ascii")
    # These are the only dynamic old-profile families the current renderer can
    # actually request. Do not carry unrelated old aliases into a new identity.
    return {s for s in re.findall(r"/\* ([A-Za-z0-9_.-]+) \*/",text)
            if s.startswith("tap_edge_")}

def life_states() -> set[str]:
    states=set()
    for family in FAMILIES:
        for episode in range(EPISODE_LIMITS[family]):
            states.add(f"life_{family}_e{episode}_s0_rest_hold")
            for action in FAMILY_ACTIONS[family]:
                for step,phase in enumerate(ACTION_PHASES[action]):
                    states.add(f"life_{family}_e{episode}_s{step}_{action}_{phase}")
    return states

def menu_states() -> set[str]:
    states=set()
    for locale in LOCALES:
        for screen,(variants,items) in enumerate(zip(MENU_VARIANTS,MENU_ITEMS)):
            visible=4 if screen==0 else MENU_VISIBLE_ROWS
            # Keep UI46 catalog IDs as aliases for OTA compatibility. Only
            # the disjoint 0/3/6 child pages are requested by new firmware.
            page_offsets=set(range(max(1,items-3))) | set(range(0,items,visible))
            for page in sorted(page_offsets):
                for variant in range(variants):
                    suffix="" if variant==0 else f"_v{variant}"
                    states.add(f"menu_ui_{locale}_s{screen}_o{page}_normal{suffix}")
            # Every authored row retains resource-only feedback variants.
            for item in range(items):
                # Retain previous authored IDs for catalog compatibility.
                # New paged feedback IDs are resources only; CP03-10 still
                # owns actual runtime scheduling.
                feedback_pages={min(max(0,item-3),max(1,items-3)-1)}
                if screen!=0:feedback_pages.add((item//visible)*visible)
                for page in feedback_pages:
                    for phase in ("ack","processing","result"):
                        for variant in range(variants):
                            suffix="" if variant==0 else f"_v{variant}"
                            states.add(f"menu_ui_{locale}_s{screen}_o{page}_{phase}_i{item}{suffix}")
    return states

def interaction_states(text: str) -> set[str]:
    states=parse_old_states() | life_states() | menu_states()
    states.update(re.findall(r'"(pointer_follow_[^"]+)"',text))
    states.update(re.findall(r'"(tap_local_[^"]+)"',text))
    states.update(re.findall(r'"(tap_edge_[^"]+)"',text))
    states.update(f"recording_timeline_{i:02d}" for i in range(64))
    states.update(("blink_open","blink_closed"))
    states.update(f"expression_{f}_v0_0_hold" for f in FAMILIES)
    hashes={}
    for state in states:
        prior=hashes.setdefault(fnv(state),state)
        if prior!=state: raise ValueError(f"FNV collision: {prior}, {state}")
    return states

def make_frames(states:set[str], *, lively:bool=False, signature:bool=False, reply_poses:bool=False,
                refined_ornaments:bool=False, richer_poses:bool=False, performance:bool=False,
                polished:bool=False, studio:bool=False, inspection:bool=False):
    authority=load_authority(ROOT)
    ornaments=None
    if refined_ornaments:
        from wba_emotion_ornaments import EmotionOrnaments
        ornaments=EmotionOrnaments(ROOT,authority)
    refinement=None
    if polished:
        from wba_pet_art_refinement import PetArtRefinement
        refinement=PetArtRefinement(ROOT,ornaments)
    if studio:
        if not polished:raise ValueError('Studio art needs polished motion')
        from wba_pet_studio_art import PetStudioArt
        refinement=PetStudioArt(ROOT,ornaments)
    acting=None
    if performance:
        from wba_pet_performance import PetPerformance
        acting=PetPerformance(ROOT,ornaments,refinement)
    # A small asymmetric forelock belongs to the face, clear of the eye and
    # recording regions. The default generation-58 art remains unchanged.
    forelock=set()
    if signature:
        knots=[(93,57),(96,54),(102,58),(101,49),(108,53)]
        for (x0,y0),(x1,y1) in zip(knots,knots[1:]):
            steps=max(abs(x1-x0),abs(y1-y0))
            for step in range(steps+1):
                x=round(x0+(x1-x0)*step/steps);y=round(y0+(y1-y0)*step/steps)
                forelock.update(((x,y),(x,y+1)))
    by_track={}
    for track,index,step in expression_steps(authority): by_track.setdefault(track,[]).append((index,step))
    track_for={family:FIXTURES[family].split("-")[0] for family in FAMILIES}
    family_steps={family:sorted(by_track[track_for[family]]) for family in FAMILIES}
    default_index={family:(4 if family=="sleepy" else int(FIXTURES[family].split("-")[1].split("-")[0])) for family in FAMILIES}
    family_offset={}
    for family,track in track_for.items():
        i,s=family_steps[family][default_index[family]]
        face=render_expression_frame(authority,track,i,s,include_ornaments=False)
        l,t,r,b=bounds(face);family_offset[family]=(100-(l+r)//2,114-(t+b)//2)
    @lru_cache(maxsize=None)
    def group_pixels(family,stage,group):
        track=track_for[family];index,step=family_steps[family][stage]
        plan=load_component_plan(authority,track,index,str(step['cue']));norm=tuple(int(v) for v in plan['normalization_offset'])
        ordered=[]
        for order,layer in enumerate(step['layers']):
            component=authority.components[(str(layer['pack']),int(layer['component_id']))]
            role=component.role;semantic=(role+'_'+component.name).lower()
            is_eye=('eye' in semantic or 'highlight' in semantic or 'sparkle' in semantic)
            is_brow='brow' in semantic;is_mouth='mouth' in semantic
            selected=(group=='ornament' and component.is_ornament) or (not component.is_ornament and (
                (group=='eyes' and is_eye) or (group=='brows' and is_brow) or
                (group=='mouth' and is_mouth) or
                (group=='nose_anchor' and 'nose' in semantic) or
                (group=='fixed' and not is_eye and not is_brow and not is_mouth)))
            if selected:ordered.append((component.z_index,order,layer,component))
        ink=set()
        for _,_,layer,component in sorted(ordered):
            x0=component.base_x+int(layer['offset'][0])+norm[0];y0=component.base_y+int(layer['offset'][1])+norm[1]
            placed={(x0+x,y0+y) for x,y in component.pixels}
            if component.composite_op=='ink':ink.update(placed)
            elif component.composite_op=='erase':ink.difference_update(placed)
        if group=='ornament':return refinement.ornament(family,stage) if refinement else ornaments.frame(family,stage) if ornaments else dock(ink)
        dx,dy=family_offset[family];return move(ink,dx,dy)
    if studio:refinement.configure(group_pixels('calm',default_index['calm'],'eyes'),group_pixels('calm',default_index['calm'],'fixed'))
    def gaze(eye,brow,eye_shift):
        if lively and eye_shift!=(0,0):
            # Keep every translated eye inside the production blink detector's
            # two native eye regions. Highlights travel with their own eye.
            dx,dy=eye_shift
            halves=[{(x,y) for x,y in eye if (x<100)==left} for left in (True,False)]
            x_limits=[(25,97),(102,174)]
            low,high=-200,200
            for points,(left,right) in zip(halves,x_limits):
                if points:
                    low=max(low,left-min(x for x,y in points))
                    high=min(high,right-max(x for x,y in points))
            dx=max(low,min(high,dx)) if low<=0<=high else 0
            low=45-min(y for x,y in eye);high=170-max(y for x,y in eye)
            dy=max(low,min(high,dy)) if low<=0<=high else 0
            eye_shift=(dx,dy)
            # Eyes lead; brows follow by a smaller amount. Nose and cheeks
            # retain the accepted identity and remain stable on the glass.
            brow=move(brow,int(dx/3),int(dy/3))
        if eye_shift!=(0,0):eye=move(eye,*eye_shift)
        return eye,brow
    def compose(family,eyes=None,brows=None,mouth=None,ornament=None,fixed=None,eye_shift=(0,0)):
        base=default_index[family]
        eyes=base if eyes is None else eyes;brows=base if brows is None else brows;mouth=base if mouth is None else mouth
        ornament=base if ornament is None else ornament;fixed=base if fixed is None else fixed
        eye,brow=gaze(group_pixels(family,eyes,'eyes'),group_pixels(family,brows,'brows'),eye_shift)
        if studio:
            result=refinement.compose(family,group_pixels(family,eyes,'eyes'),eye_shift,ornament)
        else:
            result=set(group_pixels(family,fixed,'fixed'))|set(brow)|set(group_pixels(family,mouth,'mouth'))|set(eye)|set(group_pixels(family,ornament,'ornament'))|forelock
        if any(y<16 or y>=172 and 2<=x<42 for x,y in result):raise ValueError(f'{family}: status/footer collision')
        return result
    default={family:display_bytes(compose(family)) for family in FAMILIES}
    if default["sleepy"]==default["calm"]: raise ValueError("sleepy default still equals calm")
    def close_eyelids(result,target,closed_mask):
        # Bake the registered natural-blink eyelid into each family's own eye
        # body. Left=1/right=2: a wink needs no new catalog or runtime scan.
        def body(points,left):
            todo={p for p in points if (p[0]<100)==left};groups=[]
            while todo:
                seed=todo.pop();group={seed};stack=[seed]
                while stack:
                    x,y=stack.pop()
                    for dx in (-1,0,1):
                        for dy in (-1,0,1):
                            p=(x+dx,y+dy)
                            if p in todo:todo.remove(p);group.add(p);stack.append(p)
                groups.append(group)
            return max(groups,key=len)
        source=group_pixels('calm',default_index['calm'],'eyes');closed=compose('calm',eyes=2)
        for left_eye in (True,False):
            if not (closed_mask & (1 if left_eye else 2)):continue
            source_body=body(source,left_eye)
            sl,st,sr,sb=bounds(source_body);tl,tt,tr,tb=bounds(body(target,left_eye))
            glyph={(x,y) for x,y in closed if sl<=x<=sr and st<=y<=sb}
            if not glyph or len(glyph)*2>=len(source_body):
                raise ValueError('Reply pose lost its authored closed eyelid')
            gl,gt,gr,gb=bounds(glyph)
            sw=sr-sl+1;sh=sb-st+1;tw=tr-tl+1;th=tb-tt+1;gw=gr-gl+1;gh=gb-gt+1
            width=(gw*tw+sw//2)//sw;height=min(gh,th//2)
            start_x=tl+(tw-width)//2
            center=((gt-st)*2+gh)*th//(sh*2);start_y=tt+max(0,center-height//2)
            result.difference_update((x,y) for x in range(tl,tr+1) for y in range(tt,tb+1))
            for y in range(height):
                for x in range(width):
                    if (gl+x*gw//width,gt+y*gh//height) in glyph:
                        result.add((start_x+x,start_y+y))
        return result
    @lru_cache(maxsize=None)
    def comfort_pose(ornament_stage=None):
        return display_bytes(close_eyelids(compose('warm',ornament=ornament_stage),
            group_pixels('warm',default_index['warm'],'eyes'),3))
    def align_part(target,source,group):
        # Mouth/brow swaps retain native scale and align to the registered
        # nose, rather than changing the face's proportions or cheek anchors.
        tl,tt,tr,tb=bounds(group_pixels(target,default_index[target],'nose_anchor'))
        sl,st,sr,sb=bounds(group_pixels(source,default_index[source],'nose_anchor'))
        return move(group_pixels(source,default_index[source],group),(tl+tr-sl-sr)//2,(tt+tb-st-sb)//2)
    def expression_pose(family,*,mouth_family=None,brow_lift=0,eye_shift=(0,0),closed_mask=0,ornament_stage=2,performance_key=None,performance_phase='peak'):
        if studio or refinement and performance_key:
            eye,brow=gaze(group_pixels('calm',default_index['calm'],'eyes'),
                align_part('calm',family,'brows'),eye_shift)
            mouth=align_part('calm',mouth_family or family,'mouth')
            if family=='sleepy':closed_mask=3
            if performance_key=='tap_local_bashful_left':closed_mask=0
            extra={'mouth_family':mouth_family} if studio else {}
            result=refinement.face(group_pixels('calm',default_index['calm'],'fixed'),eye,
                move(brow,0,brow_lift),mouth,closed_mask,performance_key or 'expression_'+family,performance_phase,**extra)
            return display_bytes(acting.frame(result,family,performance_key,performance_phase) if performance_key else
                result|refinement.ornament(family,ornament_stage))
        eye,brow=gaze(group_pixels(family,default_index[family],'eyes'),
            group_pixels(family,default_index[family],'brows'),eye_shift)
        mouth=align_part(family,mouth_family,'mouth') if mouth_family else group_pixels(family,default_index[family],'mouth')
        result=(set(group_pixels(family,default_index[family],'fixed'))|set(eye)|set(move(brow,0,brow_lift))|
            set(mouth))
        if closed_mask:result=close_eyelids(result,eye,closed_mask)
        if acting and performance_key:result=acting.frame(result,family,performance_key)
        else:result |= set(group_pixels(family,ornament_stage,'ornament'))|forelock
        if any(y<16 or y>=172 and 2<=x<42 for x,y in result):raise ValueError(f'{family}: reply overlay collision')
        return display_bytes(result)
    variants={
        'tap_local_curious_up':{'family':'curious','zone':'up','label':'期待','eyesClosedMask':0,
            'recipe':dict(mouth_family='warm',brow_lift=-2,eye_shift=(0,-3))},
        'tap_local_playful_right':{'family':'playful','zone':'right','label':'得意眨眼','eyesClosedMask':2,
            'recipe':dict(mouth_family='warm',closed_mask=2)},
        'tap_local_delighted_center':{'family':'delighted','zone':'center','label':'笑弯眼','eyesClosedMask':3,
            'recipe':dict(mouth_family='warm',closed_mask=3)},
        'tap_local_delighted_up':{'family':'delighted','zone':'up','label':'惊喜','eyesClosedMask':0,
            'recipe':dict(mouth_family='curious',brow_lift=-4,eye_shift=(0,-2))},
        'tap_local_bashful_down':{'family':'bashful','zone':'down','label':'害羞开心','eyesClosedMask':3,
            'recipe':dict(closed_mask=3)},
        'tap_local_sleepy_center':{'family':'sleepy','zone':'center','label':'打哈欠','eyesClosedMask':3,
            'recipe':dict(mouth_family='curious')},
    } if richer_poses else {}
    if acting:
        variants.update({
            'tap_local_curious_left':{'family':'curious','zone':'left','label':'换一边看你','eyesClosedMask':0,
                'recipe':dict(mouth_family='warm',brow_lift=-2,eye_shift=(-3,0))},
            'tap_local_playful_left':{'family':'playful','zone':'left','label':'另一边俏皮眨眼','eyesClosedMask':1,
                'recipe':dict(mouth_family='warm',closed_mask=1)},
            'tap_local_warm_down':{'family':'warm','zone':'down','label':'舒服地蹭一下','eyesClosedMask':3,
                'recipe':dict(closed_mask=3)},
            'tap_local_warm_left':{'family':'warm','zone':'left','label':'亲近浅笑','eyesClosedMask':0,
                'recipe':dict(mouth_family='calm',eye_shift=(-2,0))},
            'tap_local_bashful_left':{'family':'bashful','zone':'left','label':'害羞后偷偷看','eyesClosedMask':2,
                'recipe':dict(eye_shift=(-3,0),closed_mask=2)},
        })
    variant_frames={state:expression_pose(row['family'],performance_key=state if acting else None,
        **row['recipe']) for state,row in variants.items()}
    frames={}; metadata={}
    def raw_pixels(raw):
        return {(x,y) for y in range(200) for x in range(200) if not (raw[y*25+x//8]&(0x80>>(x&7)))}
    phase_index={"hold":0,"orient":0,"anticipate":1,"accent":2,"follow":3,"settle":4}
    for state in sorted(states):
        raw=None; kind="compatibility"
        if state.startswith('pet_motion_'):
            if not refinement:raise ValueError('Motion art needs refined acting')
            _,_,family,zone,phase=state.split('_');key=f'tap_local_{family}_{zone}'
            recipe=variants.get(key,{}).get('recipe',{})
            if not recipe:
                recipe={'closed_mask':3} if key=='tap_local_warm_up' else {'mouth_family':'warm'} if family=='playful' else {}
            raw=expression_pose(family,performance_key=key,performance_phase=phase,**recipe);kind='pet_motion'
        elif state.startswith("menu_ui_"): raw=render_menu_frame(state);kind="menu_ui"
        elif state.startswith("expression_"):
            family=state.split("_")[1];raw=default[family];kind="expression"
        elif state=="blink_open": raw=default["calm"];kind="blink"
        elif state=="blink_closed": raw=display_bytes(compose("calm",eyes=2));kind="blink"
        elif state.startswith("recording_timeline_"):
            raw=display_bytes(recording_pixels(int(state[-2:])));kind="recording_timeline"
        elif state.startswith("pointer_follow_"):
            m=re.fullmatch(r"pointer_follow_([a-z]+)_gx([02468])_gy([02468])",state)
            if not m: raise ValueError(state)
            family,gx,gy=m.groups();dx=(int(gx)-4)//2;dy=(int(gy)-4)//2
            if lively: dx*=2;dy*=2
            raw=display_bytes(compose(family,eye_shift=(dx,dy)));kind="pointer_follow"
        elif state.startswith("tap_edge_"):
            m=re.fullmatch(r"tap_edge_([a-z]+)_([a-z]+)_(center|up|down|left|right)_(orient|anticipate|accent|follow|settle)",state)
            if not m: raise ValueError(state)
            source_family,target,zone,phase=m.groups()
            if phase=='orient': pixels=compose(source_family,eyes=1)
            elif phase=='anticipate':
                pixels=(set(group_pixels(source_family,default_index[source_family],'fixed'))|
                    set(group_pixels(source_family,default_index[source_family],'mouth'))|
                    set(group_pixels(target,1,'eyes'))|set(group_pixels(target,1,'brows'))|set(group_pixels(target,1,'ornament')))
            elif phase=='accent':
                pixels=(set(group_pixels(source_family,default_index[source_family],'fixed'))|
                    set(group_pixels(target,2,'eyes'))|set(group_pixels(target,2,'brows'))|
                    set(group_pixels(target,1,'mouth'))|set(group_pixels(target,2,'ornament')))
            elif phase=='follow': pixels=compose(target,eyes=3,brows=2,mouth=3,ornament=3,fixed=3)
            else:pixels=compose(target)
            raw=display_bytes(pixels|forelock);kind="tap_edge"
        elif state.startswith("tap_local_"):
            family=state.split("_")[2]
            ornament_stage=2 if ornaments else None
            if state in variant_frames:raw=variant_frames[state]
            elif acting and state in ('tap_local_warm_center','tap_local_warm_up','tap_local_playful_center'):
                raw=expression_pose(family,mouth_family='warm' if family=='playful' else None,
                    closed_mask=3 if state=='tap_local_warm_up' else 0,performance_key=state)
            elif richer_poses and family=='playful' and state.endswith('_center'):
                raw=expression_pose(family,mouth_family='warm')
            elif reply_poses and family=='warm':
                raw=comfort_pose(ornament_stage) if state.endswith('_up') else (
                    display_bytes(compose(family,ornament=ornament_stage)) if ornaments else default[family])
            else:raw=display_bytes(compose(family,eyes=1,brows=1,ornament=ornament_stage))
            kind="tap_local"
        elif state.startswith("life_"):
            m=re.match(r"life_([a-z]+)_e(\d+)_s(\d+)_([a-z_]+)_(hold|orient|anticipate|accent|follow|settle)$",state)
            if not m: raise ValueError(state)
            family,episode,step,action,phase=m.groups();step=int(step)
            if action=="rest" or phase=="settle":
                raw=default[family];kind="life";frames[state]=raw
                metadata[state]={"kind":kind,"sha256":sha(raw),"duration_ms":480}
                continue
            stage=ACTION_STAGES[action][step]
            # Calm's retained intermediate poses are the authored natural
            # blink. Life actions may move the open eyes but must not borrow a
            # blink-closed pose as generic animation.
            if family=="calm": stage=default_index[family]
            # Eyes lead, brows follow, then mouth and authored ornament. This
            # preserves each registered component and avoids an all-face swap.
            brow_stage=max(0,stage-1);mouth_stage=max(0,stage-2)
            intensity=0 if phase in ("hold","settle") else (2 if phase=="accent" else 1)
            if lively: intensity={"hold":0,"orient":2,"anticipate":4,"accent":6,"follow":4,"settle":0}[phase]
            dx=(-intensity if action=="notice_left" else intensity if action=="notice_right" else 0)
            dy=(-intensity if action=="listen_up" else 0)
            ornament_stage=max(0,stage-1)
            if richer_poses and phase in ('accent','follow') and family=='curious' and action=='question':
                raw=expression_pose(family,mouth_family='warm',brow_lift=-2,eye_shift=(dx,dy-3),ornament_stage=ornament_stage)
            elif richer_poses and phase in ('accent','follow') and family in ('delighted','playful') and action in ('beam','tease_grin'):
                raw=expression_pose(family,mouth_family='warm',eye_shift=(dx,dy),ornament_stage=ornament_stage)
            elif richer_poses and phase in ('accent','follow') and family=='sleepy' and action=='yawn':
                raw=expression_pose(family,mouth_family='curious',eye_shift=(dx,dy),ornament_stage=ornament_stage)
            else:raw=display_bytes(compose(family,eyes=stage,brows=brow_stage,mouth=mouth_stage,ornament=ornament_stage,eye_shift=(dx,dy)))
            kind="life"
        else: raise ValueError(f"unresolved state {state}")
        if raw is None or len(raw)!=FRAME_BYTES: raise ValueError(f"unresolved state {state}")
        frames[state]=raw;metadata[state]={"kind":kind,"sha256":sha(raw),"duration_ms":480}
    pointer_eye_only=True;life_fixed_preserved=True
    for state,raw in frames.items():
        if state.startswith('pointer_follow_'):
            m=re.fullmatch(r"pointer_follow_([a-z]+)_gx([02468])_gy([02468])",state);family,gx,gy=m.groups()
            dx=(int(gx)-4)//2;dy=(int(gy)-4)//2
            if lively:dx*=2;dy*=2
            eye=group_pixels(family,default_index[family],'eyes');brow=group_pixels(family,default_index[family],'brows')
            moved_eye,moved_brow=gaze(eye,brow,(dx,dy))
            if studio:
                closed=3 if family=='sleepy' else 0
                original_parts=refinement.parts(family,closed_mask=closed)
                moved_parts=refinement.parts(family,(dx,dy),closed_mask=closed)
                allowed=original_parts[0]|original_parts[1]|moved_parts[0]|moved_parts[1]
            else:allowed=set(eye)|set(moved_eye)|set(brow)|set(moved_brow)
            if (raw_pixels(raw)^raw_pixels(default[family]))-allowed:pointer_eye_only=False
        elif state.startswith('life_'):
            family=state.split('_')[1];fixed=refinement.fixed if studio else group_pixels(family,default_index[family],'fixed')
            if not all(not(raw[y*25+x//8]&(0x80>>(x&7))) for x,y in fixed):life_fixed_preserved=False
    life_rest_default=all(frames[f"life_{family}_e0_s0_rest_hold"]==default[family] for family in FAMILIES) if not inspection else True
    calm_closed=display_bytes(compose("calm",eyes=2))
    life_excludes_closed=all(raw!=calm_closed for state,raw in frames.items() if state.startswith('life_calm_'))
    quality={"nativeComponentScale":1,"familyFaceCenters":[100,114],"ornamentDock":[155,55],
      "signatureForelockPixels":len(forelock),"warmComfortReplyUsesRegisteredClosedEyelid":reply_poses and not polished,
      "pointerChangedPixelsRestrictedToRegisteredEyes":pointer_eye_only and not lively,
      "pointerChangedPixelsRestrictedToRegisteredEyesAndBrows":pointer_eye_only,
      "lifeFixedCheekNosePixelsPreserved":life_fixed_preserved,
      "lifeRestEqualsExpressionDefault":life_rest_default,
      "lifeExcludesNaturalBlinkClosedCue":life_excludes_closed,
      "lifeOrnamentStageLag":1,
      "recordingArt":recording_evidence(),"footerGuard":{"x":[2,41],"y":[156,179],"composition":"transparent ink; base retained"}}
    if studio:
        quality['nativeStudioArt']=True
        quality['fixedAnchorScope']='all studio families use the registered calm nose/cheek masks'
        quality['pointerChangedPixelsRestrictedToRegisteredEyesAndBrows']=False
        quality['pointerChangedPixelsRestrictedToStudioEyesAndBrows']=pointer_eye_only
    if ornaments:
        quality['ornamentDock']=[153,59]
        quality['emotionOrnaments']=ornaments.evidence()
    if acting:quality['petPerformance']=acting.evidence()
    if refinement:
        quality['petArtRefinement']=refinement.evidence()
        if 'tap_local_bashful_left' in variants:variants['tap_local_bashful_left']['eyesClosedMask']=0
    if richer_poses:
        quality['expressionVariants']=[{'state':state,**{k:v for k,v in row.items() if k!='recipe'}} for state,row in variants.items()]
        quality['replyPoseComposition']=('native calm anchors, aligned family brows/mouth, smile eyelids and native-size intermediate highlights' if polished else
            'registered native eyes/brows/mouth; nose-aligned mouth swaps; registered blink eyelid fitted to own eye body')
        quality['dailyRicherExpressions']=['curious/question','delighted/beam','playful/tease_grin','sleepy/yawn']
        layout_source=ROOT/'app/companion_pendant/runtime/companion_reply_layout.h'
        layout=layout_source.read_text(encoding='utf-8')
        constants={name:int(value) for name,value in re.findall(r'#define COMP_REPLY_TEXT_(\w+) (\d+)u',layout)}
        top=constants['Y']
        # Keep the shared strip free of all pet ink; native recording art has
        # its own region and is not a pet or a conversation reply.
        crowded=[state for state,raw in frames.items() if metadata[state]['kind'] not in ('menu_ui','recording_timeline')
            and any(value!=255 for value in raw[top*25:])]
        if crowded:raise ValueError('Reply strip overlaps pet ink: '+', '.join(crowded[:6]))
        quality['replyTextReserve']={'rect':[constants['X'],top,constants['WIDTH'],constants['HEIGHT']],
            'recordingRect':[constants['RECORDING_X'],top,constants['RECORDING_WIDTH'],constants['HEIGHT']],
            'lines':constants['LINES'],'lineHeight':constants['LINE_HEIGHT'],'linePitch':constants['LINE_PITCH'],
            'petInkClear':True,'chatBackend':'NOT_IMPLEMENTED','update':'whole short sentences',
            'sourceSha256':{layout_source.relative_to(ROOT).as_posix():sha(layout_source.read_bytes())}}
    if not pointer_eye_only or not life_fixed_preserved or not life_rest_default or not life_excludes_closed:raise ValueError(f'component isolation failed: {quality}')
    return frames,metadata,quality

def write_contract(cemp:bytes,meta:dict,resource_id:str,state_count:int):
    clip_off,frame_off,string_off,string_len,payload_off=struct.unpack_from("<IIIII",cemp,32)[:5]
    clips=[]
    for i in range(meta["clip_count"]):
        no,first,count,ls,le=struct.unpack_from("<IHHHH",cemp,clip_off+i*16)
        clips.append((no,first,count,ls,le))
    frames=[]
    for i in range(meta["frame_count"]): frames.append(struct.unpack_from("<IIHHHHH",cemp,frame_off+i*20))
    strings=cemp[string_off:string_off+string_len]
    lines=["#ifndef COMPANION_WBA_RESOURCE_CONTRACT_H","#define COMPANION_WBA_RESOURCE_CONTRACT_H","#include <stdint.h>","#include \"emote_player.h\"",
      f"#define COMPANION_WBA_RESOURCE_PROFILE_REVISION {REVISION}u",f"#define COMPANION_WBA_RESOURCE_GENERATION {GENERATION}u",
      f"#define COMPANION_WBA_CEMP_CLIP_COUNT {meta['clip_count']}u",f"#define COMPANION_WBA_CEMP_FRAME_COUNT {meta['frame_count']}u",
      f"#define COMPANION_WBA_CEMP_STRING_BYTES {string_len}u",f"#define COMPANION_WBA_CEMP_TOTAL_BYTES {len(cemp)}u",
      f"#define COMPANION_WBA_RESOURCE_STATE_COUNT {state_count}u",f"#define COMPANION_WBA_RESOURCE_ID \"{resource_id}\"",
      "static const uint8_t companion_wba_cemp_strings[COMPANION_WBA_CEMP_STRING_BYTES]={"]
    for i in range(0,len(strings),16): lines.append("  "+",".join(f"0x{x:02X}u" for x in strings[i:i+16])+",")
    lines += ["};","static const comp_emote_clip_t companion_wba_cemp_clips[COMPANION_WBA_CEMP_CLIP_COUNT]={"]
    for no,first,count,ls,le in clips: lines.append(f"  {{(const char*)&companion_wba_cemp_strings[{no}u],{first}u,{count}u,{ls}u,{le}u}},")
    lines += ["};","static const comp_emote_frame_t companion_wba_cemp_frames[COMPANION_WBA_CEMP_FRAME_COUNT]={"]
    for d,s,dur,x,y,w,h in frames: lines.append(f"  {{{d}u,{s}u,{dur}u,{x}u,{y}u,{w}u,{h}u}},")
    lines += ["};","#endif"]
    GENERATED.write_text("\n".join(lines)+"\n",encoding="ascii")

def main():
    menu_geometry_header=write_geometry_header()
    live_values_header=build_live_values()
    OUT.mkdir(parents=True,exist_ok=True);PROFILE_DIR.mkdir(parents=True,exist_ok=True)
    frame_dir=OUT/"frames";frame_dir.mkdir(exist_ok=True)
    states=interaction_states(INTERACTION.read_text(encoding="ascii"))
    frames,state_meta,art_quality=make_frames(states)
    # Menu values and row feedback are sparse variants of a stable page. Keep
    # one real raster per locale/screen/page in CEMP and store the exact pixel
    # difference as a generation XOR patch. This is the existing production
    # format, remains independently seekable, and keeps the complete menu
    # menu contract inside the 1 MiB atomic production UI partition.
    base_for={}
    for state in states:
        if state.startswith('menu_ui_'):
            m=re.fullmatch(r'menu_ui_(en|zh_cn|zh_tw)_s(\d+)_o(\d+)_.*',state)
            locale,screen,page=m.groups()
            base_for[state]=f'menu_ui_{locale}_s{screen}_o{page}_normal'
        else: base_for[state]=state
    by_sha={};clips=[];state_to_clip={};clip_raw={}
    for state in sorted(states):
        raw=frames[base_for[state]];digest=sha(raw);name=by_sha.get(digest)
        if name is None:
            name=f"wba_g22_frame_{len(by_sha):04d}";by_sha[digest]=name;clip_raw[name]=raw
            path=frame_dir/f"{name}.pbm";path.write_bytes(display_to_pbm(raw))
            clips.append({"name":name,"frames":[{"source":f"frames/{name}.pbm","duration_ms":480}]})
        state_to_clip[state]=name
    manifest={"schema":"companion.emote_asset_pack_manifest.v1","name":"companion-wba-product-gen30","revision":REVISION,"priority":0,
      "profile":{"width":200,"height":200,"stride_bytes":25,"pixel_format":"mono_1bpp_white_is_one_msb"},"encoding":"packbits","clips":clips}
    manifest_path=OUT/"cemp-manifest.json";manifest_path.write_text(json.dumps(manifest,indent=2)+"\n")
    cemp,cmeta=build_pack(manifest_path);(OUT/"product.cemp").write_bytes(cemp)
    # Map clip names to CEMP frame indices; one frame per canonical clip.
    clip_index={clip["name"]:i for i,clip in enumerate(clips)}
    identity=hashlib.sha256();identity.update(f"companion-wba-ui-assets-generation{GENERATION}\0".encode('ascii'))
    for state in sorted(states): identity.update(state.encode()+b"\0"+bytes.fromhex(state_meta[state]["sha256"])+struct.pack("<H",480))
    resource_id=identity.hexdigest().upper()
    rows=[]
    for state in states:
        base=clip_raw[state_to_clip[state]];patch=xor_patch(base,frames[state])
        rows.append((fnv(state),clip_index[state_to_clip[state]],zlib.crc32(frames[state]),patch,state))
    rows.sort();manifest_bytes=32+24*len(rows);patches=bytearray();blob_offset=(len(cemp)+4095)&~4095
    blob=bytearray(manifest_bytes)
    struct.pack_into("<4sHHHHI",blob,0,b"CUIM",1,32,len(rows),24,manifest_bytes)
    # Many phase/locale rows contain byte-identical sparse patches. Entries
    # already carry independent base indices and final-frame CRCs, so they may
    # reference one immutable payload. Deduplicate exact bytes, not hashes;
    # this adds no decoding format, RAM, or runtime work for a third language.
    patch_offsets={};unshared_patch_bytes=0
    for i,(state_hash,index,crc,patch,state) in enumerate(rows):
        flags=4 if patch else 0;payload_offset=0
        unshared_patch_bytes+=len(patch)
        if patch:
            if patch not in patch_offsets:
                patch_offsets[patch]=blob_offset+manifest_bytes+len(patches)
                patches.extend(patch)
            payload_offset=patch_offsets[patch]
        struct.pack_into("<IHHIIHHI",blob,32+i*24,state_hash,index,flags,crc,payload_offset,len(patch),480,zlib.crc32(patch) if patch else 0)
    blob.extend(patches);generation_blob=bytes(blob);(OUT/"generation.bin").write_bytes(generation_blob)
    # Diagnostic speech/seed fixtures are separate developer artifacts. They
    # are never dependencies of production rendering or microphone capture.
    resource_arena_bytes=blob_offset+len(blob)
    flash_geometry=geometry(choose_static_bytes(resource_arena_bytes))
    partition=bytearray(b"\xff"*flash_geometry['staticBytes']);partition[:len(cemp)]=cemp;partition[blob_offset:blob_offset+len(blob)]=blob
    root=bytearray(b"\xff"*128);struct.pack_into("<4sHHIIIIIIIII",root,0,b"CUIR",1,128,GENERATION,len(cemp),blob_offset,len(blob),zlib.crc32(blob),0,manifest_bytes,zlib.crc32(blob[:manifest_bytes]),(blob_offset+len(blob)+4095)&~4095)
    root[44:76]=bytes.fromhex(resource_id);struct.pack_into("<I",root,124,zlib.crc32(root[:124]));partition[flash_geometry['rootA']:flash_geometry['rootA']+128]=root
    if resource_arena_bytes>flash_geometry['rootA']: raise ValueError(f"generation{GENERATION} exceeds its static resource arena")
    image=OUT/"ui-partition.bin";image.write_bytes(partition)
    art_quality['menuPatchStorage']={'uniquePayloads':len(patch_offsets),'storedBytes':len(patches),
        'unsharedBytes':unshared_patch_bytes,'savedBytes':unshared_patch_bytes-len(patches),
        'method':'exact immutable payload sharing; original XOR wire format'}
    source_manifest={"schema":"companion.wba.product.resources.v1","status":"PASS_SOFTWARE_RESOURCE_BUILD","profileRevision":REVISION,"generation":GENERATION,
      "resourceId":resource_id,"stateCount":len(states),"canonicalFrameCount":len(clips),"cempBytes":len(cemp),"generationBytes":len(blob),"generationPatchBytes":len(patches),
      "uiPartitionBytes":len(partition),"uiPartitionSha256":sha(partition),"sleepyDistinctFromCalm":state_meta["expression_sleepy_v0_0_hold"]["sha256"]!=state_meta["expression_calm_v0_0_hold"]["sha256"],
      "storageLayoutVersion":3,"resourceContentBytes":len(cemp)+len(blob)+len(root),
      "resourceArenaUsedBytes":resource_arena_bytes,"resourceBudgetBytes":len(partition),
      "resourceHeadroomTargetBytes":RESOURCE_HEADROOM,"flashGeometry":flash_geometry,
      "diagnosticAudioIncluded":False,
      "coverage":{k:sum(1 for v in state_meta.values() if v["kind"]==k) for k in sorted({v["kind"] for v in state_meta.values()})},
      "hardwareAcceptance":"NOT_RUN",
      "recordingArtRestoration":recording_evidence(),
      "states":{s:{**state_meta[s],"canonicalClip":state_to_clip[s]} for s in sorted(states)}}
    source_manifest["artQualityChecks"]=art_quality
    provenance=[Path(__file__),Path(__file__).with_name('wba_resource_geometry.py'),INTERACTION,OLD_CONTRACT,
        ROOT/'tools/wba_native_art_components.py',
        ROOT/'tools/wba_product_menu_art.py', ROOT/'tools/wba_menu_typography.py', ROOT/'tools/wba_menu_icons.py', ROOT/'tools/wba_menu_locale_contract.py', ROOT/'tools/wba_menu_translations.py', ROOT/'tools/wba_live_menu_values.py', live_values_header, ROOT/'tools/wba_recording_art.py', RECORDING_ASSET, RECORDING_ASSET.with_suffix('.json'),
        menu_geometry_header,
        ROOT/'app/companion_pendant/runtime/generated/companion_wba_menu_feedback.h',
        ROOT/'docs/art/iterations/companion-pet-expression-v9-two-track-rig-v7/candidate/target-score-attempt-01/v45-wb55-target-profile-plan.json']
    source_manifest["sourceSha256"]={p.relative_to(ROOT).as_posix():sha(p.read_bytes()) for p in provenance}
    for p in (Path('C:/Windows/Fonts')/name for name in ('simsun.ttc','simhei.ttf','msyh.ttc','msyhbd.ttc','segoeui.ttf','segoeuib.ttf')):
        source_manifest["sourceSha256"][str(p)]=sha(p.read_bytes())
    source_manifest["source_sha256"]=dict(source_manifest["sourceSha256"])
    (OUT/"profile.json").write_text(json.dumps(source_manifest,indent=2)+"\n")
    (OUT/"states.txt").write_text("\n".join(sorted(states))+"\n",encoding="ascii")
    (PROFILE_DIR/"profile.json").write_text(json.dumps({k:v for k,v in source_manifest.items() if k!="states"},indent=2)+"\n")
    write_contract(cemp,cmeta,resource_id,len(states))
    print(json.dumps({k:source_manifest[k] for k in ("status","profileRevision","generation","resourceId","stateCount","canonicalFrameCount","cempBytes","generationBytes","uiPartitionBytes","uiPartitionSha256","sleepyDistinctFromCalm")},sort_keys=True))
if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=OUT)
    parser.add_argument('--profile-output',type=Path,default=PROFILE_DIR)
    parser.add_argument('--contract',type=Path,default=GENERATED)
    args=parser.parse_args()
    OUT=args.output.resolve();PROFILE_DIR=args.profile_output.resolve();GENERATED=args.contract.resolve()
    GENERATED.parent.mkdir(parents=True,exist_ok=True)
    main()
