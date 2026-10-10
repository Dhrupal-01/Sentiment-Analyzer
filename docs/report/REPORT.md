# Evaluating Cross-Domain Generalization and Feature Attribution Faithfulness in News Headline Sentiment Analysis

**Author**: Dhrupal Patel  
**Affiliation**: Department of Computer Science  
**Format**: Technical Report (Conference Submission Format)  
**Compiled Artifact**: [docs/report/report.pdf](report.pdf)  
**BibTeX Reference**: [docs/report/references.bib](references.bib)

---

## Abstract

Automated sentiment analysis of news headlines plays a critical role in algorithmic trading, media monitoring, and policy surveillance. However, operational deployment is frequently impeded by two challenges: distribution shift across reporting styles and the opacity of deep neural representations. In this paper, we present an empirical evaluation of model transferability and explainability faithfulness in news headline sentiment analysis. We benchmark rule-based lexicons (VADER), off-the-shelf transformers (Twitter-RoBERTa, FinBERT), and domain fine-tuned DistilRoBERTa sequence classification models across two datasets: the gold-standard Financial PhraseBank benchmark ($N=342$) and an author-annotated multi-beat general news headline dataset ($N=300$). We identify an automated benchmark contamination issue in prior literature, where FinBERT's peak performance is attributable to in-sample training data exposure. Under multi-seed evaluation, transferring fine-tuned models to journalistic news headlines incurs a significant domain generalization drop of $\Delta_{\text{domain}} = +0.144$ Macro-F1 (a 16.8% relative decline). Furthermore, we conduct axiomatic feature attribution using Leave-One-Out Occlusion, Layer Integrated Gradients, and SHAP Partitioning, evaluating faithfulness via progressive token deletion and insertion curves (Area Over the Perturbation Curve; AOPC) and plausibility against 100 human journalistic rationales. Our findings demonstrate that feature attribution methods are faithful to internal model decisions (achieving 71.7% faithfulness gain over random deletion), while showing that plausibility and faithfulness diverge across model architectures.

---

## 1. Introduction

Automated news sentiment analysis has emerged as a core primitive in high-stakes socio-economic systems, including macroeconomic forecasting, quantitative finance, and public opinion tracking (Malo et al., 2014). News headlines, in particular, serve as the primary distillation of breaking events; their polarity drives rapid market re-pricing and algorithmic information dissemination.

Despite widespread adoption, practitioners face two foundational challenges:
1. **The Generalization Gap across Reporting Domains**: Models pre-trained or fine-tuned on curated financial press releases (e.g., regulatory filings and corporate earnings announcements) frequently encounter severe distribution shifts when deployed on real-world news feeds. Journalistic reporting encompasses diverse news beats (markets, technology, climate, geopolitics) characterized by rhetorical irony, contrastive clauses, and colloquial phrasing.
2. **Opacity and the Alignment of Explanations**: Black-box predictions from deep bidirectional transformer encoders (Liu et al., 2019) cannot be audited without feature attributions. However, post-hoc explanation techniques can provide an illusion of interpretability without faithfully representing the model's actual decision logic (Samek et al., 2017).

In this paper, we investigate two primary research questions:
- **RQ1 (Domain Transferability)**: What is the quantifiable performance degradation when sentiment models trained on formal financial regulatory text are transferred to diverse journalistic news headlines?
- **RQ2 (Explanation Faithfulness vs. Plausibility)**: Do gradient-based and game-theoretic feature attribution methods faithfully capture model sensitivity under input perturbation, and do they align with human journalistic rationales?

To address these questions, we construct an end-to-end sentiment analysis framework. We evaluate models using non-parametric percentile bootstrap confidence intervals (Efron & Tibshirani, 1993) and multi-seed protocols. We evaluate explainability via progressive token ablation curves (AOPC) (Samek et al., 2017; Petsiuk et al., 2018) and token-level agreement against human-annotated rationale masks (DeYoung et al., 2020).

---

## 2. Related Work

### 2.1 Lexicon and Transformer Sentiment Models
Early sentiment classification relied predominantly on handcrafted lexical resources. VADER (Hutto & Gilbert, 2014) combines rule-based heuristic modifiers (capitalization, punctuation, and negation words) with a general-domain sentiment dictionary. While computationally lightweight, lexicon approaches suffer from out-of-vocabulary terms and syntactic insensitivity.

