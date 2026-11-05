"""Native 200px WBA menu art, aligned with screen_menu.c row/variant semantics.

The renderer supplies live catalog values and status; unavailable hardware
measurements remain '--'. Text is rasterized once, not rendered by a web font.
"""
from functools import lru_cache
from pathlib import Path
import json
import re
from PIL import Image, ImageDraw
from wba_menu_icons import category_icon, chevron, back_button, NativeInk, radio_control, switch_control
from wba_menu_typography import font, draw_text, text_width, submenu_font, submenu_value_size
from wba_menu_locale_contract import extend, LOCALES
from wba_menu_translations import localize

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / 'app/companion_pendant/runtime/generated/companion_browser_interaction_contract.h'
extend(CONTRACT)
TITLES = [('设置','Settings'),('录音','Recording'),('显示','Display'),('连接','Connection'),
          ('偏好','Preferences'),('录音手势','Record gesture'),('语言','Language'),('关于','About'),
          ('互动','Interaction'),('存储','Storage'),('电源','Power'),('清空录音','Clear recordings'),('恢复默认','Restore defaults')]
LABELS = [('', ''), ('录音','Recording'),('显示','Display'),('互动','Interaction'),('连接','Connection'),
 ('存储','Storage'),('电源','Power'),('偏好','Preferences'),('关于','About'),
 ('录音状态','Recording status'),('启动手势','Start gesture'),('录音模式','Record mode'),('录音时限','Time limit'),
 ('静音自动停止','Stop on silence'),('音频格式','Audio format'),('麦克风','Microphone'),
 ('时钟格式','Clock format'),('屏幕','Panel'),('分辨率','Resolution'),('状态栏','Status bar'),
 ('连接状态','Link status'),('开始配对','Start pairing'),('切换蓝牙','Toggle Bluetooth'),('自动重连','Auto reconnect'),
 ('设备名称','Device name'),('重置名称','Reset name'),('无线连接','Wireless'),
 ('语言','Language'),('时区','Time zone'),('安静时段','Quiet hours'),('恢复默认','Restore defaults'),
 ('左下角双击','Corner double tap'),('左下角右拉','Corner pull right'),('简体中文','简体中文'),('English','English'),
 ('产品','Product'),('固件版本','Firmware'),('界面版本','UI version'),('更新方式','Updates'),('设备标识','Device ID'),
 ('触摸','Touch'),('录音手势','Record gesture'),('互动程度','Activity'),('视线跟随','Follow touch'),('自然眨眼','Natural blink'),('菜单入口','Open menu'),
 ('录音数量','Recordings'),('已用空间','Space used'),('清空录音','Clear recordings'),('存储介质','Storage medium'),
 ('录音容量','Recording capacity'),('资源容量','UI capacity'),('电量','Battery'),('充电状态','Charging'),('自动休眠','Auto sleep'),
 ('现在休眠','Sleep now'),('唤醒方式','Wake up'),('全部录音','All recordings'),('确认清空','Confirm clear'),('返回','Back'),
 ('默认设置','Default settings'),('确认恢复','Confirm restore'),('繁體中文','繁體中文')]

def rows():
    text=CONTRACT.read_text(encoding='utf-8')
    block=text.split('companion_browser_menu_rows',1)[1].split('};',1)[0]
    result=[tuple(map(int,m)) for m in re.findall(r'\{(\d+)u,\s*(\d+)u,\s*(\d+)u,\s*(\d+)u,\s*(\d+)u\}',block)]
    if len(result)!=64: raise ValueError('Menu row contract changed')
    return result

ROWS=rows()
CONFIRM_BUTTONS={1:(104,165,187,194),2:(12,165,94,194)}
CONFIRM_COUNT_TOP=110
MENU_VISIBLE_ROWS=4
MENU_ROW_TOP=52
MENU_ROW_HEIGHT=34
MENU_VALUE_TOP=9
MENU_VALUE_LEFT=100
MENU_VALUE_WIDTH=84
MENU_STACK_VALUE_TOP=18
MENU_STACK_VALUE_LEFT=16
MENU_STACK_VALUE_WIDTH=168

