# SwitchSubLevels参数与同步边界

## 配置解析

核查flowstate中的43个SwitchSubLevels调用。载荷为Type=Directly、LoadLevels与UnloadLevels路径数组，可含TeleportEntityId和IsWaitForSwitchComplete。加载/卸载列表可为空，必须保留原数组，不能根据路径名重排。传送引用只记实体ID，不推测坐标或新增对白。

新增sublevels模块验证字段类型、/Game/路径、布尔等待标记。仅阅读模式、Async缺省或false允许；未知字段、嵌套动作、非Directly和异步拒绝。严格模式不变。

## 同步边界

IsWaitForSwitchComplete=true只能证明配置要求等待，不能证明实际加载成功。false为显式不等待；字段缺省的默认语义没有证据，记为null且wait_flag_present=false。外层未设置Async不能替代内部等待标记。

JSON保存加载/卸载列表、传送ID、等待标记、原始动作及streaming_completion_verified=false、callbacks_verified=false。后续文本按源动作数组与对话控制流排列，不宣称子关卡资源加载或隐式回调在下一句话前完成。未加载的地图资产是否带额外对白仍未核验，不补造。

## 代表任务

915000005《烟云幽远心剑鸣》80段成功/6段阻塞→84成功/2阻塞，恢复4段65事件，总事件453→514（替换4个缺口）。已解析正文保持原回顾位置、说话人和选择规则。

剩余心魔幻境53/1为未支持的NPC表演Type7，36/1为StopUiScreenEffect；均保留，不一并放行。资产依旧放到最后处理。

[JSON](../outputs/回顾主干验证/915000005_烟云幽远心剑鸣.json) · [TXT](../outputs/回顾主干验证/915000005_烟云幽远心剑鸣.txt)

最终验证：133项测试通过；批次20261117_021838_826455核对135对文件，3任务恢复7段、208事件，既有成功事件及静态文字保持，渲染一致，《来自毁灭的回声》不变。任务分类和有阻塞任务数不变，不新增完整任务。

[覆盖报告](../outputs/主线批量/20261117_021838_826455/覆盖阅读版/覆盖报告.md) · [产物核对](../outputs/主线批量/20261117_021838_826455/覆盖阅读版/产物核对.json)

实际观测等待字段：42次省略、1次true；测试另覆盖false，不将缺省折算为false或true。
