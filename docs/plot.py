"""Chart for the README from out/heldout_first_run.json and out/heldout_after_fix.json."""
import json
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

a, b = json.load(open("out/heldout_first_run.json")), json.load(open("out/heldout_after_fix.json"))
rows = [("keyword check", a["keyword"]), ("keyword, skip notes\nwith not/no/will", a["keyword_skip_negation_words"]),
        ("checker, first run", a["checker"]), ("checker, after\ndisclosed fixes", b["checker"])]
fig, ax = plt.subplots(1, 2, figsize=(11, 4.2))
for i, (key, title) in enumerate([("gaps_shown_compliant", f"Real gaps shown as compliant (of {a['gaps_total']})"),
                                  ("false_flags", f"Compliant steps flagged (of {a['compliant_total']})")]):
    v = [r[key] for _, r in rows]
    bars = ax[i].bar(range(4), v, color=["#c0504d", "#d99694", "#4f81bd", "#9bbb59"])
    ax[i].set_xticks(range(4), [n for n, _ in rows], fontsize=8)
    ax[i].set_title(title, fontsize=10)
    for bar, x in zip(bars, v):
        ax[i].text(bar.get_x() + bar.get_width() / 2, x, str(x), ha="center", va="bottom", fontsize=9)
fig.suptitle(f"400 held-out synthetic falls, unseen note wording ({a['decisions']} policy-step decisions)", fontsize=11)
fig.tight_layout()
fig.savefig("docs/result.png", dpi=130)
