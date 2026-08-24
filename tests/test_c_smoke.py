import pytest

pytestmark = pytest.mark.c_ready


def test_rom_reaches_main_loop(gb):
    assert gb.tick(1)
