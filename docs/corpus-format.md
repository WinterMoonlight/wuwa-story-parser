# 单任务语料格式

## 主线阅读投影

局部片段的`order_scope=condition_completion_to_async_call`表示节点的直接条件对白完成后调用另一段异步对白。分组保留两个原流程，`proof`保存并行祖先、条件、调用前动作及异步标记。该范围确认前段完成先于后段调用，跨节点时序继续由`mainline_placement_verified=false`标明。详见[远赴乘霄局部推进](research/departure-condition-followup.md)。

`sequence_dependency_review.flow_progression`保存所选流程的调用阶段、FinishActions前的直接流程完成条件、玩法启停以及共享状态写入来源。`waits_for_flow_completion`表明动作是否配置为同步等待，`enable_disable_pair_establishes_order=false`明确启停配对尚未证明跨节点顺序。该核查结果用于追溯顺序证据，TXT仍按已经确认的片段范围输出。见[风消雪霁推进关系核查](research/wind-task-progression.md)。

无整体主干的复杂任务可使用`condition_flow_review`记录直接Condition.PlayFlow与纯性别选择器的提取证据。`gender_selections`保存原选择器、经核对一致的内嵌副本路径及所选女性分支；`rejected_selectors`与`flow_failures`保存未确认原因。新正文进入`task_local_sequences`，保留`single_flow_without_task_order`范围。该字段只补充段内可读文字，全局顺序状态见原阅读报告。详见[条件流程恢复](research/task-condition-flow-recovery.md)。

任务同步前置对白保存在锚点段的`events`开头，`inserted_task_flows`记录源流程、动作、哈希与选择路线。其事件`task_placement.kind=task_sync_prefix`保存节点、调用阶段、动作索引及`before_state`；覆盖记录使用`order_scope=task_sync_prefix_order`。`relative_order_verified`限定于两次同步调用的相对顺序，实际运行状态仍单独记录。见[数据库同步前置对白](research/database-sync-prefix.md)。

缺少主干的任务新增可选字段`sequence_dependency_review`。其中`completion_requirements`表示完成条件的必要前提，`controller_dependencies`表示指定初始状态和控制器路径中的关联。`flow_before_unlock_verified`只描述同步流程在解锁调用之前，`target_node_order_verified=false`保留其他状态写入与整体调度的未知范围。该字段用于审核依赖，详见[眠龙庭跨分支核查](research/mianlong-sequence-dependencies.md)。

复杂任务也可生成`order_scope=single_flow_without_task_order`的独立片段，来源为节点的唯一直接PlayFlow调用。`proof`保存调用阶段、动作位置、原条件、祖先节点及Async，片段间顺序保持未确认。

`batch_coverage.levelplay_local_sequences`新增`order_scope=increasing_counter_invocations`。其`proof.thresholds`保存递增数值、门槛节点、原条件和调用；`positive_writes`保存同一玩法作用域的递增动作。`relative_invocation_order_verified=true`与`placement_verified=false`同时保留，`dialogue_completion_order_verified=false`表明异步结束顺序尚未确认。初始值及所有阈值实际到达情况保持未知。详见[复杂案例验证](research/hardest-mainline-case.md)。

默认导出的TXT使用`mainline_reading`。原有`events`、`recap_backbone`、`external_content`及`batch_coverage`继续保存完整已提取材料，阅读投影为追加字段。每个`blocks[].parts[]`保存`kind`、显示`text`与`source_pointers`，可回溯原事件及原始文本。

`status`支持`ordered_draft`、`ordered_draft_with_gaps`、`local_fragments_only`、`no_ordered_body`。`ordering_basis`记录回顾与任务依赖修正、所选配置路线或局部流程来源。`runtime_verified=false`继续明确运行时顺序未核验。`retained_text_events`统计显示事件，`omission_markers`统计短说明；均不代表全任务完整率。

TXT省略未定位附录和复杂小游戏细节，原位保留演出、交互和缺失流程的简短说明。`refresh-reading`对旧JSON临时生成投影以更新TXT，保持JSON文件字节不变。下文附录相关描述记录原始材料的组织方式，当前TXT展示以本节为准。详见[本轮验证](research/mainline-reading-projection.md)。

