"""Read the current public Boot/application as a pre-update rollback artifact.

The compact24 application uses external bonds. Reads stop at0x08076000,
below the historical internal NVM as well. No SRAM/private NOR/audio reads.
The existing fixed-board lease and an idle same-version UART proof are needed.
"""
from pathlib import Path
import argparse,hashlib,json,struct,sys
from cube_programmer_api_session import Session

PROJECT=Path('C:/Users/Billy/Desktop/Denzic/Companion')
sys.path.insert(0,str(PROJECT/'tools'))
import board_turn
UID='120011000d50335754363720'
PROBE='004400403532510B31333430'
ITEM='Capture升级前保存现有公开固件回退副本'

def lease():
    with board_turn.turn_lock():
        d=board_turn.load_state()
        if d.get('holder')!='codex' or d.get('item')!=ITEM:raise RuntimeError('Board lease changed')

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--uart-proof',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True);p.add_argument('--execute',action='store_true');a=p.parse_args()
    proof=json.loads(a.uart_proof.read_text());s=proof['snapshot']['sections']
    assert not proof['errors'] and s['ID']['uid']==UID and s['ID']['fw']=='00010477' and s['ID']['ui']==85
    assert s['AUDIO']['mic_run']==0 and s['STORAGE']['erase_active']==0 and s['BLE']['linked']==0 and s['CORE']['faults']=='00000000'
    state={'result':'PLAN_PUBLIC_FIRMWARE_BACKUP','uid':UID,'version':66679,'ui':85,
      'ranges':[{'name':'boot.bin','address':0x08000000,'bytes':24576},
                {'name':'application-padded.bin','address':0x08006000,'bytes':458752}],
      'norReads':0,'recordingPayloadReads':0,'nonvolatileWrites':0,
      'sideEffects':'NORMAL/SWreset debug connection interrupts original App; software reset restores it after read. Separate from wireless acceptance.',
      'qualification':'Application artifact includes erased padding; observed non-erased extent is not claimed to be original build file length.'}
    if not a.execute:print(json.dumps(state,indent=2));return
    lease();a.output.mkdir(parents=True,exist_ok=False)
    def save():(a.output/'result.json').write_text(json.dumps(state,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    save();debug=None
    try:
        with Session(PROBE,a.output,lease,connection_mode=0,access_port=1) as probe:
            try:
                assert probe.read(0x0BF90700,12,'uid.bin').hex()==UID
                debug=int.from_bytes(probe.read(0xE0044008,4,'debug-before.bin'),'little')
                probe.word(0xE0044008,debug|(1<<12))
                state['files']={}
                for r in state['ranges']:
                    data=probe.read(r['address'],r['bytes'],r['name'])
                    state['files'][r['name']]={'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()}
                    if r['name'].startswith('application'):
                        msp,reset=struct.unpack_from('<II',data)
                        assert 0x20000000<=msp<=0x20020000 and 0x08006001<=reset<0x08076000 and reset&1
                        state.update(initialMsp=hex(msp),resetVector=hex(reset),observedNonErasedExtentBytes=len(data.rstrip(b'\xff')))
                state['result']='PASS_READ_PUBLIC_FIRMWARE_BACKUP';save()
            finally:
                if debug is not None:probe.word(0xE0044008,debug)
                probe.reset();state['originalFirmwareResetRequested']=True;save()
    except Exception as e:state.update(result='FAILED_FIRMWARE_BACKUP',error=str(e));save();raise
    finally:state['probeHandlesClosed']=True;save()
    print(json.dumps(state,ensure_ascii=False,indent=2))

if __name__=='__main__':main()
