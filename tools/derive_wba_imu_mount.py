"""Derive a board mounting map from a closed, Owner-labelled raw capture.
No serial/debug access or firmware/config write. Keep the original full-group
failure and explicitly report a contiguous stable suffix after pose adjustment.
"""
from __future__ import annotations
import argparse, hashlib, json, os, re, tempfile
from datetime import datetime, timezone, timedelta
from pathlib import Path
LIMITS={"minimum_samples":2,"minimum_span_ms":8000,"maximum_gap_ms":12000,
        "maximum_axis_range_mg":120,"maximum_age_ms":250,
        "norm_squared_min":810000,"norm_squared_max":1210000}
def age_span(new:int,old:int)->int:return (new-old)&0xffffffff
def stable_tail(samples:list[dict])->dict:
    if not samples:raise ValueError("No samples")
    tail=[]
    for sample in reversed(samples):
        vector=[sample[k] for k in ("ax","ay","az")]
        if not sample["fresh"] or sample["age_ms"]>LIMITS["maximum_age_ms"] or not sample["n"]:
            if not tail:raise ValueError("Final sample not fresh")
            break
        if not LIMITS["norm_squared_min"]<=sum(x*x for x in vector)<=LIMITS["norm_squared_max"]:
            if not tail:raise ValueError("Final sample gravity norm invalid")
            break
        if tail:
            newer=tail[0]
            if not 0<age_span(newer["ms"],sample["ms"])<=LIMITS["maximum_gap_ms"]:break
            if not 0<age_span(newer["n"],sample["n"])<=2000:break
        proposed=[sample]+tail
        if any(max(x[k] for x in proposed)-min(x[k] for x in proposed)>LIMITS["maximum_axis_range_mg"] for k in ("ax","ay","az")):break
        tail=proposed
    span=age_span(tail[-1]["ms"],tail[0]["ms"]) if tail else 0
    if len(tail)<LIMITS["minimum_samples"] or span<LIMITS["minimum_span_ms"]:
        raise ValueError("No sufficiently long stable final hold")
    return {"samples":tail,"span_ms":span,
            "mean_mg":[sum(x[k] for x in tail)/len(tail) for k in ("ax","ay","az")],
            "ranges_mg":[max(x[k] for x in tail)-min(x[k] for x in tail) for k in ("ax","ay","az")],
            "excluded_adjustment_prefix":samples[:len(samples)-len(tail)]}
def signed_axis(axis:int,value:float)->int:return 1+axis*2+(1 if value<0 else 0)
def derive(session:Path)->dict:
    receipt_path=session/"result.json"; uart_path=session/"uart.log"
    receipt=json.loads(receipt_path.read_bytes()); uart=uart_path.read_text(encoding="ascii")
    if not receipt["handlesClosed"] or not receipt["popupEnded"] or not receipt["ownerPoseLabelsConfirmed"]:
        raise ValueError("Require closed capture and three actual Owner pose labels")
    identity=receipt["latest"]["sections"]["ID"]
    if identity["uid"]!="180010000d50335754363720":raise ValueError("Wrong board")
    pieces=re.split(r"(?m)(?=^DIAG1 BEGIN seq=)",uart)
    held={}
    for name in ("flat","right","up"):
        group=receipt["groups"][name]; ready=group["ownerReady"]
        if ready["actor"]!="owner" or ready["action"]!="ready" or ready["stepAtClick"]!=name:
            raise ValueError("Missing Owner pose confirmation: "+name)
        for sample in group["samples"]:
            seq=sample["frameSeq"]
            matches=[p for p in pieces if p.startswith("DIAG1 BEGIN seq="+str(seq)+" ")]
            if len(matches)!=1:raise ValueError("Missing unique DIAG frame")
            piece=matches[0]; end=piece.find("DIAG1 END seq="+str(seq)+"\n")
            if end<0:raise ValueError("Incomplete DIAG frame")
            idline=re.search(r"(?m)^DIAG1 ID .*",piece).group()
            if f"fw={identity['fw']} " not in idline or f"uid={identity['uid']} " not in idline:
                raise ValueError("Identity changed inside pose capture")
            if sample["raw"].strip() not in piece[end:].splitlines():
                raise ValueError("Saved IMU sample not after its complete raw DIAG")
            if "mic_run=0 " not in piece or "linked=0 " not in piece:
                raise ValueError("Product capture/link active")
        held[name]=stable_tail(group["samples"])
    flat=held["flat"]["mean_mg"]; front=max(range(3),key=lambda i:abs(flat[i]))
    if abs(flat[front])<850 or any(abs(flat[i])>150 for i in range(3) if i!=front):
        raise ValueError("Flat pose not cardinal")
    axes={};used={front}
    for name in ("right","up"):
        mean=held[name]["mean_mg"];delta=[mean[i]-flat[i] for i in range(3)]
        axis=max((i for i in range(3) if i!=front),key=lambda i:abs(delta[i]))
        if axis in used or abs(delta[axis])<350 or any(abs(delta[i])>200 for i in range(3) if i not in (axis,front)):
            raise ValueError("Pose does not identify an independent transverse axis")
        if mean[front]*flat[front]<=0:raise ValueError("Unexpected face inversion")
        used.add(axis);axes[name]=signed_axis(axis,delta[axis])
    axes["front"]=signed_axis(front,flat[front])
    packed=0x80|axes["right"]|(axes["up"]<<3)|(((axes["front"]-1)&1)<<6)
    return {"schema":"companion.imu.edge_mount.v1","method":"explicit_stable_suffix_v1",
       "created_at_local":datetime.now(timezone(timedelta(hours=8))).isoformat(timespec="seconds"),
       "result":"EDGE_RAISED_MAP_DERIVED_OFFLINE_NOT_APPLIED","board_uid":identity["uid"],
       "source_firmware":identity["fw"],"limits":LIMITS,"holds":held,
       "signed_axes":axes,"packed_axes":packed,"packed_hex":f"{packed:02x}",
       "original_capture_result":receipt["result"],"original_full_group_failure":receipt.get("calibrationError"),
       "original_failure_retained":True,"scope":"Sparse held gravity samples, face-up and two raised-edge directions",
       "profile_applied":False,"persisted":False,"bias_calibrated":False,
       "portrait_holding_qualified":False,"motion_thresholds_qualified":False,
       "reference_sha256":{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (receipt_path,uart_path)}}
def main()->None:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--session",type=Path,required=True);parser.add_argument("--output",type=Path,required=True)
    args=parser.parse_args();output=args.output.resolve()
    if output.exists():raise ValueError("Output exists; original evidence must not be overwritten")
    result=derive(args.session.resolve())
    output.parent.mkdir(parents=True,exist_ok=True)
    fd,temp=tempfile.mkstemp(prefix=output.name+".",dir=output.parent)
    try:
        with os.fdopen(fd,"w",encoding="utf8") as writer:
            json.dump(result,writer,ensure_ascii=False,indent=2);writer.write("\n");writer.flush();os.fsync(writer.fileno())
        os.replace(temp,output)
    finally:
        if os.path.exists(temp):os.unlink(temp)
    print(json.dumps({"result":result["result"],"axes":result["signed_axes"],"packed":result["packed_hex"],
        "excluded":{k:len(v["excluded_adjustment_prefix"]) for k,v in result["holds"].items()},"output":str(output)}))
if __name__=="__main__":main()

