import pytest

import helpers
import rom_adapter

pytestmark = pytest.mark.c_ready


def test_rom_reaches_main_loop(gb):
    assert gb.tick(1)


def test_tuning_matches_asm():
    asm = helpers.parse_rgbinc("tuning.rgbinc")
    c = rom_adapter.parse_cdefs("tuning.h")
    shared = sorted(set(asm) & set(c))
    assert shared, "no shared tuning keys - parser broken?"
    drift = {k: (asm[k], c[k]) for k in shared if asm[k] != c[k]}
    assert not drift, f"tuning drift (asm, c): {drift}"
