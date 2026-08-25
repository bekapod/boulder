#include <gbdk/platform.h>
#include <stdint.h>

#include "sfx.h"

// script terminator, goes where a row's delay byte would be
// real delays must stay below 0xFF
#define SFX_END 0xFF
#define SFX_TRIGGER 0x80 // bit 7 of NRx4 - (re)trigger sound effect

// register low bytes - rows store one byte, the player adds 0xFF00
#define NR21 0x16
#define NR22 0x17
#define NR23 0x18
#define NR24 0x19
#define NR42 0x21
#define NR43 0x22
#define NR44 0x23

typedef struct {
    uint8_t delay; // frames to wait before this row fires
    uint8_t reg;   // low byte of the target register
    uint8_t value; // value to write to the register
} sfx_row_t;

// what fraction of each wave is "on"
#define DUTY_12_5 0x00 // a blip rather than a hum

// envelope: start volume 0-15, fade speed 1 (fast) - 7 (slow)
#define ENV(vol, fade) (((vol) << 4) | (fade))

// noise pitch: shift 0-13 (each +1 = deeper), div 0-7 fine-tunes
// (bit 3 always 0: long randomness pattern, a hiss rather than a buzz)
#define NOISE(shift, div) (((shift) << 4) | (div))

// pulse pitch: 11 bits, bigger = higher note. low 8 go in NR23,
// top 3 go in NE24 trigger write
#define PITCH_LO(p) ((p) & 0xFF)
#define PITCH_HI(p) ((p) >> 8)

// chime five-note clumb, each +0x40 = one step up
#define CHIME_NOTE_1 0x4AC
#define CHIME_NOTE_2 0x4EC
#define CHIME_NOTE_3 0x52C
#define CHIME_NOTE_4 0x56C
#define CHIME_NOTE_5 0x5AC

// hit chime: stuttered slide up - one step every 3 frames
// each step restarts at full loudness while the last is fading
static const sfx_row_t chime_script[] = {
    {0, NR21, DUTY_12_5},
    {0, NR22, ENV(9, 1)},
    {0, NR23, PITCH_LO(CHIME_NOTE_1)},
    {0, NR24, SFX_TRIGGER | PITCH_HI(CHIME_NOTE_1)},
    {3, NR23, PITCH_LO(CHIME_NOTE_2)},
    {0, NR24, SFX_TRIGGER | PITCH_HI(CHIME_NOTE_2)},
    {3, NR23, PITCH_LO(CHIME_NOTE_3)},
    {0, NR24, SFX_TRIGGER | PITCH_HI(CHIME_NOTE_3)},
    {3, NR23, PITCH_LO(CHIME_NOTE_4)},
    {0, NR24, SFX_TRIGGER | PITCH_HI(CHIME_NOTE_4)},
    {3, NR23, PITCH_LO(CHIME_NOTE_5)},
    {0, NR24, SFX_TRIGGER | PITCH_HI(CHIME_NOTE_5)},
    {SFX_END},
};

// miss thud: short low noise burst
static const sfx_row_t thud_script[] = {
    {0, NR42, ENV(12, 2)},
    {0, NR43, NOISE(6, 4)},
    {0, NR44, SFX_TRIGGER},
    {SFX_END},
};

// third-miss rumble: impact, then the boulder rumbles away down the hill
// each burst is quieter and deeper than the one before
static const sfx_row_t rumble_script[] = {
    {0, NR42, ENV(13, 3)}, // the impact, slow fade
    {0, NR43, NOISE(6, 4)},
    {0, NR44, SFX_TRIGGER},
    {12, NR42, ENV(11, 3)},
    {0, NR43, NOISE(6, 5)},
    {0, NR44, SFX_TRIGGER},
    {12, NR42, ENV(9, 3)},
    {0, NR43, NOISE(7, 4)}, // shift up: noticeably deeper
    {0, NR44, SFX_TRIGGER},
    {12, NR42, ENV(7, 3)},
    {0, NR43, NOISE(7, 5)},
    {0, NR44, SFX_TRIGGER},
    {12, NR42, ENV(5, 3)},
    {0, NR43, NOISE(8, 4)}, // deeper still: felt more than heard
    {0, NR44, SFX_TRIGGER},
    {12, NR42, ENV(3, 3)},
    {0, NR43, NOISE(8, 5)},
    {0, NR44, SFX_TRIGGER},
    {SFX_END},
};

// per-channel cursor into the running effect script
typedef struct {
    const sfx_row_t *ptr; // next unexecuted row, NULL = idle
    uint8_t delay;        // frames left to wait before the next row
} sfx_ch_t;

static sfx_ch_t ch2, ch4;

// effect id -> which script on which channel
static const struct {
    const sfx_row_t *script;
    sfx_ch_t *ch;
} sfx_table[] = {
    {chime_script, &ch2},  // SFX_CHIME
    {thud_script, &ch4},   // SFX_THUD
    {rumble_script, &ch4}, // SFX_RUMBLE
};

// one-time APU power-on. must run before any other NR write
// while NR52's power bit is off, the APU ignores all writes
void sfx_init(void) {
    NR52_REG = 0x80; // power on
    NR50_REG = 0x77; // master volume: max on both speakers
    NR51_REG = 0xAA; // route ch2 + ch4 to both speakers
    ch2.ptr = NULL;
    ch4.ptr = NULL;
}

// start an effect, id = SFX_*. overwrites the channel's cursor so
// re-triggering mid-effect restarts it, safe to call any frame.
// the VBL tick must not fire between these two writes and
// see the new ptr with the old delay
void sfx_play(uint8_t id) {
    sfx_ch_t *ch = sfx_table[id].ch;
    CRITICAL {
        ch->ptr = sfx_table[id].script;
        ch->delay = ch->ptr->delay;
    }
}

// advance one channel's running effect by one frame
static void tick_channel(sfx_ch_t *ch) {
    if (ch->ptr == NULL)
        return; // idle

    if (ch->delay) {
        ch->delay--;
        return;
    }

    for (;;) {
        *(volatile uint8_t *)(0xFF00 + ch->ptr->reg) = ch->ptr->value;
        ch->ptr++;

        if (ch->ptr->delay == SFX_END) {
            ch->ptr = NULL; // done
            return;
        }

        ch->delay = ch->ptr->delay;

        if (ch->delay) {
            return;
        }
    }
}

void sfx_tick(void) {
    tick_channel(&ch2);
    tick_channel(&ch4);
}