无回顾的简单Sequence任务可以生成`task_local_sequences`独立流程分段，使用`order_scope=single_flow_without_task_order`。`sequence_execution_review`保存Sequence子节点分组、副本进入与完成关系、可见状态候选及未解析流程。`display_order_is_execution_order=false`与`whole_task_order_verified=false`明确保留，分段列表顺序仅供展示。原有跨流程局部调用片段按原order_scope读取。详见[时序之主节点核查](research/master-of-time-sequence.md)。

`batch_coverage.order.source_priority`依次为`task_call_dependencies`、`entity_or_gameplay_trigger_dependencies`、`recap_fallback`。`recap_backbone.task_finish_supplements`记录本次恢复的直接任务后继调用，段落中的`inserted_task_flows`保留流程、源动作与选择，正文事件使用`order_scope=task_finish_call_order`。异步结束与外部回调的未核验标志继续保留。详见[任务调用与补充片段](research/task-finish-supplement.md)。

`recap_backbone.dependency_order_corrections`保存依据唯一任务完成调用修正回顾顺序的记录。`original_segment_keys`与`ordered_segment_keys`分别保留原顺序和本版阅读顺序，源条目的`entry_index`仍对应原始回顾。异步目标只确认前段完成早于后段调用，`completion_order_verified=false`保留其他结束时序未核验。当前修正通过`recap_dependency_corrected`记录，原始依赖比较继续保存在`batch_coverage.order.dependencies`。详见[荣耀暗面顺序核查](research/glory-dependency-order.md)。

通过唯一回顾提示补入的任务段使用`order_origin=task_finish_tip`，如果相邻回顾交互以该任务节点完成为前提，则使用`task_finish_before_interaction`并排在该交互之前。`source_entry`保存原始提示，`placement_proof.tip_entry_index`保存提示位置，`entry_index`保存实际插入锚点。原始`order_source.entries`保持，`tip_flow_insertions`保存所有放置依据。`source_counts.task_tip_inserted_segments/events`单独统计新增正文段和事件，`recap_parsed_segments`只计原始回顾段。详见[提示与完成条件核查](research/tip-finish-flow-validation.md)。

`batch_coverage.entity_trigger_timing`保存地图触发对白的任务节点生命周期核查。节点的`DungeonId`按副本配置映射为地图，匹配同地图实体，另外保留同编号在其他地图的调用。`common_task_region`是共同任务祖先及其阶段名，TXT据此添加阶段标签。`matching_map_lifecycle`保存原始动作、条件和回顾索引，`trigger_range`保存触发范围。`placement_verified=false`与`runtime_verified=false`表示仍未定位实际播放，所有对白继续在附录保留。此字段为可选追加字段，旧JSON仍可按原规则渲染。详见[实体触发核查](research/avinuolin-trigger-review.md)。

阅读版按来源排除操作标签。覆盖记录中`reading_exclusion_reason`取值为`task_objective_label`、`quest_occupation_notice`或`system_option_label`时，该条仍保留在JSON中，TXT省略其显示。`source_counts.reading_excluded_labels`给出排除数量。过滤基于TidTip、OccupationConfig及明确的system_option类型，正文与剧情选择按原规则保留。旧JSON可从原指针和source_path获得相同的阅读结果。见[标签与对白核查](research/reading-labels-validation.md)。

无回顾且尚无已解析整任务路线时，顶层`task_local_sequences`可保存同节点连续同步调用的局部有序片段。其字段与`recap_backbone.task_local_sequences`相同，`order_scope=adjacent_synchronous_finish_calls`表示连续同步完成动作的相对顺序。片段保留媒体调用占位和所选分支，`mainline_placement_verified=false`表示任务内整体位置仍需核查。TXT将片段集中展示，覆盖记录指向`/task_local_sequences/…`，所选文字从零散清单中去重。详见[连续调用验证](research/adjacent-task-order-validation.md)。

连续调用段支持三个及更多同步调用，`proof.action_indices`保存原数组位置，`run_dependencies`逐条保存邻接边。其他动作将连续段隔开。祖先为ParallelSelect时保留`parallel_ancestors`和`cross_branch_order_verified=false`，TXT显示简短条件说明，任务内整体位置仍待确认。详见[并行上下文规则](research/parallel-task-order-validation.md)。

