# 客户端场景动作配置核查

本说明记录独立核查结果，整合后的测试与批量收益见项目进度。

## 范围与数据

在可解码flowstate中定位ClientPreEnableSubLevels 17次、GiantToggleModel 12次，原调用集合为work/config_actions_evidence.json。29次外层均仅Name、Params、ActionGuid、ActionId，没有显式Async或回调列表。

ClientPreEnableSubLevels中16次仅EnableLevels/DisableLevels路径数组；1次另含TransitionOption={Type:SceneCapture, DelayTime:1.5, SceneCaptureEffect:/Game/...}。列表可为空，出现美术、灯光和音频关卡路径。不能根据路径名称断言被启用资产不携带文本或事件。

GiantToggleModel 12次参数均只含IsEnabled布尔值。部分调用位于ShowTalk的帧事件，部分位于后续顶层动作。读取正文不应模拟这些调用完成，更不能把帧事件强制挪到对白前或后作为已核验时序。

## 通用边界

client_scene_effects模块仅校验已观察到的显式形状。非/Game/路径、未知字段、异步、嵌套回调均拒绝。SceneCapture仅允许Type/DelayTime/SceneCaptureEffect，DelayTime必须有限且非负数，布尔值不当数值；未知过渡类型拒绝。

调用只在阅读模式记录，仍保留callbacks_verified=false、asset_content_verified=false、runtime_completion_verified=false。子关卡调用另记wait_semantics_verified=false。过渡DelayTime不是加载完成时间，也不是有证据的同步等待标记。

## 代表流程

- 158800019《暗潮将映的黎明》：剧情_2_7_狄斯台地主线_上半_巡游天国_6_1的过渡调用位于第7个顶层ShowTalk、第16个TalkItem的Actions中；1/18是基本形状，位于两组ShowTalk之间。
- 121000040《昨夜群星》：剧情_3_3_拉海洛主线_上半新_7_2在ShowTalk前后禁用/启用同一关卡，保持源数组排列。
- 886000002《梦枢心相由心生》：梦枢天罗10/1、2/4、2/12、3/5当前首个阻塞为GiantToggleModel。10/1的禁用在帧事件中，启用在后续顶层动作，不证明具体帧时序。

不会以动作名称把未知字段一并放行，不涉及LockEntity/UnlockEntity或变量状态计算，不下载或修改资产。
