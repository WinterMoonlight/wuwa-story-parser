# 第七轮：归属补漏、同步后缀与手机正文

2026-11-17，3.8.11数据快照。基线20261117_123229_887664。本轮保留16任务27处回顾阻塞，三个子agent分别核查实体归属、调用顺序、外部正文，主agent复核并整合。资产与原始数据库未修改；有序前缀不计完整解析。

## 归属：实体触发对白

此前declared_entity_content仅扫描任务子实体的BubbleComponent/InteractComponent。新增entity_trigger_content沿QuestData.Children的精确e_MapId_EntityId声明，唯一关联db_level_entity.db/levelentityconfig行；不从Reference或同EntityId其他地图推断任务所有权。

仅取已核查路径中的实际PlayFlow：TriggerComponent.Actions与ExitConfig.Actions、ClientTriggerComponent.OnTriggerEnter/OnTriggerExit.Actions、EntityStateComponent.StateChangeBehaviors[*].Action。Preload、RemovePreloadResource即使含流程三元组也不是对白调用，排除。JSON保留实体声明、完整组件条件、动作路径、原始动作、源哈希和记录指针。

任务690000001《远航星》三个异步触发流程1/20/1、1/25/1、1/69/1合计7条文字原先未收录。本轮放入候选材料，TXT注明触发条件和主干顺序尚未核验；不解释为必经对白，不把动作数组顺序扩展成主干顺序。已有主干、交互和玩法来源优先保留，新增候选按精确流程键避免重复收录。

## 顺序：所有互斥分支共有的同步后缀

114000026《如一叶小舟穿行于茫茫海洋》节点114/123/130的FinishActions都只有两条同步PlayFlow：序幕1/1→10/1。回顾1/1仅出现一次，10/1未列回顾。节点110按Global DirectTrain的互补布尔值分路；120按任务145000004节点31完成条件的Eq/Ne分路。所有叶路径均为Sequence/ConditionSelector，任意两叶有互补选择器分歧。

新增sync_call_suffix验证所有精确锚点及后缀引用都来自该调用对，内嵌节点与独立节点一致。Sequence内嵌Children对应ParentNodeId关联子节点，不能仅比较被扁平化后删除Children的字典。祖先和叶节点限定已核查字段，拒绝循环、其他控制字段、额外或异步调用、重复回顾锚点、不互补条件、不同内嵌副本。后缀只接受完整可解析的SetPlotMode/ShowTalk，拒绝动作回调、条件选项、跳转、QTE及未核验副作用。

10/1的12条对白与1个选项放到回顾1/1之后，JSON保留3个调用点、条件分支与源动作。该证据证明局部调用后缀，不证明整个任务实际运行、重试次数或任务完整。

## 正文：手机Voice与Emoji

db_PhoneMsg.shortmessage.Id→field2的流程三元→flowstate.StateKey→ShowTalk。本次发现文本已由既有Exporter提取，但inspect_message后处理遇Voice/Emoji类型会拒绝整条消息。

精确Voice类型保留同项TidTalk配置文本及姓名，不声称音频已核验；精确Emoji类型只接受正整数EmojiId，并在原事件位置显示“表情：图片内容尚未核验”。源标注可能是dnt、图片描述或缺失文本，不能当图像内容已确认。raw_text、source_item、EmojiId和缺失记录留JSON，最终render_result重复渲染也保护占位。未知类型、额外字段和畸形ID继续拒绝。

14条真实消息单独解析共264事件，含153个Voice、12个Emoji，不等于264条新台词。消息38005有31事件，表情是最后一项；任务119000001节点15发送该消息。消息内部顺序有流程依据，但发送动作不证明玩家读完时刻，所以外部消息仍单列。34001两条表情源Tid缺失继续记录，不宣称文字补齐。

## 回归与取证记录

新增测试涵盖精确实体归属与反例、预加载排除、触发材料不进主干、互斥同步后缀与异步/未知控制拒绝、14条手机消息及表情最终渲染。

整合时发现并修正两项真实结构问题：递归配置的Type可能是字典，节点识别不能用集合成员查询；Sequence内嵌Children需与扁平节点关系核对，而不是直接按完整字典判断不一致。手机渲染测试最初缺validation测试夹具，补齐夹具后复验。以上问题未靠放宽执行语义解决。

本地详细取证：work/round7_ownership.md、work/round7_ownership_new_candidates.json、work/round7_order.md、work/round7_content.md、work/round7_phone_evidence.json。最终批量统计与验证记录见下节。


## 最终验证结果

第七轮三路核查完成：全量269项通过（111.486秒），最终字段收紧后7项针对复验通过。批次20261117_124337_124773重导135对JSON/TXT，原2634个已解析区段的事件顺序保持；《如一叶小舟穿行于茫茫海洋》补入13事件，11条任务记录新增68次实体触发候选引用，6任务14条手机消息恢复264事件（含表情占位，非唯一新台词）。16任务27处阻塞逐处保持，3段30事件前缀仍blocked，严格通过仍2；资产不动。

- 最新完整产物：outputs/主线批量/20261117_124337_124773/覆盖阅读版；覆盖报告、剩余阻塞报告及产物核对.json同目录。
- TXT逐份与JSON渲染一致；旧可见文本保留，旧正文事件作为有序子序列保留，27个blocked区段对象及剩余阻塞报告与基线完全相同。
- 新增实体材料：11条任务记录、31个任务/流程组合、68次引用。相同任务的不同记录可重复归属，非全库唯一台词数。
- 新增手机材料：6任务14消息264事件。消息内部顺序保留，外部调用实际阅读时刻继续未知，不自动升为主干。
- 手机34001的2条表情源Tid缺失继续保留；覆盖报告缺失任务数1→2来自新增来源的缺失诊断。
- 四份代表样本（每份JSON/TXT）：114000026、690000001、192000006、119000001，位于outputs/第七轮基础语料核查。
- 最终收紧Selector槽字段时曾漏闭括号，针对测试及一次批量启动失败；修复后7项针对测试通过，再完整批量导出核对。失败批次不作为成果入口。

下一步继续寻找实体触发/手机显式打开的唯一锚点；无确定顺序就保留单列。当前仍是基础语料解析验证阶段，未宣称完整任务或游戏实际运行复现。
