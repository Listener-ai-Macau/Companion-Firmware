/* UI84 production menu composition from external, CRC-checked glyphs. */
#include "generated/companion_quiet_timer_geometry.h"
#if COMPANION_WBA_RESOURCE_PROFILE && COMPANION_WBA_UI_EXTERNAL && COMPANION_WBA_RESOURCE_GENERATION >= 84u
static bool COMP_RENDER_UI_SMALL customer_glyph(comp_runtime_renderer_t *r,unsigned locale,unsigned index,
    comp_wba_external_bitmap_t *glyph,unsigned *width)
{
    uint8_t record[8];
    if(locale>=3u || index>=COMP_CUSTOMER_GLYPHS_PER_LOCALE || !r->read_ui || !progress(r) ||
       !r->read_ui(r->context,COMP_CUSTOMER_BITMAP_FLAG+(locale*COMP_CUSTOMER_GLYPHS_PER_LOCALE+index)*8u,record,sizeof(record)))return false;
    const uint32_t offset=(uint32_t)record[0]|((uint32_t)record[1]<<8u);
    glyph->offset=(uint16_t)offset;glyph->bytes=record[2];
    glyph->crc32=(uint32_t)record[4]|((uint32_t)record[5]<<8u)|((uint32_t)record[6]<<16u)|((uint32_t)record[7]<<24u);
    *width=record[3];
    return glyph->bytes && glyph->bytes<=COMP_WBA_EXTERNAL_MAX_GLYPH_BYTES && *width && *width<=176u &&
        offset>=3u*COMP_CUSTOMER_GLYPHS_PER_LOCALE*8u && offset<=COMP_CUSTOMER_ATLAS_BYTES &&
        glyph->bytes<=COMP_CUSTOMER_ATLAS_BYTES-offset;
}
static bool COMP_RENDER_UI_SMALL customer_word(comp_runtime_renderer_t *r,const comp_runtime_frame_t *f,
    uint8_t *frame,unsigned word,int x,int y,int alignment)
{
    comp_wba_external_bitmap_t glyph;unsigned width;
    if(!customer_glyph(r,(unsigned)f->menu.language,word,&glyph,&width))return false;
    if(alignment==1)x-=(int)width;else if(alignment==2)x-=(int)width/2;
    return x>=0 && y>=0 && bitmap_paint_source(r,frame,&glyph,22u,width,16u,(unsigned)x,(unsigned)y,COMP_CUSTOMER_BITMAP_FLAG);
}
/* Crop only a whole existing first word. Stride/CRC/199-byte streaming and
 * every original raster pixel remain under the existing atlas reader. */