## 现有文本顺序范围

阅读版新增`batch_coverage.text_order_review`，分别记录条件路线已排序、媒体内部内容后置、缺失流程定义及局部顺序待确认。范围为回顾片段，其他附录的未定位内容仍保留在原coverage.gaps。`whole_task_text_order_verified=false`，原任务级状态继续按既有规则计算。

条件路线证据在`recap_backbone.segments[].unverified_content`中以`kind=conditional_text_route`保存。入口前提、实体作用域、可满足性见证、符号副作用及原选项索引完整保留，实际运行状态与跨段变量传播均未确认。正文覆盖记录使用`order_scope=conditional_recap_segment`。

界面返回路线证据使用`kind=panel_return_text_route`，记录`conditional_on_panel_return=true`、原控制边界和局部文本顺序。`runtime_return_verified`与`panel_display_timing_verified`均为false，正文覆盖范围为`panel_return_recap_segment`。原位`ui_reference`保存界面调用，`content_deferred=true`的说明不计正文数量。相关规则见[界面返回文本核查](research/panel-return-text-validation.md)。

单线QTE阅读投影使用`kind=configured_qte_text_order`证据，保存完整声明顺序、普通文本节点和QTE编号。`runtime_return_verified`、`qte_result_selected`、`all_runtime_outcomes_verified`均为false。`qte_reference`事件保留原位控制节点，其`content_deferred=true`，不计正文数。正文记录的范围为`configured_qte_recap_segment`，缺失普通文字继续记录在missing_text_ids。见[单线QTE规则](research/qte-configured-text-order.md)。

`recap_backbone.task_local_sequences`保存同一节点条件流程到同步完成调用的局部有序片段。`local_order_verified=true`与`mainline_placement_verified=false`同时保留，文本记录范围为`same_node_condition_to_finish`。JSON保留中间场景动作及回调内容未核验标记，TXT在附录中连续展示已确认顺序的两段。对应所选静态文本从散列显示中去重，未选分支仍保留。见[局部调用顺序](research/task-local-sequence-validation.md)。

独立演出后置证据使用`kind=deferred_sequence_content`，原位事件为`media_reference`且`content_deferred=true`。覆盖记录将它计为占位，正文数量不增加。原始帧动作保留，帧时序和回调未执行。规则范围见[验证报告](research/known-text-order-validation.md)。

## 当前输出

`outputs/任务样本/<任务ID>_<任务名>.json` 与同名 `.txt`。JSON 是结构化主数据，TXT 从相同事件列表生成。

主要字段：

| 字段 | 内容 |
|---|---|
| schema_version | 单流程为 1；多场景回顾路线为 2 |
| quest_id / title | 任务标识与显示标题 |
| source | 原始任务定义、任务节点、流程键、流程 BLOB 的 SHA-256 |
| route | 路线策略、每次选择和全部选项、性别变量策略、游戏操作假设 |
| events | 选中路径上的有序对白和选择 |
| action_trace | 实际处理的动作配置 |
| validation | 缺失引用、未解身份、支持范围与限制 |

对白事件保存 text_id、state_key、talk_id、speaker_id、display_name、raw_text 和 source_item。身份关联使用 resolved_speaker_id、resolved_name、identity_status 和 evidence；后续图谱的 canonical_character_id 尚未实现。

`display_name_only` 仅表示有显示名称，不是实际人物身份已核验；`config_actor_continuity` 表示同一演员槽位的称呼连续关系；`unresolved` 保留未知。

## 路线规则

首次选择第一个无条件选项；同一提问菜单再次出现时选择尚未选过的选项，直到退出。JSON 中保留未选择的选项文字和动作，但不把未选分支对白加入 events。遇到未知条件、无退出循环、缺失跳转目标或未支持动作，命令失败，避免静默生成伪完整语料。

任务样本假设玩家已完成 ReachArea 条件，不模拟真实玩家状态。阅读正文统一选 Female 分支，{PlayerName} 替换为“漂泊者”，{TA} 替换为“她”；原始模板保存在 raw_text。

当前 `complete_for_supported_task_shape` 仅表示受支持任务形态中的选中流程路线已处理且无缺失文本；不是全游戏、全分支或环境对白覆盖证明。

## 后续格式演进

