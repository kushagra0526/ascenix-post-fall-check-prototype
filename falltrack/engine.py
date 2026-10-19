"""Post-fall follow-up check: read free-text progress notes into dated events, then score them against the home's policy.

read_notes(case)  -> events (kind, time, status, quote, note) + ignored clauses with the reason
score(case, events, policy) -> one result per policy step (MET / LATE / MISSING / ATTEMPT_ONLY / MISSING_SLOTS / ...)
"""
import re
from datetime import datetime, timedelta

from .policy import DEFAULT_POLICY

COMPLIANT = {"MET", "NOT_REQUIRED"}

# ---------------------------------------------------------------- lexicons
W = r"(?:\W+\w+){0,3}?\W+"  # up to 3 words in between
MD = r"\b(?:dr|doctor|md|physician|np|nurse practitioner|on[- ]?call|attending|gp|most responsible physician|mrp)\b"
POA = (r"\b(?:poa|sdm|substitute decision[- ]?maker|family|daughter|son|wife|husband|spouse|partner|niece|nephew|sister|"
       r"brother|next of kin|nok|guardian|granddaughter|grandson|daughter-in-law|son-in-law)\b")
NOTIFY = (r"\b(?:notified|informed|made aware|aware|updated|spoke(?: with| to)?|spoken (?:with|to)|discussed with|reached|"
          r"contacted|told|called back|returned (?:the |my )?call|called|phoned|telephoned|rang|advised)\b")
ATTEMPT = (r"(?:no answer|not answer|did not pick up|didn't pick up|left (?:a |an )?(?:vm|voicemail|voice mail|message|msg)|"
           r"\bvm\b|voicemail|voice mail|message left|msg left|unable to (?:reach|contact|get (?:a )?hold of|speak)|"
           r"(?:could not|couldn't|cannot|can't) (?:reach|contact|get through)|not reachable|unreachable|line busy|"
           r"no response|no reply|unanswered|awaiting (?:a )?(?:call ?back|return call|response|reply)|went to voicemail)")
FAX = r"\b(?:faxed|fax sent|sent (?:a )?fax|via fax|by fax|paged|page sent|texted|sent (?:a )?(?:message|msg))\b"
NEG = r"\b(?:not|never|no one|nobody|yet to|neither|nor)\b|n't\b"
PLAN = (r"\b(?:will|to be|plan(?:ning|ned|s)? to|to notify|to call|to inform|pending|awaiting|tomorrow|"
        r"in (?:the )?am\b|in (?:the )?morning|next shift|later|once|when|scheduled|needs? to|should|must)\b")
PAST = (r"\b(?:previous|prior|last (?:fall|week|month|year|time)|earlier fall|hx of|history of|"
        r"(?:\d+|a|one|two|three|several) (?:days?|weeks?|months?|years?) ago|"
        r"in (?:january|february|march|april|may|june|july|august|september|october|november|december))\b")

ASSESS = (r"(?:post[- ]?fall (?:assessment|assess\b|huddle|eval|evaluation|analysis)|\bpfa\b|morse(?: fall)?(?: scale)?|"
          r"scott fall|fall risk (?:assessment|screen|tool|score)|falls? assessment)")
DONE = (r"\b(?:completed?|done|conducted|performed|finished|updated|reviewed|revised|amended|added|initiated|"
        r"implemented|in place|scored?|filled(?: out| in)?|carried out|held|documented)\b|\b\d{1,3}\b")
CAREPLAN = r"(?:care ?plan|plan of care|\bpoc\b|kardex|\bcp\b)"
FOLLOWUP = (r"(?:post[- ]?fall|fall f/?u|f/?u (?:re:? |for |on )?(?:the |recent )?fall|follow[- ]?up (?:re:? |for |on |to |after )?"
            r"(?:the |recent |yesterday's |last night's )?fall|(?:after|following|since) (?:the |recent |yesterday's |last night's )?fall|"
            r"day \d (?:of|post)|72[- ]?h(?:ou)?r)")
NEURO = (r"(?:neuro(?:logical)?(?:[- ]?(?:vitals?|vs|checks?|signs|obs|observations|assessment))?|\bnvs?\b|\bhir\b|"
         r"head injury routine|perrla|pupils?|\bgcs\b|glasgow)")
NEURO_PLAN = r"\b(?:next|due|to continue|continue|continuing|to be done|scheduled|will)\b"
NEURO_NEG = (r"\b(?:not done|not completed|not taken|not obtained|missed|omitted|held|not checked|"
             r"unable to (?:complete|obtain|do|assess))\b")
