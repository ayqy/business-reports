# 2019 上线周：逐次战斗事件的有界参考转换

**核验日：2026 年 9 月 26 日（北京时间）。** 本文服务于管理员要求的详细玩法规格。参照构建为 `15.6.0.35747`；[配置](historical-combat-events.json)、[基础 20 个验收向量](historical-combat-event-vectors.json)、[九类监听节点及 33 个向量](historical-combat-listener-audit.md)、[固定光环与失盾监听及后续免疫边界的 25 个向量](historical-combat-aura-audit.md)、[扎普双击及强制目标的 17 个向量](historical-zapp-combat-audit.md)、[超杀召唤及击杀成长的 20 个向量](historical-combat-composite-attack-audit.md)、[两类群体强化亡语的 15 个向量](historical-combat-death-buff-audit.md)、[坎格尔死亡历史与重召的 18 个向量](historical-combat-kangor-audit.md)、[三张随从随机费用亡语的 29 个向量](historical-combat-random-cost-audit.md)、[斯尼德传说亡语的 16 个向量](historical-combat-random-legendary-audit.md)、[阴森巨蟒随机亡语的 18 个向量](historical-combat-random-deathrattle-audit.md)和[执行器](verify_historical_combat_events.py)只定义**可执行参考实现**，不声称复原暴雪服务端战斗队列。[完整机制目录](historical-2019-mechanics.md)、[证据账本](historical-evidence.md)分别保存历史说明和 H01/H03/H04/H09/H16 出处。

[温顺的巨壳龙七种非数值进化效果](historical-combat-adapt-audit.md)另有 18 个跨招募、逐击和终局的参考向量；其[专项验证器](verify_historical_adapt_combat.py)与下述 211 个既有逐击向量分别运行，不能把两组数混为同一验收口径。

## 证据裁决

| 命题 | 来源与等级 | 可用于本转换器的范围 |
|---|---|---|
| 招募结束后自动战斗，随后依据胜负、伤害和淘汰继续循环 | 暴雪 2019 官方说明 H01，`[O]` | 可确定阶段关系；不能推出逐帧事件优先级。 |
| 嘲讽目标、左右攻击、平局与英雄伤害计算 | 同期历史说明 H03，`[W]` | 可支持参考规则的语义；不证明目标抽样权重。 |
| 正义保护者的嘲讽/圣盾、迈克斯纳的剧毒、机械袋鼠普通及金色亡语衍生物等卡面定义 | 固定构建客户端 H04，`[C]` | 基础攻生、文字和已核对实体；不证明效果到服务端事件的精确路由。 |
| 三张随从的原卡费用随机亡语 | H04 卡面及 H05 构建内费用 `[C]`；H09 仅为第三方数组 `[S]` | 普通／金色请求 1／2 次及费用 1／2／4 可核；9／10／14 项参考数组和调用方索引不能证明原版候选资格与权重。 |
| 斯尼德普通／金色的传说召唤 | H04 卡面给出 1／2 次请求、H05 给出客户端传说标签 [C]；H09 的 12 项数组 [S]，H10 只旁证同期数量口径 [M] | 候选索引和两个可执行产物只能标参考注入；12 个 ID 均带传说标签不等于原版可生成，资格、权重、同刻顺序为 unknown。 |
| 阴森巨蟒普通／金色的亡语随从召唤 | H04 卡面给出 2／4 次请求；H05 的 22 个客户端亡语标签 `[C]` 与 H09 的 22 项社区数组 `[S]` 集合一致 | 仅核对标签和社区数组；两个可执行候选、生成后的再次亡语及英雄伤害都是 `[R]` 参考转换，不能证明原版资格和顺序。 |
| 同刻伤害、死亡、亡语与召唤的先后顺序 | H01—H04 无可重放同构建战报；H09 只能证明第三方模拟器自身实现 | 原版为 `unknown`；下述先后仅为 `[R]`。 |

本轮没有新的同构建原版战报。所有实际未核定的先攻、目标概率、同刻队列、召唤插入点、倍数源和衍生物伤害等级，均由[配置的 `historical_unknown`](historical-combat-events.json)保留为 `unknown`。输入侧须为关键词、先攻方、目标和 token 等级标明可核来源或 `reference_injected`；不能把由输入注入得到的战斗结果写成原版实测。

## 用户故事与动作合同 `[R]`

用户在招募结束后应看到逐次攻击、圣盾被打破、剧毒击杀、死亡和召唤的可解释日志，终局再看到英雄生命变化。战斗副本来自[生命周期转换器](historical-combat-lifecycle-audit.md)的 `begin_combat` 快照；招募原阵容不受临时损伤影响。当前有界实现以调用方给定的首攻方和合法目标开始，不替它宣称原版抽样。

