# Headline Sentiment Annotation Guide

This guide defines the standardized methodology, label definitions, decision rules, and edge-case protocols for human annotation of news headlines in the **News Sentiment Analyzer** project.

---

## 1. Objective and Scope

The goal of this annotation task is to establish an in-domain ground-truth benchmark to evaluate sentiment models (VADER lexicon baseline, tweet-trained RoBERTa, and domain-specific FinBERT) on real-world news headlines.

Annotators classify headlines into one of four mutually exclusive categories:
- **`positive`**
- **`neutral`**
- **`negative`**
- **`skip`**

> [!IMPORTANT]
> **Strict Neutrality**: Annotators must evaluate the sentiment conveyed by the text itself, not their personal emotional reaction, political perspective, or investment portfolio. Do not look up model predictions or pre-fill responses.

---

## 2. Operational Label Definitions

### `positive`
The headline conveys a favorable outcome, growth, progress, success, optimism, or recovery.
- **Key Indicators**: Growth, surges, record profits, breakthroughs, approval, outperformance, peace agreements, rally, dividend hike, upgrades.
- *Examples*:
  - *"Tech giant reports record quarterly profits beating Wall Street targets"*
  - *"FDA grants fast-track approval for promising cancer therapy"*
  - *"Unemployment falls to historic 50-year low as hiring rebounds"*

### `neutral`
The headline reports objective facts, routine updates, scheduled events, regulatory procedures, or balanced statements with no discernable affective valence or directional slant.
- **Key Indicators**: Statements of fact, scheduled meetings, monetary policy announcements without evaluative adjectives, statistical data releases, appointments.
- *Examples*:
  - *"Federal Reserve convenes for two-day monetary policy meeting"*
  - *"Treasury issues $45 billion in 10-year benchmark notes"*
  - *"Ministry publishes monthly trade and export statistics for September"*

### `negative`
The headline conveys an unfavorable outcome, decline, crisis, conflict, legal trouble, disaster, failure, or controversy.
- **Key Indicators**: Plunges, losses, layoffs, fraud, indictment, recession, recall, default, strike, sanctions, war, crash.
- *Examples*:
  - *"Automaker issues urgent recall of 200,000 vehicles over brake failure"*
  - *"Retail sales tumble sharply amid persistent inflation pressures"*
  - *"Regulators open antitrust investigation into tech merger"*

### `skip`
The item cannot or should not be reliably annotated due to data anomalies.
- **Criteria**:
  - Non-English headlines.
  - Incomplete or severely truncated strings (e.g. ending abruptly mid-word).
  - Garbled character encodings or HTML artifact gibberish.
  - Pure navigation boilerplate (e.g. *"Click here to subscribe"*, *"Page not found"*).

---

## 3. Decision Protocols for Edge Cases

### 3.1 Neutral Reporting of Negative Events (Factual Reporting vs Editorial Slant)
A frequent point of divergence between rule-based lexicons (like VADER) and human annotators is how factual reporting of adverse events is framed.

- **Factual, Matter-of-Fact Reporting**: If a headline objectively reports a tragedy, crime, or natural phenomenon without sensationalism or editorializing, assess whether the core event is inherently catastrophic:
  - *"Earthquake magnitude 5.2 recorded off coastal province; no casualties reported"* $\rightarrow$ **`neutral`** (factual seismic event, explicit absence of harm).
  - *"Earthquake destroys 40 homes and kills 12 in coastal province"* $\rightarrow$ **`negative`** (human casualty and destruction make the underlying reality inherently adverse).
  - *"Central bank raises benchmark interest rate by 25 basis points"* $\rightarrow$ **`neutral`** (procedural monetary decision).
  - *"Interest rate hike triggers immediate market selloff and mortgage distress"* $\rightarrow$ **`negative`** (explicit adverse market impact).

### 3.2 Corporate Actions with Dual Perspective (Layoffs, Cost-Cutting)
Corporate restructuring (e.g., job cuts) often boosts shareholder value while harming employees:
- **Rule**: Default to broad socioeconomic valence unless the headline explicitly centers equity market celebration.
  - *"Company to lay off 1,200 workers in restructuring push"* $\rightarrow$ **`negative`**.
  - *"Shares surge 8% as investors cheer company's aggressive cost cuts"* $\rightarrow$ **`positive`** (headline explicitly focuses on investor cheer and surging shares).

### 3.3 Negations and Diminished Polarity
Watch for syntactic negations that invert or neutralize polarized words:
- *"Economy avoids anticipated recession in third quarter"* $\rightarrow$ **`positive`** (averting a negative outcome is favorable).
- *"New smartphone fails to impress reviewers"* $\rightarrow$ **`negative`** (failed expectation).
- *"Company denies allegations of accounting irregularities"* $\rightarrow$ **`negative`** (association with allegations and irregularities carries negative controversy).

### 3.4 Mixed Sentiment Headlines
When a headline juxtaposes positive and negative clauses:
- *"Revenue jumps 15%, but profit misses expectations on higher costs"*
- **Rule**: If one aspect represents the primary headline consequence, follow the governing clause. If the clauses are evenly counterbalanced with contrasting conjunctions (*but*, *yet*, *despite*), evaluate the net orientation:
  - If conflicting and unresolved $\rightarrow$ **`neutral`** (balanced).
  - If one outcome dominates (e.g., *"Stocks finish higher despite early morning slump"*) $\rightarrow$ **`positive`** (final net result).

### 3.5 Ambiguity and Clickbait
- If a headline asks an open rhetorical question (*"Will oil prices crash this winter?"*):
  - Do not assume the answer. Unless explicit sentiment is asserted, classify speculative questions as **`neutral`**.

---

## 4. Annotator Workflow & CLI Usage

### Step 1: Launch the Interactive Labeling Tool
To begin or resume labeling unannotated headlines:
```bash
# Label using default annotator id ('annotator_1')
newsent label

# Label as a specific annotator with a target limit
newsent label --annotator dhrupal --limit 300

# Label with stratified sampling across topics and providers
newsent label --annotator reviewer_2 --stratified --limit 100
```

### Step 2: Keyboard Commands in the Tool
For each headline presented:
- `p` or `1`: Assign **`positive`**
- `n` or `2`: Assign **`neutral`**
- `e` or `3`: Assign **`negative`**
- `s` or `4`: **`skip`**
- `q`: Save progress and safely quit the session
- Optional notes can be entered when prompted to capture ambiguity rationale.

### Step 3: Compute Inter-Annotator Agreement (Cohen's Kappa)
Once two annotators have labeled an overlapping set of headlines:
```bash
newsent label-agreement --annotator1 dhrupal --annotator2 reviewer_2
```
This calculates:
- Sample size of overlapping annotated items (excluding skipped headlines).
- Raw percentage agreement ($p_o$).
- Cohen's kappa coefficient ($\kappa = \frac{p_o - p_e}{1 - p_e}$).
- Full inter-annotator confusion matrix.
- Detailed list of specific headlines where annotators disagreed.

### Interpretation of Cohen's Kappa ($\kappa$)
- $\kappa < 0.20$: Slight agreement
- $0.21 \le \kappa \le 0.40$: Fair agreement
- $0.41 \le \kappa \le 0.60$: Moderate agreement
- $0.61 \le \kappa \le 0.80$: Substantial agreement
- $0.81 \le \kappa \le 1.00$: Near-perfect agreement
Target threshold for publication-quality sentiment benchmarks is $\kappa \ge 0.65$.
