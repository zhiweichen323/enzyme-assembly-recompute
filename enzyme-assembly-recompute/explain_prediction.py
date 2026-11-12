#!/usr/bin/env python3
"""Explain one saved held-out prediction, feature by feature."""
from __future__ import annotations
import argparse
import csv
import json
from pathlib import Path
import numpy as np
from scipy.special import expit

BASE = Path(__file__).resolve().parent


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--results', default='results/quick')
    parser.add_argument('--gene', default='PPAT')
    args = parser.parse_args()
    out = Path(args.results)
    if not out.is_absolute(): out = BASE / out
    document = json.loads((out / 'loo_fold_models.json').read_text(encoding='utf-8'))
    features = document['feature_names']
    fold = next((f for f in document['folds'] if args.gene in f['test_genes']), None)
    if fold is None: raise ValueError(f'Gene not found in saved folds: {args.gene}')
    position = fold['test_genes'].index(args.gene)
    raw = np.array(fold['test_raw_features'][position])
    mean, scale, weights = (np.array(fold[k]) for k in ('mean', 'scale', 'weights'))
    standardized = (raw - mean) / scale
    contributions = standardized * weights
    z = fold['intercept'] + float(contributions.sum())
    p = float(expit(z)); saved = fold['test_scores'][position]
    if abs(p - saved) > 1e-12: raise RuntimeError('Saved prediction and reconstructed score disagree.')
    rows = [dict(feature=name, raw_value=float(raw[i]), train_mean=float(mean[i]),
                 train_scale=float(scale[i]), standardized=float(standardized[i]),
                 weight=float(weights[i]), contribution=float(contributions[i]))
            for i, name in enumerate(features)]
    csv_path = out / f'prediction_breakdown_{args.gene}.csv'
    with csv_path.open('w', encoding='utf-8-sig', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader(); writer.writerows(rows)
    text = f'''# {args.gene}的留一法预测分数怎样计算

- 所属留一轮次：{fold['fold_id']}。
- 训练样本：{fold['train_n']}个，阳性{fold['train_positive_n']}个、阴性{fold['train_negative_n']}个。
- 留出对象：{args.gene}；它没有参与本轮标准化参数和模型权重的拟合。
- 截距：{fold['intercept']:.17g}。

每项先算`standardized=(raw_value-train_mean)/train_scale`，再算`contribution=weight*standardized`。

| 特征 | 原始值 | 训练均值 | 训练标准差 | 标准化值 | 权重 | 对线性分数的贡献 |
|---|---:|---:|---:|---:|---:|---:|
'''
    for r in rows:
        text += '| ' + r['feature'] + ' | ' + ' | '.join(f"{r[k]:.10g}" for k in ('raw_value','train_mean','train_scale','standardized','weight','contribution')) + ' |\n'
    text += f'''
全部特征贡献相加为{float(contributions.sum()):.17g}；加上截距得到：

$$
z={z:.17g}
$$

再经过sigmoid：

$$
p=\\frac{{1}}{{1+e^{{-z}}}}={p:.17g}
$$

保存的原始折外分数为{saved:.17g}，两种计算在浮点误差范围内一致。Markdown表格只展示有限位小数，逐项复核时使用CSV或JSON中的完整数值。

这是模型对当前组装阳性类别的分数，不能直接当作经过校准的细胞内LLPS发生概率。无膜细胞器研究背景与标签边界见仓库中的`docs/biological_background.md`。
'''
    md_path = out / f'prediction_breakdown_{args.gene}.md'
    md_path.write_text(text, encoding='utf-8')
    print(f'{args.gene}: z={z:.12f}, probability={p:.12f}; train_n={fold["train_n"]}')
    print(f'Wrote {csv_path.name} and {md_path.name}')


if __name__ == '__main__':
    main()