当前已有跨流程事件序号、场景切片、条件假设和批次源库哈希/失败清单。后续应补齐统一数据快照 manifest、完整源库引用、解析器版本与文本分库来源。语料变更须提升 schema_version，并提供迁移说明。

阅读摘要、RAG 条目和知识图谱分别引用 task_id / state_key / text_id。不要以 TXT 的行号作为长期证据主键，也不要用摘要替代原文。

## schema_version 2：多场景任务

保留原有事件字段；新增每条事件的 `sequence`（从 1 开始）。`source.flow_state` / `flow_state_sha256` 改为 `source.scenes` 数组，每个场景含状态键、BLOB 哈希、对应任务节点 ID、事件切片 `[event_start, event_end_exclusive)`（从 0 开始）。消费者应根据 schema_version 分支读取。

`source.order_source` 保存 PlotHandBook 表、任务 ID、BLOB 哈希和原始有序条目；空 Flow 的提示条目保留为证据，不当作对白执行。`action_trace` 的每个动作新增 state_key。世界表现动作只记录，不模拟实体状态；前置与交互视为满足。

本版完整性仅指回顾顺序覆盖全部任务显式流程且选中路线无缺失文本，不能证明游戏运行时节点顺序、环境对白或未选分支覆盖。`unresolved_anonymous_lines` 是旧字段名，实际计数包含未知说话人和无 WhoId 叙述，不能直接当作问号台词数量。

## 阅读文本渲染约定

rendering.version=1：事件的 text 是阅读正文，raw_text 保留数据库原文；TXT 使用 text。选项列表同样保存 text / raw_text。display_name 与 resolved_name 经同样替换，原值保存在 raw_display_name / raw_resolved_name。标题原值保存在 raw_title。source、source_item 和动作证据不改写。

固定 player_name=漂泊者、gender=female。只解析明确的 PlayerName、TA 和 Male/Female 模板，不把普通句子中的“他”一律替换；例如 {Male=她;Female=他} 的女性分支仍是“他”。未知模板保留。此次为 schema 1/2 增加阅读字段，原 raw_text 含义不变。

## 复杂回顾任务的新增证据

source.task_audit 保存父子结构校验、流程引用归属、任务动作处理方式和玩法条件假设；runtime_graph_executed 固定为 false，不将回顾投影误称为任务引擎模拟。validation.talk_groups 记录每组对白的全部 ID、实际访问序列、未选 ID，以及全部分支的文本与跳转引用核验。

事件新增 talk_group；选择新增 visit。choice_key 在同一场景第二组及以后对白中追加 group 后缀，避免不同 ShowTalk 的同号选项碰撞。画面文字新增 kind=narration，保留 source_action。循环菜单策略名为 first_untried_option_on_menu_revisit；普通互斥分支仍只取一条。原字段兼容保留。

## 待核验外部内容

显式 --allow-incomplete 模式新增 external_content 附录（节点、动作索引、来源哈希、前序动作和失败分支标识）；PlayMovie 未读资产生成 kind=media_reference 事件。附录文本同样有 raw_text/text。存在外部缺口时 validation.status=needs_review、complete_for_supported_task_shape=false，使用 coverage_version=2，分别写 confirmed_missing_text_ids、known_text_references_complete 与 unverified_content；TXT 显著标注草稿，独立保存到待核验任务目录。此模式不改变严格批量成功标准。

media_reference 表示媒体调用，不表示确认缺失台词。旧 external_gaps 字段已由结构化 unverified_content 替代，消费者应按 coverage_version 区分。若本地提供匹配的 StreamMediaSource 属性 JSON，则附 media_source_evidence（文件哈希、资源地址）；不会访问该地址或由此推断字幕有无。

## 待核验导出的界面证据

`external_content` 的 `owner` 保存配置角色归属，`ancestry` 保存当前节点至根的条件上下文，`timing` 保存前序异步调用索引和后续动作。`completion_order_verified=false`，不把配置排列冒充播放完成顺序。

