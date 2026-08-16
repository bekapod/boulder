"""Difficulty-curve playtest bot — NOT part of the pytest correctness suite.

Usage:
    uv run --project tests python tests/playtest_bot.py \
        --sigma 1.5 --runs 50 --seed 1 --csv sweep.csv
"""

import argparse
import csv
import random
from dataclasses import dataclass, fields
from pathlib import Path

from pyboy import PyBoy

import helpers

ROOT = helpers.ROOT
ROM = helpers.ROM

_T = helpers.tuning()
BAR = _T["BAR_INNER_WIDTH"]
PAUSE = _T["MARKER_PAUSE_FRAMES"]
SWEET_LO = _T["SWEET_SPOT_MIN"]
SWEET_HI = _T["SWEET_SPOT_MAX"]
SWEET_CENTER = (SWEET_LO + SWEET_HI) / 2

_STATES = helpers.parse_rgbinc("utils.rgbinc")
STATE_PLAY = _STATES["STATE_PLAY"]
STATE_GAMEOVER = _STATES["STATE_GAMEOVER"]

DEFAULT_MAX_FRAMES = 20_000  # ~5.6 min of game time; sigma=0 never dies

# PADF_A from hardware.rgbinc; the pad struct is active-low, so a
# CLEARED bit in wInputPressed means "A was pressed this frame"
PADF_A = 0x01


def marker_track(cycle: int, direction: int) -> list[int]:
    """Screen px the game would judge a press against, per movement frame."""
    inc = (BAR * 256 + cycle - 1) // cycle
    pos, track = 0, []
    while True:
        pos += inc
        if pos >> 8 >= BAR:
            return track
        screen = (pos + 128) >> 8
        track.append(BAR - screen if direction else screen)


def plan_press(cycle: int, direction: int) -> int:
    """The movement frame (1-based) whose judged px is nearest the sweet-spot
    center. May still be a miss if no frame lands inside the window — that
    *is* the mechanical ceiling, so the perfect bot presses (and dies) there
    rather than politely declining."""
    track = marker_track(cycle, direction)
    best = min(range(len(track)), key=lambda i: abs(track[i] - SWEET_CENTER))
    return best + 1


@dataclass
class RunStats:
    death_altitude: int
    max_altitude: int
    presses: int
    hits: int
    misses: int
    ignored: int
    frames: int
    survived: bool


def play_run(
    pyboy: PyBoy,
    sigma: float,
    rng: random.Random,
    mu: float = 0.0,
    max_frames: int = DEFAULT_MAX_FRAMES,
) -> RunStats:
    """Drive one run from STATE_PLAY until game over (or max_frames).
    """
    mem = pyboy.memory
    a_state = pyboy.symbol_lookup("wStateId")[1]
    a_dir = pyboy.symbol_lookup("wMarkerDir")[1]
    a_alt = pyboy.symbol_lookup("wAltitude")[1]
    a_pressed = pyboy.symbol_lookup("wInputPressed")[1]

    def altitude() -> int:
        return mem[a_alt] | (mem[a_alt + 1] << 8)

    assert mem[a_state] == STATE_PLAY, "play_run expects STATE_PLAY"

    stats = RunStats(0, 0, 0, 0, 0, 0, 0, survived=False)
    judged = {"hit": 0, "miss": 0}
    clock = {"frame": 0, "press_at": None}

    def on_judge(_) -> None:
        clock["frame"] += 1
        if clock["frame"] == clock["press_at"]:
            clock["press_at"] = None
            stats.presses += 1
            mem[a_pressed] &= ~PADF_A & 0xFF  # active-low: clear = pressed

    def on_sweep_end(_) -> None:
        q = altitude() // _T["METRES_PER_SPEEDUP"]
        cycle = _T["CYCLE_FRAMES"] - min(q, _T["CYCLE_FRAMES"] - _T["MARKER_CYCLE_MIN"])
        n = plan_press(cycle, mem[a_dir] ^ 1)
        jitter = round(rng.gauss(mu, sigma))
        clock["press_at"] = max(
            clock["frame"] + 1 + PAUSE + n + jitter, clock["frame"] + 1
        )

    pyboy.hook_register(None, "JudgePress", on_judge, None)
    pyboy.hook_register(None, "MoveMarker.sweep_ended", on_sweep_end, None)
    pyboy.hook_register(
        None,
        "JudgePress.hit",
        lambda _: judged.__setitem__("hit", judged["hit"] + 1),
        None,
    )
    pyboy.hook_register(
        None,
        "JudgePress.miss",
        lambda _: judged.__setitem__("miss", judged["miss"] + 1),
        None,
    )
    frame = 0
    try:
        while frame < max_frames:
            if mem[a_state] == STATE_GAMEOVER:
                break
            pyboy.tick(1, render=False)
            frame += 1
            stats.max_altitude = max(stats.max_altitude, altitude())
        else:
            stats.survived = True
    finally:
        pyboy.hook_deregister(None, "JudgePress")
        pyboy.hook_deregister(None, "MoveMarker.sweep_ended")
        pyboy.hook_deregister(None, "JudgePress.hit")
        pyboy.hook_deregister(None, "JudgePress.miss")

    stats.hits = judged["hit"]
    stats.misses = judged["miss"]
    stats.ignored = stats.presses - stats.hits - stats.misses
    stats.frames = frame
    stats.death_altitude = altitude()
    return stats


