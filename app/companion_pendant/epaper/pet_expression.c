#include "pet_expression.h"
#include "pet_visual_style.h"

#include <string.h>

#define PET_LOGICAL_MAX_X 199u
#define PET_LOGICAL_MAX_Y 199u
#define PET_MIN_RENDER_WIDTH 64u
#define PET_MIN_RENDER_HEIGHT 64u

static int8_t clamp_gaze(int16_t value)
{
    if (value < -32) {
        return -32;
    }
    if (value > 32) {
        return 32;
    }
    return (int8_t)value;
}

static uint8_t clamp_open(int16_t value)
{
    if (value < 18) {
        return 18u;
    }
    if (value > 100) {
        return 100u;
    }
    return (uint8_t)value;
}

static int8_t clamp_face_shift(int16_t value)
{
    if (value < -18) {
        return -18;
    }
    if (value > 18) {
        return 18;
    }
    return (int8_t)value;
}

static int8_t clamp_brow_asymmetry(int16_t value)
{
    if (value < -18) {
        return -18;
    }
    if (value > 18) {
        return 18;
    }
    return (int8_t)value;
}

static int8_t clamp_eye_pair_tilt(int16_t value)
{
    if (value < -12) {
        return -12;
    }
    if (value > 12) {
        return 12;
    }
    return (int8_t)value;
}

static void fill_ellipse(comp_screen_framebuffer_t *framebuffer,
                         int16_t center_x,
                         int16_t center_y,
                         int16_t radius_x,
                         int16_t radius_y,
                         bool black)
{
    int32_t radius_x_squared;
    int32_t radius_y_squared;
    int32_t threshold;

    if (radius_x <= 0 || radius_y <= 0) {
        return;
    }
    radius_x_squared = (int32_t)radius_x * radius_x;
    radius_y_squared = (int32_t)radius_y * radius_y;
    threshold = radius_x_squared * radius_y_squared;
    for (int16_t y = (int16_t)(-radius_y); y <= radius_y; ++y) {
        int32_t y_term = (int32_t)y * y * radius_x_squared;
        for (int16_t x = (int16_t)(-radius_x); x <= radius_x; ++x) {
            if ((int32_t)x * x * radius_y_squared + y_term <= threshold) {
                comp_screen_framebuffer_set_pixel(framebuffer,
                                                  (int16_t)(center_x + x),
                                                  (int16_t)(center_y + y),
                                                  black);
            }
        }
    }
}

static int16_t map_logical_position(int16_t value, uint16_t pixels, uint16_t logical_max)
{
    int32_t scaled;

    if (value < 0) {
        return (int16_t)-map_logical_position((int16_t)-value, pixels, logical_max);
    }
    scaled = ((int32_t)value * (int32_t)(pixels - 1u) + (int32_t)(logical_max / 2u)) /
             (int32_t)logical_max;
    return (int16_t)scaled;
}

static int16_t map_logical_radius(int16_t value, uint16_t pixels, uint16_t logical_max)
{
    int32_t scaled = ((int32_t)value * (int32_t)(pixels - 1u) +
                      (int32_t)(logical_max / 2u)) /
                     (int32_t)logical_max;

    return (int16_t)(scaled > 0 ? scaled : 1);
}

static void fill_logical_ellipse(comp_screen_framebuffer_t *framebuffer,
                                 int16_t center_x,
                                 int16_t center_y,
                                 int16_t radius_x,
                                 int16_t radius_y,
                                 bool black)
{
    fill_ellipse(framebuffer,
                 map_logical_position(center_x, framebuffer->width, PET_LOGICAL_MAX_X),
                 map_logical_position(center_y, framebuffer->height, PET_LOGICAL_MAX_Y),
                 map_logical_radius(radius_x, framebuffer->width, PET_LOGICAL_MAX_X),
                 map_logical_radius(radius_y, framebuffer->height, PET_LOGICAL_MAX_Y),
                 black);
}

static void draw_logical_line(comp_screen_framebuffer_t *framebuffer,
                              int16_t x0,
                              int16_t y0,
                              int16_t x1,
                              int16_t y1,
                              bool black)
{
    comp_screen_framebuffer_draw_line(
        framebuffer,
        map_logical_position(x0, framebuffer->width, PET_LOGICAL_MAX_X),
        map_logical_position(y0, framebuffer->height, PET_LOGICAL_MAX_Y),
        map_logical_position(x1, framebuffer->width, PET_LOGICAL_MAX_X),
        map_logical_position(y1, framebuffer->height, PET_LOGICAL_MAX_Y),
        black);
}

static void stroke_logical_ellipse(comp_screen_framebuffer_t *framebuffer,
                                   int16_t center_x,
                                   int16_t center_y,
                                   int16_t radius_x,
                                   int16_t radius_y,
                                   bool black)
{
    fill_logical_ellipse(framebuffer, center_x, center_y, radius_x, radius_y, black);
    if (radius_x > 2 && radius_y > 2) {
        fill_logical_ellipse(framebuffer,
                             center_x,
                             center_y,
                             (int16_t)(radius_x - 2),
                             (int16_t)(radius_y - 2),
                             !black);
    }
}

static void draw_small_spark(comp_screen_framebuffer_t *framebuffer,
                             int16_t center_x,
                             int16_t center_y,
                             int16_t radius)
{
    draw_logical_line(framebuffer,
                      center_x,
                      (int16_t)(center_y - radius),
                      center_x,
                      (int16_t)(center_y + radius),
                      true);
    draw_logical_line(framebuffer,
                      (int16_t)(center_x - radius),
                      center_y,
                      (int16_t)(center_x + radius),
                      center_y,
                      true);
    draw_logical_line(framebuffer,
                      (int16_t)(center_x - radius / 2),
                      (int16_t)(center_y - radius / 2),
                      (int16_t)(center_x + radius / 2),
                      (int16_t)(center_y + radius / 2),
                      true);
    draw_logical_line(framebuffer,
                      (int16_t)(center_x + radius / 2),
                      (int16_t)(center_y - radius / 2),
                      (int16_t)(center_x - radius / 2),
                      (int16_t)(center_y + radius / 2),
                      true);
}

