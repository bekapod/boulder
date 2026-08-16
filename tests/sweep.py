import datetime
import statistics
from pathlib import Path

import helpers
import playtest_bot as bot

SIGMAS = [
    (0.0, "perfect (TAS)"),
    (0.5, "top rhythm gamer"),
    (1.0, "skilled"),
    (1.2, "good rhythm player"),
    (1.5, "skilled-casual"),
    (2.0, "engaged casual"),
    (3.0, "casual"),
    (4.0, "tired / first session"),
]
RUNS = 50
SEED = 1

_T = helpers.tuning()
OUT_DIR = bot.ROOT / "docs" / "tuning"

COLLAPSE_RATIO = 1.35


def predicted_collapse_altitude(sigma: float) -> int | None:
    cycle = COLLAPSE_RATIO * sigma * _T["BAR_INNER_WIDTH"] / _T["SWEET_SPOT_WIDTH"]
    if cycle < _T["MARKER_CYCLE_MIN"]:
        return None
    cycle = min(cycle, _T["CYCLE_FRAMES"])
    return round((_T["CYCLE_FRAMES"] - cycle) * _T["METRES_PER_SPEEDUP"])


def dist(values: list[int]) -> dict[str, int]:
    if len(values) == 1:
        v = values[0]
        return {"mean": v, "median": v, "p10": v, "p90": v}
    s = sorted(values)
    return {
        "mean": round(statistics.mean(s)),
        "median": round(statistics.median(s)),
        "p10": s[round(0.1 * (len(s) - 1))],
        "p90": s[round(0.9 * (len(s) - 1))],
    }


def aggregate(rows: list[dict]) -> dict:
    death = dist([r["death_altitude"] for r in rows])
    peak = dist([r["max_altitude"] for r in rows])
    return {
        "sigma": rows[0]["sigma"],
        "runs": len(rows),
        "survived": sum(r["survived"] for r in rows),
        "misses": sum(r["misses"] for r in rows),
        "death": death,
        "max": peak,
    }


def summary_lines(aggs: list[dict], date: str) -> list[str]:
    floor_alt = (_T["CYCLE_FRAMES"] - _T["MARKER_CYCLE_MIN"]) * _T["METRES_PER_SPEEDUP"]
    labels = dict(SIGMAS)
    lines = [
        f"# Sweep {date}",
        "",
        f"{RUNS} runs per skill level (sigma 0 plays identically every "
        f"time, so it runs once), each capped at "
        f"~{bot.DEFAULT_MAX_FRAMES / 3600:.1f} min of game time. "
        "'survived' = still alive when time ran out.",
        "",
        "| sigma | player | runs | survived | dies around (usual range) "
        "| peaks around (usual range) | predicted wall |",
        "|---|---|---|---|---|---|---|",
    ]
    for a in aggs:
        pred = predicted_collapse_altitude(a["sigma"])
        pred_s = f"~{pred} m" if pred is not None else f"past top speed ({floor_alt} m)"
        d, m = a["death"], a["max"]
        lines.append(
            f"| {a['sigma']} | {labels.get(a['sigma'], '')} | {a['runs']} "
            f"| {a['survived']} | {d['median']} m ({d['p10']}-{d['p90']}) "
            f"| {m['median']} m ({m['p10']}-{m['p90']}) | {pred_s} |"
        )
    medians = [a["max"]["median"] for a in aggs]
    monotone = all(a >= b for a, b in zip(medians, medians[1:]))
    lines += [
        "",
        "Sanity check (steadier players should climb higher): "
        + ("PASS." if monotone
           else f"FAIL — peaks {medians} don't drop as sigma rises; "
                "don't trust this sweep."),
    ]
    perfect = next((a for a in aggs if a["sigma"] == 0.0), None)
    if perfect:
        if perfect["misses"] == 0 and perfect["survived"] == perfect["runs"]:
            lines += [
                "",
                "Perfect-play check: the sigma=0 bot never missed, even at "
                "top speed — the game has no built-in limit, only human "
                "hands do.",
            ]
        else:
            lines += [
                "",
                f"Perfect-play check: even the sigma=0 bot missed "
                f"{perfect['misses']} times and topped out at "
                f"{perfect['max']['median']} m — nobody can climb past "
                "this, no matter how good.",
            ]
    lines += [
        "",
        "Tuning constants at sweep time: "
        + ", ".join(
            f"{k}={_T[k]}"
            for k in (
                "CYCLE_FRAMES", "MARKER_CYCLE_MIN", "METRES_PER_SPEEDUP",
                "SWEET_SPOT_WIDTH", "HIT_REWARD", "MISS_PENALTY_DIV", "MISS_LIMIT",
            )
        ),
        "",
        f"The marker hits top speed at {floor_alt} m with this tuning. "
        "(GAM-6's ~1200-1400 m guess used older numbers; the predictions "
        "above use the current ones.)",
        "",
        "Notes:",
        "- for runs that survived, 'dies around' is just where they stood",
        "  when time ran out — read 'peaks around' for those instead.",
        "- missing slows the game back down, so players hover above where",
        "  their runs actually end.",
    ]
    return lines


def main() -> None:
    date = datetime.date.today().isoformat()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    csv_path = OUT_DIR / f"sweep-{date}.csv"
    md_path = OUT_DIR / f"sweep-{date}-summary.md"

    pyboy = bot.make_pyboy()
    all_rows, aggs = [], []
    try:
        helpers.wait_for_boot(pyboy)
        for sigma, _label in SIGMAS:
            runs = 1 if sigma == 0 else RUNS
            rows = bot.run_batch(pyboy, sigma, runs, SEED)
            all_rows += rows
            aggs.append(aggregate(rows))
            a = aggs[-1]
            print(
                f"sigma {sigma}: {runs} runs, {a['survived']} survived, "
                f"median death {a['death']['median']} m, "
                f"median max {a['max']['median']} m"
            )
    finally:
        pyboy.stop(save=False)

    bot.write_csv(csv_path, all_rows)
    summary = "\n".join(summary_lines(aggs, date)) + "\n"
    md_path.write_text(summary)
    print(f"\nwrote {csv_path.relative_to(bot.ROOT)} and {md_path.relative_to(bot.ROOT)}")
    print(summary)


if __name__ == "__main__":
    main()
