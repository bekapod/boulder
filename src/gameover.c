#include <gbdk/platform.h>
#include <string.h>

#include "../res/gameover.h"

#include "altitude.h"
#include "blink.h"
#include "gameover.h"
#include "main.h"
#include "tiles.h"

#define SPRITE_PITCH 6

uint16_t best;
static uint8_t new_best;

static uint8_t draw_text_sprites(uint8_t oam_slot_index, uint8_t x, uint8_t y, char text[]) {
    for (uint8_t i = 0; text[i] != '\0'; i++) {
        uint8_t tile = 0;

        if (text[i] >= 'A' && text[i] <= 'Z') {
            tile = TILE_FONT_FIRST + (text[i] - 'A');
        }

        if (text[i] == '!') {
            tile = TILE_EXCLAIM;
        }

        set_sprite_tile(oam_slot_index + i, tile);
        move_sprite(oam_slot_index + i, x + i * SPRITE_PITCH, y);
    }

    return oam_slot_index + strlen(text);
}

static void draw_digits(uint8_t oam_slot_index, uint16_t value) {
    if (value > 999) {
        value = 999;
    }

    uint8_t hundreds = value / 100;
    uint8_t tens = (value / 10) % 10;
    uint8_t ones = value % 10;

    if (hundreds == 0 && tens == 0) {
        tens = 0;
    } else {
        tens = TILE_DIGIT_FIRST + tens;
    }

    if (hundreds == 0) {
        hundreds = 0;
    } else {
        hundreds = TILE_DIGIT_FIRST + hundreds;
    }

    ones = TILE_DIGIT_FIRST + ones;

    set_sprite_tile(oam_slot_index, hundreds);
    set_sprite_tile(oam_slot_index + 1, tens);
    set_sprite_tile(oam_slot_index + 2, ones);
}

void gameover_init(void) {
    DISPLAY_OFF;
    LCDC_REG |= LCDCF_BG8000;

    set_bkg_data(TILE_FULLSCREEN_FIRST, gameover_TILE_COUNT, gameover_tiles);
    set_bkg_based_tiles(0, 0, DEVICE_SCREEN_WIDTH, DEVICE_SCREEN_HEIGHT, gameover_map,
                        TILE_FULLSCREEN_FIRST);

    if (altitude > best) {
        best = altitude;
        new_best = 1;
    } else {
        new_best = 0;
    }

    blink_init();

    draw_text_sprites(0, 60, 62, "GAME OVER");
    draw_text_sprites(9, 49, 79, "RUN");
    draw_text_sprites(OAM_RUN_VALUE, 99, 79, "000M");
    draw_digits(OAM_RUN_VALUE, altitude);
    draw_text_sprites(16, 49, 89, "BEST");
    draw_text_sprites(OAM_BEST_VALUE, 99, 89, "000M");
    draw_digits(OAM_BEST_VALUE, best);
    draw_text_sprites(OAM_NEWBEST_FIRST, 60, new_best ? 106 : 0, "NEW BEST!");

    LCDC_REG = LCDCF_ON | LCDCF_BG8000 | LCDCF_OBJ8 | LCDCF_OBJON | LCDCF_BGON;
    state = STATE_GAMEOVER;
}

void gameover_update(void) {
    if (new_best) {
        blink_tick();

        if (blink_dirty) {
            blink_dirty = 0;
            for (uint8_t i = 0; i < 9; i++) {
                move_sprite(OAM_NEWBEST_FIRST + i, 60 + i * SPRITE_PITCH, blink_visible ? 106 : 0);
            }
        }
    }

    if (input_pressed & J_START) {
        state = STATE_PLAY_INIT;
    }
}