static void draw_small_heart(comp_screen_framebuffer_t *framebuffer,
                             int16_t center_x,
                             int16_t center_y,
                             int16_t radius)
{
    fill_logical_ellipse(framebuffer,
                         (int16_t)(center_x - radius / 2),
                         center_y,
                         (int16_t)(radius / 2),
                         (int16_t)(radius / 2),
                         true);
    fill_logical_ellipse(framebuffer,
                         (int16_t)(center_x + radius / 2),
                         center_y,
                         (int16_t)(radius / 2),
                         (int16_t)(radius / 2),
                         true);
    draw_logical_line(framebuffer,
                      (int16_t)(center_x - radius),
                      (int16_t)(center_y + radius / 2),
                      center_x,
                      (int16_t)(center_y + radius * 2),
                      true);
    draw_logical_line(framebuffer,
                      (int16_t)(center_x + radius),
                      (int16_t)(center_y + radius / 2),
                      center_x,
                      (int16_t)(center_y + radius * 2),
                      true);
}

static void draw_small_question(comp_screen_framebuffer_t *framebuffer,
                                int16_t center_x,
                                int16_t center_y)
{
    stroke_logical_ellipse(framebuffer, center_x, center_y, 6, 5, true);
    fill_logical_ellipse(framebuffer,
                         (int16_t)(center_x - 5),
                         (int16_t)(center_y + 1),
                         6,
                         5,
                         false);
    draw_logical_line(framebuffer,
                      (int16_t)(center_x + 3),
                      (int16_t)(center_y + 4),
                      center_x,
                      (int16_t)(center_y + 12),
                      true);
    fill_logical_ellipse(framebuffer, center_x, (int16_t)(center_y + 18), 2, 2, true);
}

static void draw_small_z(comp_screen_framebuffer_t *framebuffer,
                         int16_t x,
                         int16_t y,
                         int16_t size)
{
    draw_logical_line(framebuffer, x, y, (int16_t)(x + size), y, true);
    draw_logical_line(framebuffer,
                      (int16_t)(x + size),
                      y,
                      x,
                      (int16_t)(y + size),
                      true);
    draw_logical_line(framebuffer,
                      x,
                      (int16_t)(y + size),
                      (int16_t)(x + size),
                      (int16_t)(y + size),
                      true);
}

static void draw_eye_arc(comp_screen_framebuffer_t *framebuffer,
                         int16_t center_x,
                         int16_t center_y,
                         const comp_pet_expression_pose_t *pose,
                         bool smiling)
{
    int16_t eye_radius_x = (int16_t)((COMP_PET_STYLE_EYE_BASE_RX +
                                      ((uint16_t)pose->eye_open *
                                       COMP_PET_STYLE_EYE_OPEN_RX_GAIN) /
                                          100u) *
                                     pose->eye_width / 100u);
    int16_t arc_radius_y = smiling ? COMP_PET_STYLE_EYE_ARC_SMILE_RY :
                                     COMP_PET_STYLE_EYE_ARC_SLEEPY_RY;
    int16_t cut_center_y = (int16_t)(center_y + (smiling ? 6 : -5));
    int16_t end_y = (int16_t)(center_y + (smiling ? 4 : -3));

    fill_logical_ellipse(framebuffer, center_x, center_y, eye_radius_x, arc_radius_y, true);
    fill_logical_ellipse(framebuffer,
                         center_x,
                         cut_center_y,
                         (int16_t)(eye_radius_x + 2),
                         (int16_t)(arc_radius_y - 1),
                         false);
    fill_logical_ellipse(framebuffer,
                         (int16_t)(center_x - eye_radius_x + 3),
                         end_y,
                         2,
                         2,
                         true);
    fill_logical_ellipse(framebuffer,
                         (int16_t)(center_x + eye_radius_x - 3),
                         end_y,
                         2,
                         2,
                         true);
}

static void draw_eye(comp_screen_framebuffer_t *framebuffer,
                     int16_t center_x,
                     int16_t center_y,
                     const comp_pet_expression_pose_t *pose,
                     bool left)
{
    int16_t eye_radius_y = (int16_t)(COMP_PET_STYLE_EYE_BASE_RY +
                                     ((uint16_t)pose->eye_open *
                                      COMP_PET_STYLE_EYE_OPEN_RY_GAIN) /
                                         100u);
    int16_t eye_radius_x = (int16_t)((COMP_PET_STYLE_EYE_BASE_RX +
                                      ((uint16_t)pose->eye_open *
                                       COMP_PET_STYLE_EYE_OPEN_RX_GAIN) /
                                          100u) *
                                     pose->eye_width / 100u);
    int16_t highlight_radius_x = (int16_t)(COMP_PET_STYLE_HIGHLIGHT_RX *
                                           pose->highlight_scale / 100u);
    int16_t highlight_radius_y = (int16_t)(COMP_PET_STYLE_HIGHLIGHT_RY *
                                           pose->highlight_scale / 100u);
    int16_t highlight_x;
    int16_t highlight_y;
    int16_t lid_inner_y;
    int16_t lid_outer_y;
    int16_t side = left ? -1 : 1;
    bool smiling_arc = pose->mouth == COMP_PET_MOUTH_SMILE &&
                       pose->brow == COMP_PET_BROW_WARM && pose->eye_open <= 64u;
    bool sleepy_arc = pose->brow == COMP_PET_BROW_SLEEPY && pose->eye_open <= 48u;

    if (smiling_arc || sleepy_arc) {
        draw_eye_arc(framebuffer, center_x, center_y, pose, smiling_arc);
        return;
    }

    fill_logical_ellipse(framebuffer, center_x, center_y, eye_radius_x, eye_radius_y, true);
    highlight_x = (int16_t)(center_x - side * 5 + pose->gaze_x / 3);
    highlight_y = (int16_t)(center_y - eye_radius_y / 3 + pose->gaze_y / 3 +
                             ((pose->variation & 1u) == 0u ? -1 : 1));
    fill_logical_ellipse(framebuffer,
                         highlight_x,
                         highlight_y,
                         highlight_radius_x > 0 ? highlight_radius_x : 1,
                         highlight_radius_y > 0 ? highlight_radius_y : 1,
                         false);
    if (pose->eye_open >= 72u) {
        fill_logical_ellipse(framebuffer,
                             (int16_t)(highlight_x + side * 7),
                             (int16_t)(highlight_y + 9),
                             highlight_radius_x > 2 ? highlight_radius_x / 2 : 1,
                             highlight_radius_y > 2 ? highlight_radius_y / 2 : 1,
                             false);
    }
    if (pose->eye_open <= 48u) {
        lid_inner_y = (int16_t)(center_y - eye_radius_y / 2 -
                                 side * pose->eyelid_tilt / 4);
        lid_outer_y = (int16_t)(center_y - eye_radius_y / 2 +
                                 side * pose->eyelid_tilt / 4);
        draw_logical_line(framebuffer,
                          (int16_t)(center_x - eye_radius_x),
                          left ? lid_outer_y : lid_inner_y,
                          (int16_t)(center_x + eye_radius_x),
                          left ? lid_inner_y : lid_outer_y,
                          false);
    }
}

