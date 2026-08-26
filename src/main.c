#include <gbdk/platform.h>

#include "main.h"
#include "play.h"
#include "sfx.h"
#include "title.h"

uint8_t state = STATE_TITLE_INIT;
uint8_t input_pressed;

static uint8_t input_held;

void main(void) {
    BGP_REG = 0xE4;  // background palette -> 11100100 -> lightest to darkest
    OBP0_REG = 0xE4; // sprite palette 0 -> ''
    OBP1_REG = 0x1B; // sprite palette 1 -> 00011011 -> darkest to lightest

    sfx_init();
    add_VBL(sfx_tick);

    while (1) {
        vsync();

        // per-state vblank work (tilemap flushes), still inside
        // the vblank window
        switch (state) {
        case STATE_TITLE:
            title_vblank();
            break;
        }

        uint8_t held = joypad();
        // joypad() gives held with a 1 per button currently down
        // here we want "newly pressed", down now but not down in the
        // last frame. ~input_held is a mask over every button that was
        // up, AND-ing selects buttons satisfying both
        // a held button appears in input_pressed for one frame (when it was
        // newly pressed)
        input_pressed = held & ~input_held;
        input_held = held;

        switch (state) {
        case STATE_TITLE_INIT:
            title_init();
            break;
        case STATE_TITLE:
            title_update();
            break;
        case STATE_PLAY_INIT:
            play_init();
            break;
        case STATE_PLAY:
            play_update();
            break;
        case STATE_GAMEOVER_INIT:
            state = STATE_GAMEOVER;
            break;
        case STATE_GAMEOVER:
            break;
        case STATE_TUMBLE_INIT:
            state = STATE_TUMBLE;
            break;
        }
    }
}
