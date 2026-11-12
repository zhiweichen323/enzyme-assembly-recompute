#!/usr/bin/env python3
"""Run a documented recomputation from the supplied Table S3 CSV inputs."""
from __future__ import annotations
import os
# Set before numerical-library imports; tiny matrix fits do not need BLAS fan-out.
for variable in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS'):
    os.environ[variable] = '1'
import argparse
import csv
import hashlib
import json
import multiprocessing as mp
import platform
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from contextlib import contextmanager
from importlib.metadata import version as package_version
from pathlib import Path
import numpy as np
import scipy
from scipy import stats
from mlo_core import (FEATURES, load_data, fit_and_predict, crossval_predictions,
                      auc_score, roc_points, permutation_worker,
                      permutation_summary, bootstrap_fixed_oof,
                      aggregate_pathways, bh_adjust)

BASE = Path(__file__).resolve().parent
VERSION = "0.2.2"


def project_path(value):
    p = Path(value).expanduser()
    return p.resolve() if p.is_absolute() else (BASE / p).resolve()


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def json_safe(value):
    if isinstance(value, dict): return {str(k): json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, np.ndarray)): return [json_safe(v) for v in value]
    if isinstance(value, (np.integer,)): return int(value)
    if isinstance(value, (np.floating, float)):
        return float(value) if np.isfinite(value) else None
    return value


def save_json(path, value):
    Path(path).write_text(json.dumps(json_safe(value), ensure_ascii=False, indent=2, allow_nan=False) + '\n', encoding='utf-8')


def save_csv(path, columns, rows):
    with Path(path).open('w', encoding='utf-8-sig', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)



def validate_config(config, workers_override=None):
    """Validate configuration before creating outputs or fitting any models."""
    if not isinstance(config, dict):
        raise ValueError('Configuration must be a JSON object.')
    allowed = {'$schema', 'input_csv', 'output_dir', 'expected_counts', 'fit',
               'permutations', 'bootstrap_replicates', 'seed', 'workers',
               'include_leave_pathway_out', 'include_pathway_aggregate', 'notes'}
    if set(config) - allowed:
        raise ValueError(f'Unknown configuration keys: {sorted(set(config) - allowed)}')
    if '$schema' in config and not isinstance(config['$schema'], str):
        raise ValueError('$schema must be a string.')
    if 'notes' in config and not isinstance(config['notes'], dict):
        raise ValueError('notes must be an object.')
    for field in ('input_csv', 'output_dir'):
        if not isinstance(config.get(field), str) or not config[field].strip():
            raise ValueError(f'{field} must be a non-empty path string.')
    fit = config.get('fit')
    if not isinstance(fit, dict):
        raise ValueError('fit must be an object.')
    if set(fit) - {'lambda', 'max_iter', 'ftol', 'gtol'}:
        raise ValueError(f'Unknown fit keys: {sorted(set(fit) - {"lambda", "max_iter", "ftol", "gtol"})}')
    for field, allow_zero in [('lambda', False), ('ftol', True), ('gtol', False)]:
        value = fit.get(field)
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError(f'fit.{field} must be a finite number.')
        if not np.isfinite(value) or (value < 0 if allow_zero else value <= 0):
            raise ValueError(f'Invalid fit.{field}: {value!r}')
    integer_values = {
        'fit.max_iter': (fit.get('max_iter'), 1),
        'permutations': (config.get('permutations'), 1),
        'bootstrap_replicates': (config.get('bootstrap_replicates'), 2),
        'seed': (config.get('seed'), 0),
        'workers': (workers_override if workers_override is not None else config.get('workers', 1), 1),
    }
    for field, (value, minimum) in integer_values.items():
        if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
            raise ValueError(f'{field} must be an integer >= {minimum}.')
    for field in ('include_leave_pathway_out', 'include_pathway_aggregate'):
        if not isinstance(config.get(field), bool):
            raise ValueError(f'{field} must be true or false.')
    expected = config.get('expected_counts', {})
    if not isinstance(expected, dict) or set(expected) - {'n', 'positive', 'negative'}:
        raise ValueError('expected_counts may contain n, positive, and negative.')
    for field, value in expected.items():
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            raise ValueError(f'expected_counts.{field} must be a non-negative integer.')


