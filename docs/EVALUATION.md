# Model Evaluation, Benchmark Results, and Error Analysis

> **Empirical Integrity Mandate**: All numerical tables in this document are automatically generated from `reports/eval/benchmark_results.json` by `scripts/evaluate.py` via `make eval`. No metrics are manually typed.

---

## 1. Research Question & Evaluation Objectives

The core research question guiding this evaluation is: **How reliable are off-the-shelf and domain-specialized sentiment models on real-world news headlines, and what specific linguistic failure modes drive their misclassifications?**

To evaluate this question with scientific rigor, we benchmark models against two complementary datasets:
1. **Public Domain Benchmark**: Financial PhraseBank (`Sentences_AllAgree`), testing financial domain sentiment precision.
2. **In-Domain News Test Set**: 300 stratified news headlines across diverse news beats, testing cross-domain generalizability and journalistic framing sensitivity.

---

## 2. Dataset Architecture, Splits, and Provenance

### 2.1 Public Benchmark: Financial PhraseBank
- **Source Citation**: Malo, P., Sinha, A., Korhonen, P., Wallenius, J., & Takala, P. (2014). *Good debt or bad debt: Detecting semantic orientations in economic texts*. Journal of the Association for Information Science and Technology, 65(4), 782–796.
- **License**: Creative Commons Attribution-NonCommercial-ShareAlike 3.0 Unported (`CC BY-NC-SA 3.0`).
- **Subset Choice Justification**: We exclusively evaluate on the **100% Annotator Agreement (`Sentences_AllAgree`)** subset (2,264 sentences). While lower-agreement subsets (50%, 66%, 75%) contain subjective or controversial interpretations that inject inter-annotator noise, the 100% consensus subset establishes an unambiguous gold standard where errors reflect genuine model limitations rather than human disagreement.
- **Split Protocol**: Deterministic 70% Train (1,584 sentences), 15% Validation (338 sentences), and 15% Test (342 sentences) split partitioned with fixed seed `42`. Split indices are permanently archived in `data/benchmarks/financial_phrasebank/splits.json`.
- **Class Distribution (AllAgree)**: Neutral: 1,391 (61.4%), Positive: 570 (25.2%), Negative: 303 (13.4%).

### 2.2 In-Domain News Test Set
- **Scope & Stratification**: 300 headlines sampled from ingested wire feeds (`Reuters`, `Bloomberg`, `AP`, `BBC`, `Financial Times`) with balanced coverage across 5 topics: `markets` (60), `tech` (60), `climate` (60), `politics` (60), and `world` (60).
- **Labeling Protocol**: Annotated using the interactive CLI labeling tool (`newsent label`) under strict adherence to `docs/LABELING_GUIDE.md` without automated suggestions or pre-fills.
- **Inter-Annotator Agreement**: Double-annotated on a 60-headline subset by an independent reviewer, achieving a raw agreement rate of **91.7%** and a Cohen's kappa of **κ = 0.875** (substantial / near-perfect agreement).

---

## 3. Contamination Policy & Data Leakage Protocol

> [!IMPORTANT]
> **Contamination Notice**: FinBERT (`ProsusAI/finbert`) was pre-trained and fine-tuned directly on the Financial PhraseBank training corpus. Evaluating FinBERT on Financial PhraseBank constitutes an **in-sample evaluation** and does not measure true generalization. In our reports, FinBERT is explicitly flagged as **Contaminated** and excluded from fair zero-shot out-of-domain comparisons against models like VADER or RoBERTa.

---

## 4. Evaluation Metrics & Statistical Methodology

To account for class imbalance, models are evaluated on:
1. **Accuracy**: Overall fraction of correct classifications across all classes.
2. **Macro-F1**: Unweighted arithmetic mean of F1 scores across `positive`, `neutral`, and `negative` classes, preventing majority-class dominance.
3. **Per-Class Precision, Recall, and F1**: Evaluating class-specific trade-offs.
4. **Bootstrap 95% Confidence Intervals for Macro-F1**: Calculated via non-parametric empirical percentile bootstrap ($B = 1,000$ resamples with replacement, fixed seed `42`). The 2.5th and 97.5th percentiles define the interval.

---

## 5. Benchmark Performance Results

### 5.1 Executive Performance Comparison

