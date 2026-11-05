#include "screen_framebuffer.h"

#include <string.h>

static const char k_font_chars[] = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ:-?%!~.";
static const uint8_t k_font_rows[][7] = {
    {0x0Eu,0x11u,0x13u,0x15u,0x19u,0x11u,0x0Eu},
    {0x04u,0x0Cu,0x04u,0x04u,0x04u,0x04u,0x0Eu},
    {0x0Eu,0x11u,0x01u,0x02u,0x04u,0x08u,0x1Fu},
    {0x1Eu,0x01u,0x01u,0x0Eu,0x01u,0x01u,0x1Eu},
    {0x02u,0x06u,0x0Au,0x12u,0x1Fu,0x02u,0x02u},
    {0x1Fu,0x10u,0x10u,0x1Eu,0x01u,0x01u,0x1Eu},
    {0x0Eu,0x10u,0x10u,0x1Eu,0x11u,0x11u,0x0Eu},
    {0x1Fu,0x01u,0x02u,0x04u,0x08u,0x08u,0x08u},
    {0x0Eu,0x11u,0x11u,0x0Eu,0x11u,0x11u,0x0Eu},
    {0x0Eu,0x11u,0x11u,0x0Fu,0x01u,0x01u,0x0Eu},
    {0x0Eu,0x11u,0x11u,0x1Fu,0x11u,0x11u,0x11u},
    {0x1Eu,0x11u,0x11u,0x1Eu,0x11u,0x11u,0x1Eu},
    {0x0Eu,0x11u,0x10u,0x10u,0x10u,0x11u,0x0Eu},
    {0x1Eu,0x11u,0x11u,0x11u,0x11u,0x11u,0x1Eu},
    {0x1Fu,0x10u,0x10u,0x1Eu,0x10u,0x10u,0x1Fu},
    {0x1Fu,0x10u,0x10u,0x1Eu,0x10u,0x10u,0x10u},
    {0x0Eu,0x11u,0x10u,0x17u,0x11u,0x11u,0x0Fu},
    {0x11u,0x11u,0x11u,0x1Fu,0x11u,0x11u,0x11u},
    {0x0Eu,0x04u,0x04u,0x04u,0x04u,0x04u,0x0Eu},
    {0x07u,0x02u,0x02u,0x02u,0x12u,0x12u,0x0Cu},
    {0x11u,0x12u,0x14u,0x18u,0x14u,0x12u,0x11u},
    {0x10u,0x10u,0x10u,0x10u,0x10u,0x10u,0x1Fu},
    {0x11u,0x1Bu,0x15u,0x15u,0x11u,0x11u,0x11u},
    {0x11u,0x19u,0x15u,0x13u,0x11u,0x11u,0x11u},
    {0x0Eu,0x11u,0x11u,0x11u,0x11u,0x11u,0x0Eu},
    {0x1Eu,0x11u,0x11u,0x1Eu,0x10u,0x10u,0x10u},
    {0x0Eu,0x11u,0x11u,0x11u,0x15u,0x12u,0x0Du},
    {0x1Eu,0x11u,0x11u,0x1Eu,0x14u,0x12u,0x11u},
    {0x0Fu,0x10u,0x10u,0x0Eu,0x01u,0x01u,0x1Eu},
    {0x1Fu,0x04u,0x04u,0x04u,0x04u,0x04u,0x04u},
    {0x11u,0x11u,0x11u,0x11u,0x11u,0x11u,0x0Eu},
    {0x11u,0x11u,0x11u,0x11u,0x11u,0x0Au,0x04u},
    {0x11u,0x11u,0x11u,0x15u,0x15u,0x15u,0x0Au},
    {0x11u,0x11u,0x0Au,0x04u,0x0Au,0x11u,0x11u},
    {0x11u,0x11u,0x0Au,0x04u,0x04u,0x04u,0x04u},
    {0x1Fu,0x01u,0x02u,0x04u,0x08u,0x10u,0x1Fu},
    {0x00u,0x04u,0x04u,0x00u,0x04u,0x04u,0x00u},
    {0x00u,0x00u,0x00u,0x1Fu,0x00u,0x00u,0x00u},
    {0x0Eu,0x11u,0x01u,0x02u,0x04u,0x00u,0x04u},
    {0x19u,0x19u,0x02u,0x04u,0x08u,0x13u,0x13u},
    {0x04u,0x04u,0x04u,0x04u,0x04u,0x00u,0x04u},
    {0x00u,0x00u,0x09u,0x16u,0x00u,0x00u,0x00u}, /* ~ estimate */
    {0x00u,0x00u,0x00u,0x00u,0x00u,0x00u,0x04u}, /* voltage decimal */
};

