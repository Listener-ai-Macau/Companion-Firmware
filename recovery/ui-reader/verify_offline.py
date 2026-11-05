from pathlib import Path
import ctypes as c,hashlib,json,os,shutil,tempfile
import sys
root=Path('C:/Users/Billy/Desktop/Denzic/Companion/firmware-recovery')
sys.path.insert(0,str(root/'tools'))
from verify_wba_factory_loader import Loader,Storage,Display,InitProgress,LogMessage,LoadBar
build=root/'.cache/ui-reader-build-r2';report=json.loads((build/'result.json').read_text())
source=build/report['loader'];api_dir=Path('C:/ST/STM32CubeProgrammer/api/lib')
with os.add_dll_directory(str(api_dir)),os.add_dll_directory('C:/ST/STM32CubeProgrammer/bin'),tempfile.TemporaryDirectory(prefix='ui-reader-offline-') as tmp:
    external=Path(tmp)/'ExternalLoader';external.mkdir()
    shutil.copy2(source,external/source.name)
    api=c.CDLL(str(api_dir/'CubeProgrammer_API.dll'))
    messages=[]
    callbacks=Display(InitProgress(lambda:None),LogMessage(lambda level,msg:messages.append(msg)),LoadBar(lambda x,n:None))
    api.setDisplayCallbacks.argtypes=[Display];api.setDisplayCallbacks(callbacks)
    api.setVerbosityLevel(3)
    api.setLoadersPath.argtypes=[c.c_char_p];api.setLoadersPath(str(Path(tmp)).encode())
    api.getExternalLoaders.argtypes=[c.c_char_p,c.POINTER(c.POINTER(Storage))]
    api.getExternalLoaders.restype=c.c_int
    storage=c.POINTER(Storage)()
    rc=api.getExternalLoaders(str(Path(tmp)).encode(),c.byref(storage))
    assert rc==0 and storage and storage.contents.count==1,{'rc':rc,'messages':messages}
    api.setExternalLoaderPath.argtypes=[c.c_char_p,c.POINTER(c.POINTER(Loader))];api.setExternalLoaderPath.restype=None
    ptr=c.POINTER(Loader)();api.setExternalLoaderPath(source.name.encode(),c.byref(ptr))
    assert ptr,{'reason':'Installed ST API did not parse the reader ELF','messages':messages}
    info=ptr.contents
    values={'name':info.name.decode(),'start':info.start,'size':info.size,'sectorCount':info.sectors[0].count,'sectorBytes':info.sectors[0].size}
    assert values=={'name':'Companion_UI85_READ_ONLY','start':0x90000000,'size':950272,'sectorCount':232,'sectorBytes':4096},values
    api.deleteLoaders()
result={'result':'PASS_ST_API_OFFLINE_UI_READER_PARSE','metadata':values,'readerSha256':hashlib.sha256(source.read_bytes()).hexdigest(),'probeConnections':0,'deviceIO':False}
(build/'st-offline-parse.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf8',newline='\n')
print(json.dumps(result))