static void draw_brow(comp_screen_framebuffer_t *framebuffer,
                      int16_t center_x,
                      int16_t eye_y,
                      const comp_pet_expression_pose_t *pose,
                      bool left)
{
    int16_t half_width;
    int16_t lift = (int16_t)(pose->brow_lift / 3u);
    int16_t asymmetry = (int16_t)(pose->brow_asymmetry / 3);
    int16_t side = left ? -1 : 1;
    int16_t inner_x;
    int16_t outer_x;
    int16_t inner_y = (int16_t)(eye_y - 31 - lift + (left ? asymmetry : -asymmetry));
    int16_t outer_y = inner_y;

    if (pose->brow == COMP_PET_BROW_NONE) {
        return;
    }
    half_width = (int16_t)(12 * pose->eye_width / 100u);
    inner_x = (int16_t)(center_x - side * half_width);
    outer_x = (int16_t)(center_x + side * half_width);

    switch (pose->brow) {
    case COMP_PET_BROW_RAISED:
        outer_y = (int16_t)(inner_y + 5);
        break;
    case COMP_PET_BROW_WARM:
        inner_y = (int16_t)(inner_y + 3);
        outer_y = (int16_t)(inner_y - 3);
        break;
    case COMP_PET_BROW_FOCUSED:
        inner_y = (int16_t)(inner_y + 6);
        outer_y = (int16_t)(inner_y - 7);
        break;
    case COMP_PET_BROW_WORRIED:
        inner_y = (int16_t)(inner_y - 5);
        outer_y = (int16_t)(inner_y + 8);
        break;
    case COMP_PET_BROW_SLEEPY:
        inner_y = (int16_t)(inner_y + 5);
        outer_y = (int16_t)(inner_y + 2);
        break;
    case COMP_PET_BROW_RELAXED:
    default:
        outer_y = (int16_t)(inner_y + 1);
        break;
    }
    draw_logical_line(framebuffer, inner_x, inner_y, outer_x, outer_y, true);
    fill_logical_ellipse(framebuffer, inner_x, inner_y, 1, 1, true);
    fill_logical_ellipse(framebuffer, outer_x, outer_y, 1, 1, true);
}

