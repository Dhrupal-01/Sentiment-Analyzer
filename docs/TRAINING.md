# Training Guide: Fine-Tuning Sentiment Models on Free GPUs

This document provides step-by-step instructions for fine-tuning encoder models (e.g. `distilbert/distilroberta-base`) on the Financial PhraseBank benchmark across multiple random seeds, selecting checkpoints strictly on the validation split, and evaluating the cross-domain transfer gap.

---

## 1. Overview & Reproducibility Principles

1. **Strict Split Isolation**:
   - `data/benchmarks/financial_phrasebank/train.jsonl` (1,584 sentences): Training only.
   - `data/benchmarks/financial_phrasebank/val.jsonl` (338 sentences): Checkpoint selection only.
   - `data/benchmarks/financial_phrasebank/test.jsonl` (342 sentences): Held-out benchmark test set. **Never touched during training or hyperparameter tuning**.
   - `data/benchmarks/in_domain_test.jsonl` (300 sentences): Held-out general news headline set for measuring the **Domain Gap**.
2. **Multi-Seed Variance**:
   - Standard seeds: `42`, `43`, `44`.
   - Results are reported as sample mean ± standard deviation ($\mu \pm \sigma$), preventing cherry-picking.
3. **Hardware Requirements**:
   - Training completes in **under 15 minutes** on any free GPU:
     - **Google Colab**: Free Nvidia T4 GPU (16GB VRAM)
     - **Kaggle**: Free Nvidia P100 or T4x2 GPU (16GB VRAM)

---

## 2. Option A: Google Colab (Recommended)

Google Colab provides a free, zero-setup GPU environment.

### Step-by-Step Instructions

1. **Open Google Colab**:
   - Navigate to [https://colab.research.google.com](https://colab.research.google.com).
2. **Set GPU Accelerator**:
   - In the top menu, click **Runtime** → **Change runtime type**.
   - Select **T4 GPU** as the Hardware accelerator.
   - Click **Save**.
3. **Upload the Notebook**:
   - Click **File** → **Upload notebook**.
   - Upload `notebooks/finetune_sentiment.ipynb` from this repository.
4. **Clone Repository or Upload Datasets**:
   - Run the setup cell in the notebook to clone the project:
     ```bash
     !git clone https://github.com/Dhrupal-01/Sentiment-Analyzer.git
     %cd Sentiment-Analyzer
     ```
   - Alternatively, upload the `data/` folder directly to the Colab files pane.
5. **Install Dependencies**:
   ```bash
   !pip install "transformers[torch]" datasets evaluate accelerate pyyaml scikit-learn
   ```
6. **Execute Training Across 3 Seeds**:
   ```bash
   !python scripts/train.py --config configs/train.yaml
   ```
7. **Download Best Model Checkpoint**:
   - After training finishes, the best checkpoint is stored at `models/fine_tuned/best`.
   - Zip and download the checkpoint to your local machine:
     ```python
     from google.colab import files
     !zip -r fine_tuned_model.zip models/fine_tuned/best reports/training
     files.download("fine_tuned_model.zip")
     ```
8. **Place Checkpoint in Local Repository**:
   - Extract `fine_tuned_model.zip` into `models/fine_tuned/best/` in your local project.
   - Run `make eval` locally to verify that the evaluation report and documentation update automatically.

---

## 3. Option B: Kaggle Notebooks

Kaggle provides 30 hours per week of free GPU compute (Nvidia P100 / T4).

### Step-by-Step Instructions

1. **Create Kaggle Notebook**:
   - Go to [https://www.kaggle.com/code](https://www.kaggle.com/code) and click **New Notebook**.
2. **Enable GPU & Internet**:
   - In the right-hand **Notebook Options** panel:
     - Set **Accelerator** to **GPU P100** or **GPU T4 x2**.
     - Set **Internet** to **On**.
3. **Upload Dataset or Clone Repo**:
   - In the first code cell, clone the repository:
     ```bash
     !git clone https://github.com/Dhrupal-01/Sentiment-Analyzer.git /kaggle/working/Sentiment-Analyzer
     %cd /kaggle/working/Sentiment-Analyzer
     ```
4. **Install Packages & Run**:
   ```bash
   !pip install "transformers[torch]" datasets evaluate accelerate pyyaml scikit-learn
   !python scripts/train.py --config configs/train.yaml
   ```
5. **Save Kaggle Output**:
   - The artifacts in `/kaggle/working/Sentiment-Analyzer/models/fine_tuned/best` will appear in the output pane for instant download.

---

## 4. Option C: Local Testing (Zero-GPU Dry-Run)

If you are developing locally on a laptop without an Nvidia GPU or PyTorch installed, you can execute the simulated training pipeline:

```bash
# Runs full multi-seed simulation, generates telemetry CSV and summary JSON
.venv/bin/python scripts/train.py --dry-run
```

This generates:
- `reports/training/metrics.csv`
- `reports/training/run_summary.json`
- `models/fine_tuned/best/config.json`

Then run:
```bash
make eval
```
The benchmark report (`reports/eval/evaluation_report.md`) and documentation (`docs/EVALUATION.md`) will automatically ingest the training summary and render the multi-seed variance and Domain Gap tables.

---

## 5. Configuration Reference (`configs/train.yaml`)

```yaml
model:
  base_model: "distilbert/distilroberta-base"
  num_labels: 3
  id2label:
    0: "negative"
    1: "neutral"
    2: "positive"
  label2id:
    negative: 0
    neutral: 1
    positive: 2

data:
  train_path: "data/benchmarks/financial_phrasebank/train.jsonl"
  val_path: "data/benchmarks/financial_phrasebank/val.jsonl"
  test_path: "data/benchmarks/financial_phrasebank/test.jsonl"
  in_domain_path: "data/benchmarks/in_domain_test.jsonl"
  max_length: 128

training:
  learning_rate: 2.0e-5
  num_train_epochs: 4
  per_device_train_batch_size: 16
  per_device_eval_batch_size: 32
  warmup_ratio: 0.1
  weight_decay: 0.01
  eval_strategy: "epoch"
  save_strategy: "epoch"
  metric_for_best_model: "macro_f1"
  greater_is_better: true
  load_best_model_at_end: true
  seeds:
    - 42
    - 43
    - 44
  output_dir: "models/fine_tuned"
  logging_dir: "reports/training"

hub:
  push_to_hub: false
  hub_model_id: "Dhrupal-01/distilroberta-financial-sentiment"
```

---

## 6. Pushing Model to Hugging Face Hub (Optional)

To publish your fine-tuned model checkpoint to the Hugging Face Hub:

1. Obtain a Write Access Token from [huggingface.co/settings/tokens](https://huggingface.co/settings/tokens).
2. Set token in environment:
   ```bash
   export HF_TOKEN="your_hf_write_token"
   ```
3. Run training with `--push-to-hub`:
   ```bash
   .venv/bin/python scripts/train.py --config configs/train.yaml --push-to-hub
   ```
   Or set `push_to_hub: true` in `configs/train.yaml`.
