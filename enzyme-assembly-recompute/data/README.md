# Input data

The default analysis uses `analysis_input_100.csv`: 100 protein entries, 14 numeric features, 39 positive labels, and 61 negative labels.

The dataset supports a feature-table analysis motivated by membraneless-organelle research. Rows are proteins, not whole organelles; positive labels combine LLPS and other assembly states. Background and label interpretation are described in [Biological background (中文)](../docs/biological_background.md).

| File | Purpose |
|---|---|
| `table_s1_annotations.csv` | Source annotations and evidence summaries |
| `table_s2_pathways_as_reported.csv` | Source pathway counts, including recorded inconsistencies |
| `table_s3_features_as_reported.csv` | Source feature table with three-decimal display values |
| `analysis_input_100.csv` | Binary-labelled subset with an added 0/1 target |
| `excluded_provisional_5.csv` | Provisional entries excluded from the primary task |
| `feature_dictionary.csv` | Original and normalized feature names |
| `input_audit.json` | Known quality issues and extraction checks |
| `rnp_control_gene_list.txt` | Gene list only; not a complete RNP feature input |

[Input specification](../docs/input_format.md) · [Data card](../docs/data_sources.md) · [Provenance](../reference/data_provenance.json)
