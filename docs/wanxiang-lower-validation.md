# 万象新声·下：外部内容调查与待核验导出

2026-11-17，QuestId=139000026，数据快照 3.8.11。

## 已查明的关联

| 调用 | 证据 | 处理边界 |
|---|---|---|
| PlayMovie C3jinzhoutexie | db_cgVedio.videodata，女版 CgId=104/GirlOrBoy=0，字段 4 指向 M01012_Nvzhu | 输出资源引用和媒体引用标记，不伪造对白 |
| 视频字幕 | videocaption 无同名 CgName 记录 | 不等于无字幕；演出资产尚未读取 |
| CommonTip | QuestFailed 节点 181；TidMainText 对应“距离任务目标过远，请完成任务目标后继续” | 失败提示单列附录，不拼到正常路线 |
| OpenSystemBoard | 节点 16 FinishActions；三次 PlayFlow 后；RoleDescription/BoardId=1 → roledescription.Id=1、RoleId=1202、字段 3 文本键 | 提取介绍正文，保留调用位置和前序动作；不宣称还原全部 UI |
| OpenSystemFunction | 节点 176；FunctionId=10001003 → functioncondition 字段 1“共鸣者-声骸页签” | 仅提取界面名称；前序 PlayFlow 是 Async，不推断其完成时刻 |
| CompleteGuide | 节点 146，GuideId=10058 | 记录为完成标记，不把它当成播放引导 |

视频女性资源路径：`/Game/Aki/Sequence/LevelB_Seq/Main/Section1/M01012/M01012_Nvzhu.M01012_Nvzhu`。需要从客户端导出并检查该演出资产及依赖，才能判断是否含对白/字幕；ConfigDB 表缺行不能代替这一核验。

## 通用规则与产物

新增 external.py：按调用类型及引用 ID 关联配置，不依赖任务 ID 或人物名。节点内容记录 node_id、阶段、动作索引、前序动作与来源哈希；无法确定全局顺序的内容放附录。

```powershell
python run.py export-task --quest-id 139000026 --allow-incomplete
```

结果在 `outputs/待核验任务/139000026_万象新声·下.json` 及同名 TXT。共 10 段流程、39 个事件：33 条对白/叙述、5 次选择、1 个媒体引用标记。正文文本引用无缺失；附录记录 4 个外部任务调用。女性渲染与原文保留不变。

`validation.status=needs_review`、`complete_for_supported_task_shape=false`，并以 confirmed_missing_text_ids 和 unverified_content 分别记录已确认缺失与待核验事项。不开启此参数时仍拒绝导出，批处理不将草稿计入成功。待核验产物不能直接当作完整知识库基底。

另修正一种选项容器：Type=Option、有 Options、无 TextId 且 PlotLineKey 为空时，不将其遗留 TidTalk 当成旁白。原节点保存在 talk_groups.non_dialogue_option_containers。实际案例中的 Flow_139000018_1320 就属于这种容器，不能凭缺失键补写剧情。

## 验证及下一步

22 项测试通过，包含真实引用、女性视频版本、失败提示隔离、严格模式拒绝、缺失视频引用、选项容器，以及原有案例回归。测试中的全批量复查仍为主线 2/85、补充 0/50。

还需读取女性演出资产与依赖，验证字幕/对白来源；补 UI 可展示正文、条件和时间顺序。此处“无缺失文本”仅针对已解析数据库文本，不代表无视频或界面缺口。之后再用万象新声·上做跨任务验证。

## 后续纠正：媒体未知不等于文本缺失

用户提供的属性文件证明该资源是 StreamMediaSource，指向 filepath://./Aki/Movies/ZhanZhuang/M01012_Nvzhu.mp4；没有对白轨道字段。用户未找到该媒体文件，本项目不再要求提供视频本体作为文本导出的前提。

当前整理版仍为 39 个事件，其中 1 项 kind=media_reference。coverage_version=2，confirmed_missing_text_ids=[]，known_text_references_complete=true；额外媒体文本和 UI 时序在 unverified_content 中独立保留。不能将“无匹配字幕记录”解释为“确认缺字幕”或“确认没有字幕”。严格成功标准尚未调整，批量仍为 2/85。

## 2026-11-17：界面归属与局部调用时序核对

新增通用节点上下文：沿 ParentNodeId 保存祖先链、条件与并行节点 Count；失败分支识别覆盖后代。动作记录同阶段前序/后续调用及异步索引，只证明配置排列，不证明完成时刻或全局运行顺序。

RoleDescription BoardId=1 → RoleId=1202 → db_role.roleinfo 字段4的 RoleInfo_1202_Name → 炽霞；保留角色行哈希和姓名文本键，不使用剧情猜名，也不改匿名说话人规则。节点16角色介绍位于三次 PlayFlow 调用之后。节点176在 Wait、Async PlayFlow 之后调用声骸页签，不能断言对白先结束。节点181失败提示在 SetPlayerPos 之后配置，不混入正常对白；节点146仍仅为引导完成标记。

新增 task_ui_texts 附录，共20个引用，覆盖 TidTip、UIConfig 标题/子标题和 OccupationConfig；保存具体字段路径、所属节点、显示标记、条件、raw_text 与女性渲染 text。空字符串不是缺失；HideUi/HideTip 不被忽略，也不等同于已经证明运行时隐藏；{q_count} 保留为动态计数，不能伪造玩家状态。

重新导出39事件、4外部调用、20界面引用；已确认缺失文本引用0。全部24项测试通过，包含135个候选的批量集成检查，严格成功仍主线2/85、补充0/50。JSON/TXT 保持 needs_review：完整界面展示、跨节点运行时序、媒体额外文本尚未证明。

下一步：用《万象新声·上》做相同界面归属/异步规则的跨任务验证，分析接受任务等额外控制；全局任务图执行与完整 UI 重建仍属后续工作。无需将视频本体作为文本导出前提。