static void draw_mouth(comp_screen_framebuffer_t *framebuffer,
                       const comp_pet_expression_pose_t *pose,
                       int16_t face_shift_x,
                       int16_t face_shift_y)
{
    const int16_t center_x = (int16_t)(COMP_PET_STYLE_CANVAS_CENTER_X + face_shift_x);
    const int16_t center_y = (int16_t)(COMP_PET_STYLE_MOUTH_CENTER_Y + face_shift_y);
    const int16_t nose_y = (int16_t)(COMP_PET_STYLE_NOSE_Y + face_shift_y);
    const int16_t mouth_width = (int16_t)(COMP_PET_STYLE_MOUTH_BASE_WIDTH *
                                          pose->mouth_scale / 100u);
    const int16_t mouth_inner = (int16_t)(COMP_PET_STYLE_MOUTH_BASE_INNER *
                                          pose->mouth_scale / 100u);
    const int16_t mouth_height = (int16_t)(COMP_PET_STYLE_MOUTH_BASE_HEIGHT *
                                           pose->mouth_scale / 100u);

    fill_logical_ellipse(framebuffer,
                         center_x,
                         nose_y,
                         pose->mouth_scale >= 118u ? 4 : 3,
                         2,
                         true);
    fill_logical_ellipse(framebuffer,
                         (int16_t)(center_x - 1),
                         (int16_t)(nose_y - 1),
                         1,
                         1,
                         false);
    draw_logical_line(framebuffer,
                      center_x,
                      (int16_t)(nose_y + 2),
                      center_x,
                      (int16_t)(center_y - 12),
                      true);
    switch (pose->mouth) {
    case COMP_PET_MOUTH_SMILE:
        draw_logical_line(framebuffer,
                          center_x,
                          (int16_t)(center_y - 10),
                          (int16_t)(center_x - mouth_inner),
                          (int16_t)(center_y - 3),
                          true);
        draw_logical_line(framebuffer,
                          center_x,
                          (int16_t)(center_y - 10),
                          (int16_t)(center_x + mouth_inner),
                          (int16_t)(center_y - 3),
                          true);
        draw_logical_line(framebuffer,
                          (int16_t)(center_x - mouth_inner),
                          (int16_t)(center_y - 3),
                          (int16_t)(center_x - mouth_width),
                          (int16_t)(center_y - 6),
                          true);
        draw_logical_line(framebuffer,
                          (int16_t)(center_x + mouth_inner),
                          (int16_t)(center_y - 3),
                          (int16_t)(center_x + mouth_width),
                          (int16_t)(center_y - 6),
                          true);
        break;
    case COMP_PET_MOUTH_OPEN:
        fill_logical_ellipse(framebuffer,
                             center_x,
                             (int16_t)(center_y - 4),
                             (int16_t)(13 * pose->mouth_scale / 100u),
                             (int16_t)(9 * pose->mouth_scale / 100u),
                             true);
        fill_logical_ellipse(framebuffer,
                             center_x,
                             (int16_t)(center_y - 4),
                             (int16_t)(7 * pose->mouth_scale / 100u),
                             (int16_t)(4 * pose->mouth_scale / 100u),
                             false);
        break;
    case COMP_PET_MOUTH_FROWN:
        draw_logical_line(framebuffer,
                          (int16_t)(center_x - mouth_width),
                          center_y,
                          (int16_t)(center_x - mouth_inner),
                          (int16_t)(center_y - mouth_height),
                          true);
        draw_logical_line(framebuffer,
                          (int16_t)(center_x - mouth_inner),
                          (int16_t)(center_y - mouth_height),
                          (int16_t)(center_x + mouth_inner),
                          (int16_t)(center_y - mouth_height),
                          true);
        draw_logical_line(framebuffer,
                          (int16_t)(center_x + mouth_inner),
                          (int16_t)(center_y - mouth_height),
                          (int16_t)(center_x + mouth_width),
                          center_y,
                          true);
        break;
    case COMP_PET_MOUTH_SOFT:
        draw_logical_line(framebuffer,
                          center_x,
                          (int16_t)(center_y - 8),
                          (int16_t)(center_x - mouth_inner),
                          (int16_t)(center_y - 4),
                          true);
        draw_logical_line(framebuffer,
                          center_x,
                          (int16_t)(center_y - 8),
                          (int16_t)(center_x + mouth_inner),
                          (int16_t)(center_y - 4),
                          true);
        draw_logical_line(framebuffer,
                          (int16_t)(center_x - mouth_inner),
                          (int16_t)(center_y - 4),
                          (int16_t)(center_x - mouth_width + 3),
                          (int16_t)(center_y - 5),
                          true);
        draw_logical_line(framebuffer,
                          (int16_t)(center_x + mouth_inner),
                          (int16_t)(center_y - 4),
                          (int16_t)(center_x + mouth_width - 3),
                          (int16_t)(center_y - 5),
                          true);
        break;
    case COMP_PET_MOUTH_POUT:
        fill_logical_ellipse(framebuffer,
                             center_x,
                             (int16_t)(center_y - 5),
                             (int16_t)(7 * pose->mouth_scale / 100u),
                             (int16_t)(5 * pose->mouth_scale / 100u),
                             true);
        fill_logical_ellipse(framebuffer,
                             center_x,
                             (int16_t)(center_y - 5),
                             (int16_t)(3 * pose->mouth_scale / 100u),
                             2,
                             false);
        break;
    case COMP_PET_MOUTH_NEUTRAL:
    default:
        draw_logical_line(framebuffer,
                          (int16_t)(center_x - mouth_inner - 4),
                          (int16_t)(center_y - 4),
                          (int16_t)(center_x + mouth_inner + 4),
                          (int16_t)(center_y - 4),
                          true);
        break;
    }
    if (pose->mouth == COMP_PET_MOUTH_SMILE) {
        fill_logical_ellipse(framebuffer,
                             (int16_t)(center_x - mouth_width),
                             (int16_t)(center_y - 6),
                             2,
                             2,
                             true);
        fill_logical_ellipse(framebuffer,
                             (int16_t)(center_x + mouth_width),
                             (int16_t)(center_y - 6),
                             2,
                             2,
                             true);
    } else if (pose->mouth == COMP_PET_MOUTH_SOFT) {
        fill_logical_ellipse(framebuffer,
                             (int16_t)(center_x - mouth_width + 3),
                             (int16_t)(center_y - 5),
                             1,
                             1,
                             true);
        fill_logical_ellipse(framebuffer,
                             (int16_t)(center_x + mouth_width - 3),
                             (int16_t)(center_y - 5),
                             1,
                             1,
                             true);
    } else if (pose->mouth == COMP_PET_MOUTH_FROWN) {
        fill_logical_ellipse(framebuffer,
                             (int16_t)(center_x - mouth_width),
                             center_y,
                             1,
                             1,
                             true);
        fill_logical_ellipse(framebuffer,
                             (int16_t)(center_x + mouth_width),
                             center_y,
                             1,
                             1,
                             true);
    }
}

