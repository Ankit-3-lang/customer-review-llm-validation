import sys, re, html, json
import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
from openpyxl.worksheet.datavalidation import DataValidation
from openpyxl.formatting.rule import FormulaRule

src, out_xlsx, out_key = sys.argv[1], sys.argv[2], sys.argv[3]
df = pd.read_json(src, orient="records")

NONE_TOK = {"none mentioned","none","n/a","na","no issues mentioned","no issues","no problems"}
EXAMPLE_ID = "R1EUO62UQI0UL7"   # notebook's test review, used as the worked example

def clean(t):
    t = str(t)
    t = re.sub(r'\\+"', '"', t)
    t = t.replace("<br />", "\n").replace("<br/>", "\n").replace("<br>", "\n")
    t = html.unescape(t)
    t = re.sub(r"\n{3,}", "\n\n", t)
    return t.strip()

def pp_list(x):
    return [str(i).strip() for i in x] if isinstance(x, list) else []

pool = df[df["review_id"] != EXAMPLE_ID]
sample = pool.groupby("star_rating").sample(n=20, random_state=42)
sample = sample.sample(frac=1, random_state=7).reset_index(drop=True)   # shuffle so stars can't be guessed from position
assert len(sample) == 100 and sample["review_id"].is_unique

rows, key = [], []
for i, r in sample.iterrows():
    raw = pp_list(r["pain_points"])
    shown = [p for p in raw if p.lower() not in NONE_TOK]
    rows.append({
        "n": i + 1,
        "product": str(r["product_title"])[:90],
        "review": clean(r["review_body"]),
        "ai_pain": "\n".join("• " + p for p in shown) if shown else "(AI listed no complaints)",
        "ai_none": not shown,
        "review_id": r["review_id"],
    })
    key.append({"n": i + 1, "review_id": r["review_id"], "star_rating": int(r["star_rating"]),
                "ai_sentiment": r["sentiment"], "ai_pain_points_raw": json.dumps(raw),
                "ai_listed_none": not shown,
                "had_none_token": any(p.lower() in NONE_TOK for p in raw)})
pd.DataFrame(key).to_csv(out_key, index=False)

# ---------- workbook ----------
F = "Arial"
wb = Workbook()
ins = wb.active; ins.title = "Instructions"
ws = wb.create_sheet("Review Check")

hdr_fill = PatternFill("solid", fgColor="1F3864")
input_fill = PatternFill("solid", fgColor="FFF2CC")
done_fill = PatternFill("solid", fgColor="E2EFDA")
gray_fill = PatternFill("solid", fgColor="F2F2F2")
thin = Side(style="thin", color="BFBFBF")
box = Border(left=thin, right=thin, top=thin, bottom=thin)
wrap_top = Alignment(wrap_text=True, vertical="top")

# --- Review Check sheet ---
headers = ["#", "Product", "Review (read this)", "Q1. Your sentiment",
           "What the AI said the customer complained about",
           "Q2. Are the AI's complaints correct?", "Q3. Did the AI miss a complaint?",
           "Notes (optional)", "Review ID"]
widths = [5, 22, 70, 16, 32, 20, 18, 26, 17]
for c, (h, w) in enumerate(zip(headers, widths), start=1):
    cell = ws.cell(row=1, column=c, value=h)
    cell.font = Font(name=F, bold=True, color="FFFFFF", size=10)
    cell.fill = hdr_fill; cell.alignment = Alignment(wrap_text=True, vertical="center", horizontal="center")
    cell.border = box
    ws.column_dimensions[cell.column_letter].width = w
ws.row_dimensions[1].height = 45
ws.freeze_panes = "D2"

