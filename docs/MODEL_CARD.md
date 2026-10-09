# Model Card: Fine-Tuned DistilRoBERTa for Financial Sentiment

## Model Details

- **Model Name**: DistilRoBERTa Financial Sentiment Classifier
- **Base Architecture**: `distilbert/distilroberta-base` (6-layer, 768-hidden, 12-heads, 82M parameters)
- **Task**: 3-Class Sentiment Sequence Classification (`negative`, `neutral`, `positive`)
- **Language**: English (`en`)
- **License**: Apache 2.0 (codebase) / CC BY-NC-SA 3.0 (data derivative)
- **Model Registry Key**: `fine_tuned`
- **Model Repository / Checkpoint**: `models/fine_tuned/best`
- **Optional Hugging Face Hub ID**: `Dhrupal-01/distilroberta-financial-sentiment`

---

## Intended Use

### Primary Intended Uses
- Automated classification of financial news headlines, earnings reports, and macroeconomic bulletins.
- Aggregation of daily and weekly sentiment indices across equity, commodity, and financial topics.
- Serving sentiment predictions with calibrated probabilities and continuous scores in $[-1.0, 1.0]$.

### Out-of-Scope & Misuse
- High-frequency automated trading execution without human-in-the-loop validation.
- General consumer social media sentiment (e.g. colloquial slang, sarcasm, memes).
- General news domains (e.g. violent crime, sports, celebrity culture) where the financial
  training domain exhibits a measurable domain gap.

---

## Training Data & Split Protocol

### Source Dataset
- **Financial PhraseBank (`Sentences_AllAgree`)**:
  - Malo, P., Sinha, A., Korhonen, P., Wallenius, J., & Takala, P. (2014).
    *Good debt or bad debt: Detecting semantic orientations in economic texts*. JASIST.
  - 100% Annotator Agreement consensus subset (2,264 sentences).

### Split Partitioning Protocol
- **Strict Split Isolation**: The dataset is deterministically partitioned into:
  - **Train split**: 1,584 sentences (70%)
  - **Validation split**: 338 sentences (15%)
  - **Test split**: 342 sentences (15%)
- **Zero Test Leakage**: The held-out test split is permanently quarantined during model
  training, hyperparameter tuning, and checkpoint selection. Checkpoints are chosen strictly
  by Macro-F1 on the validation split (`load_best_model_at_end=True`).

### Class Distribution (AllAgree)
- `neutral`: 1,391 sentences (61.4%)
- `positive`: 570 sentences (25.2%)
- `negative`: 303 sentences (13.4%)

---

## Training Setup & Hyperparameters

The model is trained via `scripts/train.py` using Hugging Face `Trainer` driven by `configs/train.yaml`:

| Hyperparameter | Value | Rationale |
| :--- | :--- | :--- |
| **Base Model** | `distilbert/distilroberta-base` | Low latency (~82M params) suitable for local/CPU serving |
| **Optimizer** | AdamW | Standard transformer optimization |
| **Learning Rate** | `2.0e-5` | Conservative fine-tuning rate preventing catastrophic forgetting |
| **Learning Rate Schedule**| Linear warmup with decay | Stabilizes initial classification head weights |
| **Warmup Ratio** | `0.1` (10% of total steps) | Prevents gradient instability in initial steps |
| **Weight Decay** | `0.01` | L2 regularization on encoder weights |
| **Epochs** | `4` | Sufficient convergence without overfitting on small train set |
| **Train Batch Size** | `16` | Fits in standard 16GB GPU memory with gradient stability |
| **Eval Batch Size** | `32` | Accelerated validation evaluation |
| **Max Sequence Length** | `128` tokens | Covers 100% of headlines and financial phrases |
| **Checkpoint Selection**| Best `macro_f1` on Validation | Balanced optimization across all 3 sentiment classes |
| **Random Seeds** | `[42, 43, 44]` | Multi-seed evaluation reporting sample mean ± std |

---

## Multi-Seed Evaluation & Benchmark Results

To avoid cherry-picking single runs, the model is trained across 3 random seeds.
We report sample mean ± standard deviation ($\mu \pm \sigma$):

