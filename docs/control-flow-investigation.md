# 变量与状态控制核查（2026-11-17）

## 结论

本轮未放宽SetVar、FinishState或ChangeState支持。它们能改变后续分支和流程边界，不能照搬镜头/特效动作的“保留记录后继续读取”策略。代码没有因本次调查跳过这些控制。

可复现脚本：`PYTHONPATH=src python work/investigate_control_flow.py`（PowerShell先设置环境变量）。输出work/control_flow_evidence.json，包含原始动作、JSON路径、原始记录SHA256及完整代表条件节点。脚本内验证3个写入与2个比较条件，数据库以只读方式打开。

## 已核查数量

全部可解码flowstate内：SetVar 644次，FinishState 282次，ChangeState 54次。这是全库调用次数，包含测试、支线和嵌套动作，不是主线失败数量。

基线批次20261117_022259_453266中，回顾段落的首个错误分别有SetVar 19处、FinishState 3处、ChangeState 1处。修复首错不保证整段通过。该基线另有3处条件对白错误。

## 代表依赖：《捕梦于神秘园中》147000002

在剧情_2_5_隐海试验场_声骸培养场_1_2中，玩家选项分别把Self Boolean变量“是否选了右边的路”写成false/true；1_14中还存在一次写true。相同变量不是无用标记。

任务节点147000002_33是ConditionSelector，明确含两个CompareVar/Eq条件：

- 值为false：进入ParallelSelect 64，再经ChildQuest 34往左，异步调用1/17。
- 值为true：进入Sequence 104，包含ChildQuest 105→106→107→114；依次涉及玩法147700013、异步8/1、同步1/3，之后才回到往左与异步1/17。

因此，虽然两条路最终可能汇合，中间实际经过的玩法、对白和顺序不同。若把SetVar无条件跳过，可能把右路内容错误拼进左路，或将两路都视为必经。

上面的相同Self变量引用发生于同一任务上下文，只能作为本任务依赖证据；不能全库按变量名字相同就合并作用域。

## FinishState/ChangeState边界

狂欢节21/2中，TalkId5动作是FinishState后接FinishTalk；外层ShowTalk后仍有FadeInScreen与DestroyEntity。狂欢节60/1中，FinishState既出现在玩家选项中，也出现在末句动作中。仅凭“FinishState”名字不能确定它是立即中断所有调用栈、仅标记状态完成，还是等待当前动作收尾。不得简单映射为FinishTalk，更不能作为无效果操作略过。

ChangeState当前常见载荷为StateId，但需要先确认目标状态的作用域、跳转时机、循环以及与原动作尾部的关系，不能直接按ID大小排列或从当前点继续。

## 后续实现顺序

1. 明确Self/Global及任务实例作用域；建立带类型的变量环境。未赋值必须保持unknown，不能默认为false/0。
2. 只执行已选路径上的常量赋值，记录前后值与动作来源，不执行未选分支。
3. 验证CompareVar操作及ConditionSelector结构，unknown时保留分支缺口，不猜路线。
4. 把环境沿任务依赖图传播；当前独立回顾段落每段新建Exporter，不能假装拥有跨段运行状态。
5. 分别验证FinishState和ChangeState的控制边界，再实现返回/跳转传播与循环检测。

这属于控制流解释器工作，资产保持后置不影响开展；但不应为了增加“解析通过数”而丢弃控制信息。
