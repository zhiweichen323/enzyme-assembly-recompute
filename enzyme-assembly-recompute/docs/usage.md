# Usage

Examples use the Linux/WSL interpreter path from [Installation](installation.md). Commands operate on a checked-out source tree.

## What a run produces

A run evaluates whether the supplied sequence-derived features distinguish metabolic protein assembly labels, a specific analysis motivated by membraneless-organelle research. Input rows are protein entries. The target includes multiple assembly states, so the resulting scores refer to assembly annotations rather than verified intracellular LLPS probabilities.

The input is an existing feature CSV; the analysis produces held-out scores, validation statistics, fitted parameters, and reports. It does not start from FASTA sequences or simulate a physical organelle. See [Methods](methods.md) and [Biological background (中文)](biological_background.md) for the scientific scope.

## Validate an input and configuration

```bash
./.venv/bin/python run_analysis.py --config configs/quick.json --check-only
```

Expected bundled input: 100 rows, 14 features, 39 positive labels, 61 negative labels, and 25 classifiable pathway groups. The command validates configuration ranges, input dimensions, label consistency, and training-class coverage without creating run outputs.

Configuration syntax is described by [configs/schema.json](../configs/schema.json). The runner also performs runtime preflight validation.

## Quick and main analyses

```bash
./.venv/bin/python run_analysis.py --config configs/quick.json
cat results/quick/report.md
```

```bash
./.venv/bin/python run_analysis.py --config configs/main.json
cat results/main/report.md
```

| Configuration | Permutations | Conditional bootstrap replicates | Output |
|---|---:|---:|---|
| `quick.json` | 10 | 50 | `results/quick/` |
| `main.json` | 300 | 200 | `results/main/` |

Both configurations fit the same primary models. Each invocation starts independently from the input CSV. The quick p-value is a smoke-test result with limited Monte Carlo resolution.

## CLI arguments

| Argument | Meaning |
|---|---|
| `--version` | Print the software snapshot version |
| `--config PATH` | JSON configuration; default `configs/quick.json` |
| `--workers N` | Override permutation worker count |
| `--output PATH` | Override the output directory |
| `--check-only` | Validate inputs and configuration without analysis |

Relative configuration, input, and output paths are resolved from the repository root. Absolute paths are accepted. Output directories must be absent or empty.

```bash
./.venv/bin/python run_analysis.py --config configs/main.json --workers 2 --output results/run_02
```

## Configuration fields

| Field | Meaning |
|---|---|
| `input_csv`, `output_dir` | Input and output locations |
| `expected_counts` | Optional guards for total and class counts |
| `fit.lambda` | Positive L2 strength |
| `fit.max_iter` | Positive iteration limit |
| `fit.ftol`, `fit.gtol` | Non-negative function tolerance and positive gradient tolerance |
| `permutations` | Positive number of full-pipeline label permutations |
| `bootstrap_replicates` | Number of conditional resamples, at least 2 |
| `seed` | Non-negative integer; bootstrap uses seed + 1 |
| `workers` | Positive worker count |
| `include_leave_pathway_out` | Enable grouped holdout analysis |
| `include_pathway_aggregate` | Enable pathway-summary classification |

Unknown configuration and fitting keys are rejected. Hyperparameter selection is outside the default workflow; selecting values with held-out results requires a separate validation design.

## Run state and failures

`run_status.json` records one of:

| State | Interpretation |
|---|---|
| `running` | Invocation started but has not recorded an outcome |
| `complete` | All requested outputs were generated |
| `failed` | A caught runtime error interrupted analysis; type and message are recorded |
| `interrupted` | A keyboard interrupt was caught |

Invalid configurations are rejected before result creation. Exceptions within an initialized run are recorded before a non-zero exit. Exit code 1 denotes an error; 130 denotes a caught keyboard interrupt. A hard process termination or machine failure may leave `running` because no cleanup handler executes.

Partial files are not a completed run. The current workflow has no automatic resume mechanism; another invocation should use a fresh directory.

## Per-protein explanation

```bash
./.venv/bin/python explain_prediction.py --results results/main --gene PPAT
```

The command reads saved fold parameters and reconstructs the held-out score, without repeating resampling. It generates `prediction_breakdown_PPAT.csv` and a Markdown explanation. The result path must match the selected analysis run.

The explanation shows how standardized features and fitted weights produce the model score. A numerical contribution is not evidence that changing that feature would causally change assembly.

## Numerical reference comparison

```bash
./.venv/bin/python tools/check_reference.py --results results/main
```

The checker requires matching input bytes and fitting settings. It compares frozen held-out scores and AUCs. Resampling statistics are additionally compared when seed and replicate counts match. This is a regression check against the bundled numerical baseline, not a test of agreement with the source manuscript.

## Outputs

| File | Contents |
|---|---|
| `report.md`, `REPORT_结果解读.md` | English and Chinese reports |
| `summary.json` | Metrics and analysis conventions |
| `loo_predictions.csv` | One held-out probability per input row |
| `loo_fold_models.json` | Fold indices, scalers, fitted weights, and test scores |
| `auc_pairwise_comparisons.csv` | Cross-class comparisons used to independently verify AUC |
| `permuted_labels.csv` | Actual label assignments for each permutation |
| `permutation_aucs.csv` | Permutation AUCs for enabled holdout tasks |
| `bootstrap_aucs.csv` | Conditional bootstrap AUCs |
| `leave_pathway_predictions.csv` | Grouped holdout predictions |
| `pathway_aggregate_input.csv`, `pathway_aggregate_predictions.csv` | Pathway-level inputs and held-out scores |
| `feature_tests.csv` | Supplementary tests and BH-adjusted values |
| `roc.png/pdf`, `permutation_null.png/pdf` | Static figures |
| `model_final.json` | Separate full-input model fit |
| `paper_comparison.csv` | Manuscript values and current values with convention notes |
| `environment.json`, `config_used.json` | Versions, hashes, and resolved configuration |
| `progress.log`, `run_status.json` | Progress and outcome |

Run-specific paths are retained in local metadata for traceability. Only curated, path-normalized examples are stored in the repository.
