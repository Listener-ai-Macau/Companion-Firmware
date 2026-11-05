#include "menu_v5_localization.h"

#include <stddef.h>

#define COMP_MENU_V5_TEXT_KEY_COUNT ((unsigned int)COMP_MENU_V5_TEXT_ABOUT + 1u)

static const char *const k_english[COMP_MENU_V5_TEXT_KEY_COUNT] = {
    "Voice", "Device", "Connection", "Preferences", "Recording",
    "History", "Wake word", "E-paper", "Touch", "Battery", "UI assets",
    "Pair new device", "Link status", "Reconnect", "Language", "Gesture",
    "Refresh rate", "Diagnostics", "About",
};

static const char *const k_chinese[COMP_MENU_V5_TEXT_KEY_COUNT] = {
    "语音", "设备", "连接", "偏好设置", "录音状态",
    "录音历史", "唤醒词", "电子纸", "触控", "电池", "界面资源",
    "配对新设备", "连接状态", "重新连接", "语言", "手势",
    "刷新频率", "诊断", "关于",
};

bool comp_menu_v5_language_is_valid(comp_menu_v5_language_t language)
{
    return language < COMP_MENU_V5_LANGUAGE_COUNT;
}

static bool text_key_is_valid(comp_menu_v5_text_key_t key)
{
    return (unsigned int)key < COMP_MENU_V5_TEXT_KEY_COUNT;
}

const char *comp_menu_v5_text(comp_menu_v5_language_t language,
                              comp_menu_v5_text_key_t key)
{
    if (!comp_menu_v5_language_is_valid(language) || !text_key_is_valid(key)) {
        return NULL;
    }
    return language == COMP_MENU_V5_LANGUAGE_ZH_CN ?
               k_chinese[(unsigned int)key] :
               k_english[(unsigned int)key];
}

const char *comp_menu_v5_language_display_name(comp_menu_v5_language_t language)
{
    switch (language) {
    case COMP_MENU_V5_LANGUAGE_EN:
        return "English";
    case COMP_MENU_V5_LANGUAGE_ZH_CN:
        return "中文";
    default:
        return NULL;
    }
}

const char *comp_menu_v5_action_label(comp_menu_v5_language_t language,
                                      comp_menu_v5_action_t action)
{
    if (!comp_menu_v5_language_is_valid(language)) {
        return NULL;
    }
    switch (action) {
    case COMP_MENU_V5_ACTION_PAIR_NEW_DEVICE:
        return language == COMP_MENU_V5_LANGUAGE_ZH_CN ? "配对新设备" : "Pair new device";
    case COMP_MENU_V5_ACTION_RECONNECT:
        return language == COMP_MENU_V5_LANGUAGE_ZH_CN ? "重新连接" : "Reconnect";
    case COMP_MENU_V5_ACTION_LANGUAGE:
        return language == COMP_MENU_V5_LANGUAGE_ZH_CN ? "切换语言" : "Switch language";
    default:
        return NULL;
    }
}

bool comp_menu_v5_toggle_language(comp_menu_v5_language_t current,
                                  comp_menu_v5_language_t *out_next)
{
    if (out_next == NULL || !comp_menu_v5_language_is_valid(current)) {
        return false;
    }
    *out_next = current == COMP_MENU_V5_LANGUAGE_EN ?
                    COMP_MENU_V5_LANGUAGE_ZH_CN :
                    COMP_MENU_V5_LANGUAGE_EN;
    return true;
}

bool comp_menu_v5_apply_language_action(comp_menu_v5_action_t action,
                                        comp_menu_v5_language_t current,
                                        comp_menu_v5_language_t *out_next)
{
    return action == COMP_MENU_V5_ACTION_LANGUAGE &&
           comp_menu_v5_toggle_language(current, out_next);
}