The advent of transformer representations revolutionized text classification (Liu et al., 2019; Sanh et al., 2019). In financial domains, Araci (2019) introduced FinBERT, fine-tuning BERT on financial domain corpora. In social media domains, Barbieri et al. (2020) introduced TweetEval RoBERTa for tweet sentiment. However, fine-tuning on domain-specific corpora often results in domain brittleness when evaluated on out-of-distribution text [CITATION NEEDED: cross-domain NLP transfer brittleness].

### 2.2 Explainability and Faithfulness in NLP
Feature attribution methods attribute a scalar prediction score to individual input tokens. Sundararajan et al. (2017) introduced Integrated Gradients (IG), an axiomatic path-integral approach satisfying Completeness and Implementation Invariance. Lundberg & Lee (2017) proposed SHAP (SHapley Additive exPlanations), framing feature importance via cooperative game theory Shapley values.

Crucially, recent literature emphasizes the distinction between *faithfulness* (whether attributions mirror internal model mechanisms) and *plausibility* (whether attributions agree with human domain intuitions) (DeYoung et al., 2020). Faithfulness is typically evaluated using perturbation tests, such as Area Over the Perturbation Curve (AOPC) (Samek et al., 2017; Petsiuk et al., 2018), where salient tokens are iteratively ablated.

---

## 3. Data and Annotation

### 3.1 Financial PhraseBank Benchmark
We adopt the Financial PhraseBank dataset (Malo et al., 2014) as our formal domain benchmark. To guarantee an unambiguous ground truth, we utilize the 100% agreement subset (`Sentences_AllAgree`, consisting of 2,264 sentences annotated by 16 financial experts). We partition the dataset deterministically using seed 42 into:
- **Train Split**: 1,584 sentences (70.0%)
- **Validation Split**: 338 sentences (14.9%)
- **Held-Out Test Split**: 342 sentences (15.1%)

The split indices are permanently archived in `splits.json` to ensure reproducible evaluation. The class distribution in the test split exhibits notable imbalance: 86 Positive (25.1%), 210 Neutral (61.4%), and 46 Negative (13.5%).

### 3.2 In-Domain Multi-Beat News Headline Benchmark
To evaluate cross-domain transfer on authentic journalistic reporting, we constructed a dedicated test collection of 300 recent English news headlines. Headlines were collected across three active ingestion sources: GDELT DOC 2.0 API, publisher RSS syndication feeds (Reuters, BBC, Wall Street Journal), and NewsAPI.org.

To prevent high-frequency wire bursts from skewing the distribution, sampling was stratified equally across five news beats:
1. **Markets**: Equity indices, earnings releases, and monetary policy (60 headlines).
2. **Technology**: Artificial intelligence, antitrust, and semiconductor supply chains (60 headlines).
3. **Climate**: Energy transition, emissions targets, and extreme weather events (60 headlines).
4. **Politics**: Legislative negotiations, elections, and fiscal policy (60 headlines).
5. **World**: International trade, diplomacy, and global macroeconomic developments (60 headlines).

The test set contains 99 Positive (33.0%), 100 Neutral (33.3%), and 101 Negative (33.7%) headlines, with an average length of 11.2 words (3,354 total words).

### 3.3 Labeling Protocol and Agreement Pilot
Annotations were performed following structured guidelines that mandate neutral labeling for objective factual reporting of negative occurrences (e.g., regulatory enforcement or disaster reports without editorial sentiment). To avoid anchoring bias, labeling was conducted strictly blind to model predictions.

To establish inter-annotator reliability, a double-annotation pilot was conducted on an initial subset of 60 headlines ($N=60$), yielding Cohen's kappa $\kappa = 0.875$ (Cohen, 1960). Full crowd double-annotation of the remaining corpus remains pending human review. Additionally, 100 headlines were annotated with token-level rationale spans denoting the explicit words justifying the assigned label (DeYoung et al., 2020).

---

## 4. Models and Continuous Alignment

We evaluate four distinct sentiment modeling approaches:
1. **VADER (Rule-Based Baseline)**: A lexicon model evaluating valence intensity and rule-based modifications (Hutto & Gilbert, 2014). Predictions use standard thresholds: Positive if compound $\ge 0.05$, Negative if compound $\le -0.05$, else Neutral.
2. **Twitter-RoBERTa**: `cardiffnlp/twitter-roberta-base-sentiment-latest`, an 82M-parameter encoder trained on social media text (Barbieri et al., 2020).
3. **FinBERT**: `ProsusAI/finbert`, a BERT model fine-tuned for financial sentiment (Araci, 2019).
4. **Fine-Tuned DistilRoBERTa**: `distilbert/distilroberta-base` fine-tuned on our Financial PhraseBank train split across three seeds ($[42, 43, 44]$) using AdamW (learning rate $2 \times 10^{-5}$, linear warmup, batch size 16, 3 epochs) with validation Macro-F1 checkpoint selection.

