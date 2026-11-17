# 新导出JavaScript脚本核查

后续95份脚本已补齐，最新结果见[第二轮核查](client-script-execution-review.md)。下文保留第一批输入时的发现和依赖状态。

2026-11-18由三个子agent分别核查任务加载、节点执行、剧情调用，主agent复读关键方法并整合结果。

## 输入与核查方式

输入目录为`work/client-scripts/JavaScript/`，共1178份文件、3,218,465字节。文件采用`.json`后缀，实际内容为JavaScript源码。分析采用静态文本检索、相对require路径解析及原文片段定位。

本地分工记录保存在`work/client-script-review/loading.md`、`execution.md`和`flow.md`。`logic_tree_imports.json`保存全部17处GeneralLogicTree引用，`source_excerpts.json`保存主agent复核的原文与SHA-256。

## 已确认可利用的实现

### 任务配置的读取入口

`Game/Module/QuestNew/QuestConfig.json`中的`GetQuestNodeConfig`使用`questId + "_" + nodeId`查询`QuestNodeDataByKey`。`QuestModel.json`随后对返回行的`Data`执行`JSON.parse`并缓存。

这与当前解析器的任务ID、节点ID和内嵌JSON读取方式相符。缓存读取端仅显示单节点查询。非数据库分支会把任务的`Tree`交给`GeneralLogicTreeConfigUtil.InitBehaviorNodeConfig`，其实现仍需要补充。

### 同步与异步的客户端剧情调用

`Game/LevelGamePlay/LevelEvents/LevelEventClientPlayFlow.json`中的`$qy`在异步模式启动剧情后设置动作完成；同步模式保存返回的FlowIncId，监听`PlotNetworkEnd`。回调同时匹配FlowIncId、FlowListName、FlowId和StateId。

该实现有适用边界。`ExecuteNew`先检查目标为客户端流程，并限制上下文Type为1，或Type为5且IsClientTrigger成立。后续解析规则应保留这一范围及调用实例标识。

### 动作组与服务端会话

`Game/LevelGamePlay/LevelGeneralController.json`的`ExecuteActionsNew`将动作数组逆序压栈，再通过`HandleNextAction`弹出执行，保持原动作数组的先后。`Async`缺省值为false。

`LevelGeneralNetworks.json`通过网络回调接收动作会话，调用`ExecuteActionsByServerNotify`并传递起止动作索引。部分行为树上下文转发`BehaviorTreeStartActionSession`。当前文件提供了发送事件的位置，其行为树接收方位于待补充的实现层。

上述代码能帮助解释动作数组、会话与等待语义。完整节点激活和跨分支次序仍需要行为树实现及相应运行上下文。

## 同名模块的实际范围

`QuestTree`提供章节展示图，使用PreNode、NextNode和SortOrder组织界面内容。当前代码未建立这些字段与QuestNodeData行为节点之间的排序映射。

`LevelFlow`当前入口创建`LevelFlowTiTanData`，后者包含特定关卡的固定四段配置。`LevelFlowSequenceAction`确有逐项执行子动作的实现。将它与任务配置Type=Sequence关联，仍需要找到明确的构造映射。

这些区别需要保留在后续解析设计中，避免仅凭名称相同就合并语义。

## 下一批最小补充范围

在FModel中继续导出以下JavaScript目录，保留原有层级。

```text
Client/Content/Aki/JavaScript/Game/Module/GeneralLogicTree/
Client/Content/Aki/JavaScript/Game/Module/Plot/Flow/
```

第一项具有最直接的节点构造和推进线索。现有脚本的17处require指向该目录下8种文件，当前全部缺失。

```text
GeneralLogicTreeConfigUtil
LogicTreeContainer
GeneralLogicTreeController
GeneralLogicTreeUtil
Define/GeneralLogicTreeDefine
BehaviorNode/LogicNode/LogicNodeBase
ControllerAssistant/ControllerAssistantBase
ControllerAssistant/ControllerWithAssistantBase
```

第二项由`LevelEventClientPlayFlow`直接引用`FlowController`，用于进一步核查剧情启动、结束及状态跳转。

当前JavaScript已经足以开展静态阅读。TypeScript和source map可作为后续辅助，下一轮优先补齐上述缺失的JavaScript实现。

## 当前结果与边界

三路核查确认这批文件有实际参考价值，并定位了精确的缺失依赖。当前新增证据尚未解决《眠龙庭》10组Sequence兄弟节点的执行顺序。现有解析器与导出语料的状态继续沿用上一轮验证结果。
