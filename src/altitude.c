#include <gbdk/platform.h>
#include <stdint.h>

#include "altitude.h"
#include "tiles.h"

uint16_t altitude;

static uint8_t digits[3];
static uint8_t dirty;

static void update_display(void) {
    uint16_t value = altitude;

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

    digits[0] = hundreds;
    digits[1] = tens;
    digits[2] = ones;
    dirty = 1;
}

void altitude_add(uint16_t amount) {
    altitude += amount;
    update_display();
}

void altitude_sub(uint16_t amount) {
    if (altitude < amount) {
        altitude = 0;
    } else {
        altitude -= amount;
    }
    update_display();
}

void altitude_init(void) {
    altitude = 0;
    set_bkg_tile_xy(ALTITUDE_TILE_COL + 3, ALTITUDE_TILE_ROW, TILE_LETTER_M);
    update_display();
}

void altitude_flush(void) {
    if (dirty == 0) {
        return;
    }

    // same as what set_bkg_tiles does but without any extra overhead we don't need here. that makes
    // it faster to run in the v. short vblank window
    uint8_t *dst = (uint8_t *)(0x9800 + ALTITUDE_TILE_ROW * 32 + ALTITUDE_TILE_COL);
    dst[0] = digits[0];
    dst[1] = digits[1];
    dst[2] = digits[2];
    dirty = 0;
}
