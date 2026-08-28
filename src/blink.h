#ifndef BLINK_H
#define BLINK_H

#include <stdint.h>

#define BLINK_FRAMES 30

extern uint8_t blink_visible; // 0 or 1
extern uint8_t blink_dirty;   // 1 = the vblank hook should re-draw

void blink_init(void);
void blink_tick(void);

#endif
