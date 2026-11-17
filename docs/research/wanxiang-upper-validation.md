# 万象新声·上：跨任务验证与导出

## 2026-11-17：《万象新声·上》跨任务验证

任务139000025，89节点、21段显式流程，与 PlotHandBook 一一覆盖。新增六类配置形状受限的世界动作：SetReviveRegion、SetPlayerOperationRestriction、ServerSetPlayerPos、UnlockTeleportTrigger、AddBuffToEntity、SetWeather；记录为玩法假设而不执行，未知参数字段拒绝。新增 AccpetCurrentQuest（源数据拼写）空参数调用标记，仅待核验模式可用，保留剧情中的调用位置，不递归接取任务或模拟回调。

序章_1_16 的 FlatBuffer 字段1与6含完全相同的动作数组。通用规则只在全部候选数组深度相等时解析一次，scenes.equivalent_action_fields 保存字段号；不同数组继续报错，不猜男女版或优先级。

复用界面关联：节点120 FunctionId10036为“协奏作用”，节点14 FunctionId10031为“锁定技能”；它们都是功能标签，不能充当完整引导正文。新增 GuideTrigger 外部记录，保存条件及GuideId，与 CompleteGuide 完成标记区分；无法解读的引导正文单列 unverified_content。

产物：outputs/待核验任务/139000025_万象新声·上.json、同名TXT。216事件=182对白+32选择+1媒体引用+1任务接受标记；47条节点界面文本引用；50个外部调用=25次GuideTrigger+23次CompleteGuide+2次OpenSystemFunction。已解析文本引用缺失0，仍保留2条匿名身份未确定记录。女性媒体 Start 对应CgId102，仍不以找视频作为文本导出前提。

28项测试全部通过。另实际运行 export-mainline，结果保存 outputs/主线批量/20261117_002647_393136：主线2/85、补充0/50，与此前一致；scan-mainline也已重跑。严格模式继续拒绝该任务，待核验产物不计入成功。

尚不支持：引导完整正文及实际显示、任务接受后的运行时激活/回调、跨节点全局执行和条件求值、媒体额外文本核验。下一步优先按GuideTrigger引用检查引导配置、补引导正文来源；完成后再进入《捕梦于神秘园中》的邮件机制。下篇此前的4外部调用计数属于当时导出范围；新增GuideTrigger通用支持后重新生成下篇可能增加附录记录，本轮未覆盖其旧产物。

复现：

```powershell
python run.py export-task --quest-id 139000025 --allow-incomplete
$env:PYTHONPATH="src"
python -m unittest discover -s tests -v
python run.py export-mainline
python run.py scan-mainline
```

## 2026-11-17：GuideTrigger 正文来源与显示条件

新增 guides.py。关联链为 db_guide_new.db：guidegroup.Id=GuideId → 字段1步骤ID向量 → guidestep.Id；步骤字段8的已核对类型1/4/3分别关联同ID的guidetips/guidefocusnew/guidetutorial。提示正文字段分别为1/13；教程字段6为组标题，字段3为页面ID向量，再关联guidetutorialpage.Id，字段2为标题、字段4为正文、字段1为图片路径。文本键通过现有MultiText索引读取，缺失引用计入confirmed_missing_text_ids。类型或引用不明确时拒绝，不静默跳过。

25次引导触发关联60个步骤（28提示、27聚焦、5教程），6页，72条标题/正文引用，无缺失文本键。正文仍216事件；引导多平台候选放外部附录，未拼成正常对白。JSON保留表名、行ID、字段号、源行SHA-256及Base64二进制，便于后续核查未解码字段。TXT带步骤ID、原始平台标记、文本用途及来源。

显示条件：10018在节点153 FinishActions配置角色处于Ground；10017在节点163 FinishActions配置Ground及InCombat=true；10054在节点120 EnterActions配置InCombat=true。保留条件数组，不假设运行时状态或求值方式。节点条件/祖先链仍保留，空Conditions不代表无其他显示限制。

步骤字段1的TFF/FTF/FFT/TTT保留为platform_mask_raw，不擅自把位序命名为某平台。按键{0}等占位符、富文本保留；图片内容未OCR。内部引导显示字段尚未完全解码，因此status=guide_config_read_display_unverified、display_verified=false。CompleteGuide仍只为完成标记，未知身份规则未变。

重新导出139000025 JSON/TXT并验证全部正文和附录文本一致。31项测试通过，包括缺失/重复步骤、未知类型、缺失文本、平台候选保留、页面顺序和真实任务条件。实际批量输出outputs/主线批量/20261117_003059_825993：主线2/85、补充0/50，严格成功数不变。

下一步按原计划进入《捕梦于神秘园中》的邮件正文来源、任务归属与顺序；引导平台位序、按键绑定、内部条件、运行时回调/时序仍作为独立未决项，不阻塞现有配置文本整理。
