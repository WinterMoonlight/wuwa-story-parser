# 逻辑树与剧情运行器补充核查

2026-11-18完成第二轮三路静态核查。新增GeneralLogicTree共83份.js，Plot/Flow共12份.js；项目脚本总数为1273。项目副本与FModel导出源逐文件SHA-256一致。

分工记录与原文定位保存在`work/client-script-review-round2/loading.md`、`execution.md`、`flow.md`。主agent复读了节点工厂、状态通知、基类更新、配置展开和剧情动作映射等关键调用点。

## 已找到真实任务节点类

`GeneralLogicTree/Define/NodeTypeDefine.js`的`newNodeObj`明确将配置Type为Sequence的节点构造为SequenceNode，将ParallelSelect构造为ParallelSelectNode。

`SequenceNode.js`设置节点类型，并处理激活/停用时的性能模式和镜头预算中心。`ParallelSelectNode.js`仅设置节点类型。共同父类LogicNodeBase处理标签、任务显示、玩法开关、存档点等内容。这条继承链中尚未找到遍历Children、决定下一子节点或按Count聚合成功/失败的算法。

## 已闭合节点状态更新链

```text
网络消息23007
  → ServerNotifyAssistant.X$t
  → BaseBehaviorTree.UpdateNodeState
  → BehaviorNodeBase.UpdateStatus
  → OnNodeActive / OnNodeDeActive
```

通知中包含树实例、节点ID与节点状态。UpdateNodeState据此更新已有节点，节点不存在时创建节点。恢复路径Recover读取运行快照中的节点状态对象，枚举键后创建相应节点。

这能确认当前客户端消费服务端下发的节点状态。恢复快照的Object.keys顺序不能据此作为任务执行次序。服务端内部如何选择后继节点、计算并行完成条件，尚未取得对应实现。

## 已闭合动作会话链

```text
LevelGeneralNetworks.QUe
  → BehaviorTreeStartActionSession
  → GeneralLogicTreeController.mYt
  → BaseBehaviorTree.DoAction
  → LevelGeneralController.ExecuteActionsByServerNotify
```

DoAction依据上下文选择节点的Actions、EnterActions、FinishActions等数组，并使用会话给出的StartIndex、EndIndex等参数。动作执行器按指定区间的数组次序执行。这解释了任务节点与实际动作之间的连接，但同级节点的完整先后仍需额外顺序证据。

## 配置展开路径

GeneralLogicTreeConfigUtil.InitBehaviorNodeConfig调用`UniverseEditor/Interface/IQuest`的`flatBehaviorTree`，再将返回的节点按ID写入Map。

这一展开路径由QuestModel的非数据库加载分支调用。数据库加载分支仍按`questId_nodeId`取得单条记录并解析Data。当前没有读取到IQuest的具体实现，也没有证明非数据库分支是当前游戏运行的实际数据路径。

若继续核查配置层面的顺序，下一份最小补充文件为

```text
Client/Content/Aki/JavaScript/UniverseEditor/Interface/IQuest.js
```

它可用于检查原始Tree的展开方式。该文件与服务端节点调度规则的覆盖范围仍需要分别验证。

## 剧情运行器的可利用部分

Plot/Flow中的FlowConfig按FlowListName、FlowId、StateId查找某个State的动作数组。FlowActionRunner保持顶层数组次序，并通过回调继续动作。FlowShowTalk按TalkItems数组推进，SwitchTalkItem按TalkId定位目标。

FlowSequence处理当前演出的TalkSequence分组、字幕事件及QTE回调。其序号属于演出字幕组，尚无证据将其直接用于任务树Sequence的同级排序。

FlowActionCenter还引用同级`Plot/FlowActions`目录中的56种动作实现，当前尚未导出。若后续核查JumpTalk、ChangeState、FinishState等参数与转移规则，可补充该目录。当前缺口按`.js`和旧导出`.json`两种后缀均已检查。

## 对眠龙庭的结果

新增脚本使节点配置、节点状态和动作执行的调用链更加明确。当前仍无法为原有10组Sequence同级节点给出经源码确认的次序，也未取得ParallelSelect的完整Count判定算法。

当前51条局部文本与已有证据继续作为阅读材料。此轮产物为源码核查记录，后续规则变更需要具体映射和验证结果支撑。JavaScript可以继续使用，TypeScript暂作可选辅助来源。
