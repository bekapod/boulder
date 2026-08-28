import itertools

import pytest

import helpers
import rom_adapter

MEASURED_SWEEPS = 5


def _hook_sweep_ends(gb) -> tuple[list[int], list[tuple[str, int]]]:
    clock = [0]
    ends: list[tuple[str, int]] = []
    dir_addr = helpers.addr(gb, "marker_dir")

    def on_end(_):
        # fires before the direction flip: 0 = was moving right, so just arrived at the right end
        side = "right" if gb.pyboy.memory[dir_addr] == 0 else "left"
        ends.append((side, clock[0]))

    rom_adapter.hook(gb.pyboy, "sweep_ended", on_end)

    return clock, ends


def _run(gb, clock: list[int], frames: int) -> None:
    for frame in range(frames):
        clock[0] = frame
        gb.tick(1)


def _periods(ends: list[tuple[str, int]]) -> list[int]:
    return [after - before for (_, before), (_, after) in itertools.pairwise(ends)]


def test_sweep_period_is_cycle_plus_pause(gb, tuning):
    period = tuning["CYCLE_FRAMES"] + tuning["MARKER_PAUSE_FRAMES"]

    gb.press("start")
    clock, ends = _hook_sweep_ends(gb)
    _run(gb, clock, (MEASURED_SWEEPS + 2) * period)

    assert len(ends) > MEASURED_SWEEPS, f"only {len(ends)} sweep-ends observed"

    sides = [side for side, _ in ends]
    assert sides[0] == "right", "first sweep should end at the right"
    assert all(a != b for a, b in itertools.pairwise(sides)), (
        f"ends did not alternate: {sides}"
    )

    periods = _periods(ends)
    assert all(p == period for p in periods), (
        f"sweep periods {periods} != {period} (CYCLE_FRAMES + MARKER_PAUSE_FRAMES)"
    )


def test_sweep_speed_follows_altitude(gb, tuning):
    fast_cycle = 10
    altitude = (tuning["CYCLE_FRAMES"] - fast_cycle + 1) * tuning[
        "METRES_PER_SPEEDUP"
    ] - 1
    fast_period = fast_cycle + tuning["MARKER_PAUSE_FRAMES"]
    slow_period = tuning["CYCLE_FRAMES"] + tuning["MARKER_PAUSE_FRAMES"]

    gb.press("start")
    gb.set16("altitude", altitude)

    clock, ends = _hook_sweep_ends(gb)
    _run(gb, clock, slow_period + (MEASURED_SWEEPS + 2) * fast_period)

    assert len(ends) > MEASURED_SWEEPS + 1, f"only {len(ends)} sweep-ends observed"

    periods = _periods(ends)[1:]
    assert all(p == fast_period for p in periods), (
        f"post-poke sweep periods {periods} != {fast_period}"
    )


def test_marker_position_stays_in_bounds(gb, tuning):
    gb.press("start")
    oam_addr = helpers.addr(gb, "shadow_OAM")
    oam_x = oam_addr + 1

    seen = set()
    for _ in range(3 * (tuning["CYCLE_FRAMES"] + tuning["MARKER_PAUSE_FRAMES"])):
        gb.tick(1)
        seen.add(gb.pyboy.memory[oam_x])

    span = max(seen) - min(seen)
    assert span == tuning["BAR_INNER_WIDTH"], (
        f"marker travel span {span} != bar width - overshoot or never reached both ends"
    )
