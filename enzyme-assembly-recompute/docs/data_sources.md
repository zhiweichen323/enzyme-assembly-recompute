# Data card

## Dataset identification

Dataset: metabolic protein assembly annotation and sequence-feature tables.

Source title: *A Systematic Test of Condensate Predictability and Its Implications for Metabolic Route Selection in Cancer*.

The source snapshot contains supplementary Tables S1–S3. A verified publication identifier and complete public analysis repository are not included in the available provenance metadata.

## Composition

| Table or subset | Contents |
|---|---|
| S1 | 105 protein entries, labels, states, groups, and evidence summaries |
| S2 | Reported counts for 26 pathway or functional groups |
| S3 | The same 105 entries and 14 three-decimal feature values |
| Primary input | 100 entries: 39 positive and 61 negative; 25 classifiable groups |
| Excluded input | Five provisional entries: ODC1, SRM, SMS, AMD1, AZIN1 |

The primary model uses only the 14 numeric features. Protein identifiers, pathways, and states remain metadata or grouping variables.

## Extraction and provenance

Table cells were extracted directly from DOCX rather than OCR. S1/S3 metadata were compared row by row. The primary input removes provisional rows and adds a consistent 0/1 target column without changing the reported numbers.

[Provenance metadata](../reference/data_provenance.json) records the original source filename, source checksum, extraction method, and CSV checksums. The primary input SHA256 is:

```text
08d3fea1b0230201498ce470eeafaa04c35878d557c2ee2bb59f23e22158fba3
```

`.gitattributes` disables CSV line-ending conversion so that provenance hashes are preserved across Git platforms. Feature precision is limited to the source table display; these values are not full-precision upstream features.

## Known quality issues

The original values and annotations are retained:

- S2 reports five G-body members while S1/S3 contain six; its total is 104 rather than 105.
- PKM2/PKM and HADHA/HADH respectively share identical 14-dimensional feature vectors.
- CAD is recorded with length 338; sequence mapping or completeness requires verification.
- TAZ requires a stable accession to disambiguate the symbol.
- Negative annotations partly reflect localization or lack of reports and do not demonstrate universal inability to assemble.
- Positive annotations combine several physical states and may include recruited components.

Details are recorded in [input_audit.json](../data/input_audit.json).

## Intended use and limitations

The dataset supports checking a specified feature-table classification workflow. It is not a validated catalogue of every condition under which a protein assembles, an experimental assay, or a source of calibrated intracellular LLPS probabilities.

Literature ascertainment, related proteins, grouping decisions, proxy-feature definitions, and rounding affect interpretation. Current numerical disagreement with the manuscript has not been assigned to a single cause.

## Optional source verification

The Word supplement is not distributed with the repository. A locally held matching source can be checked after installing `requirements-extract.txt`:

```bash
./.venv/bin/python -m pip install -r requirements-extract.txt
./.venv/bin/python tools/verify_source_tables.py --source /path/to/original_supplementary.docx
```

The optional argument is a local path. Verification checks source identity, table cells, and CSV bytes; it does not validate biological annotations.

## Rights and attribution

Data redistribution terms are unspecified in the available source materials. Software and dataset license status are recorded separately in [LICENSE_NOTICE.md](../LICENSE_NOTICE.md). Source attribution is recorded in [CITATION.md](../CITATION.md).
