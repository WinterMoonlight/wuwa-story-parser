# 镜头与朝向动作阅读支持

继续优先解析已有配置和文本顺序，资产及实际镜头时序不作为本轮前提。

## 清点与范围

flowstate可解码动作中PlayerLookAt共86次，其中85次为Pos和CameraMove，1次还有PlayAnimation。RestorePlayerCameraAdjustment共41次，39次空参数，另2次含ResetFocus曲线。ResetPlayerCameraFocus共6次，均为FadeInTime和ResetType.Type=ResetToDefaultDirection。另有43次AdjustPlayerCamera，复杂参数本轮不放行。

新增camera_effects严格校验，支持：

- PlayerLookAt：精确Pos(X/Y/Z有限数值)、CameraMove布尔值。
- RestorePlayerCameraAdjustment：空参数。
- ResetPlayerCameraFocus：非负有限FadeInTime、精确默认方向类型。

动作外层只允许Name、Params、ActionId、ActionGuid、Async，Async只能缺省或false。额外字段、动画参数、曲线、复杂镜头调整仍拒绝。仅阅读模式支持；严格模式不变。

## 顺序处理

动作按原数组处理，保存action_log与camera_effect证据，不生成台词、不改说话人、不选择分支、不修改相邻对白顺序。对选项和组合动作的旧限制保持。覆盖报告复用相同校验，已支持形状不再误报未知动作。没有任务ID特判。

这表示可以忽略镜头运行本身读取配置正文，不表示证明摄像机播放完成时间、对象朝向或隐式回调。资产仍可原位留缺口。

## 代表任务

125900000《往岁乘霄醒惊蛰》从56段可解析/14段阻塞变为67段可解析/3段阻塞，恢复11段，事件474→733（原缺口被实际事件替换）。继续保留LockEntity、复杂PlaySequenceData与缺失流程三个阻塞，不一并跳过。

[JSON](../outputs/回顾主干验证/125900000_往岁乘霄醒惊蛰.json) · [TXT](../outputs/回顾主干验证/125900000_往岁乘霄醒惊蛰.txt)

## 批量验证

126项测试通过。批次20261117_021009_480136核对135对文件，11任务恢复33段、662事件，旧事件与静态文字均保留，渲染一致。未知流程动作任务72→60，有回顾阻塞任务42→39。任务分类不变，不新增完整任务。

[覆盖报告](../outputs/主线批量/20261117_021009_480136/覆盖阅读版/覆盖报告.md) · [产物核对](../outputs/主线批量/20261117_021009_480136/覆盖阅读版/产物核对.json)