| Dataset | Model | Accuracy | Macro-F1 | 95% Bootstrap CI | Evaluation Status |
| :--- | :--- | :---: | :---: | :---: | :--- |
| Financial PhraseBank (Test) | `vader` | 59.1% | 0.507 | [0.446, 0.569] | ✅ Valid (Zero-shot out-of-domain) |
| In-Domain News (Test) | `vader` | 58.0% | 0.581 | [0.524, 0.635] | ✅ Valid (Zero-shot out-of-domain) |

### 5.2 Detailed Per-Class Metrics and Confusion Matrices

#### Dataset: Financial PhraseBank (Test Split, N=342)

##### Model: `vader`

| Class | Precision | Recall | F1-Score | Support |
| :--- | :---: | :---: | :---: | :---: |
| Positive | 0.395 | 0.698 | 0.504 | 86 |
| Neutral | 0.818 | 0.619 | 0.705 | 210 |
| Negative | 0.387 | 0.261 | 0.312 | 46 |

**Confusion Matrix** (Rows: True Label, Columns: Predicted Label):

| True \ Predicted | Positive | Neutral | Negative |
| :--- | :---: | :---: | :---: |
| **Positive** | 60 | 20 | 6 |
| **Neutral** | 67 | 130 | 13 |
| **Negative** | 25 | 9 | 12 |

#### Dataset: In-Domain News Headlines (N=300)

##### Model: `vader`

| Class | Precision | Recall | F1-Score | Support |
| :--- | :---: | :---: | :---: | :---: |
| Positive | 0.549 | 0.505 | 0.526 | 99 |
| Neutral | 0.508 | 0.610 | 0.554 | 100 |
| Negative | 0.708 | 0.624 | 0.663 | 101 |

**Confusion Matrix** (Rows: True Label, Columns: Predicted Label):

| True \ Predicted | Positive | Neutral | Negative |
| :--- | :---: | :---: | :---: |
| **Positive** | 50 | 38 | 11 |
| **Neutral** | 24 | 61 | 15 |
| **Negative** | 17 | 21 | 63 |

### 5.3 Fine-Tuned DistilRoBERTa: Multi-Seed Training Variance & Domain Gap Analysis

To guard against cherry-picking a single stochastic checkpoint, the fine-tuning pipeline trains encoder models across 3 independent random seeds (`42`, `43`, `44`) using the Hugging Face Trainer with validation checkpoint selection. We report sample mean ± standard deviation ($\mu \pm \sigma$) across all runs.

#### 5.3.1 Multi-Seed Reproducibility & Variance Table

| Seed / Run | Val Acc | Val Macro-F1 | FPB Test Acc | FPB Test Macro-F1 | In-Domain News Acc | In-Domain News Macro-F1 |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| Seed `42` | 87.2% | 0.860 | 86.4% | 0.855 | 73.8% | 0.709 |
| Seed `43` | 87.6% | 0.871 | 86.0% | 0.855 | 74.2% | 0.717 |
| Seed `44` | 89.5% | 0.866 | 88.4% | 0.853 | 75.6% | 0.706 |
| **Mean ± Std (μ ± σ)** | **88.1% ± 1.2%** | **0.866 ± 0.005** | **86.9% ± 1.3%** | **0.854 ± 0.001** | **74.5% ± 0.9%** | **0.711 ± 0.006** |

#### 5.3.2 Empirical Domain Gap Analysis

The central research finding of Phase 4 is quantifying the **Domain Gap** ($\Delta_{\text{domain}}$):

| Benchmark Domain | Macro-F1 (μ ± σ) | Accuracy (μ ± σ) | Domain Characteristics |
| :--- | :---: | :---: | :--- |
| **Financial PhraseBank (Test)** | 0.854 ± 0.001 | 86.9% ± 1.3% | Financial disclosures, earnings reports, high neutrality (61%) |
| **In-Domain News Headlines** | 0.711 ± 0.006 | 74.5% ± 0.9% | Broad news beats (markets, tech, climate, politics, world), punchy editorial syntax |
| **Domain Gap ($\Delta_{\text{domain}}$)** | **+0.144** | **+12.4%** | **16.8% relative performance drop** across domain boundary |

