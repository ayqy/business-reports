# FF-0810｜单机酒馆战棋创业想法与产品规格

- [创业可行性报告](report.md)：中国市场数据、参照案例、政策及权利风险、月入一万元税前门槛与情景测算。
- [市场来源与核验过程](research/sources.md)、[计算模型](research/model.py)及[结果](research/model-results.json)：区分官方事实、推断和自设参数。
- [$scan 详细功能需求规格](scan/functional-spec.md)：管理员破格要求；说明参考玩法、原创实现、逐页交互、引擎/AI/季票/存档、可观察验收及发行门禁。
- [$scan 一手证据账本](scan/sources.md)及[官方商店快照](scan/store-extract.json)：规格的来源与边界。
- [2019 上线周 81 张普通/金色逐卡索引](scan/historical-card-pool.md)及[结构化数据](scan/historical-card-pool.json)：按六级酒馆与历史种族分栏列出名称、ID、数值、机制摘要和金色证据等级。
- [13 张金色卡缺口的逐项审查](scan/historical-golden-gap-audit.md)：区分同构建衍生物、官方后续追溯、同期社区记录与未证实的三合一推断。
- [13 张金色卡的可执行参照验收向量](scan/historical-golden-acceptance.json)及[运行器](scan/verify_historical_golden_acceptance.py)：覆盖跨手场三合一、18 个确定性效果场景、虚空行者衍生物身份与精确复刻未知项；运行 `python scan/verify_historical_golden_acceptance.py`，结果仅用于参考规格一致性。
- [68 张有独立金色实体卡的效果节点审查](scan/historical-effect-node-audit.md)、[24 张强化/光环节点与 58 个向量](scan/historical-effect-nodes.json)及[验证器](scan/verify_historical_effect_nodes.py)：普通/金色卡面字段来自固定构建客户端，事件路径明确标为参照实现。
- [15 张固定召唤卡的类型化节点与 57 个向量](scan/historical-fixed-token-nodes.json)及[验证器](scan/verify_historical_fixed_tokens.py)：涵盖母卡与衍生物候选身份、数量、七格截断及战斗快照；效果到实体 ID 的生成链仍是推断。
- [13 张复合生命周期卡的节点与 84 个普通/金色向量](scan/historical-composite-nodes.json)及[验证器](scan/verify_historical_composite_nodes.py)：限定单事件的亡语/战吼倍数、磁力、超杀、成长、光环和机械死亡历史；不能裁决的治疗、多源叠加及同刻死亡明确拒绝。68 张直接金色卡中累计有 52 张有界参照效果。
- [剩余 16 张随机/发现卡的触发与数量意图外壳及 66 个向量](scan/historical-random-effect-shells.json)、[验证器](scan/verify_historical_random_effect_shells.py)：全数核对固定构建卡面，但目标、动态生成资格、权重和选项仍为未知，不能将外壳算作完整效果实现。
- [16 张随机/发现卡的独立参考裁决](scan/historical-random-reference.md)、[配置](scan/historical-random-reference.json)、[66 个普通/金色向量](scan/historical-random-reference-vectors.json)及[运行器](scan/verify_historical_random_reference.py)：可供单事件原型选目标、生成卡 ID 和选项；社区候选集与自行制定的抽取策略均明确标注，原版资格、权重与同刻顺序继续为 `unknown`。
- [推定首发 24 位英雄的技能节点与审查](scan/historical-hero-power-node-audit.md)、[45 个验收向量](scan/historical-hero-power-vectors.json)及[验证器](scan/verify_historical_hero_power_nodes.py)：逐一核对触发、费用、目标及延迟结算，原版首发开关和事件顺序仍未知。
- [招募阶段九项有界状态转换](scan/historical-recruitment-transition-audit.md)、[参考配置](scan/historical-recruitment-transitions.json)、[32 个验收向量](scan/historical-recruitment-vectors.json)及[执行器](scan/verify_historical_recruitment_transitions.py)：覆盖购买、出售、刷新、冻结、升级、跨手场三合一、打出金色、三选一发现和下一轮；另核对 13 张缺独立金色实体的形式键。原版库存、抽取权重、折扣顺序及同刻事件优先级仍为 `unknown`。
- [布莱恩与蛮鱼斥候的重复发现审查](scan/historical-recruitment-murloc-brann-audit.md)及[32 个斥候招募向量](scan/historical-recruitment-murloc-vectors.json)：按普通／金色卡面建立有界 2／3／4／6 次参考选择，覆盖满手牌、金色奖励、后续非法选择和动态条件回滚；原版资格、权重及顺序仍为 `unknown`。
- [布莱恩与温顺的巨壳龙的战吼叠加审查](scan/historical-recruitment-adapt-brann-audit.md)、[36 个巨壳龙招募向量](scan/historical-recruitment-adapt-vectors.json)及[19 个招募至战斗贯通向量](scan/historical-combat-adapt-vectors.json)：按固定构建普通／金色卡面建立有界 2／3／4／6 次参考选择，核对选择时点、奖励、回滚和英雄淘汰；原版选项、权重及嵌套顺序仍为 `unknown`。
- [战斗生命周期的类型化参考转换](scan/historical-combat-lifecycle-audit.md)、[配置](scan/historical-combat-lifecycle.json)、[基础 30 个验收向量](scan/historical-combat-lifecycle-vectors.json)及[运行器](scan/verify_historical_combat_lifecycle.py)：衔接阵容锁定、八席及代理快照、外部战斗终局输入、伤害淘汰与下轮招募；原版配对与同刻事件顺序未被这些向量证实。
- [逐次战斗事件的有界参考转换](scan/historical-combat-event-audit.md)、[配置](scan/historical-combat-events.json)、[基础 20 个向量](scan/historical-combat-event-vectors.json)及[运行器](scan/verify_historical_combat_events.py)：覆盖攻击、伤害、圣盾、剧毒、固定死亡召唤和战斗结算接线。
- [九类战斗倍数与友军监听节点审查](scan/historical-combat-listener-audit.md)、[类型化节点](scan/historical-combat-listener-nodes.json)及[33 个验收向量](scan/historical-combat-listener-vectors.json)：覆盖普通/金色瑞文戴尔、卡德加及死亡/召唤监听。
- [固定战斗光环与失盾监听审查](scan/historical-combat-aura-audit.md)、[六个类型化节点](scan/historical-combat-aura-nodes.json)及[25 个验收向量](scan/historical-combat-aura-vectors.json)：普通/金色恐狼、鱼人领军、方阵指挥官、攻城恶魔、玛尔加尼斯随从光环与伯瓦尔失盾成长接入战斗；后续追加两条英雄免疫贯通路径。
- [玛尔加尼斯英雄免疫阶段边界](scan/historical-hero-immunity-audit.md)、[类型化节点](scan/historical-hero-immunity-nodes.json)及[17 个生命周期向量](scan/historical-hero-immunity-vectors.json)：参考区分招募时愤怒编织者自伤、玛尔加尼斯在战斗中死亡后的战败伤害及下轮恢复，生命周期向量累计 47 个；原版评价时点仍为 `unknown`。
- [扎普双击与最低攻击力目标审查](scan/historical-zapp-combat-audit.md)、[类型化节点](scan/historical-combat-attack-nodes.json)及[17 个验收向量](scan/historical-combat-attack-vectors.json)：普通卡面直证、金色风怒的后续官方追溯与 14/20 推定分级；每击重选目标、两次攻击、嘲讽冲突和并列目标的有界拒绝、两条英雄伤害贯通路径。
- [铁皮恐角龙超杀召唤与波戈蒙斯塔击杀成长审查](scan/historical-combat-composite-attack-audit.md)、[20 个逐击及终局向量](scan/historical-combat-composite-attack-vectors.json)：普通/金色数值、等额致死、圣盾、满格、同刻死亡和四条英雄伤害贯通路径；小恐龙实体生成链为推断。
- [恩佐斯的子嗣与巨狼戈德林亡语强化审查](scan/historical-combat-death-buff-audit.md)、[15 个逐击及终局向量](scan/historical-combat-death-buff-vectors.json)：普通/金色数值、野兽过滤、同批死亡、瑞文戴尔倍数、固定召唤先后及两条英雄伤害贯通路径。该轮战斗向量累计 130 个；原版同刻顺序仍为 `unknown`。
- [坎格尔的学徒机械死亡历史与重召边界](scan/historical-combat-kangor-audit.md)、[类型化节点](scan/historical-combat-kangor-nodes.json)及[18 个逐击及终局向量](scan/historical-combat-kangor-vectors.json)：普通/金色前 2／4 台己方机械、死亡批次、重召状态参考选择、七格截断及三条英雄伤害贯通路径。该轮战斗向量累计 148 个；原版同刻顺序与重召状态仍为 `unknown`。
- [骑乘迅猛龙与两张载人机械原卡费用随机亡语审查](scan/historical-combat-random-cost-audit.md)、[类型化节点](scan/historical-combat-random-cost-nodes.json)、[33 个候选的固定构建费用摘录](scan/historical-combat-random-cost-candidates.json)及[29 个逐击及终局向量](scan/historical-combat-random-cost-vectors.json)：区分客户端费用直证与同期社区参考池，贯通三张来源的普通／金色召唤、满格、瑞文戴尔及四条英雄伤害路径。该轮战斗向量累计 177 个；原版候选资格与权重仍为 `unknown`。
- [斯尼德的伐木机传说亡语审查](scan/historical-combat-random-legendary-audit.md)、[普通及金色节点](scan/historical-combat-random-legendary-nodes.json)、[12 项社区参考候选的客户端标签摘录](scan/historical-combat-random-legendary-candidates.json)及[16 个逐击及终局向量](scan/historical-combat-random-legendary-vectors.json)：核对普通／金色 1／2 次请求，仅在两个可界定候选上运行有界召唤与英雄伤害，其他候选及原版精确模式拒绝；该轮战斗向量累计 193 个。H10 只佐证“12 种”的同期数量口径，原版成员资格、权重及事件顺序仍为 `unknown`。
- [阴森巨蟒随机亡语候选及战斗审查](scan/historical-combat-random-deathrattle-audit.md)、[普通及金色节点](scan/historical-combat-random-deathrattle-nodes.json)、[22 项候选的客户端标签摘录](scan/historical-combat-random-deathrattle-candidates.json)及[18 个逐击及终局向量](scan/historical-combat-random-deathrattle-vectors.json)：卡面 2／4 次召唤请求直证，H09 的 22 项社区池仅作参考，当前两个候选可执行且生成后亡语能继续强化；战斗向量累计 211 个，其中 29 条贯通终局。原版候选资格、权重及事件顺序仍为 `unknown`。
- [历史玩法和判定规格](scan/historical-2019-mechanics.md)、[逐字段标记证据等级的规则参数](scan/historical-rule-parameters.json)、[固定衍生物与动态池缺口](scan/historical-token-pool.md)、[28 个英雄资源及推定首发 24 人](scan/historical-hero-candidates.md)、[内容素材制作规格](scan/content-asset-plan.md)、[历史来源与核验边界](scan/historical-evidence.md)：区分客户端直证、官方公告、同期社区记录和可执行参考规则。
- [同期第三方战斗模拟器的五类动态候选池及逐 ID 差异](scan/historical-community-simulator-pools.json)：固定到 2019 年 11 月 17 日的社区代码提交；不等于暴雪服务端真实名单、权重或事件顺序。
- [同期原版录像与可重放战报核验](scan/historical-replay-audit.md)：记录视频入口、作者文字可核部分、七张争议卡逐项状态及精确复刻的证据门槛。

先前的 iPhone 中国/全球上架与其他市场调查在[No23目录](../No23-iphone-indie-game-publishing-market/README.md)。详规是拟议产品的工程设计，不能据此宣称原提案已通过盈利、授权或发行审查。