REFUSED = (r"\b(?:refused|refuses|refusing|declined|declines|would not allow|wouldn't allow|did not allow|didn't allow|"
           r"resisted|resistive|uncooperative|not cooperative|pushed (?:staff|writer|nurse|rn|rpn) away|swatted)\b")
ABNORMAL = (r"(?:gcs\s*(?:of\s*|=\s*|:\s*)?(?:1[0-4]|[3-9])\b|pupils? (?:unequal|sluggish|non[- ]?reactive|fixed|dilated)|"
            r"unequal pupils|new(?:ly)? (?:confus|letharg|drows)|(?:more|increased|increasingly) (?:confused|lethargic|drowsy)|"
            r"vomit|emesis|slurred|new weakness|decreased (?:loc|level of consciousness)|difficult to rouse|hard to rouse)")
HIR_DC = (r"(?:hir|head injury routine|neuro(?:[- ]?(?:vitals?|checks?|vs))?|nvs?)\s*(?:was |were |is |are )?"
          r"(?:d/c(?:'?d)?|dc'?d|discontinued|stopped|ceased|ended|no longer required)")
ORDER = r"\b(?:per|order|ordered|as per|by|orders)\b" + W + r"?(?:dr|md|np|physician|doctor|nurse practitioner)\b"
SELF_POA = (r"(?:self[- ]?poa|own (?:poa|sdm|substitute decision[- ]?maker|decision[- ]?maker)|"
            r"capable (?:of making|to make) (?:own|their own|his own|her own) (?:care |treatment )?decisions)")
HEAD_CUE = (r"(?:found (?:lying |sitting |kneeling |laying )?(?:on|beside|next to) (?:the )?floor|found on floor|unwitnessed|"
            r"not witnessed|no witness|hit (?:his|her|their|the) head|struck (?:his|her|their|the) head|head strike|"
            r"bump(?:ed)? (?:on|to) (?:the |his |her |their )?head|(?:hematoma|bump|lac|laceration|goose egg) (?:on|to) (?:the |his |her |their )?"
            r"(?:head|forehead|scalp|occiput)|(?:forehead|scalp) (?:bump|lac|laceration|hematoma))")
CUE_NEG = r"\b(?:no|not|denies|denied|without|didn't|did not|never|nil)\b" + r"(?:\W+\w+){0,3}?\W*$"


# ---------------------------------------------------------------- times
TIME_RX = [
    re.compile(r"\b(\d{1,2}):(\d{2})\s*(am|pm)?\b"),
    re.compile(r"(?:@|\bat)\s*(\d{2})(\d{2})\b"),
    re.compile(r"\b(\d{2})(\d{2})\s*(?:h|hr|hrs)\b"),
    re.compile(r"\b(\d{1,2})\s*(am|pm)\b"),
]
LIST_RX = re.compile(r"(?:,|\band\b|&)\s*@?\s*(\d{2})(\d{2})\b")


def _hm(m):
    g = [x for x in m.groups() if x is not None]
    if len(g) >= 2 and g[1] in ("am", "pm"):
        h, mi, ap = int(g[0]), 0, g[1]
    else:
        h, mi = int(g[0]), int(g[1])
        ap = g[2] if len(g) > 2 else None
    if ap == "pm" and h < 12:
        h += 12
    if ap == "am" and h == 12:
        h = 0
    return (h, mi) if h < 24 and mi < 60 else None


def times_in(text):
    """Clock times written in a clause, in order of appearance."""
    found = []
    for rx in TIME_RX:
        for m in rx.finditer(text):
            hm = _hm(m)
            if hm:
                found.append((m.start(), hm))
    if found:
        for m in LIST_RX.finditer(text):
            h, mi = int(m.group(1)), int(m.group(2))
            if h < 24 and mi < 60 and all(p != m.start(1) for p, _ in found):
                found.append((m.start(1), (h, mi)))
    seen, out = set(), []
    for p, hm in sorted(found):
        if p not in seen:
            seen.add(p)
            out.append(hm)
    return out


def resolve(hm, ref):
    """Latest datetime with this clock time at or before the note's entry time (+5 min slack)."""
    t = ref.replace(hour=hm[0], minute=hm[1], second=0, microsecond=0)
    return t - timedelta(days=1) if t > ref + timedelta(minutes=5) else t


