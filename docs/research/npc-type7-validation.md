# NPC表演Type7与《烟云幽远心剑鸣》

## 数据证据

全flowstate的19次FlowDefineNpcGroupPerform中，Type7只有剧情_3_6_心魔幻境_53_1一处：PerformType={Type:7, Key:chanfu}。外层仅Name、Params、ActionGuid、ActionId；没有显式条件、回调或嵌套动作。测试流程剧情_LYZ_TEST_3.6_1_1使用相同Key但Type0，不能据此断言Type0和7等价。

精确Key还出现在任务915000005节点29的SetNpcGroupPerform（Type6、Player、Target=915800000、IsWaitActionFinish=true），节点6的RemoveNpcGroupPerform。节点20描述为“回去搀扶清宵”，另用chanfu2。交互库也有chanfu创建调用，表情库有Helpless_chanfu动画路径。这支持Key属于搀扶表演上下文，但不足以证明Type7枚举语义、完成条件或隐式回调。

NpcGroupPerformConfig的6行仍均为Type5；不能把不同动作的Type数字当作同一枚举，也不能用名称强行关联。当前没有引擎实现或资产内回调证据。

可复核原动作、SHA256、关联任务节点与文本保存在work/npc_type7_evidence.json。

## 调用与文本顺序

53/1原数组为SetPlotMode → PostAkEvent → FlowDefineNpcGroupPerform(Type7) → ShowTalk → PostAkEvent。ShowTalk只有TalkId=1，TalkSequence=[[1]]，文本键Main_Mengzhou_3_6_413_2，说话人WhoId=350141解析为清宵：

> 先把我放下……你会便于行动一些。

相邻回顾文字为前段“……呼……嗯……”和后段“我……用飞剑助你。”恢复句子使用原回顾位置，未把上下文推断当作排序依据。

ShowTalk另引用DA_M3_12_24演出；TalkFrameEvents的A事件在TalkItemId=1、Offset=-1处调用DestroyEntity(EntityIds=[915800000])。这是ShowTalk的帧事件，不是已证实的Type7完成回调。它没有直接文字或分支；原配置完整保留，但Offset的帧时序、销毁效果及演出资产都不模拟。本轮没有宣称帧事件或隐式回调已执行。

## 通用规则

阅读模式允许Type7加非空Key的精确标量形状，与既有Type0/1共用字段校验；不写死任务ID或chanfu。未知Type、空白Key、额外字段、嵌套逻辑、显式回调和Async=true拒绝。Type0同时收紧为空白Key拒绝。严格模式仍拒绝该表演动作。

仅按显式配置继续读后续对白，JSON保留source_action、callbacks_verified=false。Type7额外记录enum_semantics_verified=false、runtime_completion_verified=false、asset_content_verified=false、order_scope=explicit_configuration_only。TXT保留对白；资产与全任务的未核验状态继续存在。

## 结果与验收范围

代表任务85成功/1阻塞→86成功/0阻塞。恢复1句对白，替换1个缺口，因此总事件仍542。回顾配置全可读，不等于全任务通过阅读验收或运行时模拟完成。

136项测试通过，覆盖Type7通用Key、参数/回调拒绝、前后顺序、未核验标记和严格模式。批次20261117_022259_453266对比20261117_022006_840272核对135对JSON/TXT，恢复1任务1段1事件。原成功正文和静态文字保留，渲染一致，《来自毁灭的回声》不变。仍有回顾段落阻塞的任务36→35；任务分类仍12确定路线、1部分有序、60回顾草稿、62材料清单，严格通过2，未新增整任务验收。

[样本TXT](../../outputs/回顾主干验证/915000005_烟云幽远心剑鸣.txt) · [样本JSON](../../outputs/回顾主干验证/915000005_烟云幽远心剑鸣.json)

[批量覆盖报告](../../outputs/主线批量/20261117_022259_453266/覆盖阅读版/覆盖报告.md) · [产物核对](../../outputs/主线批量/20261117_022259_453266/覆盖阅读版/产物核对.json)

下一步从剩余35个回顾阻塞任务中选择高频且有明确配置证据的动作；同时保持配置顺序与运行时完成分开记录，变量和条件不作为表现动作跳过。资产继续最后核验。
