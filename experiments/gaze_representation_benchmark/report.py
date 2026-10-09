"""Deterministic aggregate-only Markdown report; no data loading or calculations."""

import json
from statistics import median


def cell(value):
    if value is None:
        return "undefined"
    if isinstance(value, bool):
        return "PASS" if value else "FAIL"
    if isinstance(value, float):
        return f"{value:.9g}"
    if isinstance(value, (dict, list)):
        return json.dumps(value, sort_keys=True, separators=(",", ":")).replace("|", "\\|")
    return str(value).replace("|", "\\|")


def table(headers, rows):
    return (
        "\n"
        + " | ".join(headers)
        + "\n"
        + " | ".join("---" for _ in headers)
        + "\n"
        + "\n".join(" | ".join(cell(v) for v in row) for row in rows)
        + "\n"
    )


def render(summary):
    lines = [
        "# Stage B2 — one-shot frozen representation evaluation\n",
        f"Freeze commit: `{summary['freeze_commit']}`. Definitions were frozen before geometry-2 outcome evaluation. Exactly R0/R1/R2 were evaluated; production is unchanged.\n",
        "Primary [0,3) seconds is authoritative. Secondary [0.8,3) is descriptive. Halves retain the 1.5 s boundary. All predictions are unclipped normalized screen coordinates. Every session builds its own references and nine-presentation independent-linear maps from calibration only. Feature level summaries weight presentations equally; screen errors weight samples equally. No target, block or missing ordering check is discarded.\n",
        "## Provenance and integrity\n",
        table(
            ["capture", "role", "SHA-256", "bytes"],
            [
                [
                    s,
                    "development" if s == "geometry-1" else "untouched holdout",
                    p["sha256"],
                    p["bytes"],
                ]
                for s, p in summary["captures"].items()
            ],
        ),
        "Both inputs passed protocol/version/configuration/schema, expected participant/session/role, complete 9 calibration + 27 validation schedule, raw geometry/frame identity, per-frame R0 reconstruction and independently reconstructed fresh session-calibration checks before outcome calculation. Captures were read-only; SHA-256 was checked again after evaluation.\n",
        "Aggregate JSON contains full-precision numerical metrics, every presentation/window/eye, both feature axes, exact-target and row/column transfer, variability, first/second-half and pairwise block drift, signed/absolute screen residual distributions by target/row/column/block/session, availability reasons and common-frame diagnostics: [results_summary.json](results_summary.json). It contains no participant frames, landmarks, geometry, frame timestamps or sample traces. This Markdown prints the principal tables and every binocular ordering check; the JSON is the complete numerical supplement.\n",
    ]
    execution = summary.get("execution", {})
    lines.append(
        f"Evaluator sealed before outcomes: `{execution.get('evaluator_commit', 'synthetic')}`. Python {execution.get('python', 'synthetic')}; NumPy {execution.get('numpy', 'synthetic')}. One-shot marker prevents rerun/overwrite.\n"
    )
    lines.append(execution.get("freeze_merge", "Synthetic execution.") + "\n")
    for session, data in summary["sessions"].items():
        label = "DEVELOPMENT RESULT" if session == "geometry-1" else "UNTOUCHED HOLDOUT RESULT"
        lines.append(f"## {label} — {session}\n")
        lines.append(
            "Schema/geometry coverage (integrity-only aggregate):\n\n```json\n"
            + json.dumps(
                summary["captures"][session].get("integrity", {}), sort_keys=True, indent=2
            )
            + "\n```\n"
        )
        reps = data["representations"]
        lines.append("### Calibration coverage, fit and amplification\n")
        rows = []
        for name, channels in reps.items():
            for eye, c in channels.items():
                cal = c["calibration"]
                mapping = cal["mapping"] or {}
                rows.append(
                    [
                        name,
                        eye,
                        cal["availability"]["usable"],
                        cal["availability"]["attempts"],
                        [p["usable"] for p in cal["presentations"]],
                        cal["presentation_errors"]["x_mae"],
                        cal["presentation_errors"]["y_mae"],
                        *[
                            mapping.get(k)
                            for k in ("x_slope", "x_intercept", "y_slope", "y_intercept")
                        ],
                        cal["mapping_unavailable_reason"],
                    ]
                )
        lines.append(
            table(
                [
                    "R",
                    "eye",
                    "usable",
                    "attempts",
                    "nine counts",
                    "cal x MAE",
                    "cal y MAE",
                    "x slope",
                    "x intercept",
                    "y slope",
                    "y intercept",
                    "map unavailable",
                ],
                rows,
            )
        )
        lines.append(
            "Mapping amplification is exactly x_slope × horizontal shift and y_slope × vertical shift. Mapped transfer and signed pairwise block shifts are in the feature JSON, with unchanged coefficients. Calibration fit is descriptive and cannot establish transfer.\n"
        )
        rows = []
        for name, channels in reps.items():
            for eye, c in channels.items():
                for p in c["calibration"]["presentations"]:
                    rows.append(
                        [
                            name,
                            eye,
                            p["target_id"],
                            p["horizontal_median"],
                            p["vertical_median"],
                            p["prediction"],
                            p["dx"],
                            p["dy"],
                        ]
                    )
        lines.append(
            table(["R", "eye", "target", "cal h", "cal v", "prediction", "dx", "dy"], rows)
        )
        lines.append("### Native screen performance and per-eye availability\n")
        rows = []
        for name, channels in reps.items():
            for eye, c in channels.items():
                for window in ("primary", "secondary"):
                    w = c[window]
                    err, av = w["screen"]["all"], w["availability"]["all"]
                    rows.append(
                        [
                            name,
                            eye,
                            window,
                            av["usable"],
                            av["attempts"],
                            av["usable_fraction"],
                            err["count"],
                            *[
                                err[k]
                                for k in (
                                    "x_mae",
                                    "y_mae",
                                    "x_bias",
                                    "y_bias",
                                    "mean_euclidean",
                                    "median_euclidean",
                                    "p95_euclidean",
                                )
                            ],
                            av["unavailable_reasons"],
                        ]
                    )
        lines.append(
            table(
                [
                    "R",
                    "eye",
                    "window",
                    "usable",
                    "attempts",
                    "fraction",
                    "mapped n",
                    "x MAE",
                    "y MAE",
                    "x bias",
                    "y bias",
                    "mean distance",
                    "median distance",
                    "p95 distance",
                    "unavailable reasons",
                ],
                rows,
            )
        )
        lines.append("### Feature transfer, separation, variability and drift\n")
        rows = []
        for name, channels in reps.items():
            for eye, c in channels.items():
                for window in ("primary", "secondary"):
                    for axis, f in c[window]["features"].items():
                        targets = f["targets"]

                        def target_median(key):
                            values = [t[key] for t in targets]
                            return median(values) if all(v is not None for v in values) else None

                        target_mad = [t["distribution"]["mad"] for t in targets]
                        target_iqr = [t["distribution"]["iqr"] for t in targets]
                        rows.append(
                            [
                                name,
                                eye,
                                window,
                                axis,
                                f["direction"],
                                f["calibration_level_medians"],
                                f["calibration_minimum_separation"],
                                f["ordering"]["pooled"]["minimum_separation"],
                                f["median_absolute_transfer"],
                                f["normalized_transfer"],
                                f["normalized_transfer_calibration_separation"],
                                median(target_mad)
                                if all(v is not None for v in target_mad)
                                else None,
                                median(target_iqr)
                                if all(v is not None for v in target_iqr)
                                else None,
                                target_median("mad_over_separation"),
                                target_median("iqr_over_separation"),
                                f["median_block_range"],
                                f["maximum_block_range"],
                                f["absolute_half_shift_summary"]["median"],
                            ]
                        )
        lines.append(
            table(
                [
                    "R",
                    "eye",
                    "window",
                    "axis",
                    "cal direction",
                    "cal level medians",
                    "cal separation",
                    "val separation",
                    "median abs transfer",
                    "normalized transfer",
                    "cal-sep ratio",
                    "median target MAD",
                    "median target IQR",
                    "median MAD/sep",
                    "median IQR/sep",
                    "median block range",
                    "max block range",
                    "median abs half change",
                ],
                rows,
            )
        )
        lines.append("### All binocular ordering checks\n")
        rows = []
        for name, channels in reps.items():
            for window in ("primary", "secondary"):
                for axis, f in channels["binocular"][window]["features"].items():
                    for check, values in f["ordering"].items():
                        rows.append(
                            [
                                name,
                                window,
                                axis,
                                check,
                                values["level_medians"],
                                values["signed_adjacent_separations"],
                                values["minimum_separation"],
                                values["ordered"],
                            ]
                        )
        lines.append(
            table(
                [
                    "R",
                    "window",
                    "axis",
                    "check",
                    "level medians",
                    "signed adjacent separations",
                    "minimum abs separation",
                    "ordering",
                ],
                rows,
            )
        )
        lines.append("### Primary binocular target transfer, variability and block/half drift\n")
        rows = []
        for name, channels in reps.items():
            for axis, f in channels["binocular"]["primary"]["features"].items():
                for t in f["targets"]:
                    rows.append(
                        [
                            name,
                            axis,
                            t["target_id"],
                            t["calibration_median"],
                            t["validation_median"],
                            t["signed_transfer"],
                            t["absolute_transfer"],
                            t["mapped_transfer"],
                            t["distribution"]["mad"],
                            t["distribution"]["iqr"],
                            t["mad_over_separation"],
                            t["iqr_over_separation"],
                            t["block_medians"],
                            t["pairwise_block_changes"],
                            t["block_range"],
                            t["first_half_validation_median"],
                            t["second_half_validation_median"],
                            t["first_half_transfer"],
                            t["second_half_transfer"],
                        ]
                    )
        lines.append(
            table(
                [
                    "R",
                    "axis",
                    "target",
                    "cal median",
                    "val median",
                    "signed transfer",
                    "abs transfer",
                    "mapped shift",
                    "MAD",
                    "IQR",
                    "MAD/sep",
                    "IQR/sep",
                    "block medians",
                    "pairwise signed changes (1→2,1→3,2→3)",
                    "range",
                    "first median",
                    "second median",
                    "first transfer",
                    "second transfer",
                ],
                rows,
            )
        )
        lines.append("### Primary binocular residuals by target, row, column and block\n")
        rows = []
        for name, channels in reps.items():
            w = channels["binocular"]["primary"]
            for grouping in ("target_id", "target_y", "target_x", "block"):
                for err, av in zip(w["screen"][grouping], w["availability"][grouping], strict=True):
                    rows.append(
                        [
                            name,
                            grouping,
                            err["value"],
                            av["usable"],
                            av["attempts"],
                            av["usable_fraction"],
                            err["count"],
                            *[
                                err[k]
                                for k in (
                                    "x_mae",
                                    "y_mae",
                                    "x_bias",
                                    "y_bias",
                                    "mean_euclidean",
                                    "median_euclidean",
                                    "p95_euclidean",
                                )
                            ],
                            av["unavailable_reasons"],
                        ]
                    )
        lines.append(
            table(
                [
                    "R",
                    "group",
                    "value",
                    "usable",
                    "attempts",
                    "fraction",
                    "mapped n",
                    "x MAE",
                    "y MAE",
                    "x bias",
                    "y bias",
                    "mean distance",
                    "median distance",
                    "p95 distance",
                    "unavailable reasons",
                ],
                rows,
            )
        )
        lines.append("### Exact common-frame comparisons (original calibration maps)\n")
        rows = []
        for name, comparison in data["comparisons"].items():
            for view in ("native", "common"):
                for window in ("primary", "secondary"):
                    for role, w in comparison[view][window].items():
                        err = w["screen"]["all"]
                        f = w["features"]["vertical"]
                        rows.append(
                            [
                                name,
                                view,
                                window,
                                role,
                                w["availability"]["all"]["attempts"],
                                err["count"],
                                err["x_mae"],
                                err["y_mae"],
                                f["normalized_transfer"],
                                sum(v["ordered"] is True for v in f["ordering"].values()),
                            ]
                        )
        lines.append(
            table(
                [
                    "candidate",
                    "coverage",
                    "window",
                    "representation",
                    "retained attempts",
                    "mapped n",
                    "x MAE",
                    "y MAE",
                    "normalized vertical transfer",
                    "correct vertical checks /16",
                ],
                rows,
            )
        )
        lines.append(
            "The common-frame JSON recomputes all feature, transfer, ordering, residual and availability summaries using each pair's identical frame identities. Neither reference nor mapping is refitted. Native R0 remains visible; neither coverage view can conceal or rescue a failure in the other.\n"
        )
    lines.append("## Untouched holdout: unchanged five-part PROMISING gate\n")
    descriptions = [
        "1: y MAE candidate/R0 ≤ 0.80",
        "2: normalized vertical transfer candidate/R0 ≤ 0.75",
        "3: no R0-correct vertical ordering check lost",
        "4: x MAE candidate/R0 ≤ 1.15",
        "5: no leakage, validation fit, future-frame dependence or post-holdout tuning",
    ]
    gates = summary["holdout_gate"]
    lines.append(
        "Each value reports native and exact common-frame coverage. The same five frozen criteria must be supported in both required views, with unchanged thresholds and no additional criterion or missing-frame cutoff. This prevents selecting whichever coverage looks favorable. Secondary results cannot rescue primary failures.\n"
    )
    for view in ("native", "common"):
        lines.append(f"### Primary {view} coverage — component gates\n")
        component = {
            name: summary["sessions"]["geometry-2"]["comparisons"][name][view]["primary_comparison"]
            for name in ("R1", "R2")
        }
        lines.append(
            table(
                ["criterion", "R1 value", "R1 pass/fail", "R2 value", "R2 pass/fail"],
                [
                    [
                        description,
                        component["R1"]["criteria"][str(k)]["value"],
                        component["R1"]["criteria"][str(k)]["pass"],
                        component["R2"]["criteria"][str(k)]["value"],
                        component["R2"]["criteria"][str(k)]["pass"],
                    ]
                    for k, description in enumerate(descriptions, 1)
                ],
            )
        )
    lines.append("### Five-criterion final decision (both coverage views explicit)\n")
    rows = [
        [
            description,
            gates["R1"]["criteria"][str(k)]["value"],
            gates["R1"]["criteria"][str(k)]["pass"],
            gates["R2"]["criteria"][str(k)]["value"],
            gates["R2"]["criteria"][str(k)]["pass"],
        ]
        for k, description in enumerate(descriptions, 1)
    ]
    lines.append(table(["criterion", "R1 value", "R1 pass/fail", "R2 value", "R2 pass/fail"], rows))
    for name in ("R1", "R2"):
        lines.append(f"**{name} OVERALL = {gates[name]['overall']}**\n")
    lines.append("## Engineering interpretation and limitations\n")
    if all(g["overall"] == "FAIL" for g in gates.values()):
        lines.append(
            "The preregistered representation alternatives failed the authoritative geometry-2 gate. No alternative replaces R0. Geometry-1 is descriptive development context and does not change either holdout decision.\n"
        )
    else:
        passed = ", ".join(name for name, g in gates.items() if g["overall"] == "PROMISING")
        lines.append(
            f"{passed} is PROMISING only for later live validation. Production R0 remains unchanged. Other candidates retain their recorded FAIL decision; geometry-1 does not alter holdout decisions.\n"
        )
    lines.append(
        "Better calibration fit, lower feature variability or one favorable target does not establish transfer. Decisions use all five frozen primary criteria, without softened thresholds or a partial-pass class. Missing/zero comparison denominators are undefined and do not pass. Common-frame coverage is explicit; unavailable candidate frames are never silently removed from native R0.\n"
    )
    lines.append(
        "Two sessions from one participant support this one-shot descriptive experiment, not population inference or an accessibility/clinical claim. R1 uses estimated nonmetric MediaPipe depth without camera intrinsics. R2's fixed affine contour may suppress signal as well as nuisance motion. No clipping, temporal filter, validation correction, formula replacement or production change was introduced. No new live interaction or session collection occurred; this task ends here.\n"
    )
    return "\n".join(lines)
