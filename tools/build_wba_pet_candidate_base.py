"""Build a candidate-only layout-3 base catalog from frozen drawing code."""
from pathlib import Path
import argparse,importlib.util,json

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--producer',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    args=p.parse_args();root=Path(__file__).resolve().parents[1];out=args.output.resolve()
    path=args.producer.resolve();original=path.read_bytes()
    spec=importlib.util.spec_from_file_location('companion_frozen_pet_base',path)
    producer=importlib.util.module_from_spec(spec);spec.loader.exec_module(producer)
    producer.ROOT=root;producer.OUT=out;producer.PROFILE_DIR=out/'summary'
    producer.GENERATED=out/'companion_wba_resource_contract.h'
    generated=root/'app/companion_pendant/runtime/generated'
    producer.INTERACTION=generated/'companion_browser_interaction_contract.h'
    producer.OLD_CONTRACT=generated/'companion_browser_cemp_contract.h'
    # These unaffected atlases already exist. Candidate base export must not
    # rewrite the other chat's generated files while it compiles firmware.
    producer.write_geometry_header=lambda:generated/'companion_wba_menu_geometry.h'
    producer.build_live_values=lambda:generated/'companion_wba_live_menu_values.h'
    producer.main()
    result=json.loads((out/'profile.json').read_text())
    preserved=json.loads((root/'.cache/wba-product-resources/profile.json').read_text())
    if result['resourceId']!=preserved['resourceId']:raise RuntimeError('Default UI58 pixel identity changed')
    if path.read_bytes()!=original:raise RuntimeError('Frozen drawing source changed')
    print('CANDIDATE_LAYOUT3_BASE_EXPORTED_UI58_PIXEL_IDENTITY_RETAINED')

if __name__=='__main__':main()
