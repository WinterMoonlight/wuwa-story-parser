# 开发与换机

## 恢复工作环境

1. 克隆仓库并阅读根目录`task_plan.md`、`progress.md`和`findings.md`。
2. 安装Python 3.10+，当前验证使用Python 3.13。
3. 单独恢复完整同版本ConfigDB，或者设置`WUWA_CONFIG_DB`。
4. 核对Misc中的快照信息，再运行结构检查和测试。

```powershell
python scripts/check_project.py
$env:PYTHONPATH = 'src'
python -m unittest discover -s tests -v
python run.py export-recap --quest-id 139000026 --output outputs/sample
```

源码仓库包含程序、测试、指南、研究报告及审查记录。数据库、outputs、work和本地.codex配置由使用者另行恢复。完整测试读取本机快照，当前预期快照为3.8.11。

## 当前状态

本轮新增`linked_recap.py`，针对正常任务流程单列的情况查找唯一关联回顾。168850009的3/10、3/13、3/11从Type11条目168850014取得顺序，经前置关系、唯一提示、完整归属、占位节点与调用依赖核对，阅读版恢复76条，共127条。原始51条events和外部资料保留，严格验收不提升，来源及回顾区段写入`linked_recap_sections`。详见[后日谈恢复](../research/epilogue-linked-recap.md)。

当前批次为`20261118_021247_948737`。多阶段直接PlayFlow按独立片段提取，保留进入/完成调用阶段，不因调用先后就宣称异步播放完成先后。《远赴乘霄》恢复节点35的4句，阅读正文由182条增至186条。节点150的6/13→6/9仍是一组6句，整任务顺序仍待确认。详见[阶段核查](../research/departure-phase-progression.md)和[连接规则](../research/departure-condition-followup.md)。

`sequence_dependency_review.flow_progression`记录流程阶段、玩法启停、局部完成前提和共享状态写入。《风消雪霁》的三段整体顺序继续未确认，具体缺证点见[推进关系核查](../research/wind-task-progression.md)。

上一轮`task_condition_flows.condition_task_sequences`补充无整体主干任务中的直接Condition.PlayFlow，纯性别分支的内嵌树须逐节点匹配独立存储记录，随后读取女性分支。7条主线新增399条局部事件，见[条件流程与性别分支恢复](../research/task-condition-flow-recovery.md)。

上一轮数据库修正规则为`sync_prefix.insert_sync_dialogue_prefix`，经`task_extras.review_extras`进入单任务和批量导出。节点前两项唯一同步调用可以把第一项对白放到第二项的回顾锚点前，排除条件祖先、异步与歧义引用。《昔我悲伤，今却歌唱》已恢复4句前置对白，对应批次为`20261118_011538_306549`。证据、边界与验证见[数据库同步前置对白恢复](../research/database-sync-prefix.md)。

默认导出已启用主线精简阅读版，新增`mainline_reading`及`主线阅读报告`。完整材料继续保存在JSON，TXT省略复杂玩法与未定位附录。最新主线统计为73份有主干草稿、11份仅局部有序、1份暂无有序正文。最新扩展为复杂任务单个直接调用的局部提取，以及同一玩法递增计数器的阈值调用排序。12条任务的整体顺序继续待恢复，详见[最复杂任务试验](../research/hardest-mainline-case.md)。

阅读版已完成教学输入及动态队名模板显示，19份TXT发生显示变化。后续按用户要求重点处理变量条件与引用遍历，界面、场景动作的未知类型采用降级策略。实现边界和路线见[当前计划](../research/reading-templates-plan.md)。

最新修正规则覆盖玩法节点的直接Condition.PlayFlow引用，原动作列表提取继续保留。《来自毁灭的回声》新增19条候选文本，主干和第28、29段缺口保持。后续重点核查这些玩法文本的主干位置，以及相关玩法的交互条件和依赖关系。[本轮证据](../research/echoes-recap-28-29.md)

本轮按用户要求完成资源引用和阅读标签清理。手机Emoji与图片Attachment的占位键已从正文缺失清单排除，剩余1条普通正文待确认。TXT统一去除富文本标签，源文字和图片信息保存在JSON。逐处前后文与复现方法见[资源核查](../research/resource-reference-cleanup.md)。

最近解析批次为20261118_021247_948737。135任务记录中132有文字，12所选路线、0部分有序、61回顾草稿、62候选材料。回顾缺失定义为7任务12处，精确去重10项，另保留1处原选项控制缺口，严格整任务通过2。

最新`sequence_dependency_review`保存无主干任务的Sequence结构、完成条件、控制器状态关系及变量写入。卷宗49到条件58、卷宗对白到控制器146900070的路径已经记录，整体节点顺序继续待核查。[依赖核查记录](../research/mianlong-sequence-dependencies.md)

最新加入`sequence_task_review.py`，为没有回顾的简单Sequence任务生成单流程阅读片段。《时序之主》99句对白、6条选择已有段内顺序，媒体1条占位。节点78进入1507与79等待完成的关系已记录，83显示对象到65交互的关系只作候选。整个任务的兄弟节点执行次序继续未核验，不能把新增分段视为完整路线。详见[本轮核查](../research/master-of-time-sequence.md)。

用户明确任务调用优先，实体或玩法触发依赖其次，回顾作为补充。`task_finish_supplement.py`恢复《灼我以烈阳》38/1后40/1的4句对白，保留异步作用范围和场景动作。12条无整体顺序的Type1记录已有文本，部分有局部有序片段，仍需将区段连成任务路线。详见[本轮规则](../research/task-finish-supplement.md)。