def make_pyboy(rom: Path = ROM) -> PyBoy:
    return PyBoy(
        str(rom),
        window="null",
        symbols=str(rom.with_suffix(".sym")),
        sound_emulated=False,
        no_input=True,
    )


def start_run(pyboy: PyBoy) -> None:
    a_state = pyboy.symbol_lookup("wStateId")[1]
    a_fn = pyboy.symbol_lookup("wStateFn")[1]
    a_alt = pyboy.symbol_lookup("wAltitude")[1]
    play_init = pyboy.symbol_lookup("Play_Init")[1]
    pyboy.tick(2, render=False)
    pyboy.memory[a_fn] = play_init & 0xFF
    pyboy.memory[a_fn + 1] = play_init >> 8
    pyboy.tick(helpers.SETTLE_FRAMES, render=False)
    altitude = pyboy.memory[a_alt] | (pyboy.memory[a_alt + 1] << 8)
    assert pyboy.memory[a_state] == STATE_PLAY and altitude == 0, (
        "restart into play failed"
    )


CSV_FIELDS = ["sigma", "run", "seed"] + [f.name for f in fields(RunStats)]


def run_batch(
    pyboy: PyBoy,
    sigma: float,
    runs: int,
    seed: int,
    mu: float = 0.0,
    max_frames: int = DEFAULT_MAX_FRAMES,
) -> list[dict]:
    rows = []
    for run in range(runs):
        rng = random.Random(f"{seed}:{sigma}:{run}")  # str-seeded = stable
        start_run(pyboy)
        stats = play_run(pyboy, sigma, rng, mu=mu, max_frames=max_frames)
        rows.append({"sigma": sigma, "run": run, "seed": seed, **vars(stats)})
    return rows


def write_csv(path: Path, rows: list[dict], append: bool = False) -> None:
    new_file = not (append and path.exists() and path.stat().st_size > 0)
    with open(path, "a" if append else "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
        if new_file:
            writer.writeheader()
        writer.writerows(rows)


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--sigma", type=float, required=True, help="timing error, frames")
    ap.add_argument("--runs", type=int, default=50)
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--mu", type=float, default=0.0, help="mean press bias, frames")
    ap.add_argument("--max-frames", type=int, default=DEFAULT_MAX_FRAMES)
    ap.add_argument("--csv", type=Path, default=None, help="append rows here")
    ap.add_argument("--rom", type=Path, default=ROM)
    args = ap.parse_args(argv)

    pyboy = make_pyboy(args.rom)
    try:
        helpers.wait_for_boot(pyboy)
        rows = run_batch(
            pyboy,
            args.sigma,
            args.runs,
            args.seed,
            mu=args.mu,
            max_frames=args.max_frames,
        )
    finally:
        pyboy.stop(save=False)

    if args.csv:
        write_csv(args.csv, rows, append=True)
    for row in rows:
        print(row)


if __name__ == "__main__":
    main()
