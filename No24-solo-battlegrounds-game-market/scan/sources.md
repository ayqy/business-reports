# $scan 一手证据账本

核验日：2026-09-25（北京时间）。此账本支撑“拟议产品的规格设计”，**不证明尚不存在的产品已经具备这些功能**。分级按 `$scan`：A1 官方结构化商店响应、A2 官方玩法公告/截图/帮助、B1 官方站、B2 官方隐私与平台规则、C2 近期评论、E 为本规格推断/原创提案。

| ID | 级别与原址 | 可直接观察的行为/字段 | 适用边界 |
| --- | --- | --- | --- |
| <a id="s01"></a>S01 | A2 [暴雪《Introducing Hearthstone Battlegrounds》2019](https://hearthstone.blizzard.com/en-us/news/23156373/introducing-hearthstone-battlegrounds) | 八人自动战斗；选英雄、招募、刷新、出售、冻结、升级、三合一、摆位、战斗、再次招募直到决出名次。文章配官方界面图和教学说明。 | 历史机制参考；不是2026现行数值，也不是拟议产品可照搬的素材/卡牌/界面。 |
| <a id="s02"></a>S02 | A2 [暴雪酒馆战棋第14赛季2026公告](https://hearthstone.blizzard.com/en-us/news/24290433/announcing-battlegrounds-season-14-dark-gifts-of-dalaran) | 当期季票新增2名开局英雄选项，Pass+每局1次免费英雄重掷。 | 证明原产品已售这些权益；不证明用户会为纯单机版本同样付钱。 |
| <a id="s03"></a>S03 | A2 [暴雪第9赛季2024公告](https://hearthstone.blizzard.com/en-us/news/24159389/announcing-battlegrounds-season-9) | 英雄重掷规则、免费券与季票的权益差别、美区当期14.99/19.99美元。 | 只能作为历史权益与价格锚点，不能写为2026中国售价。 |
| <a id="s04"></a>S04 | B1 [《月圆之夜》官方站](http://www.yueyuanzhiye.com/) | 官方同时展示单机冒险、镜中对决和长期内容活动；页脚展示出版许可和 ISBN。 | 证明中国用户可接触的单机卡牌参照，不证明本产品的玩法和收入。 |
| <a id="s05"></a>S05 | A1 [Apple中国区《炉石传说》商店页](https://apps.apple.com/cn/app/%E7%82%89%E7%9F%B3%E4%BC%A0%E8%AF%B4/id841140063)与[官方 Lookup API](https://itunes.apple.com/lookup?id=841140063&country=cn) | 应用身份、公开文案、版本、截图 URL、累计评分等结构化字段；快照见 `raw/store-detail.json`。Lookup 响应未提供隐私政策 URL。 | App 含其他模式，商店评分不能单独归给酒馆战棋。 |
| <a id="s06"></a>S06 | A1 [Apple中国区《月圆之夜》商店页](https://apps.apple.com/cn/app/%E6%9C%88%E5%9C%86%E4%B9%8B%E5%A4%9C/id1278845241)与[官方 Lookup API](https://itunes.apple.com/lookup?id=1278845241&country=cn) | 单机卡牌产品在架、文案、版本、截图与公开元数据；快照见 `raw/store-detail.json`。 | 当前上架状态不等于单机自走棋收入，也不等于其所有模块离线可用。 |
| <a id="s07"></a>S07 | C2 [Apple中国区《月圆之夜》最近评论](https://itunes.apple.com/cn/rss/customerreviews/id=1278845241/sortBy=mostRecent/json) | 上轮保存的50条最近评论中7条提到“单机”，部分要求保留干净的单机体验，见 `../research/apple-cn-recent-reviews.json`。 | 非随机样本，只支持需求存在性与抱怨词，不支持总体占比。 |
| <a id="s08"></a>S08 | B2 [Apple审核准则](https://developer.apple.com/app-store/review/guidelines/) 3.1.1、4.1、5.2 | 游戏内数字权益需按适用规则使用内购；禁止简单模仿、未经授权或误导性的第三方内容。 | 审核规则不是拟议游戏的个案法律判决。 |
| <a id="s09"></a>S09 | A2 [Apple StoreKit购买及恢复示例](https://developer.apple.com/documentation/storekit/offering-completing-and-restoring-in-app-purchases) | Apple提供检索、展示、完成与恢复应用内购买的官方实现路径。 | 本规格的季票、离线缓存与到期策略是原创产品设计，不能说 Apple 示例已经实现。 |
| <a id="s10"></a>S10 | B2 [Apple中国区游戏资料要求](https://developer.apple.com/help/app-store-connect/reference/app-information/)及[国家新闻出版署国产游戏申报材料](https://www.nppa.gov.cn/bsfw/xksx/cbfxl/wlcbfwspsx/202210/t20221013_600725.html) | 大陆区游戏审批号及出版/运营材料要求，下载式单机在申报范围中。 | 需求规格不能代替审批、发行主体与个案审查。 |
| <a id="s11"></a>S11 | B2 [Apple 内购类型说明](https://developer.apple.com/help/app-store-connect/reference/in-app-purchases-and-subscriptions/in-app-purchase-types) | 非消耗型内购一次购买、不随时间到期；非自动续期订阅可设有限服务期，不会自动续费。 | 本规格选择「每季单独非消耗型 SKU、已购季永久可玩」是产品设计，并非 Apple 要求所有季票这么卖。 |
| <a id="s12"></a>S12 | B2 [Apple App 隐私详情](https://developer.apple.com/app-store/app-privacy-details/) | App Store 需填写自身及第三方的数据收集实践；Apple 文中要求提供可公开访问的隐私政策 URL。 | 拟议产品的本机存储、无账号、无广告是设计决定；不能据此推定参照游戏的数据处理方式。 |

## 原创设计与推断的记法

### 2019 首版内容与规则增量

卡池、客户端构建、上线周历史修订、三合一金色与玩法机制的证据方法集中见[历史证据账本](historical-evidence.md)。它把暴雪官方文字、构建 35747 的版本化卡定义与 2019 年 11 月 10 日 06:55（北京时间）的社区历史表分开；构建内 81 张普通卡、68 张可直接核对的金色卡及 13 张金色推断均在[结构化索引](historical-card-pool.json)留下逐项标记。客户端资源与社区历史表交叉核查不等于两个独立运营观测，不能据此推定服务端抽卡概率。

- `D`：上表 S01—S10 可直接证明的原产品或平台行为。
- `I`：由一手证据约束的页面结构或交互顺序推断；拟议产品实际仍需原型验证。
- `U`：管理员要求（全本机AI、怀旧节奏、原创Q版、昵称语气、季票）；尚非竞品已发功能证据。
- `P`：本规格提出的原创产品规则、数值、AI策略、数据结构或验收指标；都须经玩法测试和权利审查，不可称为市场事实。

## 官方图片判读边界

2019 年 [暴雪玩法文章](#s01)中的 [招募示意图](https://bnetcmsus-a.akamaihd.net/cms/gallery/O22Q4B2SGRGM1572367737416.png)、[三合一示意图](https://bnetcmsus-a.akamaihd.net/cms/gallery/M5H43MNOO4E31572367737216.jpg)、[战斗过渡图](https://bnetcmsus-a.akamaihd.net/cms/gallery/1DZML2G2NP9Y1572367736483.jpg)已逐张查看，属于教学插图或过渡画面，**不能确定移动端实际按钮位置、屏幕顺序或 2026 年 UI**。本规格的页面布局因此全部标 `P`，其动作顺序只由文章文字支持。
