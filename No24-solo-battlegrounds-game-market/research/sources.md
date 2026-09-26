# FF-0810｜一手来源、交叉核验与边界

核验日：2026-09-25（北京时间）。方方优先取监管机构、平台、游戏发行方和上市公司自身公布的资料。网站原始地址保留在下表；对动态页面，研究脚本保存了当日规范化快照。下列“交叉核验”指不同维度的方向核对，**不等于审计了另一机构的原始数据库**。

| 编号 | 一手来源与可核验事实 | 交叉核验、不能推出什么 |
| --- | --- | --- |
| <a id="m01"></a>M01 | [中国音数协游戏工委《2025中国游戏产业报告》](https://www.cgigc.com.cn/details.html?id=08de474f-eed0-496a-8fdc-bb4a06b1b1a1&tp=report)：2025国内游戏收入3507.89亿元、同比+7.68%；用户6.83亿、+1.35%；移动游戏2570.76亿元、+7.92%；移动休闲342.65亿元、+9.56%；小程序游戏535.35亿元、+34.39%；2025国内收入前100移动游戏中卡牌品类按**产品数**占8%，报告称策略/卡牌数量占比虽高，收入占比无优势。 | 与 M02/M03 的大厂收入增长方向一致，但口径一个是全国实际销售、一个是公司合并报表，不能相加；没有单机自走棋、通行证或独立开发者细分的收入及利润。 |
| <a id="m02"></a>M02 | [网易2025年度业绩公告](https://ir.netease.com/news-releases/news-release-details/netease-announces-fourth-quarter-and-fiscal-year-2025-unaudited)：游戏及相关增值服务净收入2025年921亿元、2024年836亿元；网易**公司归母净利润**2025年338亿元、2024年297亿元。公告称暴雪在华游戏年度收入创高，但未披露酒馆战棋单模式收入。 | 与 M01 的增长方向交叉核对；**338亿元不是游戏分部或《炉石传说》的利润**。收入差额85亿元，按四舍五入数算+10.17%；不能拿来预测个人团队利润率。 |
| <a id="m03"></a>M03 | [网易2026年上半年业绩公告](https://ir.netease.com/news-releases/news-release-details/netease-announces-second-quarter-and-interim-2026-unaudited)：上半年游戏及相关收入507亿元，同比+8.3%；公司归母净利润177亿元。 | 与 M02 比较的是同一公司不同期间；网易未拆出酒馆战棋/《炉石传说》具体收入和利润。 |
| <a id="m04"></a>M04 | [暴雪酒馆战棋第14赛季公告](https://hearthstone.blizzard.com/en-us/news/24290433/announcing-battlegrounds-season-14-dark-gifts-of-dalaran)：Season Pass 增加2名开局英雄选项，Pass+ 每局附1次英雄重掷。 | 与 M05 比较可知用户设想的付费权益已在原产品内；公告不能证明中国玩家的付费转化率。 |
| <a id="m05"></a>M05 | [暴雪第9赛季公告](https://hearthstone.blizzard.com/en-us/news/24159389/announcing-battlegrounds-season-9)：当期美区 Pass 14.99 美元、Pass+ 19.99 美元；公开详细重掷规则和免费玩家也可获取重掷券。 | 这是2024年历史定价锚点，**不是2026中国区售价**。M04 说明权益延续，但没有当期价格可核。 |
| <a id="m06"></a>M06 | [《月圆之夜》官方站](http://www.yueyuanzhiye.com/)：官方展示单机玩法、镜中对决活动，并在页脚列互联网出版许可及 ISBN；官网披露9种职业、600多张卡牌、142位对手等内容规模。 | 与 M07 中国区 App Store 2017年以来仍在更新、累计评分量核对“有长期供给/需求”；官网参数是官方自报，不代表单机自走棋模式同时有这些具体资产或盈利。 |
| <a id="m07"></a>M07 | [Apple iTunes Search API](https://itunes.apple.com/search?term=%E8%87%AA%E8%B5%B0%E6%A3%8B%20%E5%8D%95%E6%9C%BA&country=cn&entity=software&limit=200) 及本目录 `apple-cn-search-snapshot.json`：2026-09-25中国区关键词快照；每条保留官方应用详情链接、累计评分数、价格、发布日期与最近版本日期。 | 从 API 与应用详情 URL 做同平台核对；搜索结果含很多不相关游戏，排名和返回数不是完整市场总体；评分数**绝不可转换成下载、付费、月活、营收或利润**。 |
| <a id="m08"></a>M08 | [Apple《月圆之夜》最近评论 RSS](https://itunes.apple.com/cn/rss/customerreviews/id=1278845241/sortBy=mostRecent/json) 与 [《炉石传说》最近评论 RSS](https://itunes.apple.com/cn/rss/customerreviews/id=841140063/sortBy=mostRecent/json)，本目录 `apple-cn-recent-reviews.json` 保存各50条。 | 《月圆之夜》50条最近评论中7条含“单机”；只能证明存在具体用户表达，不能估计总体偏好、转化率或人群规模。 |
| <a id="m09"></a>M09 | [Apple App Review Guidelines](https://developer.apple.com/app-store/review/guidelines/) 4.1 和 5.2：不得简单复制热门应用、微调名称/UI冒充原创；上架内容应自有或经许可，不可用第三方受保护的商标、版权内容或误导性名称/元数据。 | 官方审核规则直接证明**平台风险**，不等于法院已裁定这款尚未制作的游戏侵权。AI绘制新原画也不能自动化解卡牌表达、组合、昵称、UI和营销问题。 |
| <a id="m10"></a>M10 | [Apple 中国大陆区应用资料](https://developer.apple.com/help/app-store-connect/reference/app-information/)：大陆区游戏须有游戏审批号并提交核验材料；没有区分免费、广告或内购豁免。 | 与 M11 申报材料、已有 [No23上架报告](../../No23-iphone-indie-game-publishing-market/report.md) 交叉核对；具体游戏个案仍需主管部门/出版单位确认。 |
| <a id="m11"></a>M11 | [国家新闻出版署国产游戏申报材料](https://www.nppa.gov.cn/bsfw/xksx/cbfxl/wlcbfwspsx/202210/t20221013_600725.html)：出版单位、运营机构、作品权利和审批资料要求，网络下载的单机游戏纳入申报类型。 | 与 M10 相互支持中国区发行门槛；有著作权或技术能力不等于个人能独立完成出版运营链条。 |
| <a id="m12"></a>M12 | [Apple Small Business Program](https://developer.apple.com/app-store/small-business-program/)：符合条件且参加计划时，付费 App 和 IAP 佣金15%。 | 经济模型将15%作有利情景，另测30%；获得计划资格不是自动的。退款3%、68元/季、4个月、2%转化、40%续费、月固定成本3000元均为**自设假设**。 |
| <a id="m13"></a>M13 | [Valve《The Future of Artifact》官方开发公告](https://store.steampowered.com/news/app/583950/view/4057152305713777403)：初始销售虽好但活跃玩家迅速下降，未达到继续开发所需规模，停止开发2.0并把两版本改免费。 | 这是相关策略卡牌领域的**全球失败案例**，并非中国该游戏营收数据；说明“短期关注/初期销量”不保证持续付费。 |
| <a id="m14"></a>M14 | [《魔卡棋旅》中国区商店页](https://apps.apple.com/cn/app/%E9%AD%94%E5%8D%A1%E6%A3%8B%E6%97%85/id6742221550)、[《斗阵骑士》中国区商店页](https://apps.apple.com/cn/app/%E6%96%97%E9%98%B5%E9%AA%91%E5%A3%AB/id6760652297)：快照标价分别18、15元，累计评分666、27。 | 仅用于观察**公开评分较少的同类产品价格和公开声量，团队规模未知**，不能凭评分反推销量、利润或宣称失败；模型以这些实价锚点反算达到目标所需月销量。 |

## 缺口与检索停止点

公开的一手资料未提供“中国单机酒馆战棋细分市场规模”、单个小团队的实际净利润、内购转化率、留存率、获客成本和季票续费率。方方不把第三方估算或评论数伪装成精确流水；以明示假设建立可复算情景，再把未知变量列为是否投入制作的验证门槛。2026年全年尚未结束，不能以2025全年或网易2026上半年代表2026全年。
