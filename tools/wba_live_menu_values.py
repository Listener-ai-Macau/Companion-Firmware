"""Small native three-language labels for values known only at runtime."""
from pathlib import Path
import math
from PIL import Image, ImageDraw
from wba_product_menu_art import font, draw_text
from wba_menu_typography import submenu_value_size, text_width
from wba_menu_translations import localize

ROOT = Path(__file__).resolve().parents[1]
HEADER = ROOT/'app/companion_pendant/runtime/generated/companion_wba_live_menu_values.h'
FEEDBACK_HEADER = ROOT/'app/companion_pendant/runtime/generated/companion_wba_menu_feedback.h'
FEEDBACK_LABELS = [
    ('','',''), ('处理中','處理中','Working'), ('等待配对','等待配對','Waiting for pairing'),
    ('正在清空','正在清空','Clearing recordings'), ('设置已保存','設定已儲存','Settings saved'),
    ('已清空','已清空','Recordings cleared'), ('已恢复默认','已恢復預設','Defaults restored'),
    ('安全连接就绪','安全連線就緒','Secure connection ready'),
    ('暂不可用','暫時無法使用','Unavailable'), ('设备忙，请稍候','裝置忙，請稍候','Busy, please wait'),
    ('失败，请重试','失敗，請重試','Failed, please retry'),
    ('擦除失败，重试中','抹除失敗，重試中','Erase failed, retrying'),
    ('配对超时，请重试','配對逾時，請重試','Pairing timed out, retry'),
]

def build_feedback():
    width,height,stride=176,14,22
    lines=['/* Generated static feedback for real runtime menu outcomes. */',
        '#ifndef COMPANION_WBA_MENU_FEEDBACK_H','#define COMPANION_WBA_MENU_FEEDBACK_H',
        '#include <stdint.h>',f'#define COMP_WBA_MENU_FEEDBACK_COUNT {len(FEEDBACK_LABELS)}u',
        '#define COMP_WBA_MENU_FEEDBACK_HEIGHT 14u','#define COMP_WBA_MENU_FEEDBACK_STRIDE 22u',
        f'static const uint8_t comp_wba_menu_feedback[3][{len(FEEDBACK_LABELS)}][308] = {{']
    all_widths=[]
    for locale in ('en','zh_cn','zh_tw'):
        lines.append('{');widths=[]
        for triple in FEEDBACK_LABELS:
            label=triple[2 if locale=='en' else 1 if locale=='zh_tw' else 0]
            im=Image.new('1',(width,height),1);d=ImageDraw.Draw(im)
            size=submenu_value_size(label);required=text_width(label,size,submenu=True)
            if required>width:raise ValueError('Feedback overflow: '+label)
            draw_text(d,(0,0),label,size,width=width,submenu=True)
            widths.append(required)
            lines.append('{'+','.join(f'0x{v:02X}' for v in im.tobytes())+'},')
        lines.append('},');all_widths.append(widths)
    lines+=['};',f'static const uint8_t comp_wba_menu_feedback_advance[3][{len(FEEDBACK_LABELS)}] = {{']
    lines+=['{'+','.join(map(str,w))+'},' for w in all_widths]
    lines+=['};','#endif','']
    FEEDBACK_HEADER.write_text('\n'.join(lines),encoding='ascii')
    return FEEDBACK_HEADER
LABELS = [
    ('待机','Ready'), ('准备中','Preparing'), ('录音中','Recording'),
    ('保存中','Saving'), ('已取消','Cancelled'), ('已保存','Saved'),
    ('同步中','Syncing'), ('已同步','Synced'), ('录音失败','Recording failed'),
    ('暂不可用','Unavailable'), ('请稍候','Please wait'),
]
WIDTH, HEIGHT = 128, 14

