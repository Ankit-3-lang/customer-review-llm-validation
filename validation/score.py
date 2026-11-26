"""
Score a hand-labelled sample against the model's own answers.

Reports agreement, Cohen's kappa, a breakdown by star rating, and a test for
whether the model was really reading the review or just echoing the stars.

Usage:
    python validation/score.py labelled.csv answer_key.csv insights.json

See the README for what each input is and how the sample was drawn.
"""

import sys, json, math
import pandas as pd
from sklearn.metrics import cohen_kappa_score

ret = pd.read_csv(sys.argv[1]); key = pd.read_csv(sys.argv[2])
src = pd.read_json(sys.argv[3], orient="records")[["review_id","review_body"]]
ret.columns = ["n","product","review","my_sent","ai_pain","q2","q3","notes","review_id"]
ret["n"] = ret["n"].astype(int)
m = ret.merge(key, on=["n","review_id"], how="inner", validate="1:1")
assert len(m) == 100
done = m[m["my_sent"].notna() & m["q3"].notna() & m["q2"].notna()].copy()
skipped = m[(m["n"] <= done["n"].max()) & ~m["n"].isin(done["n"])]["n"].tolist()
print(f"Completed rows: {len(done)} | skipped inside range: {skipped}")

def wilson(k, n, z=1.96):
    p = k/n; d = 1 + z*z/n
    c = (p + z*z/(2*n))/d; h = z*math.sqrt(p*(1-p)/n + z*z/(4*n*n))/d
    return c-h, c+h

h = done["my_sent"].str.strip().str.lower(); a = done["ai_sentiment"].str.strip().str.lower()
k = (h == a).sum(); n = len(done); lo, hi = wilson(k, n)
print(f"\nSENTIMENT agreement: {k}/{n} = {k/n:.0%}  (95% CI {lo:.0%}–{hi:.0%}),  Cohen's kappa = {cohen_kappa_score(h, a):.2f}")
print(pd.crosstab(h.rename("you"), a.rename("AI"), margins=True))
print("\nAgreement by star rating:")
print(done.assign(agree=(h==a)).groupby("star_rating")["agree"].agg(["sum","count"]))

star_map = done["star_rating"].map({1:"negative",2:"negative",3:"mixed",4:"positive",5:"positive"})
print(f"\nStar-copy test: AI label = star-implied label in {(a==star_map).mean():.0%} of rows; "
      f"your label = star-implied label in {(h==star_map).mean():.0%}")
dis = done[h != a]
print(f"Of {len(dis)} disagreements, AI matched the star-implied label in {(dis['ai_sentiment']==star_map[dis.index]).sum()}")

has = done[done["q2"] != "N/A - AI listed none"]
print(f"\nCOMPLAINTS LISTED BY AI (Q2), n={len(has)}:")
print(has["q2"].value_counts().to_string())
none = done[done["q2"] == "N/A - AI listed none"]
print(f"\nMISSED COMPLAINTS (Q3), n={len(done)}: Yes = {(done['q3']=='Yes').sum()}  "
      f"| among AI-listed-none rows: {(none['q3']=='Yes').sum()}/{len(none)}")
flag = done[(h!=a) | (done["q2"]!="All correct") & (done["q2"]!="N/A - AI listed none") | (done["q3"]=="Yes")]
flag = flag.merge(src, on="review_id", how="left")
out = flag[["n","star_rating","my_sent","ai_sentiment","ai_pain","q2","q3","review_body"]]
out.to_csv("validation/flagged_rows.csv", index=False)
print(f"\nFlagged rows saved: {len(out)}")
