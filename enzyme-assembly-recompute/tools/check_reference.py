#!/usr/bin/env python3
"""Compare a local run with frozen results for the unchanged supplied inputs."""
from __future__ import annotations
import argparse
import csv
import json
from pathlib import Path
import numpy as np

BASE = Path(__file__).resolve().parents[1]
REFERENCE = BASE / 'examples' / 'reference_run'


def read_predictions(path):
    with Path(path).open(encoding='utf-8-sig', newline='') as stream:
        rows = list(csv.DictReader(stream))
    records = {row['gene']: row for row in rows}
    if len(records) != len(rows):
        raise ValueError('Duplicate gene names in prediction file.')
    return records


def require_close(name, actual, expected, atol=1e-12):
    if not np.allclose(actual, expected, atol=atol, rtol=0):
        raise ValueError(f'{name} differs from the frozen reference: {actual!r} versus {expected!r}')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--results', default='results/main')
    args = parser.parse_args()
    results = Path(args.results).expanduser()
    if not results.is_absolute():
        results = BASE / results
    status = json.loads((results / 'run_status.json').read_text(encoding='utf-8'))
    if status.get('status') != 'complete':
        raise ValueError('The selected run is not marked complete.')
    actual = json.loads((results / 'summary.json').read_text(encoding='utf-8'))
    expected = json.loads((REFERENCE / 'summary.json').read_text(encoding='utf-8'))
    if actual['input_sha256'] != expected['input_sha256']:
        raise ValueError('Different input bytes; this frozen reference does not apply.')
    if actual['settings'] != expected['settings']:
        raise ValueError('Different fitting settings; this frozen reference does not apply.')
    current_rows = read_predictions(results / 'loo_predictions.csv')
    reference_rows = read_predictions(REFERENCE / 'loo_predictions.csv')
    if current_rows.keys() != reference_rows.keys():
        raise ValueError('Different gene identifiers in prediction files.')
    keys = list(reference_rows)
    if any(current_rows[k]['y_true'] != reference_rows[k]['y_true'] for k in keys):
        raise ValueError('Reference labels differ.')
    current_scores = np.array([float(current_rows[k]['probability']) for k in keys])
    reference_scores = np.array([float(reference_rows[k]['probability']) for k in keys])
    max_difference = float(np.max(np.abs(current_scores - reference_scores)))
    require_close('Held-out probabilities', current_scores, reference_scores, atol=1e-6)
    require_close('LOO AUC', actual['loo']['auc'], expected['loo']['auc'])
    checked = ['input_sha256', 'fitting_settings', 'held_out_probabilities', 'loo_auc']
    for key in ('leave_pathway_out', 'pathway_aggregate'):
        if key in actual:
            require_close(key + ' AUC', actual[key]['auc'], expected[key]['auc'])
            checked.append(key + '_auc')
    seed_matches = actual['seed'] == expected['seed']
    for task in ('loo', 'leave_pathway_out'):
        current_permutation = actual.get(task, {}).get('permutation')
        expected_permutation = expected.get(task, {}).get('permutation')
        if seed_matches and current_permutation and expected_permutation and current_permutation['n'] == expected_permutation['n']:
            for statistic in ('count_gt', 'count_ge', 'p_raw_gt', 'p_raw_ge', 'p_plus1_ge'):
                require_close(task + ' permutation ' + statistic,
                              current_permutation[statistic], expected_permutation[statistic])
            checked.append(task + '_permutation_statistics')
    current_bootstrap = actual['loo']['conditional_bootstrap']
    expected_bootstrap = expected['loo']['conditional_bootstrap']
    if seed_matches and current_bootstrap['replicates'] == expected_bootstrap['replicates']:
        require_close('Conditional bootstrap CI', current_bootstrap['percentile_ci95'], expected_bootstrap['percentile_ci95'])
        checked.append('conditional_bootstrap_ci')
    print(json.dumps({'status': 'matched', 'checked': checked,
                      'max_absolute_probability_difference': max_difference,
                      'note': 'Resampling statistics are compared only when seed and replicate count match.'}, ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    main()
