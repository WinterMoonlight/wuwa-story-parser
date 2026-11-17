# 命令参考

在项目根目录使用 `python run.py`。安装项目后可将其替换为 `wuwa-story`，设置 `PYTHONPATH=src` 后也可使用 `python -m wuwa_story`。

## 语义明确的导出入口

```powershell
python run.py export-reading-batch
python run.py export-recap --quest-id 139000027 --output outputs/sample
python run.py export-recap --quest-id 147000002 --choices choices.json --output outputs/alternate
python run.py export-task --quest-id 880000013
python run.py export-task --quest-id 139000026 --allow-incomplete
```

`export-reading-batch`生成135条当前分类任务的覆盖阅读版与严格批处理报告。`export-recap`生成单任务阅读草稿，使用相同批量分析逻辑。`export-task`运行任务导出器，`--allow-incomplete`允许其已支持的阅读投影。

选择文件为JSON对象，键为解析器输出的选择键，值为从0开始的选项索引。实际例子见[条件路线验证](research/capture-dream-variables-validation.md)。

## 阅读审查版

```powershell
python run.py export-review --batch outputs/主线批量/20261117_132957_607004/覆盖阅读版 --review docs/reviews/reading-acceptance-005.json --output outputs/review
```

审查记录绑定源JSON/TXT的SHA-256。批次或文件变化时需重新核查，再更新审查记录。当前审查记录需要恢复对应本地批次才能重导。

## 数据和诊断

|命令|作用|
|---|---|
|`inspect`|检查主要数据库表和样例|
|`inventory`|扫描原始数据库，生成中间索引|
|`index`|基于inventory结果整理章节与流程索引|
|`scan-mainline`|任务结构和机制诊断|
|`export-mainline`|严格批处理与失败清单|
|`refresh-reading`|重新渲染已有导出TXT|

## 路径配置

|环境变量|默认值|
|---|---|
|`WUWA_PROJECT_ROOT`|源码项目根目录|
|`WUWA_CONFIG_DB`|`ConfigDB`|
|`WUWA_OUTPUT_DIR`|`outputs`|
|`WUWA_WORK_DIR`|`work`|

相对环境变量路径按项目根目录解析。`--output`、`--batch`等CLI显式路径按当前运行目录解析。
