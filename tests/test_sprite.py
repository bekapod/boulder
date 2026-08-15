def test_sprite_x_moves_in_play(gb):
    gb.press("start")
    x_before = gb.pyboy.memory[0xFE01]
    gb.tick(10)
    x_after = gb.pyboy.memory[0xFE01]
    assert x_after != x_before, "Sprite X position did not change during PLAY state"
