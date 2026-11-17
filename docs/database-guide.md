# 数据库组织与关联方式

## 资料范围

本文依据本地 ConfigDB 数据库的实际检查结果编写，未将公共仓库的字段布局直接当成本地事实。

`Misc/BuildInfo.txt` 标识：

```text
Stream=branch_3.8_final
Changelist=9463240
PatchVersion=3.8.11
```

`Misc/ConfigVersion.txt` 中 `PublicJsonVersion=9449032`。这些是数据快照标识，不证明所有包含的任务都已开放，也不能据文件名判断剧情首次上线版本。

已读取 988 个 `.db` 文件，无 SQLite 打开错误。数据中存在测试、隐藏、占位与未必可达的内容。

## 目录组织

```text
ConfigDB/
├─ db_QuestTree.db           章节树
├─ db_QuestData.db           任务定义
├─ db_QuestNodeData.db       任务执行节点
├─ db_flow.db               流程目录
├─ db_flowState.db          流程状态及动作
├─ db_speaker.db            说话人配置
├─ db_level_entity.db       地图实体配置
├─ db_plot_audio.db         剧情音频映射
├─ db_*.db                  其他玩法、角色、物品等配置
├─ zh-Hans/lang_*.db        简体中文文本
├─ en/、ja/、zh-Hant/等     其他语言
└─ Misc/                    版本和构建信息等
```

根目录配置主要描述“怎样运行、引用什么”；语言目录主要描述“显示什么”。每个数据库可以有多个表，不应假设文件名等于表名。

## SQLite 外层与 BinData 内层

大量配置表只有可索引的键和 `BinData BLOB`。BLOB 是二进制配置结构；其中某些字段存放 JSON 字符串，另外一些字段是整数、字符串、数组等。

例如 `questdata(QuestId, BinData)` 的 JSON 中包含任务的 `TidName`、`Type`、`DungeonId`；`flowstate(StateKey, BinData)` 中则包含动作数组。当前解析器按二进制字符串字段边界解码 JSON，不把整个 BLOB 当 UTF-8 文本，也不把数据库行顺序当剧情顺序。

本地读取成功：任务 JSON 1,930/1,930，任务节点 JSON 27,161/27,161，流程状态 JSON 21,971/21,971。读取成功只表示数据可解码，不表示所有控制动作都能执行。

## 核心表

| 文件 / 表 | 外层键和重要字段 | 当前记录数 | 作用 |
|---|---|---:|---|
| `db_QuestTree / questtreechapter` | `Id, BinData` | 5 | 章节名称引用等 |
| `db_QuestTree / questtreenode` | `Id, ChapterId, BinData` | 137 | 任务列表、前置与后继节点 |
| `db_QuestData / questdata` | `QuestId, BinData` | 1,930 | 任务定义 |
| `db_QuestNodeData / questnodedata` | `Key, BinData` | 27,161 | 节点、条件和动作 |
| `db_flow / flow` | `Id, BinData` | 10,782 | 流程目录 |
| `db_flowState / flowstate` | `StateKey, BinData` | 21,971 | 流程状态动作 |
| `db_speaker / speaker` | `Id, NameStringKey, TitleStringKey, BinData` | 7,017 | 显示身份及相关资源 |
| `db_PlotHandBook / plothandbookconfig` | `QuestId, BinData` | 100 | 剧情回顾相关配置；当前不作为唯一任务目录 |
| `zh-Hans/lang_multi_text / MultiText` | `Id, Content, RedirectDbIndex` | 342,381 | 混合中文文本 |
| `zh-Hans/lang_multi_text_1sthalf / MultiText` | `Id, Content` | 2,149 | 分库正文 |
| `zh-Hans/lang_speaker / Speaker` | `Id, Content` | 8,303 | 显示名称或文本键 |

完整表清单由 `inventory` 写到 `outputs/数据库目录清单.json`，不在本文重复列出所有 988 个文件。

## 章节到正文的关联

```text
questtreechapter.Id
  → questtreenode.ChapterId
  → 节点内部的任务 ID 数组
  → questdata.QuestId
  → questnodedata.Key（任务ID_节点ID）
  → PlayFlow / 交互配置等中的 FlowListName、FlowId、StateId
  → flowstate.StateKey
  → ShowTalk.Params.TalkItems
  → TidTalk → MultiText.Id → Content
```

`TidTalkOption` 是选项文字的引用。`JumpTalk.Params.TalkId` 是当前对白块里的跳转目标，不是文本库 ID。任务节点还可能包含 Sequence、选择器、条件和嵌套节点，不能按数字键排序模拟游戏。

