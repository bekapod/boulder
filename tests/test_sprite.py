from helpers import (
    SWEET_HI,
    SWEET_LO,
    enter_play,
    miss_once,
    parse_rgbinc,
    screen_pos,
    tap_a,
    tick_until,
)

_TILES = parse_rgbinc("tiles.rgbinc")
BOULDER_IDLE_A = _TILES["TILE_BOULDER_FIRST"]
BOULDER_PUSH = BOULDER_IDLE_A + _TILES["ACTOR_FRAME_PUSH"]
BOULDER_IDLE_B = BOULDER_IDLE_A + _TILES["BOULDER_FRAME_ROLL"]
BOULDER_MISS = BOULDER_IDLE_A + _TILES["ACTOR_FRAME_MISS"]

OAM_BOULDER_Y = 0xFE04
OAM_BOULDER_X = 0xFE05
OAM_BOULDER_TILE = 0xFE06


def test_sprite_x_moves_in_play(gb):
    gb.press("start")
    x_before = gb.pyboy.memory[0xFE01]
    gb.tick(10)
    x_after = gb.pyboy.memory[0xFE01]
    assert x_after != x_before, "Sprite X position did not change during PLAY state"


def test_hit_pushes_then_settles_rolled(gb, states, tuning):
    """a hit swaps to the push frame + moves up-slope; the flash
    countdown snaps position home and advances the boulder to idle-B"""
    enter_play(gb, states)
    gb.tick(2)
    home_x = gb.pyboy.memory[OAM_BOULDER_X]
    assert gb.pyboy.memory[OAM_BOULDER_TILE] == BOULDER_IDLE_A

    tick_until(gb, lambda: SWEET_LO <= screen_pos(gb) <= SWEET_HI, 200, "sweet spot")
    tap_a(gb)
    assert gb.pyboy.memory[OAM_BOULDER_TILE] == BOULDER_PUSH
    assert gb.pyboy.memory[OAM_BOULDER_X] == home_x + 2

    tick_until(
        gb,
        lambda: gb.pyboy.memory[OAM_BOULDER_TILE] == BOULDER_IDLE_B,
        tuning["HIT_FREEZE_FRAMES"] + 4,
        "boulder settled",
    )
    assert gb.pyboy.memory[OAM_BOULDER_X] == home_x


def test_miss_rolls_back_then_settles(gb, states, tuning):
    """a miss swaps to the miss frame + moves down-slope; the flash
    countdown snaps position home and advances the boulder to idle-B"""
    enter_play(gb, states)
    gb.tick(2)
    home_x = gb.pyboy.memory[OAM_BOULDER_X]
    assert gb.pyboy.memory[OAM_BOULDER_TILE] == BOULDER_IDLE_A

    miss_once(gb)
    assert gb.pyboy.memory[OAM_BOULDER_TILE] == BOULDER_MISS
    assert gb.pyboy.memory[OAM_BOULDER_X] == home_x - 2

    tick_until(
        gb,
        lambda: gb.pyboy.memory[OAM_BOULDER_TILE] == BOULDER_IDLE_A,
        tuning["MISS_POSE_FRAMES"] + 4,
        "boulder settled",
    )
    assert gb.pyboy.memory[OAM_BOULDER_X] == home_x
