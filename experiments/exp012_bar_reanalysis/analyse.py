"""exp012 — the disagreement set, and which foreclosures stand in it.

Reads ``rescore.json``. Reports where the two bars AGREE and moves on; the
deliverable is the disagreement set, and within it the comparisons a foreclosure
rests on.
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
        "by_experiment": {},
        "foreclosures": {},
        "disagreement_set": sorted(dis, key=lambda r: -r["x_bar_se"]),
    }
    for exp in sorted({r["experiment"] for r in rows}):
        e = [r for r in rows if r["experiment"] == exp]
        en = [r for r in e if not r["distinguishable_sd"]]
        out["by_experiment"][exp] = {
            "comparisons": len(e),
            "nulls": len(en),
            "flips": sum(r["disagree"] for r in e),
        }

    for fc, entries in LOAD_BEARING.items():
        cell: dict[str, Any] = {"comparisons": [], "affected": False, "affected_primary": False}
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
                }
            )
            if r["disagree"]:
                cell["affected"] = True
                if role == "primary":
                    cell["affected_primary"] = True
        out["foreclosures"][fc] = cell

    (HERE / "verdicts.json").write_text(json.dumps(out, indent=2))

    t = out["totals"]
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
        print(f"  {fc}: {mark}{prim}")
        for c in cell["comparisons"]:
            if "status" not in c or c["status"] == "NOT FOUND":
                print(f"      {c['comparison']:48s} NOT FOUND")
                continue
            print(
                f"      {c['comparison']:48s} [{c['role']:13s}] {c['status']:26s} "
                f"x_sd {c['x_bar_sd']:5.2f} x_se {c['x_bar_se']:6.2f} "
                f"sign {c['seeds_favouring_lower']:2d} p={c['sign_test_p']:.4f}"
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
