#ifndef COMPANION_EPAPER_SCREEN_FRAMEBUFFER_H
#define COMPANION_EPAPER_SCREEN_FRAMEBUFFER_H

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

typedef struct {
    uint8_t *data;
    size_t data_bytes;
    uint16_t width;
    uint16_t height;
    uint16_t stride_bytes;
} comp_screen_framebuffer_t;

bool comp_screen_framebuffer_init(comp_screen_framebuffer_t *framebuffer,
                                  uint8_t *data,
                                  size_t data_bytes,
                                  uint16_t width,
                                  uint16_t height);
void comp_screen_framebuffer_clear(comp_screen_framebuffer_t *framebuffer, bool black);
void comp_screen_framebuffer_set_pixel(comp_screen_framebuffer_t *framebuffer,
                                       int16_t x,
                                       int16_t y,
                                       bool black);
void comp_screen_framebuffer_fill_rect(comp_screen_framebuffer_t *framebuffer,
                                       int16_t x,
                                       int16_t y,
                                       uint16_t width,
                                       uint16_t height,
                                       bool black);
void comp_screen_framebuffer_invert_rect(comp_screen_framebuffer_t *framebuffer,
                                         int16_t x,
                                         int16_t y,
                                         uint16_t width,
                                         uint16_t height);
void comp_screen_framebuffer_stroke_rect(comp_screen_framebuffer_t *framebuffer,
                                         int16_t x,
                                         int16_t y,
                                         uint16_t width,
                                         uint16_t height,
                                         uint8_t thickness,
                                         bool black);
void comp_screen_framebuffer_draw_line(comp_screen_framebuffer_t *framebuffer,
                                       int16_t x0,
                                       int16_t y0,
                                       int16_t x1,
                                       int16_t y1,
                                       bool black);
uint16_t comp_screen_framebuffer_text_width(const char *text, uint8_t scale);
void comp_screen_framebuffer_draw_text(comp_screen_framebuffer_t *framebuffer,
                                       int16_t x,
                                       int16_t y,
                                       const char *text,
                                       uint8_t scale,
                                       bool black);
bool comp_screen_framebuffer_self_test(void);

#ifdef __cplusplus
}
#endif

#endif /* COMPANION_EPAPER_SCREEN_FRAMEBUFFER_H */
