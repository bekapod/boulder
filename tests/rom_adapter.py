import os
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DIALECT = os.environ.get("BOULDER_ROM") or "asm"

ROM = ROOT / "build" / ("boulder-c.gb" if DIALECT == "c" else "boulder.gb")
SYM = ROM.with_suffix(".sym")

RENAMES = {
    "title_update": "Title_Update",
    "state": "wStateId",
}


def symbol(name: str) -> str:
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
