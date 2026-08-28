"""State machine dispatch: TITLE -> PLAY -> GAMEOVER -> PLAY.

START advances TITLE and retries from GAMEOVER, and does nothing during PLAY
"""

import re

import pytest

from helpers import ROOT, force_game_over


def _parse_c_array(path, name):
    """Extract a uint8 C array from a png2asset-generated .c file."""
    src = path.read_text()
    m = re.search(rf"{name}\[\d+\]\s*=\s*\{{([^}}]+)\}}", src)
    assert m, f"{name} not found in {path}"
    return bytes(int(v, 0) for v in re.findall(r"0x[0-9a-fA-F]+|\d+", m.group(1)))


def test_rom_boots_without_crashing(gb):
    assert gb.tick(60), "emulator stopped during the first second of runtime"


def test_initial_state_is_title(gb, states):
    assert gb.state == states["STATE_TITLE"]


def test_start_advances_title_to_play(gb, states):
    gb.press("start")
    assert gb.state == states["STATE_PLAY"]


def test_start_is_ignored_during_play(gb, states):
    gb.press("start")
    gb.press("start")
    assert gb.state == states["STATE_PLAY"]


def test_full_loop_play_gameover_retry(gb, states):
    gb.press("start")
    assert gb.state == states["STATE_PLAY"]

    force_game_over(gb, states)
    assert gb.state == states["STATE_GAMEOVER"]

    gb.press("start")
    assert gb.state == states["STATE_PLAY"]


def test_title_screen_shows_the_title_map(gb):
    """Boot draws title_map into the BG map at one uniform tile offset."""
    tlm = _parse_c_array(ROOT / "res" / "title.c", "title_map")
    vram = gb.pyboy.memory[0x9800 : 0x9800 + 18 * 32]
    cells = [vram[row * 32 + col] for row in range(18) for col in range(20)]
    offset = cells[0] - tlm[0]
    assert offset > 0, "title tiles should sit above the shared low slots"
    assert all(c - t == offset for c, t in zip(cells, tlm))