`task_ui_texts` 独立于对白 events：每项记录 node_id、source_path、source_config、context、visibility_flags、text_id、raw_text、text、missing、display_verified。当前支持节点 TidTip、UIConfig 与 OccupationConfig 中的 Tid 字段。字段不存在、空字符串、隐藏标记和缺失文本键含义不同；本附录不等于完整 UI 截图或运行时展示序列。缺失引用纳入 confirmed_missing_text_ids；空字符串不计为缺失。动态计数占位符原样保留。TXT 对应输出独立附录。

## 接受任务与引导引用

待核验模式支持 `quest_control` 事件保存 AccpetCurrentQuest 的调用位置，原始动作保留，不代表执行了接取或回调。`unverified_content.kind=quest_acceptance` 声明边界。`GuideTrigger` 在 external_content 保存 guide_id、conditions、节点及局部时序，状态 guide_content_unverified；CompleteGuide 仍为完成标记。`source.scenes[].equivalent_action_fields` 保存内容完全相同的候选动作数组字段号，数组内容冲突仍拒绝解析。

### GuideTrigger配置正文

external_content中的guide保存group_source、step_ids、steps、trigger_conditions与limitations。步骤含platform_mask_raw、step_source/content_source，教程另含有序pages。源证据含表/行、SHA-256及bin_data_base64；并未把未知二进制字段解释为确定语义。texts统一保存text_id/raw_text/text/missing及来源字段、step_id和用途。状态guide_config_read_display_unverified表示已读取配置正文、未确认实际显示；缺失引用仍进入统一完整性统计。多平台候选不合并进对白events，按键占位符保留。

### 邮件、章节与传送引用

external_content新增SendNpcMail的quest_id/mail_id/read_condition_nodes，保留源行present_fields、bin_data_base64与sha256。mail_body_unavailable_in_row表示当前源行无法关联正文，不等同于缺失某个已知文本键；它进入unverified_content。PromptQuestChapterUI与TeleportDungeon保留调用参数且标记未核验，不执行运行时动作。支持节点Actions阶段，和EnterActions/FinishActions分开记录。头像显示动作不会赋予说话人身份。

### 手机独立流程

external_content.phone保存message_id、state_key、contacts、events、route、talk_groups和action_trace。手机events有自己的流程作用域，不混入正文events；保留raw_text及统一女性/漂泊者渲染。phone.missing_text_ids合入任务缺失统计。源表、字段与哈希及message_bin_data_base64支持溯源。read_time_verified=false明确不承诺阅读时间；发送位置由外部记录的quest_id/node_id/phase确定。SwitchSubLevels记录加载/卸载路径；祖先链包含DungeonId和DisableOnline。

### Reigns与变量证据

external_content.gameplay保存state_key/source_actions/endings/initial_properties/cards/route_simulated=false；texts为带源路径的全分支候选清单，卡牌原文不一定是文本键（text_id=null）。CardId和CardIds并存时不猜优先级，缺失卡牌独立标reference_unresolved。SetVar保存variable/assigned_value/readers，状态variable_assignment_not_executed；祖先链保留ExitCondition。不执行存档状态或以读取表行顺序冒充路线。

### Reigns计算依据核查

mechanics_audit包含buff_ids、buff_effects_resolved、settlement_calls、ending_probes及route_attempt。ending_probes仅比较初始属性，分别列出假设all/any结果，未指定ConditionType枚举语义。blocked_missing_semantics表示未能开始可信数值求解，successful_route=null，不是已搜索并证明无解。卡牌收集包含直接ReignsCallCard；本地化键与字段名关联，legacy_inline_text保存旧内嵌文案。

## 当前TXT阅读版规则（优先于上文旧版说明）

TXT仅呈现可读剧情、选择、小游戏正文及简短缺失/未核验说明；节点、变量、条件、来源路径、统计诊断均保留在JSON。小游戏不同分支仍明确标为候选回应，不伪装成成功路线；重复小游戏调用按reigns_id只展示一次。JSON的所有调用、原文及证据不做去重或删除。普通任务界面配置仅留JSON；手机/引导等补充可读正文保留。

### 已有产物刷新

`refresh-reading`以已有任务JSON为依据，只更新阅读TXT。既有选择、证据和完整性状态不变；非任务JSON跳过。历史目录不改名，生成统一阅读索引和JSON哈希核查清单。这不是用新解析器重新还原历史任务。
# 批量覆盖阅读版补充

