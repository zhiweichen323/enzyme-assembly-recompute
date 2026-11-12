# Methods

## Classification task

The biological motivation is the organization of metabolic proteins in the context of membraneless organelles and intracellular assemblies. The computational hypothesis is narrower: whether 14 precomputed sequence descriptors provide predictive information about the supplied binary assembly annotations. Each sample is a protein entry, not an organelle.

The supplied label set combines LLPS, filaments, amyloids, and stable oligomers. A positive label may describe assembly participation rather than independent assembly-driving ability; a negative label is not an exhaustive test across conditions. Consequently, the classifier target is the source assembly label, not a universal LLPS phenotype. Background concepts and literature are available in [Biological background (中文)](biological_background.md).

The fitted model contains scaling parameters, an intercept, and feature weights. Held-out classification statistics evaluate the predictive information of this representation. The workflow does not simulate molecular dynamics, identify causal environmental triggers, or calculate organelle function, enzyme kinetics, or metabolic flux.

## Preprocessing and model

For feature j, training-fold values define the mean and population standard deviation:

$$
x'_{ij}=(x_{ij}-\mu_j)/s_j.
$$

Zero standard deviations are replaced by one. Test samples use the training-fold transformation.

Logistic regression uses:

$$
z_i=b+\sum_jw_jx'_{ij},\qquad p_i=\frac1{1+e^{-z_i}}.
$$

The objective is:

$$
J=-\frac1n\sum_i[y_i\log p_i+(1-y_i)\log(1-p_i)]+\frac\lambda2\sum_jw_j^2.
$$

The intercept is unpenalized. The implementation uses SciPy L-BFGS-B, stable `logaddexp`/`expit`, and an analytic gradient. Optimizer success is required. The default fitting settings are recorded in the configuration files.

## Cross-validation

Leave-one-out validation fits a new scaler and classifier for each held-out protein. Scores are pooled before computing one ROC AUC. Individual single-class test folds do not receive their own AUC.

Leave-pathway-out validation excludes every member of a selected group. Its pooled protein-level AUC is distinct from pathway-aggregate classification.

AUC is checked using both average ranks and direct positive-negative comparisons, with score ties contributing one half. The bundled dataset yields 39 × 61 = 2379 pairs; those pairs are not independent biological samples.

## Label permutations

The feature matrix remains fixed while individual protein labels are shuffled, preserving class totals. The entire enabled fitting and holdout procedure is repeated. Strict and inclusive upper-tail fractions and the finite-permutation estimate are exported:

$$
p_{+1}=\frac{1+\#(AUC_{perm}\ge AUC_{obs})}{B+1}.
$$

The workflow does not implement constrained pathway-level permutations. Exchangeability under group dependence and literature ascertainment are separate assumptions.

## Conditional bootstrap

Saved out-of-fold label-score records are sampled with replacement within each class, preserving class totals. AUC is recalculated without refitting models. The 2.5% and 97.5% linear quantiles define the reported percentile interval.

This procedure estimates variability conditional on the saved predictions. It does not include model-refitting or pathway-resampling uncertainty and is not asserted to match the source manuscript's unspecified bootstrap implementation.

## Pathway aggregation

Each uniformly labelled pathway becomes one record containing 14 feature means, 14 population standard deviations, and protein count. For the reference data, 25 records and 29 features are evaluated by pooled leave-one-record-out predictions.

## Supplementary tests

Positive-negative feature comparisons use asymptotic two-sided Mann–Whitney tests. LLPS, filament, and oligomer groups are compared with Kruskal–Wallis; the singleton amyloid group is excluded. BH-adjusted q-values are additional implementation outputs.

Small groups, related proteins, correlated features, and annotation quality limit interpretation. A weak classifier does not establish that all sequence representations are uninformative, and non-significance is not evidence of equivalence.

## Implementation lineage

The mathematical core is unchanged from the frozen version 0.1.0 baseline. The workflow is an independent implementation of the feature-table analysis; upstream feature-generation code and complete primary-analysis software are not part of this snapshot. See [Reproducibility](../REPRODUCIBILITY.md) and the [data card](data_sources.md).
