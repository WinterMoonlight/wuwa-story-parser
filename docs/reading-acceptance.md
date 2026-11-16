# 阅读版验收与高频动作核查

## 本轮优先级

目标是更多任务形成有依据的有序正文，再完成一个小章节的连续阅读和知识库样例。追逐单条未知台词、复现所有游戏机制不再作为前置条件。仍不能把未知条件忽略后拼成所谓完整剧情。

## 分层验收

|层次|要求|不能代表什么|
|---|---|---|
|材料提取|正文有来源，候选/失败/未知分开|不代表任务顺序|
|有序草稿|回顾或依赖证明顺序，选项路径一致，缺口明确|不代表运行时或完整正文|
|阅读验收通过|逐任务及章节检查衔接、关键缺段、重复、选择、说话人及来源；重要缺口解决或明确限定用途|不等于游戏全分支模拟|
|检索与图谱样例|源文可引用，事实与推测分开，支线/失败不能当实际发生|不能仅凭召回到文本就宣称事实|

每任务JSON/TXT、女性漂泊者、原始文本及问号规则不变。没有有序正文的任务不计入阅读路线数。有序草稿若只有未知补充时序，必须显示限制；关键正文缺失不能悄悄算完整。新增 `batch_coverage.reading_acceptance`：本轮只赋予 ordered_draft 或 materials_only；`accepted=false`、`chapter_readthrough_verified=false` 表示尚未按新标准完成章节验收，不否定历史单任务核验。

## 动作证据与边界

本次扩展仅作用于 `allow_incomplete` 的任务回顾投影，严格模式保持原规则。保留全部动作参数与 `runtime_executed=false`、`indirect_trigger_effects_verified=false`。不能将清场描述为对剧情完全无影响：它会影响实体/玩法可见性，可能影响实际交互触发。本轮只确认所接受参数没有直接文本、条件或Flow调用载荷，不模拟世界状态，不据此调整任何回顾顺序或选择。

`reading_effects.py`核验：

- HideGroup外层必须有非空字符串GroupKey和HideConfig，可选布尔IsHidePasserByNpc。
- SpecifyEntity仅接收整数EntityIds列表。
- WorldMonsterAndMonsterTreasure仅接收整数HideRangeEntities列表。
- WorldEntityAndLevelPlay必须有HideRangeEntities，允许整数列表AppendEntities、AppendLevelPlays、ExcludeEntities、ExcludeLevelPlays。空列表可保留；布尔值不当整数。
- SetAudioState仅接受AudioConfig中的非空字符串Group、State。它是音频状态配置，不是已经提取的语音或字幕。
- ForceClean、SpecifyLevelPlay、SpecifyDataLayers及未知字段、字典形式列表成员仍拒绝，不据名称猜语义。

这解决了可选字段/列表变体造成的过严拒绝；没有让任意动作通过。流程内部的同名动作仍需独立验证，未统一放行。

当前135任务的全部任务动作清点中，449次HideGroup通过已核验形状（涉及87任务）：WorldEntityAndLevelPlay 267次、SpecifyEntity 121次、WorldMonsterAndMonsterTreasure 61次；148次SetAudioState涉及34任务。它们包含此前已支持的调用，不能将总数视为新增收益。

## 实际收益：0个新增，0个回退

基线20261117_011321_141069 → 新批次20261117_011716_907293。

- 135任务，11有序配置草稿、124仅候选；132有可读文字。严格2/85、补充0/50保持。
- 45任务的首个错误变化；其中4个仍是未支持HideGroup形状（包含错误说明更新），另外41个推进到后续错误。
- 新出现的首个阻塞包括ToggleMapMarkState、玩家操作限制、移动、气泡清除、无唯一回顾、引用不一致和外部解码等。
- 14任务仍包含未支持的HideGroup配置，不只是首错中的4个。
- 不能声称本轮新增了41或45个可读任务；实际新增为0。

## 后续按整任务剩余依赖选择

新增 `task_action_assessment` 保存全部可观察任务动作问题和接受的动作证据；检查范围不含所有外部解码和流程运行，不能把空issues当任务成功。

全任务动作问题涉及：SetPlayerOperationRestriction 51任务、EnableLevelPlay 39、ToggleMapMarkState 33、RestorePlayerCameraAdjustment 31、AdjustPlayerCamera 29、MoveWithSpline 25。数量不能相加，也不能直接作为收益排名。

