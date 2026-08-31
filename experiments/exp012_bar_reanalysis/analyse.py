"""exp012 — the disagreement set, and which foreclosures stand in it.

Reads ``rescore.json``. Reports where the two bars AGREE and moves on; the
deliverable is the disagreement set, and within it the comparisons a foreclosure
rests on.

**THREE CRITERIA ARE REPORTED, NOT TWO, AND THEY ANSWER THREE QUESTIONS.**
Naming all three is the fix for the defect that produced this iteration — a
single unnamed threshold acquiring the authority of an answer to whichever
question the reader had in mind.

- **sd** — does the effect exceed scene-to-scene variation? *Would this reliably
  help on a new scene?*
- **sign test** — is there an effect at all? *Is the direction consistent?*
- **materiality** — is it large enough to act on?

**The se bar is not a fourth criterion; it is not a test.** ``|mean| > sd/sqrt(n)``
is ``t > 1``, which is p ~ 0.33 two-sided — no conventional level. It is reported
because it was asked for and because the disagreement set is the deliverable, but
"45 nulls flip" means "two non-tests disagree on 45 comparisons", not "45 nulls
were real". The sign test is what says which of them carry a signal.
"""

from __future__ import annotations

import collections
import json
import pathlib
from typing import Any

HERE = pathlib.Path(__file__).parent

#: Comparisons a foreclosure's own text names as its evidence. Read from the
#: ledger entries, not guessed: fc-007's rationale names A' against C on both
#: primary metrics; fc-008's names E against A' and D against E; fc-010's names
#: N and V against W. Secondary metrics and non-scored regions are listed so the
#: report can say a flip landed OUTSIDE the load-bearing set rather than in it.
LOAD_BEARING = {
    "fc-007": [
        ("exp001_gaze_objective", "A_prime_vs_C|median_abs_err", "primary"),
        ("exp001_gaze_objective", "A_prime_vs_C|p90", "primary"),
    ],
    "fc-008": [
        ("exp002_saliency_value", "E_vs_A_prime|median_abs_err", "primary"),
        ("exp002_saliency_value", "E_vs_A_prime|p90", "primary"),
        ("exp002_saliency_value", "D_vs_E|median_abs_err", "primary"),
        ("exp002_saliency_value", "D_vs_E|p90", "primary"),
        (
            "exp005_stratified_reanalysis",
            "exp002:E_vs_A_prime@AWAY|median_abs_err",
            "qualification",
        ),
        ("exp005_stratified_reanalysis", "exp002:E_vs_A_prime@AWAY|p90", "qualification"),
    ],
    "fc-010": [
        ("exp003_vergence_acquisition", "N_vs_W@intersection|median_abs_err", "primary"),
        ("exp003_vergence_acquisition", "N_vs_W@intersection|p90", "primary"),
        ("exp003_vergence_acquisition", "V_vs_W@intersection|median_abs_err", "primary"),
        ("exp003_vergence_acquisition", "V_vs_W@intersection|p90", "primary"),
    ],
}