| 输入或状态 | 检查与转换 |
|---|---|
| `CombatState` | `phase`、双方 `board[0..7]`、`turn`、各方下次攻击游标、`initial_ids`、已生成清单、序号、`death_batch_serial`、双方独立的 `mech_death_history` 与事件日志；所有实例 ID 全局唯一。 |
| `CombatUnit` | 从 81 卡表或固定衍生物表取基础攻生与种族，并叠加快照强化；`health` 为当前生命、`max_health` 为有效最大生命，伤害仅减少前者；关键词由有等级的输入指定，已核对的固定卡面关键词不得静默省略。 |
| `attack(attacker_id,target_id,token_tiers?)` | 进攻方从游标顺序选可攻击个体；普通随从遇到对方嘲讽须以嘲讽为目标。主动攻击和主目标反击取攻击前快照；顺劈主目标及左右邻居，邻居不反击。 |
| `BGS_022` 与 `pending_extra_attack` | [扎普节点](historical-combat-attack-nodes.json)按每击当前最低攻击力校验目标；首击后若仍可行动则保留同方待击，第二击重新校验，再切换进攻方。嘲讽冲突拒绝，并列目标必须显式标注参考注入。金色 14/20 仍是三合一推断。 |
| `TRL_232 / OG_300` 攻击后效果 | [复合攻击节点](historical-combat-attack-nodes.json)在死亡批次后处理铁皮恐角龙的严格超额伤害召唤，或波戈蒙斯塔自攻击杀后的 2/2、4/4 成长。来源同刻死亡和顺劈组合原子拒绝，衍生物 ID 连线仍为推断。 |
| `OG_256 / BGS_018` 群体强化亡语 | [亡语强化节点](historical-combat-death-buff-nodes.json)在本批死者移除后逐次强化存活友军；巨狼只命中野兽和 `ALL` 种族。单一存活瑞文戴尔可使每次亡语执行两遍或三遍。原版同刻优先级仍为 `unknown`。 |
| `BGS_012` 坎格尔的学徒 | [重召节点](historical-combat-kangor-nodes.json)从战斗开始记录己方机械逐批死亡历史，普通／金色各选最先 2／4 台，以显式参考状态复制为临时单位；同批无法判先后、重复死亡身份及卡德加组合拒绝。原版重召状态和优先级仍为 `unknown`。 |
| `BGS_025 / BGS_023 / BGS_024` 随机亡语 | [三张原卡费用节点](historical-combat-random-cost-nodes.json)把 1／2 次请求接入逐次死亡事件；仅使用 H09 数组中由调用方分级注入的索引，固定构建候选费用与普通攻生见[摘录](historical-combat-random-cost-candidates.json)。缺索引、命中未覆盖候选、同批双来源和卡德加组合原子拒绝；原版生成资格与权重仍为 `unknown`。 |
| `BGS_006` 斯尼德传说亡语 | [传说亡语节点](historical-combat-random-legendary-nodes.json)依 H04 产生普通／金色 1／2 次请求；H09 的 12 项有序数组仅作参考索引，本执行器只支持百变泽鲁斯与布莱恩·铜须的有界战斗状态。未覆盖候选、索引错误、同批双随机来源与卡德加组合原子拒绝；H10 只旁证数量。 |
| `BGS_008` 阴森巨蟒亡语随从召唤 | [随机亡语节点](historical-combat-random-deathrattle-nodes.json)依 H04 产生普通／金色 2／4 次请求；H09 的 22 项数组仅作参考索引，本执行器只支持恩佐斯的子嗣与巨狼戈德林。生成者后来死亡可触发其已编译群体强化亡语；未覆盖或递归候选、索引错误、同批多随机来源与卡德加组合原子拒绝。 |
| `BGS_031` 进化后战斗状态 | [巨壳龙战斗审查](historical-combat-adapt-audit.md)将嘲讽、风怒、圣盾、潜行、剧毒接入逐击，孢子亡语接入带等级的植物召唤；免于法术或英雄技能指定作为类型化状态保留，普通攻击仍可命中。重复关键词、潜行次轮清除、满格召唤和原子拒绝另有专项向量。 |
| `hit` | 圣盾吸收一次正伤害并消失；只有实际造成正伤害，剧毒才令目标死亡。此轮把主攻及反击记录为一个打击事件，之后统一移除死亡批次。 |
| `death/summon` | 固定亡语或存活后的受伤召唤使用已列出的普通/金色衍生物；先移除本批死亡，再按左方、右方及原位置参考顺序生成。每方最多七格，多余召唤记 `summon_dropped`。战前所有实例 ID 始终保留在分配禁用集中，避免死亡后重用。 |
| `terminal` | 某一方已无随从时，导出 `left_survivors/right_survivors/generated`，交给生命周期 `settle_combat` 算胜负、英雄伤害和淘汰；临时单位只进入终局清单，不写回招募阵容。 |

