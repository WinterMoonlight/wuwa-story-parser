# 剩余20项阻塞的证据与补文件清单

范围更新：用户已明确优先排列现有文本，视频和演出内部文字后置。本清单保留为后续外部内容取证参考，当前推进不要求先补齐这里列出的资产。最新验收范围见docs/reading-acceptance.md。

核对日期为2026-11-17，依据批次`20261117_144506_357719`、24项历史队列及后续专项核查。当前有13个任务、22处回顾阻塞，按精确状态和错误去重为20项。B19重复出现三次。B02千夏原选项的控制缺口另行记录，当前默认已采用可解析备选，因此不在这20项内。

## 按下一步工作区分

|范围|数量|现有配置还能做什么|需要补充的证据|
|---|---:|---|---|
|B05 条件菜单|1|实现有明确入口前提的完整局部分支，已有两条8事件实跑证据|若要还原某次真实游玩，另需当时变量状态或可证明的初始化执行链|
|B21—B24 演出调用|4|增加UnlockEntity/AwakeEntity参数支持和实体链审计|完整区段还需要演出属性、事件时刻、文本轨道或无文本依据|
|B06—B09 QTE|4|保留已提取的前后文字和已知配置顺序|QTE完成/失败/退出映射及ShowTalk继续条件|
|B11—B20 缺失流程|10|精确缺失键、回顾位置和候选映射均已核查|补丁中的精确状态定义或明确迁移/废弃说明|
|B01 Enrollment|1|已有调用前1事件、调用后25事件的局部文字|实际View调度、BoardId用途及回调到后续对白的关系|

目前没有一项能够在不引入新证据或条件前提的情况下直接宣布完整解除。B05仍有本地实现空间，基础语料可以明确记录所选合法路线的前提，无须把玩家真实存档作为开始实现的条件。该能力的局部完整性和实际游玩可达性需要分别记录。

## 20项逐项清单

表中的B编号沿用现有研究队列，便于对应已有报告。

|编号|任务与状态|缺少的关键证据|下一步|
|---|---|---|---|
|B01|冰原下的星炬，拉海洛上半1/15/1|Enrollment到实际View的调度，打开/提交/关闭后何时继续对白|优先查运行脚本，候选UI资产只能辅助|
|B05|今夜，注定属于月亮，尤诺NPC生态5/1|实际入口的喝绿的、喝红的、还剩，或首次交互执行证明|现有配置可实现带前提的两条路线，暂不要求用户补文件|
|B06|独在异乡为异客，黎那汐塔下半3/6|9027001至9027005的完成/失败映射与段落结束条件|取DA_M2_12_32及其事件依赖|
|B07|致第二次日出，拉海洛下半2/4/5|9027017的完成/失败/退出行为|取DA_M3_1_14及其事件依赖|
|B08|远航星，高达10/1|1031010、1031005、1031006、1031007完成后到换关卡和后两句的返回边|取DA_M3_2_19及其事件依赖|
|B09|远航星，高达3/1|1031008、1031009到Talk2的返回边|取DA_P0043及其事件依赖，已有浮动字幕同文线索已核查|
|B11|往岁乘霄醒惊蛰，岁光副本1/3|精确状态定义或明确替代关系|核对新增配置版本，精确键见下表|
|B12|来自毁灭的回声，黑海岸6/17|精确状态定义或明确替代关系|同上|
|B13|来自毁灭的回声，黑海岸6/3|精确状态定义或明确替代关系|同上|
|B14|昔我悲伤，今却歌唱，帕尔米罗4/8|精确状态定义或明确替代关系|同上|
|B15|圣者，忤逆者，告死者，阿维纽林10/1|精确状态定义或明确替代关系|同上|
|B16|圣者，忤逆者，告死者，阿维纽林11/27|精确状态定义或明确替代关系|同上|
|B17|圣者，忤逆者，告死者，阿维纽林4/11|精确状态定义或明确替代关系|同上|
|B18|圣者，忤逆者，告死者，阿维纽林5/30|精确状态定义或明确替代关系|同上|
|B19|荣耀暗面，七丘上1 5/5，出现3次|精确状态定义与三处引用的关系|同上，单独核验重复调用|
|B20|独在异乡为异客，黎那汐塔下半6/11|整个Flow6及State11定义，或明确迁移关系|同上，当前Flow6目录也缺失|
|B21|往岁乘霄醒惊蛰，岩壁遗迹5/2|Relic16演出内容、事件A时刻及UnlockEntity回调|取DA_Seq_CXS_Relic16|
|B22|夜与昼，均请摘下面纱，金库上层2/19|冰柱01演出、事件A及唤醒/改状态链|取DA_BingZhu01|
|B23|夜与昼，均请摘下面纱，金库上层2/20|冰柱02演出、事件A及唤醒/改状态链|取DA_BingZhu02|
|B24|庭际刀刃鸣，第四章26/2|演出正文、事件A/B实际时刻和目标地图绑定|取dat_Shangjiao01_Camera_Seq3_2|

