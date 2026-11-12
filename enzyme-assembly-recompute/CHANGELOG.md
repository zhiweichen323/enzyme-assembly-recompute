# Changelog

## 0.2.2 — 2026-11-12

- Expand the Chinese README into a step-by-step workflow covering commands, purpose, expected output, and handoffs between analysis scripts.
- Explain the relationship between quick and main runs, completion checks, reference comparisons, and per-protein reconstruction.
- Add native Windows command equivalents, interpreter selection guidance, and troubleshooting.
- Preserve numerical algorithms, configurations, input bytes, and reference results; update the software version only.

## 0.2.1 — 2026-11-12

### Documentation

- Explain the connection to membraneless organelles and the precise metabolic protein assembly classification question in both READMEs.
- Add a biological background document with verified literature and explicit distinctions between proteins, organelles, LLPS, and other assembly states.
- Clarify samples, labels, fitted parameters, analysis steps, and interpretation limits in usage, methods, input documentation, and generated reports.
- Explain repository-relative documentation links and the requirements for local navigation.

### Numerical compatibility

- Numerical core, configuration files, input tables, and frozen numerical outputs are unchanged.
- Runner version and report text are updated; the fitting and resampling algorithms are unchanged.

## 0.2.0 — 2026-11-12

### Added

- Public-facing Chinese and English READMEs.
- Reproducibility, citation, and license-status records.
- Configuration JSON Schema and preflight validation.
- Explicit failed and interrupted run states.
- English `report.md`, retaining the existing Chinese report output.
- Bug-report and pull-request templates, repository-document checks, and workflow-contract tests.

### Changed

- Reports use actual input dimensions rather than fixed sample counts.
- Publication handover instructions are separated from public software documentation.
- Reference comparisons include applicable leave-pathway-out permutation statistics.

### Numerical compatibility

- Numerical core and input CSV bytes remain unchanged from 0.1.0.
- The default numerical reference remains the same; reporting and validation code hashes change in this version.

## 0.1.0 — 2026-11-12

- Initial source-run workflow, supplied feature tables, fold-level model exports, frozen numerical examples, and cross-platform workflow configuration.
