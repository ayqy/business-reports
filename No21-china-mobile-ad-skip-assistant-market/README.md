# No21：中国移动 App 广告跳过助手小生意调研

本目录保存 FF-0177 的完整调研过程、公开证据快照、可复现测算、竞品功能扫描和最终报告。

一句话结果：产品在 Android 上可做，但目前不应把它当作可稳定月入一万元的独立开发者生意；免费强替代、规则维护负担和获客门槛同时存在，公开市场也没有提供足以验证稳定付费的经营数据。

## 文件导航

- [report.md](report.md)：决策优先的最终市场报告。
- [research/process.md](research/process.md)：范围、问题抽象、否证门槛、采样方法和研究日志。
- [research/sources.md](research/sources.md)：逐项来源账本、证据等级和使用边界。
- [research/calculations.md](research/calculations.md)：月入一万元单位经济、获客阈值和 3—5 年情景模型。
- [research/scan/competitor-functional-matrix.md](research/scan/competitor-functional-matrix.md)：按 scan 证据分级形成的竞品功能矩阵与 PRD 触发判断。
- research/data/：2026-08-22 冻结的 GitHub、Google Play、经济模型和预测情景结构化快照。
- research/scripts/：公开证据采集、模型计算和一致性验证脚本。

## 证据口径

- 直接证据：官方平台、官方仓库、官方政策页或可明确归属的当事人公开表述。
- 测算：公式、输入和结果均公开；情景输入不伪装成行业统计。
- 推断：由多条证据共同支持但没有直接统计量的判断，均在报告中标明。

Google Play 安装量是平台展示档位，不是月活；GitHub Release 下载是资产请求数，不是唯一用户；Star 不是收入。私营小工具没有公开审计营收和利润，本目录没有用虚构的“行业平均数”填补这一空白。

## PRD 条件

任务契约只在最终结论评估可行时要求完整需求规格说明书。本报告的当前结论为 no-go，故完整 PRD 条件未触发；scan 已用于目标选择、功能证据分级和竞品矩阵，没有把条件性交付物私自升级为必交付项。