def main() -> None:
    rows = json.loads((HERE / "rescore.json").read_text())
    by_key = {(r["experiment"], r["comparison"]): r for r in rows}
    dis = [r for r in rows if r["disagree"]]
    flipped_positives = [r for r in rows if r["distinguishable_sd"] and not r["distinguishable_se"]]
    nulls = [r for r in rows if not r["distinguishable_sd"]]

    out: dict[str, Any] = {
        "experiment": "exp012_bar_reanalysis",
        "totals": {
            "comparisons": len(rows),
            "experiments": len({r["experiment"] for r in rows}),
            "distinguishable_sd": sum(r["distinguishable_sd"] for r in rows),
            "distinguishable_se": sum(r["distinguishable_se"] for r in rows),
            "nulls_sd": len(nulls),
            "disagreement_set": len(dis),
            "agreement_fraction": (len(rows) - len(dis)) / len(rows),
            "nulls_that_flip_fraction": len(dis) / len(nulls) if nulls else 0.0,
            "positives_that_flipped": len(flipped_positives),
            "recorded_verdict_mismatches": sum(not r["recorded_verdict_matches"] for r in rows),
        },
        "binds": {
            "sd_bar": dict(collections.Counter(r["binds_sd"] for r in rows)),
            "se_bar": dict(collections.Counter(r["binds_se"] for r in rows)),
            "agree_by_construction": sum(1 for r in rows if r["binds_se"] == "materiality"),
        },
        "se_bar_is_not_a_test": {
            "threshold": "|mean| > sd/sqrt(n), i.e. t > 1",
            "two_sided_p_by_n": {},
            "disagreements_passing_sign_test": 0,
            "disagreements_failing_sign_test": 0,
        },
        "by_experiment": {},
        "foreclosures": {},
        "disagreement_set": sorted(dis, key=lambda r: -r["x_bar_se"]),
    }
    from scipy import stats as _st

    for n in sorted({r["n_seeds"] for r in rows}):
        out["se_bar_is_not_a_test"]["two_sided_p_by_n"][str(n)] = float(2 * _st.t.sf(1.0, n - 1))
    sig = [r for r in dis if r["sign_significant"]]
    out["se_bar_is_not_a_test"]["disagreements_passing_sign_test"] = len(sig)
    out["se_bar_is_not_a_test"]["disagreements_failing_sign_test"] = len(dis) - len(sig)
    out["disagreements_passing_sign_test"] = sorted(sig, key=lambda r: r["sign_test_p"])

    for exp in sorted({r["experiment"] for r in rows}):
        e = [r for r in rows if r["experiment"] == exp]
        en = [r for r in e if not r["distinguishable_sd"]]
        out["by_experiment"][exp] = {
            "comparisons": len(e),
            "nulls": len(en),
            "flips": sum(r["disagree"] for r in e),
        }

    for fc, entries in LOAD_BEARING.items():
        cell: dict[str, Any] = {
            "comparisons": [],
            "affected": False,
            "affected_primary": False,
            "flip_passes_sign_test": False,
        }
        for exp, comp, role in entries:
            r = by_key.get((exp, comp))
            if r is None:
                cell["comparisons"].append(
                    {"comparison": comp, "role": role, "status": "NOT FOUND"}
                )
                continue
            status = (
                "FLIPS"
                if r["disagree"]
                else (
                    "distinguishable under both" if r["distinguishable_sd"] else "null under both"
                )
            )
            cell["comparisons"].append(
                {
                    "experiment": exp,
                    "comparison": comp,
                    "role": role,
                    "status": status,
                    "n_seeds": r["n_seeds"],
                    "mean_diff": r["mean_diff"],
                    "x_bar_sd": r["x_bar_sd"],
                    "x_bar_se": r["x_bar_se"],
                    "seeds_favouring_lower": r["seeds_favouring_lower"],
                    "sign_test_p": r["sign_test_p"],
                    "sign_significant": r["sign_significant"],
                }
            )
            if r["disagree"]:
                cell["affected"] = True
                if role == "primary":
                    cell["affected_primary"] = True
                if r["sign_significant"]:
                    cell["flip_passes_sign_test"] = True
        out["foreclosures"][fc] = cell

    (HERE / "verdicts.json").write_text(json.dumps(out, indent=2))

    t = out["totals"]
    at = [
        r for r in rows if r["experiment"].startswith("exp011") and "AT_common" in r["comparison"]
    ]
    print("=== THE LOAD-BEARING NULL THAT ACTUALLY MOVED: exp011's AT band ===")
    print("  Closing the loop helps MOST at depth discontinuities — the framework's")
    print("  original motivation — and two of four levels recorded it as a null.")
    print(f"  {'level':>6} {'mean_diff':>10} {'x_bar_sd':>9} {'sign':>7} {'p':>10}  recorded")
    for r in sorted(at, key=lambda x: x["comparison"]):
        lvl = r["comparison"].split(":")[0]
        rec = "INDISTINGUISHABLE" if not r["distinguishable_sd"] else "distinguishable"
        print(
            f"  {lvl:>6} {r['mean_diff']:+10.5f} {r['x_bar_sd']:9.2f} "
            f"{r['seeds_favouring_lower']:3d}/{r['seeds_nonzero']:<3d} "
            f"{r['sign_test_p']:10.2e}  {rec}"
        )
    print("  The direction is consistent at EVERY level. The two recorded as nulls")
    print("  are nulls about EFFECT SIZE, not about existence.\n")

    print("=== (d) first: did a positive flip? ===")
    print(
        f"  positives that flipped: {t['positives_that_flipped']}  "
        f"(algebra says 0; a nonzero count means the implementation is wrong)"
    )
    print(
        f"  re-scored verdicts disagreeing with what each experiment recorded: "
        f"{t['recorded_verdict_mismatches']}"
    )

    print(
        f"\n=== the two bars agree on {t['comparisons'] - t['disagreement_set']} of "
        f"{t['comparisons']} comparisons ({t['agreement_fraction'] * 100:.1f}%) ==="
    )
    print(f"  distinguishable: sd {t['distinguishable_sd']}, se {t['distinguishable_se']}")
    print(
        f"  nulls under sd: {t['nulls_sd']}, of which {t['disagreement_set']} flip "
        f"({t['nulls_that_flip_fraction'] * 100:.1f}%)"
    )
    print(
        f"  the materiality floor binds under se in {out['binds']['agree_by_construction']} "
        f"comparisons — there the two bars agree BY CONSTRUCTION"
    )

    nt = out["se_bar_is_not_a_test"]
    print("\n=== the se bar is NOT a significance test, and this is Chat's error ===")
    print(f"  threshold: {nt['threshold']}")
    ps = ", ".join(f"n={k}: {v:.3f}" for k, v in nt["two_sided_p_by_n"].items())
    print(f"  as a two-sided p: {ps}  — no conventional level")
    print(
        f"  so of the {t['disagreement_set']} disagreements, "
        f"{nt['disagreements_passing_sign_test']} pass a sign test at p < 0.05 and "
        f"{nt['disagreements_failing_sign_test']} do not."
    )
    print("  The set is where TWO NON-TESTS DISAGREE, not 45 nulls that were real.")

    print("\n=== the disagreements that carry a signal (sign test p < 0.05) ===")
    for r in out["disagreements_passing_sign_test"]:
        print(
            f"  {r['experiment'][:6]} {r['comparison']:46s} "
            f"sign {r['seeds_favouring_lower']:2d}/{r['seeds_nonzero']:<2d} "
            f"p={r['sign_test_p']:.2e} x_sd {r['x_bar_sd']:.2f} mean{r['mean_diff']:+.5f}"
        )

    print("\n=== disagreement set by experiment ===")
    for exp, c in out["by_experiment"].items():
        print(
            f"  {exp:32s} {c['flips']:3d}/{c['nulls']:3d} nulls flip"
            f"  ({c['comparisons']:3d} comparisons)"
        )

    print("\n=== does a foreclosure rest on anything in the set? ===")
    for fc, cell in out["foreclosures"].items():
        mark = "AFFECTED" if cell["affected"] else "not affected"
        prim = " (ON A PRIMARY METRIC)" if cell["affected_primary"] else ""
        sign = (
            " — and the flip PASSES a sign test"
            if cell["flip_passes_sign_test"]
            else (" — but the flip FAILS a sign test, so nothing moved" if cell["affected"] else "")
        )
        print(f"  {fc}: {mark}{prim}{sign}")
        for c in cell["comparisons"]:
            if "status" not in c or c["status"] == "NOT FOUND":
                print(f"      {c['comparison']:48s} NOT FOUND")
                continue
            print(
                f"      {c['comparison']:48s} [{c['role']:13s}] {c['status']:26s} "
                f"x_sd {c['x_bar_sd']:5.2f} x_se {c['x_bar_se']:6.2f} "
                f"sign {c['seeds_favouring_lower']:2d} p={c['sign_test_p']:.4f}"
                f"{'  SIGNIFICANT' if c['sign_significant'] else ''}"
            )
        print()

    print("=== the ten largest disagreements ===")
    for r in out["disagreement_set"][:10]:
        print(
            f"  {r['experiment'][:6]} {r['comparison']:46s} n={r['n_seeds']:2d} "
            f"mean{r['mean_diff']:+9.5f} x_sd {r['x_bar_sd']:.2f} -> x_se {r['x_bar_se']:5.2f} "
            f"sign {r['seeds_favouring_lower']}/{r['seeds_nonzero']} p={r['sign_test_p']:.4f}"
        )
    print(f"\nwrote {HERE / 'verdicts.json'}")


if __name__ == "__main__":
    main()
