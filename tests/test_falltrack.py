import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from falltrack import engine  # noqa: E402
from falltrack.engine import resolve, shift_windows, times_in  # noqa: E402


def case(notes, witnessed=False, t0="2026-03-04T02:40"):
    return {"incident": {"id": "T", "resident": "R", "time": t0, "witnessed": witnessed, "head_strike": False},
            "end": "2026-03-07T12:00", "notes": [{"id": f"N{i}", "time": t, "text": x} for i, (t, x) in enumerate(notes)]}


def test_times_and_resolution():
    assert times_in(" nv @0255, 0310 / 0325 ") == [(2, 55), (3, 10), (3, 25)]
    assert times_in(" hir 4:12 pm gcs 15 ") == [(16, 12)]
    assert times_in(" bp 128/76 rm 214 ") == []
    # a time later than the entry belongs to the previous day
    assert resolve((23, 50), datetime(2026, 3, 4, 0, 30)) == datetime(2026, 3, 3, 23, 50)


def test_notification_wording():
    st = lambda txt: engine.run(case([("2026-03-04T03:00", txt + " Re: fall.")]))["steps"]["POA"]["status"]
    assert st("Called daughter (POA), no answer, left VM.") == "ATTEMPT_ONLY"
    assert st("POA not yet notified.") == "MISSING"
    assert st("Will call SDM in the morning.") == "MISSING"
    assert st("Spoke with son (POA), aware of fall.") == "MET"
    assert st("Left VM for daughter, then daughter called back and was informed.") == "MET"
    assert st("Resident is own SDM.") == "NOT_REQUIRED"
    assert st("POA was notified of previous fall last month.") == "MISSING"
    # a family call about something else is not a fall notification
    r = engine.run(case([("2026-03-04T03:00", "Daughter called to ask about laundry.")]))
    assert r["steps"]["POA"]["status"] == "MISSING"


def test_hir_slots_next_due_and_refusal():
    notes = [("2026-03-04T02:41", "NV done, PERRLA."), ("2026-03-04T03:30", "NV @0255, 0310 WNL. Next NV due @0325."),
             ("2026-03-04T03:41", "Resident refused neuro vitals.")]
    s = engine.run(case(notes))["steps"]["HIR"]
    by = {x["due"].strftime("%H:%M"): x["status"] for x in s["slots"]}
    assert by["02:40"] == by["02:55"] == by["03:10"] == "MET"
    assert by["03:25"] == "MISSING"            # "next due" is a plan, not a check
    assert by["03:40"] == "REFUSED"            # documented refusal counts
    assert s["status"] == "MISSING_SLOTS"


def test_stop_needs_an_order():
    base = [("2026-03-04T02:41", "NV WNL.")]
    no = engine.run(case(base + [("2026-03-04T02:50", "HIR stopped, resident sleeping.")]))["steps"]["HIR"]
    yes = engine.run(case(base + [("2026-03-04T02:50", "HIR discontinued per Dr Patel order.")]))["steps"]["HIR"]
    assert no["missing"] > 10 and yes["missing"] == 0


def test_form_says_witnessed_but_note_says_found_on_floor():
    c = case([("2026-03-04T02:50", "Witnessed fall. When writer arrived resident was found on floor.")], witnessed=True)
    assert engine.run(c)["steps"]["HIR"]["status"] == "MISSING_SLOTS"
    c = case([("2026-03-04T02:50", "Witnessed by PSW, lowered to floor. Resident denies hitting head.")], witnessed=True)
    assert engine.run(c)["steps"]["HIR"]["status"] == "NOT_REQUIRED"


def test_shifts_and_abnormal_escalation():
    w = shift_windows(datetime(2026, 3, 4, 2, 40), 9, [7, 15, 23])
    assert w[0][0] == datetime(2026, 3, 4, 7) and len(w) == 9 and w[-1][1] == datetime(2026, 3, 7, 7)
    c = case([("2026-03-04T02:41", "NV: GCS 13, newly confused.")])
    assert engine.run(c)["steps"]["HIR_ESC"]["status"] == "ESCALATION_MISSING"
    c = case([("2026-03-04T02:41", "NV: GCS 13, newly confused."), ("2026-03-04T03:00", "Dr Patel notified of fall and GCS change.")])
    assert engine.run(c)["steps"]["HIR_ESC"]["status"] == "MET"