新增的 `batch_coverage` 字段、四类内容和原始指针规则见[覆盖阅读版](coverage-reading.md)。`confirmed_route` 仅表示所选配置路线；`inventory_only` 任务不能作为已排序的完整剧情直接用于知识库。入库时必须保留类别及证据，候选、失败和未核验材料不能混写成既定事实。


## 手机解码纠正与最新批次

见[手机36009核查](research/phone36009-decoding.md)。字段1为联系人ID，字段9非联系人；无台词Option容器不再误报缺文。PhoneMessage拆分系统提示与图片附件，图片引用不等于图像内容已提取。最新批次20261117_010808_314910，72测试通过，11配置路线；missing_text任务降至7。旧时间戳产物是历史状态。

## 七任务文本引用核查更新（2026-11-17）

以[缺失引用核查](research/missing-text-validation.md)为当前接手点。NoTextItem/QTE的TidTalk按控制引用处理，JSON保留non_dialogue_controls及原始文本和动作；TXT不输出内部演出占位为台词。QTE成功/失败不按普通选择执行，批量单列qte_runtime_unverified。普通Talk的缺失不静默过滤。76项测试通过；最新批次20261117_011055_476513，135对文件核对通过，missing_text任务剩《灼我以烈阳》1个。资源缺失与失效回顾引用尚不可区分，下一步查4/5与4/1的归属/版本证据。

## 灼我以烈阳引用核查补充（2026-11-17）

见[本轮核查](research/scorching-sun-reference-validation.md)：缺失键有共用语音候选，但无字幕替代证据，保留missing_text。JSON新增missing_text_diagnostics，包含任务/回顾归属与语音候选，replacement_applied为false；候选不进入阅读正文。79项测试通过，批次20261117_011321_141069核对135对文件，统计不变。该条目待新证据，后续可推进QTE路线验证。

## 阅读覆盖与验收更新（2026-11-17）

以[阅读验收标准](reading-acceptance.md)为最新规划：JSON新增batch_coverage.reading_acceptance与task_action_assessment，有序草稿不自动验收通过。HideGroup/SetAudioState仅在待核验任务回顾投影中接受已验证形状，保留运行时影响未知，严格规则不变。84项测试；批次20261117_011716_907293，新增有序0、回退0，135对产物核对通过。下一步核对168000003回顾额外3/6、3/7的来源与顺序，不再仅按单动作频率推进。

## 梦枢实体交互更新（2026-11-17）

[本轮证据与阅读检查](research/mengshu-entity-validation.md)：任务声明子实体及直属节点唤醒、实体单Flow交互可解释回顾额外引用，保存linked_entities与reading_context，不证明必经/实时顺序。168000003新增50事件草稿，字幕缺口保持。88测试，批次20261117_011935_649075有序12、候选123，135对核对通过，严格标准不变。下一步查M0391已有字幕配置并做本章衔接验证。

## 配置字幕更新（2026-11-17）

见[M0391字幕核查](research/m0391-caption-validation.md)。媒体事件新增media.captions与caption_order_evidence，字段4关联正文，四组候选数值一致排序仅作为相对顺序推断；无语言/单位/角色猜测。M0391已补10条，C0027已补18条，替代旧“字幕尚未解码”的进度描述。92测试、批次20261117_012201_323353核对135对产物；有序12、候选123不变。阅读检查仍保留实际播放及额外画面文字边界。

## 后日谈部分有序规则（2026-11-17）

新增 `partial_order`，介于有序配置草稿与仅候选材料之间，不计入 `selected_route`。`events` 仅包含已排列的回顾段落；`source.recap_reference_resolution.unplaced_task_flows` 保存未定位的正常流程归属，`external_content[].unplaced_flow` 保留其流程、选择和动作，`texts` 保留内部对白顺序。`validation.unplaced_flow_count` 记录段数。

批量 `order.selected_route_verified=false`、`recap_segment_order_verified=true`，缺口为 `normal_task_flows_unplaced`。正文开头与每个补充段明确说明顺序未补齐；不得将这些正常正文当作失败分支、任意交互或重复材料删除。`reading_acceptance.status=partial_order`、`accepted=false`；PreQuest只证明任务前置关系，不自动证明连续播放或章节验收通过。

