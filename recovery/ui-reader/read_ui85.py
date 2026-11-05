"""Recover only the installed public UI bank with a temporary SRAM reader.

Default is an offline plan. --execute uses a separately claimed board lease.
This interrupts the application and software-resets it afterward. It is not
wireless acceptance, firmware installation, pairing or recording recovery.
"""
from pathlib import Path
import argparse,ctypes as c,hashlib,json,struct,subprocess,sys,zlib,shutil,tempfile
ROOT=Path('C:/Users/Billy/Desktop/Denzic/Companion')
SRC=ROOT/'firmware-recovery'
sys.path[:0]=[str(ROOT/'tools'),str(SRC/'tools')]
import board_turn
from cube_programmer_api_session import Session
from verify_wba_factory_loader import Loader,Storage

UI_BYTES=950272
UID='120011000d50335754363720'
SERIAL='004400403532510B31333430'
ITEM='Capture取回UI85公开资源；临时RAM只读，非产品无线验收'
BUILD=SRC/'.cache/ui-reader-build-r2'
EXPECTED='5c16dfabdb1a59e4280f2eb867050d870273c717dbf4a571e3ee9f72ccb12b09'

def lease():
    with board_turn.turn_lock():
        state=board_turn.load_state()
        if state.get('holder')!='codex' or state.get('item')!=ITEM:
            raise RuntimeError('The existing exclusive board lease is not this resource read')

def read_ui(session,offset,size):
    if not 0<=offset<UI_BYTES or not 0<size<=min(16384,UI_BYTES-offset):
        raise ValueError('Read outside the public resource bank or SRAM buffer bound')
    lease();pointer=c.POINTER(c.c_ubyte)();owned=False
    try:
        rc=session.api.readMemory(0x90000000+offset,c.byref(pointer),size)
        owned=rc==0;session.checked(rc,'public UI read')
        if not pointer:raise RuntimeError('ST did not return the public resource bytes')
        return c.string_at(pointer,size)
    finally:
        if owned and pointer:session.api.freeLibraryMemory(c.cast(pointer,c.c_void_p))