def build():
    build_feedback()
    lines=['/* Generated native menu values; white background, black ink. */',
           '#ifndef COMPANION_WBA_LIVE_MENU_VALUES_H', '#define COMPANION_WBA_LIVE_MENU_VALUES_H',
           '#include <stdint.h>', '#define COMP_WBA_LIVE_VALUE_WIDTH 128u',
           '#define COMP_WBA_LIVE_VALUE_HEIGHT 14u',
           '#define COMP_WBA_LIVE_VALUE_STRIDE 16u',
           'static const uint8_t comp_wba_live_values[3][11][224] = {']
    localized_advances=[]
    for locale in ('en','zh_cn','zh_tw'): # persisted EN=0, ZH=1, ZH_TW=2
        lines.append('{')
        advances=[]
        for pair in LABELS:
            label=localize(pair[1 if locale=='en' else 0],locale);im=Image.new('1',(WIDTH,HEIGHT),1);d=ImageDraw.Draw(im)
            size=submenu_value_size(label)
            required=text_width(label,size,submenu=True)
            if required>(128 if locale=='en' else 84):
                raise ValueError(f'Live menu label overflow: {label}')
            draw_text(d,(0,0),label,size,width=WIDTH,submenu=True)
            advances.append(required)
            lines.append('{'+','.join(f'0x{v:02X}' for v in im.convert('1',dither=Image.Dither.NONE).tobytes())+'},')
        lines.append('},')
        localized_advances.append(advances)
    lines += ['};','static const uint8_t comp_wba_live_value_advance[3][11] = {']
    lines += ['{'+','.join(map(str,a))+'},' for a in localized_advances]
    lines += ['};', 'static const char comp_wba_value_chars[] = "0123456789%KBM.- :";']
    # The status rail keeps its compact 12px clock; actual row values use the
    # same 12px face as the authored subordinate values. Separate atlases prevent a
    # five-character 24h clock from colliding with recording/hold status cues.
    for prefix,size,bold,width,height in (('value',12,False,16,14),('clock',12,False,12,12)):
        lines.append(f'static const uint8_t comp_wba_{prefix}_digits[18][{2*height}] = {{')
        advances=[]
        selected=font(size,bold)
        for char in '0123456789%KBM.- :':
            im=Image.new('1',(width,height),1);d=ImageDraw.Draw(im)
            box=selected.getbbox(char)
            if box[2]>width:
                raise ValueError('Numeric menu glyph overflow')
            advances.append(math.ceil(selected.getlength(char)))
            top=selected.getbbox('0')[1]
            if box[3]-top>height or box[1]<top and char.strip():
                raise ValueError(f'Numeric menu glyph vertical overflow: {char}')
            d.fontmode='1'
            d.text((0,-top),char,font=selected,fill=0)
            lines.append('{'+','.join(f'0x{v:02X}' for v in im.tobytes())+'},')
        lines += ['};', f'static const uint8_t comp_wba_{prefix}_advance[18] = {{'+
                  ','.join(map(str,advances))+'};']
    # A native 24px count for destructive confirmation; no scaled bitmap.
    lines += ['#define COMP_WBA_COUNT_HEIGHT 25u','#define COMP_WBA_COUNT_WIDTH 24u',
              '#define COMP_WBA_COUNT_STRIDE 3u',
              'static const uint8_t comp_wba_count_digits[10][75] = {']
    advances=[];selected=font(24);top=selected.getbbox('0')[1]
    for char in '0123456789':
        box=selected.getbbox(char)
        if box[2]>24 or box[3]-top>25:raise ValueError('Confirmation digit overflow')
        im=Image.new('1',(24,25),1);d=ImageDraw.Draw(im);d.fontmode='1'
        d.text((0,-top),char,font=selected,fill=0)
        lines.append('{'+','.join(f'0x{v:02X}' for v in im.tobytes())+'},')
        advances.append(math.ceil(selected.getlength(char)))
    lines += ['};','static const uint8_t comp_wba_count_advance[10] = {'+
              ','.join(map(str,advances))+'};','#endif','']
    HEADER.write_text('\n'.join(lines),encoding='ascii')
    return HEADER

if __name__ == '__main__': print(build())
