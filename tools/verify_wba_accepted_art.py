"""Compare every current state to the accepted gen29 bank; permit only About text."""
from pathlib import Path
import hashlib,json
ROOT=Path(__file__).resolve().parents[1]
def main():
    before=ROOT/'.cache/wba-ui-polish/gen29-profile.json'
    after=ROOT/'.cache/wba-product-resources/profile.json'
    a=json.loads(before.read_text()); b=json.loads(after.read_text())
    if set(a['states'])!=set(b['states']): raise RuntimeError('Accepted state coverage changed')
    changed=[key for key,value in a['states'].items() if value['sha256']!=b['states'][key]['sha256']]
    if any(not key.startswith('menu_ui_') or '_s7_' not in key for key in changed):
        raise RuntimeError('Accepted expression/accessory/wave/menu pixels changed outside About')
    sources=[before,after,ROOT/'tools/wba_product_menu_art.py',Path(__file__)]
    result={'result':'PASS_ACCEPTED_ART_PRESERVATION','beforeGeneration':a['generation'],
        'afterGeneration':b['generation'],'statesCompared':len(a['states']),'changedStates':changed,
        'scope':'UI bank: only About version text changed. Runtime status indicators have separate compositor ownership tests.',
        'hardwareAcceptance':'NOT_RUN','source_sha256':{p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in sources}}
    target=ROOT/'.cache/wba-ui-polish/preservation-result.json'
    target.write_text(json.dumps(result,indent=2)+'\n')
    print(f"PASS_ACCEPTED_ART_PRESERVATION states={len(a['states'])} identical={len(a['states'])-len(changed)} about_changes={len(changed)}")
if __name__=='__main__': main()
