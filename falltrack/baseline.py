"""Keyword check for comparison: a step counts as done if any note in its window contains a keyword.
This is my reconstruction of a simple documentation audit, NOT Ascenix's product."""
import re
from datetime import timedelta

from .engine import parse, shift_windows
from .policy import DEFAULT_POLICY

KW = {
    "ASSESS": r"assessment|\bpfa\b|morse",
    "MD": r"\b(?:dr|md|np|physician|doctor)\b",
    "POA": r"\b(?:poa|sdm|daughter|son|wife|husband|family|niece|nephew)\b",
    "CAREPLAN": r"care ?plan|\bcp\b",
}
NEURO = r"neuro|\bnvs?\b|\bhir\b|pupil|gcs"
NEGWORDS = r"\b(?:not|no|unable|will|to be|pending|refused|declined)\b"


def run(case, policy=DEFAULT_POLICY, negation=False):
    t0, end = parse(case["incident"]["time"]), parse(case["end"])
    notes = [(parse(n["time"]), n["text"].lower()) for n in case["notes"] if parse(n["time"]) >= t0 - timedelta(minutes=10)]
    hours = {"ASSESS": policy["assess_within_h"], "MD": policy["md_within_h"], "POA": policy["poa_within_h"],
             "CAREPLAN": policy["careplan_within_h"]}
    res = {}
    for k, rx in KW.items():
        hit = [t for t, x in notes if re.search(rx, x) and not (negation and re.search(NEGWORDS, x))]
        res[k] = {"status": "MISSING" if not hit else "MET" if min(hit) <= t0 + timedelta(hours=hours[k]) else "LATE"}
    inc = case["incident"]
    if inc["witnessed"] and not inc["head_strike"]:
        res["HIR"] = {"status": "NOT_REQUIRED"}
    else:
        neuro = [t for t, x in notes if re.search(NEURO, x)]
        slots, used = [], set()
        for off, tol in policy["hir_slots"]:
            due = t0 + timedelta(minutes=off)
            if due > end:
                break
            m = [i for i, t in enumerate(neuro) if i not in used and abs((t - due).total_seconds()) <= tol * 60]
            if m:
                used.add(m[0])
            slots.append({"due": due, "status": "MET" if m else "MISSING"})
        res["HIR"] = {"status": "MISSING_SLOTS" if any(s["status"] == "MISSING" for s in slots) else "MET", "slots": slots}
    res["HIR_ESC"] = {"status": "NOT_REQUIRED"}  # free-text findings not read
    shifts = [w for w in shift_windows(t0, policy["followup_shifts"], policy["shift_starts"]) if w[1] <= end]
    miss = [w for w in shifts if not any(w[0] <= t < w[1] and "fall" in x for t, x in notes)]
    res["FOLLOWUP"] = {"status": "MISSING_SHIFTS" if miss else "MET", "missing": miss}
    return {"steps": res}
