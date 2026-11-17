# 第九轮：36000阅读步骤与后置世界动作

2026-11-17，3.8.11快照。基线20261117_124951_778402。三路核查动作参数、完成条件及回顾/调用顺序，主agent统一整合。27处阻塞、前缀及资产边界保持。

## 手机阅读位置

173000000《烟云幽远心剑鸣》节点2唯一发送36000，并要求同ID ReadPhoneMessage/CompleteMessage，TrackCustomBoard指向同一消息。节点TidTip唯一对应回顾entry0空Flow，祖先98→1是纯Sequence；没有失败、退出、并行或循环边界。可解码任务/流程JSON中未发现其他发送或显式打开引用。

消息共15事件，含3个选项、3个表情占位、1条系统提示，无缺失正文。精确手机流程未重复出现在回顾Flow条目。entry1仍是提示，首个回顾Flow3/1在entry2：手机应在自己的entry0独立显示，不放到3/1末尾，不用节点编号排序。

## 周围动作与边界

EnterActions先发送消息，再SetTime 10:00、ShowUi=false。FinishActions是CompleteMessage条件完成后的配置阶段：AwakeEntity、HideGroup、ChangeEntityState、UnlockTeleportTrigger、FocusOnMapMark、SetTime。将手机按提示定位不等于执行这些动作，也不证明它们引起的世界变化已完成。

精确实体核查：

- AwakeEntity目标173000021、173000022仅有NPC待机Montage表演；资产回调未核验。
- 目标173800323的TriggerComponent仅PreloadFlows玄方城3/1，预加载不是播放对白。
- ChangeEntityState目标693751151在Map8唯一行106625，匹配“关卡.Common.状态.激活”的行为，仅EnableNearbyTracking(false)、UnlockTeleportTrigger3520020、AwakeEntity空列表。PendingConditionAvailable保留，不模拟引擎执行。

HideGroup的范围实体173800007在Map8/1601存在重复ID；本轮只记录范围参数形状，不选择实体行、不宣称范围实体或隐藏回调已验证。它属于阅读完成后的世界上下文，不作为恢复任何间接对白的依据。实体唯一审计仅用于AwakeEntity与ChangeEntityState的明确目标。

## 通用规则

phone_world_context只服务于手机回顾提示定位，不加入全局忽略动作白名单。精确校验动作字段、值类型、同步形状和进入/完成阶段。SetTime仅支持无UI合法时刻；实体唤醒/改状态必须唯一匹配实体数据、嵌入字段一致，并审计组件与对应状态回调；未知字段、真正PlayFlow/文本调用、目标缺失或多义一律拒绝。

phone_tip_anchors原有唯一提示、同ID完整阅读/发送/跟踪板、无重复引用等守卫保留。新proof.surrounding_action_evidence保留7个世界动作及实体源配置/哈希，post_read_world_effects_simulated=false。手机区段只含15个原消息事件；不追加或推演世界动作的间接正文。

原external_content证据保留，TXT与计数不重复；27个blocked回顾区段对象不改，有序前缀不算完整。没有实体数据source时拒绝新增实体操作支持，不能因调用端未提供库而跳过审计。

## 测试与证据

测试覆盖无UI时间边界、异步/未知字段拒绝、阶段限制、实体歧义和真正PlayFlow回调拒绝、真实7动作证据、36000回顾位置及源事件顺序。旧第八轮36000拒绝测试调整为“缺少实体审计源时仍拒绝”，保留原拒绝意图。

本地详细证据：work/round9_actions.md、work/round9_conditions.md、work/round9_order.md及对应probe/实体摘要。最终批量结果见下节。


## 最终验证

第九轮36000核查完成：279项全量测试通过（117.372秒），批次20261117_125513_437599核对135对JSON/TXT。烟云幽远心剑鸣36000的15事件按回顾entry0归位，7个周围世界动作及实体审计留JSON，不模拟后置影响。累计4条手机区段40事件归位，不是新台词或完整任务。2634个回顾流程段、27处阻塞、3段30事件前缀、68次实体候选保持，严格通过仍2；资产未动。

- 最新产物：outputs/主线批量/20261117_125513_437599/覆盖阅读版，含覆盖报告、剩余阻塞报告及产物核对.json。
- 对照基线，原回顾segments与主干events逐对象相等；原三个手机区段位置与事件保持，新增36000 entry0的15事件。
- TXT逐份与JSON阅读渲染一致，旧可见文字保留；每任务计数总和不变，已归位消息不在附录重复计数。
- 27处阻塞报告及68次实体候选逐对象相等；前缀不升级，严格通过2、132任务有文字等整体状态不变。
- 代表JSON/TXT在outputs/第九轮36000核查；新增4项测试，全量通过。未提交或推送仓库。

下一步继续寻找其他可证锚点；不把世界上下文审计扩成运行时模拟，不借成就任务条件排列主线，也不以区域窗口代替实体播放顺序。
