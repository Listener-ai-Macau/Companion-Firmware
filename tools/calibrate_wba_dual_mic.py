#!/usr/bin/env python3
"""Estimate a fixed dual-PDM candidate from a finite current-board DMIC1 probe.

Pure file processing. Never opens UART/BLE, records audio, installs firmware or
turns on processing. A known single broad-band source and actual normal-device
identity are prerequisites, not conclusions of correlation. Review the JSON
and retain the original capture before using its explicit build arguments.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import math
from pathlib import Path
import re

LAGS=range(-3,4)
MAX_SAMPLES=32000

def integer(row:dict[str,str], key:str, minimum:int, maximum:int)->int:
    value=row.get(key,'')
    if not re.fullmatch(r'-?[0-9]{1,20}',value):raise ValueError(f'Missing/invalid {key}')
    n=int(value)
    if not minimum<=n<=maximum:raise ValueError(f'Out of range {key}')
    return n

def wide(row:dict[str,str], prefix:str, signed:bool=False)->int:
    high=integer(row,prefix+'_hi',-(1<<31)if signed else 0,(1<<31)-1 if signed else (1<<32)-1)
    low=integer(row,prefix+'_lo',0,(1<<32)-1)
    value=((high&0xffffffff)<<32)|low
    return value-(1<<64)if signed and value>=(1<<63)else value

def fields(line:str)->dict[str,str]:
    result={}
    for word in line.split()[1:]:
        if '=' not in word:continue
        key,value=word.split('=',1)
        if key in result:raise ValueError('Duplicate probe field')
        result[key]=value
    return result

def parse_probe(text:str, token:int)->dict:
    if len(text)>2_000_000:raise ValueError('Probe log too large')
    blocks=[];current=None
    for line in text.splitlines():
        if not line.startswith('DMIC1 '):continue
        row=fields(line)
        if 'schema'in row:
            if current is not None:blocks.append(current)
            current={'header':row,'lags':{}}
        elif 'lag'in row:
            if current is None:raise ValueError('Unbound lag row')
            lag=integer(row,'lag',-3,3)
            if lag in current['lags']:raise ValueError('Duplicate lag row')
            current['lags'][lag]=row
    if current is not None:blocks.append(current)
    matches=[x for x in blocks if x['header'].get('token')==str(token)]
    if len(matches)!=1:raise ValueError('Need exactly one complete probe for the requested recording token')
    result=matches[0];h=result['header']
    if integer(h,'schema',1,1)!=1 or integer(h,'invalid',0,1):raise ValueError('Discontinuous/invalid probe')
    samples=integer(h,'samples',0,MAX_SAMPLES)
    n=integer(h,'count',0,MAX_SAMPLES)
    if samples<8006 or n!=samples-6:raise ValueError('Insufficient or inconsistent synchronous sample count')
    if set(result['lags'])!=set(LAGS):raise ValueError('Missing lag rows')
    if integer(h,'clip_l',0,MAX_SAMPLES)or integer(h,'clip_r',0,MAX_SAMPLES):raise ValueError('Clipping prevents calibration')
    return result

def estimate(probe:dict, *, known_single_source:bool, max_delay_samples:float=2)->dict:
    if not known_single_source:raise ValueError('Known single broad-band desired source must be explicitly declared')
    if not math.isfinite(max_delay_samples)or not 0<max_delay_samples<=2.5:raise ValueError('Invalid measured-geometry delay bound')
    h=probe['header'];n=int(h['count']);left_sum=wide(h,'ls',True);left_square=wide(h,'lss')
    if abs(left_sum)>n*32768 or left_square>n*32768**2:raise ValueError('Impossible left statistics')
    left_var=n*left_square-left_sum**2
    if left_var<=0 or math.sqrt(left_var)/n<64:raise ValueError('Left source energy insufficient; not a hardware-failure verdict')
    rows=[]
    for lag in LAGS:
        row=probe['lags'][lag];rs=wide(row,'rs',True);rss=wide(row,'rss');cross=wide(row,'cross',True)
        if abs(rs)>n*32768 or rss>n*32768**2:raise ValueError('Impossible right statistics')
        rv=n*rss-rs**2
        if rv<=0 or math.sqrt(rv)/n<64:raise ValueError('Right source energy insufficient; not a hardware-failure verdict')
        cov=n*cross-left_sum*rs;rho=cov/math.sqrt(left_var*rv)
        if abs(rho)>1.000001:raise ValueError('Inconsistent covariance statistics')
        rows.append(dict(lag=lag,correlation=rho,score=abs(rho),rightVariance=rv))
    peak=max(range(len(rows)),key=lambda k:rows[k]['score'])
    if peak in [0,len(rows)-1]:raise ValueError('Correlation peak at search edge; do not guess a larger delay')
    a,b,c=(rows[i]['score']for i in [peak-1,peak,peak+1])
    if b<0.85:raise ValueError('Low channel coherence; retain baseline')
    distant=[row['score']for i,row in enumerate(rows)if abs(i-peak)>1]
    if distant and b-max(distant)<0.04:raise ValueError('Ambiguous/periodic peak; use a broad-band known source')
    denominator=a-2*b+c
    if denominator>=0:raise ValueError('No unique correlation maximum')
    fraction=0.5*(a-c)/denominator
    if abs(fraction)>0.5:raise ValueError('Unstable fractional delay')
    delay=rows[peak]['lag']+fraction
    if abs(delay)>max_delay_samples:raise ValueError('Delay outside caller-provided geometry; check actual source/order')
    gain=math.sqrt(left_var/rows[peak]['rightVariance']);gain_q15=round(gain*32768)
    if not 16384<=gain_q15<=65535:raise ValueError('Gain mismatch outside existing fixed-trim range')
    delay_q8=round(delay*256);invert=rows[peak]['correlation']<0
    args=['--microphone-dual-delay-q8',str(delay_q8),'--microphone-dual-right-gain-q15',str(gain_q15)]
    if invert:args.append('--microphone-dual-invert-right')
    return dict(result='FIXED_FRONT_END_CALIBRATION_CANDIDATE_ONLY',sampleRate=16000,synchronousSamples=n,maxDelaySamples=max_delay_samples,
        delaySamples=delay,delayQ8=delay_q8,rightGainQ15=gain_q15,invertRight=invert,
        lagCorrelations=[dict(lag=row['lag'],correlation=row['correlation'])for row in rows],
        candidateBuildArguments=args,automaticApply=False,physicalNoiseReductionQualified=False,
        speechIntelligibilityQualified=False,speakerIdentityExtraction=False,
        warning='Known-source declaration and identity supplied by caller. Correlation does not prove source identity or denoising; speech/noise A/B and real capture deadlines still required.')

def main()->None:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--probe-log',type=Path,required=True)
    parser.add_argument('--token',type=int,required=True)
    parser.add_argument('--device-uid',required=True)
    parser.add_argument('--firmware-source',required=True)
    parser.add_argument('--known-single-source',action='store_true')
    parser.add_argument('--max-delay-samples',type=float,default=2)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    if not re.fullmatch('[0-9a-fA-F]{24}',args.device_uid)or not re.fullmatch('[0-9a-f]{40}',args.firmware_source):
        parser.error('Explicit normal-device UID and immutable firmware source required')
    if args.output.exists():parser.error('Output exists; retain previous result instead of overwriting')
    raw=args.probe_log.read_bytes();text=raw.decode('utf-8','strict')
    try:result=estimate(parse_probe(text,args.token),known_single_source=args.known_single_source,max_delay_samples=args.max_delay_samples)
    except ValueError as error:
        result=dict(result='CALIBRATION_REFUSED_RETAIN_BASELINE',reason=str(error),automaticApply=False,
            physicalNoiseReductionQualified=False)
    result.update(deviceUid=args.device_uid.lower(),firmwareSource=args.firmware_source,recordingToken=args.token,
        probeLogSha256=hashlib.sha256(raw).hexdigest(),identityCallerDeclared=True,knownSingleSourceCallerDeclared=args.known_single_source)
    args.output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(result,ensure_ascii=False))
    if result['result'].startswith('CALIBRATION_REFUSED'):raise SystemExit(2)

if __name__=='__main__':main()
