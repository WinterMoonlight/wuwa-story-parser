# 阅读版验收与高频动作核查

## 本轮优先级

2026-11-18调整后，主要输入与验证依据回归现有ConfigDB。验收围绕数据库中已有文字的提取、归属、选择衔接及播放顺序展开。客户端脚本研究作为辅助资料，缺少脚本的记录仍可继续进行数据库解析与导出。

当前交付为解析器与基础语料。用户明确优先恢复可连续阅读的主线剧情；《荣耀暗面》等复杂活动内部的小分支、小玩法可以省略，此原则同样适用于其他任务。

每个任务采用一条可解析的正常选择路线，主干保留原始对白、起因、主要经过、必要结果和后续承接。复杂数值机制、重复操作、失败尝试和可选闲聊按主线需要取舍。已有明确活动过程时可用简短过渡说明衔接，结果根据文字或配置证据表述。

引用入口与条件变量的改进优先服务主线衔接和关键对白。技术记录与原始材料继续保存在JSON，阅读版按主干用途组织。视频内部内容和未取得资源沿用后置安排。

## 当前范围的验收标准

默认TXT现已实施主线精简投影。`主线阅读报告`描述TXT的实际呈现范围，原`覆盖报告`保留全部提取材料的统计。主干草稿继续需要阅读核验，`local_fragments_only`与`no_ordered_body`仍属于整体顺序待恢复的任务。详见[实施与验证](research/mainline-reading-projection.md)。

1. 能按顺序阅读任务起因、主要过程、关键对白和必要结果，前后任务衔接有依据。
2. 每处选择采用一条可解析的正常路线，选择与后续对白相接，重复调用有来源记录。
3. 复杂活动保留推进主线所必需的文字与结果，可略过内部数值、可选分支、失败尝试和重复操作。
4. 过渡说明明确标注省略活动过程；尚未核实的结果保留短说明。
5. 女漂泊者、统一玩家名、配置说话人和来源追溯要求继续适用。
6. JSON保存源文本、条件、动作及省略依据；TXT以主线连续阅读为验收重点。

每轮修复需指出具体解决的引用、分支、重复或顺序问题，并核对其他任务的原有正文。局部有序片段继续记录自身范围，整体顺序缺证时保留对应状态。当前后置的资源空缺保存来源和简短说明。

阅读验收逐项检查所选主干及活动前后的承接。历史完整性统计、全部分支覆盖统计继续用作技术参考。下方保留更广范围的历史验收记录，当前交付优先按以上标准执行。

## 当前验收规则

每次验收绑定数据库快照、任务ID、产物哈希与审查结论。逐任务记录正文覆盖、重复、分支一致、身份处理、阅读顺序及剩余限制。连续阅读另记录相邻任务关联依据、首尾事件与人物地点衔接。

|结论|适用条件|
|---|---|
|可连续阅读|主干关键文本已覆盖，顺序和选择可追溯，附录归属清楚，首尾衔接已检查|
|带明确缺口可阅读|主要文本可读，存在可定位且已说明的未核验内容，使用范围需列明|
|仍是材料|关键正文或必要顺序尚未确定，现有材料不足以支持完整阅读|

`accepted=true`只用于“可连续阅读”的任务级人工审查记录。`chapter_readthrough_verified`需要覆盖指定章节全部任务；三任务样本使用独立的连续阅读记录。缺口结论与证据应随JSON交付，TXT提供简短说明。历史自动生成的`accepted=false`表示未录入审查，需查看本轮独立验收记录。

## 分层验收

|层次|要求|不能代表什么|
|---|---|---|
|材料提取|正文有来源，候选/失败/未知分开|不代表任务顺序|
|有序草稿|回顾或依赖证明顺序，选项路径一致，缺口明确|不代表运行时或完整正文|
|阅读验收通过|逐任务及章节检查衔接、关键缺段、重复、选择、说话人及来源；重要缺口解决或明确限定用途|不等于游戏全分支模拟|

以下为早期自动覆盖分类的设计记录。批量自动输出使用 `batch_coverage.reading_acceptance` 记录草稿状态，人工审查结果由 `docs/reviews/` 中带源哈希的记录及审查版JSON/TXT交付。当前标准以上方“当前验收规则”为准。

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

[本轮证据与阅读检查](research/mengshu-entity-validation.md)：任务声明子实体及直属节点唤醒、实体单Flow交互可解释回顾额外引用，保存linked_entities与reading_context，不证明必经/实时顺序。168000003新增50事件草稿，字幕缺口保持。88测试，批次20261117_011935_649075有序12、候选123，135对核对通过，严格标准不变。下一步查M0391已有字幕配置并做本章衔接验证。

## 后日谈部分有序规则（2026-11-17）

新增 `partial_order`，介于有序配置草稿与仅候选材料之间，不计入 `selected_route`。`events` 仅包含已排列的回顾段落；`source.recap_reference_resolution.unplaced_task_flows` 保存未定位的正常流程归属，`external_content[].unplaced_flow` 保留其流程、选择和动作，`texts` 保留内部对白顺序。`validation.unplaced_flow_count` 记录段数。

批量 `order.selected_route_verified=false`、`recap_segment_order_verified=true`，缺口为 `normal_task_flows_unplaced`。正文开头与每个补充段明确说明顺序未补齐；不得将这些正常正文当作失败分支、任意交互或重复材料删除。`reading_acceptance.status=partial_order`、`accepted=false`；PreQuest只证明任务前置关系，不自动证明连续播放或章节验收通过。

当前135任务：12有序草稿、1部分有序、122候选；95测试通过。完整证据、产物和后续步骤见[后日谈核查](research/mengshu-epilogue-validation.md)。

## 回顾主干草稿（2026-11-17）

新增 `recap_draft` 状态。完整任务解析失败但存在唯一回顾列表时，`recap_backbone.segments` 按回顾条目顺序保存每段 `events`、`route.choices`、动作/身份来源和缺口；`entry_index` 保留原列表位置。顶层 `events` 仍只表示原已验证任务路线，可能为空；不要因此误认为回顾主干无正文。

逐段使用独立解析状态，段内失败不保留半条路线；`recap_gap` 位于原段落位置，缺口占位不计正文数。主干的覆盖记录使用 `order_scope=recap_segment_only`，即使列在confirmed_route分类，也不证明整个任务实际播放顺序；全任务 `selected_route_verified=false`、`reading_acceptance.accepted=false`。TXT先展示主干，再展示尚未归位/未选择材料，不再把主干选择抽离对白。

`duplicate_text_flows` 只记录非回顾来源与现有材料完整文字序列（含文本键、类型、说话人）一致的情况。`text_duplicate_of` 让TXT省略重复展示，JSON保留来源；不表示动作等价，不折叠回顾中重复出现的位置。当前批次60个回顾草稿；全文仍需检查缺段、未定位流程及运行时条件。详见[回顾主干验证](research/echoes-recap-validation.md)。
