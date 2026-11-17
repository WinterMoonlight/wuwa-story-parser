# Enrollment与变量条件边界复核

2026-11-17。基线为20261117_141230_051601，三名子agent分别核查Enrollment界面、尤诺变量条件与千夏状态退出，主agent统一实现。

## 结果范围

本轮保持14任务23次回顾阻塞，精确去重21项。没有把已知前缀或条件性的后续片段算作完整解析。

《今夜，注定属于月亮》新增菜单前2句有序对白。《冰原下的星炬》新增界面调用前1句有序对白，并将调用后的25个对白及选择事件整理成独立配置片段。已有静态材料得到局部阅读顺序，未发现新的数据库台词。

## 条件菜单

尤诺实体Map8/185750018的初值为两个饮用标记false、剩余数量2。按已声明饮用动作可形成4种本地状态，其中3种允许再次进入。任务声明该实体，但没有指定回顾发生在首次进入，不能把初值当成当前值。

菜单的两个选项均有PreCondition。新增pending_boundary只提取首次未知菜单之前的连续普通对白，边界项自身对白也保留。该范围无动作、选项或条件。菜单原条件、原始source_item、后续CalculateVar与实体动作均保留，条件未求值，选项未选择。

原来的CalculateVar报错提前遮住了条件菜单。本轮报告首错为Conditional menu availability is unknown，分类继续为variable_state，并说明后续算术和实体动作仍待核查。

拒绝异步或未知回调、复杂TalkSequence、未知条件形状、前段跳转/动作、重复ID、缺少前文文本，以及存在明确无条件选项的菜单。严格解析入口保持原有拒绝行为。

## Enrollment

Enrollment/BoardId0仍未找到精确界面映射。新查到AdmissionStudentCardView与Activity30/Admission的8条Prefab文本，只作为候选证据，未写入界面正文。

调用所在Talk1先显示普通对白，随后打开界面，其唯一选项无条件且没有动作。新规则保存调用前1句，并在原位写明界面正文和返回关系未知。

整个ShowTalk的其余控制仅普通JumpTalk/FinishTalk，无变量与条件，两个显式分支都可得到完整局部配置序列。因此界面后25个事件放入local_fragments，范围为configuration_after_unresolved_ui，实际返回未知、整段完成false。TXT在同一段以明显标题分开显示，覆盖报告将其归unverified。原始同源材料避免在附录重复展示。

多次未知界面、选项带条件/动作、图循环、坏跳转、未知动作或顺序元数据均拒绝这种片段提取。该规则没有将Enrollment加入无效果动作清单。

## 千夏默认分支

ShowTalk没有TalkSequence和SequenceTransitions。默认分支SetVar、FadeInScreen、FinishState后仍有顶层清理动作，无法证明其后的控制返回行为。全库存在FinishState后还有动作及对白的配置，不能直接等同FinishTalk。

保留默认17事件前缀及缺口。此前显式选择“晚点再说吧”的18事件备选仍可导出。

## 验证与来源

|流程|状态源SHA-256|
|---|---|
|尤诺5/1|18d1deab82a33da02272f7c867cd65ea8cec528ceb8a5e684d80948e273230ae|
|Enrollment1/15/1|f7d127d3f1505457a84f721fefa4335052f52f1a6b7d127f3b1dba0aa84921f5|
|千夏9/14|e8372cd283326f3fd0db54b5f695465d6423c8503bac79941fe9e51ec16e8d4f|

新增测试覆盖首未知菜单、原始source_item、严格模式、跨ShowTalk相同ID、界面前缀/片段分离、异步/条件/坏跳转拒绝及覆盖分类。

331项测试通过，新增7项边界测试。最终批次为20261117_142003_983579，135对JSON/TXT逐份匹配，2638个原已解析区段逐对象保持。只有915000001与886000001两份TXT变化，输入哈希和原可见文字保持。产物核对.json记录详细对照，代表文件位于outputs/界面与变量条件核查。

详细只读取证在work/focus_enrollment.md、work/focus_variables.md、work/focus_state_exit.md及各自probe和JSON。

原始数据与资产未修改。后续若要消除这些阻塞，需要界面精确映射/返回关系、当前变量状态或状态结束的新证据。
