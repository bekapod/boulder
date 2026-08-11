"""State machine dispatch: TITLE -> PLAY -> GAMEOVER -> PLAY, all on START."""


def test_rom_boots_without_crashing(gb):
    assert gb.tick(60), "emulator stopped during the first second of runtime"


def test_initial_state_is_title(gb, states):
    assert gb.state == states["STATE_TITLE"]


def test_start_advances_title_to_play(gb, states):
    gb.press("start")
    assert gb.state == states["STATE_PLAY"]


def test_start_cycles_play_gameover_play(gb, states):
    gb.press("start")
    assert gb.state == states["STATE_PLAY"]

    gb.press("start")
    assert gb.state == states["STATE_GAMEOVER"]

    gb.press("start")
    assert gb.state == states["STATE_PLAY"]