### Validation Performance (Financial PhraseBank Val Split, N=338)

| Seed | Validation Accuracy | Validation Macro-F1 |
| :---: | :---: | :---: |
| `42` | 87.2% | 0.860 |
| `43` | 87.6% | 0.871 |
| `44` | 89.5% | 0.866 |
| **Aggregate ($\mu \pm \sigma$)** | **88.1% ± 1.2%** | **0.866 ± 0.005** |

### Benchmark Test Performance (Financial PhraseBank Test Split, N=342)

| Seed | Test Accuracy | Test Macro-F1 |
| :---: | :---: | :---: |
| `42` | 86.4% | 0.855 |
| `43` | 86.0% | 0.855 |
| `44` | 88.4% | 0.853 |
| **Aggregate ($\mu \pm \sigma$)** | **86.9% ± 1.3%** | **0.854 ± 0.001** |

---

## Cross-Domain Evaluation & The Domain Gap

To quantify how well a financial-domain model generalizes to broad journalistic news feeds,
the fine-tuned checkpoints were evaluated on our 300-item stratified news headline test set
(`data/benchmarks/in_domain_test.jsonl`):

| Evaluation Set | Macro-F1 ($\mu \pm \sigma$) | Accuracy ($\mu \pm \sigma$) | Domain Notes |
| :--- | :---: | :---: | :--- |
| **Financial PhraseBank Test** | 0.854 ± 0.001 | 86.9% ± 1.3% | Corporate earnings & financial statements |
| **In-Domain News Headlines** | 0.711 ± 0.006 | 74.5% ± 0.9% | Broad news beats (markets, tech, climate, politics, world) |
| **The Domain Gap ($\Delta_{\text{domain}}$)** | **-0.144** | **-12.4%** | **16.8% relative Macro-F1 drop** across domain boundary |

### Qualitative Analysis of the Domain Gap
1. **Linguistic Framing**: Financial PhraseBank uses explicit quantitative prose
   (*"Operating profit increased by 14%"*), whereas news headlines utilize editorial syntax,
   irony, and ellipsis (*"Tech stocks bleed as rate fears rattle Wall Street"*).
2. **Topic Divergence**: When evaluating outside corporate finance (e.g. political elections,
   climate disasters, diplomatic negotiations), financial sentiment encoders suffer reduced
   recall on non-economic conflict.
3. **Neutral Class Skew**: The financial dataset's 61% neutral prior induces conservative
   neutral predictions on ambiguous news headlines.

---

## Limitations, Biases & Ethical Considerations

1. **Class Imbalance Sensitivity**: Financial PhraseBank has fewer negative examples (13.4%),
   leading to lower negative-class recall compared to neutral.
2. **Entity-Level Sentiment**: The model performs sentence-level sequence classification.
   In complex headlines involving multiple entities (e.g., *"Apple sues Qualcomm"*),
   the prediction does not differentiate between the subject and the object.
3. **Journalistic Objectivity Bias**: Tragic events reported neutrally (e.g. earthquake casualties)
   can be misclassified as negative due to keyword sentiment carry-over.

---

## How to Use

### Loading via Model Registry
```python
from news_sentiment.models.registry import get_model

# Loads fine-tuned model checkpoint from models/fine_tuned/best
model = get_model("fine_tuned")
prediction = model.predict_one("Federal Reserve holds interest rates steady amid steady inflation")

print(prediction.label)  # "neutral"
print(prediction.score)  # float in [-1.0, 1.0]
print(prediction.probabilities)  # {"positive": ..., "neutral": ..., "negative": ...}
```

### Loading via Hugging Face Transformers
```python
from transformers import AutoModelForSequenceClassification, AutoTokenizer, pipeline

model_dir = "models/fine_tuned/best"
tokenizer = AutoTokenizer.from_pretrained(model_dir)
model = AutoModelForSequenceClassification.from_pretrained(model_dir)

nlp = pipeline("text-classification", model=model, tokenizer=tokenizer)
result = nlp("Alphabet announces record cloud revenue growth")
print(result)
```
