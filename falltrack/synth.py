"""Synthetic falls with progress notes. Truth = the events that really happened (kind, status, time),
rendered into free text from a wording bank. Gaps and look-alikes are planted and labelled.

bank "dev" lives here; bank "heldout" is heldout/wording.json (written and frozen in git before the first run).
"""
import json
import os
import random
from datetime import datetime, timedelta

DEV = {
    "time_styles": ["@{HHMM}", "at {HH}:{MM}", "{HHMM}h"],
    "family": ["daughter (POA)", "son (POA)", "POA", "SDM", "wife (SDM)", "niece (POA)"],
    "doc": ["Dr Patel", "Dr. Nguyen", "NP Gomez", "on-call MD", "the physician"],
    "fall_unwitnessed": ["Resident found on floor beside bed by PSW at start of rounds.",
                         "Unwitnessed fall: resident found sitting on the floor in bathroom.",
                         "Resident found lying on floor next to wheelchair, unable to say what happened."],
    "fall_witnessed": ["Witnessed by PSW sliding out of wheelchair, lowered to floor.",
                       "Resident lost balance while walking with walker, PSW witnessed and assisted to floor.",
                       "Witnessed fall in dining room, resident sat down hard on buttocks."],
    "head_strike": ["Resident hit head on night table, small bump on forehead noted."],
    "denies_head": ["Resident denies hitting head.", "Did not hit head per PSW who witnessed."],
    "mismatch_cue": ["When writer arrived resident was found on floor, PSW had stepped out of the room."],
    "assess_done": ["Post fall assessment completed, Morse score {score}.", "PFA done.",
                    "Post-fall huddle held with team, assessment completed."],
    "assess_plan": ["Post fall assessment to be completed by day nurse.", "PFA pending."],
    "md_done": ["{doc} notified of fall, no new orders.", "{doc} aware of fall.", "Called {doc}, informed of fall, will review in AM."],
    "md_attempt": ["Paged {doc}, awaiting call back.", "Fax sent to {doc} re: fall.", "Left message for {doc}."],
    "md_plan": ["Will notify {doc} in AM.", "{doc} to be notified of fall."],
    "md_neg": ["{doc} not yet notified."],
    "poa_done": ["{who} notified of fall.", "Spoke with {who}, aware of fall and plan.", "Called {who}, informed of fall."],
    "poa_attempt": ["Called {who}, no answer, left VM.", "Unable to reach {who}.", "Left voicemail for {who} re: fall."],
    "poa_plan": ["Will call {who} in the morning.", "{who} to be notified."],
    "poa_neg": ["{who} not notified yet."],
    "poa_past": ["{who} was notified of previous fall last month."],
    "self_poa": ["Resident is own SDM, informed of fall.", "Self-POA, resident aware."],
    "neuro_single": ["NV done, PERRLA, GCS 15.", "Neuro vitals WNL.", "HIR: pupils equal and reactive, GCS 15."],
    "neuro_timed": ["Neuro vitals {t} WNL.", "NV {t}: PERRLA, GCS 15."],
    "neuro_multi": ["NV {t1}, {t2}, {t3} all WNL.", "Neuro checks done {t1}, {t2} and {t3}, GCS 15."],
    "neuro_refused": ["Resident refused neuro vitals.", "Declined NV, will reattempt."],
    "neuro_next_due": ["Next NV due {t}.", "HIR to continue, next check {t}."],
    "neuro_abnormal": ["NV: GCS 13, newly confused.", "Neuro vitals: pupils unequal."],
    "hir_dc_order": ["HIR discontinued per Dr Patel order.", "Neuro checks d/c'd as per NP order."],
    "hir_dc_no_order": ["HIR stopped, resident sleeping.", "Neuro checks discontinued, resident settled."],
    "late_entry": ["Late entry for {t}: "],
    "followup": ["Post fall follow-up: no s/s of injury, ROM at baseline.", "Day {d} post fall, no complaints of pain.",
                 "Follow up re fall: resident resting, bed in low position."],
    "followup_lookalike": ["Hx of falls, last fall in June.", "Resident has history of falls, bed alarm in place."],
    "careplan_done": ["Care plan updated: bed in lowest position, hip protectors.", "CP reviewed, new intervention added."],
    "careplan_plan": ["Care plan to be reviewed at next care conference."],
    "filler": ["Ate 75% of lunch.", "Meds given as ordered.", "VS: BP 132/78, HR 76, T 36.8.", "Denies pain.",
               "Son visited this afternoon.", "Daughter called to ask about laundry.", "Slept well, no concerns.",
               "No new orders."],
}

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def bank(name):
    if name == "dev":
        return DEV
    return json.load(open(os.path.join(HERE, "heldout", "wording.json"), encoding="utf-8"))


def fmt(t, style):
    h12 = t.hour % 12 or 12
    return style.format(HHMM=f"{t:%H%M}", HH=f"{t:%H}", MM=f"{t:%M}", h=h12, ampm="am" if t.hour < 12 else "pm")