for r in rows:
    x = r["n"] + 1
    vals = [r["n"], r["product"], r["review"], None, r["ai_pain"],
            "N/A - AI listed none" if r["ai_none"] else None, None, None, r["review_id"]]
    for c, v in enumerate(vals, start=1):
        cell = ws.cell(row=x, column=c, value=v)
        cell.font = Font(name=F, size=10, color="808080" if c == 9 else "000000")
        cell.alignment = wrap_top; cell.border = box
    for c in (4, 6, 7, 8):
        ws.cell(row=x, column=c).fill = input_fill
    ws.cell(row=x, column=5).fill = gray_fill
    # row height: estimate wrapped lines in the review column (~78 chars/line at width 70)
    lines = sum(max(1, -(-len(seg) // 78)) for seg in r["review"].split("\n"))
    pain_lines = r["ai_pain"].count("\n") + 1
    ws.row_dimensions[x].height = min(409, max(45, 13.5 * max(lines, pain_lines * 2) + 6))

last = len(rows) + 1
dv1 = DataValidation(type="list", formula1='"positive,negative,mixed,neutral"', allow_blank=True,
                     showErrorMessage=True, errorTitle="Pick from the list",
                     error="Choose positive, negative, mixed or neutral.")
dv2 = DataValidation(type="list", formula1='"All correct,Some wrong,All wrong,N/A - AI listed none"',
                     allow_blank=True, showErrorMessage=True, errorTitle="Pick from the list",
                     error="Choose one of the options in the list.")
dv3 = DataValidation(type="list", formula1='"Yes,No"', allow_blank=True, showErrorMessage=True,
                     errorTitle="Pick from the list", error="Choose Yes or No.")
for dv, col in ((dv1, "D"), (dv2, "F"), (dv3, "G")):
    ws.add_data_validation(dv); dv.add(f"{col}2:{col}{last}")
for col in ("D", "F", "G"):
    ws.conditional_formatting.add(f"{col}2:{col}{last}",
        FormulaRule(formula=[f'LEN({col}2)>0'], fill=done_fill))

# --- Instructions sheet ---
ins.column_dimensions["A"].width = 30
ins.column_dimensions["B"].width = 95
def put(r, a, b=None, bold=False, size=10, fill=None):
    ca = ins.cell(row=r, column=1, value=a); ca.font = Font(name=F, bold=True if b is not None else bold, size=size)
    ca.alignment = wrap_top
    if b is not None:
        cb = ins.cell(row=r, column=2, value=b); cb.font = Font(name=F, size=size); cb.alignment = wrap_top
        if fill: cb.fill = fill
    if fill: ca.fill = fill

put(1, "AI Review Check: 100 reviews", bold=True, size=14)
put(2, "Goal", "Check whether the AI read these reviews correctly. You answer 3 questions per review; I compare your answers with the AI's and calculate how often it was right.")
put(3, "Time", "About 1 hour. Most reviews take 20–40 seconds. You can stop and come back; just save the file.")
put(5, "HOW TO DO IT", bold=True, size=11)
put(6, "Step 1", "Go to the 'Review Check' tab. Read the review in column C.")
put(7, "Step 2 – Q1 (column D)", "Pick the sentiment YOU think the review has, from the dropdown. Go with your own reading of the text.")
put(8, "Step 3 – Q2 (column F)", "Look at column E (what the AI said the customer complained about). Pick:\n• All correct – every item listed is a real complaint in this review\n• Some wrong – at least one item is not really a complaint, or isn't in the review\n• All wrong – none of the items are real complaints\n• N/A - AI listed none – already filled in where the AI found no complaints (leave it)")
put(9, "Step 4 – Q3 (column G)", "Did the customer complain about something the AI did NOT list? Yes or No. (If the AI listed no complaints but the review has one, answer Yes.)")
put(10, "Step 5", "Optional: add a short note in column H when something is odd (sarcasm, mixed review, off-topic).")
put(11, "Step 6", "When all 100 rows are green, save the file and upload it back to Claude.")
put(13, "SENTIMENT GUIDE", bold=True, size=11)
put(14, "positive", "Mostly happy with the product. Small gripes are fine.")
put(15, "negative", "Mostly unhappy: it failed, disappointed, or they'd return it.")
put(16, "mixed", "Clear good AND clear bad points, neither one dominates.")
put(17, "neutral", "No real opinion: just facts, a question, or about shipping only.")
put(19, "RULES", bold=True, size=11)
put(20, "Don't look things up", "Judge only from the review text. The star rating is hidden on purpose so it doesn't sway you.")
put(21, "Yellow cells", "Yellow cells are the only ones you edit. They turn green when answered.")
put(23, "WORKED EXAMPLE (not part of the 100)", bold=True, size=11)
put(24, "Review", "\"...the remote was super easy to configure but from day one I noticed that the software driven remote was not as intuitive as I'd hoped for and in 2–3 weeks the remote just plain didn't work; it froze up... Eventually it just didn't work AT ALL... Thank GAWD for Amazon's return process.\"")
put(25, "AI's complaints", "• software not intuitive\n• remote froze up\n• stopped working")
put(26, "Q1 answer", "negative   (it failed and they returned it; the easy setup doesn't outweigh that)", fill=input_fill)
put(27, "Q2 answer", "All correct   (all three are real complaints in the text)", fill=input_fill)
put(28, "Q3 answer", "No   (the AI caught every complaint)", fill=input_fill)
put(30, "PROGRESS", bold=True, size=11)
ins.cell(row=31, column=1, value="Q1 answered").font = Font(name=F, bold=True, size=10)
ins.cell(row=31, column=2, value=f"=COUNTA('Review Check'!D2:D{last})&\" of 100\"").font = Font(name=F, size=10)
n_need = sum(not r["ai_none"] for r in rows)
ins.cell(row=32, column=1, value="Q2 answered").font = Font(name=F, bold=True, size=10)
ins.cell(row=32, column=2, value=f"=COUNTIFS('Review Check'!F2:F{last},\"<>\",'Review Check'!F2:F{last},\"<>N/A - AI listed none\")&\" of {n_need}  (the other {100-n_need} are pre-filled N/A)\"").font = Font(name=F, size=10)
ins.cell(row=33, column=1, value="Q3 answered").font = Font(name=F, bold=True, size=10)
ins.cell(row=33, column=2, value=f"=COUNTA('Review Check'!G2:G{last})&\" of 100\"").font = Font(name=F, size=10)
for r in (8, 24, 25):
    ins.row_dimensions[r].height = 75 if r != 25 else 42

for sh in (ws, ins):
    sh.page_setup.orientation = "landscape"
    sh.page_setup.fitToWidth = 1
    sh.page_setup.fitToHeight = 0
    sh.sheet_properties.pageSetUpPr.fitToPage = True
ws.print_title_rows = "1:1"
wb.save(out_xlsx)
print("rows", len(rows), "| AI listed none:", sum(r["ai_none"] for r in rows))
print(pd.DataFrame(key).groupby("star_rating")["ai_sentiment"].value_counts().unstack(fill_value=0))
