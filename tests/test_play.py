from helpers import (
    SWEET_HI,
    SWEET_LO,
    enter_play,
    miss_once,
    next_sweep,
    parse_rgbinc,
    progress,
    screen_pos,
    tap_a,
    tick_until,
)

_TILES = parse_rgbinc("tiles.rgbinc")
DIGITS = _TILES["ALTITUDE_MAP_ADDR"]
TILE_DIGIT_FIRST = _TILES["TILE_DIGIT_FIRST"]
TILE_LETTER_M = _TILES["TILE_LETTER_M"]
BLANK = 0


def digit_cells(gb):
    return [gb.pyboy.memory[DIGITS + i] for i in range(3)]


def expected_cells(altitude):
    """The three tile indices the screen should show for this altitude."""
    altitude = min(altitude, 999)
    hundreds, rest = divmod(altitude, 100)
    tens, ones = divmod(rest, 10)

    return [
        BLANK if hundreds == 0 else TILE_DIGIT_FIRST + hundreds,
        BLANK if hundreds == 0 and tens == 0 else TILE_DIGIT_FIRST + tens,
        TILE_DIGIT_FIRST + ones,
    ]


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
    """altitude/MISS_PENALTY_DIV lost per miss, floor-rounded; third
    strike -> GAMEOVER, 0m."""
    enter_play(gb, states)
    gb.set16("wAltitude", 47)

    miss_once(gb)
    assert gb.read16("wAltitude") == 47 - 47 // tuning["MISS_PENALTY_DIV"]
    assert gb.read("wMissStreak") == 1

    for strike in (2, 3):
        next_sweep(gb)
        miss_once(gb)
        if strike < tuning["MISS_LIMIT"]:
            assert gb.read("wMissStreak") == strike
            assert gb.state == states["STATE_PLAY"]

    assert gb.state == states["STATE_TUMBLE"]

    final = gb.read16("wAltitude")
    tap_a(gb)
    tap_a(gb)
    tap_a(gb)
    assert final == gb.read16("wAltitude")

    tick_until(
        gb,
        lambda: gb.state == states["STATE_GAMEOVER"],
        tuning["TUMBLE_FRAMES"] + 8,
        "game over",
    )
    assert 0 < final < 47  # penalties + slip bled it, but it wasn't zeroed
    assert digit_cells(gb) == expected_cells(final)

    # replaying resets it
    gb.tick(1)
    gb.press("start")
    assert gb.state == states["STATE_PLAY"]
    assert gb.read16("wAltitude") == 0
    assert digit_cells(gb) == expected_cells(0)


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
    SPOT = (
        _TILES["_SCRN0"]
        + _TILES["BAR_TILE_ROW"] * 32
        + _TILES["BAR_TILE_COL"]
        + _TILES["FLASH_TILE_OFFSET"]
    )

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


def test_altitude_display_tracks_memory(gb, states):
    """set wAltitude to a value and check the screen shows the right digits."""
    enter_play(gb, states)
    assert digit_cells(gb) == expected_cells(0)
    assert gb.pyboy.memory[DIGITS + 3] == TILE_LETTER_M

    for setted in (8, 100, 247, 5000):
        gb.set16("wAltitude", setted)
        tick_until(
            gb, lambda: gb.read16("wAltitude") == setted - 1, 40, "slip republish"
        )
        gb.tick(2)  # the dirty flag raised mid-frame delivers at the next vblank
        assert digit_cells(gb) == expected_cells(setted - 1)
