# 明日摇曳的绯影：手机与场景配置核查

## 2026-11-17：《明日摇曳的绯影》手机正文与场景切换

QuestId165800001，10节点，两段显式剧情回顾。任务成功节点3的FinishActions先ShowHidedGroup，后PhoneSystemInteract/SendPhoneMessage32010。手机正文不在这两段回顾内，不能只靠回顾覆盖率认定任务文本齐全。

关联链（2026-11-17纠正）：shortmessage.Id32010的字段1=3是联系人ID，关联chatpartner3/洛瑟菈；字段2是[剧情_3_2_拉海洛主线_下半,16,1]。此前把字段1当类型、字段9误读为联系人48/赞妮是解码错误，已修复并重新导出样本，见phone36009-decoding.md。

新增phone.py：仅接受已核对的SendPhoneMessage结构和类型3，唯一引用检查；独立复用对白、选项及全分支引用检查，保留phone.events/route/talk_groups/action_trace、源行Base64、源表/字段与哈希。独立实例防止联系人或匿名演员绑定污染正文。联系人不覆盖每条消息的WhoId身份。手机文本缺失进入任务统一统计；平台读取时刻、通知与回复时刻未模拟。严格未知类型继续拒绝。

手机附录包含12条对话、2次选择；正文53对白+6选择=59事件，两者不混排。玩家名和女性分支统一规则沿用。节点3成功阶段发送不等于即时阅读，read_time_verified=false。

场景：节点19条件要求进入2518；节点14声明DungeonId2518/DisableOnline，节点16归属其下。节点16 EnterActions先FadeInScreen再SwitchSubLevels，加载Instance_Litang_Light、卸载Light_01/02；FinishActions先TeleportDungeon906(LocationEntityId165800064，FadeInScreen过渡)再FadeOutScreen。保留父链副本字段、原始条件及局部顺序，不声称已运行全局任务图。HideGroup增加SpecifyEntity形状，其他未知结构仍拒绝。节点15WaitTime为1天，保留配置，不实际等待。

产物outputs/待核验任务/165800001_明日摇曳的绯影.json及TXT：59正文事件、14手机事件、6界面引用、4外部调用，已解析文本键无缺失，仍标needs_review。JSON/TXT正文及手机文本一致。

37项测试全部通过，涵盖真实手机归属、独立流程、联系人、缺失/重复引用、未知类型与缺字向任务统计传播。实际批量outputs/主线批量/20261117_003733_854027：主线2/85、补充0/50。下一步按原计划核查《铁锈，剑与烈阳》的小游戏文本及变量对路线的影响；手机通知/阅读时刻、完整UI及运行时切换继续保留未决。

复现：`python run.py export-task --quest-id 165800001 --allow-incomplete`；`python run.py export-mainline`。
