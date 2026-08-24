#ifndef MAIN_H
#define MAIN_H

#include <stdint.h>

enum state_id {
    STATE_TITLE_INIT = 0,
    STATE_TITLE = 1,
    STATE_PLAY_INIT = 2,
    STATE_PLAY = 3,
    STATE_GAMEOVER_INIT = 4,
    STATE_GAMEOVER = 5,
    STATE_TUMBLE_INIT = 6,
    STATE_TUMBLE = 7,
};

extern uint8_t state;

#endif