def write_geometry_header():
    path=ROOT/'app/companion_pendant/runtime/generated/companion_wba_menu_geometry.h'
    lines=['/* Generated from the native menu drawing coordinates. */',
           '#ifndef COMPANION_WBA_MENU_GEOMETRY_H','#define COMPANION_WBA_MENU_GEOMETRY_H',
           f'#define COMP_WBA_CONFIRM_COUNT_TOP {CONFIRM_COUNT_TOP}u',
           f'#define COMP_WBA_MENU_VISIBLE_ROWS {MENU_VISIBLE_ROWS}u',
           f'#define COMP_WBA_MENU_ROW_TOP {MENU_ROW_TOP}u',
           f'#define COMP_WBA_MENU_ROW_HEIGHT {MENU_ROW_HEIGHT}u',
           f'#define COMP_WBA_MENU_BODY_BOTTOM {MENU_ROW_TOP+MENU_VISIBLE_ROWS*MENU_ROW_HEIGHT}u',
           f'#define COMP_WBA_MENU_VALUE_TOP {MENU_VALUE_TOP}u',
           f'#define COMP_WBA_MENU_VALUE_LEFT {MENU_VALUE_LEFT}u',
           f'#define COMP_WBA_MENU_VALUE_WIDTH {MENU_VALUE_WIDTH}u',
           f'#define COMP_WBA_MENU_STACK_VALUE_TOP {MENU_STACK_VALUE_TOP}u',
           f'#define COMP_WBA_MENU_STACK_VALUE_LEFT {MENU_STACK_VALUE_LEFT}u',
           f'#define COMP_WBA_MENU_STACK_VALUE_WIDTH {MENU_STACK_VALUE_WIDTH}u']
    for index,name in ((1,'CONFIRM'),(2,'CANCEL')):
        for key,value in zip(('LEFT','TOP','RIGHT','BOTTOM'),CONFIRM_BUTTONS[index]):
            lines.append(f'#define COMP_WBA_{name}_{key} {value}u')
    lines += ['#endif','']
    path.write_text('\n'.join(lines),encoding='ascii')
    return path

def confirmation_art(d,screen,locale,phase,item):
    tr=lambda zh,en:localize(en if locale=='en' else zh,locale)
    ink=NativeInk(d)
    if screen==11:
        ink.roundrect((87,53,112,80),4,stroke=2.2)
        ink.roundrect((94,47,105,53),2.5,stroke=2.0)
        ink.line([(83,53),(116,53)],width=2.4)
        for xx in (94,100,106):ink.line([(xx,60),(xx,73)],width=2.0)
        centered_text(d,100,90,tr('全部录音','All recordings'),14,width=168)
        centered_text(d,100,CONFIRM_COUNT_TOP,'--',24,width=168)
        note=('此操作不可撤销','This cannot be undone');action=('确认清空','Confirm clear')
    else:
        ink.arc(100,65,15,15,320,width=2.4)
        ink.line([(110,48),(110,58),(120,58)],width=2.0)
        centered_text(d,100,91,tr('默认设置','Default settings'),14,width=168)
        note=('录音文件会保留','Recordings will be kept');action=('确认恢复','Confirm restore')
    centered_text(d,100,145,tr(*note),12,width=178)
    for index,text in ((2,('取消','Cancel')),(1,action)):
        box=CONFIRM_BUTTONS[index];ink.roundrect(box,8,stroke=None if index==1 else 1.8)
        label=tr(*text);size=12 if text_width(label,12)<=76 else 11
        left,_,right,_=font(size).getbbox(label)
        xx=(box[0]+box[2])/2-(right-left)/2-max(0,left)
        draw_text(d,(xx,174),label,size,width=76,fill=1 if index==1 else 0)
    if phase!='normal' and item in CONFIRM_BUTTONS:
        box=CONFIRM_BUTTONS[item]
        d.line((box[0]+8,198,box[2]-8,198),fill=0,width=1)