static void draw_mark(comp_screen_framebuffer_t *framebuffer, comp_pet_mark_t mark)
{
    switch (mark) {
    case COMP_PET_MARK_LISTEN:
        draw_logical_line(framebuffer, 151, 91, 146, 98, true);
        draw_logical_line(framebuffer, 146, 98, 151, 105, true);
        draw_logical_line(framebuffer, 164, 88, 158, 98, true);
        draw_logical_line(framebuffer, 158, 98, 164, 108, true);
        draw_logical_line(framebuffer, 49, 91, 54, 98, true);
        draw_logical_line(framebuffer, 54, 98, 49, 105, true);
        break;
    case COMP_PET_MARK_THINK:
        stroke_logical_ellipse(framebuffer, 151, 72, 2, 2, true);
        stroke_logical_ellipse(framebuffer, 160, 62, 4, 4, true);
        stroke_logical_ellipse(framebuffer, 171, 50, 8, 6, true);
        fill_logical_ellipse(framebuffer, 176, 47, 4, 3, true);
        fill_logical_ellipse(framebuffer, 176, 47, 2, 1, false);
        break;
    case COMP_PET_MARK_RECORD:
        fill_logical_ellipse(framebuffer, 170, 34, 6, 6, true);
        fill_logical_ellipse(framebuffer, 170, 34, 3, 3, false);
        fill_logical_ellipse(framebuffer, 170, 34, 1, 1, true);
        break;
    case COMP_PET_MARK_SPARK:
        draw_small_spark(framebuffer, 170, 46, 10);
        draw_small_spark(framebuffer, 152, 59, 5);
        break;
    case COMP_PET_MARK_ALERT:
        draw_logical_line(framebuffer, 170, 37, 170, 53, true);
        fill_logical_ellipse(framebuffer, 170, 61, 2, 2, true);
        break;
    case COMP_PET_MARK_QUESTION:
        draw_small_question(framebuffer, 150, 38);
        break;
    case COMP_PET_MARK_HEART:
        draw_small_heart(framebuffer, 100, 34, 6);
        break;
    case COMP_PET_MARK_SLEEP:
        draw_small_z(framebuffer, 151, 35, 10);
        draw_small_z(framebuffer, 164, 25, 8);
        break;
    case COMP_PET_MARK_NONE:
    default:
        break;
    }
}

static uint32_t framebuffer_signature(const uint8_t *data, size_t length)
{
    uint32_t signature = 2166136261u;

    for (size_t index = 0u; index < length; ++index) {
        signature ^= data[index];
        signature *= 16777619u;
    }
    return signature;
}

bool comp_pet_expression_pose_is_valid(const comp_pet_expression_pose_t *pose)
{
    return pose != NULL && comp_epaper_expression_is_supported(pose->expression) &&
           pose->gaze_x >= -32 && pose->gaze_x <= 32 &&
           pose->gaze_y >= -32 && pose->gaze_y <= 32 &&
           pose->eye_open >= 18u && pose->eye_open <= 100u &&
           pose->eyelid_tilt >= -24 && pose->eyelid_tilt <= 24 &&
           pose->eye_width >= 60u && pose->eye_width <= 140u &&
           pose->eye_spacing >= 76u && pose->eye_spacing <= 124u &&
           pose->eye_pair_tilt >= -12 && pose->eye_pair_tilt <= 12 &&
           pose->highlight_scale >= 60u && pose->highlight_scale <= 140u &&
           pose->face_shift_x >= -18 && pose->face_shift_x <= 18 &&
           pose->face_shift_y >= -18 && pose->face_shift_y <= 18 &&
           pose->brow_lift <= 36u &&
           pose->brow_asymmetry >= -18 && pose->brow_asymmetry <= 18 &&
           pose->mouth_scale >= 60u && pose->mouth_scale <= 140u &&
           pose->cheek_strength <= 3u && pose->brow <= COMP_PET_BROW_SLEEPY &&
           pose->mouth <= COMP_PET_MOUTH_POUT &&
           pose->mark <= COMP_PET_MARK_SLEEP;
}

