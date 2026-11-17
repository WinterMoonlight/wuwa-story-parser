# 浮动字幕、条件路线与界面调度专项

2026-11-17。基线为`20261117_143635_948384`。三个子agent分别核查B09字幕调用、B05条件路线、B01界面调度，由主agent复核整合。

## 结论

本轮新增解除0项。保留13任务22处回顾阻塞，精确去重20项，另有1处原选项控制缺口。公共解析代码保持原规则。

|项目|新增核查|处置|
|---|---|---|
|B09 远航星|三维浮动字幕Id4的全库调用线索|没有独立触发和QTE完成证据，保留缺口|
|B05 尤诺饮品交互|两种条件路线的完整局部文本与实体回调|两条各8事件可在明确前提下展开，当前状态未知，默认缺口保留|
|B01 Enrollment|全根目录配置的界面调度与标量引用|学生证候选缺少精确调度和返回映射，保留缺口|

## B09字幕调用

只读检查988个SQLite数据库、2905张表、6010043行，所有表读取成功。检索`subtitle`、`MAIN_YHX_78_2`、浮动字幕和漂浮字幕，解析命中行的嵌入JSON。范围为现有配置，没有读取演出资产。

`MAIN_YHX_78_2`精确命中15行，包括13种语言文本、原始ShowTalk和三维浮动字幕Id4。原始ShowTalk显式序列为`[1,0,2]`，两个QTE在Talk2之前。三维字幕行只增加同文呈现配置，没有提供独立触发时间或完成回调。

|来源|SHA-256|
|---|---|
|floatingsubtitle3d Id4|`59a7af40ea5b4d6b2934fa2372e871b3cb7c9cf4d6bf3306b424c54efc7999aa`|

二维字幕表也有Id4，其文本键为`test2`。两个表的数字ID不能交叉关联。解码配置未发现指向目标的`SubtitleId`或`FloatingSubtitleId`字段。`FloatingSubtitleLanguageDiff`的57处记录位于Map1594的10个3.7实体。`UpdateSubtitle`的23处记录属于3.8内容，均没有建立B09调用关系。

任务114000031有154个实体Children、218个实体Reference，Children没有LevelPlay，六个玩法均为WeakReference。这些弱引用没有证明QTE后字幕的触发位置。

该线索已完成现有可解码配置范围内的核查。后续重开需要目标三维字幕的明确调用，或者这两个QTE的结果与继续播放映射。未带字段标签的二进制数字和资产内部引用仍不在此次结论范围内。

## B05条件路线

源状态为`剧情_尤诺线npc生态_5_1`，拥有者为Map8/Entity185750018。

|来源|SHA-256|
|---|---|
|flowstate|`18d1deab82a33da02272f7c867cd65ea8cec528ceb8a5e684d80948e273230ae`|
|拥有者实体|`fb5b6b608d61f88ca9474d9771d7b061de7e1971311a74e77869faca4d8cf8ce`|

证据脚本使用复制后的条件投影调用现有Exporter，检查原始数组顺序、JumpTalk、菜单索引、末尾控制和原始source_item。绿色与红色路线分别产生7句对白和1条选择。

|选择|路径中的TalkId|必要入口前提|局部结束|
|---|---|---|---|
|冰镇的雪酒|1、2、3、4、5、6、7|还剩大于0且喝绿的为false|显式FinishTalk|
|热煮的佳酿|1、2、12、8、9、10、11|还剩大于0且喝红的为false|数组末尾|

两条路线都检查到算术写入后的两句正文。各自的SetVar、CalculateVar和ChangeEntityState按源顺序记录。Map8下两个目标实体的已声明回调只有MeshActor可见性切换，没有额外文本回调。相同EntityId在Map1532也存在，必须带MapId关联。

初始化状态提供两种路线可满足的见证。实体可重复交互，三个合法入口状态没有共同可选项，因此初始化值仍不能用作当前回顾的变量值。该交互也没有新的必经任务锚点。

本轮将条件投影保留为研究证据。生产默认策略不增加假设，也不把条件路线计入已解除阻塞。未来若增加显式条件路线，需要独立记录入口前提、符号写入、当前状态未核验和局部完整性，并保留原阻塞口径。

## B01界面调度

只读扫描ConfigDB根目录515个数据库、1307462行，覆盖433795736字节BinData。检索大小写不敏感的Enrollment、Admission、StudentCard，并检查2201245881的原始32位字节与SQLite整数列引用。

Enrollment仍只命中原始flowstate，动作为`OpenSystemBoard(SystemType=Enrollment, BoardId=0)`。`AdmissionStudentCardView`仅命中uishow自身，候选PrefabPathHash2201245881仅命中8条prefabtextitem。

|来源|SHA-256|
|---|---|
|原始flowstate|`f7d127d3f1505457a84f721fefa4335052f52f1a6b7d127f3b1dba0aa84921f5`|
|AdmissionStudentCardView|`9cb36f79ead4691683ddd26d2974e1deeefa839b0f151030592560084b8ccee3`|

新增找到8条男女拍照姿势资源路径、相机界面资源、7项学生证富文本标记。它们没有给出本次动作的View映射或继续对白回调。uishow的field4值2同时用于253个View，不能解释为Enrollment的唯一枚举。

有效的下一项证据为OpenSystemBoard的Enrollment处理分支，包含实际ViewName、BoardId用途和继续对白回调。继续保留调用前1句与调用后25事件的既有范围说明。

## 复现记录

本地研究脚本和原始证据位于`work/float_call_trace.py`、`work/menu_reachable_probe.py`、`work/ui_dispatch_trace_probe.py`及各自JSON。work由Git忽略，克隆后可用本报告中的精确键、表、范围和哈希复查。

最新批次为`20261117_144506_357719`，135对JSON/TXT逐文件与基线完全一致，TXT均与JSON渲染一致。覆盖报告、输入哈希和阻塞报告一致。335项全量测试通过，用时156.842秒。结构与链接检查覆盖180个Python文件、113份Markdown。

批量产物与验证记录见根目录progress.md。原始数据库、资产和生产解析规则保持。
