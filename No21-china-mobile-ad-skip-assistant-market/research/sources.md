# 来源账本

验证日期均为 2026-08-22。A 级为官方平台、官方仓库或官方政策；B 级为高可信媒体对明确主体或报告的直接转述。动态计数以 research/data 中冻结快照为准。

| ID | 等级 | 来源与链接 | 本报告使用的事实 | 交叉验证与边界 |
|---|---|---|---|---|
| S01 | B1 | [新华社：撤下“摇一摇” App 开屏广告乱象整治持续推进](https://www.news.cn/legal/20260626/d2e75eef052d43d3988ac60fa572bf1a/c.html) | 2026-06-26 报道：黑猫“摇一摇”相关投诉超 2,600 条；工信部累计通报 50 余批次；治理针对乱跳、关不掉和诱导误触，并非全面禁止开屏广告 | 国家通讯社调查报道；投诉数仍是平台搜索结果，不等同全市场发生率 |
| S02 | B1 | [央广网：互联网广告目前规模如何，又将走向何方？](https://ad.cnr.cn/hyzx/20250211/t20250211_527068285.shtml) | 中关村互动营销实验室口径：2024 年互联网广告收入 6,508.63 亿元、同比增 13.55%；传统视频贴片和纯展示份额下滑 | 与 S03 方向交叉验证；统计口径不同，不拼成一条序列 |
| S03 | B1 | [QuestMobile 经澎湃发布：2025 中国营销报告](https://www.thepaper.cn/newsDetail_forward_32820010) | QuestMobile 口径：2023 年 7,146.1 亿元增至 2025 年 7,930.8 亿元；2025 年强曝光、弱互动的开屏广告下降 | 作者页明确为 QuestMobile；不可与 S02 的绝对额直接同比 |
| S04 | B1 | [中国新闻网：“李跳跳”违法了吗？](https://www.chinanews.com.cn/gsztc/2023/08-30/10069260.shtml) | 开发者称李跳跳是公益、单机、无联网、无盈利；2023-08-24 因收到律师函无限期停止更新 | 证明当事人表述和停更，不证明法院判决，也没有收入数据 |
| S05 | A1 | [GitHub API：gkd-kit/gkd](https://api.github.com/repos/gkd-kit/gkd) | 41,076 Star、1,944 Fork、GPL-3.0、更新时间等仓库计数 | 动态数据；冻结原始结构见 github_snapshot.json |
| S06 | A1 | [GitHub API：GKD Releases](https://api.github.com/repos/gkd-kit/gkd/releases?per_page=100) | 75 个 Release；APK 累计 565,905 次下载；v1.12.1 APK 为 42,417 次 | 下载是资产请求数，可能重复，不是唯一安装或 MAU |
| S07 | A1 | [GKD 官方 README](https://github.com/gkd-kit/gkd) | 基于无障碍、选择器、订阅和快照审查；默认不提供规则；公开赞助入口 | 功能与商业边界直接证据；赞助入口不等于收入 |
| S08 | A1 | [GKD Google Play 详情页](https://play.google.com/store/apps/details?id=li.songe.gkd&hl=en&gl=US) | 50K+ 安装、4.8 分、472 条评论、无广告/无 IAP 标签 | 商店档位不是精确安装数；与 GitHub 采用信号交叉验证 |
| S09 | A1 | [GitHub Topic API：gkd-subscription](https://api.github.com/search/repositories?q=topic%3Agkd-subscription&per_page=100) | 返回 29 个公开仓库；15 个不超过 10 Star、24 个不超过 100、27 个不超过 1,000；前三占 95.6% | 只覆盖主动打 Topic 的公开仓库，不是所有规则维护者 |
| S10 | A1 | [AIsouler/GKD_subscription](https://github.com/AIsouler/GKD_subscription) | 886 App、2,074 应用规则组；维护两年后于 2026-02-12 停更，维护者写明“热情终究会耗尽” | 直接证明头部个人维护负担；不等于所有维护者都会停更 |
| S11 | A1 | [Lin-arm/GKD_subscription](https://github.com/Lin-arm/GKD_subscription) | 社区接力 Fork 已覆盖 972 App、2,408 应用规则组 | 证明社区可接力，也证明持续更新仍不可省略 |
| S12 | A1 | [AD Jump Google Play](https://play.google.com/store/apps/details?id=net.airplanez.android.adskip&hl=en&gl=US) | 100K+ 安装、3.5 分、3K 评论、含广告；自动跳过和静音 | 安装证明采用，不公开 MAU、广告收入或利润 |
| S13 | A1 | [Skip Ad Google Play](https://play.google.com/store/apps/details?id=com.candlelight.adskipper&hl=en&gl=US) | 10K+ 安装、3.4 分、233 评论；跳过、静音、关闭视频广告 | 当前页无可验证收入 |
| S14 | A1 | [AdSkipper: Auto Skip Ads Google Play](https://play.google.com/store/apps/details?id=com.evolvarc.adskipper&hl=en&gl=US) | 1K+ 安装、3.4 分、39 评论；2026-03-15 更新 | 新小玩家样本，不代表失败原因 |
| S15 | A1 | [Mavenka Ad Skipper Google Play](https://play.google.com/store/apps/details?id=com.mavenkalabs.adskipper&hl=en&gl=US) | 100K+ 安装、3.2 分、415 评论；跳过并静音特定音视频 App 广告 | 有规模但评分一般；无收入披露 |
| S16 | A1 | [AdSkipper Google Play](https://play.google.com/store/apps/details?id=decemberpei.gmail.adskipper&hl=en&gl=US) | 50K+ 安装、4.4 分、861 评论；自动点击 skip | 采用信号；无收入披露 |
| S17 | A1 | [Skipify Google Play](https://play.google.com/store/apps/details?id=com.kw.skipify&hl=en&gl=US) | 1K+ 安装、40 评论；每日 6 次免费，4.99 美元终身解锁，有 IAP | 唯一明确付费锚；购买数、营收和利润均未公开 |
| S18 | A1 | [Ad Skip Google Play](https://play.google.com/store/apps/details?id=com.rhaon.ad_skip&hl=en&gl=US) | 10K+ 安装、含广告，最后更新 2022-10-17 | 老样本说明产品可长期留存；不能推断仍活跃 |
| S19 | A1 | [Skip Ads Pro Google Play](https://play.google.com/store/apps/details?id=skip.ads.pro&hl=en&gl=US) | 10K+ 安装、含广告，最后更新 2022-11-03 | 同上；无经营数据 |
| S20 | A1 | [Ad-silence Google Play](https://play.google.com/store/apps/details?id=bluepie.ad_silence&hl=en&gl=US) | 100K+ 安装、开源、针对音频广告静音 | 相邻而非完全同类；不处理中国开屏规则 |
| S21 | A1 | [Google Play：AccessibilityService API 政策](https://support.google.com/googleplay/android-developer/answer/10964491?hl=en) | 禁止自主规划执行，但明确不禁止遵循静态人工脚本的确定性规则；非无障碍工具需声明、显著披露和主动同意 | 证明规则式产品可上架，不保证具体 App 必然通过审核 |
| S22 | A1 | [Android：受限设置说明](https://support.google.com/android/answer/12623953?hl=en) | 侧载 App 可能需用户允许受限设置；无障碍可读取屏幕并代表用户与 App 交互 | 直接证明信任和安装摩擦 |
| S23 | A1 | [Google Play 服务费](https://support.google.com/googleplay/android-developer/answer/112622?hl=en) | 15% 服务费档：开发者每年前 100 万美元收入 15%；自动续订订阅 15% | 测算采用 15%；是否成功注册该档仍需经营者确认 |
| S24 | A1 | [Apple Platform Security：运行时进程安全](https://support.apple.com/guide/security/security-of-runtime-process-sec15bfe098e/web) | 第三方 App 受沙箱限制，不能收集/修改其他 App 信息，只能使用 iOS 明确提供的服务 | “不能复制 Android 跨 App 自动点击”是基于该架构的推断 |
| S25 | B2 | [南方都市报：App“摇一摇”广告有了新标准](https://m.mp.oeeee.com/a/BAAFRD0000202507221105494.html) | 2025 实践指南给出加速度不小于 15m/s²、双向转角不小于 35°、操作不少于 3 秒等触发参考，并要求一键关闭 | 行业实践指南的媒体转述；与 S01 的监管方向交叉验证 |

## 数据文件对应关系

- github_snapshot.json：S05、S06、S09、S10、S11 的冻结结构化数据。
- google_play_snapshot.json / csv：S08、S12—S20 的冻结结构化数据。
- economics.json / csv：S17、S23 与显式情景输入形成的测算结果。
- forecast_scenarios.csv：3—5 年指数情景，不是第三方预测数据。

## 来源冲突处理

S02 与 S03 的互联网广告绝对规模不同，原因是发布主体与统计口径不同。报告只使用两者共同支持的方向：“广义互联网广告仍增长，传统展示/开屏形态相对走弱”，不计算跨口径增长率，也不据此伪造跳广告工具的人民币 TAM。
