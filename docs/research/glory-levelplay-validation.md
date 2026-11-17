# 荣耀暗面：LevelPlay146850003归属与调用核查

2026-11-17，ConfigDB 3.8.11。任务125000125《荣耀暗面》确认新增四句玩法对白，放在附录；没有新的充分证据将其插入有序主干。资产问题保持原状。

## 任务归属

QuestData.Children声明`l_8_146850003`，LevelPlayData中唯一记录的Id=146850003、LevelId=8与之吻合。

任务节点125的Condition是CheckLevelPlay，LevelPlayIds=[146850003]、CompleteNumber=1。EnterActions启用该玩法，FinishActions禁用；它位于Sequence207下，外层ParallelSelect205的SaveConfig另有重连恢复时禁用玩法的动作。这些配置证实关联，不代表玩法每个节点都执行一次。

该节点TidTip在回顾条目21出现一次（零起算）。后接副本玩法3/2，而3/2是包含M0269视频调用的流程。提示可将内容关联到祭坛阶段，却不能直接决定异步对白的完成时刻。

## 四句正文和原始调用位置

| 流程 | 调用位置（动作下标从0起） | 正文 |
|---|---|---|
| 副本玩法_上3/1 | 节点6，FinishActions[2]，Async=true；条件为ReachArea | （藏身在那甬状的实验装置中吗？） / （必须破坏周围的管线，让它坠落下来。） |
| 副本玩法_上3/4 | 节点38，Actions[2]，Async=true；配置描述“斩击完成” | （这些机关，恐怕是建造这处实验场的人设置的防御装置。） |
| 副本玩法_上3/5 | 节点65，Actions[5]，Async=true；配置描述“斩击完成” | （察觉到部分设施被我破坏后，防御装置的攻击频率也上升了。） |

另外节点7在FinishActions[2]异步调用`剧情_2.4_祭坛_1_1`。此流程包含DA_P0021演出调用，没有ShowTalk正文；此次只记录来源，不继续追查资产。

副本玩法3/6没有出现在本玩法的显式PlayFlow调用中，不能仅因编号相近补入。同名任务125000126声明的LevelPlay125000006也不属于本次精确声明范围。

## 为什么暂不放回主干

- 本组节点提供ParentNodeId，没有可直接使用的显式Children排序；不按节点Id、数据库行顺序或描述中的“第一圈/第二圈”推断执行次序。
- 存在ParallelSelect、Repeater、QuestFailed，以及超时、角色切换、实体状态、死亡/传送失败等条件，尚未构成一条经过验证的成功执行路线。
- 三处正文都是异步调用，后续节点继续推进不等于前一段对白已播放完毕。唯一阶段提示也不是具体对白锚点。
- 任务原有8/3→8/1与回顾相冲突的问题独立存在，本轮没有改变该诊断。

因此新增主干插入0处。四句单列为“任务场景玩法对白：归属有配置依据，触发及与主干的先后尚未核验”。附录排列不代表运行时先后。

## 通用实现

`declared_levelplay.py`精确匹配QuestData.Children的地图/玩法声明与唯一LevelPlayData定义，读取对应LevelPlayNodeData。拒绝重复节点、定义地图不匹配、节点Key/Id不匹配、冲突JSON字段；无效祖先链不用于产生调用关联。

仅提取节点顶层Actions/EnterActions/FinishActions中具有完整三元组的PlayFlow引用；不把SaveConfig、FixProcessor及其他嵌套回调展开为正常剧情。完整定义和节点仍保留在JSON，未识别流程不假装执行。

JSON的batch_coverage新增declared_levelplay_links与declared_levelplay_audit：记录调用节点/动作下标、Async、祖先、原始条件和来源SHA256。source_counts新增declared_levelplay_candidate_occurrences。候选记录用reading_context=declared_levelplay_candidate，不提升selected_route_verified，不修改回顾引用集合或严格模式。

范围限制：暂不递归玩法Reference、子实体、嵌套回调；不模拟玩法成功/失败和恢复路径，不凭任务声明推断必经。

## 验证与导出

195项测试通过（43.808秒）。新增测试覆盖错误地图、仅Reference不算声明、重复节点、循环祖先、SaveConfig不混入正常调用，以及实际任务四句附录、回顾32段可解析/2段阻塞/328事件保持。

最终批次`20261117_105258_445773`：135对JSON/TXT核对通过。相对上一批，29任务新增855次候选文本；原2596个已解析段落、正文与选择、既有文本记录、外部内容和资产均保持，全部TXT与JSON渲染一致。严格通过2，回顾阻塞29任务65处，新增整任务验收0。

样本：[TXT](../../outputs/玩法归属核查/125000125_荣耀暗面.txt) / [JSON](../../outputs/玩法归属核查/125000125_荣耀暗面.json)。批量：[覆盖报告](../../outputs/主线批量/20261117_105258_445773/覆盖阅读版/覆盖报告.md) / [核对记录](../../outputs/主线批量/20261117_105258_445773/覆盖阅读版/产物核对.json)。这些游戏文本产物不随Git提交。

```powershell
$env:PYTHONPATH = 'src'
python -m wuwa_story.recap_backbone --quest-id 125000125 --output outputs/玩法归属核查
python -m unittest discover -s tests -v
python run.py export-reading-batch
```

下一步从玩法候选中筛选具有明确同步调用和排序证据的案例；本任务四句维持单列，避免反复用同一阶段提示猜顺序。