当前135任务：12有序草稿、1部分有序、122候选；95测试通过。完整证据、产物和后续步骤见[后日谈核查](research/mengshu-epilogue-validation.md)。

## 批量静态记录的姓名和类型（2026-11-17）

`batch_coverage.records` 中有 `origin` 的静态记录增加 `kind`：dialogue、choice、screen_text、qte_result、system_option、unknown_option。`category` 仍表示路线/候选/失败/待核验范围，不能用kind代替可信度。

普通对白的 `who_id/speaker_id` 只来自当前TidTalk对象；`source_who_id` 保存当前原始值，`inherited_who_id` 仅保存递归祖先信息供审计，不能用于归属。`name_source` 保存配置姓名读取依据，`identity_status` 区分display_name_only和unresolved；不从静态顺序推测演员身份变化。未确定显示问号。

普通选项 `kind=choice`、`display_name=漂泊者`、`who_id=null`、`selected=false`，只代表可选文字存在；TXT显示漂泊者【选择】。居中文字无人物归属；QTE结果和系统选项不等于已发生的玩家对白。详见[核查报告](research/batch-speaker-validation.md)。

## 回顾主干草稿（2026-11-17）

新增 `recap_draft` 状态。完整任务解析失败但存在唯一回顾列表时，`recap_backbone.segments` 按回顾条目顺序保存每段 `events`、`route.choices`、动作/身份来源和缺口；`entry_index` 保留原列表位置。顶层 `events` 仍只表示原已验证任务路线，可能为空；不要因此误认为回顾主干无正文。

逐段使用独立解析状态，段内失败不保留半条路线；`recap_gap` 位于原段落位置，缺口占位不计正文数。主干的覆盖记录使用 `order_scope=recap_segment_only`，即使列在confirmed_route分类，也不证明整个任务实际播放顺序；全任务 `selected_route_verified=false`、`reading_acceptance.accepted=false`。TXT先展示主干，再展示尚未归位/未选择材料，不再把主干选择抽离对白。

`duplicate_text_flows` 只记录非回顾来源与现有材料完整文字序列（含文本键、类型、说话人）一致的情况。`text_duplicate_of` 让TXT省略重复展示，JSON保留来源；不表示动作等价，不折叠回顾中重复出现的位置。当前批次60个回顾草稿；全文仍需检查缺段、未定位流程及运行时条件。详见[回顾主干验证](research/echoes-recap-validation.md)。

## 七缺口复核更新（2026-11-17）

最新[复核报告](research/echoes-seven-gaps-validation.md)：目标任务90/92段、986事件；剩余2段是缺失流程。PlaySequenceData扩展了镜头重置和受限实体状态回调形状，仍输出unparsed_content，保留asset_content_decoded=false、frame_events_executed=false和源参数。5/16图标动作支持不改变姓名或分支；这些修改不构成演出字幕完整性证明。106测试、135对最终批量核对通过。

## 演出来源状态（2026-11-17）

PlaySequenceData的source_resolution记录完整asset_path、精确videodata匹配和properties_status；属性存在也不等于已解码。视频sound_sources记录音频事件及哈希，text_decoded=false，不能当字幕。TXT区分演出与信息面板；无字幕行不证明没有对白。详见[来源核查](research/echoes-performance-sources.md)。

## InformationView（2026-11-17核验）

OpenSystemBoard.InformationView的BoardId精确关联db_infodisplay.infodisplay.Id；BinData字段3/4分别为标题和正文文本键。information_board事件保存两条texts、purpose、source_field、text_id、raw_text及源行哈希，组合显示标题和正文。任务级调用保持外部材料位置；面板中的引用对白不自动归属人物。见[资料核查](research/echoes-information-view.md)。

## 任务额外流程证据

recap_backbone.task_only_review保存额外流程源节点、祖先、性别/异步证据和placement_verified。仅受限同步转场可用task_placement标记插入事件；空文本只留text_evidence，visible_event_count=0，不生成缺失或空白台词。来源分类不能当成确定的实际执行路线。详见[额外流程规则](research/echoes-task-extras.md)。
## 未解决调用附近的局部正文

回顾段落仍为blocked时，可以包含prefix_event_count和control_boundary，明确哪些文字位于未知控制之前。条件菜单的可用性不会由默认变量值推断。

