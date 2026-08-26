"""Play-state test vocabulary: read the marker, time presses, force outcomes."""

import re
from functools import cache
from pathlib import Path

import pytest

import rom_adapter

ROOT = Path(__file__).resolve().parent.parent
ROM = rom_adapter.ROM
SYM = rom_adapter.SYM

# Upper bound on boot ROM (~70 frames) + our init before we call the ROM broken.
BOOT_CAP_FRAMES = 600

# Frames to run after an input so the update + the new state's init
# have both executed.
SETTLE_FRAMES = 8


def wait_for_boot(pyboy) -> None:
    """Tick past PyBoy's ~70-frame boot ROM until Title_Update executes,
    proving init is done and input polling has started."""
    booted = []
    rom_adapter.hook(pyboy, "title_update", lambda _: booted.append(True))
    for _ in range(BOOT_CAP_FRAMES):
        pyboy.tick(1, render=False)
        if booted:
            rom_adapter.unhook(pyboy, "title_update")
            return
    raise RuntimeError(
        f"ROM did not reach the main loop within {BOOT_CAP_FRAMES} frames"
    )


def parse_rgbinc(filename: str) -> dict[str, int]:
    """def NAME equ EXPR constants from an rgbinc, resolved top to bottom"""
    src = (ROOT / filename).read_text()
    found: dict[str, int] = {"_SCRN0": 0x9800}
    for name, expr in re.findall(r"(?m)^def (\w+) equ (.+?)\s*(?:;.*)?$", src):
        expr = re.sub(r"\$([0-9A-Fa-f]+)", r"0x\1", expr)  # rgbasm hex -> python hex
        # eval is safe here: input is our own repo's tuning.rgbinc, not
        # external data, and builtins are stripped. ast.literal_eval can't
        # be used because expressions reference earlier constants by name.
        try:
            found[name] = int(eval(expr, {"__builtins__": {}}, found))
        except NameError:
            continue
    assert found, "no constants found in tuning.rgbinc"
    return found


@cache
def tuning() -> dict[str, int]:
    return parse_rgbinc("tuning.rgbinc")


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
    return gb.pyboy.symbol_lookup(rom_adapter.symbol(symbol))[1]


def screen_pos(gb) -> int:
    return gb.read("marker_screen_pos")


def progress(gb) -> int:
    """Whole-pixel progress through the sweep, 0..64 whatever the direction.

    Stays at 0 for the whole endpoint pause, so progress >= 2 also proves the marker is moving (i.e. presses will be judged)."""

    return gb.pyboy.memory[addr(gb, "marker_pos") + 1]


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
    d = gb.read("marker_dir")
    tick_until(gb, lambda: gb.read("marker_dir") != d, SWEEP_CAP, "sweep end")


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
            break  # the third strike landed; PLAY is over
        next_sweep(gb)

    tick_until(
        gb,
        lambda: gb.state == states["STATE_GAMEOVER"],
        _T["TUMBLE_FRAMES"] + 8,
        "tumble to end",
    )
    gb.tick(1)
