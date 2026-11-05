"""Build-time electrical qualification. Never infer approval from a PCB value."""
from pathlib import Path
import hashlib
import json

DEFAULT={
    'schema':'companion.wba_v11.power_profile.v2',
    # Owner's hardware reply, 2026-10-08: this assembled board is 100k/68k.
    # Nominal resistance confirmation does not qualify VDDA/headroom or SOC.
    'topOhm':100000, 'bottomOhm':68000, 'referenceMv':1800, 'referenceMinMv':1700,
    'maximumBatteryMv':4350, 'minimumBatteryMv':2800, 'minimumUpdateMv':3600,
    'dividerVerified':False, 'referenceVerified':False, 'chargerPullupsVerified':False,
    'socCurveVerified':False, 'socPoints':[], 'qualificationEvidence':None,
    'recordingStopMv':0, 'recordingResumeMv':0, 'recordingLimitsVerified':False,
}
def validate(value):
    if not isinstance(value,dict) or value.get('schema')!=DEFAULT['schema']:
        raise ValueError('Power profile schema is required')
    if set(value)!=set(DEFAULT): raise ValueError('Power profile fields differ from the explicit qualification schema')
    for key in ('dividerVerified','referenceVerified','chargerPullupsVerified','socCurveVerified','recordingLimitsVerified'):
        if type(value[key]) is not bool: raise ValueError(f'{key} must be a boolean')
    limits={'topOhm':(1,10000000),'bottomOhm':(1,10000000),
        'referenceMv':(1500,3600),'referenceMinMv':(1500,3600),
        'maximumBatteryMv':(2000,5000),'minimumBatteryMv':(1000,5000),'minimumUpdateMv':(1000,5000)}
    for key,(low,high) in limits.items():
        if type(value[key]) is not int or not low<=value[key]<=high: raise ValueError(f'{key} out of range')
    if not value['minimumBatteryMv']<value['maximumBatteryMv'] or not \
       value['minimumBatteryMv']<=value['minimumUpdateMv']<=value['maximumBatteryMv'] or \
       value['referenceMv']<value['referenceMinMv']: raise ValueError('Invalid voltage thresholds/reference range')
    safe=value['maximumBatteryMv']*value['bottomOhm']<=\
        (value['referenceMinMv']-100)*(value['topOhm']+value['bottomOhm'])
    if value['dividerVerified'] and not safe: raise ValueError('Verified divider still exceeds ADC reference/headroom')
    for key in ('recordingStopMv','recordingResumeMv'):
        if type(value[key]) is not int or not 0<=value[key]<=5000:
            raise ValueError(f'{key} out of range')
    stop,resume=value['recordingStopMv'],value['recordingResumeMv']
    if (stop or resume) and not value['minimumBatteryMv']<stop<resume<=value['maximumBatteryMv']:
        raise ValueError('Recording limits must have a valid observation floor and recovery hysteresis')
    if value['recordingLimitsVerified'] and not (stop and resume and safe and
            value['dividerVerified'] and value['referenceVerified']):
        raise ValueError('Recording protection requires qualified limits, safe divider and reference')
    points=value['socPoints']
    if not isinstance(points,list) or (points and (not value['socCurveVerified'] or not 2<=len(points)<=16)) or \
       (value['socCurveVerified'] and not points): raise ValueError('A SOC curve requires explicit qualification and 2..16 points')
    previous=(0,-1)
    for point in points:
        if not isinstance(point,dict) or set(point)!={'millivolts','percent'} or \
           type(point['millivolts']) is not int or type(point['percent']) is not int or not \
           value['minimumBatteryMv']<=point['millivolts']<=value['maximumBatteryMv'] or not \
           0<=point['percent']<=100 or point['millivolts']<=previous[0] or point['percent']<=previous[1]:
            raise ValueError('SOC points must be strictly ascending qualified voltage/percentage pairs')
        previous=(point['millivolts'],point['percent'])
    qualified=any(value[key] for key in ('dividerVerified','referenceVerified','chargerPullupsVerified','socCurveVerified','recordingLimitsVerified'))
    if qualified and (not isinstance(value['qualificationEvidence'],str) or not value['qualificationEvidence'].strip()):
        raise ValueError('Qualified electrical parameters require a measurement/rework evidence reference')
    return safe

def write_header(out:Path, source:Path|None=None):
    value=json.loads(source.read_text(encoding='utf-8-sig')) if source else dict(DEFAULT)
    safe=validate(value)
    points=value['socPoints']
    header=['#ifndef WBA_BOARD_POWER_PROFILE_H','#define WBA_BOARD_POWER_PROFILE_H',
            '#include "wba_power_monitor.h"']
    if points:
        header.append('static const comp_wba_soc_point_t comp_v11_qualified_soc[] = {'+
            ','.join('{'+str(p['millivolts'])+'u,'+str(p['percent'])+'u}' for p in points)+'};')
    header.append('static const comp_wba_power_profile_t comp_v11_qualified_power = {')
    fields={'top_ohm':'topOhm','bottom_ohm':'bottomOhm','reference_mv':'referenceMv',
        'reference_min_mv':'referenceMinMv','maximum_battery_mv':'maximumBatteryMv',
        'minimum_battery_mv':'minimumBatteryMv','minimum_update_mv':'minimumUpdateMv',
        'recording_stop_mv':'recordingStopMv','recording_resume_mv':'recordingResumeMv'}
    header.extend('    .'+dest+'='+str(value[src])+'u,' for dest,src in fields.items())
    header.extend(['    .adc_full_scale=4095u,',
        f'    .soc_points={"comp_v11_qualified_soc" if points else "0"}, .soc_point_count={len(points)}u,',
        '    .divider_verified='+str(value['dividerVerified']).lower()+',',
        '    .reference_verified='+str(value['referenceVerified']).lower()+',',
        '    .charger_pullups_verified='+str(value['chargerPullupsVerified']).lower()+',',
        '    .recording_limits_verified='+str(value['recordingLimitsVerified']).lower(),'};','#endif',''])
    target=out/'wba_board_power_profile.h'; target.write_text('\n'.join(header),encoding='ascii')
    (out/'power-profile.json').write_text(json.dumps(value,indent=2)+'\n',encoding='utf-8')
    return {'parameters':value,'divider_safe':safe,
        'sampling_qualified':value['dividerVerified'] and value['referenceVerified'] and safe,
        'recording_protection_qualified':value['recordingLimitsVerified'],
        'source_path':str(source.resolve()) if source else None,
        'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest() if source else None,
        'generated_header_sha256':hashlib.sha256(target.read_bytes()).hexdigest()}
