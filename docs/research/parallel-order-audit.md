# 并行回调与顺序核查（2026-11-17）

## 范围与结果

只核查本地同版本 QuestData、QuestNodeData、PlotHandBook 中的配置依赖，不请求或修改资产。没有把 ParallelSelect、AlwaysFalse、距离范围或者相同父节点当作全局时间顺序。

扫描全部任务发现 244 个“完成条件为 PlayFlow 且完成动作再次调用 PlayFlow，或同一完成动作列表含多次 PlayFlow”的节点。限定任务 Type=1/15，19 个任务存在 36 对相邻同步 PlayFlow（省略 Async 或显式 false）。这是配置调用局部关系，不能证明节点一定执行，也不能证明已等待其他并行分支结束。

## 代表证据

- 139000030《奔策候残星》节点 116：相邻调用 1/38→1/26。回顾的流程出现位置（仅对流程计数、零起算）分别为 [17] 与 [10,18]。重复 1/26 有独立出现意义，不能取首个或最后一个覆盖映射而声称完成了调用关联。
- 140000011 节点 71：4/21→4/22，前者不在回顾，后者在回顾；前者是纯画面文字，现有 task_extras 已有合适的唯一同步锚点处理，本轮没有另插一次。
- 114000026 节点 114、123、130：均存在 1/1→10/1；1/1 在回顾而 10/1 不在。存在多调用归属，不能仅凭同名流程挑一个调用放回正文。
- 本批 36 对调用没有两端均唯一出现而反向的回顾关系。

证据完整副本：work/audit_parallel_calls.json 与 work/audit_parallel_pairs.json。后者仅保留相邻同步调用与回顾位置，前者保留节点和回顾配置。

## 通用模块

新增 src/wuwa_story/dependency_positions.py，已由主 agent 接入 dependencies.py 和批量报告的 order.dependencies。

- adjacent_sync_dependencies(nodes)：仅直接 ChildQuest 的 FinishActions 中相邻两项均为精确 PlayFlow 时生成局部边。只允许 Name、Params、Async、ActionId、ActionGuid；Params 仅 FlowListName、FlowId、StateId；FlowListName 非空字符串、数值为正整数，拒绝 bool。Async 必须省略或严格为 false。额外 Condition/Callback、间隔动作或非 ChildQuest 均不推断。
- 边表达前一同步调用完成→下一调用发起，以“同一次激活确实走到这两个调用”为前提，runtime_executed=false、global_order_verified=false。不等于并行完成回调解析。
- dependency_positions(edges, ordered)：返回 conflicts、unresolved、consistent。只有两端不同、分别唯一出现才比较索引；反向才进入 conflicts。任何一端未出现、重复出现或相同引用对应两次调用均进入 unresolved，并保存完整 from_positions/to_positions。
- 即使 consistent 也只是局部边与回顾相容，不提升全任务验收。不能让新增未定位依赖直接排列正文或删除重复段。

## 验证

新增 tests/test_dependency_positions.py，5 项测试通过：唯一逆序与正序、重复与缺失、异步及未知字段反例、显式 false/元数据，以及实库 139000030 的 [17]→[10,18]。

命令：`$env:PYTHONPATH='src'; python -m unittest discover -s tests -p test_dependency_positions.py -v`。

整合保留原 conflicts 对外字段名，新增 unresolved 与 consistent 独立字段；不把 unresolved 当作通过。原有同节点条件完成边也应使用该函数，避免字典末次覆盖出现位置。批量输出与全套测试由主 agent 统一执行。


## 整合补充

回顾来源不是唯一记录/数组时，不能将拼接后的位置判为已一致或已冲突，改记 ambiguous_recap_order_source。存在未定位依赖或冲突时，selected_route_verified 不得为 true。回顾段内文本顺序与全任务运行顺序仍为不同概念。

当前批量新列出《荣耀暗面》125000125：节点117的条件完成流程8/3→完成动作8/1，而回顾位置为32→30（仅计流程，零起算）。这是局部关系与回顾之间的冲突，不据此自动调换正文。TXT保留简短待核验说明，下一轮查调用归属与回顾用途。