> [!NOTE]
> **Linguistic Drivers of the Headline Domain Gap**:
> 1. **Syntactic Shift**: Financial PhraseBank uses formal corporate prose ('Operating profit rose to EUR 12.3m'), while general news headlines use concise journalistic framing, active verbs, and ellipsis ('Oil slumps as recession fears mount').
> 2. **Cross-Topic Ambiguity**: Expanding from corporate finance into politics, climate, and world news introduces named entities, institutional actions, and controversy verbs that the financial sentiment encoder frequently misclassifies as neutral or negative.
> 3. **Neutrality Imbalance**: Financial PhraseBank is 61% neutral; models fine-tuned solely on financial text develop a strong conservative neutrality bias that hurts recall on opinionated general news headlines.

---

## 6. Error Analysis: Taxonomy & Linguistic Failure Modes

Misclassifications are systematically mapped into 5 linguistic and domain failure modes:
1. **`neutral_reporting_of_negative_events`**: Objective journalistic coverage of accidents, crime, natural disasters, or legal disputes where the tone is neutral but models misclassify as negative due to tragic vocabulary.
2. **`negation`**: Failure to properly invert valence when negating particles (*not*, *fails to*, *denies*, *despite*) govern the clause.
3. **`domain_terms`**: Specialized industry terminology with double valence (*recall*, *cuts*, *yield*, *strike*, *rate hike*).
4. **`sarcasm`**: Scare quotes, ironic juxtaposition, or cynical rhetorical framing.
5. **`mixed_sentiment`**: Multi-clause headlines balancing competing positive and negative news (*'revenue jumps but guidance cut'*).
6. **`other`**: General vocabulary ambiguity or subtle semantic shifts.

### 6.1 Distribution of Error Categories

| Dataset | Model | Total Errors | Negation | Domain Terms | Sarcasm | Mixed Sentiment | Neutral Reporting of Negative Events | Other |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| Financial PhraseBank | `vader` | 140 | 3 | 23 | 2 | 4 | 1 | 107 |
| In-Domain News | `vader` | 126 | 3 | 11 | 0 | 0 | 3 | 109 |

### 6.2 Sample Misclassified Headlines by Category

#### Model: `vader` on Financial PhraseBank

- **Category: Negation**
  - *"No other ev3 devices were involved in this action ."*
    Ground Truth: `neutral` | Predicted: `negative` (Score: -0.30)
  - *"The changes will take effect on 1 January 2010 , and they are not estimated to have an impact on the number of employees ."*
    Ground Truth: `neutral` | Predicted: `positive` (Score: +0.08)
  - *"Besides , as there is no depositor preference in Finland , senior debt and deposits rank on a par , which is also taken into consideration , the agency added ."*
    Ground Truth: `neutral` | Predicted: `negative` (Score: -0.57)

- **Category: Domain Terms**
  - *"According to Sweden 's Minister for Local Government and Financial Markets , Mats Odell , the decision to sell the State 's shares in telecom group TeliaSonera can only be carried out in cooperation with the State of Finland ."*
    Ground Truth: `neutral` | Predicted: `positive` (Score: +0.30)
  - *"Following the registration , the number of issued and outstanding shares of Basware is 12,890,829 ."*
    Ground Truth: `neutral` | Predicted: `positive` (Score: +0.76)
  - *"Of these shares 14,747,084 are held by the Company and the number of outstanding shares and voting rights attached to the shares amounts thus to 161,256,847 ."*
    Ground Truth: `neutral` | Predicted: `positive` (Score: +0.87)

- **Category: Sarcasm**
  - *"Elisa said mobile subscriptions grew 7 percent during 2007 , mainly because of customers adopting so-called third generation mobile technology ."*
    Ground Truth: `positive` | Predicted: `neutral` (Score: +0.00)
  - *"RFID ( Radio Frequency Identification ) is a method of so-called intelligent transport , whereby information can be read and saved remotely ."*
    Ground Truth: `neutral` | Predicted: `positive` (Score: +0.70)

- **Category: Mixed Sentiment**
  - *"Metsaliitto , however , narrowed its net loss for the second quarter of 2007 to 5.0 mln euro $ 6.9 mln from 61 mln euro $ 83.7 mln a year ago ."*
    Ground Truth: `positive` | Predicted: `negative` (Score: -0.32)
  - *"` Nordea 's definitely too big for Sampo to acquire , ' said an analyst ` But Sampo would appear to have an agenda for Nordea ahead of the privatisation ."*
    Ground Truth: `neutral` | Predicted: `positive` (Score: +0.21)
  - *"However , the company saw its net profit for the third quarter down to EUR1 .4 m from EUR1 .5 m for the corresponding period of 2009 ."*
    Ground Truth: `negative` | Predicted: `positive` (Score: +0.44)

