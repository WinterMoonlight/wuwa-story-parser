# 变量与条件并行核查（2026-11-17）

## 结论

本轮不扩大跨任务、跨回顾段的变量传播。已有条件投影对“无外部写入”有明确假设，但必须先排除配置中已经可见的矛盾；不能拿假设覆盖一个已知写入。

新增 `conditional_guard.py` 只做拒绝和记录证据，不执行任务动作，不改变量作用域，不推断资产回调。

## 数据证据

扫描 Type1/Type15 任务及其任务/回顾引用流程，按任务归属记录得到 58 次 SetVar：30 次 Boolean/Self/Name、14 次 Int/Global/Keyword、7 次 String/Global/Keyword、7 次 Boolean/Global/Keyword。这不是全库唯一动作数；复用流程与两类任务记录会重复计入。原始记录为 `work/audit_variable_inventory.json`。

现有变量解释器只支持 Boolean，并以 Name 标识变量。真实 Global 写入使用 Keyword，不能简单把全部 SetVar 加入白名单。Int、String、Global 和 Other/Entity 读取均需要单独的作用域和来源证据。

递归扫描节点得到 457 个 Type=CompareVar 对象，其中 265 个是 `{Type, Count, Conditions}` 包装结构，192 个是 `{Type, Var1, Compare, Var2}` 原子比较。原子操作包括 Eq177、Ge6、Lt5、Ne3、Gt1。嵌套与平铺的节点副本会重复计入；这些数字用于确认形状，不是唯一条件数量。不能只凭 Type=CompareVar 解释为一种结构，也不能擅自将 Count 解释成布尔 AND。

## 已复现的投影漏洞

以 147000002《捕梦于神秘园中》的真实未投影回顾为底本，分别变异：

1. 在 writer 节点22的 FinishActions 尾部加入对“是否选了右边的路”的 true 赋值。旧投影仍使用对白选项留下的 false 值，选择左路。
2. 给 writer 流程的 ShowTalk 设置 Async=true。旧投影仍将其中选项赋值视为已经在条件判断之前完成。

这两种是反例测试，不是说当前游戏快照本身存在这两处配置。实际节点22的 FinishActions 有唤醒实体、修改实体状态、启用玩法等外部效果，尚不能证明无间接写入；原有“不被外部交互覆盖”的声明继续保留。父 Sequence28 没有 Children 数组，不能凭同父或 Id 顺序声称运行时相邻。

反例脚本：`work/audit_variable_counterexamples.py`。接入 guard 之前，基线和两个反例均投影到 slot0。

## 本轮防护规则

- writer 动作树含 Async 非 false 时拒绝投影，包括包裹赋值的异步 ShowTalk。
- 检查 writer.FinishActions 和 selector.EnterActions；同变量写入、无法识别目标的 SetVar、状态结束/跳转控制均保留缺口。
- 父 Sequence 有明确 Children 时，检查两个端点唯一且方向一致，并检查中间节点。嵌套和平铺副本均检查，不能以其中一份覆盖另一份。
- 父节点不提供 Children 时返回 `parent_order_evidence=not_available`；沿用回顾投影假设，不增加运行时排序证明。
- 其他已明确命名的变量写入不冒充目标变量写入；资产、玩法间接写入仍属未核验。

## 验证与边界

独立测试 `tests/test_conditional_guard.py` 的7项通过，包含反向顺序、未解析中间节点、异步祖先、已知写入、其他变量、无副作用检查。真实147000002基线 guard.allowed=true。

主 agent 已接入 conditional_recap，并增加真实配置变异的集成反例：拒绝投影时原段落不变。177项全套测试和135任务批量核对通过，见[整合验证](control-flow-review-validation.md)。该模块本身不增加任何“整任务完成”数量，不把 Global/Int 支持当成本轮已经完成。
