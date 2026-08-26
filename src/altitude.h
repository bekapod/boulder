#ifndef ALTITUDE_H
#define ALTITUDE_H

#include <stdint.h>

extern uint16_t altitude;

void altitude_init(void);
void altitude_add(uint16_t amount);
void altitude_sub(uint16_t amount);
void altitude_flush(void);

#endif