建议下一案例是168000003《梦枢心相由心生》：本轮已无该检查范围内的任务/流程动作问题，但回顾额外引用3/6、3/7两个状态，因而仍拒绝路线。应查这两个状态是否由实体/玩法承接，确认归属与顺序，不能直接删除。它比继续横向增加几十种动作更接近“完成一个任务”的目标。

备选181000000《予以明日的花束》虽然只剩一种任务动作问题ToggleMapMarkState，但还有6个回顾独有引用；因此不能承诺支持该动作就新增有序任务。168850009《梦枢心相由心生·后日谈》动作检查也无问题，但有3个任务独有和4个回顾独有引用，需独立核对。

## 验证与复现

84项测试通过。135对文件的TXT均匹配渲染器、全部可读记录保留、分类计数一致；原11任务的events列表与基线完全相同。未执行新的章节连读验收。

```powershell
$env:PYTHONPATH='src'
python -m unittest discover -s tests -v
python run.py export-reading-batch
python -m wuwa_story.blockers outputs/主线批量/20261117_011321_141069/覆盖阅读版/覆盖报告.json outputs/主线批量/20261117_011716_907293/覆盖阅读版/覆盖报告.json outputs/阅读覆盖提升/阻塞前后对比.json
```

- [首错变化及全动作问题](../outputs/阅读覆盖提升/阻塞前后对比.md)
- [机器对比](../outputs/阅读覆盖提升/阻塞前后对比.json)
- [最新覆盖报告](../outputs/主线批量/20261117_011716_907293/覆盖阅读版/覆盖报告.md)
- [产物核对](../outputs/主线批量/20261117_011716_907293/覆盖阅读版/产物核对.json)

## 梦枢实体交互更新（2026-11-17）

[本轮证据与阅读检查](mengshu-entity-validation.md)：任务声明子实体及直属节点唤醒、实体单Flow交互可解释回顾额外引用，保存linked_entities与reading_context，不证明必经/实时顺序。168000003新增50事件草稿，字幕缺口保持。88测试，批次20261117_011935_649075有序12、候选123，135对核对通过，严格标准不变。下一步查M0391已有字幕配置并做本章衔接验证。

## 后日谈部分有序规则（2026-11-17）

新增 `partial_order`，介于有序配置草稿与仅候选材料之间，不计入 `selected_route`。`events` 仅包含已排列的回顾段落；`source.recap_reference_resolution.unplaced_task_flows` 保存未定位的正常流程归属，`external_content[].unplaced_flow` 保留其流程、选择和动作，`texts` 保留内部对白顺序。`validation.unplaced_flow_count` 记录段数。

批量 `order.selected_route_verified=false`、`recap_segment_order_verified=true`，缺口为 `normal_task_flows_unplaced`。正文开头与每个补充段明确说明顺序未补齐；不得将这些正常正文当作失败分支、任意交互或重复材料删除。`reading_acceptance.status=partial_order`、`accepted=false`；PreQuest只证明任务前置关系，不自动证明连续播放或章节验收通过。

当前135任务：12有序草稿、1部分有序、122候选；95测试通过。完整证据、产物和后续步骤见[后日谈核查](mengshu-epilogue-validation.md)。

## 回顾主干草稿（2026-11-17）

新增 `recap_draft` 状态。完整任务解析失败但存在唯一回顾列表时，`recap_backbone.segments` 按回顾条目顺序保存每段 `events`、`route.choices`、动作/身份来源和缺口；`entry_index` 保留原列表位置。顶层 `events` 仍只表示原已验证任务路线，可能为空；不要因此误认为回顾主干无正文。

逐段使用独立解析状态，段内失败不保留半条路线；`recap_gap` 位于原段落位置，缺口占位不计正文数。主干的覆盖记录使用 `order_scope=recap_segment_only`，即使列在confirmed_route分类，也不证明整个任务实际播放顺序；全任务 `selected_route_verified=false`、`reading_acceptance.accepted=false`。TXT先展示主干，再展示尚未归位/未选择材料，不再把主干选择抽离对白。

`duplicate_text_flows` 只记录非回顾来源与现有材料完整文字序列（含文本键、类型、说话人）一致的情况。`text_duplicate_of` 让TXT省略重复展示，JSON保留来源；不表示动作等价，不折叠回顾中重复出现的位置。当前批次60个回顾草稿；全文仍需检查缺段、未定位流程及运行时条件。详见[回顾主干验证](echoes-recap-validation.md)。