def centered_text(d,cx,y,text,size,bold=False,width=178,fill=0):
    """Center visible ink rather than the font's invisible advance cell."""
    left,_,right,_=font(size,bold).getbbox(text)
    x=cx-(right-left)/2-max(0,left)
    draw_text(d,(x,y),text,size,bold,width,fill)

def submenu_row(d,y,kind,ident,label,value,selected,enabled,locale):
    """Open two-column rows on the native grid, with no border or dividers."""
    def text(x,top,word,size=14,width=155):
        draw_text(d,(x,top),word,size,width=width,submenu=True)
    if kind==4:
        radio_control(d,24,y+17,selected)
        text(42,y+9,label,width=143)
    elif kind==5:
        text(16,y+9,label,width=131)
        switch_control(d,157,y+10,enabled)
    else:
        end=171 if kind in (1,6) else 184
        size=submenu_value_size(value)
        value_width=text_width(value,size,submenu=True) if value else 0
        # Runtime English status must use the same reserved two-line geometry
        # for both '--' and every longer live value, including Recording failed.
        stacked=(ident==9 and locale=='en') or (
            value and text_width(label,14,submenu=True)+value_width+14>end-16)
        if not value:
            text(16,y+9,label)
        elif stacked:
            text(16,y+1,label,size=submenu_value_size(label),width=end-16)
            text(16,y+MENU_STACK_VALUE_TOP,value,size=size,width=end-16)
        else:
            text(16,y+9,label,width=end-16-value_width-14)
            text(end-value_width,y+MENU_VALUE_TOP,value,size=size,width=value_width)
        if kind in (1,3,7):chevron(d,178,y+17,left=kind==7)
        elif kind==6:
            ink=NativeInk(d)
            ink.line([(179,y+11),(179,y+23)],width=1.2)
            ink.line([(176,y+14),(179,y+11),(182,y+14)],width=1.2)
            ink.line([(176,y+20),(179,y+23),(182,y+20)],width=1.2)

