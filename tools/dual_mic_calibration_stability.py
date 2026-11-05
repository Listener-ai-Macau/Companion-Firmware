"""Saved-pair temporal admission shared by publisher and build input reader.

This is metadata consistency and source-window agreement, not acoustic or
speech-fidelity qualification. It never reads a device or changes audio.
"""
import math,re

MIN_WINDOW_FRAMES=8006
MAX_DELAY_SPREAD_Q8=64
MAX_GAIN_SPREAD_DB=1.0

def require(ok,message):
    if not ok:raise ValueError('Temporal calibration '+message)

def integer(value,lo,hi):
    require(type(value)is int and lo<=value<=hi,'has invalid integer metadata')
    return value

def validate(config):
    proof=config.get('temporalStability')
    require(isinstance(proof,dict),'needs two independent source-window results; regenerate from the retained original')
    require(type(proof.get('schema'))is int and proof['schema']==1 and
        proof.get('result')=='TWO_DISJOINT_WINDOWS_AGREE_WITH_FULL_PAIR','has invalid proof identity')
    require(type(proof.get('sourceSamplesDiscarded'))is int and proof['sourceSamplesDiscarded']==0,
        'must preserve the full original source interval')
    require(proof.get('maximumDelaySpreadQ8')==MAX_DELAY_SPREAD_Q8 and
        type(proof.get('maximumDelaySpreadQ8'))is int and
        type(proof.get('maximumGainSpreadDb'))in(int,float) and
        proof['maximumGainSpreadDb']==MAX_GAIN_SPREAD_DB,'has unsupported agreement limits')
    n=integer(config.get('synchronousSamples'),2*MIN_WINDOW_FRAMES-6,31994)+6
    windows=proof.get('windows');require(isinstance(windows,list)and len(windows)==2,'needs exactly two disjoint windows')
    cursor=0
    for row in windows:
        require(isinstance(row,dict),'has an invalid window')
        first=integer(row.get('firstSample'),0,n);end=integer(row.get('endSample'),0,n)
        require(first==cursor and end-first>=MIN_WINDOW_FRAMES,'windows must independently cover the entire original')
        cursor=end
        digest=row.get('probeLogSha256')
        require(isinstance(digest,str)and re.fullmatch('[0-9a-f]{64}',digest)is not None and set(digest)!={'0'},
            'needs each exact source-window probe hash')
    require(cursor==n,'windows do not cover the original source')
    estimates=[config,*windows]
    for row in estimates:
        integer(row.get('delayQ8'),-640,640);integer(row.get('rightGainQ15'),16384,65535)
        require(type(row.get('invertRight'))is bool,'has invalid polarity')
    require(len({x['invertRight']for x in estimates})==1,'polarity changes; retain baseline')
    delay=max(x['delayQ8']for x in estimates)-min(x['delayQ8']for x in estimates)
    gain_db=20*math.log10(max(x['rightGainQ15']for x in estimates)/min(x['rightGainQ15']for x in estimates))
    require(delay<=MAX_DELAY_SPREAD_Q8,'delay changes by more than0.25samples; retain baseline')
    require(gain_db<=MAX_GAIN_SPREAD_DB,'gain changes by more than1dB; retain baseline')
    require(type(proof.get('delaySpreadQ8'))is int and proof['delaySpreadQ8']==delay and
        type(proof.get('gainSpreadDb'))in(int,float) and math.isfinite(proof['gainSpreadDb']) and
        abs(proof['gainSpreadDb']-gain_db)<1e-12,'reported agreement differs from the window results')
    return proof
