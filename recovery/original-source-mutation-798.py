from pathlib import Path
p=Path('platform/stm32wba55_companion_v11/tests/test_product_recording_segmented.c')
s=p.read_text(encoding='utf-8')
s=s.replace('comp_segment_entry_t entry;bool found=false;','comp_segment_entry_t entry={0};bool found=false;')
s=s.replace('key(&app,true,75u);','key(&app,true,COMPANION_WBA_SCREEN_ENABLED?75u:110u);')
p.write_text(s,encoding='utf-8',newline='')