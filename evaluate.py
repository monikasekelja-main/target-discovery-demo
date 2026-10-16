"""Transparent eligibility checks for a SYNTHETIC assay example, not target validation.

This module reads only runtime evidence and a scientist-authored policy. Expected
answers live in evaluation/ and must not be exposed to an agent at runtime.
"""
from __future__ import annotations

import json
from math import isfinite, sqrt
from pathlib import Path
from statistics import mean, stdev

# Two-sided 95% Student-t critical value, 7 df. Fixed n=8 is deliberate for this demo.
T_975_DF7 = 2.3646242510102993

# Ignore only floating-point noise, never rounding to the displayed precision.
NUMERIC_TOLERANCE = 1e-9


def below(value, threshold):
    return value < threshold - NUMERIC_TOLERANCE


def above(value, threshold):
    return value > threshold + NUMERIC_TOLERANCE


def interval(values):
    if len(values) != 8 or not all(isfinite(x) for x in values):
        raise ValueError("This illustrative analysis requires eight finite donor values.")
    m = mean(values)
    half = T_975_DF7 * stdev(values) / sqrt(8)
    return {"mean": m, "lower_95": m - half, "upper_95": m + half, "n_donors": 8}


def assess(record, policy):
    """Return action eligibility, diagnostics and failed gates; human review is required."""
    expected_donors = policy["donor_ids"]
    failed = []
    stats = {}
    qc = policy['qc_thresholds']
    tolerance = policy['tolerability_thresholds']
    if record.get("synthetic") is not True:
        failed.append("G0: this demo accepts explicitly synthetic fixtures only")
    if record.get("context") != policy["context"]:
        failed.append("G0: hypothesis/assay context mismatch")
    if record.get("policy_version") != policy["policy_version"]:
        failed.append("G0: decision-policy version mismatch")
    assays = record.get("assays", {})
    if set(assays) != set(policy["assay_ids"]):
        failed.append("G1: missing or unexpected perturbation assay")
    for assay_id in policy["assay_ids"]:
        rows = assays.get(assay_id, [])
        if sorted(r.get("donor_id", "") for r in rows) != sorted(expected_donors):
            failed.append(f"G1:{assay_id}: expected eight complete, unique donor pairs")
            continue
        usable = True
        for r in rows:
            prefix = f"{assay_id}/{r['donor_id']}"
            required = policy["required_measurement_fields"]
            if any(k not in r or not isinstance(r[k], (float, int)) or not isfinite(r[k]) for k in required):
                failed.append(f"G1:{prefix}: missing or non-finite measurement")
                usable = False
                continue
            percent_fields = [k for k in required if k.endswith("_pct") and k not in ("positive_control_live_recovery_pct", "max_technical_cv_pct")]
            if any(not 0 <= r[k] <= 100 for k in percent_fields) or any(
                r[k] <= 0 for k in ["ntc_live_cells", "kd_live_cells", "ntc_target_mfi", "kd_target_mfi", "ntc_il17_positive_pct", "unstim_il17_positive_pct"]
            ):
                failed.append(f"G1:{prefix}: invalid measurement range or denominator")
                usable = False
                continue
            if r["technical_replicates"] != policy['technical_replicates_per_condition'] or r["min_live_cd4_events_per_well"] < policy["min_live_cd4_events"]:
                failed.append(f"G1:{prefix}: replicate/event-count requirement failed")
            positive_reduction = 100 * (1 - r["positive_control_il17_positive_pct"] / r["ntc_il17_positive_pct"])
            dynamic_range = r["ntc_il17_positive_pct"] / r["unstim_il17_positive_pct"]
            if (below(r["ntc_live_fraction_pct"], qc['ntc_viable_fraction_min_pct']) or below(dynamic_range, qc['dynamic_range_min_fold'])
                or below(positive_reduction, qc['positive_control_reduction_min_pct'])
                or below(r["positive_control_live_fraction_pct"], qc['positive_control_viable_fraction_min_pct'])
                or below(r["positive_control_live_recovery_pct"], qc['positive_control_recovery_min_pct'])
                or above(r["max_technical_cv_pct"], qc['max_technical_cv_pct'])):
                failed.append(f"G2:{prefix}: assay-control/QC requirement failed")
            engagement = 100 * (1 - r["kd_target_mfi"] / r["ntc_target_mfi"])
            if below(engagement, policy["protein_reduction_range_pct"][0]) or above(engagement, policy["protein_reduction_range_pct"][1]):
                failed.append(f"G3:{prefix}: protein reduction outside specified range")
            recovery = 100 * r["kd_live_cells"] / r["ntc_live_cells"]
            if below(r["kd_live_fraction_pct"], tolerance['viable_fraction_min_pct']) or below(recovery, tolerance['per_donor_recovery_min_pct']):
                failed.append(f"G4:{prefix}: cell-loss/viability requirement failed")
        if not usable:
            continue
        effects = [100 * (1 - r["kd_il17_positive_pct"] / r["ntc_il17_positive_pct"]) for r in rows]
        recoveries = [100 * r["kd_live_cells"] / r["ntc_live_cells"] for r in rows]
        engagement = [100 * (1 - r["kd_target_mfi"] / r["ntc_target_mfi"]) for r in rows]
        stats[assay_id] = {
            "functional_reduction_pct": interval(effects),
            "live_cell_recovery_pct": interval(recoveries),
            "protein_reduction_range_pct": [min(engagement), max(engagement)],
            "viable_fraction_range_pct": [min(r["kd_live_fraction_pct"] for r in rows), max(r["kd_live_fraction_pct"] for r in rows)],
            "donor_functional_reductions_pct": {r["donor_id"]: effect for r, effect in zip(rows, effects)},
        }
        if below(stats[assay_id]["live_cell_recovery_pct"]["lower_95"], tolerance["mean_recovery_lower_ci_min_pct"]):
            failed.append(f"G4:{assay_id}: lower 95% bound on mean live-cell recovery below policy threshold")
    if failed:
        action = "INCONCLUSIVE"
        reason = "A prerequisite failed; effect estimates are diagnostic only. Investigate the failed gate."
    elif all(not below(stats[a]["functional_reduction_pct"]["lower_95"], policy["minimum_useful_reduction_pct"]) for a in policy["assay_ids"]):
        action = "ADVANCE_TO_REPLICATION"
        reason = "Both methods meet the useful-effect criterion with intact prerequisites."
    elif all(below(stats[a]["functional_reduction_pct"]["upper_95"], policy["minimum_useful_reduction_pct"]) for a in policy["assay_ids"]):
        action = "DEPRIORITIZE_TESTED_HYPOTHESIS"
        reason = "Both methods exclude the predefined useful mean effect in this tested setting."
    else:
        action = "INCONCLUSIVE"
        reason = "At least one interval crosses the useful-effect boundary, or the methods disagree."
    return {
        "experiment_id": record.get("experiment_id"),
        "policy_version": policy["policy_version"],
        "proposed_action": action,
        "reason": reason,
        "prerequisites_passed": not failed,
        "failed_gates": sorted(set(failed)),
        "statistics": stats,
        "human_review_required": True,
        "claim_scope": policy["context"],
    }


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("experiment", type=Path)
    parser.add_argument("--policy", type=Path, default=Path(__file__).parent / "runtime" / "policy.json")
    args = parser.parse_args()
    print(json.dumps(assess(json.loads(args.experiment.read_text()), json.loads(args.policy.read_text())), indent=2))
