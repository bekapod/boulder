def test_sprite_x_moves_in_play(gb):
    gb.press("start")
    x_before = gb.pyboy.memory[0xFE01]
    gb.tick(10)
    x_after = gb.pyboy.memory[0xFE01]
    assert x_after != x_before, "Sprite X position did not change during PLAY state"


def test_sprite_x_reverses_at_end(gb):
    gb.press("start")
    assert gb.read("wMarkerDir") == 0x01
    gb.tick(80)
    assert gb.read("wMarkerDir") == 0xFF, (
        "Sprite X direction did not reverse at the end of the screen"
    )
