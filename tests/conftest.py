"""Shared PyBoy harness for the boulder ROM.

The vocabulary for every test: boot the ROM headless, poke/press,
tick N frames, assert against WRAM by symbol name (from boulder.sym).
Any symbol a test reads must be `export`ed in the rgbasm source.
"""

import pytest
from pyboy import PyBoy

import helpers
import rom_adapter

ROOT = helpers.ROOT
ROM = helpers.ROM
SYM = helpers.SYM


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
        self.tick(helpers.SETTLE_FRAMES)

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
        return self.read(rom_adapter.symbol("state"))


@pytest.fixture(scope="session")
def states() -> dict[str, int]:
    return rom_adapter.states()


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
        sound_emulated=True,
        no_input=True,
    )
    harness = Harness(pyboy)
    helpers.wait_for_boot(pyboy)
    yield harness
    pyboy.stop(save=False)
