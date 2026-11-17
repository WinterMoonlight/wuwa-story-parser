# 单任务语料格式

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
