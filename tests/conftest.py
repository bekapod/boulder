"""Shared PyBoy harness for the boulder ROM.

The vocabulary for every test: boot the ROM headless, poke/press,
tick N frames, assert against WRAM by symbol name (from boulder.sym).
Any symbol a test reads must be `export`ed in the rgbasm source.
"""

import re
from pathlib import Path

import helpers
import pytest
from pyboy import PyBoy

ROOT = Path(__file__).resolve().parent.parent
ROM = ROOT / "boulder.gb"
SYM = ROOT / "boulder.sym"

# Upper bound on boot ROM (~70 frames) + our init before we call the ROM broken.
BOOT_CAP_FRAMES = 600

# Frames to run after an input so the update + the new state's init
# have both executed.
SETTLE_FRAMES = 4


class Harness:
    """Thin wrapper: symbol-addressed memory access + frame-timed input."""

    def __init__(self, pyboy: PyBoy):
        self.pyboy = pyboy

    def read(self, symbol: str) -> int:
        """Read one byte of WRAM by its exported symbol name."""
        return self.pyboy.memory[self.pyboy.symbol_lookup(symbol)]

    def tick(self, frames: int = 1) -> bool:
        """Advance emulation; False means the emulator has stopped."""
        return self.pyboy.tick(frames, render=False)

    def press(self, button: str) -> None:
        """Tap a button for one frame and let the game react."""
        self.pyboy.button(button)
        self.tick(SETTLE_FRAMES)

    def read16(self, symbol: str) -> int:
        """Read a little-endian 16-bit WRAM value by symbol name."""
        a = self.pyboy.symbol_lookup(symbol)[1]
        return self.pyboy.memory[a] | (self.pyboy.memory[a + 1] << 8)

    def set16(self, symbol: str, value: int) -> None:
        a = self.pyboy.symbol_lookup(symbol)[1]
        self.pyboy.memory[a] = value & 0xFF
        self.pyboy.memory[a + 1] = value >> 8

    @property
    def state(self) -> int:
        return self.read("wStateId")


@pytest.fixture(scope="session")
def states() -> dict[str, int]:
    """STATE_* ids parsed from utils.rgbinc (equ constants aren't in the .sym)."""
    src = (ROOT / "utils.rgbinc").read_text()
    found = {
        m[0]: int(m[1]) for m in re.findall(r"(?m)^def (STATE_\w+) equ (\d+)", src)
    }
    assert found, "no STATE_* constants found in utils.rgbinc"
    return found


@pytest.fixture(scope="session")
def tuning() -> dict[str, int]:
    """Gameplay-feel constants parsed from tuning.rgbinc (see helpers.tuning)."""
    return helpers.tuning()


@pytest.fixture
def gb():
    if not ROM.exists():
        pytest.fail(
            f"{ROM.name} not found — build it first (run `make test` from the repo root)"
        )
    pyboy = PyBoy(
        str(ROM),
        window="null",
        symbols=str(SYM),
        sound_emulated=False,
        no_input=True,
    )
    harness = Harness(pyboy)
    _wait_for_boot(harness)
    yield harness
    pyboy.stop(save=False)


def _wait_for_boot(harness: Harness) -> None:
    """Tick past PyBoy's ~70-frame boot ROM until Title_Update executes,
    proving init is done and input polling has started."""
    pyboy = harness.pyboy
    booted = []
    pyboy.hook_register(None, "Title_Update", lambda _: booted.append(True), None)
    for _ in range(BOOT_CAP_FRAMES):
        harness.tick(1)
        if booted:
            pyboy.hook_deregister(None, "Title_Update")
            return
    pytest.fail(f"ROM did not reach the main loop within {BOOT_CAP_FRAMES} frames")