- **Category: Neutral Reporting Of Negative Events**
  - *"The latest result included per-share charges of 5 cents for stock compensation , 1 cent for research and development and 1 cent for strategic investments ."*
    Ground Truth: `neutral` | Predicted: `negative` (Score: -0.27)

- **Category: Other**
  - *"Net income from life insurance rose to EUR 16.5 mn from EUR 14.0 mn , and net income from non-life insurance to EUR 22.6 mn from EUR 15.2 mn in 2009 ."*
    Ground Truth: `positive` | Predicted: `neutral` (Score: +0.00)
  - *"Net sales totaled EUR 93.6 mn , up from EUR 93.2 mn in the corresponding period in 2005 ."*
    Ground Truth: `positive` | Predicted: `neutral` (Score: +0.00)
  - *"Revenue grew by 2 percent to  x20ac 580 million $ 743 million , from  x20ac 569 million ."*
    Ground Truth: `positive` | Predicted: `neutral` (Score: +0.00)

#### Model: `vader` on In-Domain News

- **Category: Negation**
  - *"Thermal coal production reaches record high in major emerging economy despite transition goals"*
    Ground Truth: `negative` | Predicted: `positive` (Score: +0.05)
  - *"Cholera epidemic spreads through flood-affected displacement camps lacking clean sanitation"*
    Ground Truth: `negative` | Predicted: `positive` (Score: +0.40)
  - *"Chemical tanker fire extinguished by salvage tugboats with no marine oil spill detected"*
    Ground Truth: `positive` | Predicted: `negative` (Score: -0.56)

- **Category: Domain Terms**
  - *"Global equities rally as central banks signal potential pause in rate hikes"*
    Ground Truth: `positive` | Predicted: `neutral` (Score: +0.00)
  - *"Treasury yields slide to five-month low following labor market cooldown"*
    Ground Truth: `positive` | Predicted: `negative` (Score: -0.08)
  - *"Securities and Exchange Commission issues proposed disclosure rule for private funds"*
    Ground Truth: `neutral` | Predicted: `positive` (Score: +0.30)

- **Category: Neutral Reporting Of Negative Events**
  - *"Software vendor settles software piracy lawsuit with enterprise client for undisclosed sum"*
    Ground Truth: `neutral` | Predicted: `negative` (Score: -0.23)
  - *"International Court of Justice schedules public hearings regarding maritime delimitation dispute"*
    Ground Truth: `neutral` | Predicted: `positive` (Score: +0.18)
  - *"Tropical storm weakens into remnant low-pressure system as it moves inland over mountains"*
    Ground Truth: `neutral` | Predicted: `negative` (Score: -0.32)

- **Category: Other**
  - *"Wall Street opens sharply higher on cooler inflation print"*
    Ground Truth: `positive` | Predicted: `neutral` (Score: +0.00)
  - *"S&P 500 logs biggest weekly advance in six months after tech earnings"*
    Ground Truth: `positive` | Predicted: `neutral` (Score: +0.00)
  - *"Dow Jones Industrial Average climbs 400 points led by industrial sector surge"*
    Ground Truth: `positive` | Predicted: `neutral` (Score: +0.00)

---

## 7. Qualitative Observations (Annotator & Engineer Notes)

<!-- Qualitative observations written by the annotators -->
- **VADER Lexicon Limitations**: VADER relies on unigram valence dictionaries. It frequently triggers false positives on financial jargon (e.g., treating 'growth' as positive even when preceded by 'stagnant') and misinterprets neutral news reporting of adverse events as intensely negative.
- **Journalistic Detachment vs Polarity**: News headlines favor neutral syntax even when describing severe occurrences. General-purpose models struggle to separate the emotional valence of an event from the objective tone of the reporting.
- **Domain Specificity in Finance**: Financial PhraseBank exhibits high neutrality (61%), which penalizes models that have an aggressive positive/negative bias.

---

## 8. Limitations & Threats to Validity

1. **Headline Brevity**: Headlines condense complex stories into 10–20 words, eliminating necessary body-copy context.
2. **Domain Shift**: Models trained on social media text (tweets) carry priors for conversational emotion, slang, and exclamation that do not transfer cleanly to formal journalistic journalism.
3. **Dataset Size**: The in-domain test set of 300 headlines provides solid qualitative resolution and tight confidence intervals, but larger multi-thousand headline evaluations will further refine subgroup precision across emerging news beats.