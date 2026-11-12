# Contributing

## Bug reports

Use the repository issue form. Include the snapshot or commit, Python and dependency versions, full command, configuration, expected behavior, actual behavior, and a minimal reproduction. Numerical reports should also include the input SHA256 and the relevant `summary.json` fields.

## Development checks

Install `requirements-tested.txt` in a local environment, then run from the repository root:

```bash
./.venv/bin/python -m unittest discover -s tests -v
./.venv/bin/python tools/check_repository.py
./.venv/bin/python run_analysis.py --config configs/quick.json --output results/development_check
./.venv/bin/python tools/check_reference.py --results results/development_check
```

Use a new output directory for another run. Changes affecting resampling should also be checked with the main configuration.

## Numerical changes

Preserve training/test separation, fold-local preprocessing, label meaning, and the distinction between conditional bootstrap and model-refitting uncertainty. Changes to data, features, estimators, seeds, or resampling rules require an explicit method description and a separate numerical baseline.

The frozen reference represents a specific input and configuration. Its values should not be overwritten to conceal a discrepancy. Report both the reason for a baseline update and the validation supporting it.

## Pull requests

Describe the problem, resulting behavior, and executed checks. Link related issues where applicable. Keep generated runs under the ignored `results/` directory. Preserve CSV bytes unless a documented dataset revision is intended; `.gitattributes` disables CSV line-ending conversion.

Public documentation should describe the software independently of any local workstation, account, or prior conversation. Repository links and images should use relative paths.
