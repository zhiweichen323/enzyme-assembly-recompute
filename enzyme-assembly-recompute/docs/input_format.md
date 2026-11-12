# Input specification

The default input is `data/analysis_input_100.csv`, an UTF-8 CSV with BOM, one header, and 100 data rows. It contains five metadata/target columns and fourteen numeric feature columns.

## Metadata and target

| Column | Contract |
|---|---|
| `gene` | Unique, non-empty entry identifier |
| `pathway` | Non-empty group identifier |
| `label` | `positive` or `negative` |
| `state` | Source assembly/localization annotation |
| `y` | `1` for positive, `0` for negative; must agree with label |

The runner rejects missing required columns, duplicate identifiers, inconsistent targets, non-finite feature values, and class counts differing from the configured guards. Missing values are not imputed.

## Features

| Order | Column | Interpretation |
|---:|---|---|
| 1 | `length` | Residue count |
| 2 | `net_charge_count` | Simplified K+R−D−E count |
| 3 | `charge_density` | Charge count divided by length |
| 4 | `positive_frac` | Positive-residue fraction |
| 5 | `negative_frac` | Negative-residue fraction |
| 6 | `aromatic_frac` | F/Y/W fraction |
| 7 | `low_complexity_frac` | Low-complexity proxy |
| 8 | `charge_patterning_kappa` | Charge-patterning proxy |
| 9 | `disorder_proxy` | Disorder proxy |
| 10 | `pI_approx` | Approximate isoelectric point |
| 11 | `amyloid_proxy` | Amyloid-window proxy |
| 12 | `hydrophobic_patch_len` | Longest hydrophobic patch |
| 13 | `hydrophobic_patch_density` | Hydrophobic-patch density |
| 14 | `aggregation_prone_frac` | Aggregation-prone residue fraction |

Original-to-normalized names are provided in [feature_dictionary.csv](../data/feature_dictionary.csv). The runner selects columns by these names; identifiers and state labels are not primary model features.

Proxy-feature algorithms are upstream definitions. Their exact regeneration requires the missing original feature module; this workflow starts from the supplied numeric table.

## Bundled data and modifications

S1 contains source annotations; S2 contains reported group counts; S3 contains 105 feature records. The primary input excludes five provisional entries, retains the reported numeric strings, and adds `y`.

CSV bytes, including BOM and line endings, are preserved for provenance. `.gitattributes` disables Git line-ending conversion for CSV files.

Alternative datasets require explicit provenance, consistent labels and feature definitions, updated count guards, and valid two-class coverage in every training fold. Pathway aggregation also requires uniform labels within a group and at least two groups per class. Reference numerical comparisons apply only to the bundled input and its documented settings.