新增`recap_dependency_order.py`，对唯一且已解析的回顾段落，依据同一节点的完成条件及直接调用修正顺序。《荣耀暗面》8/3完成后异步调用8/1，用户查看录播后支持该顺序，已移为附近8/2、8/3、8/1。8/2相对8/3沿用原回顾。JSON保留原顺序和修正依据，历史配置成因未知。详见[本轮记录](../research/glory-dependency-order.md)。

最新规则位于`tip_finish_flow.py`与`recap_order.py`。915000004的27/1通过节点155的同步完成动作、唯一回顾提示及27/2实体交互的CheckChildQuestFinished条件定位。27/1已放在27/2之前，18句对白与5条选择进入正文，4条未选材料留在附录。不能仅按空提示的位置插入，此例已通过连续阅读发现并修正提示位置与完成依赖的冲突。详见[本轮记录](../research/tip-finish-flow-validation.md)。

本轮新增`entity_trigger_timing.py`，按地图与实体编号关联任务节点的唤醒和销毁。《圣者，忤逆者，告死者》4段17条文本继续在附录，TXT新增阶段标签。14/1与14/2应匹配地图904，14/1的实体编号在地图8另有复用。阶段证据未证明实际范围进入时间与异步结束顺序，后续不得直接按唤醒节点插入。通用规则覆盖11任务31处引用，详细证据及下一步见[阿维纽林触发核查](../research/avinuolin-trigger-review.md)。

当前按现有文本顺序推进，媒体内部内容后置。尤诺变量条件路线与入学界面返回路线均已支持，四处QTE也可按唯一完整TalkSequence排列已有文本。实际结果和返回仍未核验。原20项中另有4项独立演出后置、10项定义缺失；其他任务的整体顺序和附录归属继续按覆盖报告推进。最新实测见[进度](../../progress.md)与[专项记录](../research/qte-configured-text-order.md)。

最新通用规则把同一节点的条件流程与同步完成调用组成局部有序片段。《那神圣微风时常吹入》已生成一组40事件，未提升为主干顺序已确认。后续应继续核查这些片段的唯一插入位置及其他明确调用链。[规则记录](../research/task-local-sequence-validation.md)

无回顾主干任务已支持相邻同步调用的局部顺序，前轮增加7组171条文本事件，涉及6条任务记录。媒体占位后的已知对白可继续导出。结果存于顶层task_local_sequences，各组整体位置继续待确认。[规则记录](../research/adjacent-task-order-validation.md)

后续已扩展并行祖先与最大连续同步调用段，新增5组207条文本事件，涉及4条任务记录。调用之间有其他动作时分别保留，分支触发条件不代入实际存档。当前总计13组418条局部有序文本事件，整任务顺序尚待继续关联。[扩展规则](../research/parallel-task-order-validation.md)

## 接手顺序

最新局部排序规则支持条件对白完成后的InformationView和后续对白；面板正文放在`intermediate_content`，原外部资料保留，重复统计使用来源指针。代表任务为880000025节点26，批量同时作用于回放32750006。两条记录仍为局部有序，不把面板关闭或其他节点顺序视作已验证。详见[心愿纸条核查](../research/wish-note-call-order.md)。

2026-11-18最新方向以数据库解析和基础语料为主。先阅读根目录当前计划与批次`20261118_021247_948737`的报告，优先核查数据库引用漏扫、选择后续、重复和有明确依赖的排序问题。每项记录任务ID、入口、现有证据及尚缺证据，再选择可实际修复的代表任务。

JavaScript两轮研究保留在专题文档中供定点参考，此前补导IQuest与FlowActions的建议已移出当前待办。12条无整体顺序主线继续按已有证据输出局部正文，后续遇到新的数据库依据再扩展。视频、演出内部内容和复杂活动细节沿用后置安排。当前项目交付为解析器和JSON/TXT基础语料，知识库及知识图谱另行规划。

TXT已按字段来源排除任务目标、占用提示和明确系统按钮标签，原始JSON继续保留。用户截图中的远航星天槎系统与陆·赫斯对白具有玩法187000050归属，当前仍保留其位置待确认状态。后续继续核查任务调用顺序，避免按相似措辞删除真实对白。[标签核查](../research/reading-labels-validation.md)

先从现有配置中选择能恢复已有对白顺序的代表问题，重点核查显式跳转、同步调用、分支汇合和重复展示。缺失正文、流程及媒体内部内容暂存记录。旧严格完整性统计继续保留，当前开发验收关注已有文本能否按配置顺序导出。每轮规则修复后运行相关测试、全量回归及批量比较，再记录已排序范围和顺序待确认处。

模拟领域1505的14条候选已有详细触发证据。8/3多调用、8/8完成条件引用及37至成功节点3的关系需要新执行证据。现有研究见[第五轮阅读验收](../research/reading-acceptance-005.md)。

## 维护约定

- 现有`wuwa_story.*`模块路径继续兼容，公共命令集中到`cli.py`。
- 新专题结论放`docs/research/`，当前接口说明放顶层docs指南。
- 人工审查记录放`docs/reviews/`，生成文件进入outputs。
- 当前规划三文件保持简洁，已完成的长历史可追加到`docs/history/`。
- 可使用`python scripts/check_project.py`检查语法与可见本地Markdown链接。
