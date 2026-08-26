import os
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DIALECT = os.environ.get("BOULDER_ROM") or "asm"

ROM = ROOT / "build" / ("boulder-c.gb" if DIALECT == "c" else "boulder.gb")
SYM = ROM.with_suffix(".sym")

RENAMES = {
    "title_update": "Title_Update",
    "play_init": "Play_Init",
    "state": "wStateId",
    "state_fn": "wStateFn",
    "best": "wBest",
    "marker_dir": "wMarkerDir",
    "marker_pos": "wMarkerPos",
    "marker_pause": "wMarkerPause",
    "marker_screen_pos": "wMarkerScreenPos",
    "altitude": "wAltitude",
    "shadow_OAM": "wShadowOAM",
    "miss_streak": "wMissStreak",
    "cycle_frames": "wCycleFrames",
    "input_pressed": "wInputPressed",
    "sweep_ended": "MoveMarker.sweep_ended",
    "judge_press": "JudgePress",
    "judge_hit": "JudgePress.hit",
    "judge_miss": "JudgePress.miss",
}


def symbol(name: str) -> str:
    assert name not in RENAMES.values(), f"use the portable name for {name!r}"
    if DIALECT == "c":
        return "_" + name
    return RENAMES.get(name, name)


def hook(pyboy, name: str, callback) -> None:
    bank, addr = pyboy.symbol_lookup(symbol(name))
    if addr >= 0x4000:
        bank = 1
    pyboy.hook_register(bank, addr, callback, None)


def unhook(pyboy, name: str) -> None:
    bank, addr = pyboy.symbol_lookup(symbol(name))
    pyboy.hook_deregister(1 if addr >= 0x4000 else bank, addr)


def states() -> dict[str, int]:
    if DIALECT == "c":
        src = (ROOT / "src" / "main.h").read_text()
        pattern = r"(?m)^\s*(STATE_\w+) = (\d+),"
    else:
        src = (ROOT / "utils.rgbinc").read_text()
        pattern = r"(?m)^def (STATE_\w+) equ (\d+)"
    found = {m[0]: int(m[1]) for m in re.findall(pattern, src)}
    assert found, f"No states found for dialect {DIALECT}"
    return found


def eval_defs(pairs, seed=None) -> dict[str, int]:
    """Resolve (name, expr) constants top to bottom, earlier names usable
    in later exprs. eval is safe here: input is our own repo's headers,
    not external data, and builtins are stripped. ast.literal_eval can't
    be used because expressions reference earlier constants by name.
    int() truncates toward zero, matching C division for the positive
    values tuning uses. An expr naming a constant from another file is
    skipped."""
    found: dict[str, int] = dict(seed or {})
    for name, expr in pairs:
        try:
            # safe: our own repo's headers, no builtins (see docstring)
            found[name] = int(eval(expr, {"__builtins__": {}}, found))
        except NameError:
            continue
    return found


def parse_cdefs(filename):
    """#define NAME EXPR constants from a header file"""
    src = (ROOT / "src" / filename).read_text()
    return eval_defs(re.findall(r"(?m)^#define (\w+) +(.+?)\s*(?:(?://|/\*).*)?$", src))