static const uint8_t *font_rows(char character)
{
    const char *match = strchr(k_font_chars, character);
    return match == NULL ? NULL : k_font_rows[(size_t)(match - k_font_chars)];
}

bool comp_screen_framebuffer_init(comp_screen_framebuffer_t *framebuffer,
                                  uint8_t *data,
                                  size_t data_bytes,
                                  uint16_t width,
                                  uint16_t height)
{
    uint16_t stride;
    size_t required;

    if (framebuffer == NULL || data == NULL || width == 0u || height == 0u) {
        return false;
    }
    stride = (uint16_t)((width + 7u) / 8u);
    required = (size_t)stride * height;
    if (data_bytes < required) {
        return false;
    }
    *framebuffer = (comp_screen_framebuffer_t){
        .data = data,
        .data_bytes = data_bytes,
        .width = width,
        .height = height,
        .stride_bytes = stride,
    };
    return true;
}

void comp_screen_framebuffer_clear(comp_screen_framebuffer_t *framebuffer, bool black)
{
    if (framebuffer != NULL && framebuffer->data != NULL) {
        memset(framebuffer->data, black ? 0x00 : 0xFF, framebuffer->data_bytes);
    }
}

void comp_screen_framebuffer_set_pixel(comp_screen_framebuffer_t *framebuffer,
                                       int16_t x,
                                       int16_t y,
                                       bool black)
{
    size_t index;
    uint8_t mask;

    if (framebuffer == NULL || framebuffer->data == NULL || x < 0 || y < 0 ||
        x >= (int16_t)framebuffer->width || y >= (int16_t)framebuffer->height) {
        return;
    }
    index = ((size_t)y * framebuffer->stride_bytes) + ((uint16_t)x / 8u);
    mask = (uint8_t)(0x80u >> ((uint16_t)x & 7u));
    if (black) {
        framebuffer->data[index] &= (uint8_t)~mask;
    } else {
        framebuffer->data[index] |= mask;
    }
}

void comp_screen_framebuffer_fill_rect(comp_screen_framebuffer_t *framebuffer,
                                       int16_t x,
                                       int16_t y,
                                       uint16_t width,
                                       uint16_t height,
                                       bool black)
{
    for (uint16_t yy = 0u; yy < height; ++yy) {
        for (uint16_t xx = 0u; xx < width; ++xx) {
            comp_screen_framebuffer_set_pixel(framebuffer,
                                              (int16_t)(x + (int16_t)xx),
                                              (int16_t)(y + (int16_t)yy),
                                              black);
        }
    }
}

void comp_screen_framebuffer_invert_rect(comp_screen_framebuffer_t *framebuffer,
                                         int16_t x,
                                         int16_t y,
                                         uint16_t width,
                                         uint16_t height)
{
    if (framebuffer == NULL || framebuffer->data == NULL) {
        return;
    }
    for (uint16_t yy = 0u; yy < height; ++yy) {
        int16_t pixel_y = (int16_t)(y + (int16_t)yy);
        if (pixel_y < 0 || pixel_y >= (int16_t)framebuffer->height) {
            continue;
        }
        for (uint16_t xx = 0u; xx < width; ++xx) {
            int16_t pixel_x = (int16_t)(x + (int16_t)xx);
            size_t index;
            uint8_t mask;

            if (pixel_x < 0 || pixel_x >= (int16_t)framebuffer->width) {
                continue;
            }
            index = ((size_t)pixel_y * framebuffer->stride_bytes) +
                    ((uint16_t)pixel_x / 8u);
            mask = (uint8_t)(0x80u >> ((uint16_t)pixel_x & 7u));
            framebuffer->data[index] ^= mask;
        }
    }
}