def root_info(data):
    if len(data)!=128 or data[:8]!=b'CUIR\x01\x00\x80\x00' or zlib.crc32(data[:124])!=struct.unpack_from('<I',data,124)[0]:
        raise ValueError('Invalid installed resource root')
    return {'generation':struct.unpack_from('<I',data,8)[0],
            'cempBytes':struct.unpack_from('<I',data,12)[0],
            'blobOffset':struct.unpack_from('<I',data,16)[0],
            'blobBytes':struct.unpack_from('<I',data,20)[0],
            'blobCrc':struct.unpack_from('<I',data,24)[0],
            'manifestBytes':struct.unpack_from('<I',data,32)[0],
            'manifestCrc':struct.unpack_from('<I',data,36)[0],
            'resourceId':data[44:76].hex().upper()}

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--execute',action='store_true')
    parser.add_argument('--output',type=Path,default=SRC/'.cache/ui85-board-read')
    args=parser.parse_args()
    report=json.loads((BUILD/'result.json').read_text())
    loader=BUILD/report['loader']
    assert report['write_bytes']==0 and report['read_bytes']==UI_BYTES
    assert hashlib.sha256(loader.read_bytes()).hexdigest()==report['loader_sha256']
    plan={'operation':'READ_EXISTING_PUBLIC_UI_ONLY','uid':UID,'stLink':SERIAL,
          'virtualAddress':'0x90000000','bytes':UI_BYTES,'expectedGeneration':85,
          'expectedHistoricalSha256':EXPECTED,'readerSha256':report['loader_sha256'],
          'readOnlyHostBoundaryTests':'PASS','temporaryReaderPlacement':'SRAM1 only; ELF LOAD ranges checked by builder',
          'effects':['NORMAL/SWreset debugger connection stops application','temporary SRAM reader initializes SPI3/clocks','restore debug register and software reset original firmware after read'],
          'nonvolatileMutationCalls':[],'deviceIO':False}
    if not args.execute:print(json.dumps(plan,ensure_ascii=False,indent=2));return
    lease();args.output.mkdir(parents=True,exist_ok=False)
    state={**plan,'deviceIO':True,'phase':'CONNECTING','result':'IN_PROGRESS'}
    def save():
        (args.output/'result.json').write_text(json.dumps(state,ensure_ascii=False,indent=2)+'\n',encoding='utf8',newline='\n')
    save()
    loader_name=None;debug=None;session=None
    try:
        with tempfile.TemporaryDirectory(prefix='capture-ui-read-') as loader_tmp,Session(SERIAL,args.output,lease,connection_mode=0,access_port=1) as session:
            actual=session.read(0x0BF90700,12,'uid.bin').hex()
            if actual!=UID:raise RuntimeError('Fixed board UID differs')
            debug=int.from_bytes(session.read(0xE0044008,4,'debug-before.bin'),'little')
            session.word(0xE0044008,debug|(1<<12))
            try:
                external=Path(loader_tmp)/'ExternalLoader';external.mkdir()
                shutil.copy2(loader,external/loader.name)
                session.api.setLoadersPath(str(Path(loader_tmp)).encode())
                session.api.getExternalLoaders.argtypes=[c.c_char_p,c.POINTER(c.POINTER(Storage))]
                session.api.getExternalLoaders.restype=c.c_int
                storage=c.POINTER(Storage)()
                session.checked(session.api.getExternalLoaders(str(Path(loader_tmp)).encode(),c.byref(storage)),'read-only loader inventory')
                if not storage or storage.contents.count!=1:raise RuntimeError('Temporary reader directory is incomplete')
                session.api.setExternalLoaderPath.argtypes=[c.c_char_p,c.POINTER(c.POINTER(Loader))]
                session.api.setExternalLoaderPath.restype=None
                session.api.removeExternalLoader.argtypes=[c.c_char_p]
                session.api.removeExternalLoader.restype=None
                loaded=c.POINTER(Loader)()
                session.api.setExternalLoaderPath(loader.name.encode(),c.byref(loaded))
                if not loaded:raise RuntimeError('ST rejected the temporary read-only loader')
                info=loaded.contents
                if info.start!=0x90000000 or info.size!=UI_BYTES or info.name.decode()!='Companion_UI85_READ_ONLY':
                    raise RuntimeError('Unexpected SRAM reader geometry')
                loader_name=info.path.decode() or str(loader)
                state['phase']='PUBLIC_ROOT_READ';save()
                root=root_info(read_ui(session,UI_BYTES-8192,128))
                if root['generation']!=85:raise RuntimeError('Installed UI generation is not85')
                state['root']=root;state['phase']='PUBLIC_BANK_READ';save()
                data=bytearray()
                for at in range(0,UI_BYTES,16384):
                    data.extend(read_ui(session,at,min(16384,UI_BYTES-at)))
                    if at%131072==0:print('Recovered public resource bytes',len(data),flush=True)
                digest=hashlib.sha256(data).hexdigest()
                (args.output/'ui-partition.bin').write_bytes(data)
                state.update(sha256=digest,bytesRead=len(data),historicalImageMatches=digest==EXPECTED)
                if digest!=EXPECTED:raise RuntimeError('Public bank saved, but hash differs from historical UI85; no source identity claim')
                state.update(result='PASS_EXACT_HISTORICAL_UI85_RECOVERED',phase='PUBLIC_BANK_VERIFIED');save()
            finally:
                if loader_name:
                    session.api.removeExternalLoader(loader_name.encode());loader_name=None
                if debug is not None:session.word(0xE0044008,debug)
                session.reset();state['originalFirmwareResetRequested']=True;save()
    except Exception as error:
        state.update(result='FAILED_UI_RESOURCE_READ',error=str(error));save();raise
    finally:
        state['probeHandlesClosed']=True;save()
    print(json.dumps(state,ensure_ascii=False,indent=2))

if __name__=='__main__':main()