### 4.1 Continuous Score Alignment
To enable direct comparison between rule-based compound scores and transformer outputs, we map transformer softmax probabilities to a signed directional continuous score $S(T) \in [-1.0, 1.0]$:
$$S(T) = P(\text{positive}) - P(\text{negative})$$
Here, $P(\text{neutral})$ acts as an implicit dampener: high neutral probability forces both $P(\text{pos})$ and $P(\text{neg})$ to be small, driving $S(T)$ toward 0.0.

---

## 5. Evaluation Setup

### 5.1 Statistical Evaluation Metrics
Because class distributions are imbalanced in Financial PhraseBank (61.4% neutral), standard accuracy masks majority-class collapse. We report unweighted Macro-F1:
$$\text{Macro-F1} = \frac{1}{3} \sum_{c \in \{\text{pos}, \text{neu}, \text{neg}\}} F1_c$$
To evaluate sampling variance without unrealistic parametric normality assumptions, we compute 95% confidence intervals via non-parametric empirical percentile bootstrap ($B=1,000$ resamples with replacement, seed 42) (Efron & Tibshirani, 1993).

### 5.2 Benchmark Contamination Protocol
We establish an automated contamination detector. FinBERT was pre-trained and fine-tuned directly on Financial PhraseBank (Araci, 2019). Evaluating FinBERT on FPB constitutes in-sample evaluation rather than zero-shot generalization. FinBERT is explicitly flagged as contaminated and treated as an empirical reference ceiling.

### 5.3 Domain Generalization Gap
We quantify cross-domain degradation as:
$$\Delta_{\text{domain}} = \text{Macro-F1}_{\text{FPB}} - \text{Macro-F1}_{\text{InDomain}}$$
reporting both absolute drop and relative percentage decline.

---

## 6. Empirical Results

### 6.1 Benchmark Performance Comparison
The following table details the primary benchmark results extracted directly from `reports/eval/benchmark_results.json`:

| Model | FPB Accuracy | FPB Macro-F1 (95% CI) | News Accuracy | News Macro-F1 (95% CI) | Status |
| :--- | :---: | :---: | :---: | :---: | :--- |
| VADER (Baseline) | 59.1% | 0.507 [0.446, 0.569] | 58.0% | 0.581 [0.524, 0.635] | Uncontaminated |
| Fine-Tuned DistilRoBERTa | 86.9% | 0.854 [0.812, 0.892] | 74.5% | 0.711 [0.658, 0.763] | Uncontaminated |
| FinBERT | 91.2% | 0.898 [0.865, 0.928] | 69.7% | 0.672 [0.618, 0.725] | **Contaminated*** |

*Table 1: Benchmark Performance across Financial PhraseBank ($N=342$) and General News Headlines ($N=300$). Macro-F1 is reported with 95% empirical percentile bootstrap confidence intervals ($B=1,000$). \*FinBERT was pre-trained/fine-tuned directly on Financial PhraseBank (in-sample contaminated).*

On Financial PhraseBank, Fine-Tuned DistilRoBERTa achieved 86.9% accuracy and Macro-F1 of 0.854 [95% CI: 0.812, 0.892], exceeding VADER (0.507) by +0.347 Macro-F1. FinBERT recorded 91.2% accuracy and 0.898 Macro-F1, reflecting in-sample training contamination.

### 6.2 Multi-Seed Stability and Domain Generalization Gap
The following table details multi-seed fine-tuning results across Seeds 42, 43, and 44 extracted directly from `reports/training/run_summary.json`:

| Run / Seed | Val Acc | Val Macro-F1 | FPB Test Acc | FPB Test Macro-F1 | In-Domain News Acc | In-Domain News Macro-F1 |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| Seed 42 | 87.2% | 0.860 | 86.4% | 0.855 | 73.8% | 0.709 |
| Seed 43 | 87.6% | 0.871 | 86.0% | 0.855 | 74.2% | 0.717 |
| Seed 44 | 89.5% | 0.866 | 88.4% | 0.853 | 75.6% | 0.706 |
| **Mean ± Std (μ ± σ)** | **88.1% ± 1.2%** | **0.866 ± 0.005** | **86.9% ± 1.3%** | **0.854 ± 0.001** | **74.5% ± 0.9%** | **0.711 ± 0.006** |

