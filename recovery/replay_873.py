from pathlib import Path
import json,re,ast
rows=json.loads((Path(__file__).parent/'commands-all.json').read_text())
source=re.search(r"@'\n(.*?)\n'@",rows[873]['cmd'],re.S)[1]
tree=ast.parse(source)
strings=[(n.targets[0].id,ast.literal_eval(n.value)) for n in tree.body if isinstance(n,ast.Assign) and isinstance(n.targets[0],ast.Name) and n.targets[0].id in ('old','new')]
assert [x[0] for x in strings]==['old','new','old','old','new']
p=Path('C:/Users/Billy/Desktop/Denzic/Companion/firmware-recovery/platform/stm32wba55_companion_v11/tests/test_product_recording_segmented.c')
s=p.read_text(encoding='utf8')
# The later calendar patch inserted its checks between the tick and surface lines.
a=strings[0][1].split('\n',1)[1];b=strings[1][1].split('\n',1)[1]
assert s.count(a)==1;s=s.replace(a,b,1)
a=strings[2][1];assert s.count(a)==1;s=s.replace(a,'        key(&app,true,10u);key(&app,false,4u);step(&app,60u);',1)
a=strings[3][1];b=strings[4][1];assert s.count(a)==1;s=s.replace(a,b,1)
p.write_text(s,encoding='utf8',newline='\n')
print('Recovered original 2026-11-05T01:31:04.473Z Capture fixture timing changes')
