"""One synthetic unwitnessed fall: what the checker reads from the notes vs a keyword check."""
from falltrack import baseline, engine

N = lambda t, x: {"time": t, "text": x}
CASE = {
    "incident": {"id": "INC-DEMO", "resident": "R-214 (synthetic)", "time": "2026-03-04T02:40", "witnessed": False, "head_strike": False},
    "end": "2026-03-07T11:00",
    "notes": [
        N("2026-03-04T02:43", "Resident found on floor beside bed by PSW. HIR initiated, NV WNL, PERRLA, GCS 15."),
        N("2026-03-04T03:05", "Called daughter (POA) re: fall, no answer, left VM."),
        N("2026-03-04T03:20", "Dr. Patel aware of fall, no new orders."),
        N("2026-03-04T03:45", "NV @0255, 0310, 0325 and 0340 all WNL."),
        N("2026-03-04T04:12", "Neuro vitals WNL."),
        N("2026-03-04T04:41", "Neuro vitals WNL."),
        N("2026-03-04T06:55", "NV @0540, 0640 WNL. Next NV due @0740."),
        N("2026-03-04T07:50", "Post fall assessment to be completed by day nurse."),
        N("2026-03-04T08:45", "Resident refused neuro vitals."),
        N("2026-03-04T09:40", "Post fall assessment completed, Morse score 75. Care plan updated: bed in lowest position."),
        N("2026-03-04T16:38", "Neuro vitals WNL."),
        N("2026-03-04T20:45", "Neuro vitals WNL."),
        N("2026-03-05T00:35", "Neuro vitals WNL."),
    ] + [N(t, "Post fall follow-up: no s/s of injury, ROM at baseline.") for t in
         ("2026-03-04T11:00", "2026-03-04T19:00", "2026-03-05T03:00", "2026-03-05T19:00",
          "2026-03-06T03:00", "2026-03-06T11:00", "2026-03-06T19:00", "2026-03-07T03:00")]
      + [N("2026-03-05T12:00", "Hx of falls, last fall in June.")],
}

for i, n in enumerate(CASE["notes"]):
    n["id"] = f"N{i + 1:02d}"

if __name__ == "__main__":
    import sys
    sys.stdout.reconfigure(encoding="utf-8")
    r = engine.run(CASE)
    b = baseline.run(CASE)["steps"]
    print("Unwitnessed fall 02:40 · synthetic resident · policy: sample home (falltrack/policy.py)\n")
    for k, s in r["steps"].items():
        extra = ""
        if k == "HIR" and s["status"] != "NOT_REQUIRED":
            miss = [x["due"].strftime("%H:%M") for x in s["slots"] if x["status"] == "MISSING"]
            ref = [x["due"].strftime("%H:%M") for x in s["slots"] if x["status"] == "REFUSED"]
            extra = f"missing {len(miss)}/{len(s['slots'])}: {', '.join(miss)}" + (f" · refused (documented) {', '.join(ref)}" if ref else "")
        elif k == "FOLLOWUP" and s["missing"]:
            extra = "no note in shift " + ", ".join(a.strftime("%a %H:%M") for a, _ in s["missing"])
        elif "evidence" in s:
            extra = f"\"{s['evidence']['quote']}\" ({s['evidence']['note'] or '-'})"
        if s["status"] == "ATTEMPT_ONLY":
            extra = f"{s['attempts']} attempt(s), no contact: " + extra
        bk = b[k]["status"]
        if k == "HIR" and "slots" in b[k]:
            bk += f" ({sum(x['status'] == 'MISSING' for x in b[k]['slots'])} slots)"
        print(f"  {k:9} {s['status']:15} keyword: {bk:24} {extra}")
        print(f"            {s['policy']}")
    print("\nIgnored by the checker (with reason):")
    for nid, c, why in r["ignored"]:
        print(f"  {nid or '-'}: \"{c}\" -> {why}")