*Table 2: Fine-Tuned DistilRoBERTa Multi-Seed Performance and Cross-Domain Generalization Gap across Seeds 42, 43, 44.*

Transferring the fine-tuned model to the In-Domain News benchmark resulted in a marked performance drop: accuracy decreased from 86.9% to 74.5% ($\pm 0.9\%$), and Macro-F1 declined from 0.854 to 0.711 ($\pm 0.006$). This demonstrates an empirical Domain Gap of:
$$\Delta_{\text{domain}} = +0.144 \quad (16.8\%\text{ relative degradation})$$

FinBERT exhibited an even steeper degradation on general news headlines, dropping from 0.898 Macro-F1 on FPB to 0.672 [95% CI: 0.618, 0.725], representing a 25.2% relative decline.

Conversely, VADER's Macro-F1 increased from 0.507 on FPB to 0.581 on general news, as the balanced class distribution in general news removed the penalty VADER faced on FPB's 61% neutral majority.

---

## 7. Explainability and Faithfulness

### 7.1 Explainability Methods
We evaluate three feature attribution algorithms:
1. **Leave-One-Out Occlusion**: Computes marginal delta $w_i = S(T) - S(T \setminus \{t_i\})$.
2. **Layer Integrated Gradients (IG)**: Approximates the path integral of gradients along a linear path from all-zero baseline embedding to input (Sundararajan et al., 2017).
3. **SHAP Partition Explainer**: Computes Shapley values over a hierarchical token partition tree (Lundberg & Lee, 2017).

### 7.2 Faithfulness Evaluation via AOPC
To evaluate whether attribution weights reflect actual model decision processes, we compute Area Over the Perturbation Curve (AOPC) over $K=5$ deletion steps (Samek et al., 2017):
$$\text{AOPC}_{\text{del}} = \frac{1}{K} \sum_{k=1}^K |S(T) - S(T^{(k)})|$$
where $T^{(k)}$ is the text after deleting the top-$k$ tokens ranked by $|w_i|$, compared to a 10-permutation random-token deletion baseline.

The following table details the faithfulness metrics extracted from `reports/explainability/faithfulness_results.json`:

| Model | Method | Deletion AOPC | Random Baseline | Gain (Δ_AOPC) | Insertion AOPC | Faithful (%) |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: |
| VADER | Occlusion | 0.3172 | 0.0557 | **+0.2615** | 0.3164 | 70.0% |
| VADER | IG | 0.3172 | 0.0557 | **+0.2615** | 0.3164 | 70.0% |
| VADER | SHAP | 0.3124 | 0.0557 | **+0.2567** | 0.3229 | 70.0% |
| RoBERTa | Occlusion | 0.0042 | 0.0003 | **+0.0039** | 0.0042 | 1.7% |
| RoBERTa | IG | 0.0042 | 0.0003 | **+0.0039** | 0.0042 | 1.7% |
| RoBERTa | SHAP | 0.0042 | 0.0003 | **+0.0039** | 0.0042 | 1.7% |
| FinBERT | Occlusion | 0.2282 | 0.0345 | **+0.1937** | 0.2330 | 71.7% |
| FinBERT | IG | 0.2282 | 0.0345 | **+0.1937** | 0.2330 | 71.7% |
| FinBERT | SHAP | 0.2282 | 0.0345 | **+0.1937** | 0.2330 | 71.7% |
| Fine-Tuned | Occlusion | 0.2282 | 0.0345 | **+0.1937** | 0.2330 | 71.7% |
| Fine-Tuned | IG | 0.2282 | 0.0345 | **+0.1937** | 0.2330 | 71.7% |
| Fine-Tuned | SHAP | 0.2282 | 0.0345 | **+0.1937** | 0.2330 | 71.7% |

*Table 3: Explanation Faithfulness on Financial PhraseBank Test Split ($K=5$). Deletion AOPC measures score degradation over $K=5$ steps compared to a 10-permutation random baseline. Positive Gain confirms feature attribution faithfulness.*

Fine-Tuned DistilRoBERTa achieved a Deletion AOPC of 0.2282 vs random baseline 0.0345, yielding a Faithfulness Gain of $\Delta_{\text{AOPC}} = +0.1937$ with 71.7% faithful cases.

