# FlowDefineNpcGroupPerform参数与回调核查

## 来源

在可解码flowstate动作中找到19次调用，4组参数：Type=0/Key=qianshou1共13次，Type=1/空Key共4次，Type=7/chanfu共1次，Type=0/chanfu共1次。动作只携带PerformType.Type/Key；检查调用中没有嵌套对白、条件或回调列表。

另检查db_NpcGroupPerformConfig.db：npcgroupperformconfig含Id、PerformMark、PerformType、RoleId、NpcType、BinData。现有6行PerformType均为5，BinData未提取到嵌入JSON。不能用相似名称或枚举数字推定与本次Type0/1/7的关系，也不能由调用没有回调字段就断言引擎不存在隐式回调。资产及运行时行为留待后续核验。

## 通用规则

仅阅读模式接受Type=0且Key为非空字符串，或Type=1且Key为空字符串；Type=7未知语义保留。参数只许PerformType，其内部只许Type和Key。外层仅Name、Params、ActionId、ActionGuid、Async，异步与其他字段拒绝。

调用留在action_log和npc_group_performance记录中，callbacks_verified=false。按现有顺序继续读取对白，不把Key当台词，不改变说话人、选项或跳转。严格模式仍拒绝。组合选项的原有检查不放宽。覆盖报告使用相同形状校验，已支持形式不再误报未知动作。

## 代表任务

886000001《今夜，注定属于月亮》60段成功/12阻塞→66成功/6阻塞。恢复6段共84事件，替换6条缺口，总事件530→608。

仍阻塞：生态条件对白1段、SetVar4段、SwitchSubLevels1段。特别是混沌之间2/5虽然本轮表演调用已能读取，末尾子关卡切换仍未支持，因此没有冒充整段完成。

原有回顾位置、动作和对话选择控制顺序不变；未知资产不会补造正文。

[JSON](../outputs/回顾主干验证/886000001_今夜，注定属于月亮.json) · [TXT](../outputs/回顾主干验证/886000001_今夜，注定属于月亮.txt)

最终验证：131项测试通过；批次20261117_021648_403941核对135对JSON/TXT，3任务恢复8段、97事件，既有成功事件和静态文字保留、渲染一致，《来自毁灭的回声》不变。有回顾阻塞任务37→36，未知流程动作任务59→58。任务分类不变，不新增完整任务。

[覆盖报告](../outputs/主线批量/20261117_021648_403941/覆盖阅读版/覆盖报告.md) · [产物核对](../outputs/主线批量/20261117_021648_403941/覆盖阅读版/产物核对.json)

后续更新：Type7现已支持配置阅读，精确枚举语义仍未确定；见[Type7核查](npc-type7-validation.md)。以上为最初Type0/1核查时的历史结果。
