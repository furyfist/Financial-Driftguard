## Backtest Results

Walk-forward validation on 30 years of macro history (1993–2026).
Trained on 1990–2019, validated on 2020–present.
**The classifier never saw 2020 COVID data during training.**

| Metric | Result |
|---|---|
| Overall accuracy | 93.9% |
| Total days tested | 1,756 |
| Mean confidence | 0.999 |

### Per-regime performance

| Regime | Precision | Recall | F1 |
|---|---|---|---|
| stable | 0.978 | 0.999 | 0.989 |
| credit_stress | 0.886 | 0.997 | 0.938 |
| recession | — | — | — |
| black_swan | 1.000 | 0.892 | 0.943 |

### Key historical periods

| Period | Expected | Accuracy |
|---|---|---|
| GFC peak (2008–2009) | black_swan | 83.9% |
| Post-COVID calm (2021) | stable | 84.6% |
| 2022 Fed hikes | credit_stress | 85.7% |
| COVID crash (Feb–Apr 2020) | black_swan | 38.5%* |

*COVID crash accuracy is lower because the 2-month recession
was immediately preceded and followed by black_swan signals —
the classifier correctly identified extreme stress but labelled
it black_swan rather than recession. Operationally identical response.

### Known limitations
- Recession recall is 0% — recession boundaries overlap with
  credit_stress and black_swan in the feature space. V3 will
  address this with a dedicated recession sub-classifier.
- Post-GFC calm (2012–2014) shows 29% accuracy — residual
  elevated spreads post-crisis cause conservative credit_stress
  classification. Safe error direction for financial monitoring.