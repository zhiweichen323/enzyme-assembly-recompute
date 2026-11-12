# Enzyme Assembly Recompute

面向无膜细胞器研究，检验代谢蛋白的序列特征能否预测组装标签的 Python 分析工具。

程序、输入数据和完整文档位于 [enzyme-assembly-recompute](enzyme-assembly-recompute/) 子目录。

## 文档入口

- [中文使用说明与安装步骤](enzyme-assembly-recompute/README.md)
- [English documentation](enzyme-assembly-recompute/README.en.md)
- [无膜细胞器与研究背景](enzyme-assembly-recompute/docs/biological_background.md)
- [命令、配置与输出文件](enzyme-assembly-recompute/docs/usage.md)
- [模型与统计方法](enzyme-assembly-recompute/docs/methods.md)
- [可复现性与参考结果](enzyme-assembly-recompute/REPRODUCIBILITY.md)
- [引用与来源记录](enzyme-assembly-recompute/CITATION.md)
- [许可说明](enzyme-assembly-recompute/LICENSE_NOTICE.md)

## 运行位置

下载或克隆整个仓库后，先在仓库目录内执行 `cd enzyme-assembly-recompute`，再按照中文使用说明创建 Python 环境和运行程序。

## 结果的含义

输入为预先计算的序列特征和参考组装标签。程序输出交叉验证预测分数、ROC AUC、置换检验和条件性 Bootstrap 区间，不计算分子动力学轨迹或细胞内 LLPS 发生概率。来源手稿报告值与本项目重算值存在差异，详细说明见项目文档。
