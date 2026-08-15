"""Play-state test vocabulary: read the marker, time presses, force outcomes."""

import re
from functools import cache
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent


@cache
def tuning() -> dict[str, int]:
    """Gameplay-feel constants parsed from tuning.rgbinc.

    Values may be expressions over earlier constants, so evaluate each
    line with everything parsed so far in scope (the same top-to-bottom
    resolution the assembler does)."""
    src = (ROOT / "tuning.rgbinc").read_text()
    found: dict[str, int] = {}
    for name, expr in re.findall(r"(?m)^def (\w+) equ (.+?)\s*(?:;.*)?$", src):
        # eval is safe here: input is our own repo's tuning.rgbinc, not
        # external data, and builtins are stripped. ast.literal_eval can't
        # be used because expressions reference earlier constants by name.
        found[name] = int(eval(expr, {"__builtins__": {}}, found))
    assert found, "no constants found in tuning.rgbinc"
    return found


_T = tuning()

BAR_INNER_WIDTH = _T["BAR_INNER_WIDTH"]

# Aim this many px inside the true sweet spot so one frame of timing
# jitter can't turn a "hit" test flaky.
SWEET_MARGIN = 4
SWEET_LO = _T["SWEET_SPOT_MIN"] + SWEET_MARGIN
SWEET_HI = _T["SWEET_SPOT_MAX"] - SWEET_MARGIN

SWEEP_CAP = (
    _T["CYCLE_FRAMES"] + _T["MARKER_PAUSE_FRAMES"] + _T["HIT_FREEZE_FRAMES"] + 16
)


def addr(gb, symbol: str) -> int:
    return gb.pyboy.symbol_lookup(symbol)[1]


def screen_pos(gb) -> int:
    pos = gb.pyboy.memory[addr(gb, "wMarkerPos") + 1]
    if gb.read("wMarkerDir"):
        pos = BAR_INNER_WIDTH - pos
    return pos


def progress(gb) -> int:
    """Whole-pixel progress through the sweep, 0..64 whatever the direction.

    Stays at 0 for the whole endpoint pause, so progress >= 2 also proves the marker is moving (i.e. presses will be judged)."""

    return gb.pyboy.memory[addr(gb, "wMarkerPos") + 1]


def tick_until(gb, cond, cap: int, what: str) -> None:
    for _ in range(cap):
        if cond():
            return
        gb.tick(1)
    pytest.fail(f"timeout ({cap} frames) waiting for {what}")


def enter_play(gb, states) -> None:
    gb.press("start")
    assert gb.state == states["STATE_PLAY"]


def next_sweep(gb) -> None:
    """Run until the endpoint flip that starts a fresh (unjudged) sweep."""
    d = gb.read("wMarkerDir")
    tick_until(gb, lambda: gb.read("wMarkerDir") != d, SWEEP_CAP, "sweep end")


def tap_a(gb) -> None:
    """Press A and give the judgment one frame to land."""
    gb.pyboy.button("a")
    gb.tick(2)


def miss_once(gb) -> None:
    """Press just after a turnaround: moving, but far from the sweet spot."""
    tick_until(gb, lambda: 2 <= progress(gb) <= 8, 200, "early sweep")
    tap_a(gb)


def force_game_over(gb, states) -> None:
    """Miss until the third strike lands."""
    for _ in range(3):
        miss_once(gb)
        if gb.state != states["STATE_PLAY"]:
            return  # the third strike landed; PLAY is over
        next_sweep(gb)
