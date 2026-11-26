# Customer Review Analysis — and a check on whether the AI got it right

What do 30,000 Amazon electronics reviews say about why products disappoint,
and **how much can you trust an AI model to read them for you?**

The second question turned out to be the more interesting one.

---

## The short version

| | |
|---|---|
| **Data** | 29,942 Amazon Electronics reviews, 2008–2015 |
| **Method** | An LLM extracts pain points, positives and sentiment from each review; embeddings + K-Means group them |
| **Run time** | About an hour, 10 requests in parallel |
| **Validation** | 100 reviews hand-labelled blind, then compared with the model |
| **Agreement** | **83%** overall (Cohen's kappa 0.75) — but only **60%** on 3-star reviews |

**The model leaned on the star rating instead of reading the text.** It was
perfect on clear 1- and 5-star reviews and collapsed on ambiguous ones. In 11 of
17 disagreements its label matched what the stars implied rather than what the
customer actually wrote. It never once chose "neutral", and it used "mixed" as a
safe default — only 56% of the reviews it called mixed really were.

That is the finding worth keeping: **an AI reading text is most confident exactly
where it is least reliable.**

## What the reviews said

- **Reliability drew more complaints than any other category** (1,861 mentions),
  led by "stopped working" and "short lifespan".
- **Compatibility was the most negative category**: 89% of mentions were
  complaints, which points at product listings rather than the products.
- Clustering separated a **3,225-review failure cluster** (1.6-star average) from
  a **3,135-review satisfaction cluster** (4.8-star average).
- Four recommendations went into an executive summary, backed by 2008–2015 trend data.

## How the validation worked

The point was to measure the model against a human, not against itself.

1. **Sample.** `validation/build_sheet.py` draws 100 reviews, 20 from each star
   rating, then shuffles them. The star rating and the model's own answer are
   both hidden, so neither can influence the human label.
2. **Label by hand.** An Excel sheet with dropdowns, filled in blind: sentiment,
   whether the model's complaint list was right, and whether it missed anything.
3. **Score.** `validation/score.py` reports agreement, Cohen's kappa, a breakdown
   by star rating, and every disagreement for reading afterwards.

Cohen's kappa matters here because raw agreement flatters any task where one
answer dominates. Kappa corrects for the agreement you would get by chance.

### What the errors looked like

- **Sarcasm.** *"They won't disappoint you. So long as you have low standards."*
  The model read it as positive.
- **Fragments.** The prompt asked for complaints in "2–3 words", which chopped
  real issues into meaningless pieces like "extended use" and "trial error".
- **Instructions ignored.** Told to return an empty list when there were no
  complaints, the model wrote "none mentioned" 1,537 times instead — and those
  strings were being counted as complaints.
- **Same issue, many phrasings.** "stopped working", "did not work", "does not
  work", "broke quickly" and "failed quickly" are one problem split five ways;
  together they outnumber the apparent top complaint two to one.

## Running it

```bash
pip install -r requirements.txt
cp .env.example .env        # then add your own OPENROUTER_API_KEY
jupyter notebook notebooks/Customer_Sentiment_Project.ipynb
```

The API key is read from the environment, never hardcoded. `.env` is gitignored.

## Limits

- The reviews are 2008–2015 Amazon data. The products are not current; the
  method is the point.
- 100 labelled reviews gives roughly a ±7 point margin on the 83% figure.
- One human labeller, so there is no inter-rater check on the human side either.
- Interactive Plotly charts are stripped from the committed notebook — GitHub
  cannot render them. Run it locally to see them.
