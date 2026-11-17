# 《来自毁灭的回声》演出文本来源核查

2026-11-17。当前仍为90/92段、986个主干事件。此次没有新增可确认的字幕正文；两处缺失流程6/17、6/3保持原位缺口。

## 已确认的来源

|调用|当前证据|可得出的结论|
|---|---|---|
|PlayMovie M0248|videodata女性条目168；videocaption共13行；四组数值轨排序一致|13条配置字幕已保留在调用位置，不推断字幕说话人及绝对时间|
|PlayMovie M0242|videodata女性条目160；无videocaption行；有videosound行51|知道媒体和音频引用，不知道是否另有对白，不能声明没有字幕|
|4次PlaySequenceData|完整DA资产路径与调用参数|当前无资产属性导出，不能还原轨道、字幕或依赖资产|
|4次OpenSystemBoard|InformationView及103000005—103000008|这些是信息面板，不是视频；正文仍待独立解析|

M0242、M0248的音频事件分别为play_sequence_music_sfx_vo_m0242、play_sequence_music_sfx_vo_m0248。音频事件名不等于字幕键，不能凭名字或相似文本拼接对白。videosound性别码保留原值2，未自行解释或替代女性videodata选择。

## 检索范围

扫描515个根目录数据库的TEXT及BLOB字节，按4个DA资产名及两个视频名取得47处字段命中。DA名称只在相应flowstate调用中命中；M0242/M0248还在媒体、声音、回顾图片等表出现。db_custom_sequence未发现这些DA名称。

项目的work/asset_exports/properties当前只有M01012_Nvzhu.json，并非本任务资产。检索不覆盖尚未导出的游戏资产或任意压缩/加密的外部资源，所以“当前没有来源”不能表述为“游戏没有正文”。

[机器证据与来源清单](../../outputs/回顾主干验证/演出来源核查.json)包含每次调用、命中表/行、库哈希、已有属性文件及待补资产。

## 通用规则更新

- PlaySequenceData只按完整资产路径与videodata字段4精确关联，不按同名文件、数字编号或路径片段猜配。只有唯一女性条目才能复用既有字幕解析。
- source_resolution保留精确匹配、属性文件存在状态和期望位置；属性文件存在也不代表内容已解析。当前4个DA都没有媒体表精确关联。
- inspect_movie保留videosound来源和哈希，text_decoded=false；有音频引用不代表已读到文字。silence_verified始终不因字幕零行而变为true。
- TXT分别显示演出来源待核实与信息面板正文未解析。技术路径和状态留JSON；M0248的13字幕继续显示，不能作为本轮新增字幕统计。

## 继续核查需要的属性文件

先导出下列对象的属性JSON，不需要先导出整个视频。FModel中 `/Game/Aki/` 对应此项目已见的 `Client/Content/Aki/`。将属性JSON放入 `work/asset_exports/properties/`，保留对象名；解析它们后，再根据真实引用决定所需轨道、Sequence或字幕依赖，不能预先猜出全部依赖。

|优先级|FModel目录（Client/Content/Aki/之后）|对象/期望文件名|
|---|---|---|
|需要|Sequence/Level/HHA/HHA_SceneChange|DA_HHA_SceneChange.json|
|需要|Sequence/Level/HHA/HHA_SceneChange|DA_HHA_SceneChange_02.json|
|需要|Sequence/LevelA_Seq/POI/01_3/P0003|DA_P0003.json|
|需要|Sequence/LevelA_Seq/Function/01_3|DA_01_3.json|
|需要|Sequence/LevelA_Seq/Main/01_3/M0242|M0242_Nvzhu.json|
|可后补|Sequence/LevelA_Seq/Main/01_3/M0248|M0248_Nvzhu.json|

若对象属性显示媒体地址，只把它当定位依据；如果是Sequence/DataAsset，沿属性中真实引用继续找。不能保证导出这5份后就能获得所有文本。M0248已有配置字幕，因此其媒体属性不必阻塞其他正文工作。

## 验证与产物

109项测试通过。新增测试验证完整路径匹配、同名不同路径拒绝、歧义拒绝、M0242零字幕不推断静音及M0248的13字幕。

最终批次20261117_013837_207359：135任务，12配置路线、1部分有序、60回顾主干草稿、62仅候选；132有文字，严格2/85和0/50保持。135对JSON/TXT核对通过，正文、选择与缺口位置不变，静态文字保留，计数与渲染一致。两处缺失流程未改动。

- [新版TXT](../../outputs/回顾主干验证/145000004_来自毁灭的回声.txt) / [JSON](../../outputs/回顾主干验证/145000004_来自毁灭的回声.json)
- [覆盖报告](../../outputs/主线批量/20261117_013837_207359/覆盖阅读版/覆盖报告.md)
- [产物核对](../../outputs/主线批量/20261117_013837_207359/覆盖阅读版/产物核对.json)

下一步需要上述真实资产属性才能继续核查DA轨道或M0242媒体来源；在补齐之前，可以独立推进InformationView正文映射或任务额外流程归位。不要重复猜配两处冻结流程。
