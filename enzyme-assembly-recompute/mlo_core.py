"""Transparent numerical core for the supplied rounded Table S3 data.

This is a new implementation, not the author's missing analysis package.
Labels are 0/1. The objective is mean cross-entropy + lambda/2 * ||w||^2.
"""
from __future__ import annotations
import csv
from pathlib import Path
import numpy as np
from scipy.optimize import minimize
from scipy.special import expit
from scipy.stats import rankdata

FEATURES = (
    'length', 'net_charge_count', 'charge_density', 'positive_frac',
    'negative_frac', 'aromatic_frac', 'low_complexity_frac',
    'charge_patterning_kappa', 'disorder_proxy', 'pI_approx',
    'amyloid_proxy', 'hydrophobic_patch_len', 'hydrophobic_patch_density',
    'aggregation_prone_frac',
)


def load_data(path: str | Path):
    with Path(path).open(encoding='utf-8-sig', newline='') as stream:
        reader = csv.DictReader(stream)
        required = {'gene', 'pathway', 'label', 'state', 'y', *FEATURES}
        missing = required - set(reader.fieldnames or [])
        if missing:
            raise ValueError(f'Missing input columns: {sorted(missing)}')
        rows = list(reader)
    if not rows:
        raise ValueError('Input has no data rows.')
    if len({r['gene'] for r in rows}) != len(rows):
        raise ValueError('Duplicate gene identifiers in analysis input.')
    for row in rows:
        if row['label'] not in {'positive', 'negative'}:
            raise ValueError(f"Non-binary label: {row['gene']}")
        if row['y'] != ('1' if row['label'] == 'positive' else '0'):
            raise ValueError(f"label and y disagree: {row['gene']}")
        if not row['gene'].strip() or not row['pathway'].strip():
            raise ValueError('Blank gene or pathway.')
    X = np.array([[float(r[f]) for f in FEATURES] for r in rows], dtype=float)
    y = np.array([int(r['y']) for r in rows], dtype=int)
    if not np.isfinite(X).all():
        raise ValueError('Non-finite feature value; no automatic imputation is performed.')
    if set(y.tolist()) != {0, 1}:
        raise ValueError('Both classes are needed.')
    groups = np.array([r['pathway'] for r in rows])
    return rows, X, y, groups


def loss_and_grad(theta, design, y, lam):
    """design includes an intercept column; theta[0] is not penalized."""
    z = design @ theta
    loss = np.mean(np.logaddexp(0.0, z) - y * z)
    loss += 0.5 * lam * np.dot(theta[1:], theta[1:])
    grad = design.T @ (expit(z) - y) / len(y)
    grad[1:] += lam * theta[1:]
    return float(loss), grad


def fit_and_predict(X_train, y_train, X_test, settings):
    if set(np.asarray(y_train).tolist()) != {0, 1}:
        raise ValueError('Training fold has only one class.')
    mean = X_train.mean(axis=0)
    scale = X_train.std(axis=0, ddof=0)
    scale[scale == 0.0] = 1.0
    standardized = (X_train - mean) / scale
    design = np.column_stack([np.ones(len(y_train)), standardized])
    result = minimize(
        loss_and_grad, np.zeros(design.shape[1]),
        args=(design, y_train, float(settings['lambda'])), jac=True,
        method='L-BFGS-B',
        options={'maxiter': int(settings['max_iter']),
                 'ftol': float(settings['ftol']),
                 'gtol': float(settings['gtol'])},
    )
    if not result.success or not np.isfinite(result.x).all():
        raise RuntimeError(f'Optimizer failed; result is not accepted: {result.message}')
    test_scaled = (X_test - mean) / scale
    margin = result.x[0] + test_scaled @ result.x[1:]
    scores = expit(margin)
    model = {
        'mean': mean.tolist(), 'scale': scale.tolist(),
        'intercept': float(result.x[0]), 'weights': result.x[1:].tolist(),
        'lambda': float(settings['lambda']), 'train_n': int(len(y_train)),
        'train_positive_n': int(np.sum(y_train)),
        'train_negative_n': int(len(y_train) - np.sum(y_train)),
        'optimizer': {'success': True, 'iterations': int(result.nit),
                      'objective': float(result.fun),
                      'gradient_inf_norm': float(np.max(np.abs(result.jac))),
                      'message': str(result.message)},
    }
    return scores, model


