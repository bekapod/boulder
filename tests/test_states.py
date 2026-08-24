"""State machine dispatch: TITLE -> PLAY -> GAMEOVER -> PLAY.

START advances TITLE and retries from GAMEOVER, and does nothing during PLAY
"""

import pytest

from helpers import ROOT, force_game_over


@pytest.mark.c_ready
def test_rom_boots_without_crashing(gb):
    assert gb.tick(60), "emulator stopped during the first second of runtime"


@pytest.mark.c_ready
def test_initial_state_is_title(gb, states):
    assert gb.state == states["STATE_TITLE"]


@pytest.mark.c_ready
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


@pytest.mark.c_ready
def test_title_screen_shows_the_title_map(gb):
    """Boot draws title.tlm into the BG map at one uniform tile offset."""
    tlm = (ROOT / "build" / "title.tlm").read_bytes()
    vram = gb.pyboy.memory[0x9800 : 0x9800 + 18 * 32]
    cells = [vram[row * 32 + col] for row in range(18) for col in range(20)]
    offset = cells[0] - tlm[0]
    assert offset > 0, "title tiles should sit above the shared low slots"
    assert all(c - t == offset for c, t in zip(cells, tlm))
