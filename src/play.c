#include <gbdk/platform.h>

#include "../res/bar_bg.h"
#include "../res/marker_obj.h"
#include "../res/scene_map.h"
#include "../res/tileset.h"

#include "main.h"
#include "play.h"
#include "tiles.h"
#include "tuning.h"

#define MARKER_TIP (marker_obj_WIDTH / 2)
#define MARKER_OAM_X_BASE (BAR_TILE_COL * 8 + BAR_BORDER_PX + 8 - MARKER_TIP)
#define MARKER_OAM_Y (uint8_t)(BAR_TILE_ROW * 8 + 5 + 16) // 5 = 8px row - 3px overlap into the bar
#define OAM_IDX_MARKER 0

uint8_t marker_dir;
uint16_t marker_pos;
uint8_t marker_screen_pos;
uint8_t marker_pause;
uint8_t cycle_frames;
uint16_t altitude;
uint16_t marker_step;

static void recompute_cycle(void) {
    uint16_t q = altitude / METRES_PER_SPEEDUP;

    if (q > CYCLE_FRAMES - MARKER_CYCLE_MIN) {
        q = CYCLE_FRAMES - MARKER_CYCLE_MIN;
    }

    cycle_frames = CYCLE_FRAMES - q;

    marker_step = (BAR_INNER_WIDTH * 256u + cycle_frames - 1) / cycle_frames;
}

void play_init(void) {
    DISPLAY_OFF;
    LCDC_REG |= LCDCF_BG8000;

    set_bkg_data(TILE_BAR_FIRST, bar_bg_TILE_COUNT, bar_bg_tiles);
    set_bkg_data(TILE_SCENE_FIRST, tileset_TILE_COUNT, tileset_tiles);

    set_sprite_data(TILE_MARKER, marker_obj_TILE_COUNT, marker_obj_tiles);

    set_bkg_based_tiles(0, 0, DEVICE_SCREEN_WIDTH, DEVICE_SCREEN_HEIGHT, scene_map_map,
                        TILE_SCENE_FIRST);

    // sad. we use two counters here because if we derive x and tile from
    // the same counter the compiler (SDCC 4.x) creates a bug and the bar appears too
    // far to the right ;_;
    uint8_t tile = TILE_BAR_FIRST;
    for (uint8_t x = BAR_TILE_COL; x < BAR_TILE_COL + BAR_WIDTH_TILES; x++) {
        set_bkg_tile_xy(x, BAR_TILE_ROW, tile);
        tile++;
    }

    set_sprite_tile(OAM_IDX_MARKER, TILE_MARKER);
    move_sprite(OAM_IDX_MARKER, MARKER_OAM_X_BASE, MARKER_OAM_Y);

    marker_dir = 0;
    marker_pos = 0;
    marker_screen_pos = 0;
    marker_pause = 0;

    recompute_cycle();

    LCDC_REG = LCDCF_ON | LCDCF_BG8000 | LCDCF_OBJ8 | LCDCF_OBJON | LCDCF_BGON;
    state = STATE_PLAY;
}

void sweep_ended(void) {
    marker_pos = 0;
    recompute_cycle();
    marker_dir ^= 1;
    marker_pause = MARKER_PAUSE_FRAMES;
}

static void move_marker(void) {
    if (marker_pause) {
        marker_pause--;
        return;
    }

    marker_pos += marker_step;

    if (marker_pos >> 8 >= BAR_INNER_WIDTH) {
        sweep_ended();
    }
}

static void render_marker(void) {
    marker_screen_pos = (marker_pos + 128) >> 8;

    if (marker_dir == 1) {
        marker_screen_pos = BAR_INNER_WIDTH - marker_screen_pos;
    }

    move_sprite(OAM_IDX_MARKER, MARKER_OAM_X_BASE + marker_screen_pos, MARKER_OAM_Y);
}

void play_update(void) {
    move_marker();
    render_marker();
}