def crossval_predictions(X, y, settings, groups=None, keep_models=False):
    """Return pooled out-of-fold scores. No AUC is computed inside a fold."""
    n = len(y)
    scores = np.empty(n, dtype=float)
    seen = np.zeros(n, dtype=int)
    models = []
    test_sets = ([np.array([i]) for i in range(n)] if groups is None else
                 [np.flatnonzero(groups == g) for g in dict.fromkeys(groups.tolist())])
    for fold_id, test in enumerate(test_sets, 1):
        train_mask = np.ones(n, dtype=bool)
        train_mask[test] = False
        train = np.flatnonzero(train_mask)
        pred, model = fit_and_predict(X[train], y[train], X[test], settings)
        scores[test] = pred
        seen[test] += 1
        if keep_models:
            model.update({'fold_id': fold_id, 'train_indices': train.tolist(),
                          'test_indices': test.tolist(),
                          'test_raw_features': X[test].tolist(),
                          'test_scores': pred.tolist()})
            models.append(model)
    if not np.all(seen == 1):
        raise RuntimeError('Every sample must receive exactly one held-out prediction.')
    return scores, models


def auc_score(y, scores):
    y, scores = np.asarray(y), np.asarray(scores, dtype=float)
    if len(y) != len(scores) or not np.isfinite(scores).all():
        raise ValueError('Invalid labels/scores for AUC.')
    n_pos = int(np.sum(y == 1)); n_neg = int(np.sum(y == 0))
    if n_pos == 0 or n_neg == 0:
        raise ValueError('AUC needs at least one member of each class.')
    ranks = rankdata(scores, method='average')
    return float((ranks[y == 1].sum() - n_pos * (n_pos + 1) / 2) / (n_pos * n_neg))


def roc_points(y, scores):
    y, scores = np.asarray(y), np.asarray(scores)
    order = np.argsort(-scores, kind='stable')
    ys, ss = y[order], scores[order]
    ends = np.r_[np.flatnonzero(np.diff(ss) != 0), len(ss) - 1]
    tp = np.cumsum(ys)[ends]
    fp = ends + 1 - tp
    return np.r_[0., fp / np.sum(y == 0)], np.r_[0., tp / np.sum(y == 1)]


def permutation_worker(payload):
    index, X, y_perm, settings, groups, include_lpo = payload
    pred, _ = crossval_predictions(X, y_perm, settings)
    loo = auc_score(y_perm, pred)
    lpo = None
    if include_lpo:
        pred_group, _ = crossval_predictions(X, y_perm, settings, groups=groups)
        lpo = auc_score(y_perm, pred_group)
    return index, loo, lpo


def permutation_summary(observed, null):
    null = np.asarray(null, dtype=float)
    b = len(null)
    if not b:
        return None
    gt, ge = int(np.sum(null > observed)), int(np.sum(null >= observed))
    return {'n': b, 'null_mean': float(null.mean()),
            'null_std_ddof1': float(null.std(ddof=1)) if b > 1 else None,
            'count_gt': gt, 'count_ge': ge,
            'p_raw_gt': gt / b, 'p_raw_ge': ge / b,
            'p_plus1_ge': (ge + 1) / (b + 1),
            'tail': 'upper', 'unit': 'individual protein labels',
            'note': 'No pathway-constrained permutation. This does not correct label/reporting bias.'}


def bootstrap_fixed_oof(y, scores, replicates, seed):
    """Stratified paired bootstrap of fixed OOF scores; NO model refitting."""
    rng = np.random.default_rng(seed)
    pos, neg = np.flatnonzero(y == 1), np.flatnonzero(y == 0)
    values = np.empty(replicates)
    for i in range(replicates):
        idx = np.r_[rng.choice(pos, size=len(pos), replace=True),
                    rng.choice(neg, size=len(neg), replace=True)]
        values[i] = auc_score(y[idx], scores[idx])
    return values


def aggregate_pathways(X, y, groups):
    rows, labels, names = [], [], []
    for group in dict.fromkeys(groups.tolist()):
        idx = np.flatnonzero(groups == group)
        if len(np.unique(y[idx])) != 1:
            raise ValueError(f'Non-uniform pathway label: {group}')
        rows.append(np.r_[X[idx].mean(axis=0), X[idx].std(axis=0, ddof=0), len(idx)])
        labels.append(y[idx[0]]); names.append(group)
    return np.array(rows), np.array(labels), names


def bh_adjust(pvalues):
    values = np.asarray(pvalues, dtype=float)
    result = np.full(len(values), np.nan)
    valid = np.flatnonzero(np.isfinite(values))
    if not len(valid):
        return result
    order = valid[np.argsort(values[valid])]
    adjusted = values[order] * len(order) / np.arange(1, len(order) + 1)
    result[order] = np.minimum(1., np.minimum.accumulate(adjusted[::-1])[::-1])
    return result