# ---------------------------------------------------------------- reading
def normalise(text):
    t = " " + text.lower() + " "
    t = re.sub(r"\bdr\.", "dr", t)
    t = re.sub(r"\b([ap])\.m\.", r"\1m", t)
    t = re.sub(r"\bw/", "with ", t)
    t = t.replace("’", "'")
    return t


def sentences(t):
    return [s for s in re.split(r"(?<=[.!?])\s+|\n+", t) if s.strip()]


def clauses(s):
    return [c for c in re.split(r";|,\s*(?=[a-z])(?!at\s*\d)|\s-\s(?=[a-z])|\bbut\b|\bthen\b|\bhowever\b", s) if c.strip()]


def scoped(c, verb_rx, marker_rx):
    """For each verb hit: is a marker within 3 words before it?  -> list of booleans."""
    out = []
    for m in re.finditer(verb_rx, c):
        before = c[max(0, m.start() - 40):m.start()]
        words = re.findall(r"[\w']+", before)[-4:]
        out.append(bool(re.search(marker_rx, " ".join(words) + " ")))
    return out


def notify_status(c, fax_counts):
    if re.search(ATTEMPT, c):
        return "ATTEMPT"
    if re.search(FAX, c):
        return "DONE" if fax_counts else "ATTEMPT"
    if re.search(r"notification (?:was |is )?(?:not|never) (?:done|made|completed|sent|given)", c):
        return "NEG"
    hits = list(re.finditer(NOTIFY, c))
    if not hits:
        return "PLAN" if re.search(r"\b(?:notify|inform|call|update|contact|phone)\b", c) else None
    neg, plan = scoped(c, NOTIFY, NEG), scoped(c, NOTIFY, PLAN)
    if any(not n and not p for n, p in zip(neg, plan)):
        return "DONE"
    return "NEG" if any(neg) else "PLAN"


def generic_status(c):
    hits = list(re.finditer(DONE, c))
    if not hits:
        return "PLAN" if re.search(PLAN, c) else None
    neg, plan = scoped(c, DONE, NEG), scoped(c, DONE, PLAN)
    if re.search(r"\b(?:not yet|yet to|outstanding|incomplete|not (?:been )?(?:done|completed))\b", c):
        return "NEG"
    if any(not n and not p for n, p in zip(neg, plan)) and not re.search(r"\b(?:to be|will|needs? to|due)\b", c):
        return "DONE"
    return "NEG" if any(neg) else "PLAN"