已核对的[九类倍数与友军监听节点](historical-combat-listener-audit.md)、[五类固定随从光环及伯瓦尔失盾监听](historical-combat-aura-audit.md)、[扎普双击节点](historical-zapp-combat-audit.md)、[两类攻击后效果](historical-combat-composite-attack-audit.md)、[两类群体强化亡语](historical-combat-death-buff-audit.md)、[坎格尔重召](historical-combat-kangor-audit.md)、[三张随从的参考随机亡语](historical-combat-random-cost-audit.md)、[斯尼德传说亡语](historical-combat-random-legendary-audit.md)及[阴森巨蟒随机亡语](historical-combat-random-deathrattle-audit.md)现可在有界输入下执行；同方多个倍数源、瑞文戴尔与卡德加组合、卡德加跨侧召唤、剩余未编译的随机亡语、坎格尔同批死亡和重复身份、两类攻击效果的来源同刻死亡，以及扎普的嘲讽冲突仍明确拒绝，并保持动作前状态。[玛尔加尼斯英雄免疫](historical-hero-immunity-audit.md)仅在已界定的招募自伤与终局伤害分支执行参考判定。缺 token 等级、非法嘲讽目标及 `exact_2019` 请求也回滚。执行器没有逐卡完整支持：未知候选池和全部 81 张卡的组合尚未模拟。零攻击但仍存活的整侧和更多关键词也尚无终局裁决，不能拿本向量代替完整复刻验收。

## 验收

[20 个参考向量](historical-combat-event-vectors.json)含 17 个单动作场景及 3 条从 `end_recruit → begin_combat → attack → settle_combat` 贯通的场景：

| 向量 | 边界与预期 | 证据性质 |
|---|---|---|
| CE-01—05 | 同批双死、嘲讽非法目标回滚、圣盾挡毒、有效剧毒、顺劈仅主目标反击 | 关键词和基础攻生取 H04；事件顺序为 `[R]`。 |
| CE-06—08、12、16 | 普通/金色固定亡语、七格截断、对手侧召唤、受伤后召唤 | 母卡及衍生物定义取 H04；具体插入与等级标 `[R]`。 |
| CE-09—11、13—15、17 | 未编译随机亡语原子回滚；缺衍生物等级失败、战前 ID 不被新单位复用、拒绝 `exact_2019`；CE-11 验证铁皮恐角龙超杀缺 token 等级，CE-17 验证扎普首击清场即终止 | 参考安全合同 `[R]`。 |
| CE-B01—B02 | 各三次交替攻击，分别平局零伤和胜者造成 3 点英雄伤害并淘汰败者 | 阶段关系 H01、伤害公式 H03；打击顺序 `[R]`。 |
| CE-B03、LC-29—30 | 比斯巨兽死亡在对侧生成芬克，对侧临时单位按注入等级结算英雄伤害；伪造来源被拒绝 | H04 定义，生成事件及 token 等级 `[I]/[R]`。 |

执行 `python3 scan/verify_historical_combat_events.py` 对基础 20 个、[监听 33 个](historical-combat-listener-vectors.json)、[光环/失盾和免疫边界 25 个](historical-combat-aura-vectors.json)、[扎普 17 个](historical-combat-attack-vectors.json)、[两类复合攻击效果 20 个](historical-combat-composite-attack-vectors.json)、[两类群体强化亡语 15 个](historical-combat-death-buff-vectors.json)、[坎格尔重召 18 个](historical-combat-kangor-vectors.json)、[随机费用亡语 29 个](historical-combat-random-cost-vectors.json)、[斯尼德传说亡语 16 个](historical-combat-random-legendary-vectors.json)及[阴森巨蟒随机亡语 18 个](historical-combat-random-deathrattle-vectors.json)向量累计得到 **211/211**，其中 **29** 条贯通终局；另由 `python3 scan/verify_historical_adapt_combat.py` 核对 **18/18** 条进化跨阶段向量、`python3 scan/verify_historical_combat_lifecycle.py` 核对 **47/47** 条生命周期向量。这些验证仅说明参考合同内部一致；它们没有证明原版目标权重、扎普嘲讽例外或并列目标、金色实体、衍生物生成链、坎格尔重召状态、随机候选资格与权重、免疫评价时点、事件优先级、配对和完整逐卡胜负。
