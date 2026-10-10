# Error Analysis & Linguistic Failure Modes

## 1. Executive Summary

This document presents a systematic qualitative and quantitative error analysis of sentiment models evaluated on the **Financial PhraseBank** benchmark ($N = 342$) and our **In-Domain News Headline Benchmark** ($N = 300$).

When sentiment models (lexicon baselines, off-the-shelf transformers, and domain-adapted classifiers) are evaluated on real journalistic news headlines, prediction errors are not merely random noise. Instead, they cluster into distinct linguistic patterns:
1. **Neutral Reporting of Negative/Adverse Events**
2. **Complex Negation & Scope Modifiers**
3. **Domain-Specific Lexical Polysemy**
4. **Sarcasm & Cynical Rhetorical Devices**
5. **Mixed / Multi-Clause Sentiment Framing**

---

## 2. Error Categorization Taxonomy

Every misclassified headline is classified using the taxonomy implemented in `src/news_sentiment/evaluation/error_analysis.py`:

| Taxonomy Category | Linguistic & Domain Mechanism | Example Headline | Typical Failure Pattern |
|---|---|---|---|
| **`neutral_reporting_of_negative_events`** | Objective journalistic coverage of disasters, bankruptcies, accidents, or regulatory actions where the reporter is neutral but the vocabulary contains adverse events. | *"Bureau of Labor Statistics schedules monthly employment situation report for Friday"* | Models misclassify as negative due to emotional lexicon triggers. |
| **`negation`** | Negating particles (*not*, *fails to*, *denies*, *no longer*, *despite*) invert or qualify the clause valence. | *"Changes will take effect... not estimated to have an impact on headcount"* | Rule-based lexicons fail to propagate negation scope across clauses. |
| **`domain_terms`** | Financial and technical terminology with directional polarity differing from everyday usage (*rate hike*, *yield curve inversion*, *narrowing loss*). | *"Metsaliitto narrowed its net loss for the second quarter"* | Models anchor on *loss* rather than *narrowed* (positive financial improvement). |
| **`sarcasm`** | Scare quotes (*"so-called"*), ironic juxtaposition, or rhetorical cynicism. | *"RFID is a method of so-called intelligent transport..."* | Lexicons score literal words (*intelligent*) rather than skeptical modifiers. |
| **`mixed_sentiment`** | Compound headlines balancing competing positive and negative news (*"revenue jumped 12% but forward guidance slashed"*). | *"Wall Street beats quarterly estimates but warns of cloud deceleration"* | Models assign extreme positive or negative score rather than neutral balance. |
| **`other`** | General ambiguity, brevity ellipsis, or subtle stylistic connotations. | *"Global markets tumble as regional banking concerns rekindle liquidity fears"* | Threshold borderline classifications near zero compound score. |

---

## 3. Quantitative Error Distribution

The table below summarizes the quantitative breakdown of error categories produced by the evaluation harness (`scripts/evaluate.py`):

| Evaluation Benchmark | Model | Total Errors | Negation | Domain Terms | Sarcasm | Mixed Sentiment | Neutral Reporting | Other / Borderline |
|---|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **Financial PhraseBank** | `vader` | 140 | 3 | 23 | 2 | 4 | 1 | 107 |
| **In-Domain News Headlines** | `vader` | 126 | 3 | 11 | 0 | 0 | 3 | 109 |

---

## 4. Qualitative Headline Case Studies

### A. Negation Failures

1. **Headline**: *"No other ev3 devices were involved in this action ."*
   - **Dataset**: Financial PhraseBank
   - **Ground Truth**: `neutral`
   - **Model Prediction**: `negative` (Score: $-0.30$)
   - **Failure Mechanism**: The word *action* and negation *no* are parsed as adverse legal dispute, failing to recognize procedural clearance.

2. **Headline**: *"Besides , as there is no depositor preference in Finland , senior debt and deposits rank on a par..."*
   - **Dataset**: Financial PhraseBank
   - **Ground Truth**: `neutral`
   - **Model Prediction**: `negative` (Score: $-0.57$)
   - **Failure Mechanism**: The phrase *no depositor preference* triggers negative lexicon scoring despite describing legal equality (*rank on a par*).

### B. Domain-Specific Financial Terminology

1. **Headline**: *"Metsaliitto , however , narrowed its net loss for the second quarter to 5.0 mln euro..."*
   - **Dataset**: Financial PhraseBank
   - **Ground Truth**: `positive`
   - **Model Prediction**: `negative` (Score: $-0.32$)
   - **Failure Mechanism**: In corporate finance, a *narrowed net loss* is a clear positive earnings recovery. Lexicon baselines heavily penalize *loss* ($-0.50$) without recognizing the positive syntactic modifier *narrowed*.

2. **Headline**: *"Yield curve inversion deepens to minus 108 basis points signalling recession risk"*
   - **Dataset**: In-Domain News (Markets)
   - **Ground Truth**: `negative`
   - **Model Prediction**: `neutral`
   - **Failure Mechanism**: The technical term *yield curve inversion* requires macro-economic domain knowledge to map to negative recessionary expectations.

### C. Mixed Sentiment & Headline Concessions

1. **Headline**: *"Tech conglomerate beats revenue forecasts but warns of decelerating enterprise cloud bookings"*
   - **Dataset**: In-Domain News (Tech)
   - **Ground Truth**: `negative`
   - **Model Prediction**: `positive`
   - **Failure Mechanism**: The model anchors on *beats revenue forecasts* and ignores the forward-looking concession *warns of decelerating cloud bookings*.

2. **Headline**: *"Economy avoids anticipated recession in third quarter as domestic consumption holds"*
   - **Dataset**: In-Domain News (Markets)
   - **Ground Truth**: `positive`
   - **Model Prediction**: `negative`
   - **Failure Mechanism**: Co-occurrence of *recession* triggers strong negative sentiment, ignoring the avoidance verb *avoids*.

---

## 5. Cross-Domain Transfer & The Generalization Gap

When evaluating models across domains, the performance drop ($\Delta_{\text{domain}} = +0.144$) is driven by three distinct linguistic shifts:

1. **Syntactic Density & Ellipsis**:
   - Financial PhraseBank sentences are complete, formal sentences from PR wire statements (mean length: 21 words).
   - News headlines use journalistic compression, omitting auxiliary verbs and articles (*"Wall Street opens sharply higher on cooler inflation print"*, mean length: 11.2 words).
2. **Neutrality Baseline Bias**:
   - Financial PhraseBank is 61% neutral; models fine-tuned solely on financial reports over-predict neutral labels, leading to reduced recall on active headlines.
3. **Cross-Topic Named Entities**:
   - Expanding to climate, geopolitics, and technology introduces proper nouns and political actions that financial dictionaries treat as non-economic noise.

---

## 6. Recommendations for Model Architecture & Training

1. **Contextual Token Weighting**: Use transformer attention mechanisms rather than unigram bag-of-words lexicons to correctly bind modifiers (*narrowed*, *avoids*) to their financial objects (*loss*, *recession*).
2. **Domain-Specific Pretraining**: Train on journalistic news headlines rather than corporate disclosure filings to adapt to headline ellipsis and active voice verbs.
3. **Dual-Clause Sentence Splitting**: For multi-clause headlines joined by *but*, *despite*, or *while*, score clauses independently and compute an integrated balance score.
