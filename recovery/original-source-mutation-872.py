from pathlib import Path
p=Path('platform/stm32wba55_companion_v11/wake_events.h');s=p.read_text(encoding='utf-8')
a=s.index('/* Key timing survives');b=s.index('static inline void comp_v11_wake_events_note_isr(',a);c=s.index('/* The foreground caller',b)
helper=s[a:b];note=s[b:c];s=s[:a]+note+helper+s[c:];p.write_text(s,encoding='utf-8',newline='')