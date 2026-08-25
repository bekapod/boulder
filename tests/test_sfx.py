import pytest

from helpers import (
    SWEET_HI,
    SWEET_LO,
    enter_play,
    miss_once,
    screen_pos,
    tap_a,
    tick_until,
)

NR21, NR22 = 0xFF16, 0xFF17
NR42, NR43 = 0xFF21, 0xFF22
NR50, NR51, NR52 = 0xFF24, 0xFF25, 0xFF26

CHIME_ENV, CHIME_DUTY_READ = 0x91, 0x3F
THUD_ENV, THUD_POLY = 0xC2, 0x64


def apu(gb, addr):
    return gb.pyboy.memory[addr]


@pytest.mark.c_ready
def test_apu_powered_on_at_boot(gb):
    assert apu(gb, NR52) & 0x80
    assert apu(gb, NR50) == 0x77
    assert apu(gb, NR51) == 0xAA


def test_hit_plays_chime_on_ch2(gb, states):
    enter_play(gb, states)
    tick_until(gb, lambda: SWEET_LO <= screen_pos(gb) <= SWEET_HI, 200, "sweet spot")
    tap_a(gb)
    gb.tick(8)  # past the second chime note (fires 4 frames in)
    assert apu(gb, NR22) == CHIME_ENV
    assert apu(gb, NR21) == CHIME_DUTY_READ
    assert apu(gb, NR52) & 0x02  # CH2 is audibly sounding


def test_miss_plays_thud_on_ch4(gb, states):
    enter_play(gb, states)
    miss_once(gb)
    assert apu(gb, NR42) == THUD_ENV
    assert apu(gb, NR43) == THUD_POLY
    assert apu(gb, NR52) & 0x08  # CH4 is audibly sounding


def test_idle_slip_is_silent(gb, states, tuning):
    """slip is not a miss: a deduction happens with no channel sounding."""
    enter_play(gb, states)
    gb.set16("wAltitude", 100)
    tick_until(gb, lambda: gb.read16("wAltitude") < 100, 35, "first slip tick")
    assert apu(gb, NR52) & 0x0F == 0
