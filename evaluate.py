"""Score the checker vs keyword audits on synthetic falls with planted gaps and look-alikes.

python evaluate.py dev | heldout     (heldout seeds + wording frozen in heldout/ before the first run)
"""
import json
import os
import sys
from collections import Counter

from falltrack import baseline, engine
from falltrack.engine import COMPLIANT
from falltrack.synth import random_case

SYSTEMS = {"checker": engine.run, "keyword": baseline.run,
           "keyword_skip_negation_words": lambda c: baseline.run(c, negation=True)}


def slot_set(step):
    return {s["due"] for s in step.get("slots", []) if s["status"] == "MISSING"}


def score(seeds, bank="dev"):
    out = {k: {"gap_shown_compliant": Counter(), "false_flag": Counter(), "status_wrong": 0,
               "missed_slots_found": 0, "false_missing_slots": 0} for k in SYSTEMS}
    gaps, oks, decisions, missing_slots, looks, examples = Counter(), Counter(), 0, 0, Counter(), []
    for s in seeds:
        case, truth, planted, lk = random_case(s, bank)
        looks.update(lk)
        tr = engine.score(case, truth)
        tslots = slot_set(tr["HIR"])
        missing_slots += len(tslots)
        for k, t in tr.items():
            decisions += 1
            (oks if t["status"] in COMPLIANT else gaps)[k] += 1
        for name, fn in SYSTEMS.items():
            got = fn(case)["steps"]
            o = out[name]
            for k, t in tr.items():
                tc, gc = t["status"] in COMPLIANT, got[k]["status"] in COMPLIANT
                if not tc and gc:
                    o["gap_shown_compliant"][k] += 1
                if tc and not gc:
                    o["false_flag"][k] += 1
                    if name == "checker" and len(examples) < 40:
                        examples.append((s, k, t["status"], got[k]["status"]))
                if not tc and not gc and name == "checker" and t["status"] != got[k]["status"] and len(examples) < 40:
                    examples.append((s, k, t["status"], got[k]["status"]))
                o["status_wrong"] += t["status"] != got[k]["status"]
            gs = slot_set(got["HIR"])
            o["missed_slots_found"] += len(tslots & gs)
            o["false_missing_slots"] += len(gs - tslots)
    res = {"cases": len(seeds), "decisions": decisions, "gaps": dict(gaps), "compliant": dict(oks),
           "gaps_total": sum(gaps.values()), "compliant_total": sum(oks.values()), "missing_hir_slots": missing_slots,
           "lookalikes": dict(looks)}
    for name, o in out.items():
        res[name] = {"gaps_shown_compliant": sum(o["gap_shown_compliant"].values()),
                     "false_flags": sum(o["false_flag"].values()), "status_wrong": o["status_wrong"],
                     "missed_slots_found": o["missed_slots_found"], "false_missing_slots": o["false_missing_slots"],
                     "gaps_shown_compliant_by_step": dict(o["gap_shown_compliant"]),
                     "false_flags_by_step": dict(o["false_flag"])}
    res["checker_disagreements_sample"] = examples
    return res


if __name__ == "__main__":
    split = sys.argv[1] if len(sys.argv) > 1 else "dev"
    seeds = list(range(400)) if split == "dev" else json.load(open("heldout/seeds.json"))["seeds"]
    res = score(seeds, "dev" if split == "dev" else "heldout")
    print(json.dumps({k: v for k, v in res.items() if k != "checker_disagreements_sample"}, indent=2))
    print("sample checker disagreements:", res["checker_disagreements_sample"][:15])
    os.makedirs("out", exist_ok=True)
    json.dump(res, open(f"out/{split}.json", "w"), indent=2, default=str)