def values(screen,variant,zh):
    def t(a,b): return a if zh else b
    def toggle(on): return t('开','On') if on else t('关','Off')
    gesture=variant//16 if screen==1 else variant//12 if screen==8 else variant if screen==5 else 0
    gest=t('左下角双击','Double tap corner') if not gesture else t('左下角右拉','Pull corner right')
    v={9:'--',10:gest,14:t('16 kHz 录音','16 kHz recording'),15:t('内置','Built-in'),17:t('电子墨水屏','E-ink'),18:'200 × 200',19:t('时钟 · 连接 · 电量','Clock · link · battery'),
       24:t('在 Type 中查看','View in Type'),26:t('蓝牙','Bluetooth'),27:t('简体中文','English'),35:'Companion V1.1',36:'1.1.40',37:'58',38:t('通过 Type','Via Type'),39:t('在 Type 中查看','View in Type'),
       40:t('单点触摸','Single touch'),41:gest,45:t('长按 3 秒','Hold 3 seconds'),46:'',47:'',49:t('机身存储','On-device'),50:'8 MiB',51:'2 MiB',52:'--',53:'--',56:t('触摸 / 拿起','Touch / pick up'),
       57:'',60:t('保留录音','Recordings are kept')}
    if screen==1:
        v.update({11:t('语音','Voice') if (variant//8)%2==0 else t('会议','Meeting'),
                  12:[t('30 分钟','30 min'),t('15 分钟','15 min'),t('60 分钟','60 min'),t('不限时','No limit')][(variant//2)%4],13:toggle(variant%2==0)})
    if screen==2: v[16]='24 h' if variant==0 else '12 h'
    if screen==3: v.update({20:t('已连接','Connected') if variant<2 else t('未连接','Disconnected'),23:toggle(variant%2==0)})
    if screen==4: v.update({28:['UTC+08','UTC+00','UTC−05'][variant//3],29:['23:00–07:00','22:00–08:00',t('关闭','Off')][variant%3]})
    if screen==8: v.update({42:[t('标准','Standard'),t('活泼','Lively'),t('安静','Quiet')][(variant//4)%3],43:toggle((variant//2)%2==0),44:toggle(variant%2==0)})
    if screen==10: v[54]=[t('3 分钟','3 min'),t('5 分钟','5 min'),t('关闭','Off'),t('1 分钟','1 min')][variant]
    return v

@lru_cache(maxsize=4096)
def menu_frame(state):
    m=re.fullmatch(r'menu_ui_(en|zh_cn|zh_tw)_s(\d+)_o(\d+)_(normal|ack|processing|result)(?:_i(\d+))?(?:_v(\d+))?',state)
    if not m: raise ValueError(state)
    locale,ss,oo,phase,ii,vv=m.groups();screen=int(ss);page=int(oo);item=int(ii or 255);variant=int(vv or 0);zh=locale!='en'
    items=[r for r in ROWS if r[0]==screen];vals=values(screen,variant,zh)
    tr=lambda value: localize(value,locale)
    if locale=='zh_tw':vals[27]='繁體中文'
    # Render text directly in monochrome. Thresholding antialiased Chinese
    # glyphs at this size drops strokes before they reach the e-paper panel.
    image=Image.new('1',(200,200),1);d=ImageDraw.Draw(image)
    # y=0..15 belongs to the live production status renderer.
    back_button(d)
    title=tr(TITLES[screen][0 if zh else 1])
    if screen==0 or screen in (11,12):
        title_size=15 if text_width(title,15,True)<=145 else 14
        centered_text(d,100,23,title,title_size,True,145)
    else:
        title_size=16 if text_width(title,16,submenu=True)<=145 else 14
        left,_,right,_=submenu_font(title_size).getbbox(title)
        draw_text(d,(100-(right-left)/2-max(0,left),23),title,title_size,width=145,submenu=True)
    if screen==0:
        # Four equal optical cells, with inert gutters in screen_menu.c.
        # One vertical swipe changes a whole page; no half-grid offsets.
        page=4 if page>=4 else 0
        # Free-standing ink symbols. White gutters retain the four-cell touch
        # behavior without miniature boxes inside the registered cells.
        for _,index,kind,target,ident in items[page:page+4]:
            local=index-page;cx=51+(local%2)*98;top=49+(local//2)*75
            card_bottom=114 if local<2 else 186
            category_icon(d,ident,cx-22,top)
            label=tr(LABELS[ident][0 if zh else 1])
            centered_text(d,cx,top+47,label,15,False,86)
            if phase!='normal' and index==item:
                # Authored feedback resource, not a claim that the runtime
                # dispatches these phases. Keep the gutter and touch bounds.
                d.line((cx-15,card_bottom,cx+15,card_bottom),fill=0,width=1)
        for n in range(2):
            cx=94+n*12
            if n==page//4:NativeInk(d).roundrect((cx-3,192,cx+3,194),1.5)
            else:NativeInk(d).ellipse((cx-1,192,cx+1,194))
        return image.tobytes()
    if screen in (11,12):
        confirmation_art(d,screen,locale,phase,item)
        return image.tobytes()
    # Old resource IDs remain readable, but production navigation uses only
    # complete, non-overlapping pages. No intermediate scrolling rasters.
    page=(page//MENU_VISIBLE_ROWS)*MENU_VISIBLE_ROWS
    visible_items=items[page:page+MENU_VISIBLE_ROWS]
    for _,index,kind,target,ident in visible_items:
        y=MENU_ROW_TOP+(index-page)*MENU_ROW_HEIGHT
        label=tr(LABELS[ident][0 if zh else 1])
        selected=(ident==31 and variant==0) or (ident==32 and variant==1) or (ident==33 and locale=='zh_cn') or (ident==34 and not zh) or (ident==62 and locale=='zh_tw')
        submenu_row(d,y,kind,ident,label,tr(vals.get(ident,'')),selected,vals.get(ident) in ('开','On'),locale)
        if phase!='normal' and index==item:
            # Phase keeps its original row/page and chosen values. A compact
            # side marker reads clearly without additional row boxes.
            d.line((5,y+12,5,y+28),fill=0,width=1)
    if len(items)>MENU_VISIBLE_ROWS:
        # Match the root's quiet page marks. A scrollbar would imply a
        # continuously moving list, which this slow display never renders.
        page_count=(len(items)+MENU_VISIBLE_ROWS-1)//MENU_VISIBLE_ROWS
        for n in range(page_count):
            cx=100+(n-(page_count-1)/2)*12
            if n==page//MENU_VISIBLE_ROWS:NativeInk(d).roundrect((cx-3,192,cx+3,194),1.5)
            else:NativeInk(d).ellipse((cx-1,192,cx+1,194))
    return image.tobytes()

if __name__=='__main__':
    out=ROOT/'.cache/wba-product-resources/menu-review';out.mkdir(parents=True,exist_ok=True)
    variant_counts=(1,32,2,4,9,2,1,1,24,2,4,2,1)
    rendered=0
    # Exercise every production page/variant plus every feedback phase at the
    # real item page. draw_text rejects horizontal or bottom clipping.
    for locale in LOCALES:
        for screen in range(13):
            items=[r for r in ROWS if r[0]==screen];visible=4 if screen==0 else MENU_VISIBLE_ROWS
            for page in range(0,len(items),visible):
                for variant in range(variant_counts[screen]):
                    suffix='' if variant==0 else f'_v{variant}'
                    menu_frame(f'menu_ui_{locale}_s{screen}_o{page}_normal{suffix}');rendered+=1
            for _,item,_,_,_ in items:
                page=(item//visible)*visible
                for phase in ('ack','processing','result'):
                    for variant in range(variant_counts[screen]):
                        suffix='' if variant==0 else f'_v{variant}'
                        menu_frame(f'menu_ui_{locale}_s{screen}_o{page}_{phase}_i{item}{suffix}');rendered+=1
    for locale in LOCALES:
        sheet=Image.new('L',(210*7-10,210*2-10),232)
        for screen in range(13):
            image=Image.frombytes('1',(200,200),menu_frame(f'menu_ui_{locale}_s{screen}_o0_normal')).convert('L')
            sheet.paste(image,((screen%7)*210,(screen//7)*210))
        sheet.resize((sheet.width*2,sheet.height*2),resample=Image.Resampling.NEAREST).save(out/(locale+'.png'))
    (out/'result.json').write_text(json.dumps({'status':'PASS_MENU_ART_SOFTWARE_ONLY',
        'screens':13,'locales':list(LOCALES),'renderedStates':rendered,
        'nativeSize':[200,200],'childRowOrigins':[52,86,120,154],
        'rootLayout':'2x2 grid; vertical page swipe', 'rootPageOffsets':[0,4],
        'rootTileBounds':[[8,46,93,114],[106,46,191,114],[8,121,93,186],[106,121,191,186]],
        'dynamicValueOrigin':[MENU_VALUE_LEFT,MENU_VALUE_TOP],'dynamicValueMaxHeight':14,
        'submenuLayout':'four open two-column rows; one vertical swipe turns one complete page; no follow-finger animation',
        'firmwareVersion':'1.1.40','uiVersion':58,
        'hardwareAcceptance':'NOT_RUN'},indent=2)+'\n',encoding='utf-8')
    print(out)
