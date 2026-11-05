/* Included once by screen_menu.c; no resident state is added. */
#if COMPANION_WBA_RESOURCE_PROFILE && COMPANION_WBA_RESOURCE_GENERATION >= 84u && COMPANION_SCREEN_COMP_REQ_638_SOURCE_PACK
bool comp_screen_menu_customer_active(void) {return true;}

static uint8_t customer_choice_count(unsigned item)
{
    switch(item) {case 11:case 16:case 19:return 2u;case 28:case 29:return 3u;case 42:return 4u;
        case 12:case 54:return 4u;default:return 0u;}
}
static uint8_t customer_choice_label(unsigned item,unsigned index)
{
    /* Exact original options, including invalid-slot sentinels. One compact
     * lookup replaces eight arrays and the item dispatch jump table. */
    static const uint8_t choices[][5]={
        {11u,COMP_CUSTOM_VOICE,COMP_CUSTOM_MEETING,255u,255u},
        {12u,COMP_CUSTOM_MIN15,COMP_CUSTOM_MIN30,COMP_CUSTOM_MIN60,COMP_CUSTOM_UNLIMITED},
        {16u,COMP_CUSTOM_H24,COMP_CUSTOM_H12,255u,255u},
        {19u,COMP_CUSTOM_DIGITS,COMP_CUSTOM_FILL,255u,255u},
        {28u,COMP_CUSTOM_UTC8,COMP_CUSTOM_UTC0,COMP_CUSTOM_UTC5,255u},
        {29u,COMP_CUSTOM_Q23,COMP_CUSTOM_Q22,COMP_CUSTOM_OFF,255u},
        {42u,COMP_CUSTOM_QUIET,COMP_CUSTOM_STANDARD,COMP_CUSTOM_LIVELY,COMP_CUSTOM_MIN30},
        {54u,COMP_CUSTOM_MIN1,COMP_CUSTOM_MIN3,COMP_CUSTOM_MIN5,COMP_CUSTOM_NEVER}
    };
    if(index<4u)
        for(unsigned i=0u;i<sizeof(choices)/sizeof(choices[0]);++i)
            if(choices[i][0]==item)return choices[i][index+1u];
    return 255u;
}
static uint8_t customer_selected(const comp_screen_menu_t *menu,unsigned item)
{
    const comp_screen_menu_browser_state_t *s=&menu->browser;
    switch(item) {
    case 11:return (uint8_t)s->recorder_profile;
    case 12:return s->recording_limit_minutes==15?0u:s->recording_limit_minutes==30?1u:s->recording_limit_minutes==60?2u:3u;
    case 16:return s->clock_24_hour?0u:1u;
    case 19:return s->battery_fill?1u:0u;
    case 28:return s->time_zone_offset_minutes==480?0u:s->time_zone_offset_minutes==0?1u:2u;
    case 29:return s->quiet_hours;
    case 42:return s->interaction_level;
    case 54:return s->auto_sleep_minutes==1?0u:s->auto_sleep_minutes==3?1u:s->auto_sleep_minutes==5?2u:3u;
    default:return 255u;
    }
}
uint8_t comp_screen_menu_customer_count(comp_screen_menu_view_t view)
{
    if((unsigned)view>=COMP_CUSTOMER_CHOICE_BASE)return customer_choice_count((unsigned)view-COMP_CUSTOMER_CHOICE_BASE);
    if(view==COMP_SCREEN_MENU_VIEW_BROWSER_CLEAR_RECORDINGS || view==COMP_SCREEN_MENU_VIEW_BROWSER_RESTORE_DEFAULTS ||
       view==COMP_SCREEN_MENU_VIEW_BROWSER_PET_HELP)return 3u;
    unsigned n=0u;for(unsigned i=0;i<sizeof(comp_customer_rows)/sizeof(comp_customer_rows[0]);++i)
        if(comp_customer_rows[i].view==(unsigned)view)++n;
    return (uint8_t)n;
}
bool comp_screen_menu_customer_row(const comp_screen_menu_t *menu,uint8_t index,comp_customer_menu_row_t *row)
{
    if(!menu || !row)return false;
    if((unsigned)menu->view>=COMP_CUSTOMER_CHOICE_BASE) {
        unsigned item=(unsigned)menu->view-COMP_CUSTOMER_CHOICE_BASE;
        const uint8_t label=customer_choice_label(item,index);if(label==255u)return false;
        if(item==42u && index==3u)
            *row=(comp_customer_menu_row_t){(uint8_t)menu->view,3u,255u,64u,COMP_CUSTOM_MIN30};
        else *row=(comp_customer_menu_row_t){(uint8_t)menu->view,4u,index,(uint8_t)item,label};
        return true;
    }
    if(menu->view==COMP_SCREEN_MENU_VIEW_BROWSER_CLEAR_RECORDINGS || menu->view==COMP_SCREEN_MENU_VIEW_BROWSER_RESTORE_DEFAULTS) {
        if(index==1u)*row=(comp_customer_menu_row_t){(uint8_t)menu->view,3u,255u,
            menu->view==COMP_SCREEN_MENU_VIEW_BROWSER_CLEAR_RECORDINGS?58u:61u,
            menu->view==COMP_SCREEN_MENU_VIEW_BROWSER_CLEAR_RECORDINGS?COMP_CUSTOM_CONFIRM_CLEAR:COMP_CUSTOM_CONFIRM_RESTORE};
        else if(index==2u)*row=(comp_customer_menu_row_t){(uint8_t)menu->view,7u,255u,59u,COMP_CUSTOM_CANCEL};
        else return false;
        return true;
    }
    unsigned n=0u;for(unsigned i=0;i<sizeof(comp_customer_rows)/sizeof(comp_customer_rows[0]);++i)
        if(comp_customer_rows[i].view==(unsigned)menu->view && n++==index) {
            const comp_customer_menu_packed_row_t *stored=&comp_customer_rows[i];
            const uint8_t kind=stored->kind_target>>5u;
            *row=(comp_customer_menu_row_t){stored->view,kind,
                kind==1u?(stored->kind_target&31u):255u,stored->item,stored->label};
            return true;
        }
    return false;
}
uint8_t comp_screen_menu_customer_title(const comp_screen_menu_t *menu)
{
    if((unsigned)menu->view==COMP_CUSTOMER_FILE_HELP_VIEW)return COMP_CUSTOM_FILES_ON_PC;
    if((unsigned)menu->view>=COMP_CUSTOMER_CHOICE_BASE) {
        const unsigned item=(unsigned)menu->view-COMP_CUSTOMER_CHOICE_BASE;
        for(unsigned i=0u;i<sizeof(comp_customer_rows)/sizeof(comp_customer_rows[0]);++i)
            if((comp_customer_rows[i].kind_target>>5u)==6u && comp_customer_rows[i].item==item)
                return comp_customer_rows[i].label;
        return COMP_CUSTOM_MENU;
    }
    static const uint8_t titles[]={COMP_CUSTOM_MENU,COMP_CUSTOM_RECORD,COMP_CUSTOM_DISPLAY,COMP_CUSTOM_CONNECT,
        COMP_CUSTOM_TIME,COMP_CUSTOM_GESTURE,COMP_CUSTOM_LANGUAGE,COMP_CUSTOM_ABOUT,COMP_CUSTOM_PET,
        COMP_CUSTOM_STORAGE,COMP_CUSTOM_SLEEP,COMP_CUSTOM_CLEAR,COMP_CUSTOM_RESTORE,COMP_CUSTOM_HELP,COMP_CUSTOM_QUICK,COMP_CUSTOM_DEVICE};
    return (unsigned)menu->view>=16u && (unsigned)menu->view<32u?titles[(unsigned)menu->view-16u]:COMP_CUSTOM_MENU;
}
uint8_t comp_screen_menu_customer_value(const comp_screen_menu_t *menu,uint8_t item)
{
    if(customer_choice_count(item))return customer_choice_label(item,customer_selected(menu,item));
    switch(item) {
    case 17:return COMP_CUSTOM_EINK;case 15:return COMP_CUSTOM_BUILTIN;case 49:return COMP_CUSTOM_ONDEVICE;
    case 38:return COMP_CUSTOM_VIA_TYPE;case 39:return COMP_CUSTOM_VIEW_TYPE;
    case 20:return menu->browser.link_connected?COMP_CUSTOM_CONNECTED:COMP_CUSTOM_DISCONNECTED;
    default:return 255u;
    }
}
bool comp_screen_menu_customer_checked(const comp_screen_menu_t *menu,uint8_t item)
{
    switch(item) {case 13:return menu->browser.silent_auto_stop;case 23:return menu->browser.auto_reconnect;
        case 43:return menu->browser.gaze_follow;case 44:return menu->browser.natural_blink;
        case 31:return menu->browser.recording_gesture==COMP_SCREEN_MENU_RECORDING_GESTURE_CORNER_DOUBLE_TAP;
        case 32:return menu->browser.recording_gesture==COMP_SCREEN_MENU_RECORDING_GESTURE_EDGE_PULL;
        case 33:return menu->language==COMP_SCREEN_MENU_LANGUAGE_ZH;case 34:return menu->language==COMP_SCREEN_MENU_LANGUAGE_EN;
        case 62:return menu->language==COMP_SCREEN_MENU_LANGUAGE_ZH_TW;default:return false;}
}
static void customer_set_choice(comp_screen_menu_t *menu,unsigned item,unsigned index)
{
    static const uint8_t limits[]={15,30,60,0},sleeps[]={1,3,5,0};
    static const int16_t zones[]={480,0,-300};
    switch(item) {
    case 11:menu->browser.recorder_profile=(comp_screen_menu_recorder_profile_t)index;break;
    case 12:menu->browser.recording_limit_minutes=limits[index];break;
    case 16:menu->browser.clock_24_hour=index==0u;break;
    case 19:menu->browser.battery_fill=index!=0u;break;
    case 28:menu->browser.time_zone_offset_minutes=zones[index];break;
    case 29:menu->browser.quiet_hours=(uint8_t)index;break;
    case 42:if(index<3u)menu->browser.interaction_level=(uint8_t)index;break;
    case 54:menu->browser.auto_sleep_minutes=sleeps[index];break;
    default:break;
    }
}
uint8_t comp_screen_menu_customer_setting_value(const comp_screen_menu_t *menu,uint8_t item)
{
    if(customer_choice_count(item))return customer_selected(menu,item);
    if(item==41u)return (uint8_t)menu->browser.recording_gesture;
    if(item==33u || item==34u || item==62u)return (uint8_t)menu->language;
    if(item==13u || item==23u || item==43u || item==44u)
        return comp_screen_menu_customer_checked(menu,item)?1u:0u;
    return 255u;
}
bool comp_screen_menu_customer_restore_value(comp_screen_menu_t *menu,uint8_t item,uint8_t value)
{
    const uint8_t current=comp_screen_menu_customer_setting_value(menu,item);
    if(current==255u || current==value || (item==42u && value>=3u))return false;
    if(customer_choice_count(item)) {
        if(value>=customer_choice_count(item))return false;
        customer_set_choice(menu,item,value);
    } else if(item==41u && value<=1u)menu->browser.recording_gesture=(uint8_t)value;
    else if((item==33u || item==34u || item==62u) && value<=2u)menu->language=(comp_screen_menu_language_t)value;
    else if(value<=1u) {
        if(item==13u)menu->browser.silent_auto_stop=value!=0u;
        else if(item==23u)menu->browser.auto_reconnect=value!=0u;
        else if(item==43u)menu->browser.gaze_follow=value!=0u;
        else if(item==44u)menu->browser.natural_blink=value!=0u;
        else return false;
    } else return false;
    ++menu->revision;return true;
}
static comp_screen_menu_result_t customer_tap(comp_screen_menu_t *menu,uint16_t x,uint16_t y)
{
    comp_screen_menu_result_t result={0};result.browser_item=255u;
    if(browser_back_hit(x,y)) {
        if(menu->view==COMP_SCREEN_MENU_VIEW_BROWSER_HOME){result.action=COMP_SCREEN_MENU_ACTION_EXIT_DAILY;result.changed=true;}
        else result.changed=comp_screen_menu_back(menu);
    } else {
        const uint8_t index=browser_hit_index(menu,x,y);comp_customer_menu_row_t row;
        if(!comp_screen_menu_customer_row(menu,index,&row) || row.kind==2u)goto done;
        result.browser_item=row.item;result.browser_kind=row.kind;
        if(row.item==64u) {
            /* Fourth activity row is a local timer, not persisted option3. */
            result.action=COMP_SCREEN_MENU_ACTION_PET_QUIET_TIMER;
            (void)comp_screen_menu_back(menu);++menu->revision;result.changed=true;
        } else if((unsigned)menu->view>=COMP_CUSTOMER_CHOICE_BASE) {
            const unsigned item=(unsigned)menu->view-COMP_CUSTOMER_CHOICE_BASE;
            const bool change=customer_selected(menu,item)!=index;
            if(change)customer_set_choice(menu,item,index);
            (void)comp_screen_menu_back(menu);result.changed=true;
            if(change)result.action=COMP_SCREEN_MENU_ACTION_BROWSER_SETTING_CHANGED;
        } else if(row.kind==1u)result.changed=comp_screen_menu_navigate_to(menu,(comp_screen_menu_view_t)row.target);
        else if(row.kind==6u)result.changed=comp_screen_menu_navigate_to(menu,(comp_screen_menu_view_t)(COMP_CUSTOMER_CHOICE_BASE+row.item));
        else if(row.kind==7u)result.changed=comp_screen_menu_back(menu);
        else if(row.kind==4u) {
            if(row.item==33u || row.item==34u || row.item==62u) {
                const comp_screen_menu_language_t language=row.item==33u?COMP_SCREEN_MENU_LANGUAGE_ZH:row.item==34u?COMP_SCREEN_MENU_LANGUAGE_EN:COMP_SCREEN_MENU_LANGUAGE_ZH_TW;
                if(menu->language==language)goto done;
                menu->language=language;result.action=COMP_SCREEN_MENU_ACTION_LANGUAGE_CHANGED;
            } else {
                if(!apply_browser_setting(menu,row.item))goto done;
                /* Both authored gesture options save the one actual gesture
                 * preference; the backend whitelist owns item41. */
                result.browser_item=41u;result.action=COMP_SCREEN_MENU_ACTION_BROWSER_SETTING_CHANGED;
            }
            ++menu->revision;result.changed=true;
        } else if(row.kind==5u) {
            if(!apply_browser_setting(menu,row.item))goto done;
            result.action=COMP_SCREEN_MENU_ACTION_BROWSER_SETTING_CHANGED;++menu->revision;result.changed=true;
        } else if(row.kind==3u) {
            switch(row.item) {
            case 10:result.action=(menu->flags&COMP_SCREEN_MENU_FLAG_RECORDING)?COMP_SCREEN_MENU_ACTION_RECORD_STOP:COMP_SCREEN_MENU_ACTION_RECORD_START;break;
            case 21:result.action=COMP_SCREEN_MENU_ACTION_BROWSER_PAIR;break;
            case 22:result.action=COMP_SCREEN_MENU_ACTION_BROWSER_CONNECTION_TOGGLE;break;
            case 25:result.action=COMP_SCREEN_MENU_ACTION_BROWSER_RESET_NAME;break;
            case 55:result.action=COMP_SCREEN_MENU_ACTION_BROWSER_SLEEP_NOW;break;
            case 56:result.action=COMP_SCREEN_MENU_ACTION_PET_GREETING;break;
            case 57:result.action=COMP_SCREEN_MENU_ACTION_PET_PLAY;break;
            case 58:result.action=COMP_SCREEN_MENU_ACTION_BROWSER_CLEAR_RECORDINGS;break;
            case 61:result.action=COMP_SCREEN_MENU_ACTION_BROWSER_RESTORE_DEFAULTS;break;
            default:goto done;
            }
            ++menu->revision;result.changed=true;
        }
    }
done:menu_result_from_state(menu,&result);return result;
}
#else
bool comp_screen_menu_customer_active(void){return false;}
uint8_t comp_screen_menu_customer_count(comp_screen_menu_view_t view){(void)view;return 0u;}
bool comp_screen_menu_customer_row(const comp_screen_menu_t *m,uint8_t i,comp_customer_menu_row_t *r){(void)m;(void)i;(void)r;return false;}
uint8_t comp_screen_menu_customer_title(const comp_screen_menu_t *m){(void)m;return 0u;}
uint8_t comp_screen_menu_customer_value(const comp_screen_menu_t *m,uint8_t i){(void)m;(void)i;return 255u;}
bool comp_screen_menu_customer_checked(const comp_screen_menu_t *m,uint8_t i){(void)m;(void)i;return false;}
uint8_t comp_screen_menu_customer_setting_value(const comp_screen_menu_t *m,uint8_t i){(void)m;(void)i;return 255u;}
bool comp_screen_menu_customer_restore_value(comp_screen_menu_t *m,uint8_t i,uint8_t v){(void)m;(void)i;(void)v;return false;}
static comp_screen_menu_result_t customer_tap(comp_screen_menu_t *m,uint16_t x,uint16_t y){(void)m;(void)x;(void)y;return (comp_screen_menu_result_t){0};}
#endif
