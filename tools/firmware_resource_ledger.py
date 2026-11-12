"""Attribute one real WBA ELF to modules without counting LTO aliases/unions twice.

Offline only. Uses ELF symbols, DWARF source lines and top-level struct members.
Unknown/padding and shared allocations remain explicit; not a stack/CPU profiler.
Requires pyelftools (the fixed local dependency cache is also supported).
"""
from __future__ import annotations
import argparse,bisect,collections,hashlib,json,pathlib,re,sys
try:
    import elftools
except ImportError:
    sys.path.insert(0,'E:/CodexData/Companion/.build-cache/deps/python-elftools')
from elftools.elf.elffile import ELFFile

LABELS={
 'ble':'蓝牙协议栈及BLE传输','codec':'Opus/CELT压缩代码与状态',
 'audio':'采音/PDM/播放/提示音','recording':'录音会话/目录/同步/回收',
 'imu':'IMU/Fusion/按键与手势输入','storage':'NOR/OTA/持久设置',
 'runtime':'产品调度/时钟/公共运行状态','visual':'显示/触摸保留数据与代码',
 'hal':'STM32 HAL/时钟/中断/电源','libc':'C库/编译器算术支持',
 'crypto':'公共签名/摘要/校验支持',
 'shared':'音频编码/DMA与OTA互斥共享区','unknown':'未归属/常量池/对齐',
}
def category(source,name):
    s=source.replace('\\','/').lower();n=name.lower()
    if name=='s_opus_encoder_mem':return 'shared'
    if name=='g_pfnVectors':return 'hal'
    if n.startswith(('pointer_','comp_input_','comp_lsm','fusion')):return 'imu'
    if 'gatt'in n:return 'ble'
    if any(x in s for x in ['/opus/','/celt/','/silk/']):return 'codec'
    if any(x in s for x in ['/fusion/','/imu/','recorder_input.h','wba_button.']):return 'imu'
    if any(x in s for x in ['/stm32_wpan/','/ble/','/common/wpan/'])or any(n.startswith(x)for x in ['ll','hci_','aci_','amm_','ble_','bsp_debug','linklayer_']):return 'ble'
    if any(x in n for x in ['gatt_buffer','host_buffer','host_nvm_buffer','host_event_buffer','conn_handle_pool','ble_buff','queue_handle_pool','sw_timer_pool','fw_rslvng','amm_pool','blestack']):return 'ble'
    if any(x in s for x in ['/playback/','/microphone/','/pdm/','microphone_hal','dual_mic_capture'])or n.startswith('byte_sums'):return 'audio'
    if 'opus' in n or 'celt' in n or n.startswith(('clt_','ec_')):return 'codec'
    if any(x in s for x in ['/recording/']):return 'recording'
    if any(x in s for x in ['/update/','/storage/','preferences','power_settings','pet_profile']):return 'storage'
    if any(x in s for x in ['/epaper/','/touch/','pet_','browser_']):return 'visual'
    if '/runtime/'in s or s.endswith(('/product_app.c','/main.c'))or any(x in s for x in ['reset_witness','cpu_duty','cpu_stages','diagnostic','diag_log','clock_target']):return 'runtime'
    if any(x in s for x in ['battery_adc','low_power_target','stm32_seq']):return 'hal'
    if any(x in s for x in ['companion_sha','companion_crc']):return 'crypto'
    if any(x in s for x in ['/drivers/','/cmsis/','/power/'])or n.startswith(('hal_','ll_','system','rcc','pwr')):return 'hal'
    if any(x in s for x in ['/newlib/','/libgcc/','libgcc.a','libc_nano.a','libm.a'])or n.startswith(('__aeabi','__sf','_printf','_svf','_dtoa','_malloc','_free'))or n in ['memcpy','memmove','memset','memcmp','strlen','strcmp','snprintf','vsnprintf']:return 'libc'
    if 'pointer'in n or n.startswith(('comp_lsm','comp_input','fusion')):return 'imu'
    if any(x in n for x in ['microphone','pdm','sai_','speaker','dual_pair']):return 'audio'
    if source.endswith('board_hal.c'):return 'hal'
    return 'unknown'

