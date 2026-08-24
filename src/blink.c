#include "blink.h"

#define BLINK_FRAMES 30

static uint8_t blink_frames;
uint8_t blink_visible;
uint8_t blink_dirty;

// start a blink cycle: visible, counting down, nothing to re-draw
void blink_init(void) {
    blink_frames = BLINK_FRAMES;
    blink_visible = 1;
    blink_dirty = 0;
}

// count down one frame. at zero, toggle visibility and mark dirty
void blink_tick(void) {
    if (--blink_frames)
        return;
    blink_frames = BLINK_FRAMES;
    blink_visible ^= 1;
    blink_dirty = 1;
}