void comp_pet_expression_pose_from_expression(comp_pet_expression_pose_t *out_pose,
                                              comp_epaper_expression_t expression,
                                              uint8_t phase,
                                              uint32_t variation_seed)
{
    int8_t idle_shift = (variation_seed & 1u) == 0u ? -8 : 8;
    int8_t variation_shift = (int8_t)((variation_seed % 3u) * 4u) - 4;
    uint8_t motion_phase = (uint8_t)(phase % 3u);

    if (out_pose == NULL) {
        return;
    }
    *out_pose = (comp_pet_expression_pose_t){
        .expression = comp_epaper_expression_is_supported(expression)
                          ? expression : COMP_EPAPER_EXPRESSION_IDLE,
        .gaze_x = 0,
        .gaze_y = 0,
        .eye_open = 86u,
        .eyelid_tilt = 0,
        .eye_width = 100u,
        .eye_spacing = 100u,
        .eye_pair_tilt = 0,
        .highlight_scale = 100u,
        .face_shift_x = 0,
        .face_shift_y = 0,
        .brow_lift = 0u,
        .brow_asymmetry = 0,
        .mouth_scale = 100u,
        .cheek_strength = 0u,
        .variation = (uint8_t)variation_seed,
        .brow = COMP_PET_BROW_NONE,
        .mouth = COMP_PET_MOUTH_NEUTRAL,
        .mark = COMP_PET_MARK_NONE,
    };
    switch (out_pose->expression) {
    case COMP_EPAPER_EXPRESSION_IDLE:
        out_pose->gaze_x = motion_phase == 1u ? idle_shift : 0;
        out_pose->eye_open = motion_phase == 1u ? 74u : 90u;
        out_pose->eye_width = 112u;
        out_pose->face_shift_x = motion_phase == 1u ? (int8_t)(idle_shift / 4) : 0;
        out_pose->eye_spacing = 92u;
        out_pose->highlight_scale = 122u;
        out_pose->brow = COMP_PET_BROW_RELAXED;
        out_pose->brow_lift = 4u;
        out_pose->mouth = COMP_PET_MOUTH_SOFT;
        out_pose->mouth_scale = 92u;
        out_pose->cheek_strength = 1u;
        break;
    case COMP_EPAPER_EXPRESSION_LISTENING:
        out_pose->eye_open = 98u;
        out_pose->eye_width = 112u;
        out_pose->eye_spacing = 110u;
        out_pose->highlight_scale = 92u;
        out_pose->gaze_x = motion_phase == 1u ? 6 : -4;
        out_pose->face_shift_x = motion_phase == 1u ? 2 : -1;
        out_pose->face_shift_y = -2;
        out_pose->brow = COMP_PET_BROW_RAISED;
        out_pose->brow_lift = 14u;
        out_pose->mouth = COMP_PET_MOUTH_POUT;
        out_pose->mouth_scale = 78u;
        out_pose->mark = COMP_PET_MARK_LISTEN;
        break;
    case COMP_EPAPER_EXPRESSION_THINKING:
        out_pose->eye_open = motion_phase == 1u ? 68u : 78u;
        out_pose->eye_width = 90u;
        out_pose->eye_spacing = 92u;
        out_pose->eye_pair_tilt = 6;
        out_pose->highlight_scale = 82u;
        out_pose->gaze_x = 16;
        out_pose->gaze_y = -12;
        out_pose->eyelid_tilt = 8;
        out_pose->face_shift_x = 5;
        out_pose->face_shift_y = -3;
        out_pose->brow = COMP_PET_BROW_RAISED;
        out_pose->brow_lift = 10u;
        out_pose->brow_asymmetry = 15;
        out_pose->mouth = motion_phase == 2u ? COMP_PET_MOUTH_POUT : COMP_PET_MOUTH_NEUTRAL;
        out_pose->mouth_scale = 78u;
        out_pose->mark = motion_phase == 0u ? COMP_PET_MARK_QUESTION : COMP_PET_MARK_THINK;
        break;
    case COMP_EPAPER_EXPRESSION_SPEAKING:
        out_pose->eye_open = 88u;
        out_pose->eye_width = 105u;
        out_pose->eye_spacing = 96u;
        out_pose->face_shift_y = -1;
        out_pose->brow = COMP_PET_BROW_WARM;
        out_pose->brow_lift = 4u;
        out_pose->mouth = motion_phase == 1u ? COMP_PET_MOUTH_OPEN : COMP_PET_MOUTH_SMILE;
        out_pose->mouth_scale = motion_phase == 1u ? 114u : 105u;
        out_pose->cheek_strength = 2u;
        out_pose->mark = motion_phase == 1u ? COMP_PET_MARK_LISTEN : COMP_PET_MARK_NONE;
        break;
    case COMP_EPAPER_EXPRESSION_HAPPY:
        out_pose->eye_open = motion_phase == 1u ? 42u : 56u;
        out_pose->eye_width = 110u;
        out_pose->eye_spacing = 88u;
        out_pose->highlight_scale = 130u;
        out_pose->face_shift_y = -2;
        out_pose->brow = COMP_PET_BROW_WARM;
        out_pose->brow_lift = 7u;
        out_pose->mouth = COMP_PET_MOUTH_SMILE;
        out_pose->mouth_scale = 120u;
        out_pose->cheek_strength = 3u;
        out_pose->mark = motion_phase == 2u ? COMP_PET_MARK_HEART : COMP_PET_MARK_SPARK;
        break;
    case COMP_EPAPER_EXPRESSION_SLEEPY:
        out_pose->eye_open = motion_phase == 1u ? 24u : 38u;
        out_pose->eye_width = 88u;
        out_pose->eye_spacing = 94u;
        out_pose->highlight_scale = 78u;
        out_pose->gaze_y = 12;
        out_pose->eyelid_tilt = -6;
        out_pose->face_shift_y = 5;
        out_pose->brow = COMP_PET_BROW_SLEEPY;
        out_pose->mouth = COMP_PET_MOUTH_SOFT;
        out_pose->mouth_scale = 72u;
        out_pose->mark = COMP_PET_MARK_SLEEP;
        break;
    case COMP_EPAPER_EXPRESSION_RECORDING:
        out_pose->eye_open = 92u;
        out_pose->eye_width = 106u;
        out_pose->eye_spacing = 102u;
        out_pose->highlight_scale = 90u;
        out_pose->brow = COMP_PET_BROW_FOCUSED;
        out_pose->brow_lift = 2u;
        out_pose->mouth = COMP_PET_MOUTH_NEUTRAL;
        out_pose->mouth_scale = 72u;
        out_pose->mark = COMP_PET_MARK_RECORD;
        break;
    case COMP_EPAPER_EXPRESSION_SYNC_COMPLETE:
        out_pose->eye_open = 52u;
        out_pose->eye_width = 114u;
        out_pose->eye_spacing = 88u;
        out_pose->highlight_scale = 136u;
        out_pose->eyelid_tilt = -4;
        out_pose->face_shift_y = -3;
        out_pose->brow = COMP_PET_BROW_WARM;
        out_pose->brow_lift = 8u;
        out_pose->mouth = COMP_PET_MOUTH_SMILE;
        out_pose->mouth_scale = 124u;
        out_pose->cheek_strength = 3u;
        out_pose->mark = COMP_PET_MARK_SPARK;
        break;
    case COMP_EPAPER_EXPRESSION_LOW_BATTERY:
        out_pose->eye_open = 45u;
        out_pose->eye_width = 92u;
        out_pose->eye_spacing = 98u;
        out_pose->highlight_scale = 82u;
        out_pose->gaze_y = 10;
        out_pose->eyelid_tilt = 6;
        out_pose->face_shift_y = 4;
        out_pose->brow = COMP_PET_BROW_WORRIED;
        out_pose->brow_lift = 4u;
        out_pose->mouth = COMP_PET_MOUTH_FROWN;
        out_pose->mouth_scale = 82u;
        break;
    case COMP_EPAPER_EXPRESSION_ERROR:
        out_pose->eye_open = 64u;
        out_pose->eye_width = 96u;
        out_pose->eye_spacing = 104u;
        out_pose->highlight_scale = 72u;
        out_pose->eyelid_tilt = 18;
        out_pose->brow = COMP_PET_BROW_FOCUSED;
        out_pose->brow_lift = 4u;
        out_pose->mouth = COMP_PET_MOUTH_FROWN;
        out_pose->mouth_scale = 94u;
        out_pose->mark = COMP_PET_MARK_ALERT;
        break;
    case COMP_EPAPER_EXPRESSION_COUNT:
    default:
        break;
    }
    if (out_pose->expression != COMP_EPAPER_EXPRESSION_ERROR) {
        out_pose->gaze_x = clamp_gaze((int16_t)out_pose->gaze_x + variation_shift);
    }
}