def member_category(owner,name):
    n=name.lower()
    if owner=='companion_app':
        if n in ['recording','recording_identity','recording_identity_partition','capture_baseline','silence','recording_level','recording_level_enabled']or n.startswith(('capture_','recording_')):return 'recording'
        if n in ['input','button','last_motion_ms','last_imu_wake_sequence','pointer_service_due_ms']:return 'imu'
        if any(x in n for x in ['panel','touch','asset','presenter','resource']):return 'visual'
        if any(x in n for x in ['setting','preference','pet_profile']):return 'storage'
        return 'runtime'
    if any(x in n for x in ['microphone','speaker','pcm_','audio_clock','playback']):return 'audio'
    if any(x in n for x in ['imu','motion','input_taps','input_pointer']):return 'imu'
    if any(x in n for x in ['touch','display','panel']):return 'visual'
    if n=='nor':return 'storage'
    return 'hal'

def attr(die,name):
    seen=set()
    while die is not None and die.offset not in seen:
        seen.add(die.offset)
        if name in die.attributes:return die.attributes[name],die
        ref=next((x for x in ['DW_AT_abstract_origin','DW_AT_specification']if x in die.attributes),None)
        die=die.get_DIE_from_attribute(ref)if ref else None
    return None,None
def typename(die):
    while die.tag in ['DW_TAG_typedef','DW_TAG_const_type','DW_TAG_volatile_type','DW_TAG_restrict_type']:
        die=die.get_DIE_from_attribute('DW_AT_type')
    return die
def sizeof(die):
    die=typename(die)
    if 'DW_AT_byte_size'in die.attributes:return int(die.attributes['DW_AT_byte_size'].value)
    if die.tag=='DW_TAG_pointer_type':return die.cu['address_size']
    if die.tag=='DW_TAG_array_type':
        count=1
        for d in die.iter_children():
            if d.tag!='DW_TAG_subrange_type':continue
            if 'DW_AT_count'in d.attributes:count*=d.attributes['DW_AT_count'].value
            elif 'DW_AT_upper_bound'in d.attributes:count*=d.attributes['DW_AT_upper_bound'].value+1
            else:return 0
        return count*sizeof(die.get_DIE_from_attribute('DW_AT_type'))
    return 0

