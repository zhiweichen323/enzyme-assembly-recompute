# Reproducibility

## Scope

This workflow recomputes classification statistics from a fixed, rounded feature table. It does not regenerate the sequence features, establish the underlying assembly annotations experimentally, or reproduce every reported manuscript value.

The frozen numerical reference was produced by version 0.1.0. Version 0.2.0 retained the same numerical core and CSV bytes, and added configuration validation, explicit run-state handling, and public documentation. Version 0.2.1 clarifies the membraneless-organelle research context, label scope, and generated report text, while retaining the numerical core, configurations, and CSV bytes. Regression checks compare numerical outputs rather than requiring identical reporting code hashes.

Version 0.2.2 expands the Chinese usage walkthrough and Windows command examples; its numerical algorithms, configurations, and input bytes are unchanged from 0.2.1.

## Reference environment

| Component | Version or setting |
|---|---|
| Python | 3.12; original reference run used 3.12.14 |
| NumPy | 2.3.5 |
| SciPy | 1.17.0 |
| Matplotlib | 3.10.8 |
| Input SHA256 | `08d3fea1b0230201498ce470eeafaa04c35878d557c2ee2bb59f23e22158fba3` |
| Objective | Mean binary cross-entropy + lambda/2 times squared weights |
| Intercept penalty | None |
| Lambda | 1 |
| Fold standard deviation | Population SD, `ddof=0` |
| Optimizer | L-BFGS-B; max_iter 2000, ftol 1e-8, gtol 1e-5 |
| Permutations | 300, seed 20261111 |
| Conditional bootstrap | 200, seed 20261112 |

Each training fold fits its own scaler and model. Pooled held-out probabilities, not training probabilities, are used for validation AUC. BLAS thread counts are set to one per process by the runner.

## Verification

```bash
./.venv/bin/python -m unittest discover -s tests -v
./.venv/bin/python tools/check_repository.py
./.venv/bin/python run_analysis.py --config configs/main.json --output results/reproduction
./.venv/bin/python tools/check_reference.py --results results/reproduction
```

The tests cover nine numerical and holdout checks, plus configuration rejection, failed/interrupted run states, runner-failure integration, and report metadata. The reference checker permits an absolute tolerance of 1e-6 for individual scores, and compares AUC and applicable resampling statistics against the frozen reference. Settings and input hashes must match. Resampling comparisons additionally require the same seed and replicate count.

The Actions workflow includes Ubuntu and Windows jobs. Local verification is distinct from a GitHub-hosted run; actual workflow status is attached to the corresponding repository commit.

## Statistical conventions

- **Permutation unit:** individual protein labels; class counts are preserved. The entire fitting and validation pipeline is repeated for each permutation. Pathway-constrained exchangeability is not implemented.
- **Tail probabilities:** strict and inclusive upper-tail fractions are exported, together with `(count_ge + 1) / (B + 1)`.
- **Bootstrap unit:** fixed out-of-fold label-score pairs, sampled within each class. No model refit or pathway-level resampling is performed. The interval is conditional on those saved predictions.
- **Pathway aggregation:** 14 means, 14 population standard deviations, and sample count; 25 pathway records in the supplied dataset.
- **Feature comparisons:** asymptotic two-sided Mann–Whitney and Kruskal–Wallis; BH corrections are additional outputs of this implementation.

## Data limitations

The provided feature values have three-decimal display precision. Some sequence-to-feature mappings, duplicated vectors, and pathway counts require review. Labels combine several assembly states and may reflect literature ascertainment. See the [data card](docs/data_sources.md).

Full-precision features, the original feature module, complete primary-analysis code, exact regularization conventions, and original resampling details are not available in this snapshot. The causes of the numerical differences have not been isolated. Matching a target metric through post hoc data or parameter selection would change the analysis being reproduced.
