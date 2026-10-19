"""A home's post-fall policy as data. Every number here is a home setting, not a regulation."""

DEFAULT_POLICY = {
    "name": "Sample home post-fall policy (synthetic)",
    "assess_within_h": 24,       # post-fall assessment with a falls instrument
    "md_within_h": 12,           # physician / NP notified
    "poa_within_h": 12,          # POA / SDM notified (Self-POA = not required)
    "careplan_within_h": 72,     # care plan reviewed / interventions updated
    "followup_shifts": 9,        # a post-fall note every shift for 72 h, from the next shift
    "shift_starts": [7, 15, 23],
    "md_after_abnormal_min": 60, # abnormal neuro finding -> MD notified within this
    "fax_counts_as_md": False,   # a fax / message left is an attempt, not a notification
    # head injury routine: (minutes after the fall, +/- tolerance minutes)
    "hir_slots": [(0, 5), (15, 5), (30, 5), (45, 5), (60, 5),
                  (90, 10), (120, 10),
                  (180, 15), (240, 15), (300, 15), (360, 15),
                  (600, 30), (840, 30), (1080, 30), (1320, 30)],
    "lines": {
        "ASSESS": "§2.1 Post-fall assessment completed within 24 h",
        "MD": "§2.2 Physician/NP notified within 12 h",
        "POA": "§2.3 POA/SDM notified within 12 h (not required if resident is own SDM)",
        "HIR": "§3 Head injury routine for unwitnessed falls or head strike: q15min x1h, q30min x1h, q1h x4h, q4h to 24h; "
               "refusal documented counts; stop only on a physician/NP order",
        "HIR_ESC": "§3.4 Abnormal neuro finding -> physician/NP notified within 60 min",
        "FOLLOWUP": "§4 Post-fall follow-up note every shift for 72 h",
        "CAREPLAN": "§5 Care plan reviewed within 72 h",
    },
}
