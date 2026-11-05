"""Native recording reasons; no changes to the frozen UI80 or pet artwork."""
from pathlib import Path
import hashlib
import json
from PIL import Image, ImageDraw
from build_wba_pet_help import packed
from wba_product_menu_art import draw_text
from wba_menu_typography import submenu_value_size, text_width

LABELS = (
    ('Battery too low', '电量过低', '電量過低'),
    ('Low: finishing', '低电收尾', '低電收尾'),
    ('Power unknown', '电量未知', '電量未知'),
    ('Paused', '已暂停', '已暫停'),
)


def build(out):
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    width, height, stride = 128, 14, 16
    chunks, raw_chunks, offsets, raw_offsets, widths = [], [], [], [], []
    for locale in range(3):
        row, raw_row, advances = [], [], []
        for labels in LABELS:
            label = labels[locale]
            size = submenu_value_size(label)
            advance = text_width(label, size, submenu=True)
            if advance > (128 if locale == 0 else 84):
                raise ValueError('Recording reason exceeds native value field: ' + label)
            image = Image.new('1', (width, height), 1)
            draw_text(ImageDraw.Draw(image), (0, 0), label, size,
                      width=width, submenu=True)
            raw = image.tobytes()
            row.append(sum(map(len, chunks)))
            raw_row.append(sum(map(len, raw_chunks)))
            chunks.append(packed(raw))
            raw_chunks.append(raw)
            advances.append(advance)
        offsets.append(row)
        raw_offsets.append(raw_row)
        widths.append(advances)
    lines = ['/* Generated native recording reasons; no pet artwork. */',
             '#ifndef COMPANION_RECORDING_REASON_LABELS_H',
             '#define COMPANION_RECORDING_REASON_LABELS_H', '#include <stdint.h>',
             f'#define COMP_RECORD_REASON_LABEL_COUNT {len(LABELS)}u',
             '#define COMP_RECORD_REASON_LABEL_HEIGHT 14u',
             '#define COMP_RECORD_REASON_LABEL_STRIDE 16u']
    for condition, parts, indices in (
        ('#if COMPANION_WBA_RECORDING_UI_PACKED', chunks, offsets),
        ('#else', raw_chunks, raw_offsets),
    ):
        data = b''.join(parts)
        lines += [condition, 'static const uint8_t comp_record_reason_bits[] = {']
        lines += [','.join(f'0x{v:02x}' for v in data[i:i+24]) + ','
                  for i in range(0, len(data), 24)]
        lines += ['};', f'static const uint16_t comp_record_reason_offsets[3][{len(LABELS)}] = {{']
        lines += ['{' + ','.join(map(str, row)) + '},' for row in indices]
        lines += ['};']
    lines += ['#endif', f'static const uint8_t comp_record_reason_widths[3][{len(LABELS)}] = {{']
    lines += ['{' + ','.join(map(str, row)) + '},' for row in widths]
    lines += ['};', '#endif', '']
    target = out / 'companion_recording_reason_labels.h'
    target.write_text('\n'.join(lines), encoding='ascii')
    return dict(labels=LABELS, packedBytes=sum(map(len, chunks)),
                rawBytes=sum(map(len, raw_chunks)), widths=widths,
                headerSha256=hashlib.sha256(target.read_bytes()).hexdigest())


if __name__ == '__main__':
    print(json.dumps(build(Path(__file__).resolve().parents[1] /
                          'app/companion_pendant/runtime/generated'), ensure_ascii=False))
