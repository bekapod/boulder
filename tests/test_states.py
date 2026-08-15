"""State machine dispatch: TITLE -> PLAY -> GAMEOVER -> PLAY.

START advances TITLE and retries from GAMEOVER, and does nothing during PLAY
"""

from helpers import (
    force_game_over,
)


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
