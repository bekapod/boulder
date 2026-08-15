from helpers import (
    SWEET_HI,
    SWEET_LO,
    enter_play,
    miss_once,
    next_sweep,
    progress,
    screen_pos,
    tap_a,
    tick_until,
)


def test_perfect_press_rewards_and_forgives(gb, states, tuning):
    """hit at center -> altitude +10, streak back to 0."""
    enter_play(gb, states)
    miss_once(gb)
    assert gb.read("wMissStreak") == 1

    next_sweep(gb)
    tick_until(gb, lambda: SWEET_LO <= screen_pos(gb) <= SWEET_HI, 200, "sweet spot")
    before = gb.read16("wAltitude")
    tap_a(gb)
    assert gb.read16("wAltitude") == before + tuning["HIT_REWARD"]
    assert gb.read("wMissStreak") == 0


def test_three_misses_end_the_game(gb, states, tuning):
    """-20% floor-rounded per miss; third strike -> GAMEOVER, 0m."""
    enter_play(gb, states)
    gb.set16("wAltitude", 47)

    miss_once(gb)
    assert gb.read16("wAltitude") == 38
    assert gb.read("wMissStreak") == 1

    for strike in (2, 3):
        next_sweep(gb)
        miss_once(gb)
        if strike < tuning["MISS_LIMIT"]:
            assert gb.read("wMissStreak") == strike
            assert gb.state == states["STATE_PLAY"]

    assert gb.state == states["STATE_GAMEOVER"]
    assert gb.read16("wAltitude") == 0


def test_slip_bleeds_but_never_kills(gb, states, tuning):
    """idle costs 1m per 30 frames; at 0m nothing happens, ever."""
    enter_play(gb, states)

    # at bottom: no bleed, no strikes, still PLAY
    gb.tick(tuning["SLIP_FRAMES"] * 10)
    assert gb.read16("wAltitude") == 0
    assert gb.read("wMissStreak") == 0
    assert gb.state == states["STATE_PLAY"]

    # sync to the slip phase: raise altitude, run to the next deduction
    gb.set16("wAltitude", 100)
    tick_until(gb, lambda: gb.read16("wAltitude") < 100, 35, "first slip tick")
    assert gb.read16("wAltitude") == 99
    gb.tick(tuning["SLIP_FRAMES"])
    assert gb.read16("wAltitude") == 98
    gb.tick(tuning["SLIP_FRAMES"] * 3)
    assert gb.read16("wAltitude") == 95


def test_cycle_tracks_altitude_both_ways(gb, states, tuning):
    """250m -> cycle 50; back down -> re-lengthens; floor holds."""
    enter_play(gb, states)
    assert gb.read("wCycleFrames") == tuning["CYCLE_FRAMES"]

    gb.set16("wAltitude", 250)
    tick_until(
        gb,
        lambda: gb.read("wCycleFrames") != tuning["CYCLE_FRAMES"],
        200,
        "cycle recalc",
    )
    # the slip bleeds a few metres while the sweep finishes, so don't demand
    # exactly 50
    expected = (
        tuning["CYCLE_FRAMES"] - gb.read16("wAltitude") // tuning["METRES_PER_SPEEDUP"]
    )
    assert gb.read("wCycleFrames") == expected

    gb.set16("wAltitude", 0)  # losing height slows the bar
    tick_until(
        gb,
        lambda: gb.read("wCycleFrames") == tuning["CYCLE_FRAMES"],
        200,
        "cycle back to 60",
    )

    gb.set16("wAltitude", 5000)
    tick_until(
        gb,
        lambda: gb.read("wCycleFrames") == tuning["MARKER_CYCLE_MIN"],
        200,
        "cycle floor",
    )


def test_pause_presses_are_ignored(gb, states, tuning):
    """a press during the endpoint pause neither strikes or misses."""
    enter_play(gb, states)
    next_sweep(gb)  # returns the instant the direction flips: pause is counting
    assert gb.read("wMarkerPause") > 0
    tap_a(gb)
    assert gb.read("wMissStreak") == 0

    tick_until(gb, lambda: SWEET_LO <= screen_pos(gb) <= SWEET_HI, 200, "sweet spot")
    before = gb.read16("wAltitude")
    tap_a(gb)
    assert gb.read16("wAltitude") == before + tuning["HIT_REWARD"]


def test_hit_freezes_marker_and_flashes_spot(gb, states, tuning):
    """a hit halts the marker and darkens the spot, both for HIT_FREEZE_FRAMES."""
    SPOT = 0x9800 + 16 * 32 + 4  # tilemap: bar row, cells 4..6

    def cells():
        return [gb.pyboy.memory[SPOT + i] for i in range(3)]

    enter_play(gb, states)
    light = cells()  # capture "normal"

    tick_until(gb, lambda: SWEET_LO <= screen_pos(gb) <= SWEET_HI, 200, "sweet spot")
    tap_a(gb)
    assert gb.read("wMissStreak") == 0

    p = progress(gb)
    assert cells() != light  # flash is on
    gb.tick(tuning["HIT_FREEZE_FRAMES"] - 4)  # tap_a already spent ~2 frames
    assert progress(gb) == p  # still frozen
    assert cells() != light  # still dark

    gb.tick(8)  # freeze is over
    assert cells() == light
    assert progress(gb) != p  # marker is moving again
