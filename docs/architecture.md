# 项目架构

## 数据流

```text
ConfigDB只读快照
  → 数据库解码与文本/姓名索引
  → 任务、回顾、流程及外部内容关联
  → 所选路线或回顾草稿与候选材料
  → JSON证据与TXT阅读版
  → 绑定源哈希的阅读验收
```

## 模块分组

源码包保留既有 `wuwa_story.*` 导入路径。下表按职责定位模块。

|职责|主要模块|
|---|---|
|程序入口|`cli.py`、`__main__.py`、根目录`run.py`|
|路径与数据|`paths.py`、`database.py`、`inventory.py`、`index.py`|
|任务和流程|`export_task.py`、`coverage.py`、`variables.py`、`conditional_recap.py`|
|批量与回顾|`batch.py`、`reading_batch.py`、`recap_backbone.py`、`remaining_blockers.py`|
|依赖与归属|`dependencies.py`、`declared_entity_content.py`、`declared_levelplay.py`、`dungeon_candidates.py`|
|副本时序|`levelplay_order.py`、`dungeon_return_text.py`、`dungeon_trigger_review.py`|
|外部正文|`external.py`、`phone.py`、`guides.py`、`letters.py`、`reigns.py`、`captions.py`|
|人物与显示|`speakers.py`、`inventory_speakers.py`、`rendering.py`、`reading.py`、`reading_markup.py`|
|阅读验收|`reading_review.py`与`docs/reviews/`中的审查记录|

动作支持模块在同一包内按主题划分，例如镜头、屏幕效果、NPC表演、子关卡和变量赋值。新增规则优先复用现有解析器，并以明确参数形状及真实案例验证。

## 运行入口

`python run.py`、`python -m wuwa_story`和安装后的`wuwa-story`共同委派到`cli.main`。CLI按需加载解析模块，帮助与参数检查可在没有数据库时运行。详细参数见[命令参考](commands.md)。

旧的模块运行入口如`python -m wuwa_story.recap_backbone`继续可用。公开模块路径保留，便于已有脚本和测试继续运行。

## 文件生命周期

- `ConfigDB/`保存输入快照，由数据库模块使用SQLite只读连接访问。
- `outputs/`保存可复现语料、覆盖报告和审查版。批次目录带时间戳。
- `work/`保存临时探查及运行日志。
- `docs/research/`保存长期有用的规则证据，`docs/reviews/`保存审查结论。
- 根目录规划文件只保留当前状态，完整历史存于`docs/history/`。

## 能力与已知限制

已有能力包括分支选择、可验证的条件投影、回顾顺序、说话人关联、外部文本提取、局部同步调用及保守的候选归属。JSON分别保留确定范围和未核验项，阅读验收需检查关键缺段、重复与衔接。

当前还有任务路线中断、无回顾排序、复杂变量和状态转移、QTE、运行时回调、部分媒体内容等限制。数据库字段解释依赖快照版本。`database.py`导入会建立文本索引，一些旧检查模块仍通过脚本入口执行。

下一步开发以[任务计划](../task_plan.md)为准。各项具体规则的证据见[研究目录](research/README.md)。
