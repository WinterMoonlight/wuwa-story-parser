# 捕梦于神秘园中：邮件调查与待核验导出

## 2026-11-17：《捕梦于神秘园中》邮件与调用顺序

QuestId=171000004，20节点、7段显式流程与回顾配置一致。节点6 EnterActions发送MailId250000，同节点Condition为ReadMail250000；祖先链6→5(AlwaysFalse)→2(ParallelSelect,Count=1)→1。节点2界面分别关联节点4与节点6，不按数字编号推定播放顺序，也不认定邮件阅读为所有路线必经。JSON记录quest_id、节点、阶段、动作索引、祖先条件和同ID阅读节点；正文仍按回顾配置排序，邮件放附录。

邮件调查：db_mail.db/mail的250000行仅20字节，FlatBuffer只有字段0=250000，没有发件人、标题或正文引用。扫描ConfigDB顶层表名/列名的mail相关项仅发现db_mail四表；检查zh-Hans/lang_mail.db的Mail记录及MultiText中邮件相关键，未发现可凭ID直接关联的正文。不能凭相似内容把通用/测试邮件配到此任务，也不能由此证明正文一定由服务器下发。现状态mail_body_unavailable_in_row，保留源行Base64与SHA-256。confirmed_missing_text_ids为空仅表示已解析文本键未缺失，不表示邮件正文已经恢复。

新增通用支持：SendNpcMail仅接受MailId参数并校验唯一源行，当前只识别ID-only形状，遇到新增字段拒绝，待调查后再扩展。支持Action节点的Actions阶段，不能只扫描Enter/FinishActions。HideGroup/ShowHidedGroup按核对过的形状保留为玩法假设。SetHeadIconVisible只影响展示，WhoId不用于更换说话人身份。保留HideUiExceptTaskList标记。

节点8 FinishActions：章节界面PromptQuestChapterUI(ChapterState=0,Timeout=10)→ShowHidedGroup→异步PlayFlow(1_5)→AwakeEntity；只证实配置顺序。节点17 Actions为TeleportDungeon905，位置171700000，TransitionOption指向PlayMp4/M0278。两者以独立未核验记录保留，未模拟传送，也未宣称章节界面或过场不含额外文本。

导出outputs/待核验任务/171000004_捕梦于神秘园中.json及TXT：71事件=58对白+13选择；13界面引用、3外部调用。保持女性分支和漂泊者姓名规则。JSON/TXT文本一致，status=needs_review，不能作为已完整恢复的任务。

34项测试通过；新增真实邮件归属、Action阶段、严格模式拒绝、缺失/重复/变更邮件结构、头像不改变身份测试。实际批量输出outputs/主线批量/20261117_003457_407439，主线2/85、补充0/50，无成功数提升。

下一步按计划核查《明日摇曳的绯影》的手机消息与场景切换。邮件正文250000、章节界面和M0278额外文本继续列为未决来源，不以猜测补齐。若后续获得同版本其他资源/协议配置，再根据明确ID补邮件关联。

复现：`python run.py export-task --quest-id 171000004 --allow-incomplete`；`python run.py export-mainline`。测试：设置`PYTHONPATH=src`后运行`python -m unittest discover -s tests -v`。