## 第一批补充文件

以下八个资产路径均直接来自本地flowstate的原始动作引用。路径前缀在FModel中为`Client/Content/Aki/`。每行导出对应对象的属性JSON。

|对应项|FModel中Aki之后的目录|对象名|
|---|---|---|
|B06|`Sequence/LevelB_Seq/Main/Section2_7/M2_12_32/`|`DA_M2_12_32`|
|B07|`Sequence/LevelB_Seq/Main/Section3_0/M3_1_14/`|`DA_M3_1_14`|
|B08|`Sequence/LevelB_Seq/Main/Section3_1/M3_2_19/`|`DA_M3_2_19`|
|B09|`Sequence/LevelA_Seq/POI/03_1/P0043/`|`DA_P0043`|
|B21|`Sequence/Main_Seq/Function_Seq/chengxiaoshan/`|`DA_Seq_CXS_Relic16`|
|B22|`Sequence/Main_Seq/Function_Seq/2_0_Main_Jinku/JiGuangMen/`|`DA_BingZhu01`|
|B23|`Sequence/Main_Seq/Function_Seq/2_0_Main_Jinku/JiGuangMen/`|`DA_BingZhu02`|
|B24|`Sequence/Main_Seq/Function_Seq/LongzhujusuoSeq/`|`dat_Shangjiao01_Camera_Seq3_2`|

### 导出方法与引用依赖

1. 加载完整游戏归档，在Folders按表中目录进入。截图中的顶部输入框只筛选当前文件夹，先进入目录再输入对象名。
2. 对目标选择`Save Properties (.json)`或当前版本Export子菜单中的属性JSON。属性导出与Raw Data队列属于不同输出方式。
3. 双击属性查看实际引用。沿`剧情资源`、`SequenceDataAsset`、LevelSequence及MovieScene的ObjectPath取直接依赖的属性JSON。对象内部的MovieScene、Track、Section可能已包含在同一个JSON中，先检查导出内容。
4. 依赖指向别的目录时，以原始ObjectPath为准。`/Game/Aki/.../X.X`在截图所示目录布局下对应`Client/Content/Aki/.../X`，最后点号后为对象名。
5. 对B06—B09重点保留事件轨道、QTE事件及其回调对象。对B21—B24重点保留事件A/B所在轨道、帧号、文本/字幕轨道及直接回调。具体依赖名要读到JSON后才能确认，八份入口JSON本身未必足够。
6. 属性导出报错时保留错误内容，补导该对象Raw Data及同名伴随文件，保留原目录结构。原文件可能仍需映射支持才能解析。

本批优先取控制与轨道属性。MP4只有在具体引用证明媒体内含相关内容时再处理。