实际验证示例：

```text
章节树 1（但觉今州胜旧州）
→ 节点 110000
→ 任务 139000025（万象新声·上）
→ 任务节点 139000025_19
→ 剧情_新主线_CE版_序章 / FlowId 1 / StateId 1
→ StateKey = 剧情_新主线_CE版_序章_1_1
→ TidTalk = HuanglongXZ_3_9
```

StateKey 的数字应依据显式流程引用构造；流程名本身含下划线，不能任意拆分字符串。章节树的章节 ID 与任务配置中的其它 ChapterId 不能未经验证就视作同一命名空间。

## 文本库及分库

MultiText 混合任务提示、对白、物品、角色名、界面提示等内容；仅凭 `Main_` 前缀筛选会遗漏其他命名的主线相关文本。

此快照中，大库有 2,148 条 `RedirectDbIndex=1`，正文全部是星号；这些 ID 全部能在 `multi_text_1sthalf` 找到实际正文。小库还多一条开发占位记录。

当前实现将小库按 ID 覆盖合并。这个做法对已检查快照成立；尚未实现任意重定向编号、任意数量分库或跨版本合并冲突策略。扩展时应显式按重定向表加载，并保留每条正文的源库和覆盖原因。

`{Male=...;Female=...}` 和 `{PlayerName}` 是动态模板。当前 raw_text 保留原样，text/TXT 选 Female 分支并将玩家名替换为“漂泊者”，{TA} 渲染为“她”。

## 姓名读取

```text
TalkItems.WhoId
→ speaker.Id
→ 优先 NameStringKey
→ 若无效，使用 BinData 中 Name 索引（本快照字段 3）
→ lang_speaker.Speaker.Id
→ Content 是文本键时，再查 MultiText
```

例如说话人 1424 的 `NameStringKey=-1`，通过二进制名称索引可以读到“妮娅”。空的外层名称键不意味着角色没有名字。

当前版本已验证的二进制字段位置：

| 表 | 字段位置（从 0 计数） |
|---|---|
| questtreechapter | 0=Id，1=章节名称文本键 |
| questtreenode | 0=Id，1=ChapterId，2=任务数组，9=前置节点数组，10=后继节点 |
| questtype | 2=任务类型名称文本键 |
| speaker | 3=旧式名称语言索引 |

字段位置属于版本适配，不是永久协议。外部脚本曾使用与本快照不一致的位置，因此升级数据后必须重新验证。

## 匿名身份与场景实体

`WhoId` 是显示说话人标识，不是可靠的全局人物实体 ID。本快照中 153、178、849 分别显示单、三、双问号；178 被多个不相关场景复用。

配置线索包括：

- `BeginFlowTemplate.Params.Actors`：每个槽位的 EntityId、TalkerId、IsPlayer。
- `ChangeActorTalker`：同一 ActorIndex 改用另一个 Talker。
- `db_level_entity.levelentityconfig`：Id、MapId、EntityId、BlueprintType、BinData；部分组件含 TidName。

当前实现只对活动模板内的唯一匿名槽位、已有明确称呼的连续演员绑定记录 `config_actor_continuity`。原始显示名保留，不做全局角色合并。

同一个问号 ID 可以对应同场景多个演员；同一个 EntityId 可以在不同地图指向不同对象。场景中只有一个正式角色，也不够证明问号就是他。语音文件名也可能按任务命名，不能直接用于姓名归属。

当前问号审计范围为 1,254 条记录、467 个状态；71 个状态带 BeginFlowTemplate，10 个带 ChangeActorTalker。这些是线索数量，不是已解析身份数量，也不包含所有“神秘声音”类描述名称。

## 完整性与已知限制

任务及节点内 8,890 次显式流程引用均有匹配（重复引用计入）。流程正文/选项有 139,936 个不同文本 ID，其中 685 个未在当前合并的两个中文大库中找到。不能因此直接认定资源缺失，可能需要其他文本源或特殊处理。

`db_flow_text` 只有 15 条，含明显测试内容；它不是本快照的主要剧情文本库。语言目录中的 `lang_flow` 也不能替代根目录 `db_flowState`。

任何“完整剧情”结论都还需要执行可达性、分支、条件、环境对白和覆盖检查。本文的统计与读取能力不能替代这些验证。

## 研究参考

