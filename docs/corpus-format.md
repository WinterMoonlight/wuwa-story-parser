# TXT 与 JSON 语料格式

每个任务通常生成一对同名文件。TXT 是主线阅读稿，JSON 同时保留正文、选项、动作和来源。查看[虚构 TXT 示例](../examples/minimal-story.txt)和[简化 JSON 示例](../examples/minimal-story.json)。

## TXT 怎么读

TXT 通常包含选定路线上的对白、玩家选项、旁白和需要展示的资料。女性分支和玩家名“漂泊者”是阅读版的显示策略，原模板保存在 JSON。文本缺失和暂略的演出、交互会在原位置给出短提示。可选交谈按有依据的阶段插入并加标记。

## JSON 从哪里取正文

| 字段 | 内容 |
|---|---|
| `quest_id`、`title`、`classification` | 任务身份及批量导出的章幕归属 |
| `source` | 原任务定义、任务节点、流程哈希和配置证据 |
| `events`、`route` | 受支持任务路线的事件、选项和运行假设 |
| `recap_backbone` | 任务回顾条目、每段事件以及缺失或被阻塞的段落 |
| `chapter_recap_order` | 总回顾关联出的原任务次序、提示和流程位置 |
| `task_local_sequences` | 段内有序的局部片段及其调用证据 |
| `external_content` | 手机消息、资料、玩法、媒体等引用与候选文字 |
| `validation`、`batch_coverage` | 已知缺口、提取范围、候选和阅读顺序证据 |
| `mainline_reading` | TXT 实际展示的文字和指回源记录的路径 |

`schema_version=1` 用于单显式流程结果，`2` 用于已支持的多场景回顾路线，`3` 用于覆盖导出的审计草稿。不同命令或任务会有不同可选字段。覆盖草稿的顶层 `events` 可能为空，正文也可在 `recap_backbone` 或局部片段中。

## 从一行阅读稿找到配置

`mainline_reading.blocks[].parts[]` 保存显示文字及 `source_pointers`。例如，`/recap_backbone/segments/4/events/2` 指向第五个回顾段的第三个事件。数组索引从 0 开始。由多个事件折叠成一条略过说明时，指针会保留这些来源。

对白事件通常包含 `text_id`、`state_key`、`talk_id`、`raw_text` 和 `source_item`。显示名和身份依据由 `display_name`、`name_source`、`identity_status` 等记录。选项事件另外保存 `choice_key` 和 `selected_index`，对应 `route.choices` 中的原选项。长期引用可组合任务 ID、流程键、文本键和回顾位置。

## 补位和缺口证据

- `recap_backbone.order_source.entries` 保存原回顾。补位、校正和局部片段可分别记录在 `current_task_continuation`、`dependency_order_corrections` 和 `local_fragments`。
- `current_task_continuation.placement` 记录采用的任务节点、源动作以及前后锚点。已核对属于可选交谈的段落会保存相应标记。
- 从章节总回顾恢复的单任务正文放在 `chapter_recap_order.flow_entries[].recap_segment`，并保留原任务的触发条件。
- 演出、界面和 QTE 的未核验范围记录在事件或 `unverified_content`。流程资源缺失时，保留原状态键、错误和回顾位置。
- `runtime_verified=false` 表示运行时仍待核验。阅读稿状态、严格通过和人工验收的含义见[阅读状态与覆盖报告](coverage-reading.md)。

具体规则见[任务节点与对白选择](selection.md)和[专题研究](research/README.md)。
