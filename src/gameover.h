#ifndef GAMEOVER_H
#define GAMEOVER_H

#include <stdint.h>

#define OAM_RUN_VALUE 12
#define OAM_BEST_VALUE 20
#define OAM_NEWBEST_FIRST 24

extern uint16_t best;

void gameover_init(void);
void gameover_update(void);

#endif
