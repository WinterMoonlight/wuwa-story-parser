# 换机恢复与开发接续

## 仓库与本地数据

Git保存源码、测试、README、docs以及根目录task_plan.md、findings.md、progress.md。ConfigDB、outputs、work、.codex、Python环境不随仓库上传。

克隆只恢复开发项目，不能恢复原始数据库或历史生成语料。请单独复制完整同版本ConfigDB，或设置WUWA_CONFIG_DB指向外部数据。历史文档的outputs/work链接仅在相应本地文件存在时可用。

## 恢复步骤

1. 先读[任务计划](../task_plan.md)的Next Step，再查[进度](../progress.md)和[研究结论](../findings.md)。
2. 安装Python 3.10+，当前验证平台为Windows / Python 3.13。
3. 恢复整个ConfigDB，不能只恢复中文库；核对Misc中的版本信息。
4. 在项目根目录执行：

```powershell
python --version
$env:PYTHONPATH = 'src'
python -m unittest discover -s tests -v
python run.py export-reading-batch
```

需要外部数据库时，先设置`$env:WUWA_CONFIG_DB = 'D:\GameData\ConfigDB'`。检查没有继承旧机器的WUWA_PROJECT_ROOT等路径变量。

测试含真实数据库读取；没有数据时不能保证测试可导入或通过。运行时无需第三方库或AI服务。若需要章节索引，依次运行`python run.py inventory`和`python run.py index`。

## 当前验证基线

2026-11-17，3.8.11快照：155项测试通过，135任务记录批量导出，132有文字，严格通过2；31任务还有68处回顾阻塞。最终批次20261117_023233_327940。这些是历史实测结果，不是换机后的保证。

最近完成[捕梦变量与左右路线](capture-dream-variables-validation.md)：只支持受限Boolean赋值与条件阅读路线，保留无外部改写假设。下一步核查变量在明确任务依赖间传播和FinishState/ChangeState边界。不要全局跳过SetVar，或把所有回顾段落当一条实际路线。

## 协作边界

- 通用解析器不添加任务ID、人物ID硬编码特例。
- 保留女漂泊者与玩家名替换规则；未知身份不猜。
- TXT只放可读内容，JSON保留来源、技术记录和缺口。
- 资产完整性后置；配置解析、顺序证据、整任务验收分开报告。
- 每次改动后运行适当测试和批量核对，更新根目录三份规划文件。
- planning-with-files采用根目录三文件，新机没有该skill也能接续；如需本地skills，请单独复制或安装，不覆盖既有计划。

给下一位协作者的启动说明：

> 先阅读task_plan.md、docs/handoff.md及最新验证文档，核实当前数据与测试。按Next Step继续实现通用规则，未知值和未知流程保留缺口；不把历史通过数当成本次实测。完成后更新规划与进度。