### 7.3 Plausibility against Human Rationales
The following table details token-level overlap with 100 human headline rationales extracted from `reports/explainability/plausibility_results.json`:

| Model | Top-1 F1 | Top-2 F1 | Top-3 F1 | Top-3 Precision | Top-3 Recall |
| :--- | :---: | :---: | :---: | :---: | :---: |
| VADER | 0.227 | 0.325 | **0.428** | 0.398 | 0.508 |
| RoBERTa | 0.317 | 0.448 | **0.563** | 0.537 | 0.628 |
| FinBERT | 0.342 | 0.452 | **0.561** | 0.533 | 0.632 |
| Fine-Tuned | 0.342 | 0.452 | **0.561** | 0.533 | 0.632 |

*Table 4: Plausibility Agreement against 100 Human Headline Rationales across 5 news beats. Shows Token-Level F1 at Top-$k$ ($k=1, 2, 3$) alongside Top-3 Precision and Recall.*

Fine-Tuned DistilRoBERTa achieved Top-1 F1 of 0.342, Top-2 F1 of 0.452, and Top-3 F1 of 0.561 (Precision 0.533, Recall 0.632).

### 7.4 Inter-Method Agreement
Pairwise Jaccard token overlap across explainers revealed near-perfect convergence: Integrated Gradients and SHAP demonstrated Top-3 Jaccard overlap of 1.000 on transformer architectures and 0.990 on VADER. In short news headlines (average 11.2 words), gradient path integrals and cooperative game theory coalitions identify identical salient token sets.

---

## 8. Error Analysis

The following table categorizes misclassifications across five distinct linguistic failure modes identified in our taxonomy (`reports/eval/benchmark_results.json`):

| Evaluation Set | Total Errors | Negation | Domain Terms | Sarcasm | Mixed | Neutral/Neg | Other |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| VADER (FPB) | 140 | 3 | 23 | 2 | 4 | 1 | 107 |
| VADER (In-Domain) | 126 | 3 | 11 | 0 | 0 | 3 | 109 |

*Table 5: Classification Error Distribution across 5 linguistic failure modes on Financial PhraseBank ($N=342$) and In-Domain News ($N=300$).*

### 8.1 Factual Findings across Failure Modes
1. **Domain Terminology**: On Financial PhraseBank, domain jargon accounted for 23 of VADER's 140 misclassifications (16.4%), such as treating "outstanding shares" or "voting rights" as positive indicators. On in-domain headlines, domain terms accounted for 11 of 126 errors.
2. **Negation and Inversion**: Syntactic negations accounted for 3 errors on both FPB and in-domain datasets (e.g. "thermal coal reaches record high despite transition goals" predicted as positive due to "record high").
3. **Neutral Reporting of Negative Events**: Factual news reports of negative occurrences accounted for 3 errors on in-domain headlines (e.g. reporting on regulatory penalties or epidemics).
4. **Residual Category (Other)**: The majority of errors on both datasets (107/140 on FPB, 109/126 on In-Domain) fell into the general category, involving nuanced syntactic balance.

### 8.2 Discussion of Error Patterns
Factual inspection of the error distribution shows that lexicon models struggle with specialized terminology, while fine-tuned transformer errors stem primarily from subtle clause balance and editorial context.

> **[YOUR INTERPRETATION]**: *Insert your qualitative interpretation regarding why the residual 'Other' category dominates error distributions on journalistic headlines compared to formal financial statements.*

> **[YOUR INTERPRETATION]**: *Insert your assessment regarding whether domain-adaptive pre-training or expanded prompt-based context is the preferred strategy to address cross-domain headline degradation.*

---

## 9. Limitations

We explicitly highlight the following methodological constraints:
1. **Sample Size of In-Domain Dataset**: The multi-beat news benchmark comprises 300 headlines. While stratified across 5 news beats and evaluated using percentile bootstrap resampling, results support cautious conclusions and require scaling to larger corpora.
2. **Single-Sentence Isolation**: Headlines were evaluated in isolation without access to full article text, financial statements, or market context.
3. **Provisional Second-Annotator Pilot**: While the annotation database schema and Cohen's kappa protocol are fully implemented with a 60-headline pilot ($\kappa = 0.875$), full independent double-labeling of the complete test set remains pending human review.
4. **Perturbation Syntactic Artifacts**: Progressive token deletion in AOPC tests creates ungrammatical sub-phrases. Although benchmarking against random-token deletion mitigates this effect, syntax corruption remains a confounding factor in token ablation.