void comp_pet_expression_pose_from_touch(comp_pet_expression_pose_t *out_pose,
                                         uint16_t x,
                                         uint16_t y,
                                         uint16_t width,
                                         uint16_t height,
                                         uint8_t phase,
                                         uint32_t variation_seed)
{
    uint16_t safe_width = width > 1u ? width - 1u : 1u;
    uint16_t safe_height = height > 1u ? height - 1u : 1u;

    comp_pet_expression_pose_from_expression(out_pose,
                                              COMP_EPAPER_EXPRESSION_HAPPY,
                                              phase,
                                              variation_seed);
    if (out_pose == NULL) {
        return;
    }
    out_pose->gaze_x = clamp_gaze(((int16_t)(x > safe_width ? safe_width : x) * 64) /
                                  (int16_t)safe_width - 32);
    out_pose->gaze_y = clamp_gaze(((int16_t)(y > safe_height ? safe_height : y) * 64) /
                                  (int16_t)safe_height - 32);
    out_pose->eye_open = clamp_open(phase == 0u ? 92 : phase == 1u ? 48 : 64);
    out_pose->eyelid_tilt = phase == 1u ? -4 : 0;
    out_pose->eye_width = phase == 1u ? 112u : 118u;
    out_pose->eye_spacing = phase == 0u ? 104u : 90u;
    out_pose->eye_pair_tilt = clamp_eye_pair_tilt(out_pose->gaze_y / 8);
    out_pose->highlight_scale = phase == 1u ? 128u : 138u;
    out_pose->face_shift_x = clamp_face_shift(out_pose->gaze_x / 3);
    out_pose->face_shift_y = clamp_face_shift(out_pose->gaze_y / 4);
    out_pose->brow = phase == 1u ? COMP_PET_BROW_WARM : COMP_PET_BROW_RAISED;
    out_pose->brow_lift = phase == 0u ? 13u : 6u;
    out_pose->brow_asymmetry = clamp_brow_asymmetry(out_pose->gaze_x / 3);
    out_pose->mouth = COMP_PET_MOUTH_SMILE;
    out_pose->mouth_scale = phase == 1u ? 112u : 124u;
    out_pose->cheek_strength = 3u;
    if (phase == 0u) {
        out_pose->mark = COMP_PET_MARK_QUESTION;
    } else if (phase == 1u) {
        out_pose->mark = COMP_PET_MARK_SPARK;
    } else {
        out_pose->mark = COMP_PET_MARK_HEART;
    }
}

bool comp_pet_expression_render(const comp_pet_expression_pose_t *pose,
                                comp_screen_framebuffer_t *framebuffer)
{
    int16_t eye_y;
    int16_t eye_offset_x;
    int16_t eye_half_spacing;
    int16_t left_eye_x;
    int16_t right_eye_x;

    if (!comp_pet_expression_pose_is_valid(pose) || framebuffer == NULL ||
        framebuffer->width < PET_MIN_RENDER_WIDTH ||
        framebuffer->height < PET_MIN_RENDER_HEIGHT) {
        return false;
    }
    comp_screen_framebuffer_clear(framebuffer, false);
    eye_y = (int16_t)(COMP_PET_STYLE_EYE_CENTER_Y + pose->face_shift_y +
                      pose->gaze_y / 6);
    eye_offset_x = (int16_t)(pose->face_shift_x + pose->gaze_x / 5);
    eye_half_spacing = (int16_t)(COMP_PET_STYLE_EYE_HALF_SPACING *
                                 pose->eye_spacing / 100u);
    left_eye_x = (int16_t)(COMP_PET_STYLE_CANVAS_CENTER_X - eye_half_spacing +
                           eye_offset_x);
    right_eye_x = (int16_t)(COMP_PET_STYLE_CANVAS_CENTER_X + eye_half_spacing +
                            eye_offset_x);
    draw_brow(framebuffer,
              left_eye_x,
              (int16_t)(eye_y - pose->eye_pair_tilt / 2),
              pose,
              true);
    draw_brow(framebuffer,
              right_eye_x,
              (int16_t)(eye_y + pose->eye_pair_tilt / 2),
              pose,
              false);
    draw_eye(framebuffer,
             left_eye_x,
             (int16_t)(eye_y - pose->eye_pair_tilt / 2),
             pose,
             true);
    draw_eye(framebuffer,
             right_eye_x,
             (int16_t)(eye_y + pose->eye_pair_tilt / 2),
             pose,
             false);
    draw_mouth(framebuffer, pose, pose->face_shift_x, pose->face_shift_y);
    if (pose->cheek_strength != 0u) {
        draw_logical_line(framebuffer,
                          (int16_t)(COMP_PET_STYLE_CHEEK_LEFT_X0 +
                                    pose->face_shift_x),
                          (int16_t)(COMP_PET_STYLE_CHEEK_Y0 + pose->face_shift_y),
                          (int16_t)(COMP_PET_STYLE_CHEEK_LEFT_X1 +
                                    pose->face_shift_x),
                          (int16_t)(COMP_PET_STYLE_CHEEK_Y1 + pose->face_shift_y),
                          true);
        draw_logical_line(framebuffer,
                          (int16_t)(COMP_PET_STYLE_CHEEK_RIGHT_X0 +
                                    pose->face_shift_x),
                          (int16_t)(COMP_PET_STYLE_CHEEK_Y0 + pose->face_shift_y),
                          (int16_t)(COMP_PET_STYLE_CHEEK_RIGHT_X1 +
                                    pose->face_shift_x),
                          (int16_t)(COMP_PET_STYLE_CHEEK_Y1 + pose->face_shift_y),
                          true);
        if (pose->cheek_strength > 1u) {
            draw_logical_line(framebuffer,
                              (int16_t)(COMP_PET_STYLE_CHEEK_LEFT_X0 +
                                        pose->face_shift_x),
                              (int16_t)(COMP_PET_STYLE_CHEEK_Y0 + 7 +
                                        pose->face_shift_y),
                              (int16_t)(COMP_PET_STYLE_CHEEK_LEFT_X1 - 1 +
                                        pose->face_shift_x),
                              (int16_t)(COMP_PET_STYLE_CHEEK_Y1 + 7 +
                                        pose->face_shift_y),
                              true);
            draw_logical_line(framebuffer,
                              (int16_t)(COMP_PET_STYLE_CHEEK_RIGHT_X0 +
                                        pose->face_shift_x),
                              (int16_t)(COMP_PET_STYLE_CHEEK_Y0 + 7 +
                                        pose->face_shift_y),
                              (int16_t)(COMP_PET_STYLE_CHEEK_RIGHT_X1 + 1 +
                                        pose->face_shift_x),
                              (int16_t)(COMP_PET_STYLE_CHEEK_Y1 + 7 +
                                        pose->face_shift_y),
                              true);
        }
        if (pose->cheek_strength > 2u) {
            fill_logical_ellipse(framebuffer,
                                 (int16_t)(COMP_PET_STYLE_CHEEK_DOT_LEFT_X +
                                           pose->face_shift_x),
                                 (int16_t)(COMP_PET_STYLE_CHEEK_DOT_Y +
                                           pose->face_shift_y),
                                 2,
                                 2,
                                 true);
            fill_logical_ellipse(framebuffer,
                                 (int16_t)(COMP_PET_STYLE_CHEEK_DOT_RIGHT_X +
                                           pose->face_shift_x),
                                 (int16_t)(COMP_PET_STYLE_CHEEK_DOT_Y +
                                           pose->face_shift_y),
                                 2,
                                 2,
                                 true);
        }
    }
    draw_mark(framebuffer, pose->mark);
    return true;
}

