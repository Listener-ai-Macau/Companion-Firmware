"""Apply the WBA language extension to the retained browser interaction base.

The original page/family/gesture identity remains a base identity. This explicit
extension adds locale 2 and item 62 without renumbering any existing wire/item
value or changing character choreography. Re-running the base generator is safe:
the WBA resource build reapplies and validates this extension.
"""
from pathlib import Path

LOCALES=('en','zh_cn','zh_tw')
MARKER='#define COMPANION_WBA_MENU_LANGUAGE_EXTENSION 1u'

def extend(path: Path):
    source=path.read_text(encoding='utf-8')
    changes={
        '#define COMPANION_BROWSER_MENU_ROW_COUNT 63u': '#define COMPANION_BROWSER_MENU_ROW_COUNT 64u',
        '  COMPANION_BROWSER_MENU_ITEM_EN = 34u,': '  COMPANION_BROWSER_MENU_ITEM_EN = 34u,\n  COMPANION_BROWSER_MENU_ITEM_ZH_TW = 62u,',
        '  8u, 7u, 4u, 7u, 4u, 2u, 2u, 5u, 6u, 7u, 5u, 3u, 3u': '  8u, 7u, 4u, 7u, 4u, 2u, 3u, 5u, 6u, 7u, 5u, 3u, 3u',
        '  {6u, 1u, 4u, 255u, 34u},': '  {6u, 1u, 4u, 255u, 34u},\n  {6u, 2u, 4u, 255u, 62u},',
        'static const char *const locales[2] = {"en", "zh_cn"};': 'static const char *const locales[3] = {"en", "zh_cn", "zh_tw"};',
        'destination_size == 0u || locale >= 2u ||': 'destination_size == 0u || locale >= 3u ||',
    }
    if MARKER in source:
        if not all(new in source for new in changes.values()):
            raise ValueError('Incomplete WBA three-language contract extension')
        return
    for old,new in changes.items():
        if source.count(old)!=1:
            raise ValueError('Browser menu base changed; review language extension: '+old)
        source=source.replace(old,new)
    source=source.replace('/* Generated from the fixed browser page. Do not edit. */',
        '/* Generated browser base + tools/wba_menu_locale_contract.py (COMP-REQ-792).\n'
        ' * PAGE/CONTRACT hashes below identify the retained base, not this extension. */\n'+MARKER)
    path.write_text(source,encoding='utf-8',newline='\n')

if __name__=='__main__':
    extend(Path(__file__).resolve().parents[1]/'app/companion_pendant/runtime/generated/companion_browser_interaction_contract.h')