static bool customer_short_word(comp_runtime_renderer_t *r,const comp_runtime_frame_t *f,
    uint8_t *frame,unsigned word,int x,int y)
{
    const unsigned locale=(unsigned)f->menu.language;
    const unsigned index=word==COMP_CUSTOM_QUIET?0u:word==COMP_CUSTOM_STANDARD?1u:
        word==COMP_CUSTOM_LIVELY?2u:word==COMP_CUSTOM_RESTORE?3u:4u;
    comp_wba_external_bitmap_t glyph;unsigned width;
    if(locale>=3u || index>=4u || !customer_glyph(r,locale,word,&glyph,&width) ||
       comp_quiet_prefix_width[index][locale]>width)return false;
    return bitmap_paint_source(r,frame,&glyph,22u,comp_quiet_prefix_width[index][locale],16u,
        (unsigned)x,(unsigned)y,COMP_CUSTOMER_BITMAP_FLAG);
}
static bool customer_quiet_duration(comp_runtime_renderer_t *r,const comp_runtime_frame_t *f,
    uint8_t *frame,int x,int y)
{
    return customer_short_word(r,f,frame,COMP_CUSTOM_QUIET,x,y) &&
        customer_word(r,f,frame,COMP_CUSTOM_MIN30,x+comp_quiet_prefix_width[0][f->menu.language]+8,y,0);
}
static void COMP_RENDER_UI_SMALL customer_chevron(comp_screen_framebuffer_t *fb,int x,int y)
{
    comp_screen_framebuffer_draw_line(fb,(int16_t)x,(int16_t)(y-4),(int16_t)(x+4),(int16_t)y,true);
    comp_screen_framebuffer_draw_line(fb,(int16_t)(x+4),(int16_t)y,(int16_t)x,(int16_t)(y+4),true);
}
static void COMP_RENDER_UI_SMALL customer_switch(comp_screen_framebuffer_t *fb,int y,bool on)
{
    comp_screen_framebuffer_fill_rect(fb,158,(int16_t)(y+9),18,13,true);
    quick_disc(fb,158,y+15,6,true);quick_disc(fb,175,y+15,6,true);
    if(!on) {
        comp_screen_framebuffer_fill_rect(fb,158,(int16_t)(y+10),18,11,false);
        quick_disc(fb,158,y+15,5,false);quick_disc(fb,175,y+15,5,false);
    }
    quick_disc(fb,on?175:158,y+15,4,!on);
}
static unsigned customer_number_width(const char *text)
{
    unsigned n=0u;for(;*text;++text) {
        const char *p=strchr(comp_wba_value_chars,*text);
        n+=p?comp_wba_value_advance[p-comp_wba_value_chars]:6u;
    }
    return n;
}
static bool COMP_RENDER_UI_SMALL customer_row_render(comp_runtime_renderer_t *r,const comp_runtime_frame_t *f,
    uint8_t *frame,comp_screen_framebuffer_t *fb,unsigned index,int y)
{
    comp_customer_menu_row_t row;const comp_screen_menu_t *m=&f->menu;char number[24]={0};
    if(!comp_screen_menu_customer_row(m,(uint8_t)index,&row))return false;
    unsigned label=row.label,value=comp_screen_menu_customer_value(m,row.item),record_value=255u;
    if(row.item==10u)label=(m->flags&COMP_SCREEN_MENU_FLAG_RECORDING)?COMP_CUSTOM_STOP:COMP_CUSTOM_START;
    if(row.item==22u)label=m->browser.link_connected?COMP_CUSTOM_LINK_OFF:COMP_CUSTOM_LINK_ON;
    if(row.item==64u) {
        if(!f->temporary_quiet_minutes)return customer_quiet_duration(r,f,frame,16,y+9);
        const unsigned level=m->browser.interaction_level;
        const unsigned original=level==COMP_SCREEN_MENU_INTERACTION_QUIET?COMP_CUSTOM_QUIET:
            level==COMP_SCREEN_MENU_INTERACTION_LIVELY?COMP_CUSTOM_LIVELY:COMP_CUSTOM_STANDARD;
        return customer_short_word(r,f,frame,COMP_CUSTOM_RESTORE,16,y+9) &&
            customer_short_word(r,f,frame,original,24+comp_quiet_prefix_width[3][m->language],y+9);
    }
    const bool option=row.kind==4u;
    if(option) {
        const bool selected=(unsigned)m->view>=COMP_CUSTOMER_CHOICE_BASE?value==row.label && !(row.item==42u && f->temporary_quiet_minutes):
            comp_screen_menu_customer_checked(m,row.item);
        if(!customer_word(r,f,frame,label,16,y+9,0))return false;
        quick_disc(fb,176,y+16,6,true);quick_disc(fb,176,y+16,5,false);
        if(selected)quick_disc(fb,176,y+16,3,true);
        return true;
    }
    if(row.kind==5u) {
        if(!customer_word(r,f,frame,label,16,y+9,0))return false;
        customer_switch(fb,y,comp_screen_menu_customer_checked(m,row.item));return true;
    }
    if(row.kind==1u || row.kind==3u)value=255u;
    if(row.kind==2u) {
        switch(row.item) {
        case 9:record_value=recording_value(f);break;
        case 14:value=COMP_CUSTOM_AUDIO_VALUE;break;case 18:value=COMP_CUSTOM_RES_VALUE;break;
        case 35:value=COMP_CUSTOM_PRODUCT_VALUE;break;
        case 36:
#if defined(COMPANION_WBA_APP_VERSION) && COMPANION_WBA_APP_VERSION>=0x010100u
            (void)snprintf(number,sizeof(number),"1.1.%u",(unsigned)(COMPANION_WBA_APP_VERSION-0x010100u));
#else
            memcpy(number,"--",3);
#endif
            break;
        case 37:(void)snprintf(number,sizeof(number),"%u",(unsigned)COMPANION_WBA_RESOURCE_GENERATION);break;
        case 46:(void)snprintf(number,sizeof(number),"%u",m->browser.recording_count);break;
        case 47:(void)snprintf(number,sizeof(number),"%u KB",m->browser.recording_storage_kb);break;
        case 50:(void)snprintf(number,sizeof(number),"%lu KB",(unsigned long)(COMP_WBA_NOR_RECORDING_DATA_BYTES/1024u));break;
        case 51:(void)snprintf(number,sizeof(number),"%lu KB",(unsigned long)(COMP_WBA_NOR_UI_BYTES/1024u));break;
        case 52:
            if((f->status_packed&(1u<<17)) && (f->status_packed>>24u)<=100u)
                (void)snprintf(number,sizeof(number),"%s%u%%",(f->status_packed&COMP_SCREEN_STATUS_ESTIMATED_BATTERY)?"~":"",(unsigned)(f->status_packed>>24u));
            else memcpy(number,"--",3);
            break;
        case 53:
            if(f->status_packed&COMP_SCREEN_STATUS_CHARGER_FAULT)value=COMP_CUSTOM_CHARGE_FAULT;
            else if(f->status_packed&COMP_SCREEN_STATUS_CHARGING)value=COMP_CUSTOM_CHARGE_NOW;
            else if(f->status_packed&COMP_SCREEN_STATUS_EXTERNAL_POWER)value=COMP_CUSTOM_POWERED;
            else memcpy(number,"--",3);
            break;
        default:break;
        }
    }
    unsigned label_width,value_width=0u;comp_wba_external_bitmap_t glyph;
    if(!customer_glyph(r,(unsigned)m->language,label,&glyph,&label_width))return false;
    if(record_value!=255u) {
        if(record_value<11u)value_width=comp_wba_live_value_advance[(unsigned)m->language][record_value];
        else if(record_value-11u<COMP_RECORD_REASON_LABEL_COUNT)value_width=comp_record_reason_widths[(unsigned)m->language][record_value-11u];
        else return false;
    } else if(number[0])value_width=customer_number_width(number);
    else if(value!=255u && !customer_glyph(r,(unsigned)m->language,value,&glyph,&value_width))return false;
    const bool arrow=row.kind==1u || row.kind==6u;
    const bool stacked=value_width && label_width+value_width+14u>(arrow?155u:168u);
    const int value_y=y+(stacked?18:9),right=arrow?169:184;
    if(!customer_word(r,f,frame,label,16,y+(stacked?1:9),0))return false;
    if(number[0]) {
        if(!menu_number_at(r,fb,stacked?16:100,value_y,stacked?168:right-100,number,false))return false;
    } else if(record_value!=255u) {
        const unsigned left=stacked?16u:(unsigned)right-value_width;
        if(record_value<11u) {
            if(!bitmap_paint(r,frame,&comp_wba_live_values[(unsigned)m->language][record_value],COMP_WBA_LIVE_VALUE_STRIDE,
                value_width,COMP_WBA_LIVE_VALUE_HEIGHT,left,(unsigned)value_y))return false;
        } else if(!recording_reason_label(r,frame,(unsigned)m->language,record_value-11u,left,(unsigned)value_y))return false;
    } else if(value!=255u && !customer_word(r,f,frame,value,stacked?16:right,value_y,stacked?0:1))return false;
    if(arrow)customer_chevron(fb,178,y+16);
    return true;
}
static bool customer_menu_header(comp_runtime_renderer_t *r,const comp_runtime_frame_t *f,
    uint8_t *frame,comp_screen_framebuffer_t *fb)
{
    comp_screen_framebuffer_clear(fb,false);
    if(!customer_word(r,f,frame,comp_screen_menu_customer_title(&f->menu),100,25,2))return false;
    comp_screen_framebuffer_draw_line(fb,20,28,15,33,true);
    comp_screen_framebuffer_draw_line(fb,15,33,20,38,true);
    return true;
}
static bool COMP_RENDER_UI_SMALL customer_menu_render(comp_runtime_renderer_t *r,const comp_runtime_frame_t *f,uint8_t *frame)
{
    comp_screen_framebuffer_t fb;const comp_screen_menu_t *m=&f->menu;
    if((unsigned)m->language>2u || !comp_screen_framebuffer_init(&fb,frame,5000u,200u,200u))return false;
    if(!customer_menu_header(r,f,frame,&fb))return false;
    if(m->view==COMP_SCREEN_MENU_VIEW_BROWSER_HOME) {
        for(unsigned i=0;i<4u;++i) {
            comp_customer_menu_row_t row;comp_wba_external_bitmap_t icon;unsigned width;
            const unsigned center=51u+(i%2u)*98u,top=49u+(i/2u)*75u;
            if(!comp_screen_menu_customer_row(m,(uint8_t)i,&row) ||
               !customer_glyph(r,(unsigned)m->language,COMP_CUSTOMER_LABEL_COUNT+i,&icon,&width) ||
               !bitmap_paint_source(r,frame,&icon,6u,48u,42u,center-24u,top,COMP_CUSTOMER_BITMAP_FLAG) ||
               !customer_word(r,f,frame,row.label,(int)center,(int)top+47,2))return false;
        }
        return true;
    }
    const unsigned count=comp_screen_menu_customer_count(m->view);
    for(unsigned i=m->home_page;i<count && i<(unsigned)m->home_page+4u;++i)
        if(!customer_row_render(r,f,frame,&fb,i,52+((int)i-(int)m->home_page)*34))return false;
    return true;
}
#endif
