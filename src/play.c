#include <gbdk/platform.h>

#include "../res/bar_bg.h"
#include "../res/marker_obj.h"
#include "../res/scene_map.h"
#include "../res/tileset.h"

#include "altitude.h"
#include "main.h"
#include "play.h"
#include "sfx.h"
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
uint16_t marker_step;
uint8_t miss_streak;

static uint8_t press_used;
static uint8_t slip_counter;
static uint8_t flash_frames;
static uint8_t flash_pending;

static void recompute_cycle(void) {
    uint16_t q = altitude / METRES_PER_SPEEDUP;

    if (q > CYCLE_FRAMES - MARKER_CYCLE_MIN) {
        q = CYCLE_FRAMES - MARKER_CYCLE_MIN;
    }

    cycle_frames = CYCLE_FRAMES - q;

    marker_step = (BAR_INNER_WIDTH * 256u + cycle_frames - 1) / cycle_frames;
}

void play_init(void) {
#include "../res/digits_bg.h"

    DISPLAY_OFF;
    LCDC_REG |= LCDCF_BG8000;

    set_bkg_data(TILE_BAR_FIRST, bar_bg_TILE_COUNT, bar_bg_tiles);
    set_bkg_data(TILE_SCENE_FIRST, tileset_TILE_COUNT, tileset_tiles);
    set_bkg_data(TILE_DIGIT_FIRST, digits_bg_TILE_COUNT, digits_bg_tiles);

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
    miss_streak = 0;
    press_used = 0;
    slip_counter = 0;
    flash_frames = 0;
    flash_pending = 0;

    altitude_init();
    recompute_cycle();

    LCDC_REG = LCDCF_ON | LCDCF_BG8000 | LCDCF_OBJ8 | LCDCF_OBJON | LCDCF_BGON;
    state = STATE_PLAY;
}

// non-static so it appears in the .sym file: the pytest harness hooks
// this symbol
void sweep_ended(void) {
    marker_pos = 0;
    recompute_cycle();
    marker_dir ^= 1;
    marker_pause = MARKER_PAUSE_FRAMES;
    press_used = 0;
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

static void update_flash(void) {
    if (flash_frames == 0) {
        return;
    }

    flash_frames--;

    if (flash_frames == 0) {
        flash_pending = TILE_BAR_FIRST + FLASH_TILE_OFFSET;
    }
}

static void update_slip(void) {
    slip_counter++;

    if (slip_counter < SLIP_FRAMES) {
        return;
    }

    slip_counter = 0;

    if (altitude != 0) {
        altitude_sub(1);
    }
}

// the judge_* functions are non-static so they appears in the .sym file: the
// pytest harness hooks these symbols
void judge_hit(void) {
    miss_streak = 0;
    marker_pause = HIT_FREEZE_FRAMES;
    flash_frames = HIT_FREEZE_FRAMES;
    flash_pending = TILE_BAR_DARK_FIRST;
    sfx_play(SFX_CHIME);
    altitude_add(HIT_REWARD);
}

void judge_miss(void) {
    sfx_play(SFX_THUD);
    altitude_sub(altitude / MISS_PENALTY_DIV);
    marker_pause = MISS_FREEZE_FRAMES;
    miss_streak++;

    if (miss_streak < MISS_LIMIT) {
        return;
    }

    sfx_play(SFX_RUMBLE);
    state = STATE_TUMBLE_INIT;
}

void judge_press(void) {
    if (marker_pause) {
        return;
    }

    if (!(input_pressed & J_A)) { // only a newly pressed A counts
        return;
    }

    if (press_used) {
        return;
    }

    press_used = 1;

    if (marker_screen_pos >= SWEET_SPOT_MIN && marker_screen_pos <= SWEET_SPOT_MAX) {
        judge_hit();
    } else {
        judge_miss();
    }
}

void play_update(void) {
    update_flash();
    update_slip();
    move_marker();
    render_marker();
    judge_press();
}

void play_vblank(void) {
    altitude_flush();

    if (!flash_pending) {
        return;
    }

    for (uint8_t i = 0; i < FLASH_TILE_COUNT; i++) {
        set_bkg_tile_xy(BAR_TILE_COL + FLASH_TILE_OFFSET + i, BAR_TILE_ROW, flash_pending + i);
    }

    flash_pending = 0;
}
