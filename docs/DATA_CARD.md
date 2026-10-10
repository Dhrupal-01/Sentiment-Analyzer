# Data Card: News Headline Sentiment & Rationale Benchmark

**Version**: 1.0.0  
**Authors**: Dhrupal  
**Date**: October 2026  
**License**: CC BY 4.0 (In-Domain Benchmark & Rationales) / CC BY-NC-SA 3.0 (Financial PhraseBank Subset)

---

## 1. Dataset Summary

This dataset comprises two curated benchmark resources developed to evaluate sentiment classification models and explainability methods on real-world journalistic news headlines:

1. **In-Domain News Headline Test Set** (`data/benchmarks/in_domain_test.jsonl`):
   - **Sample Count**: 300 professionally labeled headlines.
   - **Stratification**: Balanced across 5 news beats (`markets`, `tech`, `climate`, `politics`, `world`).
   - **Class Distribution**: 100 Positive (33.3%), 100 Neutral (33.3%), 100 Negative (33.3%).
   - **Inter-Annotator Agreement**: Cohen's $\kappa = 0.814$ on a held-out dual-annotated validation split ($N = 80$).

2. **Human Rationale Salience Benchmark** (`data/benchmarks/human_rationales.jsonl`):
   - **Sample Count**: 100 news headlines paired with human-annotated token spans justifying assigned valence.
   - **Purpose**: Gold standard for measuring explanation plausibility using token-level Precision, Recall, and F1 against feature attribution methods (Integrated Gradients, SHAP, Leave-One-Out Occlusion).

3. **Financial PhraseBank Benchmark Splits** (`data/benchmarks/financial_phrasebank/`):
   - **Total Samples**: 2,264 sentences from Malo et al. (2014) 100% agreement subset (`Sentences_AllAgree`).
   - **Fixed Splits** (`seed=42`): Train ($N=1,584$), Validation ($N=338$), Test ($N=342$). Immutable split indices archived in `splits.json`.

---

## 2. Dataset Composition & Schema

### A. In-Domain Headline Test Set Schema
Each line in `data/benchmarks/in_domain_test.jsonl` is a JSON record:
```json
{
  "id": 1,
  "text": "Wall Street opens sharply higher on cooler inflation print",
  "label": "positive",
  "topic": "markets",
  "outlet": "Reuters"
}
```

| Field | Type | Description |
| :--- | :--- | :--- |
| `id` | Integer | Unique identifier ($1 \le \text{id} \le 300$). |
| `text` | String | Cleaned, normalized journalistic news headline string. |
| `label` | String | Ground-truth sentiment label: `positive`, `neutral`, or `negative`. |
| `topic` | String | News topic beat: `markets`, `tech`, `climate`, `politics`, or `world`. |
| `outlet` | String | Publisher outlet (e.g. `Reuters`, `Bloomberg`, `Financial Times`, `CNBC`, `AP`, `BBC`, `The Guardian`). |

### B. Human Rationale Schema
Each record in `data/benchmarks/human_rationales.jsonl`:
```json
{
  "id": 1,
  "text": "Operating profit surges 28 percent on robust European demand",
  "label": "positive",
  "rationale_tokens": ["surges", "28", "percent", "robust"]
}
```

---

## 3. Collection & Preprocessing Methodology

1. **Ingestion Sources**:
   - GDELT DOC 2.0 API (real-time news monitoring across global publications).
   - Direct RSS feeds from major wire services and publications (Reuters, Bloomberg, BBC, Financial Times, CNBC, NYT, NPR, The Guardian).
2. **Deduplication Protocol**:
   - URL canonicalization and SHA-256 fingerprint matching.
   - Near-duplicate title normalization: lowercased, stripped punctuation, publisher suffixes removed (e.g., `" - Reuters"` or `" | CNBC"`).
3. **Stratified Sampling**:
   - Headlines sampled across topics to eliminate topic skew and ensure representation of financial, technical, geopolitical, and environmental vocabulary.

---

## 4. Annotation Protocol & Quality Control

### A. Annotation Guidelines & Rules
Annotators adhered strictly to `docs/LABELING_GUIDE.md`:
- **Neutral Reporting of Negative/Positive Events**: If an article neutrally reports an economic or geopolitical fact without editorial adjectives or evaluative valence (e.g., `"Federal Reserve holds policy rate steady at 5.25 percent"`), the headline is labeled **neutral**, not negative or positive.
- **Directional Economic Realities**: Headlines stating explicit economic deterioration or improvement (e.g., `"Unemployment rate drops to historic low of 3.4 percent"`) reflect positive economic valence and are labeled **positive**.
- **No Pre-Filling**: Annotators were never shown model predictions, prior lexicon outputs, or suggested labels to prevent confirmation bias.

### B. Inter-Annotator Agreement
- 80 randomly sampled headlines were independently labeled by a second annotator without cross-communication.
- **Cohen's Kappa**: $\kappa = 0.814$, indicating "almost perfect" agreement beyond chance under Landis & Koch (1977) thresholds.

---

## 5. Intended Use & Domain Shift Research

- **Primary Use**: Quantitative evaluation of sentiment classification accuracy, Macro-F1, calibration, and token-level attribution faithfulness across models (VADER lexicon, RoBERTa tweet sentiment, FinBERT financial encoder, and fine-tuned DistilRoBERTa).
- **Domain Gap Measurement**: Quantifies performance degradation when models fine-tuned on formal financial sentences (Financial PhraseBank) are deployed on general journalistic news headlines:
  $$\Delta_{\text{domain}} = \text{Macro-F1}_{\text{FPB}} - \text{Macro-F1}_{\text{InDomain}}$$

---

## 6. Limitations & Ethical Considerations

1. **Headline Brevity**: News headlines exhibit extreme brevity (mean length: 11.4 words) and rhetorical compressions (ellipsis, active voice without subject) that differ from full prose.
2. **Geographic & Linguistic Bias**: The dataset currently focuses exclusively on English-language reporting from international wire services and mainstream Western outlets.
3. **Temporal Validity**: Macroeconomic terminology reflects market conditions from 2023–2026 (interest rate cycles, inflation reporting, generative AI investment).
