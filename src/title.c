#include <gbdk/platform.h>

#include "../res/title.h"
#include "blink.h"
#include "main.h"
#include "tiles.h"

#if TILE_FULLSCREEN_FIRST + title_TILE_COUNT > 256
#error title tiles exceed 256 tile limit
#endif

#define BLINK_ROW 16
#define BLINK_COL 6
#define BLINK_WIDTH 8

void title_init(void) {
    DISPLAY_OFF;
    LCDC_REG |= LCDCF_BG8000;
    set_bkg_data(TILE_FULLSCREEN_FIRST, title_TILE_COUNT, title_tiles);
    set_bkg_based_tiles(0, 0, DEVICE_SCREEN_WIDTH, DEVICE_SCREEN_HEIGHT, title_map,
                        TILE_FULLSCREEN_FIRST);
    blink_init();
    LCDC_REG = LCDCF_ON | LCDCF_BG8000 | LCDCF_OBJ8 | LCDCF_OBJON | LCDCF_BGON;
    state = STATE_TITLE;
}

void title_vblank(void) {
    const uint8_t *row;

    if (!blink_dirty)
        return;
    blink_dirty = 0;

    row = title_map + (blink_visible ? BLINK_ROW : BLINK_ROW + 1) * DEVICE_SCREEN_WIDTH + BLINK_COL;
    set_bkg_based_tiles(BLINK_COL, BLINK_ROW, BLINK_WIDTH, 1, row, TILE_FULLSCREEN_FIRST);
}

void title_update(void) {
    blink_tick();
    if (input_pressed & J_START)
        state = STATE_PLAY_INIT;
}