- [WuwaID 的任务排序导出源码](https://github.com/TitoTFP/WuwaID/blob/main/scripts/export_quest_ordered.py)：用于发现关联线索；本地字段布局另行验证。
- [Wuthering Waves Dialogue Generator](https://github.com/RealNath/wuwa-dialogue-generator)：提供任务、流程与正文组合的参考，并说明某些旁路对白覆盖限制。

下载的参考源文件留在忽略的 `work` 中，未纳入正式包。

## 剧情回顾顺序：PlotHandBook

`db_PlotHandBook.db` 的 `plothandbookconfig` 表以 QuestId 关联任务。当前快照 BinData 内嵌有序 JSON 列表，条目包含 TidTip、Flow（FlowListName / FlowId / StateId）和 IsHideUi。空流程条目是提示，不是播放状态。非空流程可通过拼接状态键关联 flowstate。

此列表提供回顾顺序，不能直接视为所有任务的运行时执行顺序。解析器仅在任务拓扑受支持、回顾列表无重复且覆盖全部显式流程引用时使用它；缺少该记录或集合不一致会停止。不要将同名任务当成同一 QuestId。

### 引导配置关联（3.8.11已核对范围）
关联链为 db_guide_new.db：guidegroup.Id=GuideId → 字段1步骤ID向量 → guidestep.Id；步骤字段8的已核对类型1/4/3分别关联同ID的guidetips/guidefocusnew/guidetutorial。提示正文字段分别为1/13；教程字段6为组标题，字段3为页面ID向量，再关联guidetutorialpage.Id，字段2为标题、字段4为正文、字段1为图片路径。文本键通过现有MultiText索引读取，缺失引用计入confirmed_missing_text_ids。类型或引用不明确时拒绝，不静默跳过。


平台标记仅保留原值；内部显示条件未完整解码，不据此宣称运行时必定显示。详见wanxiang-upper-validation.md的最新记录。

### 手机消息（当前核对形状）

shortmessage字段1是ChatPartnerId整数，字段2为字符串向量（流程列表、FlowId、StateId）；字段9不是联系人列表。chatpartner字段4是姓名文本键。全库299条消息均能通过字段1连接联系人。32010→联系人3/洛瑟菈，36009→联系人72/清宵。手机正文复用flowstate解析；SystemTip和Attachment分别处理。附件关联db_PhoneMessageAttachment，Image字段3/5为图像路径。旧版“类型3、字段9联系人48/赞妮”的解释已纠正，详见phone36009-decoding.md。

## 七任务文本引用核查更新（2026-11-17）

以[缺失引用核查](research/missing-text-validation.md)为当前接手点。NoTextItem/QTE的TidTalk按控制引用处理，JSON保留non_dialogue_controls及原始文本和动作；TXT不输出内部演出占位为台词。QTE成功/失败不按普通选择执行，批量单列qte_runtime_unverified。普通Talk的缺失不静默过滤。76项测试通过；最新批次20261117_011055_476513，135对文件核对通过，missing_text任务剩《灼我以烈阳》1个。资源缺失与失效回顾引用尚不可区分，下一步查4/5与4/1的归属/版本证据。

## 灼我以烈阳引用核查补充（2026-11-17）

见[本轮核查](research/scorching-sun-reference-validation.md)：缺失键有共用语音候选，但无字幕替代证据，保留missing_text。JSON新增missing_text_diagnostics，包含任务/回顾归属与语音候选，replacement_applied为false；候选不进入阅读正文。79项测试通过，批次20261117_011321_141069核对135对文件，统计不变。该条目待新证据，后续可推进QTE路线验证。

## 配置字幕更新（2026-11-17）

见[M0391字幕核查](research/m0391-caption-validation.md)。媒体事件新增media.captions与caption_order_evidence，字段4关联正文，四组候选数值一致排序仅作为相对顺序推断；无语言/单位/角色猜测。M0391已补10条，C0027已补18条，替代旧“字幕尚未解码”的进度描述。92测试、批次20261117_012201_323353核对135对产物；有序12、候选123不变。阅读检查仍保留实际播放及额外画面文字边界。

## InformationView（2026-11-17核验）

OpenSystemBoard.InformationView的BoardId精确关联db_infodisplay.infodisplay.Id；BinData字段3/4分别为标题和正文文本键。information_board事件保存两条texts、purpose、source_field、text_id、raw_text及源行哈希，组合显示标题和正文。任务级调用保持外部材料位置；面板中的引用对白不自动归属人物。见[资料核查](research/echoes-information-view.md)。