Enrollment局部后续保存在recap_backbone.segments[].local_fragments，其order_scope为configuration_after_unresolved_ui，runtime_return_verified及whole_segment_complete均为false。这些事件在覆盖报告归unverified，TXT在缺口之后另起标题显示，不计完整区段。原始source_actions和source_item保留。

## 无条件备选路线

回顾段route.policy为first_fully_parsed_unconditional_alternative时，表示初选路径在直接SetVar处中断，解析器采用同一菜单完整可解析的无条件跳转选项。unverified_content中的implicit_choice_retry保存原始错误、控制边界、前缀和新旧选择。用户显式指定的choices始终优先。

剩余阻塞报告的unresolved_original_choices记录原选项仍未实现的控制，不能仅凭所选路线不再阻塞推断全部分支已支持。


## 资源引用与阅读标签清理（2026-11-17）

TXT统一去除颜色、术语链接、加粗、斜体等尖括号标签，保留包裹的文字。显式br标签转换为换行，ano注音沿用正文加注音说明的形式。普通比较符号和动态占位符继续保留。该转换只作用于阅读输出，JSON中的raw_text和source_item保留原始依据。

PhoneMessage中的规范Emoji与Attachment引用以图片消息处理，保留消息位置、资源编号与未核验占位。对应TidTalk没有文字时不再计作正文缺失，语音、普通文字与未知参数形状继续使用正文查找。当前《我们选择天空》的三个缺失文字误报已消除。

资源核查仍有10个精确流程键未找到定义，对应7份任务记录、12个回顾位置。用户确认的阿维纽林4/11过程动画已附人工反馈，其源定义缺失事实保留。《灼我以烈阳》仍有1个正文键待确认。

逐处上下文和复现方法见[资源引用核查](research/resource-reference-cleanup.md)。


## 阅读版动态模板显示

TXT使用教学参数数组中的动作名称展开数字占位符，未知输入保留【操作键】等可读提示。当前任务内所选全局字符串赋值可提供后续片段的名称显示，缺少记录时保留描述性标记。原始模板、选项、赋值审计和输入参数留在JSON。该显示处理不替代条件求值和运行时变量状态。

## 同节点多阶段调用

无整体主干的任务可以将同节点的多个唯一直接PlayFlow分别提取到`task_local_sequences`。`proof.phase`和`action_index`保留调用位置，`multiple_direct_calls`表示需区分多个调用。它们仍是独立片段，不能直接按输出列表推断整任务顺序。

`sequence_dependency_review.flow_progression.phase_relations`记录同次执行中EnterActions到FinishActions的调用阶段关系；异步入口的`flow_completion_before_followup_verified=false`。TXT注明“进入步骤时调用”或“完成步骤时调用”，不把阶段先后扩大为对白完成顺序。规则与例子见[远赴乘霄阶段核查](research/departure-phase-progression.md)。

## 局部对白之间的InformationView

`task_local_sequences`的`order_scope=condition_completion_via_information_board`表示条件对白完成后，按完成动作数组先调用资料面板，再调用后续对白。`segments`保留原流程；`intermediate_content`另存资料事件、原动作下标及插入位置，不伪造FlowState。

资料来自唯一BoardId和明确语言键。原始`external_content`继续保留，对应重复统计记录使用`counted_elsewhere`和`text_duplicate_of`标记；TXT在局部两段之间显示一次正文。面板关闭时机、与其他任务节点的先后仍未验证。详见[心愿纸条调用顺序](research/wish-note-call-order.md)。

## 关联回顾区段

`linked_recap_sections`保存由其他回顾条目补充的正常任务流程。仅当条目有明确前置与任务引用、精确任务提示、完整且唯一的流程归属，并通过占位节点及调用依赖检查时接入。

原`events`、`source`、`external_content`保留；阅读版使用关联区段的`segments[].events`与`route.choices`，原外部文字统计以来源指针标注重复。`validation.reading_unplaced_flow_count`记录阅读版剩余缺口，原`unplaced_flow_count`保留底层解析结果，二者口径不同。

该输出的`ordering_basis=linked_recap_sections`表示回顾区段关系已核查，实机节点执行及可选交互必经性仍未验证。详见[后日谈恢复证据](research/epilogue-linked-recap.md)。
