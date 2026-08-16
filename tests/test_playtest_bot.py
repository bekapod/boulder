import random

import helpers
import playtest_bot as bot
from playtest_bot import marker_track, plan_press

T = helpers.tuning()
BAR = T["BAR_INNER_WIDTH"]
SWEET_LO = T["SWEET_SPOT_MIN"]
SWEET_HI = T["SWEET_SPOT_MAX"]


def test_track_covers_the_bar_at_start_cycle():
    track = marker_track(T["CYCLE_FRAMES"], direction=0)
    assert track == sorted(track)
    assert track[0] <= 2, "first frame should be near the left edge"
    assert track[-1] >= BAR - 2, "last judged frame should be near the right edge"


def test_track_mirrors_by_direction():
    right = marker_track(T["CYCLE_FRAMES"], direction=0)
    left = marker_track(T["CYCLE_FRAMES"], direction=1)
    assert left == [BAR - p for p in right]


def test_track_at_cycle_floor_is_16px_steps():
    assert marker_track(T["MARKER_CYCLE_MIN"], direction=0) == [16, 32, 48]


def test_plan_press_hits_the_window_at_every_cycle():
    unhittable = []
    for cycle in range(T["MARKER_CYCLE_MIN"], T["CYCLE_FRAMES"] + 1):
        for direction in (0, 1):
            track = marker_track(cycle, direction)
            n = plan_press(cycle, direction)
            planned = track[n - 1]
            if any(SWEET_LO <= p <= SWEET_HI for p in track):
                assert SWEET_LO <= planned <= SWEET_HI, (
                    f"cycle {cycle} dir {direction}: planned px {planned} "
                    f"outside {SWEET_LO}..{SWEET_HI}"
                )
            else:
                unhittable.append((cycle, direction))
    assert unhittable == [], f"no hittable frame at: {unhittable}"


def test_marker_track_matches_emulator(gb, states, tuning):
    gb.press("start")
    assert gb.state == states["STATE_PLAY"]
    a_pos = gb.pyboy.symbol_lookup("wMarkerPos")[1]

    d0 = gb.read("wMarkerDir")
    helpers.tick_until(
        gb, lambda: gb.read("wMarkerDir") != d0, helpers.SWEEP_CAP, "sweep end"
    )
    direction = gb.read("wMarkerDir")
    cycle = gb.read("wCycleFrames")
    track = marker_track(cycle, direction)

    observed = []
    for _ in range(cycle + tuning["MARKER_PAUSE_FRAMES"] + 4):
        gb.tick(1)
        raw = gb.pyboy.memory[a_pos] | (gb.pyboy.memory[a_pos + 1] << 8)
        if raw == 0:
            continue  # endpoint pause, or the reset after the sweep ends
        observed.append((raw, gb.read("wMarkerScreenPos")))
        if len(observed) == len(track):
            break

    inc = (BAR * 256 + cycle - 1) // cycle
    assert [r for r, _ in observed] == [k * inc for k in range(1, len(track) + 1)]
    assert [s for _, s in observed] == track


def test_sigma_zero_bot_only_hits(gb, states):
    gb.press("start")
    assert gb.state == states["STATE_PLAY"]
    stats = bot.play_run(gb.pyboy, sigma=0.0, rng=random.Random(1), max_frames=800)
    assert stats.misses == 0, f"perfect bot missed: {stats}"
    assert stats.hits >= 5, f"too few hits in 800 frames: {stats}"
    ceiling = stats.hits * T["HIT_REWARD"]
    floor = ceiling - stats.frames // T["SLIP_FRAMES"]
    assert floor <= stats.death_altitude <= ceiling, stats