FModel官方发布说明确认Properties JSON独立于Export Session的Raw Data/模型等队列。界面文案可能随版本调整。[官方发布说明](https://github.com/4sval/FModel/releases)

### 项目接收位置

八份入口JSON可放`work/asset_exports/properties/`，保留原文件名，与项目已有资产查找约定一致。直接依赖和Raw Data放`work/asset_exports/dependencies/`并保留游戏相对目录，避免同名资产相互覆盖。

FModel当前导出目录可以不同，复制到项目即可。完成后提供实际保存路径。

## 第二批，运行脚本与Enrollment

B01需要实际调度实现，B06—B09可能也需要QTE运行实现。先在FModel查看`Client/Content/Aki/JavaScript/`。该目录曾出现在用户截图中，当前尚未取得其文件列表，具体实现文件名和所在子目录未核实。

最省交互的方式是把该JavaScript目录导出Raw Data并保留目录结构，放`work/asset_exports/runtime/`。之后由程序对导出内容检索`Enrollment`、`OpenSystemBoard`、`AdmissionStudentCardView`、`QteId`以及各目标QTE编号，筛出实际处理函数。文件可能经过编译或混淆，FModel导出成功不保证拿到可读源码。如果目录体积很大或只有编译文件，先提供文件列表和后缀，再限定下一批，避免盲目导出整个Aki。

`TypeScript/`和`ScriptAssemblies/`也曾出现在截图中，但还没有证据说明这两个目录包含目标实现。目前不要求整目录导出。

下列两个UI路径来自db_ui_resource，可以作为Enrollment候选属性辅助取证。

|候选对象|FModel目录|
|---|---|
|`UiView_AdmissionStudentCard`|`Client/Content/Aki/UI/UIResources/UiActivity/Prefabs/Activity30/Admission/`|
|`PC_UiView_AdmissionStudentCard`|`Client/Content/Aki/UI/UIResources/UiActivity/Prefabs/PC/Activity30/Admission/`|

两者均用属性JSON导出。仅这些候选资源无法证明Enrollment实际打开它们，最终仍需调度分支及提交/关闭回调。`BoardId=0`也没有足够信息定位为某个View。

## 第三批，十个缺失流程的配置来源

这十个中文键是数据库行键。应核对`Client/Content/Aki/ConfigDB/`中的配置及补丁来源，逐个按中文键寻找uasset没有已知依据。

|编号|精确StateKey|
|---|---|
|B11|`剧情_1_1_乘宵山主线_岁光副本_1_3`|
|B12|`剧情_1_3_黑海岸主线_6_17`|
|B13|`剧情_1_3_黑海岸主线_6_3`|
|B14|`剧情_2_0_黎那汐塔主线_第三幕上_帕尔米罗_4_8`|
|B15|`剧情_2_2_阿维纽林主线_10_1`|
|B16|`剧情_2_2_阿维纽林主线_11_27`|
|B17|`剧情_2_2_阿维纽林主线_4_11`|
|B18|`剧情_2_2_阿维纽林主线_5_30`|
|B19|`剧情_2_4_七丘主线_上1_5_5`|
|B20|`剧情_2_7_黎那汐塔主线_下半_6_11`|

现有快照为PatchVersion 3.8.11，Changelist 9463240。先核对是否有本项目尚未导入的补丁/更新版本。若要检查另一份实际来源，最小导出包为以下五个文件，数据库用Raw Data导出。

```text
Client/Content/Aki/ConfigDB/db_flowState.db
Client/Content/Aki/ConfigDB/db_flow.db
Client/Content/Aki/ConfigDB/db_PlotHandBook.db
Client/Content/Aki/ConfigDB/Misc/BuildInfo.txt
Client/Content/Aki/ConfigDB/Misc/ConfigVersion.txt
```

保存在`work/asset_exports/config_check/`，避免直接覆盖当前ConfigDB。若归档中同路径有多个版本，记录每份来源归档名，分别保存。较新或较旧版本只作为对照，核对引用和文本版本后再决定能否使用。

|当前文件|字节数|SHA-256|
|---|---:|---|
|db_flowState.db|60698624|`F6B8A427029F97F8D8D96910C34E2E2E33E8B0E61E5269B49E45B2E361F20516`|
|db_flow.db|1945600|`E50317D92A40671B2033B957F7C57020A9DE035269B25B8C1C0ADBD022B86F00`|
|db_PlotHandBook.db|1019904|`CE76C3B33F244601DBA2DCC27D429EB0D67DE87C879DC4A2842F22C64CC3F0A6`|

哈希相同就无需重复审计；大小相同仍须比较哈希。若实际生效配置与本地完全相同，FModel重新导出不能恢复其中缺失的行。届时保留缺口，等待真实新定义或明确迁移说明。

## 后续执行顺序

1. 用户先补第一批八份精确入口JSON及可直接取得的轨道依赖，主agent核验实际覆盖哪些阻塞。
2. 主agent可独立设计B05带前提的条件路线，沿用现有回归和来源保留要求。
3. 运行脚本仅在拿到可读实现后继续查B01/QTE调度。配置补包先做哈希/版本对照。
4. 每项收到新证据才重开对应调查，记录实际恢复文字和顺序。属性入口文件缺少所需轨道时，保留该项缺口并列出明确的下一条ObjectPath。

本清单提供取证路径，八个资产是否可在当前FModel中成功解析、其依赖是否完整、运行脚本是否可读均尚未实测。