def random_case(seed, bank_name="dev", policy=None):
    from .policy import DEFAULT_POLICY
    policy = policy or DEFAULT_POLICY
    B = bank(bank_name)
    r = random.Random(seed)
    hour = r.choice([0, 1, 2, 3, 4, 5, 5, 6, 6, 7, 10, 14, 16, 18, 20, 21, 22, 23])
    t0 = datetime(2026, r.randint(1, 9), r.randint(1, 28), hour, r.randint(0, 59))
    witnessed = r.random() < 0.45
    head = witnessed and r.random() < 0.25
    mismatch = witnessed and not head and r.random() < 0.15
    notes, truth, planted, looks = [], [], {}, []
    pick = lambda k: r.choice(B[k])
    style = lambda: r.choice(B["time_styles"])
    sub = lambda s: s.format(who=r.choice(B["family"]), doc=r.choice(B["doc"]), score=r.randint(45, 95),
                             d=r.randint(1, 3), t="{t}", t1="{t1}", t2="{t2}", t3="{t3}")

    def note(t, text):
        notes.append({"time": t, "text": text})

    def ev(kind, status, t):
        truth.append({"kind": kind, "status": status, "time": t, "quote": "(truth)", "note": None})

    # incident note
    first = t0 + timedelta(minutes=r.randint(10, 35))
    desc = pick("fall_witnessed" if witnessed else "fall_unwitnessed")
    if head:
        desc += " " + pick("head_strike")
    elif witnessed and not mismatch and r.random() < 0.5:
        desc += " " + pick("denies_head")
        looks.append("denies_head")
    if mismatch:
        desc += " " + pick("mismatch_cue")
        ev("HEAD_CUE", "DONE", first)
        planted["FORM_SAYS_WITNESSED"] = 1
    note(first, desc)

    def timed_step(kind, kdone, kplan, kneg, kattempt, kpast, hours, gap_types, extra_ok=()):
        mode = r.choice(["ok"] * 5 + list(gap_types) + list(extra_ok))
        if mode == "self":
            t = first + timedelta(minutes=r.randint(1, 30))
            note(t, sub(pick("self_poa")))
            ev("SELF_POA", "DONE", t)
            return
        if mode in ("ok", "late", "retry"):
            if mode == "retry" and kattempt:
                ta = t0 + timedelta(minutes=r.randint(20, 120))
                note(ta, sub(pick(kattempt)))
                ev(kind, "ATTEMPT", ta)
            lo, hi = (0.3, hours * 0.8) if mode != "late" else (hours * 1.1, hours * 2.5)
            t = t0 + timedelta(hours=r.uniform(lo, hi))
            if mode == "retry":
                t = max(t, ta + timedelta(minutes=30))
            txt = sub(pick(kdone))
            if r.random() < 0.25:  # written later as a late entry with the real time
                entry = t + timedelta(minutes=r.randint(40, 150))
                note(entry, B["late_entry"][r.randrange(len(B["late_entry"]))].replace("{t}", fmt(t, style())) + txt)
            else:
                note(t, txt)
            ev(kind, "DONE", t)
            if mode == "late":
                planted[kind + "_LATE"] = 1
            if kplan and r.random() < 0.3:
                note(t0 + timedelta(minutes=r.randint(40, 90)), sub(pick(kplan)))
                looks.append(kind + "_plan_then_done")
            return
        planted[kind + "_" + mode.upper()] = 1
        t = t0 + timedelta(minutes=r.randint(30, 300))
        if mode == "attempt":
            for _ in range(r.randint(1, 2)):
                note(t, sub(pick(kattempt)))
                ev(kind, "ATTEMPT", t)
                t += timedelta(minutes=r.randint(60, 240))
        elif mode == "plan":
            note(t, sub(pick(kplan)))
        elif mode == "neg":
            note(t, sub(pick(kneg)))
        elif mode == "past":
            note(t, sub(pick(kpast)))

    timed_step("ASSESS", "assess_done", "assess_plan", None, None, None, policy["assess_within_h"], ["missing", "late", "plan"])
    timed_step("MD", "md_done", "md_plan", "md_neg", "md_attempt", None, policy["md_within_h"],
               ["missing", "late", "attempt", "plan", "neg"], ["retry"])
    timed_step("POA", "poa_done", "poa_plan", "poa_neg", "poa_attempt", "poa_past", policy["poa_within_h"],
               ["missing", "late", "attempt", "plan", "neg", "past"], ["retry", "self"])
    timed_step("CAREPLAN", "careplan_done", "careplan_plan", None, None, None, policy["careplan_within_h"],
               ["missing", "plan"])

    # head injury routine
    required = (not witnessed) or head or mismatch
    md_times = [e["time"] for e in truth if e["kind"] == "MD" and e["status"] == "DONE"]
    if required:
        mode = r.choice(["ok", "ok", "ok", "drop", "drop", "drop_shift", "next_due", "dc_no_order", "dc_order", "refused", "abnormal"])
        if mismatch and r.random() < 0.6:
            mode = "none"
        slots = [(t0 + timedelta(minutes=o), tol) for o, tol in policy["hir_slots"]]
        dc_at = None
        drop = set()
        if mode == "drop":
            drop = set(r.sample(range(1, len(slots)), r.randint(1, 3)))
        if mode == "drop_shift":  # slots that fall within 45 min of a shift change
            drop = {i for i, (d, _) in enumerate(slots) if i and min(abs((d.replace(hour=h, minute=0) - d).total_seconds()) for h in (7, 15, 23)) < 2700}
            if not drop:
                drop = {r.randrange(1, len(slots))}
        if mode == "next_due":
            drop = {r.randrange(2, len(slots))}
        if mode == "dc_no_order":
            k = r.randrange(5, len(slots) - 2)
            drop = set(range(k, len(slots)))
            dc_at = (k, False)
        if mode == "dc_order":
            k = r.randrange(5, len(slots) - 2)
            drop = set(range(k, len(slots)))
            dc_at = (k, True)
        if mode == "none":
            drop = set(range(len(slots)))
        refused = {r.randrange(1, len(slots))} - drop if mode == "refused" else set()
        abnormal = r.randrange(1, 9) if mode == "abnormal" else None
        if mode in ("drop", "drop_shift", "next_due", "dc_no_order", "none"):
            planted["HIR_" + mode.upper()] = len(drop)
        done = [(i, d + timedelta(minutes=r.randint(-int(tol * 0.5), int(tol * 0.5)))) for i, (d, tol) in enumerate(slots) if i not in drop]
        i = 0
        while i < len(done):
            idx, t = done[i]
            status = "REFUSED" if idx in refused else "ABNORMAL" if idx == abnormal else "DONE"
            # group 3 short-interval checks into one summary note written later
            if status == "DONE" and i + 2 < len(done) and done[i + 2][0] == idx + 2 and idx + 2 <= 6 and r.random() < 0.3:
                grp = done[i:i + 3]
                if all(j not in refused and j != abnormal for j, _ in grp):
                    s = style()
                    s2 = "{HHMM}" if s.startswith("@") else s  # "@0245, 0300, 0315"
                    txt = pick("neuro_multi").format(t1=fmt(grp[0][1], s), t2=fmt(grp[1][1], s2), t3=fmt(grp[2][1], s2))
                    note(grp[2][1] + timedelta(minutes=r.randint(2, 25)), txt)
                    for _, tt in grp:
                        ev("NEURO", "DONE", tt)
                    i += 3
                    continue
            if status == "REFUSED":
                note(t, pick("neuro_refused"))
            elif status == "ABNORMAL":
                note(t, pick("neuro_abnormal"))
                if r.random() < 0.5:
                    tm = t + timedelta(minutes=r.randint(5, 40))
                    note(tm, sub(r.choice(B["md_done"])))
                    ev("MD", "DONE", tm)
                    md_times.append(tm)
                else:
                    planted["HIR_ESC_MISSING"] = 1
            elif r.random() < 0.5:
                note(t, pick("neuro_single"))
            else:
                note(t + timedelta(minutes=r.randint(10, 90)), pick("neuro_timed").replace("{t}", fmt(t, style())))
            ev("NEURO", status, t)
            if mode == "next_due" and idx + 1 in drop:
                nd = slots[idx + 1][0]
                notes[-1]["text"] += " " + pick("neuro_next_due").replace("{t}", fmt(nd, style()))
                looks.append("next_due")
            i += 1
        if dc_at:
            k, ordered = dc_at
            t = slots[k][0] - timedelta(minutes=r.randint(10, 40))
            note(t, pick("hir_dc_order" if ordered else "hir_dc_no_order"))
            ev("HIR_DC", "ORDER" if ordered else "NO_ORDER", t)

    # every-shift follow-up
    from .engine import shift_windows
    end = t0 + timedelta(hours=81)
    shifts = shift_windows(t0, policy["followup_shifts"], policy["shift_starts"])
    gap = set()
    if r.random() < 0.4:
        gap = set(r.sample(range(len(shifts)), r.randint(1, 2)))
        planted["FOLLOWUP_MISSING"] = len(gap)
    for i, (a, b) in enumerate(shifts):
        t = a + timedelta(minutes=r.randint(30, 440))
        if i in gap:
            if r.random() < 0.6:
                note(t, pick("followup_lookalike"))
                looks.append("followup_lookalike")
            continue
        note(t, sub(pick("followup")))
        ev("FOLLOWUP", "DONE", t)
    # filler
    for _ in range(r.randint(6, 14)):
        note(t0 + timedelta(minutes=r.randint(-600, 80 * 60)), pick("filler"))

    notes.sort(key=lambda n: n["time"])
    for i, n in enumerate(notes):
        n["id"] = f"N{i + 1:03d}"
    case = {"incident": {"id": f"INC-{seed}", "resident": f"R{seed % 997:03d}", "time": t0, "witnessed": witnessed,
                         "head_strike": head}, "notes": notes, "end": end}
    return case, truth, planted, looks