def analyse(elf_path):
    mapped=[];pending=''
    mapfile=elf_path.with_suffix('.map')
    if mapfile.exists():
        for line in mapfile.read_text(errors='replace').splitlines():
            match=re.match(r'^\s+(\.[\w.$-]+)\s+(0x[0-9a-fA-F]+)\s+(0x[0-9a-fA-F]+)\s+(.+)$',line)
            if match:section,a,size,source=match.groups()
            else:
                match=re.match(r'^\s+(0x[0-9a-fA-F]+)\s+(0x[0-9a-fA-F]+)\s+(.+)$',line)
                if not match or not pending:
                    pending=line.strip()if re.match(r'^\s+\.[\w.$-]+\s*$',line)else ''
                    continue
                section=pending;a,size,source=match.groups()
            pending='';a=int(a,16);size=int(size,16)
            if size and section.startswith(('.text','.rodata','.data','.bss','.sram')):mapped.append((a,a+size,source))
    mapped.sort();mapstarts=[v[0]for v in mapped]
    def map_at(address):
        i=bisect.bisect_right(mapstarts,address)-1
        return mapped[i][2]if i>=0 and address<mapped[i][1]else ''
    with elf_path.open('rb')as stream:
        elf=ELFFile(stream);dw=elf.get_dwarf_info();lines=[];variables=collections.defaultdict(list)
        def file_path(cu,index):
            lp=dw.line_program_for_CU(cu)
            if not lp or index<1 or index>len(lp.header.file_entry):return ''
            f=lp.header.file_entry[index-1];name=f.name.decode(errors='replace');i=f.dir_index
            directory=lp.header.include_directory[i-1].decode(errors='replace')if i else ''
            return directory+'/'+name
        for cu in dw.iter_CUs():
            lp=dw.line_program_for_CU(cu)
            if lp:
                prior=None
                for entry in lp.get_entries():
                    state=entry.state
                    if state is None:continue
                    if prior and state.address>prior.address:lines.append((prior.address,state.address,file_path(cu,prior.file)))
                    prior=None if state.end_sequence else state
            for die in cu.iter_DIEs():
                if die.tag!='DW_TAG_variable':continue
                name,_=attr(die,'DW_AT_name');typ,where=attr(die,'DW_AT_type');decl,declwhere=attr(die,'DW_AT_decl_file')
                if not name:continue
                variables[name.value.decode(errors='replace')].append((die,typename(where.get_DIE_from_attribute('DW_AT_type'))if typ else None,file_path(declwhere.cu,decl.value)if decl else ''))
        lines.sort();starts=[x[0]for x in lines]
        def source_at(address):
            i=bisect.bisect_right(starts,address)-1
            return lines[i][2]if i>=0 and address<lines[i][1]else ''
        raw=[]
        for s in elf.get_section_by_name('.symtab').iter_symbols():
            if s['st_info']['type']not in ['STT_FUNC','STT_OBJECT']or not s['st_size']:continue
            address=s['st_value']&~1 if s['st_info']['type']=='STT_FUNC'else s['st_value'];name=s.name
            source=source_at(address)if s['st_info']['type']=='STT_FUNC'else ''
            declaration=variables.get(name,variables.get(name.split('.lto_priv.')[0],[]))
            if not source and declaration:source=declaration[0][2]
            if category(source,name)=='unknown':
                mapped_source=map_at(address)
                if category(mapped_source,name)!='unknown':source=mapped_source
            raw.append(dict(begin=address,end=address+s['st_size'],name=name,source=source,module=category(source,name)))
        # Struct member intervals replace, rather than add to, the parent symbol.
        members=[]
        for symbol in list(raw):
            owner=symbol['name']
            if owner not in ['companion_app','companion_v11']:continue
            candidates=[v for v in variables[owner]if v[1]and sizeof(v[1])==symbol['end']-symbol['begin']]
            if not candidates:continue
            raw.remove(symbol);struct=candidates[0][1]
            for m in struct.iter_children():
                if m.tag!='DW_TAG_member'or'DW_AT_data_member_location'not in m.attributes:continue
                offset=m.attributes['DW_AT_data_member_location'].value
                if not isinstance(offset,int):continue
                name=m.attributes.get('DW_AT_name');name=name.value.decode()if name else '<union>'
                size=sizeof(m.get_DIE_from_attribute('DW_AT_type'))
                if not size:continue
                record=dict(begin=symbol['begin']+offset,end=symbol['begin']+offset+size,name=owner+'.'+name,source=symbol['source'],module=member_category(owner,name))
                raw.append(record);members.append({**record,'bytes':size})
        rows={k:dict(module=k,label=v,flashBytes=0,ramBytes=0)for k,v in LABELS.items()};intervals=[]
        sections=[]
        for section in elf.iter_sections():
            if not section['sh_flags']&2 or not section['sh_size']or section.name=='.heap_stack':continue
            begin=section['sh_addr'];end=begin+section['sh_size'];ram=begin>=0x20000000
            if not ram and not 0x08000000<=begin<0x08080000:continue
            sections.append(dict(name=section.name,begin=begin,end=end,bytes=end-begin,ram=ram))
            relevant=[s for s in raw if s['begin']<end and s['end']>begin]
            boundaries=sorted({begin,end,*[max(begin,s['begin'])for s in relevant],*[min(end,s['end'])for s in relevant]})
            for a,z in zip(boundaries,boundaries[1:]):
                candidates=[s for s in relevant if s['begin']<=a and s['end']>=z]
                modules={s['module']for s in candidates}
                module=next(iter(modules))if len(modules)==1 else 'unknown'
                size=z-a
                if ram:rows[module]['ramBytes']+=size
                if not ram or section.name=='.data':rows[module]['flashBytes']+=size
                intervals.append(dict(begin=a,end=z,bytes=size,section=section.name,module=module,names=sorted({s['name']for s in candidates}),sources=sorted({s['source']for s in candidates})))
        return dict(modules=sorted(rows.values(),key=lambda x:x['ramBytes'],reverse=True),sections=sections,members=members,intervals=intervals)

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--build',type=pathlib.Path,required=True);p.add_argument('--output',type=pathlib.Path,required=True);p.add_argument('--catalog-receipt',type=pathlib.Path);p.add_argument('--compare',type=pathlib.Path)
    a=p.parse_args();receipt=json.loads((a.build/'result.json').read_text(encoding='utf-8-sig'));elf=a.build/'companion-v11-board-bringup.elf'
    data=analyse(elf);flash=sum(x['flashBytes']for x in data['modules']);ram=sum(x['ramBytes']for x in data['modules'])
    expected_ram=sum(x['bytes']for x in receipt['sram_inspection']['sections']if x['name']!='.heap_stack')
    assert flash==receipt['bin_bytes'],(flash,receipt['bin_bytes']);assert ram==expected_ram,(ram,expected_ram)
    data.update(schema='companion.module-resource-ledger.v1',firmware=receipt['firmware_version'],toolSha256=hashlib.sha256(pathlib.Path(__file__).read_bytes()).hexdigest(),elfSha256=hashlib.sha256(elf.read_bytes()).hexdigest(),flashBytes=flash,staticRamBytes=ram,stackReservedBytes=receipt['stack_reserved_bytes'],externalGeometry=receipt['flash_geometry'],method='Disjoint ELF symbol intervals; LTO aliases counted once. .data counts in Flash load and SRAM runtime. Two composite globals split by actual DWARF member layout; unions counted once. Source attribution is not independently removable size. Unknown/padding explicit. No heap/stack high-water or CPU measurement.')
    data['externalModules']=[dict(label=label,reservedBytes=size)for label,size in [
        ('UI85图片/字库/公开资源及资源根',receipt['flash_geometry']['staticBytes']),
        ('录音身份与目录（含分段目录预留）',65536),('用户/电源设置',12288),
        ('升级/布局/已确认系统收据',24576),('BLE配对与配置封印',12288),
        ('宠物资料保留',8192),('外部复位诊断日志保留',4096),('系统保留',4096)]]
    assert sum(x['reservedBytes']for x in data['externalModules'][1:])==receipt['flash_geometry']['systemBytes']
    if a.compare:
        previous=json.loads(a.compare.read_text(encoding='utf-8-sig'));assert previous['toolSha256']==data['toolSha256'],'Regenerate baseline with this same classifier before comparing'
        old={x['module']:x for x in previous['modules']}
        data['delta']=dict(fromFirmware=previous['firmware'],flashBytes=flash-previous['flashBytes'],staticRamBytes=ram-previous['staticRamBytes'],stackReservedBytes=data['stackReservedBytes']-previous['stackReservedBytes'])
        for x in data['modules']:
            for key in ['flashBytes','ramBytes']:x[key+'Delta']=x[key]-old.get(x['module'],{}).get(key,0)
    if a.catalog_receipt:
        catalog=json.loads(a.catalog_receipt.read_text(encoding='utf-8-sig'))['catalog'];ranges=sorted((x['start'],x['end'])for x in catalog['entries']);merged=[]
        for start,end in ranges:
            if merged and start<=merged[-1][1]:merged[-1][1]=max(end,merged[-1][1])
            else:merged.append([start,end])
        used=sum(z-x for x,z in merged);cursor=receipt['flash_geometry']['payloadBase'];gaps=[]
        for start,end in merged:
            if start>cursor:gaps.append(start-cursor)
            cursor=max(cursor,end)
        if cursor<receipt['flash_geometry']['norBytes']:gaps.append(receipt['flash_geometry']['norBytes']-cursor)
        data['externalRecordingAllocation']=dict(owners=catalog['owners'],reservedExtentBytes=used,arenaBytes=receipt['flash_geometry']['payloadBytes'],unownedBytes=receipt['flash_geometry']['payloadBytes']-used,largestUnownedSpanBytes=max(gaps,default=0),source=str(a.catalog_receipt),limits='Metadata ownership extents, not logical audio content bytes or necessarily already erased/OTA-admissible space.')
    a.output.mkdir(parents=True,exist_ok=True);(a.output/'module-resources.json').write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    summary={k:v for k,v in data.items()if k not in ['intervals','members','sections']}
    (a.output/'module-resources-summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    text=[f'# FW{data["firmware"]} 模块资源账本','',data['method'],'','| 模块 | 内部Flash B | 静态SRAM B |','|---|---:|---:|']
    text.extend(f'| {x["label"]} | {x["flashBytes"]} | {x["ramBytes"]} |'for x in data['modules'])
    text.extend([f'| 合计 | {flash} | {ram} |','',f'另计预留栈：{data["stackReservedBytes"]}B。CPU沿原实测表，不把静态大小转换成CPU占用。','',f'ELF SHA256: {data["elfSha256"]}'])
    text.extend(['','| 外部Flash模块 | 分区/预留B |','|---|---:|'])
    text.extend(f'| {x["label"]} | {x["reservedBytes"]} |'for x in data['externalModules'])
    if 'externalRecordingAllocation'in data:
        alloc=data['externalRecordingAllocation'];text.extend([f'| 录音已占用物理extent | {alloc["reservedExtentBytes"]} |',f'| 录音区未归属extent（非连续空闲保证） | {alloc["unownedBytes"]} |'])
    text.extend(['','OTA不单独重复记一份NOR大区或编码器RAM，按原共享所有权使用。'])
    if 'delta'in data:text.append('本次增量：'+json.dumps(data['delta'],ensure_ascii=False))
    (a.output/'module-resources.md').write_text('\n'.join(text)+'\n',encoding='utf-8')
    print(json.dumps(summary,ensure_ascii=False))
if __name__=='__main__':main()
