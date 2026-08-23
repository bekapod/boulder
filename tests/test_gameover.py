from helpers import enter_play, force_game_over, parse_rgbinc

TILES = parse_rgbinc("tiles.rgbinc")
GO = parse_rgbinc("gameover.rgbasm")
BLINK = parse_rgbinc("blink.rgbasm")

SCRN0 = 0x9800
BLINK_PERIOD = 2 * BLINK["BLINK_FRAMES"] + 10


def sprite(gb, slot):
    """One shadow-OAM entry as [y, x, tile, attrs]."""
    a = gb.pyboy.symbol_lookup("wShadowOAM")[1] + slot * 4
    return list(gb.pyboy.memory[a : a + 4])


def expected_digits(value):
    """Mirror BuildDigits: 3 tiles, blank-padded on the left, clamped at 999."""
    value = min(value, 999)
    h, t, o = value // 100, (value // 10) % 10, value % 10
    base = TILES["TILE_DIGIT_FIRST"]
    return [base + h if h else 0, base + t if h or t else 0, base + o]


def value_digits(gb, first_slot):
    return [sprite(gb, first_slot + i)[2] for i in range(3)]


def newbest_visible(gb):
    return sprite(gb, GO["SPR_NEWBEST_FIRST"])[0] != 0


def test_run_shows_death_altitude(gb, states):
    enter_play(gb, states)
    gb.set16("wAltitude", 500)
    force_game_over(gb, states)
    assert value_digits(gb, GO["SPR_RUN_VALUE"]) == expected_digits(
        gb.read16("wAltitude")
    )


def test_record_updates_best_and_blinks(gb, states):
    enter_play(gb, states)
    gb.set16("wAltitude", 500)
    force_game_over(gb, states)

    final = gb.read16("wAltitude")
    assert final > 0, "death spiral drained the altitude to zero"
    assert gb.read16("wBest") == final
    assert value_digits(gb, GO["SPR_BEST_VALUE"]) == expected_digits(final)

    seen = set()
    for _ in range(BLINK_PERIOD):
        seen.add(newbest_visible(gb))
        gb.tick(1)
    assert seen == {True, False}, "NEW BEST! should blink and it didn't"


def test_no_record_leaves_best_alone(gb, states):
    enter_play(gb, states)
    gb.set16("wBest", 900)
    gb.set16("wAltitude", 500)
    force_game_over(gb, states)

    assert gb.read16("wBest") == 900
    assert value_digits(gb, GO["SPR_BEST_VALUE"]) == expected_digits(900)
    for _ in range(BLINK_PERIOD):
        assert not newbest_visible(gb)
        gb.tick(1)


def test_ten_instant_retries(gb, states):
    enter_play(gb, states)
    for _ in range(10):
        force_game_over(gb, states)
        gb.press("start")
        assert gb.state == states["STATE_PLAY"], "start should retry from GAMEOVER"