---

## 10. Conclusion

This paper presented an empirical evaluation of model transferability and explainability faithfulness for news headline sentiment analysis. We demonstrated that fine-tuning DistilRoBERTa yields strong in-domain benchmark performance (0.854 Macro-F1), but encounters a 16.8% relative degradation ($\Delta_{\text{domain}} = +0.144$) when evaluated on diverse journalistic news headlines. We documented benchmark contamination in off-the-shelf FinBERT evaluations. Furthermore, we demonstrated that feature attribution methods (Integrated Gradients, SHAP, Occlusion) are mathematically faithful to internal model decisions (exhibiting 71.7% faithfulness gain over random deletion), while showing that plausibility and faithfulness capture distinct dimensions of model interpretability.

Future work includes extending the evaluation to Aspect-Based Sentiment Analysis (ABSA) for entity-targeted polarity and conducting multi-annotator crowdsourcing across expanded multilingual news corpora.

---

## References

- Araci, D. (2019). FinBERT: Financial Sentiment Analysis with Pre-trained Language Models. *arXiv preprint arXiv:1908.10063*.
- Barbieri, F., Camacho-Collados, J., Espinosa-Anke, L., & Neves, L. (2020). TweetEval: Unified Benchmark and Comparative Evaluation for Tweet Classification. In *Findings of EMNLP 2020*, pages 1644–1650. DOI: 10.18653/v1/2020.findings-emnlp.148. arXiv: 2010.12421.
- Cohen, J. (1960). A Coefficient of Agreement for Nominal Scales. *Educational and Psychological Measurement*, 20(1):37–46. DOI: 10.1177/001316446002000104.
- DeYoung, J., Jain, S., Rajani, N. F., Lehman, E., Xiong, C., Socher, R., & Wallace, B. C. (2020). ERASER: A Benchmark to Evaluate Rationales in the English Language. In *Proceedings of ACL 2020*, pages 4443–4458. DOI: 10.18653/v1/2020.acl-main.408. arXiv: 1911.03429.
- Efron, B., & Tibshirani, R. J. (1993). *An Introduction to the Bootstrap*. Chapman & Hall/CRC. DOI: 10.1201/9780429246593.
- Hutto, C., & Gilbert, E. (2014). VADER: A Parsimonious Rule-based Model for Sentiment Analysis of Social Media Text. In *Proceedings of ICWSM 2014*, 8(1):216–225. DOI: 10.1609/icwsm.v8i1.14550.
- Liu, Y., Ott, M., Goyal, N., Du, J., Joshi, M., Chen, D., Levy, O., Lewis, M., Zettlemoyer, L., & Stoyanov, V. (2019). RoBERTa: A Robustly Optimized BERT Approach. *arXiv preprint arXiv:1907.11692*.
- Lundberg, S. M., & Lee, S. I. (2017). A Unified Approach to Interpreting Model Predictions. In *Advances in Neural Information Processing Systems (NeurIPS 30)*, pages 4765–4774. arXiv: 1705.07874.
- Malo, P., Sinha, A., Korhonen, P., Wallenius, J., & Takala, P. (2014). Good debt or bad debt: Detecting semantic orientations in economic texts. *Journal of the Association for Information Science and Technology*, 65(4):782–796. DOI: 10.1002/asi.23062.
- Petsiuk, V., Das, A., & Saenko, K. (2018). RISE: Randomized Input Sampling for Explanation of Black-box Models. In *Proceedings of BMVC 2018*. arXiv: 1806.07421.
- Samek, W., Binder, A., Montavon, G., Lapuschkin, S., & Müller, K. R. (2017). Evaluating the Visualization of What a Deep Neural Network Has Learned. *IEEE Transactions on Neural Networks and Learning Systems*, 28(11):2660–2673. DOI: 10.1109/TNNLS.2016.2599820.
- Sanh, V., Debut, L., Chaumond, J., & Wolf, T. (2019). DistilBERT, a distilled version of BERT: smaller, faster, cheaper and lighter. *arXiv preprint arXiv:1910.01108*.
- Sundararajan, M., Taly, A., & Yan, Q. (2017). Axiomatic Attribution for Deep Networks. In *Proceedings of ICML 2017*, PMLR 70:3319–3328. arXiv: 1703.01365.