@contextmanager
def track_run_status(output_dir):
    """Record failure or interruption without treating partial output as complete."""
    save_json(output_dir / 'run_status.json', {'status': 'running'})
    try:
        yield
    except KeyboardInterrupt:
        save_json(output_dir / 'run_status.json', {'status': 'interrupted'})
        raise
    except Exception as error:
        save_json(output_dir / 'run_status.json', {
            'status': 'failed', 'error_type': type(error).__name__,
            'error_message': str(error),
        })
        raise

def prediction_rows(records, y, scores):
    return [dict(gene=r['gene'], pathway=r['pathway'], label=r['label'],
                 state=r['state'], y_true=int(y[i]), probability=float(scores[i]),
                 predicted_y_at_0_5=int(scores[i] >= .5))
            for i, r in enumerate(records)]


def write_models(path, models, records, feature_names):
    for model in models:
        model['test_genes'] = [records[i]['gene'] for i in model['test_indices']]
    save_json(path, {'feature_names': list(feature_names),
                     'ordered_genes': [r['gene'] for r in records], 'folds': models,
                     'note': 'Each fold was freshly fitted; held-out labels were not passed to fit.'})


def feature_tests(X, y, records):
    state = np.array([r['state'] for r in records])
    output = []
    for j, name in enumerate(FEATURES):
        pos, neg = X[y == 1, j], X[y == 0, j]
        u = stats.mannwhitneyu(pos, neg, alternative='two-sided', method='asymptotic')
        sets = [X[state == k, j] for k in ('LLPS', 'filament', 'oligomer')]
        try:
            kw = stats.kruskal(*sets)
            h, kp = float(kw.statistic), float(kw.pvalue)
        except ValueError:
            h, kp = float('nan'), float('nan')
        output.append({'feature': name, 'mean_positive': float(pos.mean()),
                       'mean_negative': float(neg.mean()),
                       'mw_u': float(u.statistic), 'mw_p_two_sided': float(u.pvalue),
                       'kw_h': h, 'kw_p': kp,
                       'kw_states': 'LLPS|filament|oligomer', 'amyloid_excluded': True})
    mw_q = bh_adjust([r['mw_p_two_sided'] for r in output])
    kw_q = bh_adjust([r['kw_p'] for r in output])
    for i, record in enumerate(output):
        record['mw_bh_q_14_features'] = float(mw_q[i])
        record['kw_bh_q_14_features'] = float(kw_q[i])
    return output