def read_notes(case, policy=DEFAULT_POLICY):
    events, ignored = [], []
    t0 = parse(case["incident"]["time"])
    for note in case["notes"]:
        entry = parse(note["time"])
        if entry < t0 - timedelta(minutes=10):
            continue
        text = normalise(note["text"])
        eff = entry
        m = re.match(r"\s*(?:late entry|le)\b\s*(?:for|re:?|-|:)?\s*(?:at\s*)?(?:@\s*)?((?:\d{1,2}:\d{2}|\d{4})\s*(?:am|pm|h|hrs?)?)", text)
        if m:
            ts = times_in(" at " + m.group(1).replace(":", "") if ":" not in m.group(1) else m.group(1))
            if ts:
                eff = resolve(ts[0], entry)
            text = text[m.end():]

        topic = re.search(r"\b(?:falls?|fell|floor|incident|lowered|slid|above|event|injur\w*|neuro|nv|hir|gcs)\b", text)

        def ev(kind, status, c, when=None):
            events.append({"kind": kind, "status": status, "time": when or eff, "quote": c.strip(), "note": note["id"]})

        for s in sentences(text):
            party, per_party = set(), {}
            s_past = bool(re.search(PAST, s))
            s_neuro = False
            for c in clauses(s):
                ts = [resolve(hm, entry) for hm in times_in(c)]
                when = ts[0] if ts else None
                past = bool(re.search(PAST, c))
                # who is being notified
                here = {p for p, rx in (("MD", MD), ("POA", POA)) if re.search(rx, c)}
                if re.search(SELF_POA, c):
                    ev("SELF_POA", "DONE", c)
                    here.discard("POA")
                if here:
                    party = here
                if party and (re.search(NOTIFY, c) or re.search(ATTEMPT, c) or re.search(FAX, c)
                              or re.search(r"\b(?:notify|inform|call|update|contact)\b", c)):
                    st = "PAST" if past else notify_status(c, policy["fax_counts_as_md"])
                    for p in party:
                        if st:
                            per_party.setdefault(p, []).append((st, c, when))
                # head cue
                for m in re.finditer(HEAD_CUE, c):
                    if not re.search(CUE_NEG, c[:m.start()]) and not past:
                        ev("HEAD_CUE", "DONE", c)
                        break
                # discontinue HIR
                if re.search(HIR_DC, c):
                    ordered = re.search(ORDER, c) or re.search(ORDER, s)
                    ev("HIR_DC", "ORDER" if ordered else "NO_ORDER", c, when)
                    continue
                # neuro checks
                if re.search(NEURO, c) and not past:
                    if re.search(REFUSED, c):
                        st = "REFUSED"
                    elif re.search(NEURO_NEG, c) or re.search(r"\bnot\b" + W + r"?(?:done|completed|taken|checked)", c):
                        st = None
                        ignored.append((note["id"], c.strip(), "neuro check not done"))
                    elif re.search(NEURO_PLAN, c) and not re.search(r"\b(?:wnl|perrla|gcs\s*\d|equal|reactive|stable|done|completed|obtained|taken)\b", c):
                        st = None
                        ignored.append((note["id"], c.strip(), "a plan / next due time, not a check"))
                    else:
                        ab = [m for m in re.finditer(ABNORMAL, c) if not re.search(r"\b(?:no|denies|without|nil|not)\b\W+(?:\w+\W+)?$", c[:m.start()])]
                        st = "ABNORMAL" if ab else "DONE"
                    if st and (ts or not s_neuro):  # an untimed finding after timed checks belongs to them
                        for t in (ts or [eff]):
                            ev("NEURO", st, c, t)
                    s_neuro = s_neuro or bool(st)
                elif re.search(ABNORMAL, c) and not past and not s_neuro and not re.search(r"\b(?:no|denies|without|nil|not)\b\W+(?:\w+\W+)?" + ABNORMAL, c):
                    ev("NEURO", "ABNORMAL", c, when)
                # assessment, care plan, follow-up
                assess = re.search(ASSESS, c)
                if assess:
                    st = "PAST" if past else generic_status(c)
                    if st == "DONE":
                        ev("ASSESS", "DONE", c)
                    elif st:
                        ignored.append((note["id"], c.strip(), f"assessment {st.lower()}"))
                if re.search(CAREPLAN, c):
                    st = "PAST" if past else generic_status(c)
                    if st == "DONE":
                        ev("CAREPLAN", "DONE", c)
                    elif st:
                        ignored.append((note["id"], c.strip(), f"care plan {st.lower()}"))
                if re.search(FOLLOWUP, s) and not s_past and not re.search(ASSESS, s) and not re.search(r"\b(?:will|to be|next shift|plan to)\b" + W + r"?(?:monitor|follow|assess|check)", s):
                    if not any(e["kind"] == "FOLLOWUP" and e["note"] == note["id"] and e["time"] == eff for e in events):
                        ev("FOLLOWUP", "DONE", s)
            for p, sts in per_party.items():
                real = [x for x in sts if x[0] in ("DONE", "ATTEMPT", "NEG")]
                st, c, when = (real or sts)[-1]
                if st == "DONE" and not topic:
                    ignored.append((note["id"], c.strip(), f"{p} contacted, but the note is not about the fall"))
                elif st in ("DONE", "ATTEMPT"):
                    events.append({"kind": p, "status": st, "time": when or eff, "quote": c.strip(), "note": note["id"]})
                else:
                    ignored.append((note["id"], c.strip(), f"{p} {st.lower()}"))
    return events, ignored


# ---------------------------------------------------------------- scoring
def parse(s):
    return s if isinstance(s, datetime) else datetime.fromisoformat(s)


def shift_windows(t0, n, starts):
    def start_of(t):
        cands = [t.replace(hour=h, minute=0, second=0, microsecond=0) - timedelta(days=d) for d in (0, 1) for h in starts]
        return max(c for c in cands if c <= t)
    s = start_of(t0)
    out = []
    for _ in range(n + 1):
        nxt = min(c for c in (s.replace(hour=h, minute=0) + timedelta(days=d) for d in (0, 1) for h in starts) if c > s)
        out.append((s, nxt))
        s = nxt
    return out[1:]


