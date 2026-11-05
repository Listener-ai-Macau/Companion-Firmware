"""Generate the compact full-storage labels using the existing WBA menu font."""
from pathlib import Path
from PIL import Image, ImageDraw
from wba_menu_typography import draw_text

rows = []
for text in ('已满', '已滿'):
    image = Image.new('1', (32, 16), 1)
    draw_text(ImageDraw.Draw(image), (0, 0), text, 14, width=32, submenu=True)
    rows.append(image.tobytes())
out = Path(__file__).resolve().parents[1] / 'app/companion_pendant/runtime/generated/companion_storage_full_labels.h'
out.write_text('/* Native 14px WBA menu glyphs, generated with the existing menu typography. */\n'
    '#ifndef COMPANION_STORAGE_FULL_LABELS_H\n#define COMPANION_STORAGE_FULL_LABELS_H\n'
    'static const uint8_t comp_storage_full_labels[2][64]={\n'
    + ''.join('{' + ','.join('0x%02x' % b for b in row) + '},\n' for row in rows)
    + '};\n#endif\n', encoding='ascii')