def make_plots(out, y, scores, group_scores, null, observed, pvalue):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(5.3, 4.4), layout='constrained')
    for name, prediction, color in [('Leave one out', scores, '#23669a'),
                                     ('Leave pathway out', group_scores, '#b77125')]:
        if prediction is None: continue
        fpr, tpr = roc_points(y, prediction)
        ax.plot(fpr, tpr, label=f'{name}: AUC = {auc_score(y, prediction):.4f}', color=color, linewidth=1.8)
    ax.plot([0, 1], [0, 1], '--', color='0.65', linewidth=1)
    ax.set(xlim=(0, 1), ylim=(0, 1.02), xlabel='False positive rate', ylabel='True positive rate', title='Recomputed from supplied rounded Table S3')
    ax.legend(loc='lower right', fontsize=8)
    fig.savefig(out / 'roc.png', dpi=200); fig.savefig(out / 'roc.pdf'); plt.close(fig)
    if len(null):
        fig, ax = plt.subplots(figsize=(6, 4), layout='constrained')
        ax.hist(null, bins=min(25, max(5, len(null) // 10)), color='#9bbdd4', edgecolor='white')
        ax.axvline(observed, color='#b54032', linewidth=2, label=f'Observed AUC = {observed:.4f}')
        ax.set(xlabel='AUC after full label-permutation cross-validation', ylabel='Count',
               title=f'Protein-label permutation: B={len(null)}, plus-one p={pvalue:.4f}')
        ax.legend(fontsize=8)
        fig.savefig(out / 'permutation_null.png', dpi=200); fig.savefig(out / 'permutation_null.pdf'); plt.close(fig)


def make_report(out, summary):
    loo = summary['loo']; group = summary.get('leave_pathway_out')
    perm = loo.get('permutation')
    ci = loo['conditional_bootstrap']['percentile_ci95']
    pairs = loo['pairwise_auc_check']
    text = f'''# 本次重算结果与解读

本程序面向无膜细胞器相关研究，检验14项预先计算的序列特征能否区分来源材料标注的组装阳性、阴性代谢蛋白。每行输入是一个蛋白条目；阳性包含LLPS及其他组装状态，预测分数针对这些标签，不代表已校准的细胞内LLPS概率。

本报告记录当前输入与配置的计算结果，来源手稿的报告值单独列示。

- 输入：{summary['n']}个条目、{summary['n_features']}项特征，{summary['n_positive']}阳性、{summary['n_negative']}阴性。
- 正则化：lambda = {summary['settings']['lambda']}；平均交叉熵 + lambda/2 × 权重平方和；不惩罚截距。
- 标准化：每一折仅使用训练集均值和总体标准差（ddof=0）。
- 主任务留一法AUC：**{loo['auc']:.10f}**；论文报告0.58。
- 阳性平均预测分数：{loo['mean_score_positive']:.6f}；阴性：{loo['mean_score_negative']:.6f}。
- 跨类比较：{pairs['pairs']}对，正确{pairs['wins']}对，并列{pairs['ties']}对，错误{pairs['losses']}对。
- 固定折外分数的分层配对Bootstrap 95%百分位区间：[{ci[0]:.6f}, {ci[1]:.6f}]。
'''
    if perm:
        text += f'''- 完整留一法置换：{perm['n']}次；随机AUC均值{perm['null_mean']:.6f}。
- 原始严格大于p：{perm['p_raw_gt']:.6f}；原始大于等于p：{perm['p_raw_ge']:.6f}；加1校正p：**{perm['p_plus1_ge']:.6f}**。
'''
    if group:
        text += f"- 留通路AUC：**{group['auc']:.10f}**；论文报告0.45。\n"
        if group.get('permutation'):
            text += f"- 留通路加1置换p：{group['permutation']['p_plus1_ge']:.6f}，置换单位为单个蛋白标签。\n"
    if summary.get('pathway_aggregate'):
        agg = summary['pathway_aggregate']
        text += f"- 通路聚合：{agg['n_pathways']}个通路、29项特征，留一法AUC={agg['auc']:.10f}；论文报告0.60。\n"
    text += '''
## 这些数字怎样使用

1. 先查看`loo_predictions.csv`，每行分数来自未用该蛋白训练的模型。
2. `auc_pairwise_comparisons.csv`可以逐对复核AUC；分数使用保存的全精度，避免先四舍五入产生人工并列。
3. `permutation_aucs.csv`记录每次重排标签后重新训练的AUC；`permuted_labels.csv`记录每次实际使用的0/1标签。
4. `bootstrap_aucs.csv`用于检查区间，但这是固定折外分数的条件性Bootstrap，没有重训模型，也未按通路抽样。
5. `loo_fold_models.json`可配合`explain_prediction.py`逐项检查某蛋白的标准化、权重贡献、线性分数与sigmoid。

## 与论文不一致时如何解释

本工具保留补充表的三位小数特征，修正可见附件中的损失—梯度不一致，使用明确写出的lambda和验证规则；它是透明重算，不是已确认的原分析脚本。AUC不一致的具体原因目前不能确定。

尚未确认的复现要素包括：全精度特征矩阵、主任务拟合参数、标准化及优化配置、完整验证代码、置换交换规则，以及Bootstrap抽样和区间算法。RNP对照缺少完整特征实现及相应特征矩阵，未在本工具中生成这部分数值。

数据或参数修订应单独记录，并与固定参考结果区分。输入中的表S2计数差别、重复特征向量和序列映射疑点见`data/input_audit.json`。

`model_final.json`保存全体输入样本另行拟合的模型，折外预测用于性能评估。
'''
    (out / 'REPORT_结果解读.md').write_text(text, encoding='utf-8')
    english = f"""# Analysis report

## Purpose and scope

This analysis is motivated by membraneless-organelle research and tests whether 14 precomputed sequence features distinguish source assembly-positive and assembly-negative metabolic proteins. Each input row is a protein entry. Labels include LLPS and other assembly states; scores refer to these annotations rather than calibrated intracellular LLPS probabilities. The workflow evaluates a statistical classifier, not organelle dynamics or biochemical function.

## Input and model

- Samples: {summary['n']} ({summary['n_positive']} positive, {summary['n_negative']} negative).
- Features: {summary['n_features']}; input SHA256: `{summary['input_sha256']}`.
- L2 lambda: {summary['settings']['lambda']}; mean binary cross-entropy plus lambda/2 times squared weights; intercept unpenalized.
- Standardization: fitted separately in each training fold, population standard deviation (`ddof=0`).

## Results

- Pooled leave-one-out ROC AUC: **{loo['auc']:.10f}**.
- Pairwise check: {pairs['wins']} wins, {pairs['ties']} ties, {pairs['losses']} losses out of {pairs['pairs']} cross-class pairs.
- Conditional bootstrap percentile interval: [{ci[0]:.6f}, {ci[1]:.6f}].
"""
    if perm:
        english += f"- Full-pipeline label permutations: {perm['n']}; raw upper-tail p: {perm['p_raw_ge']:.6f}; plus-one p: **{perm['p_plus1_ge']:.6f}**.\n"
    if group:
        english += f"- Pooled leave-pathway-out ROC AUC: {group['auc']:.10f}.\n"
    english += """
## Interpretation and provenance

The conditional bootstrap resamples fixed label-score pairs within each class; it does not refit models or resample pathways. Permutations exchange individual protein labels. Group exchangeability and literature-label ascertainment remain assumptions requiring assessment.

The supplied feature table is rounded to three decimals. Manuscript values are listed separately in `paper_comparison.csv`; exact agreement with those values has not been established. Input annotation issues are recorded in `data/input_audit.json` in the repository.

`loo_predictions.csv` contains held-out scores; `model_final.json` is a separate fit to all input samples. Training scores from the latter do not replace cross-validation results.
"""
    (out / 'report.md').write_text(english, encoding='utf-8')


def main():
    parser = argparse.ArgumentParser(description='Recompute enzyme assembly classification from supplied Table S3.')
    parser.add_argument('--version', action='version', version=f'%(prog)s {VERSION}')
    parser.add_argument('--config', default='configs/quick.json')
    parser.add_argument('--workers', type=int, default=None)
    parser.add_argument('--output', default=None, help='New empty output folder, relative to project root unless absolute.')
    parser.add_argument('--check-only', action='store_true')
    args = parser.parse_args()
    config_path = project_path(args.config)
    config = json.loads(config_path.read_text(encoding='utf-8-sig'))
    validate_config(config, args.workers)
    settings = config['fit']
    input_path = project_path(config['input_csv'])
    records, X, y, groups = load_data(input_path)
    expected = config.get('expected_counts', {})
    actual = {'n': len(y), 'positive': int(y.sum()), 'negative': int((y == 0).sum())}
    if any(actual.get(k) != v for k, v in expected.items()):
        raise ValueError(f'Expected counts {expected}, actual {actual}; inspect input before running.')
    workers = args.workers if args.workers is not None else int(config.get('workers', 1))
    if workers < 1: raise ValueError('workers must be at least 1.')
    print(f"Input OK: n={len(y)}, features={X.shape[1]}, positive={y.sum()}, negative={(y == 0).sum()}, pathways={len(np.unique(groups))}", flush=True)
    print(f'Input SHA256: {digest(input_path)}', flush=True)
    if min(actual['positive'], actual['negative']) < 2:
        raise ValueError('Leave-one-out validation requires at least two members of each class.')
    if config['include_leave_pathway_out']:
        for group in np.unique(groups):
            if len(np.unique(y[groups != group])) != 2:
                raise ValueError(f'Holding out pathway {group!r} leaves only one training class.')
    if config['include_pathway_aggregate']:
        _, pathway_labels, _ = aggregate_pathways(X, y, groups)
        if min(int(pathway_labels.sum()), int((pathway_labels == 0).sum())) < 2:
            raise ValueError('Pathway aggregation requires at least two pathway records per class.')
    if args.check_only:
        return 0
    out = project_path(args.output or config['output_dir'])
    if out.exists() and any(out.iterdir()):
        raise ValueError(f'Output directory is not empty: {out}. Use --output results/new_run_name.')
    out.mkdir(parents=True, exist_ok=True)
    with track_run_status(out):
        start = time.monotonic()
        def log(message):
            print(message, flush=True)
            with (out / 'progress.log').open('a', encoding='utf-8') as f: f.write(message + '\n')
        save_json(out / 'config_used.json', config | {'workers_effective': workers, 'output_effective': str(out)})
        save_json(out / 'environment.json', {'python': sys.version, 'platform': platform.platform(),
                  'software_version': VERSION, 'numpy': np.__version__, 'scipy': scipy.__version__,
                  'matplotlib': package_version('matplotlib'), 'input_sha256': digest(input_path),
                  'code_sha256': {p.name: digest(p) for p in (BASE / 'mlo_core.py', Path(__file__))}})
        log(f'Fitting {len(y)} leave-one-out folds ...')
        scores, models = crossval_predictions(X, y, settings, keep_models=True)
        observed = auc_score(y, scores)
        columns = ['gene', 'pathway', 'label', 'state', 'y_true', 'probability', 'predicted_y_at_0_5']
        save_csv(out / 'loo_predictions.csv', columns, prediction_rows(records, y, scores))
        write_models(out / 'loo_fold_models.json', models, records, FEATURES)
        pairs = []
        for i in np.flatnonzero(y == 1):
            for j in np.flatnonzero(y == 0):
                point = 1. if scores[i] > scores[j] else (.5 if scores[i] == scores[j] else 0.)
                pairs.append({'positive_gene': records[i]['gene'], 'negative_gene': records[j]['gene'],
                              'positive_score': float(scores[i]), 'negative_score': float(scores[j]), 'point': point})
        save_csv(out / 'auc_pairwise_comparisons.csv', list(pairs[0]), pairs)
        pair_stats = {'pairs': len(pairs), 'wins': sum(p['point'] == 1 for p in pairs),
                      'ties': sum(p['point'] == .5 for p in pairs), 'losses': sum(p['point'] == 0 for p in pairs),
                      'auc_from_pairs': sum(p['point'] for p in pairs) / len(pairs)}
        if abs(pair_stats['auc_from_pairs'] - observed) > 1e-12: raise RuntimeError('Independent AUC calculations disagree.')
        log(f'LOO AUC = {observed:.10f}')
        group_scores = None; lpo_observed = None
        if config['include_leave_pathway_out']:
            group_scores, group_models = crossval_predictions(X, y, settings, groups=groups, keep_models=True)
            lpo_observed = auc_score(y, group_scores)
            save_csv(out / 'leave_pathway_predictions.csv', columns, prediction_rows(records, y, group_scores))
            write_models(out / 'leave_pathway_fold_models.json', group_models, records, FEATURES)
            log(f'Leave-pathway-out AUC = {lpo_observed:.10f}')
        B = int(config['permutations']); seed = int(config['seed'])
        if B < 1 or int(config['bootstrap_replicates']) < 2: raise ValueError('Need permutations >= 1 and bootstrap_replicates >= 2.')
        rng = np.random.default_rng(seed)
        permuted = np.array([rng.permutation(y) for _ in range(B)], dtype=int)
        save_csv(out / 'permuted_labels.csv', ['permutation', *[r['gene'] for r in records]],
                 [dict(permutation=b + 1, **{r['gene']: int(permuted[b, i]) for i, r in enumerate(records)}) for b in range(B)])
        payloads = [(b, X, permuted[b], settings, groups, bool(config['include_leave_pathway_out'])) for b in range(B)]
        null_loo = np.empty(B); null_lpo = np.empty(B) if group_scores is not None else None
        executor = ProcessPoolExecutor(max_workers=workers, mp_context=mp.get_context('spawn')) if workers > 1 else None
        iterator = executor.map(permutation_worker, payloads, chunksize=1) if executor else map(permutation_worker, payloads)
        permutation_records = []
        try:
            for b, a, ga in iterator:
                null_loo[b] = a
                if null_lpo is not None: null_lpo[b] = ga
                permutation_records.append({'permutation': b + 1, 'loo_auc': a, 'leave_pathway_auc': ga})
                if (b + 1) % 10 == 0 or b + 1 == B:
                    save_csv(out / 'permutation_aucs.csv', ['permutation', 'loo_auc', 'leave_pathway_auc'], permutation_records)
                    log(f'Permutations finished: {b + 1}/{B}; elapsed {time.monotonic() - start:.1f}s')
        finally:
            if executor: executor.shutdown(wait=True, cancel_futures=True)
        boot_seed = seed + 1
        boots = bootstrap_fixed_oof(y, scores, int(config['bootstrap_replicates']), boot_seed)
        save_csv(out / 'bootstrap_aucs.csv', ['replicate', 'auc'], [{'replicate': i + 1, 'auc': float(v)} for i, v in enumerate(boots)])
        tests = feature_tests(X, y, records)
        save_csv(out / 'feature_tests.csv', list(tests[0]), tests)
        pathway_rows = []
        for g in dict.fromkeys(groups.tolist()):
            idx = groups == g
            pathway_rows.append({'pathway': g, 'n': int(idx.sum()), 'positive': int(y[idx].sum()),
                                 'negative': int((y[idx] == 0).sum()), 'uniform': bool(len(np.unique(y[idx])) == 1)})
        save_csv(out / 'pathway_counts_from_input.csv', list(pathway_rows[0]), pathway_rows)
        _, final_model = fit_and_predict(X, y, X, settings)
        final_model.update({'feature_names': list(FEATURES), 'task': 'assembly-positive versus assembly-negative metabolic entries',
                            'input_sha256': digest(input_path), 'warning': 'Full-data model; its training scores are not used as CV predictions.'})
        save_json(out / 'model_final.json', final_model)
        summary = {'task': 'enzyme assembly binary classification', 'input_csv': str(input_path),
                   'input_sha256': digest(input_path), 'n': len(y), 'n_features': len(FEATURES),
                   'n_positive': int(y.sum()), 'n_negative': int((y == 0).sum()), 'settings': settings,
                   'seed': seed, 'source': 'Rounded three-decimal Table S3 values; original labels preserved.',
                   'loo': {'auc': observed, 'mean_score_positive': float(scores[y == 1].mean()),
                           'mean_score_negative': float(scores[y == 0].mean()),
                           'pairwise_auc_check': pair_stats, 'permutation': permutation_summary(observed, null_loo),
                           'conditional_bootstrap': {'replicates': len(boots), 'seed': boot_seed,
                                'method': 'stratified paired bootstrap of fixed OOF label-score records, no refit',
                                'percentile_ci95': np.quantile(boots, [.025, .975], method='linear').tolist(),
                                'not_equivalent_to_unspecified_paper_bootstrap': True}}}
        if lpo_observed is not None:
            summary['leave_pathway_out'] = {'auc': lpo_observed, 'n_folds': len(np.unique(groups)),
                                            'permutation': permutation_summary(lpo_observed, null_lpo)}
        if config['include_pathway_aggregate']:
            GX, gy, group_names = aggregate_pathways(X, y, groups)
            gp, _ = crossval_predictions(GX, gy, settings)
            names = [f'{f}_mean' for f in FEATURES] + [f'{f}_std_ddof0' for f in FEATURES] + ['enzyme_count']
            save_csv(out / 'pathway_aggregate_input.csv', ['pathway', 'y', *names],
                     [dict(pathway=g, y=int(gy[i]), **dict(zip(names, GX[i].tolist()))) for i, g in enumerate(group_names)])
            save_csv(out / 'pathway_aggregate_predictions.csv', ['pathway', 'y', 'probability'],
                     [{'pathway': g, 'y': int(gy[i]), 'probability': float(gp[i])} for i, g in enumerate(group_names)])
            summary['pathway_aggregate'] = {'auc': auc_score(gy, gp), 'n_pathways': len(gy), 'n_features': GX.shape[1],
                                           'within_pathway_std_ddof': 0, 'validation': 'pooled leave-one-pathway-record-out scores'}
        perm_stats = summary['loo']['permutation']
        make_plots(out, y, scores, group_scores, null_loo, observed, perm_stats['p_plus1_ge'])
        summary['elapsed_seconds'] = time.monotonic() - start
        save_json(out / 'summary.json', summary)
        comparison = [{'metric': 'primary_loo_auc', 'paper_reported': .58, 'this_run': observed, 'convention_note': 'input and implementation differ'},
                      {'metric': 'primary_permutation_p', 'paper_reported': .073, 'this_run': perm_stats['p_plus1_ge'], 'convention_note': 'this run: plus-one inclusive upper tail; manuscript correction rule unconfirmed'}]
        if lpo_observed is not None: comparison.append({'metric': 'leave_pathway_auc', 'paper_reported': .45, 'this_run': lpo_observed, 'convention_note': 'holdout grouping and input must match'})
        if summary.get('pathway_aggregate'): comparison.append({'metric': 'pathway_aggregate_auc', 'paper_reported': .60, 'this_run': summary['pathway_aggregate']['auc'], 'convention_note': 'upstream aggregation conventions incomplete'})
        save_csv(out / 'paper_comparison.csv', ['metric', 'paper_reported', 'this_run', 'convention_note'], comparison)
        make_report(out, summary)
        save_json(out / 'run_status.json', {'status': 'complete', 'elapsed_seconds': summary['elapsed_seconds']})
        log(f"Complete: {out}; LOO AUC={observed:.10f}, permutation p(+1)={perm_stats['p_plus1_ge']:.6f}")
    return 0


if __name__ == '__main__':
    mp.freeze_support()
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print('Interrupted; partial output is not a completed run.', file=sys.stderr)
        raise SystemExit(130)
    except Exception as error:
        print(f'ERROR: {error}', file=sys.stderr)
        raise SystemExit(1)
