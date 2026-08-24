#include <gbdk/platform.h>

#include "main.h"

uint8_t state = STATE_TITLE_INIT;

void title_update(void) {}

void main(void) {
    while (1) {
        vsync();
        switch (state) {
        case STATE_TITLE_INIT:
            state = STATE_TITLE;
            break;
        case STATE_TITLE:
            title_update();
            break;
        case STATE_PLAY_INIT:
            state = STATE_PLAY;
            break;
        case STATE_PLAY:
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