void comp_screen_framebuffer_stroke_rect(comp_screen_framebuffer_t *framebuffer,
                                         int16_t x,
                                         int16_t y,
                                         uint16_t width,
                                         uint16_t height,
                                         uint8_t thickness,
                                         bool black)
{
    if (width == 0u || height == 0u || thickness == 0u) {
        return;
    }
    comp_screen_framebuffer_fill_rect(framebuffer, x, y, width, thickness, black);
    comp_screen_framebuffer_fill_rect(framebuffer,
                                      x,
                                      (int16_t)(y + (int16_t)height - thickness),
                                      width,
                                      thickness,
                                      black);
    comp_screen_framebuffer_fill_rect(framebuffer, x, y, thickness, height, black);
    comp_screen_framebuffer_fill_rect(framebuffer,
                                      (int16_t)(x + (int16_t)width - thickness),
                                      y,
                                      thickness,
                                      height,
                                      black);
}

void comp_screen_framebuffer_draw_line(comp_screen_framebuffer_t *framebuffer,
                                       int16_t x0,
                                       int16_t y0,
                                       int16_t x1,
                                       int16_t y1,
                                       bool black)
{
    int16_t dx = (int16_t)(x1 > x0 ? x1 - x0 : x0 - x1);
    int16_t sx = x0 < x1 ? 1 : -1;
    int16_t dy = (int16_t)-(y1 > y0 ? y1 - y0 : y0 - y1);
    int16_t sy = y0 < y1 ? 1 : -1;
    int16_t error = (int16_t)(dx + dy);

    for (;;) {
        comp_screen_framebuffer_set_pixel(framebuffer, x0, y0, black);
        if (x0 == x1 && y0 == y1) {
            break;
        }
        int16_t doubled = (int16_t)(2 * error);
        if (doubled >= dy) {
            error = (int16_t)(error + dy);
            x0 = (int16_t)(x0 + sx);
        }
        if (doubled <= dx) {
            error = (int16_t)(error + dx);
            y0 = (int16_t)(y0 + sy);
        }
    }
}

uint16_t comp_screen_framebuffer_text_width(const char *text, uint8_t scale)
{
    size_t length = text == NULL ? 0u : strlen(text);
    if (length == 0u || scale == 0u) {
        return 0u;
    }
    return (uint16_t)((length * 6u - 1u) * scale);
}

void comp_screen_framebuffer_draw_text(comp_screen_framebuffer_t *framebuffer,
                                       int16_t x,
                                       int16_t y,
                                       const char *text,
                                       uint8_t scale,
                                       bool black)
{
    if (text == NULL || scale == 0u) {
        return;
    }
    while (*text != '\0') {
        const uint8_t *rows = font_rows(*text);
        if (rows != NULL) {
            for (uint8_t row = 0u; row < 7u; ++row) {
                for (uint8_t column = 0u; column < 5u; ++column) {
                    if ((rows[row] & (uint8_t)(0x10u >> column)) != 0u) {
                        comp_screen_framebuffer_fill_rect(
                            framebuffer,
                            (int16_t)(x + (int16_t)(column * scale)),
                            (int16_t)(y + (int16_t)(row * scale)),
                            scale,
                            scale,
                            black);
                    }
                }
            }
        }
        x = (int16_t)(x + (int16_t)(6u * scale));
        ++text;
    }
}

bool comp_screen_framebuffer_self_test(void)
{
    uint8_t data[8] = {0};
    comp_screen_framebuffer_t framebuffer;

    if (!comp_screen_framebuffer_init(&framebuffer, data, sizeof(data), 8u, 8u)) {
        return false;
    }
    comp_screen_framebuffer_clear(&framebuffer, false);
    comp_screen_framebuffer_set_pixel(&framebuffer, 0, 0, true);
    comp_screen_framebuffer_set_pixel(&framebuffer, 7, 7, true);
    return data[0] == 0x7Fu && data[7] == 0xFEu &&
           font_rows(':') != NULL &&
           font_rows('-') != NULL &&
           font_rows('?') != NULL &&
           !comp_screen_framebuffer_init(&framebuffer, data, 7u, 8u, 8u);
}
