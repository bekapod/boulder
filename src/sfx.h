#ifndef SFX_H
#define SFX_H

#include <stdint.h>

#define SFX_CHIME 0
#define SFX_THUD 1
#define SFX_RUMBLE 2

void sfx_init(void);
void sfx_play(uint8_t id);
void sfx_tick(void);

#endif