def _timed(kind, evs, t0, hours, attempt_ok=True):
    done = sorted((e for e in evs if e["kind"] == kind and e["status"] == "DONE" and e["time"] >= t0 - timedelta(minutes=10)),
                  key=lambda e: e["time"])
    if done:
        e = done[0]
        late = e["time"] > t0 + timedelta(hours=hours)
        return {"status": "LATE" if late else "MET", "at": e["time"], "evidence": e}
    att = [e for e in evs if e["kind"] == kind and e["status"] == "ATTEMPT"]
    if att and attempt_ok:
        return {"status": "ATTEMPT_ONLY", "attempts": len(att), "evidence": att[-1]}
    return {"status": "MISSING"}


def score(case, events, policy=DEFAULT_POLICY):
    inc = case["incident"]
    t0 = parse(inc["time"])
    end = parse(case["end"])
    res = {}
    res["ASSESS"] = _timed("ASSESS", events, t0, policy["assess_within_h"])
    res["MD"] = _timed("MD", events, t0, policy["md_within_h"])
    self_poa = [e for e in events if e["kind"] == "SELF_POA"]
    res["POA"] = ({"status": "NOT_REQUIRED", "reason": "resident is own SDM", "evidence": self_poa[0]} if self_poa
                  else _timed("POA", events, t0, policy["poa_within_h"]))
    cues = [e for e in events if e["kind"] == "HEAD_CUE"]
    required = (not inc["witnessed"]) or inc["head_strike"] or bool(cues)
    if not required:
        res["HIR"] = {"status": "NOT_REQUIRED", "reason": "witnessed, no head strike"}
        res["HIR_ESC"] = {"status": "NOT_REQUIRED"}
    else:
        why = ("unwitnessed" if not inc["witnessed"] else "head strike" if inc["head_strike"]
               else "incident form says witnessed, no head strike, but a note says: " + cues[0]["quote"])
        dc = sorted((e for e in events if e["kind"] == "HIR_DC" and e["status"] == "ORDER"), key=lambda e: e["time"])
        stop = dc[0]["time"] if dc else None
        checks = sorted((e for e in events if e["kind"] == "NEURO" and e["time"] >= t0 - timedelta(minutes=10)),
                        key=lambda e: e["time"])
        used, slots = set(), []
        for off, tol in policy["hir_slots"]:
            due = t0 + timedelta(minutes=off)
            if due > end:
                break
            if stop and due > stop:
                slots.append({"due": due, "status": "STOPPED_BY_ORDER"})
                continue
            best = None
            for i, e in enumerate(checks):
                d = abs((e["time"] - due).total_seconds()) / 60
                if i not in used and d <= tol and (best is None or d < best[1]):
                    best = (i, d)
            if best:
                used.add(best[0])
                e = checks[best[0]]
                slots.append({"due": due, "status": "REFUSED" if e["status"] == "REFUSED" else "MET", "evidence": e})
            else:
                slots.append({"due": due, "status": "MISSING"})
        missing = [s for s in slots if s["status"] == "MISSING"]
        nodc = [e for e in events if e["kind"] == "HIR_DC" and e["status"] == "NO_ORDER"]
        res["HIR"] = {"status": "MISSING_SLOTS" if missing else "MET", "why_required": why, "slots": slots,
                      "missing": len(missing), "stopped_without_order": nodc[:1]}
        esc = []
        for e in checks:
            if e["status"] == "ABNORMAL":
                ok = any(m["kind"] == "MD" and m["status"] == "DONE"
                         and e["time"] - timedelta(minutes=5) <= m["time"] <= e["time"] + timedelta(minutes=policy["md_after_abnormal_min"])
                         for m in events)
                if not ok:
                    esc.append(e)
        abn = any(e["status"] == "ABNORMAL" for e in checks)
        res["HIR_ESC"] = ({"status": "NOT_REQUIRED"} if not abn else
                          {"status": "ESCALATION_MISSING", "evidence": esc[0]} if esc else {"status": "MET"})
    shifts = [w for w in shift_windows(t0, policy["followup_shifts"], policy["shift_starts"]) if w[1] <= end]
    fus = [e for e in events if e["kind"] == "FOLLOWUP"]
    miss = [w for w in shifts if not any(w[0] <= e["time"] < w[1] for e in fus)]
    res["FOLLOWUP"] = {"status": "MISSING_SHIFTS" if miss else "MET", "shifts": len(shifts), "missing": miss}
    res["CAREPLAN"] = _timed("CAREPLAN", events, t0, policy["careplan_within_h"])
    for k, r in res.items():
        r["policy"] = policy["lines"][k]
    return res


def run(case, policy=DEFAULT_POLICY):
    events, ignored = read_notes(case, policy)
    return {"steps": score(case, events, policy), "events": events, "ignored": ignored}