bool comp_pet_expression_self_test(void)
{
    comp_pet_expression_pose_t pose;
    comp_pet_expression_pose_t profile_pose;
    comp_screen_framebuffer_t framebuffer;
    uint8_t render_data[512];
    uint32_t profile_signatures[COMP_EPAPER_EXPRESSION_COUNT];
    bool rendered_pixel = false;

    comp_pet_expression_pose_from_touch(&pose, 0u, 199u, 200u, 200u, 1u, 7u);
    if (!comp_pet_expression_pose_is_valid(&pose) || pose.gaze_x >= 0 || pose.gaze_y <= 0 ||
        pose.expression != COMP_EPAPER_EXPRESSION_HAPPY ||
        pose.face_shift_x >= 0 || pose.face_shift_y <= 0 ||
        pose.brow != COMP_PET_BROW_WARM || pose.eye_spacing != 90u ||
        pose.eye_pair_tilt <= 0 || pose.cheek_strength != 3u) {
        return false;
    }
    for (uint8_t expression = COMP_EPAPER_EXPRESSION_IDLE;
         expression < COMP_EPAPER_EXPRESSION_COUNT;
         ++expression) {
        comp_pet_expression_pose_from_expression(
            &profile_pose, (comp_epaper_expression_t)expression, 0u, 9u);
        if (!comp_pet_expression_pose_is_valid(&profile_pose) ||
            !comp_screen_framebuffer_init(&framebuffer,
                                          render_data,
                                          sizeof(render_data),
                                          64u,
                                          64u) ||
            !comp_pet_expression_render(&profile_pose, &framebuffer)) {
            return false;
        }
        profile_signatures[expression] = framebuffer_signature(render_data, sizeof(render_data));
        for (uint8_t previous = COMP_EPAPER_EXPRESSION_IDLE;
             previous < expression;
             ++previous) {
            if (profile_signatures[previous] == profile_signatures[expression]) {
                return false;
            }
        }
    }
    comp_pet_expression_pose_from_expression(&profile_pose,
                                              COMP_EPAPER_EXPRESSION_LISTENING,
                                              0u,
                                              3u);
    if (profile_pose.brow != COMP_PET_BROW_RAISED || profile_pose.brow_lift < 10u ||
        profile_pose.eye_spacing < 108u || profile_pose.mouth != COMP_PET_MOUTH_POUT ||
        profile_pose.face_shift_y >= 0) {
        return false;
    }
    comp_pet_expression_pose_from_expression(&profile_pose,
                                              COMP_EPAPER_EXPRESSION_HAPPY,
                                              0u,
                                              3u);
    if (profile_pose.brow != COMP_PET_BROW_WARM ||
        profile_pose.mouth != COMP_PET_MOUTH_SMILE ||
        profile_pose.eye_spacing > 90u || profile_pose.cheek_strength != 3u ||
        profile_pose.mouth_scale < 120u) {
        return false;
    }
    comp_pet_expression_pose_from_expression(&pose,
                                              COMP_EPAPER_EXPRESSION_THINKING,
                                              0u,
                                              3u);
    if (!comp_pet_expression_pose_is_valid(&pose) ||
        pose.brow != COMP_PET_BROW_RAISED || pose.brow_asymmetry <= 0 ||
        pose.face_shift_x <= 0 || pose.eye_pair_tilt <= 0 ||
        pose.mouth_scale >= 100u) {
        return false;
    }
    comp_pet_expression_pose_from_expression(&pose,
                                              COMP_EPAPER_EXPRESSION_ERROR,
                                              0u,
                                              3u);
    if (!comp_pet_expression_pose_is_valid(&pose) ||
        pose.mark != COMP_PET_MARK_ALERT || pose.mouth != COMP_PET_MOUTH_FROWN ||
        pose.eyelid_tilt != 18 ||
        !comp_screen_framebuffer_init(&framebuffer,
                                      render_data,
                                      sizeof(render_data),
                                      64u,
                                      64u) ||
        !comp_pet_expression_render(&pose, &framebuffer)) {
        return false;
    }
    for (size_t index = 0u; index < sizeof(render_data); ++index) {
        if (render_data[index] != 0xffu) {
            rendered_pixel = true;
            break;
        }
    }
    return rendered_pixel;
}
